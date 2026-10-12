# -*- coding: utf-8 -*-
"""
load_dimensions.py — Step 3: Load Dimension Tables → SQL Server FlexCoffeeTea
==============================================================================
Loads all 23 dimension CSV files from data/dimension/full/ into SQL Server
in the correct FK dependency order (Tier 0 → Tier 1 → Tier 2 → Tier 3).

Usage:
    # Load all dimensions (from project root)
    python data_warehouse/db_loader/load_dimensions.py

    # Load a specific table only
    python data_warehouse/db_loader/load_dimensions.py --table dim_store

    # Dry-run: validate CSV but don't write to DB
    python data_warehouse/db_loader/load_dimensions.py --dry-run

    # Truncate-reload (overwrite existing data)
    python data_warehouse/db_loader/load_dimensions.py --truncate

Prerequisites:
    1. SQL Server is running and database FlexCoffeeTea exists.
       Run: data_warehouse/schema/create_schema.sql first.
    2. Copy .env.example → .env and fill in connection details.
    3. pip install -r requirements.txt
"""

from __future__ import annotations

import sys
import os
import io
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
import pyodbc

# UTF-8 stdout fix for Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Resolve paths ────────────────────────────────────────────────────────────
THIS_DIR    = Path(__file__).parent
PROJECT_ROOT = THIS_DIR.parent.parent
DIM_DIR      = PROJECT_ROOT / "data" / "dimension" / "full"

sys.path.insert(0, str(THIS_DIR))
from db_config import get_connection

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("loader")

# ============================================================================
# TABLE REGISTRY
# Each entry: (table_name_in_db, csv_filename, [cols_to_drop_from_csv])
# Load order respects FK dependencies: Tier 0 → 1 → 2 → 3
# ============================================================================
DIMENSION_LOAD_ORDER: list[dict] = [
    # ── Tier 0: No foreign key dependencies ─────────────────────────────────
    {
        "table": "dim_date",
        "csv":   "dim_date.csv",
        "drop":  [],
    },
    {
        "table": "dim_product_category",
        "csv":   "dim_product_category.csv",
        "drop":  [],
    },
    {
        "table": "dim_membership_tier",
        "csv":   "dim_membership_tier.csv",
        "drop":  [],
    },
    {
        "table": "dim_modifier",
        "csv":   "dim_modifier.csv",
        "drop":  [],
    },
    {
        "table": "dim_expense_category",
        "csv":   "dim_expense_category.csv",
        "drop":  [],
    },
    {
        "table": "dim_position",
        "csv":   "dim_position.csv",
        "drop":  [],
    },
    {
        "table": "dim_shift",
        "csv":   "dim_shift.csv",
        "drop":  [],
    },
    {
        "table": "dim_warehouse",
        "csv":   "dim_warehouse.csv",
        "drop":  [],
    },
    {
        "table": "dim_supplier",
        "csv":   "dim_supplier.csv",
        "drop":  [],
    },
    {
        "table": "dim_sales_channel",
        "csv":   "dim_sales_channel.csv",
        "drop":  [],
    },
    {
        "table": "dim_reward_catalog",
        "csv":   "dim_reward_catalog.csv",
        "drop":  [],
    },
    # ── Tier 1: Depends on Tier 0 ───────────────────────────────────────────
    {
        "table": "dim_store",
        "csv":   "dim_store.csv",
        # Extra analytics cols in CSV not in schema — drop before insert
        "drop":  [
            "monthly_rent_vnd",          # in store_lease table
            "monthly_revenue_baseline_vnd",
            "revenue_per_m2_vnd",
            "months_alive_at_window_end",
        ],
    },
    {
        "table": "dim_product",
        "csv":   "dim_product.csv",
        "drop":  [],
    },
    {
        "table": "dim_ingredient",
        "csv":   "dim_ingredient.csv",
        "drop":  [],
    },
    # ── Tier 2: Depends on Tier 1 ───────────────────────────────────────────
    {
        "table": "dim_product_variant",
        "csv":   "dim_product_variant.csv",
        "drop":  [],
    },
    {
        "table": "dim_customer",
        "csv":   "dim_customer.csv",
        "drop":  [],
    },
    {
        "table": "dim_employee",
        "csv":   "dim_employee.csv",
        # position_name and slot_seq are denormalized columns not in schema
        "drop":  ["position_name", "slot_seq"],
    },
    {
        "table": "store_lease",
        "csv":   "store_lease.csv",
        "drop":  [],
    },
    {
        "table": "store_operating_hours",
        "csv":   "store_operating_hours.csv",
        "drop":  [],
    },
    {
        "table": "dim_campaign",
        "csv":   "dim_campaign.csv",
        # Extra denormalized cols in CSV not in schema
        "drop":  ["linked_product_id", "linked_product_name"],
    },
    # ── Tier 3: Depends on Tier 2 ───────────────────────────────────────────
    {
        "table": "dim_recipe",
        "csv":   "dim_recipe.csv",
        # ingredient_name is denormalized in CSV, not in schema
        "drop":  ["ingredient_name"],
    },
    {
        "table": "dim_category_modifier_exclusion",
        "csv":   "dim_category_modifier_exclusion.csv",
        "drop":  [],
        # CSV has 'excluded_modifier_group' but schema col is 'modifier_group'
        "rename": {"excluded_modifier_group": "modifier_group"},
        # SQL schema requires a key not provided by the source CSV.
        "generated_pk": "exclusion_id",
    },
    {
        "table": "dim_campaign_product_scope",
        "csv":   "dim_campaign_product_scope.csv",
        "drop":  [],
    },
]

