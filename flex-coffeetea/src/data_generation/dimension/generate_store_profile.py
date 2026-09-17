"""
Flex Coffee & Tea — Store Profile Generator
Sinh 25 cửa hàng với thuộc tính & baseline có tương quan logic, theo BRS v1.1.

Nguyên tắc cốt lõi (bám BRS Domain 1 + Cross-domain rules):
- KHÔNG phân tầng cứng Flagship/Standard/Kiosk.
- Rent = f(size, location_tier, city) + noise, KHÔNG tuyến tính đơn giản.
- Outlier có chủ đích: store nhỏ + vị trí đẹp -> rent/m2 cao, biên lợi nhuận mỏng hơn.
- Channel mix dao động quanh baseline hệ thống (50% tại chỗ / 20% app / 30% giao hàng)
  tùy theo vị trí (gần văn phòng -> app/tại chỗ cao hơn; khu du lịch/dân cư -> giao hàng cao hơn).
- Doanh thu baseline tương quan với size, location_tier, city, có ramp-up cho store mới mở.
- Store mới mở theo làn sóng (wave) chứ không mở đồng loạt.
- Warehouse: Kho miền Bắc phục vụ HN; Kho miền Nam phục vụ HCM + ĐN.
"""

import json
import random
from datetime import date, timedelta

import pandas as pd

RNG_SEED = 42
random.seed(RNG_SEED)

# ---------------------------------------------------------------------------
# 1. THAM SỐ HỆ THỐNG (system-level baseline constants)
# ---------------------------------------------------------------------------

CITIES = {
    "Ha Noi": {"code": "HN", "store_count": 10, "warehouse_region": "Kho Mien Bac",
               "rent_index": 1.15, "revenue_index": 1.05},
    "Ho Chi Minh": {"code": "HCM", "store_count": 10, "warehouse_region": "Kho Mien Nam",
                    "rent_index": 1.20, "revenue_index": 1.10},
    "Da Nang": {"code": "DN", "store_count": 5, "warehouse_region": "Kho Mien Nam",
                "rent_index": 0.85, "revenue_index": 0.80},
}

# Vị trí: prime (mặt phố lớn / trung tâm), standard (mặt phố nhỏ / khu dân cư đông),
# secondary (hẻm / xa trung tâm / khu mới phát triển)
LOCATION_TIERS = {
    "prime":     {"rent_multiplier": 2.3, "revenue_footfall_multiplier": 1.6, "weight": 0.24},
    "standard":  {"rent_multiplier": 1.3, "revenue_footfall_multiplier": 1.15, "weight": 0.48},
    "secondary": {"rent_multiplier": 0.75, "revenue_footfall_multiplier": 0.80, "weight": 0.28},
}

BASE_RENT_PER_M2 = 550_000       # VND / m2 / thang, muc gia goc truoc khi nhan he so
BASE_REVENUE_PER_M2_MONTH = 9_500_000  # VND doanh thu baseline / m2 / thang truoc he so vi tri

SIZE_RANGE_M2 = (55, 220)        # dien tich cua hang dao dong

# Tỷ trọng kênh baseline toàn hệ thống (theo yêu cầu doanh nghiệp)
CHANNEL_BASELINE = {"dine_in": 0.50, "app": 0.20, "delivery": 0.30}

# Cac lan song mo cua hang (staggered opening waves), gan voi giai doan tang truong nong
OPENING_WAVES = [
    {"wave_start": date(2020, 6, 1), "wave_end": date(2021, 3, 31), "share": 0.24},  # dot dau: HN/HCM
    {"wave_start": date(2021, 6, 1), "wave_end": date(2022, 6, 30), "share": 0.36},  # mo rong nhanh
    {"wave_start": date(2022, 9, 1), "wave_end": date(2023, 6, 30), "share": 0.28},  # mo rong sang DN
    {"wave_start": date(2023, 9, 1), "wave_end": date(2024, 3, 31), "share": 0.12},  # dot cuoi, cham lai
]

DATA_WINDOW_END = date(2026, 7, 31)  # het khung du lieu

