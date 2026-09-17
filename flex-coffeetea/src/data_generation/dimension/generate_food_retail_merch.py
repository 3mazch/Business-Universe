"""
Flex Coffee & Tea — Generator: Food / Retail / Merchandise Product & Cost-Price Logic
=====================================================================================
Khác biệt so với đồ uống (Cà phê/Trà/Đá xay/LTO):
- KHÔNG dùng dim_ingredient/dim_recipe (không BOM nhiều nguyên liệu).
- Mỗi sản phẩm = 1 SKU nhập nguyên từ nhà cung cấp outsource (finished goods).
- Giá vốn (cost_price_vnd) và giá bán (sell_price_vnd) gắn trực tiếp vào product_variant.
- Tồn kho tiêu hao theo kiểu 1:1 -- bán 1 SKU thì trừ đúng 1 đơn vị đã nhập.

Output:
- dim_supplier_outsource.csv   (nhà cung cấp outsource cho 3 category này)
- dim_product_food_retail_merch.csv   (danh sách sản phẩm + variant + cost/price)
"""

import random
import pandas as pd

RNG_SEED = 42
random.seed(RNG_SEED)

# ---------------------------------------------------------------------------
# 1. THAM SỐ MARGIN THEO CATEGORY (giả định hợp lý, cần bạn review lại)
# ---------------------------------------------------------------------------
# [Fix] Offset ID tranh xung dot PK voi dim_product_beverage. 
# Dat o moc 1000 de tach biet hoan toan khoang ID (Beverage: 1-999, Food: 1000+)
START_PRODUCT_ID = 1000
START_VARIANT_ID = 1000

# cost_ratio = cost_price / sell_price -> ty le gia von tren gia ban
# [Fix] Food-Banh lanh: doi (0.42, 0.52) -> (0.42, 0.45) de dam bao margin ~55-58% theo BRS
#   cost_ratio 0.42 -> margin 58% | cost_ratio 0.45 -> margin 55% -- dung voi BRS
CATEGORY_COST_RATIO = {
    "Food - Banh lanh":  (0.42, 0.45),   # margin ~55-58% theo BRS
    "Food - Banh nong":  (0.38, 0.48),
    "Retail":            (0.58, 0.70),   # hang dong goi ban lai, bien loi nhuan mong hon do F&B
    "Merchandise":       (0.35, 0.50),   # hang thuong hieu, bien loi nhuan tot hon
}

# Khung gia ban tham khao (VND) -- neu ban muon chinh lai, sua truc tiep o day
CATEGORY_PRICE_RANGE = {
    "Food - Banh lanh":  (28_000, 42_000),
    "Food - Banh nong":  (20_000, 38_000),
    "Retail":            (95_000, 240_000),
    "Merchandise":       (55_000, 320_000),
}

# ---------------------------------------------------------------------------
# 2. NHÀ CUNG CẤP OUTSOURCE
# ---------------------------------------------------------------------------
OUTSOURCE_SUPPLIERS = [
    {"supplier_name": "Lavie Bakery Supply", "category": "Food - Banh lanh", "region": "Toan quoc"},
    {"supplier_name": "Sun Bakehouse Wholesale", "category": "Food - Banh nong", "region": "Toan quoc"},
    {"supplier_name": "Viet Coffee Bean Trading Co.", "category": "Retail", "region": "Toan quoc"},
    {"supplier_name": "Flex Merch Production Partner", "category": "Merchandise", "region": "Toan quoc"},
]

# ---------------------------------------------------------------------------
# 3. DANH SÁCH SẢN PHẨM (theo menu đã chốt)
# ---------------------------------------------------------------------------
PRODUCTS = {
    "Food - Banh lanh": [
        "Banh lanh Matcha", "Banh lanh Socola", "Banh lanh Red Velvet",
        "Banh Mousse Chanh Day", "Sua Chua Hu",
    ],
    "Food - Banh nong": [
        "Banh Mi Que", "Banh Mi Thap Cam", "Sandwich", "Croissant Bo",
        "Croissant Chocolate", "Croissant Trung Muoi",
    ],
    "Retail": [
        "Ca Phe Hat Arabica", "Ca Phe Hat Robusta", "Ca Phe Xay Arabica",
        "Ca Phe Xay Robusta", "Tra Lai Dong Goi", "Tra O Long Dong Goi",
    ],
    "Merchandise": [
        "Ly Nhua 1 Lop", "Ly Nhua 2 Lop", "Ly Giu Nhiet", "Binh Giu Nhiet",
        "Tui Tote", "Pin Cai Ao", "Moc Khoa",
    ],
}

