"""
XGBoost-based forecasting model.

Trained on the 24 engineered features from feature_engineering.py.
Handles non-linear relationships between AQI, weather, day-of-week,
institutional load, and patient footfall.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error, mean_absolute_error

ARTIFACTS_DIR = Path(__file__).resolve().parents[5] / "data" / "processed"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


class XGBoostForecaster:
    def __init__(self, target: str = "op_count"):
        self.target = target
        self.model: Optional[xgb.XGBRegressor] = None
        self.feature_names: list[str] = []

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> "XGBoostForecaster":
        self.feature_names = list(X_train.columns)

        self.model = xgb.XGBRegressor(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=40,
            eval_metric="rmse",
        )

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Model not trained. Call fit() first.")
        preds = self.model.predict(X)
        return np.clip(preds, 0, None).round().astype(int)

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> dict:
        y_pred = self.predict(X)
        y_true = y.values
        mask = y_true != 0
        mape = float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        mae = float(mean_absolute_error(y_true, y_pred))
        return {"mape": round(mape, 2), "rmse": round(rmse, 2), "mae": round(mae, 2)}

    def feature_importance(self) -> pd.DataFrame:
        from app.services.ingestion.feature_engineering import FEATURE_COLS
        scores = self.model.feature_importances_
        names = self.feature_names if len(self.feature_names) == len(scores) else FEATURE_COLS
        df = pd.DataFrame({
            "feature": names,
            "importance": scores,
        }).sort_values("importance", ascending=False).reset_index(drop=True)
        # normalise to percentage
        df["importance_pct"] = (df["importance"] / df["importance"].sum() * 100).round(1)
        return df

    def save(self, name: Optional[str] = None) -> Path:
        name = name or f"xgb_{self.target}.json"
        path = ARTIFACTS_DIR / name
        self.model.save_model(str(path))
        return path

    @classmethod
    def load(cls, target: str = "op_count", name: Optional[str] = None) -> "XGBoostForecaster":
        name = name or f"xgb_{target}.json"
        path = ARTIFACTS_DIR / name
        obj = cls(target=target)
        obj.model = xgb.XGBRegressor()
        obj.model.load_model(str(path))
        return obj
