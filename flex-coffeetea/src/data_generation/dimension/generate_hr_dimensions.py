"""
Flex Coffee & Tea — Generator: HR Dimension Data
=================================================
Sinh du lieu:
- dim_position: 4 vi tri (Quan ly / Pha che / Thu ngan / Phuc vu) + luong chuan
- dim_shift: ca lam chuan (Ca sang / Ca chieu / Ca gay-part-time)
- dim_employee: nhan vien theo tung store, so luong = staff_count_baseline (Store Profile),
  co mo phong TURNOVER (nghi viec + tuyen thay the) xuyen suot vong doi store.

Nguon input: store_profiles_v1.csv (Buoc 1).
Nguon logic: BRS v1.2 Domain 7 (HR).
"""

import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

RNG_SEED = 42
random.seed(RNG_SEED)
np.random.seed(RNG_SEED)

DATA_WINDOW_END = date(2026, 7, 31)

# ---------------------------------------------------------------------------
# 1. DIM_POSITION
# ---------------------------------------------------------------------------
POSITIONS = [
    # (ten, luong chuan/thang full_time, VND)
    ("Quan ly", 11_000_000),
    ("Pha che", 6_800_000),
    ("Thu ngan", 6_200_000),
    ("Phuc vu", 5_800_000),
]

# ty le contract_type theo vi tri: (pct full_time)
CONTRACT_FULLTIME_PCT = {
    "Quan ly": 1.00,
    "Pha che": 0.75,
    "Thu ngan": 0.65,
    "Phuc vu": 0.30,   # da so part-time (sinh vien lam gio cao diem)
}

# tenure trung binh (thang) truoc khi nghi viec -- dung cho exponential distribution
MEAN_TENURE_MONTHS = {
    "Quan ly": 30,
    "Pha che": 15,
    "Thu ngan": 13,
    "Phuc vu": 9,      # turnover cao nhat, dung voi dac thu F&B/part-time
}
MEAN_TENURE_PARTTIME_ADJUST = 0.75  # part-time nghi som hon full-time cung vi tri ~25%
MIN_TENURE_MONTHS = 1.5

# ---------------------------------------------------------------------------
# 2. DIM_SHIFT
# ---------------------------------------------------------------------------
SHIFTS = [
    # (ten, gio bat dau, gio ket thuc, tong so gio, luong/ca, bonus)
    ("Ca sang", "06:00", "14:00", 8.0, 280_000, 0),
    ("Ca chieu", "14:00", "22:00", 8.0, 300_000, 20_000),   # bonus nhe ca chieu toi
    ("Ca gay 1(part-time)", "7:00", "11:00", 4.0, 150_000, 0),
    ("Ca gay 2(part-time)", "12:00", "16:00", 4.0, 150_000, 0),
    ("Ca gay 3(part-time)", "18:00", "22:00", 4.0, 160_000, 0),
]

# ---------------------------------------------------------------------------
# 3. HÀM SINH TÊN GIẢ (Việt hóa, tái sử dụng random)
# ---------------------------------------------------------------------------
SURNAMES = ["Nguyen", "Tran", "Le", "Pham", "Hoang", "Huynh", "Vu", "Vo", "Dang", "Bui",
            "Do", "Ho", "Ngo", "Duong", "Ly"]
MIDDLE_MALE = ["Van", "Minh", "Quoc", "Anh", "Duc", "Thanh"]
MIDDLE_FEMALE = ["Thi", "Ngoc", "Thu", "Kim", "My", "Hong"]
GIVEN_MALE = ["Nam", "Hung", "Long", "Khang", "Phong", "Tuan", "Son", "Bao", "Dat", "Kien"]
GIVEN_FEMALE = ["Linh", "Trang", "Anh", "Huong", "Mai", "Ngan", "Chi", "Thao", "Ha", "Yen"]


