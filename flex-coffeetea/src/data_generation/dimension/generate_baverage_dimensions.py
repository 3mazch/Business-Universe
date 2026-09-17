"""
Flex Coffee & Tea — Generator: Beverage Dimension Data
=======================================================
Sinh du lieu cho 4 category do uong (Ca phe, Tra, Da xay, LTO):
- dim_product_category (beverage-only, 4 dong)
- dim_product (32 san pham)
- dim_product_variant (64 bien the M/L)
- dim_ingredient (nguyen lieu pha che dung chung)
- dim_recipe (BOM: variant x ingredient x dinh luong)
- dim_modifier (topping / sweetness / ice)

Nguon logic: Flex_CoffeeTea_Menu_Recipe_v1.md (template theo kieu pha che).
sourcing_model = 'in_house_recipe' cho toan bo -- gia von KHONG luu truc tiep,
se tinh qua dim_recipe x gia nhap ingredient (fact_purchase_order_item) o buoc sau.
"""

import random
import pandas as pd

RNG_SEED = 42
random.seed(RNG_SEED)

L_SIZE_MULTIPLIER = 1.3          # dinh luong L = M x 1.3 (da chot)
L_PRICE_INCREMENT_RANGE = (5000, 8000)  # gia L cao hon M (VND), theo BRS

# ---------------------------------------------------------------------------
# 1. DANH SÁCH NGUYÊN LIỆU (dim_ingredient)
# ---------------------------------------------------------------------------
INGREDIENTS = [
    # (ten, don vi, source_type, shelf_life_days)
    ("Ca phe rang xay Robusta", "kg", "central", 270),
    ("Ca phe hat Arabica (xay espresso)", "kg", "central", 270),
    ("Sua dac", "lit", "central", 365),
    ("Sua tuoi", "lit", "local", 10),
    ("Cot dua", "lit", "local", 15),
    ("Kem beo (creamer)", "kg", "central", 180),
    ("Kem muoi", "kg", "local", 20),
    ("Tra lai (cot u san)", "lit", "central", 3),
    ("Tra o long (cot u san)", "lit", "central", 3),
    ("Syrup vai", "lit", "central", 180),
    ("Syrup nhan", "lit", "central", 180),
    ("Syrup mang cau", "lit", "central", 180),
    ("Syrup dao", "lit", "central", 180),
    ("Syrup dau", "lit", "central", 180),
    ("Syrup xoai", "lit", "central", 180),
    ("Syrup chanh", "lit", "central", 180),
    ("Syrup hoa dao (LTO)", "lit", "central", 180),
    ("Syrup oi hong dao (LTO)", "lit", "central", 180),
    ("Bot matcha", "kg", "central", 270),
    ("Bot cacao / Sot chocolate", "kg", "central", 270),
    ("Puree xoai", "kg", "local", 20),
    ("Kem pho mai", "kg", "local", 20),
    ("Syrup duong", "lit", "central", 365),
    ("Da vien", "kg", "local", 1),
    ("Tran chau den", "kg", "local", 3),
    ("Tran chau trang", "kg", "local", 3),
    ("Thach trai cay/dua/ca phe", "kg", "local", 5),
    ("Pudding trung", "kg", "local", 5),
    ("Tran chau duong den (LTO)", "kg", "local", 3),
    ("Dua non tuoi (LTO)", "kg", "local", 3),
    ("Nuoc cot chanh", "lit", "local", 5),
    ("Cold brew nen (LTO)", "lit", "central", 5),
    # --- Nguyen lieu LTO bo sung 2023-2026 ---
    ("Syrup hanh nhan (LTO)", "lit", "central", 180),
    ("Syrup cam sa (LTO)", "lit", "central", 180),
    ("Com xanh (LTO)", "kg", "local", 5),
    ("Syrup que tao do (LTO)", "lit", "central", 180),
    ("Syrup buoi mat ong (LTO)", "lit", "central", 180),
    ("Syrup dua hau (LTO)", "lit", "central", 180),
    ("Syrup cam que (LTO)", "lit", "central", 180),
    ("Syrup mam xoi (LTO)", "lit", "central", 180),
    ("Syrup dua (LTO)", "lit", "central", 180),
    ("Syrup sau (LTO)", "lit", "central", 180),
]

