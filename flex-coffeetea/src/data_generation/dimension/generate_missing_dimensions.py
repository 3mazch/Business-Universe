"""
Flex Coffee & Tea — Generate All Missing Dimensions (Phase 1)
=============================================================
Script này sinh toàn bộ dimension tables còn thiếu + rebuild những file
đã có nhưng cần cập nhật theo Implementation Plan v2.0:

  1.  dim_date            -- fix is_double_day, thêm cột, bỏ is_holiday cho Double Day
  2.  dim_product_category -- 7 categories (merge beverage + food/retail/merch)
  3.  dim_product          -- merged, string prefix ID (BVR/FOOD/RTL/MER)
  4.  dim_product_variant  -- merged, string prefix ID, bỏ cột thừa
  5.  dim_recipe           -- rebuild với variant_id mới
  6.  dim_category_modifier_exclusion -- formalize với category_id mới
  7.  dim_membership_tier  -- TIER-1/TIER-2/TIER-3
  8.  dim_reward_catalog   -- ~12 rewards
  9.  store_operating_hours -- 25 stores × 7 days
  10. store_lease          -- hợp đồng thuê + escalation
  11. dim_warehouse        -- 2 kho
  12. dim_supplier         -- full (central + local + outsource)
  13. dim_expense_category -- 4 loại
  14. dim_campaign_product_scope -- normalize từ dim_campaign.csv
  15. dim_customer         -- assign current_tier_id = TIER-1

Nguồn input:
  - data/raw/store_profiles_v1.csv
  - data/raw/dim_product_beverage.csv, dim_product_variant_beverage.csv
  - data/raw/dim_ingredient_beverage.csv, dim_recipe_beverage.csv
  - data/raw/dim_product_food_retail_merch.csv
  - data/raw/dim_customer.csv, dim_campaign.csv

Output: data/raw/ (overwrite hoặc tạo mới)
"""

import os
import random
from datetime import date, timedelta, datetime

import numpy as np
import pandas as pd

RNG_SEED = 42
random.seed(RNG_SEED)
np.random.seed(RNG_SEED)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
RAW_DIR = config.DIM_FULL_DIR
os.makedirs(RAW_DIR, exist_ok=True)

DATA_WINDOW_START = date(2020, 6, 1)   # ngày mở store đầu tiên
DATA_WINDOW_END   = date(2026, 7, 31)

MONTHS_VI = ["","Thang 1","Thang 2","Thang 3","Thang 4","Thang 5","Thang 6",
             "Thang 7","Thang 8","Thang 9","Thang 10","Thang 11","Thang 12"]
DAYS_VI   = ["","Thu 2","Thu 3","Thu 4","Thu 5","Thu 6","Thu 7","Chu Nhat"]


# ===========================================================================
# 1. DIM_DATE (rebuild — fix Double Day + thêm cột đủ theo schema v1.3)
# ===========================================================================
def generate_dim_date() -> pd.DataFrame:
    print("  [1] dim_date...")
    rows = []
    start = date(2020, 1, 1)
    end   = date(2026, 12, 31)

    # Tet holidays (approximate lunar calendar)
    tet_ranges = [
        ("2020-01-24", "2020-01-29"), ("2021-02-11", "2021-02-16"),
        ("2022-01-31", "2022-02-04"), ("2023-01-21", "2023-01-26"),
        ("2024-02-09", "2024-02-14"), ("2025-01-28", "2025-02-02"),
        ("2026-02-16", "2026-02-21"),
    ]
    tet_dates = set()
    for s, e in tet_ranges:
        d = date.fromisoformat(s)
        while d <= date.fromisoformat(e):
            tet_dates.add(d)
            d += timedelta(days=1)

    cur = start
    while cur <= end:
        dow = cur.isoweekday()  # 1=Mon, 7=Sun
        m, d, y = cur.month, cur.day, cur.year

        # National holidays
        is_holiday = 0
        holiday_name = ""
        if m == 1 and d == 1:
            is_holiday, holiday_name = 1, "New Year"
        elif m == 4 and d == 30:
            is_holiday, holiday_name = 1, "Reunification Day"
        elif m == 5 and d == 1:
            is_holiday, holiday_name = 1, "Labor Day"
        elif m == 9 and d == 2:
            is_holiday, holiday_name = 1, "National Day"
        elif cur in tet_dates:
            is_holiday, holiday_name = 1, "Tet Holiday"

        # Double Day (campaign flash sale từ 2025, KHÔNG phải national holiday)
        is_double_day = 1 if (y >= 2025 and m == d) else 0

        rows.append({
            "date_key":     int(cur.strftime("%Y%m%d")),
            "full_date":    cur.isoformat(),
            "day_of_week":  dow,
            "day_name":     DAYS_VI[dow],
            "month_num":    m,
            "month_name":   MONTHS_VI[m],
            "quarter_num":  (m - 1) // 3 + 1,
            "year_num":     y,
            "is_weekend":   1 if dow >= 6 else 0,
            "is_holiday":   is_holiday,
            "holiday_name": holiday_name,
            "is_double_day": is_double_day,
        })
        cur += timedelta(days=1)

    return pd.DataFrame(rows)


