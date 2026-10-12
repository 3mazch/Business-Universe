# -*- coding: utf-8 -*-
"""
validate_dimensions.py — Post-load validation for FlexCoffeeTea dimension tables.
==================================================================================
Runs after load_dimensions.py to verify data integrity in SQL Server.

Checks:
  [A] Row count: DB count matches CSV row count
  [B] PK uniqueness: no duplicate primary keys
  [C] NOT NULL columns: no nulls in critical fields
  [D] FK integrity: no orphan records
  [E] Business rules: store count, date range, key values

Usage:
    # Validate all dimensions
    python data_warehouse/db_loader/validate_dimensions.py

    # Validate a specific table
    python data_warehouse/db_loader/validate_dimensions.py --table dim_store

    # Show only failures
    python data_warehouse/db_loader/validate_dimensions.py --failures-only
"""

from __future__ import annotations

import sys
import io
import argparse
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

# UTF-8 stdout fix
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

THIS_DIR     = Path(__file__).parent
PROJECT_ROOT = THIS_DIR.parent.parent
DIM_DIR      = PROJECT_ROOT / "data" / "dimension" / "full"

sys.path.insert(0, str(THIS_DIR))
from db_config import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("validate")

# ── Check result store ────────────────────────────────────────────────────────
_results: list[dict] = []

