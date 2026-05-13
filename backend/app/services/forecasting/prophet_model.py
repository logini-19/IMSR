"""
Prophet-based forecasting model.

Handles trend, weekly seasonality, annual respiratory seasonality,
Tamil Nadu public holidays, and AQI as an external regressor.
"""

from __future__ import annotations

import json
import warnings
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.serialize import model_to_json, model_from_json

warnings.filterwarnings("ignore")

ARTIFACTS_DIR = Path(__file__).resolve().parents[5] / "data" / "processed"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _build_holidays() -> pd.DataFrame:
    from app.services.ingestion.holiday_calendar import get_prophet_holidays
    return get_prophet_holidays(date(2023, 1, 1), date(2027, 12, 31))


class ProphetForecaster:
    def __init__(self, target: str = "op_count"):
        self.target = target
        self.model: Optional[Prophet] = None
        self._aqi_mean: float = 60.0

    def _build_model(self) -> Prophet:
        return Prophet(
            holidays=_build_holidays(),
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            holidays_prior_scale=10.0,
            interval_width=0.80,
        )

    def fit(self, df: pd.DataFrame) -> "ProphetForecaster":
        """
        df must have columns: ds (datetime), y (target), aqi (float)
        """
        train = df[["ds", "y", "aqi"]].copy()
        train = train.dropna()

        self._aqi_mean = float(train["aqi"].mean())

        m = self._build_model()
        m.add_regressor("aqi", standardize=True)
        m.add_seasonality(
            name="respiratory_peak",
            period=365.25,
            fourier_order=5,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m.fit(train)

        self.model = m
        return self

    def predict(
        self,
        horizon_days: int = 28,
        future_aqi: Optional[Union[float, list]] = None,
    ) -> pd.DataFrame:
        """
        Returns a DataFrame with:
            ds, yhat, yhat_lower, yhat_upper, demand_level
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call fit() first.")

        future = self.model.make_future_dataframe(periods=horizon_days, freq="D")

        if future_aqi is None:
            future["aqi"] = self._aqi_mean
        elif isinstance(future_aqi, (int, float)):
            future["aqi"] = float(future_aqi)
        else:
            hist_len = len(future) - horizon_days
            future["aqi"] = list([self._aqi_mean] * hist_len) + list(future_aqi)

        forecast = self.model.predict(future)
        result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        result["yhat"] = result["yhat"].clip(lower=0).round().astype(int)
        result["yhat_lower"] = result["yhat_lower"].clip(lower=0).round().astype(int)
        result["yhat_upper"] = result["yhat_upper"].clip(lower=0).round().astype(int)
        result["demand_level"] = result["yhat"].apply(_demand_label)

        # return only the forecast horizon (not historical fitted values)
        return result.tail(horizon_days).reset_index(drop=True)

    def evaluate(self, test_df: pd.DataFrame) -> dict:
        """
        test_df: ds, y, aqi columns.
        Returns MAPE, RMSE, MAE.
        """
        future = test_df[["ds", "aqi"]].copy()
        forecast = self.model.predict(future)
        y_true = test_df["y"].values
        y_pred = forecast["yhat"].clip(lower=0).values

        return _metrics(y_true, y_pred)

    def save(self, name: Optional[str] = None) -> Path:
        name = name or f"prophet_{self.target}.json"
        path = ARTIFACTS_DIR / name
        with open(path, "w") as f:
            f.write(model_to_json(self.model))
        return path

    @classmethod
    def load(cls, target: str = "op_count", name: Optional[str] = None) -> "ProphetForecaster":
        name = name or f"prophet_{target}.json"
        path = ARTIFACTS_DIR / name
        obj = cls(target=target)
        with open(path) as f:
            obj.model = model_from_json(f.read())
        return obj


def _demand_label(yhat: float) -> str:
    if yhat >= 150:
        return "HIGH"
    elif yhat >= 100:
        return "MODERATE"
    return "LOW"


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    mask = y_true != 0
    mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    return {"mape": round(mape, 2), "rmse": round(rmse, 2), "mae": round(mae, 2)}
