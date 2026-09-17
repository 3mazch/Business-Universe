import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import random
import os

RNG_SEED = 42
random.seed(RNG_SEED)
np.random.seed(RNG_SEED)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
OUT_DIR = config.DIM_FULL_DIR

DATA_WINDOW_START = date(2020, 1, 1) # Keep window wide enough for early campaigns
DATA_WINDOW_END = date(2026, 12, 31)

def daterange_overlaps_window(start, end):
    if isinstance(start, str): start = date.fromisoformat(start)
    if isinstance(end, str): end = date.fromisoformat(end)
    return not (end < DATA_WINDOW_START or start > DATA_WINDOW_END)

def try_load_csv(path, **kwargs):
    try:
        return pd.read_csv(path, **kwargs)
    except FileNotFoundError:
        return None

# ---------------------------------------------------------
# 1. GENERATE DIM_DATE
# ---------------------------------------------------------
def generate_dim_date():
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2026, 12, 31)
    
    date_range = pd.date_range(start_date, end_date)
    df_date = pd.DataFrame({'date': date_range})
    
    df_date['date_key'] = df_date['date'].dt.strftime('%Y%m%d').astype(int)
    df_date['year'] = df_date['date'].dt.year
    df_date['month'] = df_date['date'].dt.month
    df_date['day'] = df_date['date'].dt.day
    df_date['day_of_week'] = df_date['date'].dt.dayofweek + 1
    df_date['is_weekend'] = df_date['day_of_week'].isin([6, 7]).astype(int)
    
    tet_holidays = [
        ('2020-01-24', '2020-01-29'),
        ('2021-02-11', '2021-02-16'),
        ('2022-01-31', '2022-02-04'),
        ('2023-01-21', '2023-01-26'),
        ('2024-02-09', '2024-02-14'),
        ('2025-01-28', '2025-02-02'),
        ('2026-02-16', '2026-02-21')
    ]
    
    df_date['is_holiday'] = 0
    df_date['holiday_name'] = ""
    
    for index, row in df_date.iterrows():
        m, d = row['month'], row['day']
        y = row['year']
        
        holiday = None
        if m == 1 and d == 1:
            holiday = "New Year"
        elif m == 4 and d == 30:
            holiday = "Reunification Day"
        elif m == 5 and d == 1:
            holiday = "Labor Day"
        elif m == 9 and d == 2:
            holiday = "National Day"
            
        if y >= 2025 and m == d and m in [1,2,3,4,5,6,7,8,9,10,11,12]:
            holiday = f"Double Day {m}/{d}"
            
        if holiday:
            df_date.at[index, 'is_holiday'] = 1
            df_date.at[index, 'holiday_name'] = holiday
            
    for start, end in tet_holidays:
        mask = (df_date['date'] >= start) & (df_date['date'] <= end)
        df_date.loc[mask, 'is_holiday'] = 1
        df_date.loc[mask, 'holiday_name'] = "Tet Holiday"
        
    df_date['date'] = df_date['date'].dt.strftime('%Y-%m-%d')
    return df_date

# ---------------------------------------------------------
# 2. GENERATE DIM_SALES_CHANNEL
# ---------------------------------------------------------
def generate_dim_sales_channel():
    channels = [
        (1, "POS", "dine_in", "2020-01-01"),
        (2, "ShopeeFood", "delivery", "2022-06-01"),
        (3, "Grab", "delivery", "2021-03-01"),
        (4, "App", "app", "2025-01-01"),
        (5, "BeFood", "delivery", "2025-06-01"),
        (6, "GreenSM", "delivery", "2026-01-01")
    ]
    return pd.DataFrame(channels, columns=['channel_id', 'channel_name', 'channel_group', 'launch_date'])