# ---------------------------------------------------------------------------
# 2. DANH SÁCH SẢN PHẨM THEO CATEGORY + TEMPLATE RECIPE THAM CHIẾU
# ---------------------------------------------------------------------------
# moi san pham: (ten, category, template_key, price_base_M, launch_date, discontinued_date)
BASE_LAUNCH = "2021-01-01"

PRODUCTS = [
    # --- CA PHE (phin truyen thong) ---
    ("Ca phe Den", "Ca Phe", "phin_den", 29000, BASE_LAUNCH, None),
    ("Ca phe Sua", "Ca Phe", "phin_sua", 32000, BASE_LAUNCH, None),
    ("Bac Xiu", "Ca Phe", "phin_bacxiu", 35000, BASE_LAUNCH, None),
    ("Ca phe Muoi", "Ca Phe", "phin_muoi", 39000, BASE_LAUNCH, None),
    ("Ca phe Dua", "Ca Phe", "phin_dua", 39000, BASE_LAUNCH, None),
    # --- CA PHE (espresso-based) ---
    ("Espresso", "Ca Phe", "espresso_nguyenchat", 35000, BASE_LAUNCH, None),
    ("Latte", "Ca Phe", "espresso_latte", 42000, BASE_LAUNCH, None),
    ("Cappuccino", "Ca Phe", "espresso_cappuccino", 42000, BASE_LAUNCH, None),
    ("Mocha", "Ca Phe", "espresso_mocha", 45000, BASE_LAUNCH, None),
    # --- TRA LAI (fruit / sua / kem pho mai) ---
    ("Tra Lai Vai", "Tra", "fruit_tealai", 39000, BASE_LAUNCH, None),
    ("Tra Lai Nhan", "Tra", "fruit_tealai", 39000, BASE_LAUNCH, None),
    ("Tra Lai Mang Cau", "Tra", "fruit_tealai", 39000, BASE_LAUNCH, None),
    ("Tra Sua Tra Lai", "Tra", "milktea_tealai", 42000, BASE_LAUNCH, None),
    ("Tra Kem Pho Mai Tra Lai", "Tra", "creamcheese_tealai", 45000, BASE_LAUNCH, None),
    # --- TRA O LONG (fruit / sua / kem pho mai) ---
    ("Tra O Long Dao", "Tra", "fruit_oolong", 39000, BASE_LAUNCH, None),
    ("Tra O Long Dau", "Tra", "fruit_oolong", 39000, BASE_LAUNCH, None),
    ("Tra O Long Xoai", "Tra", "fruit_oolong", 39000, BASE_LAUNCH, None),
    ("Tra Sua O Long", "Tra", "milktea_oolong", 42000, BASE_LAUNCH, None),
    ("Tra Kem Pho Mai O Long", "Tra", "creamcheese_oolong", 45000, BASE_LAUNCH, None),
    # --- TRA KHAC ---
    ("Matcha Latte", "Tra", "matcha_latte", 45000, BASE_LAUNCH, None),
    ("Chocolate Latte", "Tra", "chocolate_latte", 45000, BASE_LAUNCH, None),
    # --- DA XAY ---
    ("Da Xay Ca Phe", "Da Xay", "blend_caphe", 49000, BASE_LAUNCH, None),
    ("Da Xay Chocolate", "Da Xay", "blend_chocolate", 49000, BASE_LAUNCH, None),
    ("Da Xay Matcha", "Da Xay", "blend_matcha", 52000, BASE_LAUNCH, None),
    ("Da Xay Xoai", "Da Xay", "blend_xoai", 49000, BASE_LAUNCH, None),
    ("Da Xay Chanh", "Da Xay", "blend_chanh", 45000, BASE_LAUNCH, None),
    # --- LTO (13 nhom tu Q3/2023 den Q3/2026) ---
    # Nam 1
    ("Tra Sua Tran Chau Duong Den Nuong", "LTO", "lto_tsdduongden", 45000, "2023-07-01", "2023-09-30"),
    ("Chocolate Latte Hanh Nhan", "LTO", "lto_chocolatelatte_hanhnhan", 49000, "2023-10-01", "2023-12-31"),
    ("Latte Hoa Dao", "LTO", "lto_lattehoadao", 49000, "2024-01-01", "2024-03-31"),
    ("Cold Brew Cam Sa", "LTO", "lto_coldbrew_camsa", 49000, "2024-04-01", "2024-06-30"),
    # Nam 2
    ("Ca Phe Cot Dua Com Xanh", "LTO", "lto_caphecotdua_comxanh", 45000, "2024-07-01", "2024-09-30"),
    ("Tra Que Tao Do", "LTO", "lto_traque_taodo", 45000, "2024-10-01", "2024-12-31"),
    ("Tra O Long Buoi Mat Ong", "LTO", "lto_traolong_buoimatong", 45000, "2025-01-01", "2025-03-31"),
    ("Tra Xanh Dua Hau", "LTO", "lto_traxanh_duahau", 45000, "2025-04-01", "2025-06-30"),
    # Nam 3
    ("Ca phe Muoi Tran Chau", "LTO", "lto_caphemuoitcp", 42000, "2025-07-01", "2025-09-30"),
    ("Latte Cam Que", "LTO", "lto_lattecamque", 49000, "2025-10-01", "2025-12-31"),
    ("Tra Lai Mam Xoi", "LTO", "lto_tralai_mamxoi", 45000, "2026-01-01", "2026-03-31"),
    ("Tra Dua Tran Chau", "LTO", "lto_tradua_tranchau", 45000, "2026-04-01", "2026-06-30"),
    # Nam 4 (Q3 2026)
    ("Cold Brew Sau Mua Thu", "LTO", "lto_coldbrew_sau", 49000, "2026-07-01", "2026-09-30"),
]