# category cap 1 chinh thuc trong dim_product_category (Food / Retail / Merchandise)
CATEGORY_L1_MAP = {
    "Food - Banh lanh": "Food",
    "Food - Banh nong": "Food",
    "Retail": "Retail dong goi",
    "Merchandise": "Merchandise",
}

LAUNCH_DATE_DEFAULT = "2021-01-01"  # gia dinh cac SKU nay co mat tu som, khong theo lan song mo store


def round_to_nearest(value, nearest=1000):
    return int(round(value / nearest) * nearest)


def generate_products():
    rows = []
    product_id_seq = START_PRODUCT_ID   
    variant_id_seq = START_VARIANT_ID   

    for sub_category, product_names in PRODUCTS.items():
        cost_lo, cost_hi = CATEGORY_COST_RATIO[sub_category]
        price_lo, price_hi = CATEGORY_PRICE_RANGE[sub_category]
        category_l1 = CATEGORY_L1_MAP[sub_category]

        # tim supplier outsource tuong ung
        supplier = next(s for s in OUTSOURCE_SUPPLIERS if s["category"] == sub_category)

        for name in product_names:
            sell_price = round_to_nearest(random.uniform(price_lo, price_hi), 1000)
            cost_ratio = random.uniform(cost_lo, cost_hi)
            cost_price = round_to_nearest(sell_price * cost_ratio, 500)
            margin_pct = round((sell_price - cost_price) / sell_price * 100, 1)

            sku_prefix = {
                "Food - Banh lanh": "FOODC",
                "Food - Banh nong": "FOODH",
                "Retail": "RETAIL",
                "Merchandise": "MERCH",
            }[sub_category]
            sku = f"{sku_prefix}-{variant_id_seq:03d}"

            rows.append({
                "product_id": product_id_seq,
                "variant_id": variant_id_seq,
                "sku": sku,
                "product_name": name,
                "category_l1": category_l1,
                "sub_category": sub_category,
                "outsource_supplier": supplier["supplier_name"],
                "sourcing_model": "outsource_finished_goods",  # khong qua dim_ingredient/dim_recipe
                "cost_price_vnd": cost_price,
                "sell_price_vnd": sell_price,
                "margin_pct": margin_pct,
                "launch_date": LAUNCH_DATE_DEFAULT,
                "status": "active",
            })
            product_id_seq += 1
            variant_id_seq += 1

    return pd.DataFrame(rows)


def generate_supplier_table():
    return pd.DataFrame([
        {
            "supplier_id": i + 1,
            "supplier_name": s["supplier_name"],
            "supplies_ingredient_type": "outsource",
            "service_region": s["region"],
            "category_served": s["category"],
        }
        for i, s in enumerate(OUTSOURCE_SUPPLIERS)
    ])


def main():
    df_products = generate_products()
    df_suppliers = generate_supplier_table()

    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

    config.save_temp(df_products, "dim_product_food_retail_merch.csv")
    config.save_temp(df_suppliers, "dim_supplier_outsource.csv")

    return df_products, df_suppliers


if __name__ == "__main__":
    df_products, df_suppliers = main()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print("=== SUPPLIERS ===")
    print(df_suppliers.to_string(index=False))
    print("\n=== PRODUCTS (sample) ===")
    print(df_products.to_string(index=False))
    print("\n=== SUMMARY BY SUB-CATEGORY ===")
    summary = df_products.groupby("sub_category").agg(
        n_products=("product_id", "count"),
        avg_sell_price=("sell_price_vnd", "mean"),
        avg_cost_price=("cost_price_vnd", "mean"),
        avg_margin_pct=("margin_pct", "mean"),
    ).round(1)
    print(summary.to_string())