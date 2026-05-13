"""
Leave Impact Simulation Engine.

Given a doctor's leave request, this engine:
  1. Fetches the AI forecast for the leave period
  2. Calculates baseline vs redistributed workload
  3. Computes a feasibility score (0–100)
  4. Returns a per-day breakdown

No raw patient data is accessed — only the forecast output is used.
"""

from __future__ import annotations

import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from app.services.ingestion.holiday_calendar import is_holiday

DOCTORS_CSV = Path(__file__).resolve().parents[4] / "data" / "synthetic" / "doctors.csv"

SAFE_PATIENTS_PER_DOCTOR = 15   # recommended max per consultation session
MAX_SAFE_THRESHOLD = 18         # hard ceiling (from plan)
FEASIBILITY_GREEN = 70
FEASIBILITY_YELLOW = 40


def _load_doctors() -> pd.DataFrame:
    return pd.read_csv(DOCTORS_CSV)


def get_doctor(doctor_id: str) -> Optional[dict]:
    df = _load_doctors()
    row = df[df["doctor_id"] == doctor_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def _doctors_available_on(d: date, total: int = 25) -> int:
    """Estimate available doctors on a given day (holidays reduce count)."""
    if is_holiday(d):
        return max(18, total - 5)
    if d.weekday() >= 5:
        return max(20, total - 3)
    return total


def _demand_label(val: float) -> str:
    if val >= 150:
        return "HIGH"
    elif val >= 100:
        return "MODERATE"
    return "LOW"


def _risk_flags(d: date, op: int, load: float) -> list:
    flags = []
    if is_holiday(d):
        flags.append("public_holiday")
    if d.weekday() == 0:
        flags.append("monday_peak")
    elif d.weekday() == 1:
        flags.append("tuesday_peak")
    if d.weekday() >= 5:
        flags.append("weekend")
    if load > MAX_SAFE_THRESHOLD:
        flags.append("overload_risk")
    if op >= 150:
        flags.append("high_demand_day")
    return flags


def _feasibility_score(avg_redistributed: float, avg_baseline: float) -> int:
    """
    Score 0–100. Formula from PROJECT_PLAN:
    score = 100 × (1 - (redistributed - baseline) / max_safe)
    Clipped to [0, 100].
    """
    increase = avg_redistributed - avg_baseline
    if increase <= 0:
        return 100
    score = 100 * (1 - increase / MAX_SAFE_THRESHOLD)
    return max(0, min(100, int(round(score))))


def _feasibility_label(score: int) -> tuple[str, str]:
    if score >= FEASIBILITY_GREEN:
        return "APPROVED", "green"
    elif score >= FEASIBILITY_YELLOW:
        return "REVIEW_REQUIRED", "amber"
    return "NOT_RECOMMENDED", "red"


def _recommendation(score: int, level: str, peak_day: date, peak_val: int) -> str:
    if level == "APPROVED":
        return (
            f"Leave is feasible. Remaining doctors can handle the forecasted load. "
            f"Peak day is {peak_day.strftime('%b %d')} ({peak_val} patients) — "
            f"ensure adequate coverage."
        )
    elif level == "REVIEW_REQUIRED":
        return (
            f"Leave is possible but workload will be elevated. "
            f"Consider advancing follow-ups before {peak_day.strftime('%b %d')} "
            f"({peak_val} patients forecast). Department head approval recommended."
        )
    return (
        f"Leave is not recommended for this period. "
        f"Peak demand on {peak_day.strftime('%b %d')} ({peak_val} patients) "
        f"will significantly overload the {score}-scoring coverage plan. "
        f"Please choose a lower-demand window."
    )


def simulate_leave(
    doctor_id: str,
    start_date: date,
    end_date: date,
    leave_type: str = "Casual Leave",
    duration: str = "Full Day",
) -> dict:
    warnings.filterwarnings("ignore")

    doctor = get_doctor(doctor_id)
    if not doctor:
        raise ValueError(f"Doctor {doctor_id} not found.")

    # load forecast models
    from app.services.forecasting.ensemble import EnsembleForecaster
    op_model = EnsembleForecaster.load("op_count")
    ip_model = EnsembleForecaster.load("ip_count")

    # generate forecast covering the full leave period from today
    today = date.today()
    horizon = (end_date - today).days + 1
    if horizon < 1:
        horizon = (end_date - start_date).days + 7

    op_fc = op_model.predict(horizon_days=min(horizon, 28))
    ip_fc = ip_model.predict(horizon_days=min(horizon, 28))

    # filter to leave period
    op_fc["date"] = pd.to_datetime(op_fc["date"]).dt.date
    ip_fc["date"] = pd.to_datetime(ip_fc["date"]).dt.date

    leave_days = [
        start_date + timedelta(days=i)
        for i in range((end_date - start_date).days + 1)
    ]

    op_idx = op_fc.set_index("date")
    ip_idx = ip_fc.set_index("date")

    total_doctors = 25
    breakdown = []
    loads_baseline = []
    loads_redistributed = []

    for d in leave_days:
        doctors_today = _doctors_available_on(d, total_doctors)
        remaining = doctors_today - 1
        if remaining < 1:
            remaining = 1

        # use forecast if available, fallback to period mean
        if d in op_idx.index:
            op_val = int(op_idx.loc[d, "forecast"])
            ip_val = int(ip_idx.loc[d, "forecast"]) if d in ip_idx.index else 0
        else:
            op_val = int(op_fc["forecast"].mean())
            ip_val = int(ip_fc["forecast"].mean())

        total_val = op_val + ip_val

        # half-day: reduce impact by 50%
        effective_op = op_val if duration == "Full Day" else op_val // 2

        baseline = round(effective_op / doctors_today, 1)
        redistributed = round(effective_op / remaining, 1)

        loads_baseline.append(baseline)
        loads_redistributed.append(redistributed)

        breakdown.append({
            "date": d,
            "day_name": d.strftime("%A"),
            "op_forecast": op_val,
            "ip_forecast": ip_val,
            "total_forecast": total_val,
            "doctors_available": doctors_today,
            "load_per_doctor": baseline,
            "redistributed_load": redistributed,
            "demand_level": _demand_label(op_val),
            "risk_flags": _risk_flags(d, op_val, redistributed),
        })

    avg_baseline = round(sum(loads_baseline) / len(loads_baseline), 1)
    avg_redistributed = round(sum(loads_redistributed) / len(loads_redistributed), 1)
    load_increase_pct = round(
        (avg_redistributed - avg_baseline) / avg_baseline * 100
        if avg_baseline > 0 else 0,
        1,
    )

    # peak day
    peak = max(breakdown, key=lambda x: x["op_forecast"])
    peak_day = peak["date"]
    peak_val = peak["op_forecast"]
    avg_daily = int(sum(b["op_forecast"] for b in breakdown) / len(breakdown))

    score = _feasibility_score(avg_redistributed, avg_baseline)
    level, color = _feasibility_label(score)

    return {
        "doctor_id": doctor_id,
        "doctor_name": str(doctor["name"]),
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "duration_days": len(leave_days),
        "feasibility_score": score,
        "feasibility_level": level,
        "feasibility_color": color,
        "recommendation": _recommendation(score, level, peak_day, peak_val),
        "avg_daily_forecast": avg_daily,
        "peak_day": peak_day,
        "peak_forecast": peak_val,
        "redistribution": {
            "doctors_on_leave": 1,
            "remaining_doctors": total_doctors - 1,
            "baseline_load_per_doctor": avg_baseline,
            "redistributed_load_per_doctor": avg_redistributed,
            "load_increase_pct": load_increase_pct,
            "exceeds_safe_threshold": avg_redistributed > SAFE_PATIENTS_PER_DOCTOR,
            "safe_threshold": SAFE_PATIENTS_PER_DOCTOR,
        },
        "daily_breakdown": breakdown,
    }