OUTLIER_SMALL_PRIME_PROB = 0.5  # xac suat 1 store 'prime + size nho' duoc chon lam outlier ro net


# ---------------------------------------------------------------------------
# 2. HÀM TIỆN ÍCH
# ---------------------------------------------------------------------------

def weighted_choice(options: dict):
    keys = list(options.keys())
    weights = [options[k]["weight"] for k in keys]
    return random.choices(keys, weights=weights, k=1)[0]


def random_open_date(wave):
    delta_days = (wave["wave_end"] - wave["wave_start"]).days
    offset = random.randint(0, delta_days)
    return wave["wave_start"] + timedelta(days=offset)


def clamp(value, low, high):
    return max(low, min(high, value))


# ---------------------------------------------------------------------------
# 3. SINH DANH SÁCH STORE
# ---------------------------------------------------------------------------

def build_store_list():
    stores = []
    store_seq = 1

    for city_name, city_cfg in CITIES.items():
        n = city_cfg["store_count"]

        # phan bo location tier cho tung thanh pho theo trong so chung,
        # nhung dam bao it nhat 1 store prime va 1 store secondary neu n >= 3
        tier_pool = []
        for _ in range(n):
            tier_pool.append(weighted_choice(LOCATION_TIERS))
        if n >= 3:
            if "prime" not in tier_pool:
                tier_pool[0] = "prime"
            if "secondary" not in tier_pool:
                tier_pool[-1] = "secondary"

        # phan bo cac dot mo cua theo trong so wave, dam bao it nhat 1-2 store o dot dau
        wave_pool = []
        remaining = n
        for i, wave in enumerate(OPENING_WAVES):
            if i == len(OPENING_WAVES) - 1:
                count = remaining
            else:
                count = round(n * wave["share"])
                count = min(count, remaining)
            wave_pool.extend([wave] * count)
            remaining -= count
        while len(wave_pool) < n:
            wave_pool.append(OPENING_WAVES[0])
        random.shuffle(wave_pool)

        for i in range(n):
            location_tier = tier_pool[i]
            wave = wave_pool[i]
            open_dt = random_open_date(wave)

            # size: store prime co xu huong nho hon (mat bang dat -> thu nho dien tich)
            if location_tier == "prime":
                size_m2 = random.randint(SIZE_RANGE_M2[0], 130)
            elif location_tier == "secondary":
                size_m2 = random.randint(90, SIZE_RANGE_M2[1])
            else:
                size_m2 = random.randint(70, 180)

            store_code = f"{city_cfg['code']}-{i+1:02d}"
            store_id = store_seq
            store_seq += 1

            stores.append({
                "store_id": store_id,
                "store_code": store_code,
                "store_name": f"Flex Coffee & Tea - {city_name} {i+1:02d}",
                "city": city_name,
                "warehouse_region": city_cfg["warehouse_region"],
                "location_tier": location_tier,
                "size_m2": size_m2,
                "open_date": open_dt,
                "city_rent_index": city_cfg["rent_index"],
                "city_revenue_index": city_cfg["revenue_index"],
            })

    return stores


# ---------------------------------------------------------------------------
# 4. GÁN OUTLIER CÓ CHỦ ĐÍCH (store nhỏ + vị trí đẹp => rent cao, biên mỏng)
# ---------------------------------------------------------------------------

def flag_outliers(stores):
    for s in stores:
        is_small_prime = s["location_tier"] == "prime" and s["size_m2"] <= 90
        s["is_outlier_small_prime"] = bool(
            is_small_prime and random.random() < OUTLIER_SMALL_PRIME_PROB
        )

    # dam bao co it nhat 2 outlier ro net tren toan he thong de co du business case,
    # neu random chua du thi ep chon them tu cac ung vien dieu kien (prime + size nho)
    flagged = [s for s in stores if s["is_outlier_small_prime"]]
    if len(flagged) < 2:
        eligible = [s for s in stores if s["location_tier"] == "prime" and s["size_m2"] <= 90
                    and not s["is_outlier_small_prime"]]
        need = 2 - len(flagged)
        for s in eligible[:need]:
            s["is_outlier_small_prime"] = True

    return stores


