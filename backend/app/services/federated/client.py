"""
Flower FL client — runs on the hospital node.
Trains the linear FL model locally on hospital data.
Raw data never leaves this node — only model weights are shared.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import flwr as fl
import numpy as np
import pandas as pd

from app.services.federated.fl_model import (
    FL_FEATURES,
    get_weights,
    train_local,
    predict_local,
    prepare_fl_data,
)

DATA_PATH = Path(__file__).resolve().parents[5] / "data" / "synthetic" / "daily_records.csv"


class PulmonologyClient(fl.client.NumPyClient):
    def __init__(self, target: str = "op_count", data_path: Path = DATA_PATH):
        self.target = target
        raw = pd.read_csv(data_path, parse_dates=["date"])
        self.X, self.y = prepare_fl_data(raw, target=target)
        # 80/20 train/val split (chronological)
        split = int(len(self.X) * 0.8)
        self.X_train, self.X_val = self.X[:split], self.X[split:]
        self.y_train, self.y_val = self.y[:split], self.y[split:]
        print(f"  [Client] Node ready — {len(self.X_train)} train / {len(self.X_val)} val samples")

    def get_parameters(self, config: Dict) -> List[np.ndarray]:
        return [get_weights(len(FL_FEATURES))]

    def fit(
        self, parameters: List[np.ndarray], config: Dict
    ) -> Tuple[List[np.ndarray], int, Dict]:
        weights = parameters[0]
        lr = float(config.get("lr", 0.001))
        epochs = int(config.get("epochs", 20))

        updated_weights, train_loss = train_local(
            weights, self.X_train, self.y_train, lr=lr, epochs=epochs
        )
        print(f"  [Client] fit done  train_loss={train_loss:.2f}")
        return [updated_weights], len(self.X_train), {"train_loss": train_loss}

    def evaluate(
        self, parameters: List[np.ndarray], config: Dict
    ) -> Tuple[float, int, Dict]:
        weights = parameters[0]
        y_pred = predict_local(weights, self.X_val)
        mse = float(np.mean((y_pred - self.y_val) ** 2))
        rmse = float(np.sqrt(mse))
        mask = self.y_val != 0
        mape = float(np.mean(np.abs((self.y_val[mask] - y_pred[mask]) / self.y_val[mask])) * 100)
        print(f"  [Client] eval  RMSE={rmse:.2f}  MAPE={mape:.1f}%")
        return mse, len(self.X_val), {"rmse": rmse, "mape": mape}


def start_client(server_address: str = "127.0.0.1:9090", target: str = "op_count"):
    """Start the Flower client and connect to the aggregation server."""
    client = PulmonologyClient(target=target)
    fl.client.start_client(
        server_address=server_address,
        client=client.to_client(),
    )
