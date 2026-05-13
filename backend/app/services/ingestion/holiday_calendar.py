"""
Tamil Nadu public holiday calendar.
Used by both the feature engineering pipeline and the forecast engine
to flag future dates as holidays when generating predictions.
"""

from datetime import date, timedelta
from typing import Set, List


# ---------------------------------------------------------------------------
# Fixed holidays (same date every year)
# ---------------------------------------------------------------------------
FIXED_HOLIDAYS = [
    (1, 1),   # New Year's Day
    (1, 14),  # Pongal Day 1
    (1, 15),  # Pongal Day 2 (Mattu Pongal)
    (1, 26),  # Republic Day
    (4, 14),  # Tamil New Year / Ambedkar Jayanti
    (5, 1),   # May Day / Labour Day
    (8, 15),  # Independence Day
    (10, 2),  # Gandhi Jayanti
    (12, 25), # Christmas
]

# Variable holidays per year (Good Friday, Dussehra, Diwali shift each year)
VARIABLE_HOLIDAYS: dict[int, list[date]] = {
    2024: [
        date(2024, 3, 29),  # Good Friday
        date(2024, 10, 12), # Vijayadasami / Dussehra
        date(2024, 11, 1),  # Diwali
        date(2024, 11, 15), # Karthigai Deepam
    ],
    2025: [
        date(2025, 4, 18),  # Good Friday
        date(2025, 10, 2),  # Vijayadasami
        date(2025, 10, 20), # Diwali
        date(2025, 11, 5),  # Karthigai Deepam
    ],
    2026: [
        date(2026, 4, 3),   # Good Friday
        date(2026, 10, 22), # Vijayadasami
        date(2026, 11, 8),  # Diwali
    ],
}

# School reopening windows (start date, duration in days)
SCHOOL_REOPENING_WINDOWS: list[tuple[date, int]] = [
    (date(2024, 1, 2), 14),
    (date(2024, 6, 1), 14),
    (date(2025, 1, 2), 14),
    (date(2025, 6, 2), 14),
    (date(2026, 1, 2), 14),
    (date(2026, 6, 1), 14),
]


def _build_holiday_set(years: List[int]) -> Set[date]:
    holidays: Set[date] = set()
    for year in years:
        for month, day in FIXED_HOLIDAYS:
            holidays.add(date(year, month, day))
        for h in VARIABLE_HOLIDAYS.get(year, []):
            holidays.add(h)
    return holidays


def _build_school_reopening_set() -> Set[date]:
    days: Set[date] = set()
    for start, duration in SCHOOL_REOPENING_WINDOWS:
        for i in range(duration):
            days.add(start + timedelta(days=i))
    return days


_HOLIDAY_CACHE: dict[int, Set[date]] = {}
_SCHOOL_CACHE: Set[date] = _build_school_reopening_set()


def _get_holidays_for_year(year: int) -> Set[date]:
    if year not in _HOLIDAY_CACHE:
        _HOLIDAY_CACHE[year] = _build_holiday_set([year])
    return _HOLIDAY_CACHE[year]


def is_holiday(d: date) -> bool:
    return d in _get_holidays_for_year(d.year)


def is_school_reopening(d: date) -> bool:
    return d in _SCHOOL_CACHE


def get_holidays_in_range(start: date, end: date) -> List[date]:
    years = list(range(start.year, end.year + 1))
    all_holidays = _build_holiday_set(years)
    return sorted(h for h in all_holidays if start <= h <= end)


def get_prophet_holidays(start: date, end: date):
    """Return a DataFrame in the format Prophet expects for custom holidays."""
    import pandas as pd
    holidays = get_holidays_in_range(start, end)
    if not holidays:
        return pd.DataFrame(columns=["ds", "holiday"])
    return pd.DataFrame({
        "ds": pd.to_datetime(holidays),
        "holiday": "tn_public_holiday",
    })
