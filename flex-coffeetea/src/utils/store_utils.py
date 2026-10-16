"""
store_utils.py — Store loading, maturity classification, and revenue modelling.
Flex Coffee & Tea Data Generation Engine v1.0
"""
from __future__ import annotations
from datetime import date
from typing import Optional
import random
import math
import os

import pandas as pd

from .constants import (
    DATA_SIM_START, DATA_SIM_END, BASELINE_ANCHOR,
    PRICE_FACTOR, DIMENSION_DIR,
    SEGMENT_THRESHOLDS, MATURITY_START_LEVEL, MATURITY_RAMP_RATE,
    NEW_STORE_NOVELTY,
    OUTLIER_STORE_AOV_MULTIPLIER,
    HCM02_DECLINE_START, HCM02_DECLINE_MONTHS,
    HCM02_DECLINE_M_START, HCM02_DECLINE_M_END,
    DN05_PRESTRESS_START, DN05_PRESTRESS_M_DROP,
    DN05_TEMP_CLOSE_START, DN05_TEMP_CLOSE_END,
    DELIVERY_BOOM_CHANNELS, DELIVERY_BOOM_PERIOD,
    DELIVERY_BOOM_MIX_RATE,
)
from .date_utils import months_between, month_start, month_end


# ===========================================================================
# LOAD STORE DATA
# ===========================================================================
_stores_df: Optional[pd.DataFrame] = None
_operating_hours: Optional[dict] = None   # {store_id: {dow: (open, close)}}


def load_stores() -> pd.DataFrame:
    global _stores_df
    if _stores_df is None:
        path = os.path.join(DIMENSION_DIR, "dim_store.csv")
        df = pd.read_csv(path)
        df["open_date"] = pd.to_datetime(df["open_date"]).dt.date
        def parse_optional_date(value):
            if pd.isna(value) or str(value).strip().lower() in (
                "", "nan", "none", "(none, none)"
            ):
                return None
            return pd.to_datetime(value).date()

        df["closed_date"] = df["closed_date"].apply(parse_optional_date)
        df["temp_close_start_dt"] = df["temp_close_start"].apply(parse_optional_date)
        df["temp_close_end_dt"] = df["temp_close_end"].apply(parse_optional_date)

        _stores_df = df
    return _stores_df


def load_operating_hours() -> dict:
    """Return {store_id: {day_of_week: (open_time_str, close_time_str)}}"""
    global _operating_hours
    if _operating_hours is None:
        path = os.path.join(DIMENSION_DIR, "store_operating_hours.csv")
        df   = pd.read_csv(path)
        result = {}
        for _, row in df.iterrows():
            sid = int(row["store_id"])
            dow = int(row["day_of_week"])
            result.setdefault(sid, {})[dow] = (
                str(row["open_time"]),
                str(row["close_time"]),
            )
        _operating_hours = result
    return _operating_hours


# ===========================================================================
# STORE MATURITY CLASSIFICATION
# ===========================================================================
def get_store_segment(store_row: pd.Series) -> str:
    """Classify store into A/B/C/D segment based on age at sim_start."""
    age = months_between(store_row["open_date"], DATA_SIM_START)
    if age >= 24: return "A-Mature"
    if age >= 12: return "B-Established"
    if age >= 0:  return "C-Young"
    return "D-NewInSim"


# ===========================================================================
# STORE LIFECYCLE CHECKS
# ===========================================================================
def is_store_open(store_row: pd.Series, check_date: date) -> bool:
    """True if store is generating revenue on check_date."""
    open_dt = store_row["open_date"]
    if check_date < open_dt:
        return False

    # Permanently closed
    closed = store_row.get("closed_date")
    if closed and check_date >= closed:
        return False

    # Temporarily closed
    tc_start = store_row.get("temp_close_start_dt")
    tc_end   = store_row.get("temp_close_end_dt")
    if tc_start and tc_end and tc_start <= check_date <= tc_end:
        return False

    return True


def is_store_active_in_month(store_row: pd.Series, year: int, month: int) -> bool:
    """True if store has at least 1 active day in the given month."""
    mstart = month_start(year, month)
    mend   = month_end(year, month)

    open_dt = store_row["open_date"]
    if open_dt > mend:
        return False

    closed = store_row.get("closed_date")
    if closed and closed < mstart:
        return False

    tc_start = store_row.get("temp_close_start_dt")
    tc_end = store_row.get("temp_close_end_dt")
    if tc_start and tc_end and tc_start <= mstart and tc_end >= mend:
        return False

    return True


