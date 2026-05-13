from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas.forecast import (
    DailyForecast,
    ForecastRangeResponse,
    WeeklyForecast,
    WeeklyForecastResponse,
)
from app.services.forecasting.ensemble import EnsembleForecaster
from app.services.ingestion.holiday_calendar import is_holiday

router = APIRouter(prefix="/forecasts", tags=["Forecasts"])

# cached models — loaded once on first request
_op_model: Optional[EnsembleForecaster] = None
_ip_model: Optional[EnsembleForecaster] = None


def _get_models() -> tuple[EnsembleForecaster, EnsembleForecaster]:
    global _op_model, _ip_model
    if _op_model is None:
        try:
            _op_model = EnsembleForecaster.load("op_count")
            _ip_model = EnsembleForecaster.load("ip_count")
        except FileNotFoundError:
            raise HTTPException(
                status_code=503,
                detail="Models not trained yet. POST /api/v1/fl/train to train.",
            )
    return _op_model, _ip_model


def _build_risk_flags(row: dict) -> list[str]:
    flags = []
    d = row["date"]
    if row["demand_level"] == "HIGH":
        flags.append("high_demand")
    if d.weekday() == 0:
        flags.append("monday_peak")
    elif d.weekday() == 1:
        flags.append("tuesday_peak")
    if d.weekday() >= 5:
        flags.append("weekend_surge")
    if is_holiday(d):
        flags.append("public_holiday")
    if row["op_forecast"] < 80:
        flags.append("low_footfall_window")
    return flags


@router.get("/daily", response_model=ForecastRangeResponse)
def get_daily_forecasts(days: int = Query(default=14, ge=1, le=28)):
    """Get daily OP + IP forecasts for the next N days (max 28)."""
    import warnings
    warnings.filterwarnings("ignore")

    op_model, ip_model = _get_models()
    op_fc = op_model.predict(horizon_days=days)
    ip_fc = ip_model.predict(horizon_days=days)

    forecasts = []
    for i in range(len(op_fc)):
        op_row = op_fc.iloc[i]
        ip_val = int(ip_fc.iloc[i]["forecast"])
        row = {
            "date": op_row["date"],
            "op_forecast": int(op_row["forecast"]),
            "demand_level": op_row["demand_level"],
        }
        item = DailyForecast(
            date=op_row["date"],
            op_forecast=int(op_row["forecast"]),
            ip_forecast=ip_val,
            total_forecast=int(op_row["forecast"]) + ip_val,
            lower=int(op_row["lower"]),
            upper=int(op_row["upper"]),
            demand_level=op_row["demand_level"],
            risk_flags=_build_risk_flags(row),
        )
        forecasts.append(item)

    return ForecastRangeResponse(
        generated_at=datetime.utcnow().isoformat(),
        horizon_days=days,
        forecasts=forecasts,
    )


@router.get("/weekly", response_model=WeeklyForecastResponse)
def get_weekly_forecasts(weeks: int = Query(default=4, ge=1, le=4)):
    """Get week-by-week aggregated forecasts."""
    import warnings
    warnings.filterwarnings("ignore")

    days = weeks * 7
    op_model, ip_model = _get_models()
    op_fc = op_model.predict(horizon_days=days)
    ip_fc = ip_model.predict(horizon_days=days)

    result = []
    for w in range(weeks):
        start = w * 7
        end = start + 7
        op_week = op_fc.iloc[start:end]
        ip_week = ip_fc.iloc[start:end]

        op_total = int(op_week["forecast"].sum())
        ip_total = int(ip_week["forecast"].sum())
        peak_idx = op_week["forecast"].idxmax()

        peak_val = int(op_week.loc[peak_idx, "forecast"])
        avg_daily = op_total // 7

        demand = "HIGH" if avg_daily >= 150 else ("MODERATE" if avg_daily >= 100 else "LOW")

        result.append(WeeklyForecast(
            week_start=op_week.iloc[0]["date"],
            week_end=op_week.iloc[-1]["date"],
            op_total=op_total,
            ip_total=ip_total,
            total_footfall=op_total + ip_total,
            peak_day=op_week.loc[peak_idx, "date"],
            peak_value=peak_val,
            avg_daily=avg_daily,
            demand_level=demand,
        ))

    return WeeklyForecastResponse(
        generated_at=datetime.utcnow().isoformat(),
        weeks=result,
    )
