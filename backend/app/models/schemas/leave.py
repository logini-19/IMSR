from __future__ import annotations
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class LeaveSimulateRequest(BaseModel):
    doctor_id: str
    start_date: date
    end_date: date
    leave_type: str = "Casual Leave"
    duration: str = "Full Day"          # Full Day | Half Day


class DailyLeaveBreakdown(BaseModel):
    date: date
    day_name: str
    op_forecast: int
    ip_forecast: int
    total_forecast: int
    doctors_available: int
    load_per_doctor: float
    redistributed_load: float
    demand_level: str
    risk_flags: List[str]


class RedistributionPlan(BaseModel):
    doctors_on_leave: int
    remaining_doctors: int
    baseline_load_per_doctor: float
    redistributed_load_per_doctor: float
    load_increase_pct: float
    exceeds_safe_threshold: bool
    safe_threshold: int


class LeaveSimulateResponse(BaseModel):
    doctor_id: str
    doctor_name: str
    leave_type: str
    start_date: date
    end_date: date
    duration_days: int
    feasibility_score: int              # 0–100
    feasibility_level: str             # APPROVED | REVIEW_REQUIRED | NOT_RECOMMENDED
    feasibility_color: str             # green | amber | red
    recommendation: str
    avg_daily_forecast: int
    peak_day: date
    peak_forecast: int
    redistribution: RedistributionPlan
    daily_breakdown: List[DailyLeaveBreakdown]


class LeaveCalendarDay(BaseModel):
    date: date
    day_name: str
    op_forecast: int
    load_per_doctor: float
    window_type: str                   # OPTIMAL | MODERATE | AVOID
    color: str                         # green | amber | red
    reason: str
    is_holiday: bool
    is_weekend: bool


class SmartLeaveWindow(BaseModel):
    start_date: date
    end_date: date
    duration_days: int
    avg_daily_forecast: int
    avg_load_per_doctor: float
    window_type: str
    score: int                         # higher = better for leave
    reason: str


class SmartLeaveResponse(BaseModel):
    doctor_id: str
    doctor_name: str
    analysis_from: date
    analysis_to: date
    top_windows: List[SmartLeaveWindow]
    calendar: List[LeaveCalendarDay]
    summary: str