def count_active_days_in_month(store_row: pd.Series, year: int, month: int) -> int:
    """Count number of revenue-generating days in a given month."""
    from .date_utils import days_in_month
    return sum(1 for d in days_in_month(year, month) if is_store_open(store_row, d))


# ===========================================================================
# MATURITY FACTOR M(T)
# ===========================================================================
def store_maturity_factor(store_row: pd.Series, year: int, month: int,
                           rng: random.Random) -> float:
    """
    Returns M(T) — maturity multiplier for this store at (year, month).
    Baseline (Dec 2025) = 1.0.
    """
    store_id  = int(store_row["store_id"])
    open_dt   = store_row["open_date"]
    segment   = get_store_segment(store_row)
    target_dt = month_start(year, month)
    months_open = months_between(open_dt, target_dt)  # months since open

    # ── SPECIAL CASE: HCM-02 declining before closure ─────────────────────
    if store_id == 12:  # HCM-02
        if target_dt >= HCM02_DECLINE_START:
            # months_into_decline: 0 = April 2025 (start), 5 = Sep 2025 (close)
            months_into_decline = months_between(HCM02_DECLINE_START, target_dt)
            if months_into_decline >= HCM02_DECLINE_MONTHS:
                return HCM02_DECLINE_M_END
            # Linear decline: April(0)=1.0, May(1)=0.88, Jun(2)=0.76...
            # Each month drops by (1.0 - 0.40) / 6 = 0.10
            step = (HCM02_DECLINE_M_START - HCM02_DECLINE_M_END) / HCM02_DECLINE_MONTHS
            return round(HCM02_DECLINE_M_START - step * months_into_decline, 3)

    # ── SPECIAL CASE: DN-05 pre-closure stress ────────────────────────────
    if store_id == 25:  # DN-05
        if target_dt >= DN05_PRESTRESS_START and target_dt < DN05_TEMP_CLOSE_START:
            months_stress = months_between(DN05_PRESTRESS_START, target_dt)
            return max(0.70, 1.0 + DN05_PRESTRESS_M_DROP * months_stress)

    # ── SEGMENT A: fully mature, M ≈ 1.0 ─────────────────────────────────
    if segment == "A-Mature":
        return 1.0

    # ── SEGMENT D: not yet open → novelty → build ─────────────────────────
    if segment == "D-NewInSim":
        if months_open < 0:
            return 0.0
        if months_open in NEW_STORE_NOVELTY:
            return NEW_STORE_NOVELTY[months_open]
        # Post-novelty: start at lower level, build toward 1.0
        novelty_months = max(NEW_STORE_NOVELTY.keys())
        post_novelty   = months_open - novelty_months
        start_m = 0.72    # level after novelty phase
        ramp    = MATURITY_RAMP_RATE["D-NewInSim"]
        return min(1.0, start_m + ramp * post_novelty)

    # ── SEGMENT C: young store ─────────────────────────────────────────────
    if segment == "C-Young":
        # HCM-06 opened exactly at sim_start (month 0)
        months_since_sim = months_between(DATA_SIM_START, target_dt)
        months_open_at_sim = months_between(open_dt, DATA_SIM_START)

        if months_open == 0:
            # Grand opening month — boost
            return NEW_STORE_NOVELTY.get(0, 1.10)
        if months_open == 1:
            return NEW_STORE_NOVELTY.get(1, 1.05)

        # Starting level at sim_start (per store seed for variation)
        start_range = MATURITY_START_LEVEL["C-Young"]  # (0.68, 0.78)
        start_m = start_range[0] + rng.random() * (start_range[1] - start_range[0])
        # Build from start_m at months_open_at_sim toward 1.0
        months_building = months_open - max(2, months_open_at_sim)
        ramp = MATURITY_RAMP_RATE["C-Young"]
        return min(1.0, start_m + ramp * max(0, months_building))

    # ── SEGMENT B: established store ──────────────────────────────────────
    if segment == "B-Established":
        months_since_sim = months_between(DATA_SIM_START, target_dt)
        start_range = MATURITY_START_LEVEL["B-Established"]  # (0.78, 0.85)
        start_m = start_range[0] + rng.random() * (start_range[1] - start_range[0])
        ramp = MATURITY_RAMP_RATE["B-Established"]
        return min(1.0, start_m + ramp * months_since_sim)

    return 1.0


