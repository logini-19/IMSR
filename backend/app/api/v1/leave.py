from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas.leave import (
    LeaveSimulateRequest,
    LeaveSimulateResponse,
    DailyLeaveBreakdown,
    RedistributionPlan,
    SmartLeaveResponse,
    SmartLeaveWindow,
    LeaveCalendarDay,
)
from app.services.workforce.leave_simulator import simulate_leave, get_doctor
from app.services.workforce.leave_recommender import recommend_leave

router = APIRouter(prefix="/leave", tags=["Workforce Planning"])


@router.post("/simulate", response_model=LeaveSimulateResponse)
def simulate_leave_impact(req: LeaveSimulateRequest):
    """
    Simulate the impact of a doctor's leave on department workload.
    Returns feasibility score, per-day load redistribution, and recommendation.
    """
    if req.end_date < req.start_date:
        raise HTTPException(status_code=422, detail="end_date must be >= start_date.")

    try:
        result = simulate_leave(
            doctor_id=req.doctor_id,
            start_date=req.start_date,
            end_date=req.end_date,
            leave_type=req.leave_type,
            duration=req.duration,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    breakdown = [DailyLeaveBreakdown(**d) for d in result["daily_breakdown"]]
    redistribution = RedistributionPlan(**result["redistribution"])

    return LeaveSimulateResponse(
        **{k: v for k, v in result.items()
           if k not in ("daily_breakdown", "redistribution")},
        redistribution=redistribution,
        daily_breakdown=breakdown,
    )


@router.get("/recommend/{doctor_id}", response_model=SmartLeaveResponse)
def get_leave_recommendation(doctor_id: str):
    """
    Analyse the 28-day forecast and recommend optimal leave windows
    for a specific doctor.
    """
    doctor = get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found.")

    result = recommend_leave(doctor_id=doctor_id, doctor_name=str(doctor["name"]))

    top_windows = [SmartLeaveWindow(**w) for w in result["top_windows"]]
    calendar = [LeaveCalendarDay(**d) for d in result["calendar"]]

    return SmartLeaveResponse(
        **{k: v for k, v in result.items()
           if k not in ("top_windows", "calendar")},
        top_windows=top_windows,
        calendar=calendar,
    )