# ---------------------------------------------------------------------------
# 5. TÍNH RENT, DOANH THU BASELINE, NHÂN SỰ, CHANNEL MIX
# ---------------------------------------------------------------------------

def compute_derived_attributes(stores):
    for s in stores:
        tier_cfg = LOCATION_TIERS[s["location_tier"]]
        noise_rent = random.uniform(0.85, 1.15)

        # --- RENT ---
        # outlier nho+dep: nhan them he so phu troi 1.3-1.6x de the hien "gia cao bat thuong"
        outlier_rent_bonus = random.uniform(1.3, 1.6) if s["is_outlier_small_prime"] else 1.0

        monthly_rent = (
            s["size_m2"]
            * BASE_RENT_PER_M2
            * s["city_rent_index"]
            * tier_cfg["rent_multiplier"]
            * noise_rent
            * outlier_rent_bonus
        )
        monthly_rent = round(monthly_rent / 100_000) * 100_000  # lam tron hang tram nghin

        # --- REVENUE BASELINE (thang, khi store da on dinh, chua tinh seasonality) ---
        noise_rev = random.uniform(0.88, 1.12)
        # outlier nho+dep: footfall/doanh thu tren m2 cao hon nhieu (vi tri dac dia)
        outlier_rev_bonus = random.uniform(1.4, 1.8) if s["is_outlier_small_prime"] else 1.0

        revenue_per_m2 = (
            BASE_REVENUE_PER_M2_MONTH
            * s["city_revenue_index"]
            * tier_cfg["revenue_footfall_multiplier"]
            * noise_rev
            * outlier_rev_bonus
        )
        monthly_revenue_baseline = revenue_per_m2 * s["size_m2"]
        monthly_revenue_baseline = round(monthly_revenue_baseline / 1_000_000) * 1_000_000

        # --- STAFF COUNT ---
        # co so: dien tich + dieu chinh theo doanh thu ky vong (store doanh thu cao can nhieu nhan su hon
        # du dien tich nho, dac biet outlier nho+dep co luu luong khach cao)
        base_staff = s["size_m2"] / 11.5
        revenue_factor = monthly_revenue_baseline / (BASE_REVENUE_PER_M2_MONTH * 100)  # chuan hoa tuong doi
        staff_count = base_staff * (0.7 + 0.3 * revenue_factor)
        staff_count = int(clamp(round(staff_count), 8, 24))

        # --- CHANNEL MIX (dao dong quanh baseline he thong) ---
        # prime/trung tam van phong -> app & tai cho cao hon; secondary/xa -> giao hang cao hon
        if s["location_tier"] == "prime":
            dine_in = CHANNEL_BASELINE["dine_in"] + random.uniform(0.02, 0.08)
            app = CHANNEL_BASELINE["app"] + random.uniform(0.00, 0.05)
            delivery = 1 - dine_in - app
        elif s["location_tier"] == "secondary":
            delivery = CHANNEL_BASELINE["delivery"] + random.uniform(0.03, 0.10)
            dine_in = CHANNEL_BASELINE["dine_in"] - random.uniform(0.02, 0.08)
            app = 1 - dine_in - delivery
        else:
            dine_in = CHANNEL_BASELINE["dine_in"] + random.uniform(-0.04, 0.04)
            app = CHANNEL_BASELINE["app"] + random.uniform(-0.03, 0.03)
            delivery = 1 - dine_in - app

        # outlier nho+dep: it cho ngoi (dien tich nho) -> giam ty trong dine-in, tang app/giao hang
        if s["is_outlier_small_prime"]:
            shift = random.uniform(0.08, 0.15)
            dine_in = max(0.25, dine_in - shift)
            delivery = delivery + shift * 0.5
            app = 1 - dine_in - delivery

        total = dine_in + app + delivery
        dine_in, app, delivery = dine_in / total, app / total, delivery / total

        # --- STATUS & LIFECYCLE ---
        months_alive = (DATA_WINDOW_END.year - s["open_date"].year) * 12 + (
            DATA_WINDOW_END.month - s["open_date"].month
        )
        status = "active"
        closed_date = None
        temp_closed_period = None

        s.update({
            "monthly_rent_vnd": int(monthly_rent),
            "monthly_revenue_baseline_vnd": int(monthly_revenue_baseline),
            "revenue_per_m2_vnd": int(revenue_per_m2),
            "staff_count_baseline": staff_count,
            "channel_mix_dine_in": round(dine_in, 3),
            "channel_mix_app": round(app, 3),
            "channel_mix_delivery": round(delivery, 3),
            "months_alive_at_window_end": months_alive,
            "status": status,
            "closed_date": closed_date,
            "temp_closed_period": temp_closed_period,
        })

    return stores


