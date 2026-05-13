"""
Federated Learning orchestrator.

Implements the FL workflow directly (no Ray/subprocess dependency):
  Round N:
    1. Server holds global weights
    2. Server sends weights → hospital node
    3. Node trains locally on its data
    4. Node returns updated weights + metrics
    5. Server aggregates weights (FedAvg)
  Repeat.

Raw patient data never leaves the node — only weight arrays are exchanged.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np

from app.services.federated.fl_model import (
    FL_FEATURES,
    get_weights,
    train_local,
    predict_local,
    prepare_fl_data,
)

ARTIFACTS_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
FL_HISTORY_PATH = ARTIFACTS_DIR / "fl_history.json"
FL_WEIGHTS_PATH = ARTIFACTS_DIR / "fl_global_weights.npy"


# ---------------------------------------------------------------------------
# History persistence
# ---------------------------------------------------------------------------

def _load_history() -> List[dict]:
    if FL_HISTORY_PATH.exists():
        with open(FL_HISTORY_PATH) as f:
            return json.load(f)
    return []


def _save_history(history: List[dict]):
    with open(FL_HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


def get_fl_status() -> dict:
    history = _load_history()
    if not history:
        return {
            "model_version": "none",
            "last_trained": None,
            "total_rounds": 0,
            "current_round": None,
            "history": [],
            "node_status": "ONLINE",
        }
    latest = history[-1]
    version = f"v{len(history)}.0"
    return {
        "model_version": version,
        "last_trained": latest.get("completed_at"),
        "total_rounds": len(history),
        "current_round": None,
        "history": history,
        "node_status": "ONLINE",
    }


# ---------------------------------------------------------------------------
# FedAvg aggregation (pure numpy — no framework dependency)
# ---------------------------------------------------------------------------

def _fed_avg(weight_list: List[np.ndarray], sample_counts: List[int]) -> np.ndarray:
    """Weighted average of weight arrays proportional to dataset size."""
    total = sum(sample_counts)
    return sum(w * (n / total) for w, n in zip(weight_list, sample_counts))


# ---------------------------------------------------------------------------
# Local node simulation
# ---------------------------------------------------------------------------

def _local_fit(
    global_weights: np.ndarray,
    X_train: np.ndarray,
    y_train: np.ndarray,
    lr: float = 0.001,
    epochs: int = 20,
) -> tuple:
    """Hospital node: receive global weights, train locally, return updates."""
    updated_weights, train_loss = train_local(
        global_weights.copy(), X_train, y_train, lr=lr, epochs=epochs
    )
    return updated_weights, len(X_train), train_loss


def _local_eval(
    weights: np.ndarray,
    X_val: np.ndarray,
    y_val_scaled: np.ndarray,
    y_val_orig: np.ndarray,
) -> dict:
    from app.services.federated.fl_model import inverse_scale_y
    y_pred_scaled = predict_local(weights, X_val)
    # report metrics in original patient-count scale
    y_pred_orig = np.clip(y_pred_scaled * y_val_orig.std() + y_val_orig.mean(), 0, None)
    mse = float(np.mean((y_pred_orig - y_val_orig) ** 2))
    rmse = float(np.sqrt(mse))
    mask = y_val_orig != 0
    mape = float(np.mean(np.abs((y_val_orig[mask] - y_pred_orig[mask]) / y_val_orig[mask])) * 100)
    return {"rmse": round(rmse, 2), "mape": round(mape, 2), "val_loss": round(mse, 2)}


# ---------------------------------------------------------------------------
# Main FL simulation
# ---------------------------------------------------------------------------

def run_fl_simulation(
    num_rounds: int = 3,
    target: str = "op_count",
) -> dict:
    """
    Run FL rounds on a single hospital node (proof-of-concept).

    FL workflow per round:
      server → sends global weights → node
      node   → trains locally        → server
      server → FedAvg aggregation   → new global weights

    No raw patient data leaves the node at any point.
    """
    import pandas as pd

    data_path = Path(__file__).resolve().parents[4] / "data" / "synthetic" / "daily_records.csv"
    raw = pd.read_csv(data_path, parse_dates=["date"])
    X, y, scaler = prepare_fl_data(raw, target=target)

    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"\n[FL] Starting — {num_rounds} rounds | target={target} | "
          f"node data: {len(X_train)} train / {len(X_val)} val")

    # load existing global weights or initialise
    if FL_WEIGHTS_PATH.exists():
        global_weights = np.load(FL_WEIGHTS_PATH)
    else:
        global_weights = get_weights(len(FL_FEATURES))

    run_history: List[dict] = []

    for round_num in range(1, num_rounds + 1):
        started_at = datetime.utcnow().isoformat()

        # --- node receives weights, trains locally ---
        updated_w, n_samples, train_loss = _local_fit(
            global_weights, X_train, y_train
        )
        print(f"  [Round {round_num}] node trained  "
              f"samples={n_samples}  train_loss={train_loss:.2f}")

        # --- server aggregates (single node → FedAvg = identity) ---
        global_weights = _fed_avg([updated_w], [n_samples])

        # --- evaluate on validation set (in original scale) ---
        from app.services.federated.fl_model import inverse_scale_y
        y_val_orig = inverse_scale_y(y_val, scaler)
        eval_metrics = _local_eval(global_weights, X_val, y_val, y_val_orig)
        print(f"  [Round {round_num}] aggregated    "
              f"RMSE={eval_metrics['rmse']}  MAPE={eval_metrics['mape']}%")

        run_history.append({
            "round_number": round_num,
            "started_at": started_at,
            "completed_at": datetime.utcnow().isoformat(),
            "participating_nodes": 1,
            "status": "COMPLETED",
            "train_loss": round(train_loss, 4),
            "val_loss": eval_metrics["val_loss"],
        })

    # persist global weights + history
    np.save(FL_WEIGHTS_PATH, global_weights)
    all_history = _load_history() + run_history
    _save_history(all_history)

    final_loss = run_history[-1]["val_loss"]
    version = f"v{len(all_history)}.0"
    print(f"[FL] Done — model {version}  final_val_loss={final_loss}")

    return {
        "status": "COMPLETED",
        "message": f"FL training complete — {num_rounds} rounds on 1 node. "
                   "No raw patient data was transmitted.",
        "rounds_completed": num_rounds,
        "final_loss": final_loss,
        "model_version": version,
    }
