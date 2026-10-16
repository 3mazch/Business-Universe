"""Generate SQL-schema-aligned Sale/Orders facts from the confirmed dimensions.

The engine writes order headers, items, modifiers, payments, and campaign
discounts only. Inventory and purchase-order facts are intentionally downstream.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import logging
import math
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.constants import (  # noqa: E402
    CATEGORY_MIX,
    DATA_SIM_END,
    DATA_SIM_START,
    DIMENSION_DIR,
    ITEMS_PER_ORDER,
    MODIFIER_RATES,
    OUTLIER_STORE_AOV_MULTIPLIER,
    PAYMENT_DIST,
    PAYMENT_SURCHARGE,
    PRICE_FACTOR,
    SALE_ORDER_DIR,
)
from utils.date_utils import (  # noqa: E402
    daily_weights_for_month,
    is_double_day,
    pick_order_time,
    pos_customer_rate,
    sim_months,
)
from utils.seed_utils import get_seed  # noqa: E402
from utils.store_utils import (  # noqa: E402
    get_monthly_revenue_target,
    load_operating_hours,
    load_stores,
    store_maturity_factor,
)

LOG = logging.getLogger("sale_order_engine")
DIM_DIR = Path(DIMENSION_DIR)
DEFAULT_OUTPUT_DIR = Path(SALE_ORDER_DIR)
SAMPLE_SEED = 20261015
SAMPLE_SIZE = 100
STATUS_WEIGHTS = (("completed", 0.97), ("canceled", 0.02), ("refunded", 0.01))
DELIVERY_PLATFORM_WEIGHTS = {
    "Grab": 0.45,
    "ShopeeFood": 0.40,
    "BeFood": 0.10,
    "GreenSM": 0.05,
}
MONTHLY_SEASONALITY = {
    1: 1.00,
    2: 0.95,
    3: 0.98,
    4: 1.03,
    5: 1.05,
    6: 1.05,
    7: 1.05,
    8: 1.04,
    9: 1.00,
    10: 1.00,
    11: 1.01,
    12: 1.04,
}

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "fact_order": (
        "order_id", "store_id", "customer_id", "channel_id", "date_key",
        "order_datetime", "order_type", "order_status", "gross_amount_vnd",
        "discount_amount_vnd", "net_amount_vnd",
    ),
    "fact_order_item": (
        "order_id", "item_seq", "variant_id", "quantity", "unit_price_vnd",
        "line_amount_vnd",
    ),
    "fact_order_item_modifier": (
        "order_id", "item_seq", "modifier_id", "modifier_name",
        "modifier_group", "extra_price_vnd",
    ),
    "fact_payment": (
        "order_id", "payment_method", "payment_status", "payment_amount_vnd",
        "payment_surcharge_vnd", "payment_datetime",
    ),
    "fact_order_discount": (
        "order_id", "campaign_id", "discount_amount_vnd", "campaign_type",
    ),
}
TABLES = tuple(TABLE_COLUMNS)
INPUT_FILES = (
    "dim_store.csv",
    "dim_customer.csv",
    "dim_employee.csv",
    "dim_date.csv",
    "dim_product_category.csv",
    "dim_product.csv",
    "dim_product_variant.csv",
    "dim_modifier.csv",
    "dim_category_modifier_exclusion.csv",
    "dim_sales_channel.csv",
    "dim_campaign.csv",
    "dim_campaign_product_scope.csv",
    "store_operating_hours.csv",
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if value.lower() in {"", "nan", "none", "nat", "<na>", "(none, none)"}:
        return ""
    return value


def _date(value: Any, field: str, *, optional: bool = False) -> date | None:
    value = _text(value)
    if not value and optional:
        return None
    if not value:
        raise ValueError(f"Required date {field!r} is missing")
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ValueError(f"Invalid date in {field}: {value!r}") from exc


def _integer(value: Any, field: str, *, optional: bool = False) -> int | None:
    value = _text(value)
    if not value and optional:
        return None
    if not value:
        raise ValueError(f"Required integer {field!r} is missing")
    try:
        return int(float(value))
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid integer in {field}: {value!r}") from exc


def _number(value: Any, field: str, default: float | None = None) -> float:
    value = _text(value)
    if not value:
        if default is not None:
            return default
        raise ValueError(f"Required number {field!r} is missing")
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid number in {field}: {value!r}") from exc
    if not math.isfinite(parsed):
        if default is not None:
            return default
        raise ValueError(f"Non-finite number in {field}: {value!r}")
    return parsed


def _read_csv(name: str) -> list[dict[str, str]]:
    path = DIM_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Required dimension CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            raise ValueError(f"Dimension CSV has no header: {path}")
        return [dict(row) for row in reader]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _columns(rows: list[dict[str, str]], name: str, required: Iterable[str]) -> None:
    if not rows:
        raise ValueError(f"Required dimension {name} is empty")
    missing = set(required) - set(rows[0])
    if missing:
        raise ValueError(f"{name} is missing required columns: {sorted(missing)}")


def _assert_unique(values: Iterable[Any], name: str) -> None:
    values = list(values)
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate key found in dimension {name}")


def _parse_employee_intervals(
    employee_rows: list[dict[str, str]],
) -> dict[int, list[tuple[date, date | None]]]:
    intervals: dict[int, list[tuple[date, date | None]]] = defaultdict(list)
    for row in employee_rows:
        store_id = _integer(row["store_id"], "dim_employee.store_id")
        hire_date = _date(row["hire_date"], "dim_employee.hire_date")
        end_date = _date(
            row.get("termination_date"), "dim_employee.termination_date", optional=True
        )
        if end_date is not None and end_date < hire_date:
            raise ValueError(f"Employee {row['employee_id']} terminates before hire date")
        intervals[store_id].append((hire_date, end_date))
    return intervals


class SaleOrderDimensions:
    """Validated, immutable in-memory view of the confirmed dimension CSVs."""

    def __init__(self) -> None:
        self.rows = {name: _read_csv(name) for name in INPUT_FILES}
        self.stores = self._load_stores()
        self.hours = self._load_hours()
        self.customers = self._load_customers()
        self.customer_pools = self._build_customer_pools()
        self.staff_intervals = _parse_employee_intervals(self.rows["dim_employee.csv"])
        self.channels = self._load_channels()
        self.products = self._load_products()
        self.variants = self._load_variants()
        self.modifiers = self._load_modifiers()
        self.exclusions = self._load_exclusions()
        self.campaigns = self._load_campaigns()
        self.campaign_product_scope = self._load_campaign_product_scope()
        self.date_coverage = self._load_date_coverage()
        self._campaign_cache: dict[tuple[date, int, int], list[dict[str, Any]]] = {}
        self._variant_cache: dict[date, dict[str, list[dict[str, Any]]]] = {}
        self._preflight()

    def _load_stores(self) -> dict[int, dict[str, Any]]:
        required = (
            "store_id", "store_code", "location_tier", "open_date", "closed_date",
            "temp_close_start", "temp_close_end", "monthly_revenue_baseline_vnd",
            "channel_mix_dine_in", "channel_mix_app", "channel_mix_delivery",
        )
        _columns(self.rows["dim_store.csv"], "dim_store.csv", required)
        store_df = load_stores()
        stores: dict[int, dict[str, Any]] = {}
        for _, record in store_df.iterrows():
            row = record.to_dict()
            store_id = int(row["store_id"])
            row["store_id"] = store_id
            stores[store_id] = row
        _assert_unique(stores, "dim_store.store_id")
        return stores

    def _load_hours(self) -> dict[int, dict[int, tuple[str, str]]]:
        rows = self.rows["store_operating_hours.csv"]
        _columns(rows, "store_operating_hours.csv",
                 ("store_id", "day_of_week", "open_time", "close_time"))
        result: dict[int, dict[int, tuple[str, str]]] = defaultdict(dict)
        for row in rows:
            store_id = _integer(row["store_id"], "store_operating_hours.store_id")
            weekday = _integer(row["day_of_week"], "store_operating_hours.day_of_week")
            open_time = time.fromisoformat(row["open_time"])
            close_time = time.fromisoformat(row["close_time"])
            if weekday not in range(1, 8) or close_time <= open_time:
                raise ValueError(f"Invalid operating-hours row: {row}")
            if weekday in result[store_id]:
                raise ValueError(f"Duplicate operating-hours weekday for store {store_id}")
            result[store_id][weekday] = (row["open_time"], row["close_time"])
        return dict(result)

    def _load_customers(self) -> list[dict[str, Any]]:
        rows = self.rows["dim_customer.csv"]
        _columns(rows, "dim_customer.csv",
                 ("customer_id", "registration_date", "registration_channel", "home_store_id"))
        result = []
        for row in rows:
            result.append({
                **row,
                "customer_id_int": _integer(row["customer_id"], "dim_customer.customer_id"),
                "registration_date_dt": _date(row["registration_date"],
                                              "dim_customer.registration_date"),
                "home_store_id_int": _integer(row.get("home_store_id"),
                                               "dim_customer.home_store_id", optional=True),
            })
        _assert_unique((r["customer_id_int"] for r in result), "dim_customer.customer_id")
        return result

    def _build_customer_pools(self) -> dict[str, dict[int | None, tuple[list[date], list[int]]]]:
        grouped: dict[str, dict[int | None, list[tuple[date, int]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for row in self.customers:
            grouped[row["registration_channel"]][row["home_store_id_int"]].append(
                (row["registration_date_dt"], row["customer_id_int"])
            )
            grouped[row["registration_channel"]][None].append(
                (row["registration_date_dt"], row["customer_id_int"])
            )
        pools = {}
        for channel, groups in grouped.items():
            pools[channel] = {}
            for store_id, pairs in groups.items():
                pairs.sort()
                pools[channel][store_id] = (
                    [pair[0] for pair in pairs],
                    [pair[1] for pair in pairs],
                )
        return pools

    def _load_channels(self) -> list[dict[str, Any]]:
        rows = self.rows["dim_sales_channel.csv"]
        _columns(rows, "dim_sales_channel.csv",
                 ("channel_id", "channel_name", "channel_group", "launch_date"))
        result = []
        for row in rows:
            channel_group = row["channel_group"]
            if channel_group not in {"dine_in", "app", "delivery"}:
                raise ValueError(f"Invalid channel_group: {row}")
            result.append({
                **row,
                "channel_id_int": _integer(row["channel_id"], "dim_sales_channel.channel_id"),
                "launch_date_dt": _date(row["launch_date"], "dim_sales_channel.launch_date"),
            })
        _assert_unique((r["channel_id_int"] for r in result), "dim_sales_channel.channel_id")
        _assert_unique((r["channel_name"] for r in result), "dim_sales_channel.channel_name")
        return result

    def _load_products(self) -> dict[str, dict[str, Any]]:
        rows = self.rows["dim_product.csv"]
        _columns(rows, "dim_product.csv",
                 ("product_id", "category_id", "launch_date", "discontinued_date", "status"))
        result = {}
        for row in rows:
            result[row["product_id"]] = {
                **row,
                "launch_date_dt": _date(row["launch_date"], "dim_product.launch_date",
                                        optional=True),
                "discontinued_date_dt": _date(row["discontinued_date"],
                                              "dim_product.discontinued_date", optional=True),
            }
        _assert_unique(result, "dim_product.product_id")
        return result

    def _load_variants(self) -> list[dict[str, Any]]:
        rows = self.rows["dim_product_variant.csv"]
        _columns(rows, "dim_product_variant.csv",
                 ("variant_id", "product_id", "base_price_vnd", "effective_from",
                  "effective_to", "is_current"))
        result = []
        for row in rows:
            if row["product_id"] not in self.products:
                raise ValueError(f"Variant {row['variant_id']} has unknown product")
            result.append({
                **row,
                "base_price_int": _integer(row["base_price_vnd"],
                                           "dim_product_variant.base_price_vnd"),
                "effective_from_dt": _date(row["effective_from"],
                                           "dim_product_variant.effective_from"),
                "effective_to_dt": _date(row["effective_to"],
                                         "dim_product_variant.effective_to", optional=True),
                "category_id": self.products[row["product_id"]]["category_id"],
            })
        _assert_unique((r["variant_id"] for r in result), "dim_product_variant.variant_id")
        return result

    def _load_modifiers(self) -> dict[str, list[dict[str, Any]]]:
        rows = self.rows["dim_modifier.csv"]
        _columns(rows, "dim_modifier.csv",
                 ("modifier_id", "modifier_group", "modifier_name", "extra_price_vnd"))
        result: dict[str, list[dict[str, Any]]] = defaultdict(list)
        ids = []
        for row in rows:
            if row["modifier_group"] not in {"topping", "sweetness", "ice"}:
                raise ValueError(f"Unsupported modifier group: {row['modifier_group']}")
            modifier = {
                **row,
                "modifier_id_int": _integer(row["modifier_id"], "dim_modifier.modifier_id"),
                "extra_price_int": _integer(row["extra_price_vnd"],
                                            "dim_modifier.extra_price_vnd"),
            }
            ids.append(modifier["modifier_id_int"])
            result[row["modifier_group"]].append(modifier)
        _assert_unique(ids, "dim_modifier.modifier_id")
        return dict(result)

    def _load_exclusions(self) -> dict[str, set[str]]:
        rows = self.rows["dim_category_modifier_exclusion.csv"]
        _columns(rows, "dim_category_modifier_exclusion.csv",
                 ("category_id", "excluded_modifier_group"))
        result: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            result[row["category_id"]].add(row["excluded_modifier_group"])
        return dict(result)

    def _load_campaigns(self) -> list[dict[str, Any]]:
        rows = self.rows["dim_campaign.csv"]
        _columns(rows, "dim_campaign.csv",
                 ("campaign_id", "campaign_type", "start_date", "end_date", "scope_type",
                  "scope_store_id", "scope_channel_id", "discount_value",
                  "expected_uplift_pct", "priority"))
        valid_types = {"percent_discount", "bogo", "flash_sale", "seasonal"}
        valid_scopes = {"system", "store", "channel"}
        result = []
        for row in rows:
            campaign = {
                **row,
                "campaign_id_int": _integer(row["campaign_id"], "dim_campaign.campaign_id"),
                "start_date_dt": _date(row["start_date"], "dim_campaign.start_date"),
                "end_date_dt": _date(row["end_date"], "dim_campaign.end_date"),
                "scope_store_id_int": _integer(row["scope_store_id"],
                                                "dim_campaign.scope_store_id", optional=True),
                "scope_channel_id_int": _integer(row["scope_channel_id"],
                                                  "dim_campaign.scope_channel_id", optional=True),
                "discount_value_num": _number(row["discount_value"],
                                               "dim_campaign.discount_value", default=0.0),
                "uplift_pct_num": _number(row["expected_uplift_pct"],
                                          "dim_campaign.expected_uplift_pct", default=0.0),
                "priority_int": _integer(row["priority"], "dim_campaign.priority", optional=True)
                                or 0,
            }
            if row["campaign_type"] not in valid_types or row["scope_type"] not in valid_scopes:
                raise ValueError(f"Unsupported campaign type/scope: {row}")
            if campaign["end_date_dt"] < campaign["start_date_dt"]:
                raise ValueError(f"Campaign ends before it starts: {row['campaign_id']}")
            if campaign["discount_value_num"] < 0 or campaign["uplift_pct_num"] < 0:
                raise ValueError(f"Campaign discount/uplift cannot be negative: {row['campaign_id']}")
            result.append(campaign)
        _assert_unique((r["campaign_id_int"] for r in result), "dim_campaign.campaign_id")
        return result

    def _load_campaign_product_scope(self) -> dict[int, list[dict[str, str]]]:
        rows = self.rows["dim_campaign_product_scope.csv"]
        if rows:
            _columns(rows, "dim_campaign_product_scope.csv",
                     ("campaign_id", "category_id", "product_id"))
        result: dict[int, list[dict[str, str]]] = defaultdict(list)
        campaign_ids = {campaign["campaign_id_int"] for campaign in self.campaigns}
        category_ids = {
            category["category_id"]
            for category in self.rows["dim_product_category.csv"]
        }
        for row in rows:
            campaign_id = _integer(row["campaign_id"], "dim_campaign_product_scope.campaign_id")
            if campaign_id not in campaign_ids:
                raise ValueError(f"Campaign scope references unknown campaign {campaign_id}")
            product_id = _text(row.get("product_id"))
            category_id = _text(row.get("category_id"))
            if product_id and product_id not in self.products:
                raise ValueError(f"Campaign scope references unknown product {product_id}")
            if category_id and category_id not in category_ids:
                raise ValueError(f"Campaign scope references unknown category {category_id}")
            result[campaign_id].append({
                "product_id": product_id,
                "category_id": category_id,
            })
        return dict(result)

    def _load_date_coverage(self) -> dict[date, int]:
        rows = self.rows["dim_date.csv"]
        _columns(rows, "dim_date.csv", ("date_key", "full_date"))
        date_keys = {}
        for row in rows:
            full_date = _date(row["full_date"], "dim_date.full_date")
            date_key = _integer(row["date_key"], "dim_date.date_key")
            if full_date in date_keys or date_key in date_keys.values():
                raise ValueError("dim_date contains duplicate date or date_key")
            date_keys[full_date] = date_key
        if DATA_SIM_START not in date_keys or DATA_SIM_END not in date_keys:
            raise ValueError("dim_date does not cover the full Sale/Orders simulation window")
        return date_keys

    def _preflight(self) -> None:
        if not self.stores:
            raise ValueError("dim_store contains no stores")
        if "POS" not in {row["channel_name"] for row in self.channels}:
            raise ValueError("dim_sales_channel must contain POS")
        expected_groups = {
            "POS": "dine_in",
            "App": "app",
            **{name: "delivery" for name in DELIVERY_PLATFORM_WEIGHTS},
        }
        actual_groups = {row["channel_name"]: row["channel_group"] for row in self.channels}
        if actual_groups != expected_groups:
            raise ValueError(
                f"dim_sales_channel must match configured channel groups: {expected_groups}"
            )
        channel_ids = {channel["channel_id_int"] for channel in self.channels}
        category_ids = {row["category_id"] for row in self.rows["dim_product_category.csv"]}
        for variant in self.variants:
            if variant["category_id"] not in category_ids:
                raise ValueError(f"Variant has unknown category: {variant['variant_id']}")
        for store_id, store in self.stores.items():
            if store_id not in self.hours or set(self.hours[store_id]) != set(range(1, 8)):
                raise ValueError(f"Store {store_id} must have seven operating-hours rows")
            mix = [
                _number(store[key], f"dim_store.{key}")
                for key in ("channel_mix_dine_in", "channel_mix_app", "channel_mix_delivery")
            ]
            if any(weight < 0 for weight in mix) or abs(sum(mix) - 1.0) > 0.003:
                raise ValueError(f"Store {store_id} channel mix must sum to 1: {mix}")
        for campaign in self.campaigns:
            if campaign["scope_type"] == "store":
                if campaign["scope_store_id_int"] not in self.stores:
                    raise ValueError(f"Campaign has unknown scope_store_id: {campaign}")
            if campaign["scope_type"] == "channel":
                if campaign["scope_channel_id_int"] not in channel_ids:
                    raise ValueError(f"Campaign has unknown scope_channel_id: {campaign}")
        for store_id, store in self.stores.items():
            for day in self._active_days_for_store(store):
                if not self.has_active_employee(store_id, day):
                    raise ValueError(
                        f"Store {store_id} is open on {day} without an active employee"
                    )

    @staticmethod
    def _active_days_for_store(store: dict[str, Any]) -> Iterable[date]:
        current = max(DATA_SIM_START, store["open_date"])
        end = DATA_SIM_END
        closed = store.get("closed_date")
        if closed:
            end = min(end, closed - timedelta(days=1))
        while current <= end:
            if _is_store_open(store, current):
                yield current
            current += timedelta(days=1)

    def has_active_employee(self, store_id: int, day: date) -> bool:
        return any(
            hired <= day and (terminated is None or day <= terminated)
            for hired, terminated in self.staff_intervals.get(store_id, [])
        )

    def variants_by_category(self, day: date) -> dict[str, list[dict[str, Any]]]:
        cached = self._variant_cache.get(day)
        if cached is not None:
            return cached
        result: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for variant in self.variants:
            product = self.products[variant["product_id"]]
            if variant["effective_from_dt"] > day:
                continue
            if variant["effective_to_dt"] and day > variant["effective_to_dt"]:
                continue
            if product["launch_date_dt"] and day < product["launch_date_dt"]:
                continue
            if product["discontinued_date_dt"] and day > product["discontinued_date_dt"]:
                continue
            result[variant["category_id"]].append(variant)
        self._variant_cache[day] = dict(result)
        return self._variant_cache[day]

    def active_campaigns(
        self, store_id: int, channel_id: int, day: date
    ) -> list[dict[str, Any]]:
        key = (day, store_id, channel_id)
        if key not in self._campaign_cache:
            active = []
            for campaign in self.campaigns:
                if campaign["start_date_dt"] > day or campaign["end_date_dt"] < day:
                    continue
                scope = campaign["scope_type"]
                if scope == "store" and campaign["scope_store_id_int"] != store_id:
                    continue
                if scope == "channel" and campaign["scope_channel_id_int"] != channel_id:
                    continue
                active.append(campaign)
            active.sort(key=lambda row: (-row["priority_int"], row["campaign_id_int"]))
            self._campaign_cache[key] = active
        return self._campaign_cache[key]

    def campaign_items(
        self, campaign: dict[str, Any], items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        scopes = self.campaign_product_scope.get(campaign["campaign_id_int"])
        if not scopes:
            return items
        return [
            item for item in items
            if any(
                (not scope["product_id"] or scope["product_id"] == item["product_id"])
                and (not scope["category_id"] or scope["category_id"] == item["category_id"])
                for scope in scopes
            )
        ]

    def fingerprint(self) -> tuple[str, dict[str, str]]:
        checksums = {
            name: _file_sha256(DIM_DIR / name)
            for name in INPUT_FILES
        }
        relevant_code = [
            Path(__file__),
            PROJECT_ROOT / "src" / "utils" / "constants.py",
            PROJECT_ROOT / "src" / "utils" / "date_utils.py",
            PROJECT_ROOT / "src" / "utils" / "seed_utils.py",
            PROJECT_ROOT / "src" / "utils" / "store_utils.py",
            PROJECT_ROOT / "data_warehouse" / "schema" / "create_schema.sql",
        ]
        for path in relevant_code:
            checksums[str(path.relative_to(PROJECT_ROOT))] = _file_sha256(path)
        signature = hashlib.sha256(
            json.dumps(
                {
                    "checksums": checksums,
                    "simulation_start": DATA_SIM_START.isoformat(),
                    "simulation_end": DATA_SIM_END.isoformat(),
                    "seed_version": 1,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return signature, checksums


def _is_store_open(store: dict[str, Any], day: date) -> bool:
    if day < store["open_date"]:
        return False
    closed = store.get("closed_date")
    if closed and day >= closed:
        return False
    temp_start = store.get("temp_close_start_dt")
    temp_end = store.get("temp_close_end_dt")
    if temp_start and temp_end and temp_start <= day <= temp_end:
        return False
    return True


def _price(variant: dict[str, Any], day: date) -> int:
    factor = PRICE_FACTOR.get(day.year, 1.0)
    return max(5_000, int((variant["base_price_int"] * factor + 500) // 1_000) * 1_000)


def _item_count_distribution(aov_multiplier: float) -> tuple[list[int], list[float]]:
    counts, base_weights = zip(*ITEMS_PER_ORDER)
    base_mean = sum(count * weight for count, weight in ITEMS_PER_ORDER) / sum(base_weights)
    target_mean = min(max(counts), base_mean * aov_multiplier)
    if target_mean <= base_mean:
        return list(counts), list(base_weights)
    low, high = 0.0, 8.0
    for _ in range(40):
        exponent = (low + high) / 2
        weights = [weight * (count ** exponent) for count, weight in ITEMS_PER_ORDER]
        mean = sum(count * weight for count, weight in zip(counts, weights)) / sum(weights)
        if mean < target_mean:
            low = exponent
        else:
            high = exponent
    exponent = (low + high) / 2
    return list(counts), [
        weight * (count ** exponent)
        for count, weight in ITEMS_PER_ORDER
    ]


def _estimated_aov(
    variants_by_category: dict[str, list[dict[str, Any]]],
    year: int,
    aov_multiplier: float,
) -> float:
    category_weights = CATEGORY_MIX["dine_in"]
    category_total = 0.0
    total_weight = 0.0
    for category_id, weight in category_weights.items():
        variants = variants_by_category.get(category_id, [])
        if not variants:
            continue
        category_total += weight * sum(_price(row, date(year, 7, 1)) for row in variants) / len(variants)
        total_weight += weight
    if total_weight == 0:
        raise ValueError("No saleable variants are available for AOV estimation")
    counts, weights = _item_count_distribution(aov_multiplier)
    average_items = sum(count * weight for count, weight in zip(counts, weights)) / sum(weights)
    return max(30_000.0, category_total / total_weight * average_items)


def _channel_weights(
    store: dict[str, Any],
    channels: list[dict[str, Any]],
    day: date,
) -> list[tuple[dict[str, Any], float]]:
    active = [row for row in channels if row["launch_date_dt"] <= day]
    active_names = {row["channel_name"] for row in active}
    pos = float(store["channel_mix_dine_in"])
    app = float(store["channel_mix_app"])
    delivery = float(store["channel_mix_delivery"])
    if "App" not in active_names:
        pos += app
        app = 0.0
    delivery_channels = [
        row for row in active
        if row["channel_group"] == "delivery"
    ]
    if not delivery_channels:
        pos += delivery
        delivery = 0.0
    platform_total = sum(
        DELIVERY_PLATFORM_WEIGHTS.get(row["channel_name"], 0.0)
        for row in delivery_channels
    )
    weighted = []
    for channel in active:
        name = channel["channel_name"]
        if name == "POS":
            weight = pos
        elif name == "App":
            weight = app
        elif channel["channel_group"] == "delivery" and delivery > 0:
            platform_share = DELIVERY_PLATFORM_WEIGHTS.get(name, 0.0)
            weight = delivery * platform_share / platform_total if platform_total else 0.0
        else:
            weight = 0.0
        if weight > 0:
            weighted.append((channel, weight))
    total = sum(weight for _, weight in weighted)
    if total <= 0:
        raise ValueError(f"No active sales channel for order date {day}")
    return [(channel, weight / total) for channel, weight in weighted]


def _allocate_channel_counts(
    total: int,
    channels: list[tuple[dict[str, Any], float]],
) -> list[tuple[dict[str, Any], int]]:
    raw = [(channel, total * weight) for channel, weight in channels]
    allocated = [(channel, math.floor(value)) for channel, value in raw]
    remainder = total - sum(value for _, value in allocated)
    ranking = sorted(
        range(len(raw)),
        key=lambda index: (-(raw[index][1] - allocated[index][1]),
                           raw[index][0]["channel_id_int"]),
    )
    for index in ranking[:remainder]:
        channel, value = allocated[index]
        allocated[index] = (channel, value + 1)
    return allocated


def _order_type(channel: dict[str, Any], store: dict[str, Any], rng: random.Random) -> str:
    name = channel["channel_name"]
    if channel["channel_group"] == "delivery" and name != "App":
        return "delivery"
    if name == "POS":
        dine_in = 0.75 + (0.05 if store["location_tier"] == "prime" else -0.04)
        dine_in = min(0.9, max(0.6, dine_in + rng.uniform(-0.03, 0.03)))
        return rng.choices(("dine_in", "takeaway"), (dine_in, 1 - dine_in), k=1)[0]
    if name == "App":
        return rng.choices(("takeaway", "delivery"), (0.8, 0.2), k=1)[0]
    raise ValueError(f"Unsupported channel for order type: {name}")


def _pick_customer(
    channel_name: str,
    store_id: int,
    day: date,
    customers: dict[str, dict[int | None, tuple[list[date], list[int]]]],
    rng: random.Random,
) -> int | None:
    if channel_name in DELIVERY_PLATFORM_WEIGHTS:
        return None
    if channel_name == "App":
        groups = ("app",)
        local_preference = 0.6
    elif channel_name == "POS":
        if rng.random() >= pos_customer_rate(day.year, day.month):
            return None
        groups = ("pos", "app")
        local_preference = 0.7
    else:
        raise ValueError(f"Unsupported customer policy for channel {channel_name}")

    for group in groups:
        pools = customers.get(group, {})
        all_dates, all_ids = pools.get(None, ([], []))
        all_count = bisect.bisect_right(all_dates, day)
        if not all_count:
            continue
        if rng.random() < local_preference:
            local_dates, local_ids = pools.get(store_id, ([], []))
            local_count = bisect.bisect_right(local_dates, day)
            if local_count:
                return local_ids[rng.randrange(local_count)]
        return all_ids[rng.randrange(all_count)]
    if channel_name == "App":
        raise ValueError(f"No App-registered customer is available on {day}")
    return None


def _seasonal_category_weights(
    order_type: str, day: date, variants_by_category: dict[str, list[dict[str, Any]]]
) -> tuple[list[str], list[float]]:
    base = CATEGORY_MIX.get(order_type, CATEGORY_MIX["dine_in"])
    adjusted = dict(base)
    if day.month in {4, 5, 6, 7, 8}:
        if "CAT-02" in adjusted:
            adjusted["CAT-02"] *= 1.10
        if "CAT-03" in adjusted:
            adjusted["CAT-03"] *= 1.25
    available = [
        category for category in adjusted
        if variants_by_category.get(category)
    ]
    weights = [adjusted[category] for category in available]
    if not available or sum(weights) <= 0:
        raise ValueError(f"No available product category for {day} / {order_type}")
    return available, weights


def _generate_items(
    order_id: int,
    day: date,
    order_type: str,
    variants_by_category: dict[str, list[dict[str, Any]]],
    modifiers: dict[str, list[dict[str, Any]]],
    exclusions: dict[str, set[str]],
    item_count_distribution: tuple[list[int], list[float]],
    rng: random.Random,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    categories, category_weights = _seasonal_category_weights(
        order_type, day, variants_by_category
    )
    item_counts, item_weights = item_count_distribution
    item_count = rng.choices(item_counts, weights=item_weights, k=1)[0]
    items: list[dict[str, Any]] = []
    modifier_rows: list[dict[str, Any]] = []
    gross = 0

    for item_seq in range(1, item_count + 1):
        category_id = rng.choices(categories, weights=category_weights, k=1)[0]
        variant = rng.choice(variants_by_category[category_id])
        quantity = 1 if rng.random() < 0.95 else 2
        unit_price = _price(variant, day)
        line_amount = unit_price * quantity
        item = {
            "order_id": order_id,
            "item_seq": item_seq,
            "variant_id": variant["variant_id"],
            "product_id": variant["product_id"],
            "category_id": category_id,
            "quantity": quantity,
            "unit_price_vnd": unit_price,
            "line_amount_vnd": line_amount,
        }
        items.append(item)
        gross += line_amount

        if category_id in {"CAT-05", "CAT-06", "CAT-07"}:
            continue
        excluded = exclusions.get(category_id, set())
        selected_modifiers = []
        topping_options = modifiers.get("topping", [])
        if "topping" not in excluded and topping_options:
            topping_count = rng.choices((0, 1, 2, 3), (0.70, 0.20, 0.08, 0.02), k=1)[0]
            selected_modifiers.extend(rng.sample(topping_options, min(topping_count, len(topping_options))))
        for group, probability in (("sweetness", 0.70), ("ice", 0.80)):
            if group in excluded or (category_id == "CAT-03" and group == "ice"):
                continue
            group_options = modifiers.get(group, [])
            if group_options and rng.random() < probability:
                selected_modifiers.append(rng.choice(group_options))
        for modifier in selected_modifiers:
            modifier_rows.append({
                "order_id": order_id,
                "item_seq": item_seq,
                "modifier_id": modifier["modifier_id_int"],
                "modifier_name": modifier["modifier_name"],
                "modifier_group": modifier["modifier_group"],
                "extra_price_vnd": modifier["extra_price_int"],
            })
            gross += modifier["extra_price_int"] * quantity

    return items, modifier_rows, gross


def _eligible_items(
    campaign_items: list[dict[str, Any]],
    modifiers: list[dict[str, Any]],
    item_quantities: dict[int, int],
) -> tuple[list[dict[str, Any]], int]:
    eligible_seq = {item["item_seq"] for item in campaign_items}
    modifier_totals: Counter[int] = Counter()
    for modifier in modifiers:
        if modifier["item_seq"] in eligible_seq:
            modifier_totals[modifier["item_seq"]] += (
                modifier["extra_price_vnd"] * item_quantities[modifier["item_seq"]]
            )
    eligible_gross = sum(
        item["line_amount_vnd"] + modifier_totals[item["item_seq"]]
        for item in campaign_items
    )
    return campaign_items, eligible_gross


def _campaign_discount(
    campaigns: list[dict[str, Any]],
    day: date,
    order_hour: int,
    double_day: bool,
    items: list[dict[str, Any]],
    modifiers: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, int]:
    item_quantities = {item["item_seq"]: item["quantity"] for item in items}
    for campaign in campaigns:
        if (
            campaign["campaign_type"] == "flash_sale"
            and not double_day
            and not (14 <= order_hour < 16)
        ):
            continue
        selected = campaign.get("_eligible_items", items)
        if not selected:
            continue
        _, eligible_gross = _eligible_items(selected, modifiers, item_quantities)
        kind = campaign["campaign_type"]
        if kind == "bogo":
            eligible_units = [
                item["unit_price_vnd"]
                for item in selected
                for _ in range(item["quantity"])
            ]
            if len(eligible_units) < 2:
                continue
            discount = min(eligible_units)
        else:
            discount = int(round(eligible_gross * campaign["discount_value_num"] / 100))
        discount = min(max(discount, 0), eligible_gross)
        if discount:
            return campaign, discount
    return None, 0


def _payment(
    order_id: int,
    channel_name: str,
    status: str,
    net_amount: int,
    order_datetime: str,
    rng: random.Random,
) -> dict[str, Any]:
    distribution = PAYMENT_DIST.get(channel_name)
    if distribution is None:
        raise ValueError(f"No payment distribution configured for {channel_name}")
    methods, weights = zip(*distribution.items())
    method = rng.choices(methods, weights=weights, k=1)[0]
    if status == "canceled":
        payment_status = "failed"
        payment_amount = 0
        surcharge = 0
    else:
        payment_status = "completed"
        payment_amount = net_amount
        surcharge = int(round(net_amount * PAYMENT_SURCHARGE.get(method, 0.0)))
    return {
        "order_id": order_id,
        "payment_method": method,
        "payment_status": payment_status,
        "payment_amount_vnd": payment_amount,
        "payment_surcharge_vnd": surcharge,
        "payment_datetime": order_datetime,
    }


def _campaign_volume_driver(
    campaigns: list[dict[str, Any]], day: date
) -> dict[str, Any] | None:
    for campaign in campaigns:
        if campaign["uplift_pct_num"] <= 0:
            continue
        if campaign["campaign_type"] == "flash_sale" and not is_double_day(day):
            return campaign
        return campaign
    return None


def _weighted_seconds(open_time: str, close_time: str, channel_name: str) -> float:
    start = time.fromisoformat(open_time)
    end = time.fromisoformat(close_time)
    start_second = start.hour * 3600 + start.minute * 60 + start.second
    end_second = end.hour * 3600 + end.minute * 60 + end.second
    total = 0.0
    for hour in range(start_second // 3600, (end_second - 1) // 3600 + 1):
        segment_start = max(start_second, hour * 3600)
        segment_end = min(end_second, (hour + 1) * 3600)
        if 7 <= hour <= 9:
            weight = 3.0
        elif 11 <= hour <= 13:
            weight = 2.5
        elif 14 <= hour <= 16:
            weight = 2.0
        elif 17 <= hour <= 20:
            weight = 2.5
        else:
            weight = 1.0
        if channel_name in DELIVERY_PLATFORM_WEIGHTS and hour >= 18:
            weight *= 1.5
        total += weight * (segment_end - segment_start)
    return total


def _flash_windows(
    open_time: str, close_time: str, day: date
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], float]:
    if is_double_day(day):
        return [(open_time, close_time)], [], 1.0
    open_seconds = time.fromisoformat(open_time)
    close_seconds = time.fromisoformat(close_time)
    open_value = open_seconds.hour * 3600 + open_seconds.minute * 60 + open_seconds.second
    close_value = close_seconds.hour * 3600 + close_seconds.minute * 60 + close_seconds.second
    flash_start = max(open_value, 14 * 3600)
    flash_end = min(close_value, 16 * 3600)
    if flash_end <= flash_start:
        return [], [(open_time, close_time)], 0.0
    fmt = lambda seconds: (datetime.min + timedelta(seconds=seconds)).strftime("%H:%M:%S")
    flash = [(fmt(flash_start), fmt(flash_end))]
    regular = []
    if open_value < flash_start:
        regular.append((fmt(open_value), fmt(flash_start)))
    if flash_end < close_value:
        regular.append((fmt(flash_end), fmt(close_value)))
    total = _weighted_seconds(open_time, close_time, "")
    flash_weight = _weighted_seconds(flash[0][0], flash[0][1], "")
    return flash, regular, flash_weight / total if total else 0.0


def _order_id(year: int, month: int, store_id: int, sequence: int) -> int:
    if sequence > 999_999:
        raise ValueError(f"Store-month sequence overflow: {year}-{month:02d} store {store_id}")
    return year * 10**10 + month * 10**8 + store_id * 10**6 + sequence


def _make_order(
    dimensions: SaleOrderDimensions,
    store: dict[str, Any],
    channel: dict[str, Any],
    day: date,
    open_time: str,
    close_time: str,
    rng: random.Random,
    sequence: int,
    time_windows: list[tuple[str, str]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]],
           dict[str, Any], dict[str, Any] | None]:
    store_id = store["store_id"]
    channel_id = channel["channel_id_int"]
    channel_name = channel["channel_name"]
    order_id = _order_id(day.year, day.month, store_id, sequence)
    order_type = _order_type(channel, store, rng)
    order_time = pick_order_time(
        open_time, close_time, channel_name, rng, allowed_windows=time_windows
    )
    order_datetime = f"{day.isoformat()} {order_time}"
    customer_id = _pick_customer(
        channel_name, store_id, day, dimensions.customer_pools, rng
    )
    status = rng.choices(
        [value for value, _ in STATUS_WEIGHTS],
        weights=[weight for _, weight in STATUS_WEIGHTS],
        k=1,
    )[0]

    if status == "canceled":
        gross = discount = net = 0
        items: list[dict[str, Any]] = []
        modifier_rows: list[dict[str, Any]] = []
        campaign_row = None
    else:
        variants_by_category = dimensions.variants_by_category(day)
        aov_multiplier = OUTLIER_STORE_AOV_MULTIPLIER.get(store_id, 1.0)
        items, modifier_rows, gross = _generate_items(
            order_id,
            day,
            order_type,
            variants_by_category,
            dimensions.modifiers,
            dimensions.exclusions,
            _item_count_distribution(aov_multiplier),
            rng,
        )
        candidates = [
            {
                **candidate,
                "_eligible_items": dimensions.campaign_items(candidate, items),
            }
            for candidate in dimensions.active_campaigns(store_id, channel_id, day)
        ]
        campaign_row, discount = _campaign_discount(
            candidates,
            day,
            int(order_time[:2]),
            is_double_day(day),
            items,
            modifier_rows,
        )
        net = max(0, gross - discount)

    order_row = {
        "order_id": order_id,
        "store_id": store_id,
        "customer_id": customer_id,
        "channel_id": channel_id,
        "date_key": dimensions.date_coverage[day],
        "order_datetime": order_datetime,
        "order_type": order_type,
        "order_status": status,
        "gross_amount_vnd": gross,
        "discount_amount_vnd": discount,
        "net_amount_vnd": net,
    }
    payment_row = _payment(
        order_id, channel_name, status, net, order_datetime, rng
    )
    discount_row = None
    if campaign_row is not None and discount > 0:
        discount_row = {
            "order_id": order_id,
            "campaign_id": campaign_row["campaign_id_int"],
            "discount_amount_vnd": discount,
            "campaign_type": campaign_row["campaign_type"],
        }
    return order_row, items, modifier_rows, payment_row, discount_row


def _validate_batch(results: dict[str, list[dict[str, Any]]]) -> None:
    orders = results["fact_order"]
    order_by_id = {row["order_id"]: row for row in orders}
    if len(order_by_id) != len(orders):
        raise ValueError("Duplicate order_id within generated batch")
    item_by_key = {}
    item_totals: Counter[int] = Counter()
    item_quantities: dict[tuple[int, int], int] = {}
    modifier_totals: Counter[int] = Counter()
    topping_counts: Counter[tuple[int, int]] = Counter()
    modifier_keys = set()
    discounts: dict[int, int] = {}
    payments: dict[int, dict[str, Any]] = {}

    for row in results["fact_order_item"]:
        key = (row["order_id"], row["item_seq"])
        if key in item_by_key or row["order_id"] not in order_by_id:
            raise ValueError(f"Duplicate/orphan fact_order_item key: {key}")
        if row["quantity"] < 1 or row["unit_price_vnd"] <= 0:
            raise ValueError(f"Invalid order-item quantity/price: {key}")
        if row["line_amount_vnd"] != row["quantity"] * row["unit_price_vnd"]:
            raise ValueError(f"Line amount does not reconcile for {key}")
        item_by_key[key] = row
        item_quantities[key] = row["quantity"]
        item_totals[row["order_id"]] += row["line_amount_vnd"]

    for row in results["fact_order_item_modifier"]:
        key = (row["order_id"], row["item_seq"])
        modifier_key = (*key, row["modifier_id"])
        if key not in item_by_key or modifier_key in modifier_keys:
            raise ValueError(f"Duplicate/orphan modifier key: {modifier_key}")
        modifier_keys.add(modifier_key)
        modifier_totals[row["order_id"]] += (
            row["extra_price_vnd"] * item_quantities[key]
        )
        if row["modifier_group"] == "topping":
            topping_counts[key] += 1
            if topping_counts[key] > 3:
                raise ValueError(f"More than three toppings on item: {key}")

    for row in results["fact_payment"]:
        if row["order_id"] not in order_by_id or row["order_id"] in payments:
            raise ValueError(f"Duplicate/orphan payment for order {row['order_id']}")
        payments[row["order_id"]] = row

    for row in results["fact_order_discount"]:
        if row["order_id"] not in order_by_id or row["order_id"] in discounts:
            raise ValueError(f"Duplicate/orphan discount for order {row['order_id']}")
        discounts[row["order_id"]] = row["discount_amount_vnd"]

    if set(payments) != set(order_by_id):
        raise ValueError("Every order must have exactly one payment record")
    for order_id, order in order_by_id.items():
        status = order["order_status"]
        payment = payments[order_id]
        if status == "canceled":
            if item_totals[order_id] or modifier_totals[order_id] or discounts.get(order_id, 0):
                raise ValueError(f"Canceled order {order_id} must be header-only")
            if any(order[field] != 0 for field in (
                "gross_amount_vnd", "discount_amount_vnd", "net_amount_vnd"
            )):
                raise ValueError(f"Canceled order {order_id} must have zero amounts")
            if payment["payment_status"] != "failed" or payment["payment_amount_vnd"] != 0:
                raise ValueError(f"Canceled order {order_id} must have failed zero payment")
        else:
            gross = item_totals[order_id] + modifier_totals[order_id]
            if order["gross_amount_vnd"] != gross:
                raise ValueError(f"Gross does not reconcile with item facts: {order_id}")
            if order["net_amount_vnd"] != gross - order["discount_amount_vnd"]:
                raise ValueError(f"Net does not reconcile for order {order_id}")
            if discounts.get(order_id, 0) != order["discount_amount_vnd"]:
                raise ValueError(f"Discount fact does not reconcile for order {order_id}")
            if payment["payment_status"] != "completed":
                raise ValueError(f"Sale/refund original payment must be completed: {order_id}")
            if payment["payment_amount_vnd"] != order["net_amount_vnd"]:
                raise ValueError(f"Payment amount does not reconcile: {order_id}")


def _generate_store_month(
    dimensions: SaleOrderDimensions,
    store: dict[str, Any],
    year: int,
    month: int,
    max_orders: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(get_seed(store["store_id"], year, month))
    first_day = date(year, month, 1)
    days = daily_weights_for_month(year, month)
    active_days = [
        (day, weight)
        for day, weight in days.items()
        if _is_store_open(store, day)
    ]
    if not active_days:
        return {table: [] for table in TABLES}
    for day, _ in active_days:
        if not dimensions.has_active_employee(store["store_id"], day):
            raise ValueError(f"Store {store['store_id']} has no active employee on {day}")
        if day not in dimensions.date_coverage:
            raise ValueError(f"dim_date has no row for order date {day}")

    maturity = store_maturity_factor(store, year, month, rng)
    revenue_target = get_monthly_revenue_target(
        store, year, month, rng, maturity_m=maturity
    )
    revenue_target *= MONTHLY_SEASONALITY[month]
    aov_multiplier = OUTLIER_STORE_AOV_MULTIPLIER.get(store["store_id"], 1.0)
    reference_variants = dimensions.variants_by_category(date(year, month, 15))
    estimated_aov = _estimated_aov(reference_variants, year, aov_multiplier)
    expected_completed_orders = max(1, round(revenue_target / estimated_aov))
    expected_attempts = round(expected_completed_orders / STATUS_WEIGHTS[0][1])
    total_active_weight = sum(weight for _, weight in active_days)
    operating_hours = dimensions.hours[store["store_id"]]
    results = {table: [] for table in TABLES}
    sequence = 0

    for day, day_weight in active_days:
        base_daily_orders = max(
            0,
            round(expected_attempts * day_weight / total_active_weight
                  * rng.uniform(0.92, 1.08)),
        )
        channels = _channel_weights(store, dimensions.channels, day)
        daily_candidates = []
        for channel, count in _allocate_channel_counts(base_daily_orders, channels):
            if count <= 0:
                continue
            campaign_candidates = dimensions.active_campaigns(
                store["store_id"], channel["channel_id_int"], day
            )
            driver = _campaign_volume_driver(campaign_candidates, day)
            open_time, close_time = operating_hours[day.isoweekday()]
            if driver and driver["campaign_type"] == "flash_sale" and not is_double_day(day):
                flash_windows, regular_windows, fraction = _flash_windows(
                    open_time, close_time, day
                )
                flash_base = round(count * fraction)
                regular_count = count - flash_base
                uplifted_flash = round(
                    flash_base * (1 + driver["uplift_pct_num"] / 100)
                )
                if regular_count and regular_windows:
                    daily_candidates.append(
                        (channel, regular_count, regular_windows)
                    )
                if uplifted_flash and flash_windows:
                    daily_candidates.append((channel, uplifted_flash, flash_windows))
            else:
                uplift = driver["uplift_pct_num"] if driver else 0.0
                uplifted = round(count * (1 + uplift / 100))
                if uplifted:
                    daily_candidates.append(
                        (channel, uplifted, [(open_time, close_time)])
                    )

        stop_batch = False
        for channel, count, time_windows in daily_candidates:
            for _ in range(count):
                if max_orders is not None and len(results["fact_order"]) >= max_orders:
                    stop_batch = True
                    break
                sequence += 1
                order, items, modifier_rows, payment, discount = _make_order(
                    dimensions,
                    store,
                    channel,
                    day,
                    operating_hours[day.isoweekday()][0],
                    operating_hours[day.isoweekday()][1],
                    rng,
                    sequence,
                    time_windows,
                )
                results["fact_order"].append(order)
                results["fact_order_item"].extend(
                    {key: value for key, value in item.items()
                     if key in TABLE_COLUMNS["fact_order_item"]}
                    for item in items
                )
                results["fact_order_item_modifier"].extend(modifier_rows)
                results["fact_payment"].append(payment)
                if discount:
                    results["fact_order_discount"].append(discount)
            if stop_batch:
                break
        if stop_batch:
            break

    _validate_batch(results)
    return results


def _batch_path(output_dir: Path, table: str, year: int, month: int, store_id: int) -> Path:
    return (
        output_dir / "full" / table / str(year)
        / f"{table}_{year}_{month:02d}_S{store_id:02d}.csv"
    )


def _batch_marker_path(output_dir: Path, year: int, month: int, store_id: int) -> Path:
    return (
        output_dir / "full" / "_batch_manifests" / str(year)
        / f"batch_{year}_{month:02d}_S{store_id:02d}.json"
    )


def _atomic_csv(path: Path, rows: Iterable[dict[str, Any]], columns: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8-sig", newline="") as destination:
            writer = csv.DictWriter(
                destination, fieldnames=columns, extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise


def _save_batch(
    output_dir: Path,
    results: dict[str, list[dict[str, Any]]],
    year: int,
    month: int,
    store_id: int,
    fingerprint: str,
) -> None:
    marker = _batch_marker_path(output_dir, year, month, store_id)
    marker.unlink(missing_ok=True)
    files = {}
    for table in TABLES:
        path = _batch_path(output_dir, table, year, month, store_id)
        _atomic_csv(path, results[table], TABLE_COLUMNS[table])
        files[table] = {
            "rows": len(results[table]),
            "size_bytes": path.stat().st_size,
        }
    _write_manifest(marker, {
        "fingerprint": fingerprint,
        "year": year,
        "month": month,
        "store_id": store_id,
        "files": files,
    })


def _batch_complete(
    output_dir: Path, year: int, month: int, store_id: int, fingerprint: str
) -> bool:
    marker = _batch_marker_path(output_dir, year, month, store_id)
    if not marker.is_file():
        return False
    try:
        with marker.open("r", encoding="utf-8") as source:
            metadata = json.load(source)
    except (OSError, json.JSONDecodeError):
        return False
    if metadata.get("fingerprint") != fingerprint:
        return False
    files = metadata.get("files", {})
    for table in TABLES:
        path = _batch_path(output_dir, table, year, month, store_id)
        if not path.is_file():
            return False
        if path.stat().st_size != files.get(table, {}).get("size_bytes"):
            return False
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            header = next(csv.reader(source), [])
        if tuple(header) != TABLE_COLUMNS[table]:
            return False
    return True


def _iter_full_files(output_dir: Path, table: str) -> list[Path]:
    return sorted((output_dir / "full" / table).glob(f"**/{table}_*.csv"))


def _csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        next(reader, None)
        return sum(1 for _ in reader)


def _write_sample(output_dir: Path, sample_size: int = SAMPLE_SIZE) -> dict[str, int]:
    order_files = _iter_full_files(output_dir, "fact_order")
    if not order_files:
        raise FileNotFoundError(f"No full fact_order partitions found under {output_dir / 'full'}")
    reservoir: list[str] = []
    seen = 0
    rng = random.Random(SAMPLE_SEED)
    for path in order_files:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                order_id = row["order_id"]
                seen += 1
                if len(reservoir) < sample_size:
                    reservoir.append(order_id)
                else:
                    index = rng.randrange(seen)
                    if index < sample_size:
                        reservoir[index] = order_id
    selected = set(reservoir)
    if not selected:
        raise ValueError("Cannot create a sample from zero order rows")

    sample_counts = {}
    for table in TABLES:
        sample_path = output_dir / "sample" / f"{table}.csv"
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = sample_path.with_name(sample_path.name + ".tmp")
        row_count = 0
        try:
            with temporary.open("w", encoding="utf-8-sig", newline="") as destination:
                writer = csv.DictWriter(
                    destination, fieldnames=TABLE_COLUMNS[table],
                    extrasaction="raise", lineterminator="\n",
                )
                writer.writeheader()
                for path in _iter_full_files(output_dir, table):
                    with path.open("r", encoding="utf-8-sig", newline="") as source:
                        for row in csv.DictReader(source):
                            if row["order_id"] in selected:
                                writer.writerow(row)
                                row_count += 1
            os.replace(temporary, sample_path)
        except Exception:
            if temporary.exists():
                temporary.unlink()
            raise
        sample_counts[table] = row_count
    if sample_counts["fact_order"] != len(selected):
        raise ValueError("Sample order IDs are not unique across full partitions")
    return sample_counts


def _manifest_path(output_dir: Path) -> Path:
    return output_dir / "manifest.json"


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        json.dump(manifest, destination, ensure_ascii=False, indent=2, sort_keys=True)
        destination.write("\n")
    os.replace(temporary, path)


def _row_counts(output_dir: Path) -> dict[str, int]:
    return {
        table: sum(_csv_row_count(path) for path in _iter_full_files(output_dir, table))
        for table in TABLES
    }


def run(
    *,
    year_filter: int | None = None,
    month_filter: int | None = None,
    store_filter: list[int] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    force: bool = False,
    max_orders_per_batch: int | None = None,
    sample_only: bool = False,
    check_only: bool = False,
) -> dict[str, Any]:
    if month_filter is not None and year_filter is None:
        raise ValueError("--month requires --year")
    if max_orders_per_batch is not None and max_orders_per_batch < 1:
        raise ValueError("--max-orders-per-batch must be positive")
    output_dir = output_dir.resolve()
    dimensions = SaleOrderDimensions()
    fingerprint, checksums = dimensions.fingerprint()
    if check_only:
        LOG.info("Dimension preflight passed: %d stores, %d variants, %d campaigns",
                 len(dimensions.stores), len(dimensions.variants), len(dimensions.campaigns))
        return {"status": "preflight_passed", "fingerprint": fingerprint}

    selected_stores = sorted(dimensions.stores)
    if store_filter:
        unknown = set(store_filter) - set(selected_stores)
        if unknown:
            raise ValueError(f"Unknown store IDs: {sorted(unknown)}")
        selected_stores = [
            store_id for store_id in selected_stores if store_id in store_filter
        ]
    months = list(sim_months())
    if year_filter is not None:
        months = [ym for ym in months if ym[0] == year_filter]
    if month_filter is not None:
        months = [ym for ym in months if ym[1] == month_filter]
    if not months or not selected_stores:
        raise ValueError("No simulation month/store selected")

    full_scope = (
        year_filter is None
        and month_filter is None
        and store_filter is None
        and max_orders_per_batch is None
    )
    manifest_path = _manifest_path(output_dir)
    if not sample_only and manifest_path.exists() and not force:
        with manifest_path.open("r", encoding="utf-8") as source:
            previous = json.load(source)
        if previous.get("fingerprint") != fingerprint:
            raise ValueError(
                "Existing output was generated from a different code/schema/dimension "
                "snapshot. Use a new output directory or pass --force for a full-scope "
                "regeneration."
            )
    elif not sample_only and manifest_path.exists() and force:
        with manifest_path.open("r", encoding="utf-8") as source:
            previous = json.load(source)
        if previous.get("fingerprint") != fingerprint and not full_scope:
            raise ValueError(
                "Cannot force only part of an output generated from a different "
                "fingerprint; use a new output directory or force a full-scope run."
            )

    if sample_only:
        sample_counts = _write_sample(output_dir)
        result = {
            "status": "sample_written",
            "sample_order_count": sample_counts["fact_order"],
            "sample_row_counts": sample_counts,
        }
        LOG.info("Sample written: %s", sample_counts)
        return result

    manifest: dict[str, Any] = {
        "status": "running",
        "fingerprint": fingerprint,
        "source_dimension_dir": "data/dimension/full",
        "source_checksums_sha256": checksums,
        "simulation_start": DATA_SIM_START.isoformat(),
        "simulation_end": DATA_SIM_END.isoformat(),
        "seed_strategy": "store_id/year/month deterministic seed; sample reservoir seed 20261015",
        "sample_size_target": SAMPLE_SIZE,
        "sample_size_actual": 0,
        "full_scope_run": full_scope,
        "order_output_schema_source": "data_warehouse/schema/create_schema.sql",
        "tables": list(TABLES),
        "row_counts_full": {},
        "row_counts_sample": {},
        "batches_written": 0,
        "batches_skipped": 0,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "limitations": [
            "Refunds are full refunds represented by order_status=refunded; no refund event fields exist in the current schema.",
            "Inventory and purchase-order facts are not generated in this run.",
        ],
    }
    _write_manifest(manifest_path, manifest)

    candidate_batches = 0
    for year, month in months:
        for store_id in selected_stores:
            store = dimensions.stores[store_id]
            if not any(_is_store_open(store, day) for day in days_of_month(year, month)):
                continue
            candidate_batches += 1
            if not force and _batch_complete(output_dir, year, month, store_id, fingerprint):
                manifest["batches_skipped"] += 1
                continue
            batch = _generate_store_month(
                dimensions,
                store,
                year,
                month,
                max_orders=max_orders_per_batch,
            )
            _save_batch(output_dir, batch, year, month, store_id, fingerprint)
            manifest["batches_written"] += 1
            LOG.info(
                "%04d-%02d %s: orders=%s items=%s modifiers=%s payments=%s discounts=%s",
                year, month, store["store_code"],
                f"{len(batch['fact_order']):,}",
                f"{len(batch['fact_order_item']):,}",
                f"{len(batch['fact_order_item_modifier']):,}",
                f"{len(batch['fact_payment']):,}",
                f"{len(batch['fact_order_discount']):,}",
            )

    manifest["batches_in_scope"] = candidate_batches
    manifest["row_counts_full"] = _row_counts(output_dir)
    manifest["row_counts_sample"] = _write_sample(output_dir)
    manifest["sample_size_actual"] = manifest["row_counts_sample"]["fact_order"]
    manifest["status"] = "complete" if full_scope else "partial"
    _write_manifest(manifest_path, manifest)
    LOG.info("Sale/Orders generation %s. Full rows: %s; sample rows: %s",
             manifest["status"], manifest["row_counts_full"], manifest["row_counts_sample"])
    return manifest


def days_of_month(year: int, month: int) -> Iterable[date]:
    current = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    while current < end:
        yield current
        current += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate SQL-schema-aligned Sale/Orders fact CSVs"
    )
    parser.add_argument("--year", type=int, help="Restrict generation to one simulation year")
    parser.add_argument("--month", type=int, help="Restrict generation to one month; requires --year")
    parser.add_argument("--store", type=int, nargs="+", help="Restrict to store IDs")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Output root (default: data/synthetic/sale_orders)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite selected full partitions and regenerate the sample")
    parser.add_argument("--max-orders-per-batch", type=int,
                        help="Testing only: cap generated orders in each selected batch")
    parser.add_argument("--sample-only", action="store_true",
                        help="Rebuild the linked sample from existing full partitions")
    parser.add_argument("--check-only", action="store_true",
                        help="Validate dimensions/schema dependencies without writing output")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    run(
        year_filter=args.year,
        month_filter=args.month,
        store_filter=args.store,
        output_dir=args.output_dir,
        force=args.force,
        max_orders_per_batch=args.max_orders_per_batch,
        sample_only=args.sample_only,
        check_only=args.check_only,
    )


if __name__ == "__main__":
    main()