def _check(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    icon   = "✅" if passed else "❌"
    msg    = f"  {icon} [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    if passed:
        log.info(msg)
    else:
        log.error(msg)
    _results.append({"check": name, "passed": passed, "detail": detail})


def _query_scalar(conn, sql: str, params=None):
    cur = conn.cursor()
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


# ============================================================================
# A. Row count checks
# ============================================================================

def check_row_counts(conn):
    """Compare CSV row count vs DB row count for every dimension table."""
    log.info("\n[A] ROW COUNT CHECKS")

    # Map csv filename → table name
    table_csv_map = {
        "dim_date":                       "dim_date.csv",
        "dim_product_category":           "dim_product_category.csv",
        "dim_membership_tier":            "dim_membership_tier.csv",
        "dim_modifier":                   "dim_modifier.csv",
        "dim_expense_category":           "dim_expense_category.csv",
        "dim_position":                   "dim_position.csv",
        "dim_shift":                      "dim_shift.csv",
        "dim_warehouse":                  "dim_warehouse.csv",
        "dim_supplier":                   "dim_supplier.csv",
        "dim_sales_channel":              "dim_sales_channel.csv",
        "dim_reward_catalog":             "dim_reward_catalog.csv",
        "dim_store":                      "dim_store.csv",
        "dim_product":                    "dim_product.csv",
        "dim_ingredient":                 "dim_ingredient.csv",
        "dim_product_variant":            "dim_product_variant.csv",
        "dim_customer":                   "dim_customer.csv",
        "dim_employee":                   "dim_employee.csv",
        "store_lease":                    "store_lease.csv",
        "store_operating_hours":          "store_operating_hours.csv",
        "dim_campaign":                   "dim_campaign.csv",
        "dim_recipe":                     "dim_recipe.csv",
        "dim_category_modifier_exclusion":"dim_category_modifier_exclusion.csv",
        "dim_campaign_product_scope":     "dim_campaign_product_scope.csv",
    }

    for table, csv_file in table_csv_map.items():
        csv_path = DIM_DIR / csv_file
        if not csv_path.exists():
            _check(f"A.{table} — CSV exists", False, f"File missing: {csv_path}")
            continue

        csv_count = len(pd.read_csv(csv_path, encoding="utf-8-sig"))
        db_count  = _query_scalar(conn, f"SELECT COUNT(*) FROM dbo.[{table}]")

        _check(
            f"A.{table} — row count",
            csv_count == db_count,
            f"CSV={csv_count:,}  DB={db_count:,}{'  ✓' if csv_count == db_count else '  MISMATCH'}",
        )


# ============================================================================
# B. PK uniqueness
# ============================================================================

def check_pk_uniqueness(conn):
    """Verify no duplicate PKs exist in critical tables."""
    log.info("\n[B] PRIMARY KEY UNIQUENESS")

    pk_checks = [
        ("dim_store",                 "store_id"),
        ("dim_product",               "product_id"),
        ("dim_product_variant",       "variant_id"),
        ("dim_customer",              "customer_id"),
        ("dim_employee",              "employee_id"),
        ("dim_campaign",              "campaign_id"),
        ("dim_date",                  "date_key"),
        ("dim_ingredient",            "ingredient_id"),
        ("dim_recipe",                "recipe_id"),
    ]

    for table, pk_col in pk_checks:
        sql = f"""
            SELECT COUNT(*) FROM (
                SELECT [{pk_col}], COUNT(*) as cnt
                FROM dbo.[{table}]
                GROUP BY [{pk_col}]
                HAVING COUNT(*) > 1
            ) dupes
        """
        dupes = _query_scalar(conn, sql)
        _check(f"B.{table} — no duplicate {pk_col}", dupes == 0,
               f"{dupes} duplicate PKs" if dupes > 0 else "All unique")


# ============================================================================
# C. NOT NULL checks
# ============================================================================

def check_not_nulls(conn):
    """Check critical NOT NULL columns for unexpected nulls."""
    log.info("\n[C] NOT NULL CHECKS")

    null_checks = [
        ("dim_store",           "store_code"),
        ("dim_store",           "city"),
        ("dim_store",           "location_tier"),
        ("dim_product",         "product_name"),
        ("dim_product",         "category_id"),
        ("dim_product_variant", "variant_id"),
        ("dim_product_variant", "base_price_vnd"),
        ("dim_customer",        "registration_date"),
        ("dim_employee",        "hire_date"),
        ("dim_employee",        "contract_type"),
        ("dim_date",            "full_date"),
        ("dim_ingredient",      "unit"),
    ]

    for table, col in null_checks:
        null_count = _query_scalar(
            conn, f"SELECT COUNT(*) FROM dbo.[{table}] WHERE [{col}] IS NULL"
        )
        _check(f"C.{table}.{col} — no nulls", null_count == 0,
               f"{null_count} null rows" if null_count > 0 else "OK")


# ============================================================================
# D. FK integrity
# ============================================================================

def check_fk_integrity(conn):
    """Spot-check key FK relationships for orphan records."""
    log.info("\n[D] FOREIGN KEY INTEGRITY")

    fk_checks = [
        # (child_table, child_col, parent_table, parent_col, description)
        ("dim_product",         "category_id",  "dim_product_category", "category_id",
         "product → category"),
        ("dim_product_variant", "product_id",   "dim_product",          "product_id",
         "variant → product"),
        ("dim_recipe",          "variant_id",   "dim_product_variant",  "variant_id",
         "recipe → variant"),
        ("dim_recipe",          "ingredient_id","dim_ingredient",       "ingredient_id",
         "recipe → ingredient"),
        ("dim_customer",        "home_store_id","dim_store",            "store_id",
         "customer → store"),
        ("dim_employee",        "store_id",     "dim_store",            "store_id",
         "employee → store"),
        ("dim_employee",        "position_id",  "dim_position",         "position_id",
         "employee → position"),
        ("store_lease",         "store_id",     "dim_store",            "store_id",
         "lease → store"),
        ("dim_campaign",        "scope_store_id","dim_store",           "store_id",
         "campaign → store (nullable)"),
    ]

    for child_t, child_col, parent_t, parent_col, desc in fk_checks:
        # For nullable FKs, only check non-null child values
        sql = f"""
            SELECT COUNT(*)
            FROM dbo.[{child_t}] c
            WHERE c.[{child_col}] IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM dbo.[{parent_t}] p
                  WHERE p.[{parent_col}] = c.[{child_col}]
              )
        """
        orphans = _query_scalar(conn, sql)
        _check(f"D.{desc}", orphans == 0,
               f"{orphans} orphan rows" if orphans > 0 else "No orphans")


# ============================================================================
# E. Business rule checks
# ============================================================================

def check_business_rules(conn):
    """Verify key business facts are correctly loaded."""
    log.info("\n[E] BUSINESS RULE CHECKS")

    # E01: Exactly 25 stores
    store_count = _query_scalar(conn, "SELECT COUNT(*) FROM dbo.dim_store")
    _check("E01: dim_store — exactly 25 stores", store_count == 25,
           f"Found {store_count} stores")

    # E02: dim_date includes the required 2023–2026 simulation window.
    min_date = _query_scalar(conn, "SELECT MIN(full_date) FROM dbo.dim_date")
    max_date = _query_scalar(conn, "SELECT MAX(full_date) FROM dbo.dim_date")
    _check(
        "E02: dim_date — includes 2023 to 2026",
        min_date is not None
        and str(min_date) <= "2023-01-01"
        and str(max_date) >= "2026-12-31",
        f"Range: {min_date} → {max_date}; required window: 2023-01-01 → 2026-12-31",
    )

    # E03: dim_product_category has 7 categories (CAT-01 .. CAT-07)
    cat_count = _query_scalar(conn, "SELECT COUNT(*) FROM dbo.dim_product_category")
    _check("E03: dim_product_category — 7 categories", cat_count == 7,
           f"Found {cat_count}")

    # E04: All stores have at least 1 employee
    stores_without_emp = _query_scalar(conn, """
        SELECT COUNT(*) FROM dbo.dim_store s
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.dim_employee e WHERE e.store_id = s.store_id
        )
    """)
    _check("E04: all stores have employees", stores_without_emp == 0,
           f"{stores_without_emp} stores without employees")

    # E05: dim_product_variant — all variants have a valid base_price > 0
    bad_price = _query_scalar(
        conn, "SELECT COUNT(*) FROM dbo.dim_product_variant WHERE base_price_vnd <= 0"
    )
    _check("E05: all variants have price > 0", bad_price == 0,
           f"{bad_price} variants with invalid price")

    # E06: dim_membership_tier — 3 tiers
    tier_count = _query_scalar(conn, "SELECT COUNT(*) FROM dbo.dim_membership_tier")
    _check("E06: dim_membership_tier — 3 tiers", tier_count == 3,
           f"Found {tier_count}")

    # E07: dim_recipe — every beverage variant has at least 1 recipe row
    beverage_variants_without_recipe = _query_scalar(conn, """
        SELECT COUNT(*)
        FROM dbo.dim_product_variant v
        JOIN dbo.dim_product p ON p.product_id = v.product_id
        JOIN dbo.dim_product_category c ON c.category_id = p.category_id
        WHERE c.category_id IN ('CAT-01','CAT-02','CAT-03','CAT-04')
          AND NOT EXISTS (
              SELECT 1 FROM dbo.dim_recipe r WHERE r.variant_id = v.variant_id
          )
    """)
    _check("E07: all beverage variants have recipe rows",
           beverage_variants_without_recipe == 0,
           f"{beverage_variants_without_recipe} beverage variants missing recipe")

    # E08: store location_tier only contains valid values
    bad_tier = _query_scalar(
        conn, "SELECT COUNT(*) FROM dbo.dim_store WHERE location_tier NOT IN ('prime','standard','secondary')"
    )
    _check("E08: dim_store.location_tier — valid values only", bad_tier == 0,
           f"{bad_tier} rows with invalid tier")


# ============================================================================
# Main runner
# ============================================================================

def run(table_filter: Optional[str] = None, failures_only: bool = False):
    log.info("=" * 65)
    log.info("Flex Coffee & Tea — Dimension Validation (post-load)")
    log.info("=" * 65)

    try:
        conn = get_connection(autocommit=True)
        log.info("Connected to SQL Server ✅\n")
    except Exception as exc:
        log.error(f"Cannot connect: {exc}")
        sys.exit(1)

    check_row_counts(conn)
    check_pk_uniqueness(conn)
    check_not_nulls(conn)
    check_fk_integrity(conn)
    check_business_rules(conn)

    conn.close()

    # ── Final summary ─────────────────────────────────────────────────────────
    total  = len(_results)
    passed = sum(1 for r in _results if r["passed"])
    failed = total - passed

    log.info("\n" + "=" * 65)
    log.info(f"VALIDATION SUMMARY: {passed}/{total} checks passed")
    if failed > 0:
        log.error(f"  ❌ {failed} checks FAILED:")
        for r in _results:
            if not r["passed"]:
                log.error(f"     - {r['check']}: {r['detail']}")
    else:
        log.info("  🎉 All checks passed! Dimensions look good.")
    log.info("=" * 65)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Post-load validation of dimension tables in SQL Server"
    )
    parser.add_argument("--table", type=str, default=None,
                        help="Validate only this table (not yet filtered, runs all)")
    parser.add_argument("--failures-only", action="store_true",
                        help="Only print failed checks")
    args = parser.parse_args()
    run(table_filter=args.table, failures_only=args.failures_only)