# ---------------------------------------------------------
# 3. GENERATE DIM_CAMPAIGN (User suggested logic + Current LTOs)
# ---------------------------------------------------------
def build_lto_campaigns(start_id, df_product_lookup=None):
    rows = []
    campaign_id = start_id
    
    ltos = [
        ("Tra Sua Tran Chau Duong Den Nuong", "2023-07-01", "2023-09-30"),
        ("Chocolate Latte Hanh Nhan", "2023-10-01", "2023-12-31"),
        ("Latte Hoa Dao", "2024-01-01", "2024-03-31"),
        ("Cold Brew Cam Sa", "2024-04-01", "2024-06-30"),
        ("Ca Phe Cot Dua Com Xanh", "2024-07-01", "2024-09-30"),
        ("Tra Que Tao Do", "2024-10-01", "2024-12-31"),
        ("Tra O Long Buoi Mat Ong", "2025-01-01", "2025-03-31"),
        ("Tra Xanh Dua Hau", "2025-04-01", "2025-06-30"),
        ("Ca phe Muoi Tran Chau", "2025-07-01", "2025-09-30"),
        ("Latte Cam Que", "2025-10-01", "2025-12-31"),
        ("Tra Lai Mam Xoi", "2026-01-01", "2026-03-31"),
        ("Tra Dua Tran Chau", "2026-04-01", "2026-06-30"),
        ("Cold Brew Sau Mua Thu", "2026-07-01", "2026-09-30"),
    ]

    for product_name, launch_str, disc_str in ltos:
        launch = date.fromisoformat(launch_str)
        discontinued = date.fromisoformat(disc_str)

        if not daterange_overlaps_window(launch, discontinued):
            continue

        linked_id = None
        if df_product_lookup is not None:
            match = df_product_lookup[df_product_lookup["product_name"] == product_name]
            if not match.empty:
                linked_id = int(match.iloc[0]["product_id"])

        rows.append({
            "campaign_id": campaign_id,
            "campaign_name": f"LTO - {product_name}",
            "campaign_type": "seasonal",
            "start_date": launch.isoformat(),
            "end_date": discontinued.isoformat(),
            "scope_type": "system",
            "scope_store_id": None,
            "scope_channel_id": None,
            "linked_product_id": linked_id,
            "linked_product_name": product_name,
            "discount_value": None,
            "funding_source": "flex_funded",
            "budget_vnd": random.randint(15_000_000, 35_000_000),
            "expected_uplift_pct": round(random.uniform(10, 22), 1),
            "priority": 30,
        })
        campaign_id += 1

    return rows, campaign_id

def build_holiday_campaigns(start_id):
    rows = []
    campaign_id = start_id
    years_in_window = list(range(2023, 2027))

    HOLIDAY_TEMPLATES = [
        ("Womens Day", (3, 6), (3, 8), 20.0),
        ("Reunification", (4, 28), (5, 2), 25.0),
        ("Childrens Day", (6, 1), (6, 1), 20.0),
        ("Summer Vibes", (6, 15), (7, 15), 15.0),
        ("Back to School", (8, 15), (9, 5), 15.0),
        ("National Day", (9, 1), (9, 3), 20.0),
        ("Christmas & NYE", (12, 20), (12, 31), 20.0),
    ]

    TET_LUNAR_DATES = {
        2024: ("2024-02-09", "2024-02-14"),
        2025: ("2025-01-28", "2025-02-02"),
        2026: ("2026-02-16", "2026-02-21"),
    }

    for year in years_in_window:
        for name, (m1, d1), (m2, d2), pct in HOLIDAY_TEMPLATES:
            try:
                start = date(year, m1, d1)
                end = date(year, m2, d2) if (m2, d2) >= (m1, d1) else date(year, m2, d2)
            except ValueError:
                continue
            if end < start: end = start
            if not daterange_overlaps_window(start, end): continue

            rows.append({
                "campaign_id": campaign_id,
                "campaign_name": f"{name} {year}",
                "campaign_type": "percent_discount",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "scope_type": "system",
                "scope_store_id": None,
                "scope_channel_id": None,
                "linked_product_id": None,
                "linked_product_name": None,
                "discount_value": pct,
                "funding_source": "flex_funded",
                "budget_vnd": random.randint(20_000_000, 60_000_000),
                "expected_uplift_pct": round(pct * random.uniform(0.9, 1.3), 1),
                "priority": 50,
            })
            campaign_id += 1

        if year in TET_LUNAR_DATES:
            s, e = TET_LUNAR_DATES[year]
            rows.append({
                "campaign_id": campaign_id,
                "campaign_name": f"Tet Nguyen Dan {year}",
                "campaign_type": "percent_discount",
                "start_date": s, "end_date": e,
                "scope_type": "system", "scope_store_id": None, "scope_channel_id": None,
                "linked_product_id": None, "linked_product_name": None,
                "discount_value": 15.0,
                "funding_source": "flex_funded",
                "budget_vnd": random.randint(40_000_000, 80_000_000),
                "expected_uplift_pct": round(random.uniform(25, 40), 1),
                "priority": 60,
            })
            campaign_id += 1

    return rows, campaign_id

