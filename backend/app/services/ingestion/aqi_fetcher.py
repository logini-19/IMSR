"""
Fetches real AQI data for Coimbatore from Open-Meteo Air Quality API.
Free, no API key required.

API: https://air-quality-api.open-meteo.com/v1/air-quality
Returns US AQI (hourly), aggregated to daily mean.

Falls back to a synthetic AQI generator if the API is unavailable or
returns no data for a date range.
"""

import json
import time
import urllib.request
import urllib.parse
from datetime import date, timedelta
from typing import Optional
import numpy as np
import pandas as pd

COIMBATORE_LAT = 11.0168
COIMBATORE_LON = 76.9558
TIMEZONE = "Asia/Kolkata"

AQ_ARCHIVE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _get(url: str, params: dict, retries: int = 3) -> dict:
    full_url = url + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(full_url, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception as e:
            if attempt == retries - 1:
                raise RuntimeError(f"Failed to fetch {full_url}: {e}")
            time.sleep(2 ** attempt)


def _hourly_to_daily_aqi(raw: dict) -> pd.DataFrame:
    hourly = raw["hourly"]
    df = pd.DataFrame({
        "datetime": pd.to_datetime(hourly["time"]),
        "us_aqi": hourly.get("us_aqi", [None] * len(hourly["time"])),
        "pm2_5": hourly.get("pm2_5", [None] * len(hourly["time"])),
    })
    df["date"] = df["datetime"].dt.date

    # prefer us_aqi; estimate from pm2_5 if missing
    if df["us_aqi"].isna().all() and not df["pm2_5"].isna().all():
        df["us_aqi"] = df["pm2_5"].apply(_pm25_to_aqi)

    daily = df.groupby("date").agg(aqi=("us_aqi", "mean")).reset_index()
    daily["aqi"] = daily["aqi"].round(1)
    daily["date"] = pd.to_datetime(daily["date"])
    return daily


def _pm25_to_aqi(pm25: Optional[float]) -> Optional[float]:
    """Convert PM2.5 (µg/m³) to US AQI using EPA breakpoints."""
    if pm25 is None or np.isnan(pm25):
        return None
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 500.4, 301, 500),
    ]
    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= pm25 <= c_high:
            return round((i_high - i_low) / (c_high - c_low) * (pm25 - c_low) + i_low, 1)
    return 300.0


def _synthetic_aqi(dates: pd.Series, seed: int = 99) -> pd.Series:
    """
    Fallback: generate plausible Coimbatore AQI values based on month.
    Used when the API has no data for a given date range.
    """
    rng = np.random.default_rng(seed)
    result = []
    for d in dates:
        month = d.month if hasattr(d, "month") else pd.Timestamp(d).month
        if month in (6, 7, 8):       # monsoon — cleaner
            val = rng.uniform(60, 100)
        elif month in (10, 11, 12, 1):  # dry/festival — worse
            val = rng.uniform(120, 200)
        else:
            val = rng.uniform(80, 140)
        result.append(round(float(val), 1))
    return pd.Series(result, index=dates.index)


def fetch_aqi(start: date, end: date) -> pd.DataFrame:
    """
    Fetch real AQI for a date range. Falls back to synthetic per-day if API fails.
    Always returns a complete DataFrame with one row per day.
    """
    all_dates = pd.date_range(start=start, end=end, freq="D")

    try:
        params = {
            "latitude": COIMBATORE_LAT,
            "longitude": COIMBATORE_LON,
            "hourly": "us_aqi,pm2_5",
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "timezone": TIMEZONE,
        }
        raw = _get(AQ_ARCHIVE_URL, params)
        df = _hourly_to_daily_aqi(raw)

        # fill any gaps with synthetic
        full = pd.DataFrame({"date": all_dates})
        merged = full.merge(df, on="date", how="left")
        missing_mask = merged["aqi"].isna()
        if missing_mask.any():
            merged.loc[missing_mask, "aqi"] = _synthetic_aqi(
                merged.loc[missing_mask, "date"]
            ).values
            print(f"[INFO] AQI: {missing_mask.sum()} days filled with synthetic fallback")

        return merged

    except Exception as e:
        print(f"[WARN] AQI API failed ({e}), using synthetic AQI for full range")
        df = pd.DataFrame({"date": all_dates})
        df["aqi"] = _synthetic_aqi(df["date"])
        return df


def fetch_forecast_aqi(days: int = 7) -> pd.DataFrame:
    """Fetch AQI forecast for the next N days."""
    today = date.today()
    end = today + timedelta(days=days)
    return fetch_aqi(today, end)


def fetch_current_aqi() -> Optional[float]:
    """Fetch today's current AQI value (single number)."""
    today = date.today()
    try:
        df = fetch_aqi(today, today)
        val = df["aqi"].iloc[0]
        return float(val) if not np.isnan(val) else None
    except Exception:
        return None