# ===========================================================================
# 2-6. PRODUCT DIMENSIONS (merge + string ID)
# ===========================================================================
def generate_product_dimensions():
    print("  [2-6] Product dimensions (merged, string IDs)...")

    # --- Load existing beverage data ---
    df_bev_prod    = pd.read_csv(os.path.join(config.DIM_TEMP_DIR, "dim_product_beverage.csv"))
    df_bev_variant = pd.read_csv(os.path.join(config.DIM_TEMP_DIR, "dim_product_variant_beverage.csv"))
    df_bev_recipe  = pd.read_csv(os.path.join(config.DIM_TEMP_DIR, "dim_recipe_beverage.csv"))
    df_food_flat   = pd.read_csv(os.path.join(config.DIM_TEMP_DIR, "dim_product_food_retail_merch.csv"))
    df_ingredient  = pd.read_csv(os.path.join(config.DIM_TEMP_DIR, "dim_ingredient_beverage.csv"))
    df_old_modifier= pd.read_csv(os.path.join(RAW_DIR, "dim_modifier.csv"))

    # ── 2a. dim_product_category (7 categories, VARCHAR ID) ──────────────────
    categories = [
        ("CAT-01", "Ca Phe"),
        ("CAT-02", "Tra"),
        ("CAT-03", "Da Xay"),
        ("CAT-04", "LTO"),
        ("CAT-05", "Food"),
        ("CAT-06", "Retail Dong Goi"),
        ("CAT-07", "Merchandise"),
    ]
    df_category = pd.DataFrame(categories, columns=["category_id", "category_name"])

    cat_name_to_id = dict(zip(df_category["category_name"], df_category["category_id"]))
    # Map từ tên category gốc trong beverage script → category_id mới
    cat_old_map = {
        "Ca Phe": "CAT-01", "Tra": "CAT-02", "Da Xay": "CAT-03", "LTO": "CAT-04",
        "Food - Banh lanh": "CAT-05", "Food - Banh nong": "CAT-05",
        "Retail": "CAT-06", "Merchandise": "CAT-07",
    }

    # ── 2b. dim_product (merged) ──────────────────────────────────────────────
    product_rows = []

    # Beverage products (39 products → BVR-001 ... BVR-039)
    for _, r in df_bev_prod.iterrows():
        old_pid = r["product_id"]  # 1-based int
        new_pid = f"BVR-{old_pid:03d}"
        cat_name = df_category.iloc[r["category_id"] - 1]["category_name"]  # category_id was 1-based
        product_rows.append({
            "product_id":        new_pid,
            "category_id":       f"CAT-{r['category_id']:02d}",
            "product_name":      r["product_name"],
            "description":       None,
            "launch_date":       r["launch_date"],
            "discontinued_date": r.get("discontinued_date", None),
            "status":            r["status"],
        })

    # Food / Retail / Merch products (24 SKUs — already have unique product_id 1000-1023)
    prefix_map = {
        "Food - Banh lanh": "FOOD", "Food - Banh nong": "FOOD",
        "Retail": "RTL", "Merchandise": "MER",
    }
    prefix_counter = {"FOOD": 1, "RTL": 1, "MER": 1}

    food_pid_map = {}   # old variant_id (int) -> new product_id (str)
    food_vid_map = {}   # old variant_id (int) -> new variant_id (str)

    seen_products = {}  # product_name -> new_product_id (dedup Food)
    for _, r in df_food_flat.iterrows():
        sub = r["sub_category"]
        prefix = prefix_map.get(sub, "FOOD")
        pname = r["product_name"]

        if pname not in seen_products:
            new_pid = f"{prefix}-{prefix_counter[prefix]:03d}"
            prefix_counter[prefix] += 1
            seen_products[pname] = new_pid
            cat_id = cat_old_map.get(sub, "CAT-05")
            product_rows.append({
                "product_id":        new_pid,
                "category_id":       cat_id,
                "product_name":      pname,
                "description":       None,
                "launch_date":       r.get("launch_date", "2021-01-01"),
                "discontinued_date": None,
                "status":            r.get("status", "active"),
            })

        new_pid = seen_products[pname]
        new_vid = new_pid  # no size → variant_id = product_id
        food_pid_map[r["variant_id"]] = new_pid
        food_vid_map[r["variant_id"]] = new_vid

    df_product = pd.DataFrame(product_rows)

    # ── 2c. dim_product_variant (merged) ─────────────────────────────────────
    variant_rows = []

    # Beverage variants (78 → BVR-001-M, BVR-001-L ...)
    bev_vid_map = {}  # old int variant_id → new str
    for _, r in df_bev_variant.iterrows():
        old_vid = r["variant_id"]
        old_pid = r["product_id"]
        new_pid = f"BVR-{old_pid:03d}"
        size = r["size_code"]
        new_vid = f"{new_pid}-{size}"
        bev_vid_map[old_vid] = new_vid
        variant_rows.append({
            "variant_id":      new_vid,
            "product_id":      new_pid,
            "size_code":       size,
            "sku":             r["sku"],
            "base_price_vnd":  r["base_price_vnd"],
            "cost_price_vnd":  None,   # calculated via recipe
            "sourcing_model":  "in_house_recipe",
            "effective_from":  r["effective_from"],
            "effective_to":    r.get("effective_to", None),
            "is_current":      r["is_current"],
        })

    # Food/Retail/Merch variants
    for _, r in df_food_flat.iterrows():
        old_vid = r["variant_id"]
        new_vid = food_vid_map[old_vid]
        new_pid = food_pid_map[old_vid]
        variant_rows.append({
            "variant_id":      new_vid,
            "product_id":      new_pid,
            "size_code":       None,
            "sku":             r["sku"],
            "base_price_vnd":  r["sell_price_vnd"],   # rename
            "cost_price_vnd":  r["cost_price_vnd"],
            "sourcing_model":  "outsource_finished_goods",
            "effective_from":  r.get("launch_date", "2021-01-01"),
            "effective_to":    None,
            "is_current":      1,
        })

    df_variant = pd.DataFrame(variant_rows).drop_duplicates(subset=["variant_id"])

    # ── 2d. dim_recipe (rebuild với variant_id mới) ──────────────────────────
    recipe_rows = []
    for _, r in df_bev_recipe.iterrows():
        old_vid = r["variant_id"]
        new_vid = bev_vid_map.get(old_vid)
        if new_vid is None:
            continue
        recipe_rows.append({
            "recipe_id":         r["recipe_id"],
            "variant_id":        new_vid,
            "ingredient_id":     r["ingredient_id"],
            "ingredient_name":   r.get("ingredient_name", ""),
            "quantity_per_unit": r["quantity_per_unit"],
        })
    df_recipe = pd.DataFrame(recipe_rows)

    # ── 2e. dim_category_modifier_exclusion (formalize) ──────────────────────
    excl_rows = [
        {"category_id": "CAT-03", "modifier_group": "ice",
         "reason": "Da xay da bao gom da san, khong dieu chinh muc da"},
    ]
    df_excl = pd.DataFrame(excl_rows)

    return df_category, df_product, df_variant, df_recipe, df_excl