# ---------------------------------------------------------------------------
# 3. RECIPE TEMPLATES (dinh luong chuan tai size M, muc duong/da 100%)
# ---------------------------------------------------------------------------
# key nguyen lieu phai khop chinh xac ten trong INGREDIENTS
RECIPE_TEMPLATES = {
    "phin_den": {"Ca phe rang xay Robusta": 20, "Nuoc soi (khong tinh kho)": 0,
                 "Syrup duong": 10, "Da vien": 120},
    "phin_sua": {"Ca phe rang xay Robusta": 20, "Sua dac": 20, "Syrup duong": 8, "Da vien": 120},
    "phin_bacxiu": {"Ca phe rang xay Robusta": 20, "Sua dac": 40, "Syrup duong": 5, "Da vien": 130},
    "phin_muoi": {"Ca phe rang xay Robusta": 20, "Sua dac": 20, "Kem muoi": 30, "Syrup duong": 8, "Da vien": 120},
    "phin_dua": {"Ca phe rang xay Robusta": 20, "Sua dac": 15, "Cot dua": 40, "Syrup duong": 8, "Da vien": 120},
    "espresso_nguyenchat": {"Ca phe hat Arabica (xay espresso)": 18, "Syrup duong": 5, "Da vien": 80},
    "espresso_latte": {"Ca phe hat Arabica (xay espresso)": 18, "Sua tuoi": 150, "Syrup duong": 8, "Da vien": 100},
    "espresso_cappuccino": {"Ca phe hat Arabica (xay espresso)": 18, "Sua tuoi": 130, "Syrup duong": 8, "Da vien": 90},
    "espresso_mocha": {"Ca phe hat Arabica (xay espresso)": 18, "Sua tuoi": 140, "Bot cacao / Sot chocolate": 25,
                        "Syrup duong": 6, "Da vien": 100},
    "fruit_tealai": {"Tra lai (cot u san)": 150, "Syrup duong": 15, "Da vien": 130},  # + syrup vi rieng khi gan product
    "fruit_oolong": {"Tra o long (cot u san)": 150, "Syrup duong": 15, "Da vien": 130},
    "milktea_tealai": {"Tra lai (cot u san)": 120, "Sua dac": 30, "Kem beo (creamer)": 10, "Syrup duong": 10, "Da vien": 130},
    "milktea_oolong": {"Tra o long (cot u san)": 120, "Sua dac": 30, "Kem beo (creamer)": 10, "Syrup duong": 10, "Da vien": 130},
    "creamcheese_tealai": {"Tra lai (cot u san)": 150, "Syrup duong": 15, "Da vien": 130, "Kem pho mai": 40},
    "creamcheese_oolong": {"Tra o long (cot u san)": 150, "Syrup duong": 15, "Da vien": 130, "Kem pho mai": 40},
    "matcha_latte": {"Bot matcha": 12, "Sua tuoi": 160, "Syrup duong": 10, "Da vien": 100},
    "chocolate_latte": {"Bot cacao / Sot chocolate": 30, "Sua tuoi": 160, "Syrup duong": 8, "Da vien": 100},
    "blend_caphe": {"Da vien": 200, "Sua dac": 30, "Syrup duong": 15, "Ca phe rang xay Robusta": 15},
    "blend_chocolate": {"Da vien": 200, "Sua dac": 30, "Syrup duong": 15, "Bot cacao / Sot chocolate": 30},
    "blend_matcha": {"Da vien": 200, "Sua dac": 30, "Syrup duong": 15, "Bot matcha": 12},
    "blend_xoai": {"Da vien": 200, "Sua dac": 30, "Syrup duong": 15, "Puree xoai": 60},
    "blend_chanh": {"Da vien": 200, "Sua dac": 30, "Syrup duong": 20, "Nuoc cot chanh": 30},
    # --- Recipe templates LTO 13 quarters ---
    "lto_tsdduongden": {"Tra lai (cot u san)": 120, "Sua dac": 30, "Kem beo (creamer)": 10, "Tran chau duong den (LTO)": 30, "Syrup duong": 8, "Da vien": 120},
    "lto_chocolatelatte_hanhnhan": {"Bot cacao / Sot chocolate": 30, "Sua tuoi": 150, "Syrup hanh nhan (LTO)": 20, "Syrup duong": 8, "Da vien": 100},
    "lto_lattehoadao": {"Ca phe hat Arabica (xay espresso)": 18, "Sua tuoi": 150, "Syrup hoa dao (LTO)": 20, "Syrup duong": 5, "Da vien": 100},
    "lto_coldbrew_camsa": {"Cold brew nen (LTO)": 150, "Syrup cam sa (LTO)": 20, "Syrup duong": 10, "Da vien": 90},
    "lto_caphecotdua_comxanh": {"Ca phe rang xay Robusta": 20, "Sua dac": 15, "Cot dua": 40, "Com xanh (LTO)": 20, "Syrup duong": 5, "Da vien": 120},
    "lto_traque_taodo": {"Tra o long (cot u san)": 150, "Syrup que tao do (LTO)": 30, "Syrup duong": 10, "Da vien": 130},
    "lto_traolong_buoimatong": {"Tra o long (cot u san)": 150, "Syrup buoi mat ong (LTO)": 30, "Syrup duong": 15, "Da vien": 130},
    "lto_traxanh_duahau": {"Tra lai (cot u san)": 150, "Syrup dua hau (LTO)": 30, "Syrup duong": 15, "Da vien": 130},
    "lto_caphemuoitcp": {"Ca phe rang xay Robusta": 20, "Sua dac": 20, "Kem muoi": 30, "Tran chau den": 30, "Syrup duong": 8, "Da vien": 120},
    "lto_lattecamque": {"Ca phe hat Arabica (xay espresso)": 18, "Sua tuoi": 150, "Syrup cam que (LTO)": 20, "Syrup duong": 5, "Da vien": 100},
    "lto_tralai_mamxoi": {"Tra lai (cot u san)": 150, "Syrup mam xoi (LTO)": 30, "Syrup duong": 15, "Da vien": 130},
    "lto_tradua_tranchau": {"Tra lai (cot u san)": 150, "Syrup dua (LTO)": 30, "Tran chau den": 30, "Syrup duong": 10, "Da vien": 120},
    "lto_coldbrew_sau": {"Cold brew nen (LTO)": 150, "Syrup sau (LTO)": 20, "Syrup duong": 10, "Da vien": 90},
}