# ---------------------------------------------------------------------------
# 6. MÔ PHỎNG 1-2 CỬA HÀNG GẶP KHÓ KHĂN (đóng tạm/đóng hẳn) — phản ánh giai đoạn "chững lại"
# ---------------------------------------------------------------------------

def apply_lifecycle_events(stores, rng_seed=RNG_SEED):
    rng = random.Random(rng_seed + 1)

    # uu tien chon trong so store: doanh thu/m2 thap + khong phai outlier dac biet
    candidates = sorted(
        [s for s in stores if not s["is_outlier_small_prime"]],
        key=lambda s: s["revenue_per_m2_vnd"],
    )[:6]

    # 1 store dong tam thoi (sua chua / doi mat bang) trong ~2-3 thang gan cuoi ky
    temp_target = rng.choice(candidates)
    temp_start = DATA_WINDOW_END - timedelta(days=rng.randint(60, 150))
    temp_end = temp_start + timedelta(days=rng.randint(45, 75))
    temp_target["status"] = "temporarily_closed_recent"
    temp_target["temp_closed_period"] = f"{temp_start.isoformat()} to {temp_end.isoformat()}"

    # 1 store dong han (hieu qua kem, giai doan chung lai phai co store rut lui)
    remaining_candidates = [s for s in candidates if s["store_id"] != temp_target["store_id"]]
    closed_target = rng.choice(remaining_candidates)
    close_dt = DATA_WINDOW_END - timedelta(days=rng.randint(200, 400))
    closed_target["status"] = "closed"
    closed_target["closed_date"] = close_dt.isoformat()

    return stores


# ---------------------------------------------------------------------------
# 7. MAIN
# ---------------------------------------------------------------------------

def main():
    import os
    stores = build_store_list()
    stores = flag_outliers(stores)
    stores = compute_derived_attributes(stores)
    stores = apply_lifecycle_events(stores)

    df = pd.DataFrame(stores)
    df["open_date"] = df["open_date"].astype(str)

    # Tach temp_closed_period thanh 2 cot rieng cho khop SQL schema v1.3
    def parse_temp_closed(period_str):
        if not period_str or str(period_str) == "None":
            return None, None
        parts = str(period_str).split(" to ")
        return parts[0].strip(), parts[1].strip() if len(parts) == 2 else (None, None)

    df["temp_close_start"], df["temp_close_end"] = zip(
        *df["temp_closed_period"].apply(parse_temp_closed)
    )

    # sap xep cot cho de doc va khop voi dim_store schema
    col_order = [
        "store_id", "store_code", "store_name", "city", "warehouse_region",
        "location_tier", "size_m2", "open_date", "status", "closed_date",
        "temp_close_start", "temp_close_end",
        "is_outlier_small_prime",
        "monthly_rent_vnd", "monthly_revenue_baseline_vnd", "revenue_per_m2_vnd",
        "staff_count_baseline",
        "channel_mix_dine_in", "channel_mix_app", "channel_mix_delivery",
        "months_alive_at_window_end",
    ]
    df = df[col_order]

    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

    project_root = config.PROJECT_ROOT
    out_dict = os.path.join(project_root, "data", "dictionary")
    os.makedirs(out_dict, exist_ok=True)

    config.save_dimension(df, "dim_store.csv")

    with open(os.path.join(out_dict, "store_profiles_v1.json"), "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2, default=str)

    print(f"[OK] store_profiles_v1.json -> {out_dict}")
    return df


if __name__ == "__main__":
    df = main()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False))