# ===========================================================================
# 7. DIM_MEMBERSHIP_TIER
# ===========================================================================
def generate_membership_tier() -> pd.DataFrame:
    print("  [7] dim_membership_tier...")
    rows = [
        {"tier_id": "TIER-1", "tier_name": "Member", "min_spend_rolling_12m_vnd":        0, "tier_rank": 1},
        {"tier_id": "TIER-2", "tier_name": "Gold",   "min_spend_rolling_12m_vnd":  3_000_000, "tier_rank": 2},
        {"tier_id": "TIER-3", "tier_name": "VIP",    "min_spend_rolling_12m_vnd": 10_000_000, "tier_rank": 3},
    ]
    return pd.DataFrame(rows)


# ===========================================================================
# 8. DIM_REWARD_CATALOG
# ===========================================================================
def generate_reward_catalog() -> pd.DataFrame:
    print("  [8] dim_reward_catalog...")
    rows = [
        # voucher giam gia
        {"reward_id": 1, "reward_name": "Voucher giam 20k cho don tiep theo",  "points_required": 100, "reward_type": "voucher"},
        {"reward_id": 2, "reward_name": "Voucher giam 50k cho don tiep theo",  "points_required": 250, "reward_type": "voucher"},
        {"reward_id": 3, "reward_name": "Voucher giam 100k cho don tiep theo", "points_required": 500, "reward_type": "voucher"},
        # free product
        {"reward_id": 4, "reward_name": "1 ly Ca phe Den size M mien phi",     "points_required": 300, "reward_type": "free_product"},
        {"reward_id": 5, "reward_name": "1 ly Tra size M mien phi",            "points_required": 300, "reward_type": "free_product"},
        {"reward_id": 6, "reward_name": "1 ly do uong bat ky size M mien phi", "points_required": 400, "reward_type": "free_product"},
        {"reward_id": 7, "reward_name": "1 ly do uong bat ky size L mien phi", "points_required": 600, "reward_type": "free_product"},
        # physical gift
        {"reward_id": 8,  "reward_name": "Ly su Flex Coffee 350ml",            "points_required":  800, "reward_type": "physical_gift"},
        {"reward_id": 9,  "reward_name": "Ly giu nhiet Flex Coffee 500ml",     "points_required": 1200, "reward_type": "physical_gift"},
        {"reward_id": 10, "reward_name": "Tui vai Flex Coffee & Tea",          "points_required":  600, "reward_type": "physical_gift"},
        {"reward_id": 11, "reward_name": "Ca phe rang xay 200g (Retail)",      "points_required": 1000, "reward_type": "physical_gift"},
        {"reward_id": 12, "reward_name": "Set qua Flex (ly + ca phe + tra)",   "points_required": 2000, "reward_type": "physical_gift"},
    ]
    return pd.DataFrame(rows)