# syrup vi rieng gan them cho tung mon trai cay cu the (cong vao template fruit_tealai / fruit_oolong)
FRUIT_FLAVOR_MAP = {
    "Tra Lai Vai": "Syrup vai",
    "Tra Lai Nhan": "Syrup nhan",
    "Tra Lai Mang Cau": "Syrup mang cau",
    "Tra O Long Dao": "Syrup dao",
    "Tra O Long Dau": "Syrup dau",
    "Tra O Long Xoai": "Syrup xoai",
}
FRUIT_FLAVOR_QTY = 30  # ml

# toppping khong nam trong recipe goc (chi ap dung khi khach chon o thoi diem order) -> khong dua vao dim_recipe

# ---------------------------------------------------------------------------
# 4. MODIFIER
# ---------------------------------------------------------------------------
MODIFIERS = [
    ("topping", "Tran chau den", 8000),
    ("topping", "Tran chau trang", 8000),
    ("topping", "Thach (dua/ca phe/trai cay)", 8000),
    ("topping", "Pudding trung", 10000),
    ("topping", "Kem cheese phu", 12000),
    ("sweetness", "50% duong", 0),
    ("sweetness", "100% duong", 0),
    ("sweetness", "150% duong", 0),
    ("ice", "50% da", 0),
    ("ice", "100% da", 0),
    ("ice", "150% da", 0),
]

