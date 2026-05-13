"""
Fetches real weather data for Coimbatore from Open-Meteo (free, no API key).

Historical:  https://archive-api.open-meteo.com/v1/archive
Forecast:    https://api.open-meteo.com/v1/forecast  (up to 16 days ahead)
"""

import json
import time
import urllib.request
import urllib.parse
from datetime import date, timedelta
from typing import Optional
import pandas as pd

COIMBATORE_LAT = 11.0168
COIMBATORE_LON = 76.9558
TIMEZONE = "Asia/Kolkata"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARS = "temperature_2m,relative_humidity_2m,precipitation"


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


def _hourly_to_daily(raw: dict) -> pd.DataFrame:
    """Aggregate hourly Open-Meteo response to daily mean/sum."""
    hourly = raw["hourly"]
    df = pd.DataFrame({
        "datetime": pd.to_datetime(hourly["time"]),
        "temperature": hourly["temperature_2m"],
        "humidity": hourly["relative_humidity_2m"],
        "rainfall": hourly["precipitation"],
    })
    df["date"] = df["datetime"].dt.date
    daily = df.groupby("date").agg(
        temperature=("temperature", "mean"),
        humidity=("humidity", "mean"),
        rainfall=("rainfall", "sum"),
    ).reset_index()
    daily["temperature"] = daily["temperature"].round(1)
    daily["humidity"] = daily["humidity"].round(1)
    daily["rainfall"] = daily["rainfall"].round(1)
    daily["date"] = pd.to_datetime(daily["date"])
    return daily


def fetch_historical_weather(start: date, end: date) -> pd.DataFrame:
    """Fetch real daily weather for a past date range."""
    params = {
        "latitude": COIMBATORE_LAT,
        "longitude": COIMBATORE_LON,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": HOURLY_VARS,
        "timezone": TIMEZONE,
    }
    raw = _get(ARCHIVE_URL, params)
    return _hourly_to_daily(raw)


def fetch_forecast_weather(days: int = 16) -> pd.DataFrame:
    """Fetch weather forecast for the next N days (max 16)."""
    params = {
        "latitude": COIMBATORE_LAT,
        "longitude": COIMBATORE_LON,
        "hourly": HOURLY_VARS,
        "timezone": TIMEZONE,
        "forecast_days": min(days, 16),
    }
    raw = _get(FORECAST_URL, params)
    return _hourly_to_daily(raw)


def fetch_weather(start: date, end: date) -> Optional[pd.DataFrame]:
    """
    Smart fetch: routes past dates to archive, future dates to forecast.
    Returns None if both fail.
    """
    today = date.today()
    cutoff = today - timedelta(days=5)  # archive has ~5 day lag

    frames = []
    try:
        if start <= cutoff:
            hist_end = min(end, cutoff)
            frames.append(fetch_historical_weather(start, hist_end))
    except Exception as e:
        print(f"[WARN] Historical weather fetch failed: {e}")

    try:
        if end > cutoff:
            fc = fetch_forecast_weather(days=(end - today).days + 2)
            fc_trimmed = fc[fc["date"].dt.date >= max(start, cutoff + timedelta(1))]
            if not fc_trimmed.empty:
                frames.append(fc_trimmed)
    except Exception as e:
        print(f"[WARN] Forecast weather fetch failed: {e}")

    if not frames:
        return None

    df = pd.concat(frames).drop_duplicates("date").sort_values("date").reset_index(drop=True)
    return df