def random_name():
    is_male = random.random() < 0.5
    surname = random.choice(SURNAMES)
    if is_male:
        return f"{surname} {random.choice(MIDDLE_MALE)} {random.choice(GIVEN_MALE)}"
    return f"{surname} {random.choice(MIDDLE_FEMALE)} {random.choice(GIVEN_FEMALE)}"


# ---------------------------------------------------------------------------
# 4. XÁC ĐỊNH CƠ CẤU VỊ TRÍ THEO STORE (dựa trên staff_count_baseline + channel_mix)
# ---------------------------------------------------------------------------

def determine_position_slots(staff_count, delivery_ratio):
    """Tra ve dict {position_name: so luong slot} cho 1 store."""
    n_manager = 1
    remaining = max(staff_count - n_manager, 4)  # dam bao toi thieu co nhan vien van hanh

    # store nhieu delivery -> can nhieu pha che hon (it can phuc vu ban/don ban)
    pha_che_ratio = 0.42 + delivery_ratio * 0.15   # dao dong ~0.42-0.55
    thu_ngan_ratio = 0.23
    phuc_vu_ratio = 1 - pha_che_ratio - thu_ngan_ratio

    n_pha_che = max(round(remaining * pha_che_ratio), 2)
    n_thu_ngan = max(round(remaining * thu_ngan_ratio), 1)
    n_phuc_vu = max(remaining - n_pha_che - n_thu_ngan, 1)

    return {"Quan ly": n_manager, "Pha che": n_pha_che, "Thu ngan": n_thu_ngan, "Phuc vu": n_phuc_vu}


# ---------------------------------------------------------------------------
# 5. MÔ PHỎNG TURNOVER CHAIN CHO 1 SLOT VỊ TRÍ TẠI 1 STORE
# ---------------------------------------------------------------------------

def simulate_turnover_chain(store_id, position_name, slot_seq, start_date, end_date_cap):
    """Sinh chuoi nhan vien noi tiep nhau lap day 1 'slot' vi tri tu start_date den end_date_cap.
    Tra ve list cac dict nhan vien."""
    employees = []
    current_hire = start_date

    while current_hire < end_date_cap:
        contract_type = "full_time" if random.random() < CONTRACT_FULLTIME_PCT[position_name] else "part_time"

        mean_tenure = MEAN_TENURE_MONTHS[position_name]
        if contract_type == "part_time":
            mean_tenure *= MEAN_TENURE_PARTTIME_ADJUST

        tenure_months = max(np.random.exponential(mean_tenure), MIN_TENURE_MONTHS)
        tenure_days = int(tenure_months * 30.44)
        tentative_termination = current_hire + timedelta(days=tenure_days)

        if tentative_termination >= end_date_cap:
            employees.append({
                "store_id": store_id, "position_name": position_name, "slot_seq": slot_seq,
                "full_name": random_name(), "hire_date": current_hire,
                "termination_date": None, "contract_type": contract_type,
            })
            break
        else:
            employees.append({
                "store_id": store_id, "position_name": position_name, "slot_seq": slot_seq,
                "full_name": random_name(), "hire_date": current_hire,
                "termination_date": tentative_termination, "contract_type": contract_type,
            })
            gap_days = random.randint(5, 20)
            current_hire = tentative_termination + timedelta(days=gap_days)

    return employees


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------

def build_position_table():
    return pd.DataFrame([
        {"position_id": i, "position_name": name, "standard_monthly_salary_vnd": salary}
        for i, (name, salary) in enumerate(POSITIONS, start=1)
    ])


def build_shift_table():
    return pd.DataFrame([
        {
            "shift_id": i, "shift_name": name, "standard_start_time": start,
            "standard_end_time": end, "total_hours": hours,
            "pay_per_shift_vnd": pay, "bonus_vnd": bonus,
        }
        for i, (name, start, end, hours, pay, bonus) in enumerate(SHIFTS, start=1)
    ])