# ===========================================================================
# GLOBAL GROWTH TRAJECTORY (G(T)) — pre-computed once
# ===========================================================================
def _build_growth_table(seed: int = 999) -> dict:
    """
    Builds {(year, month): cumulative_growth} table.
    Dec 2025 = 1.0 (anchor). Computed from monthly growth rates.
    """
    from .date_utils import month_range as mr
    rng = random.Random(seed)

    rates: dict = {}
    # 2023-06 → 2024-12: +1.2–1.8%/month
    for y, m in mr(2023, 6, 2024, 12):
        rates[(y, m)] = rng.uniform(0.012, 0.018)
    # 2025–2026: mature, flat business after the rapid expansion period.
    for y, m in mr(2025, 1, 2025, 6):
        rates[(y, m)] = rng.uniform(0.000, 0.004)
    for y, m in mr(2025, 7, 2025, 12):
        rates[(y, m)] = rng.uniform(-0.002, 0.003)
    for y, m in mr(2026, 1, 2026, 7):
        rates[(y, m)] = rng.uniform(-0.005, 0.003)

    # Build cumulative from Dec 2025 anchor = 1.0
    cumulative = {(2025, 12): 1.0}

    # Go backwards from Nov 2025 → simulation start.
    y, m = 2025, 11
    while (y, m) >= (DATA_SIM_START.year, DATA_SIM_START.month):
        ny, nm = (y, m + 1) if m < 12 else (y + 1, 1)
        rate = rates.get((ny, nm), 0.012)
        cumulative[(y, m)] = cumulative[(ny, nm)] / (1 + rate)
        m -= 1
        if m < 1:
            m = 12
            y -= 1

    # Go forward from Jan 2026 → Jul 2026
    y, m = 2026, 1
    while (y, m) <= (2026, 7):
        py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
        rate = rates.get((y, m), 0.007)
        cumulative[(y, m)] = cumulative[(py, pm)] * (1 + rate)
        m += 1

    return cumulative


# Build once at module import
_GROWTH_TABLE = _build_growth_table(seed=999)


def global_growth_factor(year: int, month: int) -> float:
    """G(T): cumulative growth relative to Dec 2025 baseline (=1.0)."""
    return _GROWTH_TABLE.get((year, month), 1.0)


# ===========================================================================
# MONTHLY REVENUE TARGET
# ===========================================================================
def get_monthly_revenue_target(
    store_row: pd.Series, year: int, month: int,
    rng: random.Random,
    maturity_m: Optional[float] = None,
) -> int:
    """
    Returns estimated monthly revenue target (VND) for this store at (year, month).
    Returns 0 if store is not active.
    """
    if not is_store_active_in_month(store_row, year, month):
        return 0

    # Pro-rate for partial months (closed mid-month, or just opened)
    active_days = count_active_days_in_month(store_row, year, month)
    from calendar import monthrange
    total_days  = monthrange(year, month)[1]
    day_ratio   = active_days / total_days if total_days > 0 else 0
    if day_ratio <= 0:
        return 0

    baseline = store_row["monthly_revenue_baseline_vnd"]   # Dec 2025 anchor

    G   = global_growth_factor(year, month)
    M   = maturity_m if maturity_m is not None else \
          store_maturity_factor(store_row, year, month, rng)
    P   = PRICE_FACTOR.get(year, 1.0)
    eps = rng.uniform(0.92, 1.08)     # ±8% noise

    target = baseline * G * M * P * eps * day_ratio
    return max(0, round(target / 1_000_000) * 1_000_000)


# ===========================================================================
# DELIVERY CHANNEL BOOM FACTOR (2025 H1 — per channel)
# ===========================================================================
def delivery_channel_boom(channel_name: str, store_row: pd.Series,
                           year: int, month: int) -> float:
    """
    Boom multiplier for delivery channels in 2025 H1.
    Returns 1.0 for POS and other non-delivery channels.
    """
    target_dt = month_start(year, month)
    if not (DELIVERY_BOOM_PERIOD[0] <= target_dt <= DELIVERY_BOOM_PERIOD[1]):
        return 1.0
    if channel_name not in DELIVERY_BOOM_CHANNELS:
        return 1.0
    delivery_mix = store_row.get("channel_mix_delivery", 0.30)
    boom = 1.0 + float(delivery_mix) * DELIVERY_BOOM_MIX_RATE
    return min(boom, 1.18)   # cap at +18%


# ===========================================================================
# OUTLIER AOV MULTIPLIER
# ===========================================================================
def get_aov_multiplier(store_row: pd.Series) -> float:
    """Return AOV multiplier for outlier stores (HN-02, HN-04)."""
    sid = int(store_row["store_id"])
    return OUTLIER_STORE_AOV_MULTIPLIER.get(sid, 1.0)