CATEGORY_MODIFIER_EXCLUSION = {
    "Da Xay": ["ice"],  # da xay khong ap dung dieu chinh muc da
}

# ---------------------------------------------------------------------------
# 5. HÀM SINH DỮ LIỆU
# ---------------------------------------------------------------------------

def build_ingredient_table():
    rows = []
    for i, (name, unit, source, shelf) in enumerate(INGREDIENTS, start=1):
        rows.append({
            "ingredient_id": i, "ingredient_name": name, "unit": unit,
            "source_type": source, "avg_shelf_life_days": shelf,
        })
    df = pd.DataFrame(rows)
    # bo dong "Nuoc soi" gia (khong tinh kho, chi de placeholder trong template) neu co xuat hien trong recipe
    return df


def build_category_table():
    cats = ["Ca Phe", "Tra", "Da Xay", "LTO"]
    return pd.DataFrame([{"category_id": i, "category_name": c} for i, c in enumerate(cats, start=1)])


def build_product_and_variant_tables(df_category):
    cat_map = dict(zip(df_category["category_name"], df_category["category_id"]))
    product_rows, variant_rows = [], []
    product_id = 1
    variant_id = 1

    for name, category, template_key, price_m, launch, discontinued in PRODUCTS:
        product_rows.append({
            "product_id": product_id,
            "category_id": cat_map[category],
            "product_name": name,
            "template_key": template_key,
            "launch_date": launch,
            "discontinued_date": discontinued,
            "status": "active",   # [Fix] LTO cung la 'active' (co the lap lai theo mua) -- SQL CHECK constraint chi cho phep 'active'/'discontinued'; effective_to tren variant kiem soat availability
        })

        price_l = price_m + random.randint(*L_PRICE_INCREMENT_RANGE)
        price_l = round(price_l / 1000) * 1000

        sku_prefix = {"Ca Phe": "CF", "Tra": "TR", "Da Xay": "DX", "LTO": "LTO"}[category]

        for size_code, price in [("M", price_m), ("L", price_l)]:
            variant_rows.append({
                "variant_id": variant_id,
                "product_id": product_id,
                "product_name": name,
                "category": category,
                "size_code": size_code,
                "sku": f"{sku_prefix}-{product_id:02d}-{size_code}",
                "base_price_vnd": price,
                "cost_price_vnd": None,  # tinh qua recipe, khong luu truc tiep
                "sourcing_model": "in_house_recipe",
                "effective_from": launch,
                "effective_to": discontinued,        # [Fix] LTO: gan discontinued_date, None neu san pham con active
                "is_current": 0 if discontinued else 1,  # [Fix] LTO: is_current=0 khi da ket thuc mua
            })
            variant_id += 1

        product_id += 1

    return pd.DataFrame(product_rows), pd.DataFrame(variant_rows)


def build_recipe_table(df_variant, df_ingredient):
    ing_map = dict(zip(df_ingredient["ingredient_name"], df_ingredient["ingredient_id"]))
    rows = []
    recipe_id = 1

    variants_m = df_variant[df_variant["size_code"] == "M"]

    for _, v in variants_m.iterrows():
        product_name = v["product_name"]
        # tim template_key tuong ung tu PRODUCTS
        template_key = next(p[2] for p in PRODUCTS if p[0] == product_name)
        base_recipe = dict(RECIPE_TEMPLATES[template_key])

        # neu la mon trai cay co syrup vi rieng -> them vao
        if product_name in FRUIT_FLAVOR_MAP:
            base_recipe[FRUIT_FLAVOR_MAP[product_name]] = FRUIT_FLAVOR_QTY

        for ingredient_name, qty_m in base_recipe.items():
            if ingredient_name not in ing_map:
                continue  # bo qua placeholder nhu 'Nuoc soi'
            qty_l = round(qty_m * L_SIZE_MULTIPLIER, 1)

            # dong cho variant size M
            variant_id_m = v["variant_id"]
            rows.append({
                "recipe_id": recipe_id, "variant_id": variant_id_m,
                "ingredient_id": ing_map[ingredient_name], "ingredient_name": ingredient_name,
                "quantity_per_unit": qty_m,
            })
            recipe_id += 1

            # dong cho variant size L (tim variant_id tuong ung)
            variant_id_l = df_variant[
                (df_variant["product_id"] == v["product_id"]) & (df_variant["size_code"] == "L")
            ]["variant_id"].iloc[0]
            rows.append({
                "recipe_id": recipe_id, "variant_id": variant_id_l,
                "ingredient_id": ing_map[ingredient_name], "ingredient_name": ingredient_name,
                "quantity_per_unit": qty_l,
            })
            recipe_id += 1

    return pd.DataFrame(rows)