def build_employee_table(df_store):
    all_employees = []

    for _, s in df_store.iterrows():
        store_id = s["store_id"]
        staff_count = int(s["staff_count_baseline"])
        delivery_ratio = float(s["channel_mix_delivery"])
        open_date = pd.to_datetime(s["open_date"]).date()

        closed_val = s.get("closed_date")
        if pd.notna(closed_val) and str(closed_val).strip() not in ("", "nan", "None"):
            end_cap = pd.to_datetime(closed_val).date()
        else:
            end_cap = DATA_WINDOW_END

        slots = determine_position_slots(staff_count, delivery_ratio)

        for position_name, n_slots in slots.items():
            for slot_seq in range(1, n_slots + 1):
                chain = simulate_turnover_chain(store_id, position_name, slot_seq, open_date, end_cap)
                all_employees.extend(chain)

    pos_map = {name: i for i, (name, _) in enumerate(POSITIONS, start=1)}
    rows = []
    employee_id_seq = 1
    for emp in all_employees:
        rows.append({
            "employee_id": employee_id_seq,
            "full_name": emp["full_name"],
            "position_id": pos_map[emp["position_name"]],
            "position_name": emp["position_name"],
            "store_id": emp["store_id"],
            "hire_date": emp["hire_date"],
            "termination_date": emp["termination_date"],
            "contract_type": emp["contract_type"],
            "slot_seq": emp["slot_seq"],
        })
        employee_id_seq += 1

    return pd.DataFrame(rows)


def main():
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config
    
    out_dir = config.DIM_FULL_DIR
    
    df_store = pd.read_csv(os.path.join(out_dir, "dim_store.csv"))

    df_position = build_position_table()
    df_shift = build_shift_table()
    df_employee = build_employee_table(df_store)

    config.save_dimension(df_position, "dim_position.csv")
    config.save_dimension(df_shift, "dim_shift.csv")
    config.save_dimension(df_employee, "dim_employee.csv")

    return df_position, df_shift, df_employee, df_store


if __name__ == "__main__":
    df_position, df_shift, df_employee, df_store = main()

    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 220)

    print("=== DIM_POSITION ===")
    print(df_position.to_string(index=False))

    print("\n=== DIM_SHIFT ===")
    print(df_shift.to_string(index=False))

    print(f"\n=== DIM_EMPLOYEE: TONG {len(df_employee)} dong (bao gom ca lich su turnover) ===")
    print(df_employee.head(15).to_string(index=False))

    print("\n=== SO NHAN VIEN DANG LAM VIEC (chua nghi) TAI THOI DIEM CUOI KHUNG DU LIEU ===")
    active_now = df_employee[df_employee["termination_date"].isna()]
    print(f"Tong nhan vien active: {len(active_now)}")
    per_store = active_now.groupby("store_id").size()
    print(f"Trung binh nhan vien active/store: {per_store.mean():.1f} "
          f"(so voi staff_count_baseline trung binh: {df_store['staff_count_baseline'].mean():.1f})")

    print("\n=== PHAN BO VI TRI (toan bo lich su) ===")
    print(df_employee["position_name"].value_counts())

    print("\n=== PHAN BO CONTRACT TYPE ===")
    print(df_employee["contract_type"].value_counts())

    print("\n=== KIEM TRA TURNOVER (so nguoi trung binh / slot xuyen suot vong doi store) ===")
    n_slots_total = df_employee.groupby(["store_id", "position_name", "slot_seq"]).ngroups
    avg_chain_length = len(df_employee) / n_slots_total
    print(f"So slot vi tri (store x position x slot_seq): {n_slots_total}")
    print(f"Trung binh so nguoi/slot xuyen suot vong doi store: {avg_chain_length:.2f}")

    print(f"\n=== SAMPLE: turnover chain cho 1 slot cu the (store_id=1, Pha che, slot 1) ===")
    sample = df_employee[(df_employee["store_id"] == 1) & (df_employee["position_name"] == "Pha che")
                          & (df_employee["slot_seq"] == 1)]
    print(sample[["employee_id", "full_name", "hire_date", "termination_date", "contract_type"]].to_string(index=False))