# Build lookup: table_name → config
TABLE_REGISTRY: dict[str, dict] = {entry["table"]: entry for entry in DIMENSION_LOAD_ORDER}


# ============================================================================
# Helper: dtype → SQL-friendly Python type coercion
# ============================================================================

def _coerce_row(row: tuple) -> tuple:
    """Replace NaN/NaT with None so pyodbc sends proper SQL NULL."""
    result = []
    for val in row:
        if val is None:
            result.append(None)
        elif isinstance(val, float) and (val != val):  # NaN check
            result.append(None)
        elif hasattr(val, "isoformat"):  # date / datetime
            result.append(val)
        elif str(val).lower() in ("nan", "nat", "none", "<na>"):
            result.append(None)
        else:
            result.append(val)
    return tuple(result)


def _clean_df(df: pd.DataFrame, drop_cols: list[str], rename_cols: dict | None = None) -> pd.DataFrame:
    """Drop extra columns, rename cols, and replace NaN with None."""
    existing_drops = [c for c in drop_cols if c in df.columns]
    if existing_drops:
        df = df.drop(columns=existing_drops)
    if rename_cols:
        df = df.rename(columns=rename_cols)
    # Replace string "nan", "NaN", "None", "(None, None)" with actual NaN
    df = df.replace({"nan": None, "NaN": None, "None": None,
                     "(None, None)": None, "NaT": None})
    # Replace pandas NA/NaN
    df = df.where(pd.notna(df), other=None)
    return df


# ============================================================================
# Core loader
# ============================================================================

