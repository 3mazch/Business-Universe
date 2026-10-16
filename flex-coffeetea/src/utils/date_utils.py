"""
date_utils.py — Date/time helpers for the fact generation engine.
Flex Coffee & Tea Data Generation Engine v1.0
"""
from datetime import date, datetime, time, timedelta
from typing import Iterator, Optional, Tuple
import random

from .constants import (
    DATA_SIM_START, DATA_SIM_END,
    DAY_OF_WEEK_MULT, HOLIDAY_MULT, DOUBLE_DAY_MULT,
    TET_WEEK_DIP, MARCH_2026_MULT,
)


# ===========================================================================
# MONTH ITERATION
# ===========================================================================
def month_range(
    start_year: int, start_month: int,
    end_year: int,   end_month: int
) -> Iterator[Tuple[int, int]]:
    """Yield (year, month) tuples from start to end inclusive."""
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def sim_months() -> Iterator[Tuple[int, int]]:
    """Yield all (year, month) in simulation window."""
    return month_range(
        DATA_SIM_START.year, DATA_SIM_START.month,
        DATA_SIM_END.year,   DATA_SIM_END.month,
    )


def next_month(year: int, month: int) -> Tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def prev_month(year: int, month: int) -> Tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def months_between(d1: date, d2: date) -> int:
    """Number of complete months from d1 to d2 (positive if d2 > d1)."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def month_end(year: int, month: int) -> date:
    """Last day of month."""
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def days_in_month(year: int, month: int):
    """Return list of all dates in given month."""
    start = month_start(year, month)
    end   = month_end(year, month)
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


# ===========================================================================
# HOLIDAY DETECTION
# ===========================================================================
# Pre-computed Tết date ranges (approx lunar calendar)
_TET_RANGES = [
    (date(2023, 1, 20), date(2023, 1, 25)),
    (date(2024, 2,  8), date(2024, 2, 13)),
    (date(2025, 1, 28), date(2025, 2,  2)),
    (date(2026, 2, 16), date(2026, 2, 21)),
]
_TET_DATES: set = set()
for _s, _e in _TET_RANGES:
    _d = _s
    while _d <= _e:
        _TET_DATES.add(_d)
        _d += timedelta(days=1)

# 2 tuần sau Tết dip
_POST_TET_DIP_DATES: set = set()
for _s, _e in _TET_RANGES:
    _d = _e + timedelta(days=1)
    _dip_end = _e + timedelta(days=14)
    while _d <= _dip_end:
        _POST_TET_DIP_DATES.add(_d)
        _d += timedelta(days=1)


def is_national_holiday(d: date) -> bool:
    """True nếu ngày đó là ngày lễ quốc gia (không bao gồm Double Day)."""
    if d in _TET_DATES:
        return True
    m, day = d.month, d.day
    return (m == 1 and day == 1) or \
           (m == 4 and day == 30) or \
           (m == 5 and day == 1) or \
           (m == 9 and day == 2)


def is_double_day(d: date) -> bool:
    """True nếu là Double Day flash sale (từ 2025, tháng == ngày)."""
    return d.year >= 2025 and d.month == d.day


def is_post_tet_dip(d: date) -> bool:
    return d in _POST_TET_DIP_DATES


# ===========================================================================
# DAILY REVENUE WEIGHT
# ===========================================================================
def daily_revenue_weight(d: date) -> float:
    """
    Trả về weight điều chỉnh revenue cho một ngày cụ thể.
    Base = 1.0 (ngày thường weekday).
    """
    weight = DAY_OF_WEEK_MULT.get(d.isoweekday(), 1.0)

    if is_national_holiday(d):
        weight *= HOLIDAY_MULT
    elif is_post_tet_dip(d):
        weight *= TET_WEEK_DIP

    if is_double_day(d):
        weight *= DOUBLE_DAY_MULT

    # Tháng 3/2026: stagnation dip
    if d.year == 2026 and d.month == 3:
        weight *= MARCH_2026_MULT

    return weight


def daily_weights_for_month(year: int, month: int) -> dict:
    """Return {date: weight} for all days in month, normalized to sum=days_count."""
    weights = {d: daily_revenue_weight(d) for d in days_in_month(year, month)}
    total   = sum(weights.values())
    n_days  = len(weights)
    # Normalize: average weight = 1.0, sum = n_days
    factor  = n_days / total
    return {d: w * factor for d, w in weights.items()}


# ===========================================================================
# POS CUSTOMER REGISTRATION RATE (non-linear, App surge 2025)
# ===========================================================================
def pos_customer_rate(year: int, month: int) -> float:
    """
    Tỷ lệ POS orders có customer_id (loyalty member).
    - 2023-06: ~30% (base)
    - 2024: tăng chậm ~0.5-0.6%/tháng
    - 2025: surge mạnh (App launch cross-awareness) H1 +1.5%/tháng, H2 +1%/tháng
    - 2026: plateau ~60-65%
    """
    if year == 2023:
        months_since = month - 6
        return min(0.34, 0.30 + 0.005 * months_since)

    if year == 2024:
        base = 0.34
        months_since = month - 1   # Jan 2024 = month 0
        return min(0.42, base + 0.006 * months_since)

    if year == 2025:
        base = 0.42
        surge = 0.015 if month <= 6 else 0.010
        months_since = month - 1
        return min(0.62, base + surge * months_since)

    # 2026: plateau
    base = 0.60
    months_since = month - 1
    return min(0.65, base + 0.003 * months_since)


# ===========================================================================
# ORDER TIME GENERATION
# ===========================================================================
def pick_order_time(
    open_time_str: str,
    close_time_str: str,
    channel_name: str,
    rng: random.Random,
    allowed_windows: Optional[list[Tuple[str, str]]] = None,
) -> str:
    """
    Sinh giờ order trước giờ đóng cửa; close_time là biên loại trừ.
    Peak hours: 7-9h (sáng), 11-13h (trưa), 14-16h (xế), 17-20h (tối).
    allowed_windows optionally restricts generation to one or more [start, end) ranges.
    """
    opens = time.fromisoformat(open_time_str)
    closes = time.fromisoformat(close_time_str)
    if closes <= opens:
        raise ValueError(
            f"Overnight or invalid operating hours are unsupported: "
            f"{open_time_str}–{close_time_str}"
        )

    open_seconds = opens.hour * 3600 + opens.minute * 60 + opens.second
    close_seconds = closes.hour * 3600 + closes.minute * 60 + closes.second
    windows = allowed_windows or [(open_time_str, close_time_str)]
    segments = []

    for window_start, window_end in windows:
        start = time.fromisoformat(window_start)
        end = time.fromisoformat(window_end)
        start_seconds = max(open_seconds, start.hour * 3600 + start.minute * 60 + start.second)
        end_seconds = min(close_seconds, end.hour * 3600 + end.minute * 60 + end.second)
        if end_seconds <= start_seconds:
            continue

        first_hour = start_seconds // 3600
        last_hour = (end_seconds - 1) // 3600
        for hour in range(first_hour, last_hour + 1):
            segment_start = max(start_seconds, hour * 3600)
            segment_end = min(end_seconds, (hour + 1) * 3600)
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
            if channel_name in ("ShopeeFood", "Grab", "BeFood", "GreenSM") and hour >= 18:
                weight *= 1.5
            segments.append((segment_start, segment_end, weight * (segment_end - segment_start)))

    if not segments:
        raise ValueError(
            f"No valid order-time interval within operating hours "
            f"{open_time_str}–{close_time_str} and {windows}"
        )

    chosen_start, chosen_end, _ = rng.choices(
        segments, weights=[segment[2] for segment in segments], k=1
    )[0]
    seconds = rng.randrange(chosen_start, chosen_end)
    return (datetime.min + timedelta(seconds=seconds)).strftime("%H:%M:%S")