def build_bogo_campaigns(start_id):
    rows = []
    campaign_id = start_id
    years_in_window = list(range(2023, 2027))
    BOGO_MONTHS = [2, 5, 8, 11]

    for year in years_in_window:
        for month in BOGO_MONTHS:
            start = date(year, month, 10)
            end = start + timedelta(days=6)
            if not daterange_overlaps_window(start, end): continue
            rows.append({
                "campaign_id": campaign_id,
                "campaign_name": f"BOGO Tuan Le {month:02d}/{year}",
                "campaign_type": "bogo",
                "start_date": start.isoformat(), "end_date": end.isoformat(),
                "scope_type": "system", "scope_store_id": None, "scope_channel_id": None,
                "linked_product_id": None, "linked_product_name": None,
                "discount_value": None,
                "funding_source": "flex_funded",
                "budget_vnd": random.randint(25_000_000, 45_000_000),
                "expected_uplift_pct": round(random.uniform(30, 45), 1),
                "priority": 70,
            })
            campaign_id += 1
    return rows, campaign_id

def build_flash_sale_campaigns(start_id):
    rows = []
    campaign_id = start_id
    for year in [2025, 2026]:
        for m in [1,2,3,4,5,6,7,8,9,10,11,12]:
            dt = date(year, m, m)
            if not daterange_overlaps_window(dt, dt): continue
            rows.append({
                "campaign_id": campaign_id,
                "campaign_name": f"Double Day {m}/{m} - {year}",
                "campaign_type": "flash_sale",
                "start_date": dt.isoformat(), "end_date": dt.isoformat(),
                "scope_type": "system", "scope_store_id": None, "scope_channel_id": None,
                "linked_product_id": None, "linked_product_name": None,
                "discount_value": 25.0,
                "funding_source": "flex_funded",
                "budget_vnd": random.randint(10_000_000, 25_000_000),
                "expected_uplift_pct": round(random.uniform(45, 70), 1),
                "priority": 100,
            })
            campaign_id += 1
    return rows, campaign_id

def build_app_launch_campaign(start_id, df_channel_lookup=None):
    campaign_id = start_id
    channel_id = 4
    if df_channel_lookup is not None:
        match = df_channel_lookup[df_channel_lookup["channel_name"] == "App"]
        if not match.empty:
            channel_id = int(match.iloc[0]["channel_id"])

    row = {
        "campaign_id": campaign_id,
        "campaign_name": "Flex App Mega Launch",
        "campaign_type": "percent_discount",
        "start_date": "2025-01-01", "end_date": "2025-01-31",
        "scope_type": "channel", "scope_store_id": None, "scope_channel_id": channel_id,
        "linked_product_id": None, "linked_product_name": None,
        "discount_value": 35.0,
        "funding_source": "flex_funded",
        "budget_vnd": 150_000_000,
        "expected_uplift_pct": 80.0,
        "priority": 90,
    }
    return [row], campaign_id + 1

def build_delivery_platform_campaigns(start_id, df_channel_lookup=None):
    rows = []
    campaign_id = start_id
    DELIVERY_CHANNEL_NAMES = ["Grab", "ShopeeFood", "BeFood", "GreenSM"]
    
    for year in range(2023, 2027):
        for i, channel_name in enumerate(DELIVERY_CHANNEL_NAMES):
            month = 3 + (i * 2) % 10
            start = date(year, month, 1)
            end = start + timedelta(days=13)
            if not daterange_overlaps_window(start, end): continue

            channel_id = None
            if df_channel_lookup is not None:
                match = df_channel_lookup[df_channel_lookup["channel_name"] == channel_name]
                if not match.empty:
                    channel_id = int(match.iloc[0]["channel_id"])

            rows.append({
                "campaign_id": campaign_id,
                "campaign_name": f"{channel_name} Voucher Doi Tac Q{(month-1)//3 + 1}/{year}",
                "campaign_type": "percent_discount",
                "start_date": start.isoformat(), "end_date": end.isoformat(),
                "scope_type": "channel", "scope_store_id": None, "scope_channel_id": channel_id,
                "linked_product_id": None, "linked_product_name": None,
                "discount_value": 30.0,
                "funding_source": "shared",
                "budget_vnd": 0,
                "expected_uplift_pct": round(random.uniform(20, 35), 1),
                "priority": 40,
            })
            campaign_id += 1
    return rows, campaign_id

def build_grand_opening_campaigns(start_id, df_store=None):
    rows = []
    campaign_id = start_id
    if df_store is None: return rows, campaign_id

    for _, s in df_store.iterrows():
        open_dt = pd.to_datetime(s["open_date"]).date()
        end_dt = open_dt + timedelta(days=13)
        if not daterange_overlaps_window(open_dt, end_dt): continue
        rows.append({
            "campaign_id": campaign_id,
            "campaign_name": f"Grand Opening - {s['store_name']}",
            "campaign_type": "percent_discount",
            "start_date": open_dt.isoformat(), "end_date": end_dt.isoformat(),
            "scope_type": "store", "scope_store_id": int(s["store_id"]), "scope_channel_id": None,
            "linked_product_id": None, "linked_product_name": None,
            "discount_value": 30.0,
            "funding_source": "flex_funded",
            "budget_vnd": random.randint(20_000_000, 40_000_000),
            "expected_uplift_pct": round(random.uniform(60, 90), 1),
            "priority": 95,
        })
        campaign_id += 1
    return rows, campaign_id

