"""
constants.py — Single source of truth for all generation parameters.
Flex Coffee & Tea Data Generation Engine v1.0
"""
from datetime import date

# ===========================================================================
# SIMULATION WINDOW
# ===========================================================================
DATA_SIM_START  = date(2023, 8, 1)
DATA_SIM_END    = date(2026, 7, 31)
BASELINE_ANCHOR = date(2025, 12, 1)   # Dec 2025 = 1.0 for all store baselines

# ===========================================================================
# PRICE FACTOR (base_price_vnd = Dec 2025 reference)
# ===========================================================================
PRICE_FACTOR = {2023: 0.85, 2024: 0.95, 2025: 1.00, 2026: 1.10}

# ===========================================================================
# CHANNEL FEES (phần cửa hàng chịu — không trừ vào bill khách)
# ===========================================================================
CHANNEL_FEE = {
    "ShopeeFood": 0.15,
    "Grab":       0.20,
    "BeFood":     0.20,
    "GreenSM":    0.00,
    "App":        0.00,
    "POS":        0.00,
}

PAYMENT_SURCHARGE = {
    "cash":    0.00,
    "card":    0.02,
    "ewallet": 0.02,
    "qr":      0.02,
}

# ===========================================================================
# CHANNEL → PAYMENT METHOD DISTRIBUTION
# ===========================================================================
PAYMENT_DIST = {
    "POS":        {"cash": 0.50, "card": 0.30, "qr": 0.20},
    "App":        {"ewallet": 0.60, "qr": 0.30, "card": 0.10},
    # 3rd-party delivery: 100% ewallet (platform handles)
    "ShopeeFood": {"ewallet": 1.00},
    "Grab":       {"ewallet": 1.00},
    "BeFood":     {"ewallet": 1.00},
    "GreenSM":    {"ewallet": 1.00},
}

# ===========================================================================
# ORDER TYPE DISTRIBUTION (base — adjusted per-store by engine)
# ===========================================================================
ORDER_TYPE_DIST_BASE = {
    "POS": {"dine_in": 0.75, "takeaway": 0.25},
    "App": {"dine_in": 0.50, "takeaway": 0.30, "delivery": 0.20},
    # 3rd party: 100% delivery (handled separately)
}

# ===========================================================================
# ORDER STATUS DISTRIBUTION
# ===========================================================================
ORDER_STATUS_DIST = {"completed": 0.97, "canceled": 0.02, "refunded": 0.01}
# Tháng cao điểm (Tết, campaign lớn): canceled có thể lên 0.03–0.04

# ===========================================================================
# LOYALTY RULES
# ===========================================================================
LOYALTY_VND_PER_POINT = 10_000        # 1 point / 10.000 VND net
LOYALTY_APP_BONUS_YEAR = 2025         # năm duy nhất App bonus ×1.5
LOYALTY_APP_BONUS_MULTIPLIER = 1.5
REDEMPTION_WINDOW_MONTHS = 3          # 20% customers đủ điểm redeem trong 3 tháng
REDEMPTION_RATE = 0.20

# ===========================================================================
# MEMBERSHIP TIER THRESHOLDS (rolling 12-month net spend)
# ===========================================================================
TIER_THRESHOLDS = {
    "TIER-1": 0,
    "TIER-2": 3_000_000,
    "TIER-3": 10_000_000,
}

# ===========================================================================
# STORE SEGMENT MATURITY DEFINITIONS
# ===========================================================================
# Tuổi store (tháng) tại DATA_SIM_START (2023-06-01)
SEGMENT_THRESHOLDS = {
    "A-Mature":      (24, 999),  # ≥ 24 tháng
    "B-Established": (12, 23),   # 12–23 tháng
    "C-Young":       (0, 11),    # 0–11 tháng
    "D-NewInSim":    (-999, -1), # chưa mở tại sim_start
}

# M(T) starting level tại sim_start
MATURITY_START_LEVEL = {
    "A-Mature":      1.00,          # fully stable
    "B-Established": (0.78, 0.85),  # building phase
    "C-Young":       (0.68, 0.78),  # brand-aware but new
    "D-NewInSim":    None,          # depends on open_date
}

# Tốc độ tăng M(T) per month (linear until reach 1.0)
MATURITY_RAMP_RATE = {
    "A-Mature":      0.00,   # stable
    "B-Established": 0.025,  # +2.5%/tháng → ~1.0 sau 8–10 tháng
    "C-Young":       0.018,  # +1.8%/tháng → ~1.0 sau 15–18 tháng
    "D-NewInSim":    0.015,  # ~1.0 sau 18–22 tháng
}

# ===========================================================================
# NEW STORE NOVELTY CURVE (dùng cho D-NewInSim và C-Young tháng khai trương)
# ===========================================================================
# months_since_open → novelty multiplier
NEW_STORE_NOVELTY = {
    0: 1.10,   # tháng khai trương: grand opening boost
    1: 1.05,   # tháng 2: vẫn còn buzz
    2: 0.90,   # tháng 3: novelty qua, dip
    3: 0.88,   # tháng 4: ổn định thấp
    4: 0.92,   # tháng 5
    5: 0.95,   # tháng 6
    # tháng 7+: M(T) maturity curve takes over
}

# ===========================================================================
# OUTLIER STORE OVERRIDES
# ===========================================================================
OUTLIER_STORE_AOV_MULTIPLIER = {
    2: 1.25,   # store_id=2 (HN-02): prime nhỏ, AOV cao
    4: 1.20,   # store_id=4 (HN-04): prime nhỏ, AOV cao
}