# ===========================================================================
# 9. STORE_OPERATING_HOURS (25 stores × 7 days)
# ===========================================================================
def generate_operating_hours(df_stores: pd.DataFrame) -> pd.DataFrame:
    print("  [9] store_operating_hours...")
    rows = []
    rec_id = 1

    for _, s in df_stores.iterrows():
        tier = s["location_tier"]
        city = s["city"]

        # Base open/close theo tier và thành phố
        if tier == "prime":
            open_h, close_h = 6, 22      # mặt phố trung tâm, mở sớm đóng muộn
        elif tier == "secondary":
            open_h, close_h = 7, 21      # hẻm/xa trung tâm
        else:
            open_h, close_h = 7, 22

        for dow in range(1, 8):  # 1=Mon..7=Sun
            # Cuối tuần mở muộn hơn 30 phút, đóng muộn hơn 1 tiếng (trừ secondary)
            if dow in [6, 7]:
                ow = open_h if tier == "secondary" else open_h
                cw = close_h + (0 if tier == "secondary" else 1)
            else:
                ow, cw = open_h, close_h

            rows.append({
                "operating_hours_id": rec_id,
                "store_id":    int(s["store_id"]),
                "day_of_week": dow,
                "open_time":   f"{ow:02d}:00:00",
                "close_time":  f"{min(cw, 23):02d}:00:00",
            })
            rec_id += 1

    return pd.DataFrame(rows)


