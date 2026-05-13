"""
Ensemble forecaster — combines Prophet + XGBoost via weighted average.

Trains both models, evaluates individually, and exposes a unified
predict() interface used by the API and workforce planning engine.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from app.services.forecasting.prophet_model import ProphetForecaster, _demand_label, _metrics
from app.services.forecasting.xgboost_model import XGBoostForecaster
from app.services.ingestion.feature_engineering import (
    build_feature_matrix,
    build_prophet_df,
    engineer_features,
    FEATURE_COLS,
)
from app.services.ingestion.aqi_fetcher import fetch_forecast_aqi
from app.services.ingestion.weather_fetcher import fetch_forecast_weather
from app.services.ingestion.holiday_calendar import is_holiday, is_school_reopening

ARTIFACTS_DIR = Path(__file__).resolve().parents[5] / "data" / "processed"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PROPHET_WEIGHT = 0.5
DEFAULT_XGB_WEIGHT = 0.5


class EnsembleForecaster:
    def __init__(
        self,
        target: str = "op_count",
        prophet_weight: float = DEFAULT_PROPHET_WEIGHT,
    ):
        self.target = target
        self.prophet_weight = prophet_weight
        self.xgb_weight = 1.0 - prophet_weight
        self.prophet = ProphetForecaster(target)
        self.xgb = XGBoostForecaster(target)
        self._last_row: Optional[pd.Series] = None  # for lag seeding
        self._eval_report: dict = {}

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, csv_path: str | Path) -> "EnsembleForecaster":
        csv_path = Path(csv_path)

        # --- XGBoost ---
        print(f"  [XGBoost] Training on target={self.target} ...")
        X_tr, X_val, X_te, y_tr, y_val, y_te, _ = build_feature_matrix(
            csv_path, target=self.target
        )
        self.xgb.fit(X_tr, y_tr, X_val, y_val)

        xgb_val = self.xgb.evaluate(X_val, y_val)
        xgb_test = self.xgb.evaluate(X_te, y_te)
        print(f"  [XGBoost] val  MAPE={xgb_val['mape']}%  RMSE={xgb_val['rmse']}")
        print(f"  [XGBoost] test MAPE={xgb_test['mape']}%  RMSE={xgb_test['rmse']}")

        # --- Prophet ---
        print(f"  [Prophet] Training on target={self.target} ...")
        prophet_df = build_prophet_df(csv_path, target=self.target)
        n = len(prophet_df)
        prophet_train = prophet_df.iloc[: int(n * 0.80)]
        prophet_test = prophet_df.iloc[int(n * 0.90):]
        self.prophet.fit(prophet_train)

        prophet_test_eval = self.prophet.evaluate(prophet_test)
        print(f"  [Prophet] test MAPE={prophet_test_eval['mape']}%  RMSE={prophet_test_eval['rmse']}")

        # seed last known row for lag features during inference
        raw = pd.read_csv(csv_path, parse_dates=["date"]).sort_values("date")
        self._last_row = raw.iloc[-1].copy()

        self._eval_report = {
            "xgb_val": xgb_val,
            "xgb_test": xgb_test,
            "prophet_test": prophet_test_eval,
        }
        return self

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, horizon_days: int = 28) -> pd.DataFrame:
        """
        Generate a horizon_days forecast starting from tomorrow.
        Fetches real weather + AQI forecasts automatically.
        Returns one row per day with: date, prophet, xgb, ensemble,
        lower, upper, demand_level.
        """
        today = date.today()
        future_dates = [today + timedelta(days=i + 1) for i in range(horizon_days)]

        # --- fetch real future weather + AQI ---
        weather = _safe_fetch_weather(horizon_days)
        aqi_fc = _safe_fetch_aqi(horizon_days)

        # --- Prophet forecast ---
        future_aqi_vals = _align_env(aqi_fc, "aqi", future_dates, self.prophet._aqi_mean)
        prophet_result = self.prophet.predict(
            horizon_days=horizon_days,
            future_aqi=future_aqi_vals,
        )
        prophet_yhat = prophet_result["yhat"].values
        prophet_lower = prophet_result["yhat_lower"].values
        prophet_upper = prophet_result["yhat_upper"].values

        # --- XGBoost forecast (one day at a time, feeding lags forward) ---
        xgb_yhat = self._xgb_rolling_predict(future_dates, weather, aqi_fc)

        # --- Ensemble ---
        ensemble = (
            self.prophet_weight * prophet_yhat + self.xgb_weight * xgb_yhat
        ).round().astype(int)

        # widen CI slightly to reflect ensemble uncertainty
        lower = (prophet_lower * 0.9).round().astype(int)
        upper = (prophet_upper * 1.1).round().astype(int)

        return pd.DataFrame({
            "date": future_dates,
            "prophet": prophet_yhat,
            "xgb": xgb_yhat,
            "forecast": ensemble,
            "lower": lower,
            "upper": upper,
            "demand_level": [_demand_label(v) for v in ensemble],
        })

    def _xgb_rolling_predict(
        self,
        future_dates: list[date],
        weather: Optional[pd.DataFrame],
        aqi_fc: Optional[pd.DataFrame],
    ) -> np.ndarray:
        """Auto-regressive day-by-day XGBoost prediction seeded from last known data."""
        from app.services.ingestion.holiday_calendar import is_holiday, is_school_reopening

        last = self._last_row
        rolling_buffer = list(last.get("op_roll7", last[self.target]) * np.ones(14))

        predictions = []
        weather_idx = weather.set_index(weather["date"].dt.date) if weather is not None else None
        aqi_idx = aqi_fc.set_index(aqi_fc["date"].dt.date) if aqi_fc is not None else None

        for d in future_dates:
            dow = d.weekday()
            month = d.month
            woy = d.isocalendar()[1]

            w = weather_idx.loc[d] if weather_idx is not None and d in weather_idx.index else None
            a = aqi_idx.loc[d] if aqi_idx is not None and d in aqi_idx.index else None

            temp = float(w["temperature"]) if w is not None else float(np.mean([26.0]))
            humidity = float(w["humidity"]) if w is not None else 70.0
            rainfall = float(w["rainfall"]) if w is not None else 0.0
            aqi = float(a["aqi"]) if a is not None else self.prophet._aqi_mean

            row = {
                "dow_sin": np.sin(2 * np.pi * dow / 7),
                "dow_cos": np.cos(2 * np.pi * dow / 7),
                "month_sin": np.sin(2 * np.pi * month / 12),
                "month_cos": np.cos(2 * np.pi * month / 12),
                "week_sin": np.sin(2 * np.pi * woy / 52),
                "week_cos": np.cos(2 * np.pi * woy / 52),
                "is_monday": int(dow == 0),
                "is_tuesday": int(dow == 1),
                "is_weekend": int(dow >= 5),
                "is_holiday": int(is_holiday(d)),
                "is_school_reopening": int(is_school_reopening(d)),
                "aqi": aqi,
                "temperature": temp,
                "humidity": humidity,
                "rainfall": rainfall,
                "aqi_high": int(aqi > 150),
                "heavy_rain": int(rainfall > 20),
                "doctors_available": 22 if is_holiday(d) else 24,
                "scheduled_followups": int(np.mean(rolling_buffer[-7:]) * 0.28),
                "active_ip_patients": int(np.mean(rolling_buffer[-7:]) * 0.17 * 4),
                "op_lag_7": rolling_buffer[-7],
                "op_lag_14": rolling_buffer[-14] if len(rolling_buffer) >= 14 else rolling_buffer[0],
                "op_roll7": np.mean(rolling_buffer[-7:]),
                "op_roll14": np.mean(rolling_buffer[-14:]),
            }

            X = pd.DataFrame([row])[FEATURE_COLS]
            pred = int(self.xgb.predict(X)[0])
            predictions.append(pred)
            rolling_buffer.append(pred)

        return np.array(predictions)

    # ------------------------------------------------------------------
    # Evaluation report
    # ------------------------------------------------------------------

    def evaluation_report(self) -> dict:
        return self._eval_report

    def feature_importance(self) -> pd.DataFrame:
        return self.xgb.feature_importance()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        self.prophet.save(f"prophet_{self.target}.json")
        self.xgb.save(f"xgb_{self.target}.json")
        last_row_dict = self._last_row.to_dict() if self._last_row is not None else {}
        # cast numpy types to native python for JSON serialisation
        last_row_dict = {k: (v.item() if hasattr(v, "item") else v)
                         for k, v in last_row_dict.items()}
        meta = {
            "target": self.target,
            "prophet_weight": self.prophet_weight,
            "xgb_weight": self.xgb_weight,
            "aqi_mean": self.prophet._aqi_mean,
            "eval_report": self._eval_report,
            "last_row": last_row_dict,
        }
        with open(ARTIFACTS_DIR / f"ensemble_{self.target}_meta.json", "w") as f:
            json.dump(meta, f, indent=2, default=str)

    @classmethod
    def load(cls, target: str = "op_count") -> "EnsembleForecaster":
        meta_path = ARTIFACTS_DIR / f"ensemble_{target}_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        obj = cls(target=target, prophet_weight=meta["prophet_weight"])
        obj.prophet = ProphetForecaster.load(target)
        obj.prophet._aqi_mean = meta["aqi_mean"]
        obj.xgb = XGBoostForecaster.load(target)
        obj._eval_report = meta.get("eval_report", {})
        last_row_dict = meta.get("last_row", {})
        if last_row_dict:
            obj._last_row = pd.Series(last_row_dict)
        return obj


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _safe_fetch_weather(days: int) -> Optional[pd.DataFrame]:
    try:
        return fetch_forecast_weather(days=min(days, 16))
    except Exception as e:
        print(f"[WARN] Weather forecast fetch failed: {e}")
        return None


def _safe_fetch_aqi(days: int) -> Optional[pd.DataFrame]:
    try:
        today = date.today()
        return fetch_forecast_aqi(days=min(days, 7)) if hasattr(fetch_forecast_aqi, "__call__") else None
    except Exception:
        return None


def _align_env(
    df: Optional[pd.DataFrame],
    col: str,
    dates: list[date],
    fallback: float,
) -> list[float]:
    if df is None:
        return [fallback] * len(dates)
    idx = df.set_index(df["date"].dt.date) if "date" in df.columns else df
    return [
        float(idx.loc[d, col]) if d in idx.index else fallback
        for d in dates
    ]