def generate_dim_campaign(df_product_bev, df_channel, df_store):
    all_rows = []
    rows, next_id = build_lto_campaigns(1, df_product_bev)
    all_rows.extend(rows)
    rows, next_id = build_holiday_campaigns(next_id)
    all_rows.extend(rows)
    rows, next_id = build_bogo_campaigns(next_id)
    all_rows.extend(rows)
    rows, next_id = build_flash_sale_campaigns(next_id)
    all_rows.extend(rows)
    rows, next_id = build_app_launch_campaign(next_id, df_channel)
    all_rows.extend(rows)
    rows, next_id = build_delivery_platform_campaigns(next_id, df_channel)
    all_rows.extend(rows)
    rows, next_id = build_grand_opening_campaigns(next_id, df_store)
    all_rows.extend(rows)

    df_campaign = pd.DataFrame(all_rows)
    df_campaign = df_campaign.sort_values("start_date").reset_index(drop=True)
    df_campaign["campaign_id"] = range(1, len(df_campaign) + 1)
    
    col_order = [
        "campaign_id", "campaign_name", "campaign_type", "start_date", "end_date",
        "scope_type", "scope_store_id", "scope_channel_id",
        "linked_product_id", "linked_product_name",
        "discount_value", "funding_source", "budget_vnd", "expected_uplift_pct", "priority"
    ]
    return df_campaign[col_order]

# ---------------------------------------------------------
# 4. GENERATE DIM_CUSTOMER
# ---------------------------------------------------------
def generate_dim_customer(num_customers=15000):
    years = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
    probs = [0.05, 0.10, 0.12, 0.15, 0.15, 0.30, 0.13]
    
    year_choices = np.random.choice(years, size=num_customers, p=probs)
    
    first_names = ["Anh", "Binh", "Chau", "Dung", "Em", "Giang", "Hai", "Linh", "Minh", "Nam", "Phong", "Quang", "Son", "Trang", "Tuan", "Vy", "Yen"]
    last_names = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Huynh", "Phan", "Vu", "Vo", "Dang", "Bui", "Do", "Ho", "Ngo", "Duong"]
    
    customers = []
    for i in range(num_customers):
        y = year_choices[i]
        
        if y == 2025 and random.random() < 0.4: 
            start_dt = datetime(2025, 1, 1)
            days = 30
        else:
            start_dt = datetime(y, 1, 1)
            days = 364 if y != 2020 else 365
            
        reg_date = start_dt + timedelta(days=random.randint(0, days))
        
        if y < 2025:
            reg_channel = "pos"
        else:
            reg_channel = "app" if random.random() < 0.8 else "pos"
            
        phone = f"09{random.randint(10000000, 99999999)}"
        email = f"customer_{i+1}@example.com" if random.random() < 0.3 else ""
        home_store = random.randint(1, 25)
        
        customers.append({
            'customer_id': i + 1,
            'full_name': f"{random.choice(last_names)} {random.choice(first_names)}",
            'phone_number': phone,
            'email': email,
            'registration_date': reg_date.strftime('%Y-%m-%d'),
            'registration_channel': reg_channel,
            'home_store_id': home_store,
            'current_tier_id': ''
        })
        
    return pd.DataFrame(customers)

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    print("Generating minor dimensions...")
    df_date = generate_dim_date()
    df_channel = generate_dim_sales_channel()
    
    df_product_bev = try_load_csv(os.path.join(OUT_DIR, "dim_product_beverage.csv"))
    df_store = try_load_csv(os.path.join(OUT_DIR, "dim_store.csv"))
    
    df_campaign = generate_dim_campaign(df_product_bev, df_channel, df_store)
    df_customer = generate_dim_customer(12000)
    
    config.save_dimension(df_date, "dim_date.csv")
    config.save_dimension(df_channel, "dim_sales_channel.csv")
    config.save_dimension(df_campaign, "dim_campaign.csv")
    config.save_dimension(df_customer, "dim_customer.csv")
    
    print(f"Generated {len(df_date)} dates.")
    print(f"Generated {len(df_channel)} sales channels.")
    print(f"Generated {len(df_campaign)} campaigns.")
    print(f"Generated {len(df_customer)} customers.")
    
    print("\nChannels:")
    print(df_channel)
    print("\nCampaigns (sample):")
    print(df_campaign.head(10))