# ===========================================================================
# 10. STORE_LEASE (1-2 hợp đồng/store, escalation ~7%)
# ===========================================================================
def generate_store_lease(df_stores: pd.DataFrame) -> pd.DataFrame:
    print("  [10] store_lease...")
    rng = random.Random(RNG_SEED + 10)
    rows = []
    lease_id = 1

    LANDLORD_NAMES = [
        "Nguyen Van A", "Tran Thi B", "Cong ty BDS Phuong Nam",
        "Ho Ngoc C", "Cong ty TNHH Dau tu XYZ", "Le Thi D",
        "Pham Van E", "Cong ty Co phan Dia oc ABC",
    ]

    for _, s in df_stores.iterrows():
        store_id  = int(s["store_id"])
        open_date = date.fromisoformat(str(s["open_date"]))
        rent_base = int(s["monthly_rent_vnd"])
        landlord  = rng.choice(LANDLORD_NAMES)

        # Hợp đồng 1: từ open_date, kéo dài 24-30 tháng
        dur1 = rng.randint(24, 30)
        end1 = date(open_date.year + dur1 // 12,
                    ((open_date.month - 1 + dur1 % 12) % 12) + 1,
                    1) - timedelta(days=1)

        rows.append({
            "lease_id":         lease_id,
            "store_id":         store_id,
            "lease_start_date": open_date.isoformat(),
            "lease_end_date":   end1.isoformat(),
            "monthly_rent_vnd": rent_base,
            "landlord_name":    landlord,
            "is_current":       0 if end1 < DATA_WINDOW_END else 1,
        })
        lease_id += 1

        # Hợp đồng 2 (tái ký): nếu end1 < DATA_WINDOW_END → cần hợp đồng tiếp theo
        if end1 < DATA_WINDOW_END:
            start2 = end1 + timedelta(days=1)
            escalation = rng.uniform(1.05, 1.10)
            rent2 = round(rent_base * escalation / 100_000) * 100_000
            rows.append({
                "lease_id":         lease_id,
                "store_id":         store_id,
                "lease_start_date": start2.isoformat(),
                "lease_end_date":   None,  # còn hiệu lực
                "monthly_rent_vnd": rent2,
                "landlord_name":    landlord,
                "is_current":       1,
            })
            lease_id += 1

    return pd.DataFrame(rows)


# ===========================================================================
# 11. DIM_WAREHOUSE
# ===========================================================================
def generate_warehouse() -> pd.DataFrame:
    print("  [11] dim_warehouse...")
    rows = [
        {"warehouse_id": 1, "warehouse_name": "Kho Mien Bac", "region": "Ha Noi"},
        {"warehouse_id": 2, "warehouse_name": "Kho Mien Nam", "region": "Ho Chi Minh - Da Nang"},
    ]
    return pd.DataFrame(rows)