def build_modifier_table():
    rows = []
    for i, (group, name, price) in enumerate(MODIFIERS, start=1):
        rows.append({"modifier_id": i, "modifier_group": group, "modifier_name": name, "extra_price_vnd": price})
    return pd.DataFrame(rows)


def build_category_modifier_scope_note():
    rows = []
    for cat, excluded_groups in CATEGORY_MODIFIER_EXCLUSION.items():
        for g in excluded_groups:
            rows.append({"category_name": cat, "modifier_group": g,
                         "reason": "Da xay khong chinh da" if g=="ice" else "Khong ho tro"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def main():
    df_ingredient = build_ingredient_table()
    df_category = build_category_table()
    df_product, df_variant = build_product_and_variant_tables(df_category)
    df_recipe = build_recipe_table(df_variant, df_ingredient)
    df_modifier = build_modifier_table()
    df_modifier_scope = build_category_modifier_scope_note()

    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config
    
    config.save_temp(df_category, "dim_product_category_beverage.csv")
    config.save_temp(df_product, "dim_product_beverage.csv")
    config.save_temp(df_variant, "dim_product_variant_beverage.csv")
    config.save_temp(df_ingredient, "dim_ingredient_beverage.csv")
    config.save_temp(df_recipe, "dim_recipe_beverage.csv")
    config.save_dimension(df_modifier, "dim_modifier.csv")
    config.save_dimension(df_modifier_scope, "dim_category_modifier_exclusion.csv")

    return df_ingredient, df_category, df_product, df_variant, df_recipe, df_modifier, df_modifier_scope


if __name__ == "__main__":
    (df_ingredient, df_category, df_product, df_variant,
     df_recipe, df_modifier, df_modifier_scope) = main()

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)

    print("=== CATEGORY ===")
    print(df_category.to_string(index=False))
    print(f"\n=== PRODUCT ({len(df_product)} san pham) ===")
    print(df_product.to_string(index=False))
    print(f"\n=== VARIANT ({len(df_variant)} bien the M/L) — sample 10 dong dau ===")
    print(df_variant.head(10).to_string(index=False))
    print(f"\n=== INGREDIENT ({len(df_ingredient)} nguyen lieu) ===")
    print(df_ingredient.to_string(index=False))
    print(f"\n=== RECIPE ({len(df_recipe)} dong BOM) — sample cho 'Ca phe Sua' ===")
    sample_variant_ids = df_variant[df_variant["product_name"] == "Ca phe Sua"]["variant_id"].tolist()
    print(df_recipe[df_recipe["variant_id"].isin(sample_variant_ids)].to_string(index=False))
    print(f"\n=== RECIPE sample cho 'Tra Lai Vai' (co syrup vi rieng) ===")
    sample_variant_ids2 = df_variant[df_variant["product_name"] == "Tra Lai Vai"]["variant_id"].tolist()
    print(df_recipe[df_recipe["variant_id"].isin(sample_variant_ids2)].to_string(index=False))
    print("\n=== MODIFIER ===")
    print(df_modifier.to_string(index=False))
    print("\n=== MODIFIER EXCLUSION THEO CATEGORY ===")
    print(df_modifier_scope.to_string(index=False))
    print(f"\nTONG KET: {len(df_product)} san pham, {len(df_variant)} bien the, "
          f"{len(df_ingredient)} nguyen lieu, {len(df_recipe)} dong recipe.")