def load_table(
    conn: pyodbc.Connection,
    config: dict,
    truncate: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Load a single dimension table from CSV → SQL Server.

    Returns a result dict with keys: table, csv_rows, inserted, skipped, status.
    """
    table_name = config["table"]
    csv_file   = DIM_DIR / config["csv"]
    drop_cols  = config.get("drop", [])
    rename_cols = config.get("rename", None)

    result = {
        "table":    table_name,
        "csv_rows": 0,
        "inserted": 0,
        "skipped":  0,
        "status":   "ok",
    }

    # ── Load CSV ─────────────────────────────────────────────────────────────
    if not csv_file.exists():
        log.error(f"  [{table_name}] CSV not found: {csv_file}")
        result["status"] = "missing_csv"
        return result

    df = pd.read_csv(csv_file, encoding="utf-8-sig", low_memory=False)
    result["csv_rows"] = len(df)

    if len(df) == 0:
        log.warning(f"  [{table_name}] CSV is empty, skipping.")
        result["status"] = "empty"
        return result

    df = _clean_df(df, drop_cols, rename_cols)

    log.info(f"  [{table_name}] CSV: {len(df):,} rows | cols: {list(df.columns)}")

    if dry_run:
        if config.get("generated_pk") and config["generated_pk"] not in df.columns:
            log.info(
                f"  [{table_name}] DRY-RUN: would generate "
                f"{config['generated_pk']} values during load."
            )
        log.info(f"  [{table_name}] DRY-RUN: would insert {len(df):,} rows.")
        result["status"] = "dry_run"
        return result

    # ── Truncate if requested ─────────────────────────────────────────────────
    cursor = conn.cursor()
    if truncate:
        try:
            cursor.execute(f"TRUNCATE TABLE dbo.[{table_name}]")
            log.info(f"  [{table_name}] Truncated.")
        except pyodbc.Error as e:
            # If truncate fails (e.g. FK constraints), use DELETE instead
            log.warning(f"  [{table_name}] TRUNCATE failed ({e.args[1][:60]}...), using DELETE.")
            cursor.execute(f"DELETE FROM dbo.[{table_name}]")
        conn.commit()

    generated_pk = config.get("generated_pk")
    if generated_pk and generated_pk not in df.columns:
        cursor.execute(f"SELECT COALESCE(MAX([{generated_pk}]), 0) FROM dbo.[{table_name}]")
        first_id = cursor.fetchone()[0] + 1
        df.insert(0, generated_pk, range(first_id, first_id + len(df)))

    # ── Build INSERT statement ────────────────────────────────────────────────
    cols        = list(df.columns)
    placeholders = ", ".join(["?"] * len(cols))
    col_names    = ", ".join([f"[{c}]" for c in cols])
    sql          = f"INSERT INTO dbo.[{table_name}] ({col_names}) VALUES ({placeholders})"

    # ── Batch insert ─────────────────────────────────────────────────────────
    # fast_executemany misbinds mixed CSV values with the installed SQL Server
    # driver; regular executemany preserves the correct SQL conversions.
    cursor.fast_executemany = False

    BATCH_SIZE = 1000
    rows_data  = [_coerce_row(row) for row in df.itertuples(index=False)]

    inserted = 0
    errors   = 0
    for i in range(0, len(rows_data), BATCH_SIZE):
        batch = rows_data[i : i + BATCH_SIZE]
        try:
            cursor.executemany(sql, batch)
            conn.commit()
            inserted += len(batch)
        except pyodbc.Error as exc:
            conn.rollback()
            errors += len(batch)
            log.error(f"  [{table_name}] Batch {i//BATCH_SIZE + 1} FAILED: {exc.args[1][:120]}")
            result["status"] = "partial_error"

    result["inserted"] = inserted
    result["skipped"]  = errors
    if errors == 0:
        log.info(f"  [{table_name}] ✅ Inserted {inserted:,} rows.")
    else:
        log.warning(f"  [{table_name}] ⚠️  Inserted {inserted:,} rows | Errors: {errors:,} rows.")

    cursor.close()
    return result


# ============================================================================
# Main runner
# ============================================================================

def run(
    table_filter: Optional[str] = None,
    truncate: bool = False,
    dry_run: bool = False,
):
    """Load all (or selected) dimension tables into SQL Server."""
    start = datetime.now()

    log.info("=" * 65)
    log.info("Flex Coffee & Tea — Step 3: Load Dimensions to SQL Server")
    log.info(f"  DB:        {os.environ.get('DB_NAME', 'FlexCoffeeTea')}")
    log.info(f"  Server:    {os.environ.get('DB_SERVER', 'localhost')}")
    log.info(f"  CSV dir:   {DIM_DIR}")
    log.info(f"  Truncate:  {truncate}")
    log.info(f"  Dry-run:   {dry_run}")
    log.info("=" * 65)

    # Select tables to load
    if table_filter:
        if table_filter not in TABLE_REGISTRY:
            log.error(f"Unknown table '{table_filter}'. "
                      f"Valid options: {list(TABLE_REGISTRY.keys())}")
            sys.exit(1)
        tables_to_load = [TABLE_REGISTRY[table_filter]]
    else:
        tables_to_load = DIMENSION_LOAD_ORDER

    # Connect
    if not dry_run:
        try:
            conn = get_connection(autocommit=False)
            log.info("Connected to SQL Server ✅")
        except Exception as exc:
            log.error(f"Cannot connect to SQL Server: {exc}")
            log.error("Check your .env file — see .env.example for format.")
            sys.exit(1)
    else:
        conn = None

    # Load each table
    summary = []
    for config in tables_to_load:
        log.info(f"\n── {config['table']} ──────────────")
        result = load_table(conn, config, truncate=truncate, dry_run=dry_run)
        summary.append(result)

    if conn:
        conn.close()

    # ── Print summary ─────────────────────────────────────────────────────────
    elapsed = (datetime.now() - start).total_seconds()
    log.info("\n" + "=" * 65)
    log.info("SUMMARY")
    log.info("=" * 65)
    log.info(f"  {'Table':<40} {'CSV':>7} {'Ins':>7} {'Err':>5}  Status")
    log.info(f"  {'-'*40} {'-'*7} {'-'*7} {'-'*5}  ------")
    total_csv = total_ins = total_err = 0
    for r in summary:
        icon = (
            "✅" if r["status"] in ("ok", "dry_run", "empty")
            else "⚠️ " if r["status"] == "partial_error"
            else "❌"
        )
        log.info(
            f"  {r['table']:<40} {r['csv_rows']:>7,} {r['inserted']:>7,} "
            f"{r['skipped']:>5,}  {icon} {r['status']}"
        )
        total_csv += r["csv_rows"]
        total_ins += r["inserted"]
        total_err += r["skipped"]
    log.info(f"  {'TOTAL':<40} {total_csv:>7,} {total_ins:>7,} {total_err:>5,}")
    log.info(f"\n  Elapsed: {elapsed:.1f}s")
    log.info("=" * 65)

    if total_err > 0:
        log.warning("Some rows had errors. Check logs above for details.")
        sys.exit(1)
    else:
        log.info("All dimensions loaded successfully. 🎉")


# ============================================================================
# CLI entry point
# ============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load dimension tables from CSV → SQL Server FlexCoffeeTea"
    )
    parser.add_argument(
        "--table", type=str, default=None,
        help="Load only this specific table (e.g. --table dim_store)"
    )
    parser.add_argument(
        "--truncate", action="store_true",
        help="Truncate table before inserting (overwrite existing data)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate CSV files without writing to DB"
    )
    args = parser.parse_args()
    run(table_filter=args.table, truncate=args.truncate, dry_run=args.dry_run)