# ===========================================================================
# 12. DIM_SUPPLIER (full: central + local + outsource)
# ===========================================================================
def generate_supplier() -> pd.DataFrame:
    print("  [12] dim_supplier...")
    rows = [
        # Central suppliers (nguyen lieu chinh, nhap tu kho trung tam)
        {"supplier_id": 1, "supplier_name": "Cong ty Ca phe Trung Nguyen Wholesale",
         "supplies_ingredient_type": "central", "service_region": "Toan quoc",      "category_served": "Ca phe"},
        {"supplier_id": 2, "supplier_name": "Tra Tan Cuong Co., Ltd.",
         "supplies_ingredient_type": "central", "service_region": "Toan quoc",      "category_served": "Tra"},
        {"supplier_id": 3, "supplier_name": "Vinamilk Industrial Supply",
         "supplies_ingredient_type": "central", "service_region": "Toan quoc",      "category_served": "Sua dac, Kem beo"},
        {"supplier_id": 4, "supplier_name": "Thai Duong Syrup & Ingredients",
         "supplies_ingredient_type": "central", "service_region": "Toan quoc",      "category_served": "Syrup, Nguyen lieu kho"},

        # Local suppliers (nguyen lieu tuoi, dat theo store/vung)
        {"supplier_id": 5, "supplier_name": "Vinamilk Fresh Milk - Ha Noi",
         "supplies_ingredient_type": "local",   "service_region": "Ha Noi",          "category_served": "Sua tuoi"},
        {"supplier_id": 6, "supplier_name": "Vinamilk Fresh Milk - HCM",
         "supplies_ingredient_type": "local",   "service_region": "Ho Chi Minh",     "category_served": "Sua tuoi"},
        {"supplier_id": 7, "supplier_name": "Cung cap Trai Cay Sach - Ha Noi",
         "supplies_ingredient_type": "local",   "service_region": "Ha Noi",          "category_served": "Trai cay, Puree"},
        {"supplier_id": 8, "supplier_name": "Cung cap Trai Cay Sach - HCM",
         "supplies_ingredient_type": "local",   "service_region": "Ho Chi Minh",     "category_served": "Trai cay, Puree"},
        {"supplier_id": 9, "supplier_name": "Cung cap Trai Cay Sach - Da Nang",
         "supplies_ingredient_type": "local",   "service_region": "Da Nang",         "category_served": "Trai cay, Puree"},
        {"supplier_id": 10, "supplier_name": "Nuoc Da Sach Gia Lai - Ha Noi",
         "supplies_ingredient_type": "local",   "service_region": "Ha Noi",          "category_served": "Da vien"},
        {"supplier_id": 11, "supplier_name": "Nuoc Da Sach - HCM",
         "supplies_ingredient_type": "local",   "service_region": "Ho Chi Minh",     "category_served": "Da vien"},
        {"supplier_id": 12, "supplier_name": "Tran Chau & Topping An Phat",
         "supplies_ingredient_type": "local",   "service_region": "Toan quoc",       "category_served": "Tran chau, Thach, Pudding"},

        # Outsource suppliers (Food/Retail/Merch - giu nguyen 4 nha cu, supplier_id 13-16)
        {"supplier_id": 13, "supplier_name": "Lavie Bakery Supply",
         "supplies_ingredient_type": "outsource", "service_region": "Toan quoc",    "category_served": "Food - Banh lanh"},
        {"supplier_id": 14, "supplier_name": "Sun Bakehouse Wholesale",
         "supplies_ingredient_type": "outsource", "service_region": "Toan quoc",    "category_served": "Food - Banh nong"},
        {"supplier_id": 15, "supplier_name": "Viet Coffee Bean Trading Co.",
         "supplies_ingredient_type": "outsource", "service_region": "Toan quoc",    "category_served": "Retail"},
        {"supplier_id": 16, "supplier_name": "Flex Merch Production Partner",
         "supplies_ingredient_type": "outsource", "service_region": "Toan quoc",    "category_served": "Merchandise"},
    ]
    return pd.DataFrame(rows)


# ===========================================================================
# 13. DIM_EXPENSE_CATEGORY
# ===========================================================================
def generate_expense_category() -> pd.DataFrame:
    print("  [13] dim_expense_category...")
    rows = [
        {"expense_category_id": 1, "expense_category_name": "Dien nuoc"},
        {"expense_category_id": 2, "expense_category_name": "Marketing Local (POSM, Banner)"},
        {"expense_category_id": 3, "expense_category_name": "Bao tri Thiet bi"},
        {"expense_category_id": 4, "expense_category_name": "Chi phi Khac"},
    ]
    return pd.DataFrame(rows)


