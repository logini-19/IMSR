"""
Smart Leave Recommendation Engine.

Analyses a 28-day forecast and identifies:
  - OPTIMAL windows  — low footfall, safe for leave (green)
  - MODERATE windows — manageable load (amber)
  - AVOID windows    — peak demand, leave not advisable (red)

Returns a day-by-day calendar and a ranked list of suggested windows.
"""

from __future__ import annotations

import warnings
from datetime import date, timedelta
from typing import List

import pandas as pd

from app.services.ingestion.holiday_calendar import is_holiday
from app.services.workforce.leave_simulator import (
    SAFE_PATIENTS_PER_DOCTOR,
    _doctors_available_on,
    _demand_label,
)

TOTAL_DOCTORS = 25
HORIZON_DAYS = 28

# load-per-doctor thresholds for window classification
OPTIMAL_THRESHOLD = 5.5    # below this → green
MODERATE_THRESHOLD = 7.0   # below this → amber; above → red


def _window_type(load: float) -> tuple[str, str]:
    if load <= OPTIMAL_THRESHOLD:
        return "OPTIMAL", "green"
    elif load <= MODERATE_THRESHOLD:
        return "MODERATE", "amber"
    return "AVOID", "red"


def _window_score(avg_load: float, holiday_count: int, weekend_count: int) -> int:
    """Higher score = better for leave. 0–100."""
    load_score = max(0, 100 - int((avg_load / SAFE_PATIENTS_PER_DOCTOR) * 100))
    bonus = min(20, holiday_count * 5 + weekend_count * 3)
    return min(100, load_score + bonus)


def _reason(wtype: str, avg_forecast: int, avg_load: float, has_holiday: bool) -> str:
    base = f"Avg {avg_forecast} patients/day ({avg_load:.1f} per doctor)"
    if wtype == "OPTIMAL":
        extra = " — well below safe capacity."
        if has_holiday: extra += " Includes a holiday (natural low-demand day)."
        return base + extra
    elif wtype == "MODERATE":
        return base + " — within acceptable range, plan handover carefully."
    return base + f" — exceeds recommended {SAFE_PATIENTS_PER_DOCTOR} patients/doctor. Avoid if possible."


def _extract_windows(calendar: List[dict], min_days: int = 1) -> List[dict]:
    """Group consecutive same-type days into windows, ranked by score."""
    windows = []
    i = 0
    while i < len(calendar):
        day = calendar[i]
        wtype = day["window_type"]
        j = i
        while j < len(calendar) and calendar[j]["window_type"] == wtype:
            j += 1
        span = calendar[i:j]
        if len(span) >= min_days:
            avg_forecast = int(sum(d["op_forecast"] for d in span) / len(span))
            avg_load = round(sum(d["load_per_doctor"] for d in span) / len(span), 1)
            holidays = sum(1 for d in span if d["is_holiday"])
            weekends = sum(1 for d in span if d["is_weekend"])
            windows.append({
                "start_date": span[0]["date"],
                "end_date": span[-1]["date"],
                "duration_days": len(span),
                "avg_daily_forecast": avg_forecast,
                "avg_load_per_doctor": avg_load,
                "window_type": wtype,
                "score": _window_score(avg_load, holidays, weekends),
                "reason": _reason(wtype, avg_forecast, avg_load, holidays > 0),
            })
        i = j

    return sorted(windows, key=lambda w: w["score"], reverse=True)


def recommend_leave(doctor_id: str, doctor_name: str) -> dict:
    warnings.filterwarnings("ignore")

    from app.services.forecasting.ensemble import EnsembleForecaster
    op_model = EnsembleForecaster.load("op_count")
    op_fc = op_model.predict(horizon_days=HORIZON_DAYS)
    op_fc["date"] = pd.to_datetime(op_fc["date"]).dt.date

    today = date.today()
    analysis_to = today + timedelta(days=HORIZON_DAYS)

    calendar = []
    for _, row in op_fc.iterrows():
        d = row["date"]
        op_val = int(row["forecast"])
        doctors_today = _doctors_available_on(d, TOTAL_DOCTORS)
        remaining = doctors_today - 1  # simulating one doctor on leave
        load = round(op_val / remaining, 1) if remaining > 0 else op_val
        wtype, color = _window_type(load)

        calendar.append({
            "date": d,
            "day_name": d.strftime("%A"),
            "op_forecast": op_val,
            "load_per_doctor": load,
            "window_type": wtype,
            "color": color,
            "reason": _reason(wtype, op_val, load, is_holiday(d)),
            "is_holiday": is_holiday(d),
            "is_weekend": d.weekday() >= 5,
        })

    windows = _extract_windows(calendar)
    optimal = [w for w in windows if w["window_type"] == "OPTIMAL"]
    moderate = [w for w in windows if w["window_type"] == "MODERATE"]
    top_windows = (optimal + moderate)[:5]

    optimal_count = len([d for d in calendar if d["window_type"] == "OPTIMAL"])
    avoid_count = len([d for d in calendar if d["window_type"] == "AVOID"])

    if optimal_count >= 5:
        summary = (
            f"{optimal_count} out of {HORIZON_DAYS} days are optimal for leave. "
            f"Avoid the {avoid_count} peak days flagged in red."
        )
    else:
        summary = (
            f"Next {HORIZON_DAYS} days show elevated demand — only {optimal_count} optimal days. "
            f"Consider planning leave beyond this window."
        )

    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor_name,
        "analysis_from": today,
        "analysis_to": analysis_to,
        "top_windows": top_windows,
        "calendar": calendar,
        "summary": summary,
    }
