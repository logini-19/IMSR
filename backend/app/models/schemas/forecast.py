from __future__ import annotations
from datetime import date
from typing import List
from pydantic import BaseModel


class DailyForecast(BaseModel):
    date: date
    op_forecast: int
    ip_forecast: int
    total_forecast: int
    lower: int
    upper: int
    demand_level: str          # HIGH / MODERATE / LOW
    risk_flags: List[str] = []


class WeeklyForecast(BaseModel):
    week_start: date
    week_end: date
    op_total: int
    ip_total: int
    total_footfall: int
    peak_day: date
    peak_value: int
    avg_daily: int
    demand_level: str


class ForecastRangeResponse(BaseModel):
    generated_at: str
    horizon_days: int
    forecasts: List[DailyForecast]


class WeeklyForecastResponse(BaseModel):
    generated_at: str
    weeks: List[WeeklyForecast]