# ===========================================================================
# 14. DIM_CAMPAIGN_PRODUCT_SCOPE (normalize từ dim_campaign.linked_product_id)
# ===========================================================================
def generate_campaign_product_scope(df_campaign: pd.DataFrame,
                                    df_product: pd.DataFrame) -> pd.DataFrame:
    print("  [14] dim_campaign_product_scope...")
    # dim_campaign có cột linked_product_id (int, nullable) — map sang new string ID
    # Beverage product: old int -> BVR-{id:03d}
    rows = []
    rec_id = 1
    for _, r in df_campaign.iterrows():
        linked = r.get("linked_product_id", None)
        if pd.isna(linked):
            continue
        old_pid = int(linked)
        # Chỉ beverage products (1-39) có trong dim_campaign; food dùng category-level
        new_pid = f"BVR-{old_pid:03d}"
        if new_pid in df_product["product_id"].values:
            rows.append({
                "campaign_scope_id": rec_id,
                "campaign_id":       int(r["campaign_id"]),
                "category_id":       None,
                "product_id":        new_pid,
            })
            rec_id += 1
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["campaign_scope_id","campaign_id","category_id","product_id"])


# ===========================================================================
# 15. UPDATE DIM_CUSTOMER (assign current_tier_id = TIER-1)
# ===========================================================================
def update_customer_tiers(df_customer: pd.DataFrame) -> pd.DataFrame:
    print("  [15] dim_customer (assign initial tier TIER-1)...")
    df = df_customer.copy()
    df["current_tier_id"] = "TIER-1"
    return df


# ===========================================================================
# MAIN
# ===========================================================================
def save(df: pd.DataFrame, filename: str):
    config.save_dimension(df, filename)
    print(f"       -> {filename} ({len(df):,} rows)")


def main():
    print("=" * 60)
    print("Phase 1: Generate Missing Dimensions")
    print("=" * 60)

    # Load inputs
    df_stores   = pd.read_csv(os.path.join(RAW_DIR, "dim_store.csv"))
    df_customer = pd.read_csv(os.path.join(RAW_DIR, "dim_customer.csv"))
    df_campaign = pd.read_csv(os.path.join(RAW_DIR, "dim_campaign.csv"))

    # 1. dim_date
    df_date = generate_dim_date()
    save(df_date, "dim_date.csv")

    # 2-6. Product dimensions
    df_cat, df_prod, df_var, df_recipe, df_excl = generate_product_dimensions()
    save(df_cat,    "dim_product_category.csv")
    save(df_prod,   "dim_product.csv")
    save(df_var,    "dim_product_variant.csv")
    save(df_recipe, "dim_recipe.csv")
    save(df_excl,   "dim_category_modifier_exclusion.csv")

    # 7. dim_membership_tier
    df_tier = generate_membership_tier()
    save(df_tier, "dim_membership_tier.csv")

    # 8. dim_reward_catalog
    df_reward = generate_reward_catalog()
    save(df_reward, "dim_reward_catalog.csv")

    # 9. store_operating_hours
    df_hours = generate_operating_hours(df_stores)
    save(df_hours, "store_operating_hours.csv")

    # 10. store_lease
    df_lease = generate_store_lease(df_stores)
    save(df_lease, "store_lease.csv")

    # 11. dim_warehouse
    df_wh = generate_warehouse()
    save(df_wh, "dim_warehouse.csv")

    # 12. dim_supplier
    df_sup = generate_supplier()
    save(df_sup, "dim_supplier.csv")

    # 13. dim_expense_category
    df_exp = generate_expense_category()
    save(df_exp, "dim_expense_category.csv")

    # 14. dim_campaign_product_scope
    df_scope = generate_campaign_product_scope(df_campaign, df_prod)
    save(df_scope, "dim_campaign_product_scope.csv")

    # 15. dim_customer (cập nhật tier)
    df_cust_updated = update_customer_tiers(df_customer)
    save(df_cust_updated, "dim_customer.csv")
    
    # Export missing ones to match SQL schema
    df_ingredient = pd.read_csv(os.path.join(config.DIM_TEMP_DIR, "dim_ingredient_beverage.csv"))
    save(df_ingredient, "dim_ingredient.csv")

    print()
    print("=" * 60)
    print("[DONE] All Phase 1 dimensions generated.")
    print(f"       Output folder: {RAW_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