# ===========================================================================
# HCM-02 DECLINE PARAMETERS (store_id=12, closed 2025-09-16)
# ===========================================================================
HCM02_DECLINE_START    = date(2025, 4, 1)   # bắt đầu decline từ tháng 4/2025
HCM02_CLOSED_DATE      = date(2025, 9, 16)
HCM02_DECLINE_M_START  = 1.00              # M tại Apr 2025
HCM02_DECLINE_M_END    = 0.40              # M tại tháng đóng cửa
HCM02_DECLINE_MONTHS   = 6                 # 6 tháng decline (Apr → Sep)

# ===========================================================================
# DN-05 TEMP CLOSE PARAMETERS (store_id=25)
# ===========================================================================
DN05_PRESTRESS_START = date(2026, 1, 1)    # pre-closure signal từ Jan 2026
DN05_TEMP_CLOSE_START = date(2026, 4, 26)
DN05_TEMP_CLOSE_END   = date(2026, 7, 2)
DN05_PRESTRESS_M_DROP = -0.08             # -8% mỗi tháng trước khi đóng

# ===========================================================================
# DELIVERY CHANNEL BOOM (2025 H1 only)
# ===========================================================================
DELIVERY_BOOM_CHANNELS = {"ShopeeFood", "Grab", "BeFood", "GreenSM"}
# App-delivery cũng hưởng boom nhưng được tính riêng trong channel logic
DELIVERY_BOOM_PERIOD   = (date(2025, 1, 1), date(2025, 6, 30))
DELIVERY_BOOM_MIX_RATE = 0.40   # boom_factor = 1 + mix_delivery × 0.40 (cap 1.18)

# ===========================================================================
# SEASONALITY MULTIPLIERS (daily revenue weight)
# ===========================================================================
DAY_OF_WEEK_MULT = {
    1: 0.90,  # Mon: ít nhất
    2: 0.95,  # Tue
    3: 0.95,  # Wed
    4: 1.00,  # Thu
    5: 1.10,  # Fri
    6: 1.25,  # Sat
    7: 1.20,  # Sun
}

HOLIDAY_MULT    = 1.35  # ngày lễ quốc gia (Tết, 30/4, 1/5, 2/9)
DOUBLE_DAY_MULT = 1.28  # Double Day flash sale (from 2025)
TET_WEEK_DIP    = 0.70  # 2 tuần sau Tết (traffic giảm)
MARCH_2026_MULT = 0.98  # stagnation: tháng 3/2026 (sau Tết + stagnation)

# ===========================================================================
# POS CUSTOMER REGISTRATION RATE (per year-month)
# Non-linear: surge in 2025 due to App launch cross-awareness
# ===========================================================================
# Xem date_utils.pos_customer_rate(year, month) cho implementation chi tiết

# ===========================================================================
# CATEGORY MIX WEIGHTS (per channel — for product selection)
# ===========================================================================
CATEGORY_MIX = {
    # channel_group → {category_id: weight}
    "dine_in": {
        "CAT-01": 0.35,  # Ca Phe (nhiều nhất — ngồi uống tại chỗ)
        "CAT-02": 0.20,  # Tra
        "CAT-03": 0.15,  # Da Xay
        "CAT-04": 0.05,  # LTO
        "CAT-05": 0.15,  # Food
        "CAT-06": 0.05,  # Retail
        "CAT-07": 0.05,  # Merch
    },
    "delivery": {
        "CAT-01": 0.25,
        "CAT-02": 0.20,
        "CAT-03": 0.30,  # Da Xay phổ biến hơn khi order online
        "CAT-04": 0.05,
        "CAT-05": 0.15,  # Food
        "CAT-06": 0.03,
        "CAT-07": 0.02,
    },
    "takeaway": {
        "CAT-01": 0.30,
        "CAT-02": 0.20,
        "CAT-03": 0.20,
        "CAT-04": 0.05,
        "CAT-05": 0.18,
        "CAT-06": 0.05,
        "CAT-07": 0.02,
    },
}

# ===========================================================================
# ITEMS PER ORDER DISTRIBUTION
# ===========================================================================
# (n_items, weight)
ITEMS_PER_ORDER = [(1, 0.40), (2, 0.35), (3, 0.18), (4, 0.05), (5, 0.02)]

# ===========================================================================
# MODIFIER SELECTION RATES (per modifier group, beverage only)
# ===========================================================================
MODIFIER_RATES = {
    "ice":       0.80,  # 80% chọn mức đá (trừ Da Xay — CAT-03)
    "sweetness": 0.70,  # 70% chọn độ đường
    "topping":   0.30,  # 30% thêm topping
    "size_up":   0.15,  # 15% chọn size lớn hơn nếu có
}

# ===========================================================================
# WASTAGE BASE RATE
# ===========================================================================
BASE_WASTAGE_RATE    = 0.04   # 4% baseline
WASTAGE_HARD_CAP     = 0.15   # max 15%
WASTAGE_OUTLIER_PROB = 0.10   # 10% xác suất spike tháng bất thường
WASTAGE_OUTLIER_MULT = (1.5, 2.5)  # range của spike

# ===========================================================================
# OUTPUT
# ===========================================================================
import os
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
RAW_DIR       = os.path.join(_ROOT, "data", "raw")
DIMENSION_DIR  = os.path.join(_ROOT, "data", "dimension", "full")
SYNTHETIC_DIR = os.path.join(_ROOT, "data", "synthetic")
MERGED_DIR    = os.path.join(SYNTHETIC_DIR, "merged")
SALE_ORDER_DIR = os.path.join(SYNTHETIC_DIR, "sale_orders")

FORCE_REGENERATE = False   # True → overwrite existing files; False → skip if exists
