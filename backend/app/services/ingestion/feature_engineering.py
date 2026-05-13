"""
Feature engineering pipeline.

Usage:
    from app.services.ingestion.feature_engineering import build_feature_matrix

    X_train, X_val, X_test, y_train, y_val, y_test, feature_names = build_feature_matrix(
        csv_path="data/synthetic/daily_records.csv",
        target="op_count",
    )
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date
from typing import Union

from app.services.ingestion.holiday_calendar import is_holiday, is_school_reopening


# Features used by XGBoost (order matters — keep stable)
FEATURE_COLS = [
    # temporal cyclical
    "dow_sin", "dow_cos",
    "month_sin", "month_cos",
    "week_sin", "week_cos",
    # binary temporal
    "is_monday", "is_tuesday", "is_weekend",
    "is_holiday", "is_school_reopening",
    # environmental
    "aqi", "temperature", "humidity", "rainfall",
    "aqi_high",       # binary: aqi > 150
    "heavy_rain",     # binary: rainfall > 20
    # institutional
    "doctors_available", "scheduled_followups", "active_ip_patients",
    # lag / rolling
    "op_lag_7", "op_lag_14",
    "op_roll7", "op_roll14",
]

TARGET_COLS = ["op_count", "ip_count", "total_footfall"]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_raw(csv_path: Union[str, Path]) -> pd.DataFrame:
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(df: pd.DataFrame) -> list[str]:
    """Return a list of warning strings. Empty list = all clear."""
    warnings = []

    # no missing dates
    full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    missing = set(full_range) - set(df["date"])
    if missing:
        warnings.append(f"{len(missing)} missing dates: {sorted(missing)[:5]} ...")

    # negative counts
    for col in ["op_count", "ip_count", "total_footfall"]:
        if (df[col] < 0).any():
            warnings.append(f"Negative values found in {col}")

    # extreme outliers (>4 sigma)
    for col in ["op_count", "ip_count"]:
        mean, std = df[col].mean(), df[col].std()
        outliers = df[df[col] > mean + 4 * std]
        if not outliers.empty:
            warnings.append(f"{len(outliers)} outliers (>4σ) in {col}")

    return warnings


# ---------------------------------------------------------------------------
# Feature construction
# ---------------------------------------------------------------------------

def _add_temporal(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_monday"] = (df["day_of_week"] == 0).astype(int)
    df["is_tuesday"] = (df["day_of_week"] == 1).astype(int)
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["is_holiday"] = df["date"].dt.date.apply(is_holiday).astype(int)
    df["is_school_reopening"] = df["date"].dt.date.apply(is_school_reopening).astype(int)
    return df


def _add_cyclical(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["week_sin"] = np.sin(2 * np.pi * df["week_of_year"] / 52)
    df["week_cos"] = np.cos(2 * np.pi * df["week_of_year"] / 52)
    return df


def _add_environmental_bins(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["aqi_high"] = (df["aqi"] > 150).astype(int)
    df["heavy_rain"] = (df["rainfall"] > 20).astype(int)
    return df


def _add_lags(df: pd.DataFrame, target: str) -> pd.DataFrame:
    df = df.copy()
    df["op_lag_7"] = df[target].shift(7)
    df["op_lag_14"] = df[target].shift(14)
    df["op_roll7"] = df[target].shift(1).rolling(7).mean()
    df["op_roll14"] = df[target].shift(1).rolling(14).mean()
    return df


def engineer_features(df: pd.DataFrame, target: str = "op_count") -> pd.DataFrame:
    """Apply all transformations. Returns df with FEATURE_COLS + target present."""
    df = _add_temporal(df)
    df = _add_cyclical(df)
    df = _add_environmental_bins(df)
    df = _add_lags(df, target)
    df = df.dropna(subset=FEATURE_COLS).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Train / val / test split  (chronological — never shuffle time series)
# ---------------------------------------------------------------------------

def chronological_split(
    df: pd.DataFrame,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(df)
    test_start = int(n * (1 - test_ratio))
    val_start = int(n * (1 - test_ratio - val_ratio))
    return df.iloc[:val_start], df.iloc[val_start:test_start], df.iloc[test_start:]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_feature_matrix(
    csv_path: Union[str, Path],
    target: str = "op_count",
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
):
    """
    Load, validate, engineer, and split the dataset.

    Returns:
        X_train, X_val, X_test  — DataFrames with FEATURE_COLS
        y_train, y_val, y_test  — Series of target values
        feature_names           — ordered list of feature column names
    """
    df = load_raw(csv_path)

    issues = validate(df)
    if issues:
        for w in issues:
            print(f"[WARN] {w}")

    df = engineer_features(df, target)
    train, val, test = chronological_split(df, val_ratio, test_ratio)

    def _split(split_df):
        return split_df[FEATURE_COLS], split_df[target]

    X_train, y_train = _split(train)
    X_val, y_val = _split(val)
    X_test, y_test = _split(test)

    return X_train, X_val, X_test, y_train, y_val, y_test, FEATURE_COLS


def build_prophet_df(
    csv_path: Union[str, Path],
    target: str = "op_count",
):
    """Return a Prophet-ready DataFrame with columns [ds, y] + AQI regressor."""
    df = load_raw(csv_path)
    df = _add_environmental_bins(df)
    prophet_df = df[["date", target, "aqi"]].rename(columns={"date": "ds", target: "y"})
    return prophet_df
