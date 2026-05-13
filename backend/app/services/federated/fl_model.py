"""
Lightweight linear model used for Federated Learning.

We use a numpy-based Ridge Regression rather than XGBoost for FL
because averaging linear weights across nodes (FedAvg) is mathematically
sound. XGBoost trees are not directly averageable.

The FL model learns the core demand patterns. XGBoost refines predictions
locally using the full feature set.
"""

from __future__ import annotations

import numpy as np
from pathlib import Path
from typing import Tuple

from app.services.ingestion.feature_engineering import FEATURE_COLS

# subset of features stable enough for federation
FL_FEATURES = [
    "is_monday", "is_tuesday", "is_weekend", "is_holiday",
    "is_school_reopening", "aqi_high", "heavy_rain",
    "month_sin", "month_cos", "dow_sin", "dow_cos",
    "op_lag_7", "op_roll7",
]
N_FEATURES = len(FL_FEATURES)


def get_weights(n_features: int = N_FEATURES) -> np.ndarray:
    """Return zero-initialised weight vector [w0..wn, bias]."""
    return np.zeros(n_features + 1)


def set_weights(weights: np.ndarray):
    return weights


def train_local(
    weights: np.ndarray,
    X: np.ndarray,
    y: np.ndarray,
    lr: float = 0.001,
    epochs: int = 10,
    l2: float = 0.01,
) -> Tuple[np.ndarray, float]:
    """
    Mini-batch gradient descent for linear regression.
    Returns updated weights and final MSE loss.
    """
    w = weights.copy()
    X_b = np.column_stack([X, np.ones(len(X))])  # add bias column

    for _ in range(epochs):
        y_pred = X_b @ w
        error = y_pred - y
        grad = (2 / len(X)) * X_b.T @ error + l2 * np.append(w[:-1], 0)
        w -= lr * grad

    loss = float(np.mean((X_b @ w - y) ** 2))
    return w, loss


def predict_local(weights: np.ndarray, X: np.ndarray) -> np.ndarray:
    X_b = np.column_stack([X, np.ones(len(X))])
    return np.clip(X_b @ weights, 0, None)


def prepare_fl_data(df, target: str = "op_count"):
    """Extract FL feature matrix and target. Returns scaled X, y, and scaler params."""
    from app.services.ingestion.feature_engineering import engineer_features

    df = engineer_features(df, target=target)
    X = df[FL_FEATURES].fillna(0).values.astype(np.float64)
    y = df[target].values.astype(np.float64)

    # z-score normalise features to prevent gradient explosion
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    X_scaled = (X - mean) / std

    # also normalise target to [0,1]-ish range
    y_mean = y.mean()
    y_std = y.std() + 1e-8
    y_scaled = (y - y_mean) / y_std

    scaler = {"X_mean": mean, "X_std": std, "y_mean": y_mean, "y_std": y_std}
    return X_scaled, y_scaled, scaler


def inverse_scale_y(y_scaled: np.ndarray, scaler: dict) -> np.ndarray:
    return y_scaled * scaler["y_std"] + scaler["y_mean"]
