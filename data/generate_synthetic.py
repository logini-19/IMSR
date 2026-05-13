"""
Synthetic data generator for PSG IMSR Pulmonology department.

Produces 2 years (Jan 2024 – Dec 2025) of daily records using:
  - REAL weather data (temperature, humidity, rainfall) from Open-Meteo
  - REAL AQI data from Open-Meteo Air Quality API
  - SYNTHETIC OP/IP counts driven by the real environmental values

Run:
    python data/generate_synthetic.py

Outputs (written to data/synthetic/):
    daily_records.csv   — 730 rows
    doctors.csv         — 25 doctors
    leave_requests.csv  — historical leave records
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import numpy as np
import pandas as pd
from datetime import date, timedelta

from app.services.ingestion.weather_fetcher import fetch_historical_weather
from app.services.ingestion.aqi_fetcher import fetch_aqi
from app.services.ingestion.holiday_calendar import is_holiday, is_school_reopening

SEED = 42
rng = np.random.default_rng(SEED)
OUTPUT_DIR = Path(__file__).parent / "synthetic"
OUTPUT_DIR.mkdir(exist_ok=True)

START = date(2024, 1, 1)
END = date(2025, 12, 31)


def compute_op_count(d: date, aqi: float, rainfall: float) -> int:
    dow = d.weekday()
    month = d.month
    _is_holiday = is_holiday(d)
    _is_weekend = dow >= 5
    _is_monday = dow == 0
    _is_tuesday = dow == 1
    _is_school = is_school_reopening(d)

    base = 110.0

    # seasonal respiratory peak
    if month in (12, 1, 2):
        base *= 1.20
    elif month in (4, 5):
        base *= 0.90

    # day-of-week
    if _is_holiday:
        base *= rng.uniform(0.50, 0.60)
    elif _is_monday:
        base *= rng.uniform(1.20, 1.30)
    elif _is_tuesday:
        base *= rng.uniform(1.15, 1.25)
    elif _is_weekend:
        base *= rng.uniform(1.10, 1.18)
    else:
        base *= rng.uniform(0.90, 1.05)

    if _is_school:
        base *= rng.uniform(1.15, 1.22)

    # AQI effect
    if aqi > 150:
        base *= rng.uniform(1.25, 1.35)
    elif aqi > 120:
        base *= rng.uniform(1.10, 1.20)

    # rainfall drop
    if rainfall > 30:
        base *= rng.uniform(0.80, 0.90)
    elif rainfall > 10:
        base *= rng.uniform(0.88, 0.96)

    # Gaussian noise ±6%
    base *= rng.normal(1.0, 0.06)
    return max(30, int(round(base)))


def generate_daily_records(weather: pd.DataFrame, aqi_df: pd.DataFrame) -> pd.DataFrame:
    days = [START + timedelta(days=i) for i in range((END - START).days + 1)]

    # index real data by date for fast lookup
    weather_idx = weather.set_index(weather["date"].dt.date)
    aqi_idx = aqi_df.set_index(aqi_df["date"].dt.date)

    rows = []
    prev_week_op = [110] * 7

    for d in days:
        dow = d.weekday()

        # real environmental values
        w_row = weather_idx.loc[d] if d in weather_idx.index else None
        a_row = aqi_idx.loc[d] if d in aqi_idx.index else None

        temp = float(w_row["temperature"]) if w_row is not None else float(rng.uniform(24, 32))
        humidity = float(w_row["humidity"]) if w_row is not None else float(rng.uniform(55, 80))
        rainfall = float(w_row["rainfall"]) if w_row is not None else 0.0
        aqi = float(a_row["aqi"]) if a_row is not None else float(rng.uniform(80, 140))

        op = compute_op_count(d, aqi, rainfall)
        ip = max(5, int(round(op * rng.uniform(0.15, 0.20))))
        followups = max(0, int(round(np.mean(prev_week_op) * rng.uniform(0.25, 0.32))))

        _is_holiday = is_holiday(d)
        doctors_available = int(rng.integers(20, 23) if _is_holiday else rng.integers(23, 26))
        active_ip = max(10, int(round(ip * rng.uniform(3.5, 5.0))))

        rows.append({
            "date": d.isoformat(),
            "op_count": op,
            "ip_count": ip,
            "total_footfall": op + ip,
            "aqi": round(aqi, 1),
            "temperature": round(temp, 1),
            "humidity": round(humidity, 1),
            "rainfall": round(rainfall, 1),
            "is_holiday": int(_is_holiday),
            "is_weekend": int(dow >= 5),
            "is_monday": int(dow == 0),
            "is_tuesday": int(dow == 1),
            "is_school_reopening": int(is_school_reopening(d)),
            "day_of_week": dow,
            "month": d.month,
            "week_of_year": d.isocalendar().week,
            "doctors_available": doctors_available,
            "scheduled_followups": followups,
            "active_ip_patients": active_ip,
        })

        prev_week_op.append(op)
        prev_week_op = prev_week_op[-7:]

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    # cyclical encoding
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["week_sin"] = np.sin(2 * np.pi * df["week_of_year"] / 52)
    df["week_cos"] = np.cos(2 * np.pi * df["week_of_year"] / 52)

    # lag features
    df["op_lag_7"] = df["op_count"].shift(7)
    df["op_lag_14"] = df["op_count"].shift(14)
    df["op_roll7"] = df["op_count"].shift(1).rolling(7).mean()
    df["op_roll14"] = df["op_count"].shift(1).rolling(14).mean()

    return df


def generate_doctors() -> pd.DataFrame:
    first_names = [
        "Arjun", "Priya", "Karthik", "Meena", "Suresh", "Divya", "Rajan",
        "Anitha", "Vikram", "Lakshmi", "Senthil", "Kavitha", "Murugan",
        "Sowmya", "Balamurugan", "Revathi", "Prasanna", "Nithya", "Venkat",
        "Saranya", "Dinesh", "Padmavathi", "Harish", "Usha", "Gowtham",
    ]
    specializations = [
        "General Pulmonology", "General Pulmonology", "General Pulmonology",
        "Interventional Pulmonology", "Interventional Pulmonology",
        "Sleep Medicine", "Sleep Medicine",
        "Critical Care", "Critical Care", "Critical Care",
        "Pediatric Pulmonology", "Pediatric Pulmonology",
        "TB & Infectious", "TB & Infectious", "TB & Infectious",
        "General Pulmonology", "General Pulmonology", "General Pulmonology",
        "Interventional Pulmonology", "Sleep Medicine",
        "Critical Care", "General Pulmonology", "TB & Infectious",
        "Pediatric Pulmonology", "General Pulmonology",
    ]
    rows = []
    for i, (name, spec) in enumerate(zip(first_names, specializations), start=1):
        join_year = rng.integers(2010, 2023)
        join_month = rng.integers(1, 13)
        rows.append({
            "doctor_id": f"DR{i:03d}",
            "name": f"Dr. {name}",
            "specialization": spec,
            "join_date": date(int(join_year), int(join_month), 1).isoformat(),
            "max_patients_per_day": int(rng.integers(14, 20)),
            "is_active": 1,
        })
    return pd.DataFrame(rows)


def generate_leave_requests(doctors: pd.DataFrame) -> pd.DataFrame:
    rows = []
    leave_types = ["Casual Leave", "Medical Leave", "Conference Leave", "Personal Leave"]
    req_id = 1
    for _, doc in doctors.iterrows():
        n_leaves = rng.integers(3, 8)
        for _ in range(int(n_leaves)):
            yr = rng.choice([2024, 2025])
            month = rng.integers(1, 13)
            start_day = rng.integers(1, 26)
            duration = rng.integers(1, 6)
            start = date(int(yr), int(month), int(start_day))
            end = start + timedelta(days=int(duration) - 1)
            rows.append({
                "request_id": f"LR{req_id:04d}",
                "doctor_id": doc["doctor_id"],
                "leave_type": rng.choice(leave_types),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "duration_days": int(duration),
                "status": rng.choice(
                    ["APPROVED", "APPROVED", "APPROVED", "REJECTED"],
                    p=[0.7, 0.1, 0.1, 0.1],
                ),
            })
            req_id += 1
    return pd.DataFrame(rows)


def print_summary(df: pd.DataFrame):
    print("\n--- Daily Records Summary ---")
    print(f"  Rows          : {len(df)}")
    print(f"  Date range    : {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"  OP count      : min={df['op_count'].min()}  max={df['op_count'].max()}  mean={df['op_count'].mean():.1f}")
    print(f"  IP count      : min={df['ip_count'].min()}  max={df['ip_count'].max()}  mean={df['ip_count'].mean():.1f}")
    print(f"  Temp (°C)     : min={df['temperature'].min()}  max={df['temperature'].max()}  mean={df['temperature'].mean():.1f}")
    print(f"  Humidity (%)  : min={df['humidity'].min()}  max={df['humidity'].max()}  mean={df['humidity'].mean():.1f}")
    print(f"  Rainfall (mm) : max={df['rainfall'].max()}  rainy days={( df['rainfall'] > 0).sum()}")
    print(f"  AQI           : min={df['aqi'].min()}  max={df['aqi'].max()}  mean={df['aqi'].mean():.1f}")
    print(f"  Holidays      : {df['is_holiday'].sum()} days")
    print(f"  Weekends      : {df['is_weekend'].sum()} days")


if __name__ == "__main__":
    print(f"Fetching REAL weather data for Coimbatore ({START} → {END})...")
    weather = fetch_historical_weather(START, END)
    print(f"  Got {len(weather)} days of weather data")

    print(f"\nFetching REAL AQI data for Coimbatore ({START} → {END})...")
    aqi_df = fetch_aqi(START, END)
    print(f"  Got {len(aqi_df)} days of AQI data")

    print("\nGenerating daily records (synthetic OP/IP driven by real environment)...")
    daily = generate_daily_records(weather, aqi_df)
    daily.to_csv(OUTPUT_DIR / "daily_records.csv", index=False)
    print_summary(daily)

    print("\nGenerating doctors...")
    doctors = generate_doctors()
    doctors.to_csv(OUTPUT_DIR / "doctors.csv", index=False)
    print(f"  Doctors: {len(doctors)}")

    print("\nGenerating leave requests...")
    leaves = generate_leave_requests(doctors)
    leaves.to_csv(OUTPUT_DIR / "leave_requests.csv", index=False)
    print(f"  Leave requests: {len(leaves)}")

    print(f"\nAll files written to {OUTPUT_DIR.resolve()}")
