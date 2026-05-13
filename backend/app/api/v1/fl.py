from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas.fl import (
    FLRound,
    FLStatusResponse,
    FLTrainRequest,
    FLTrainResponse,
)
from app.services.federated.server import get_fl_status, run_fl_simulation

router = APIRouter(prefix="/fl", tags=["Federated Learning"])

_training_in_progress = False


@router.get("/status", response_model=FLStatusResponse)
def fl_status():
    """Return current FL model version, training history, and node status."""
    status = get_fl_status()
    rounds = [
        FLRound(
            round_number=r["round_number"],
            started_at=r["started_at"],
            completed_at=r.get("completed_at"),
            participating_nodes=r.get("participating_nodes", 1),
            status=r.get("status", "COMPLETED"),
            train_loss=r.get("train_loss"),
            val_loss=r.get("val_loss"),
        )
        for r in status["history"]
    ]
    return FLStatusResponse(
        model_version=status["model_version"],
        last_trained=status["last_trained"],
        total_rounds=status["total_rounds"],
        current_round=None,
        history=rounds,
        node_status=status["node_status"],
    )


@router.post("/train", response_model=FLTrainResponse)
def fl_train(req: FLTrainRequest):
    """
    Trigger a federated learning training session.
    Runs in simulation mode (single hospital node).
    Raw patient data never leaves the node.
    """
    global _training_in_progress
    if _training_in_progress:
        raise HTTPException(status_code=409, detail="FL training already in progress.")

    _training_in_progress = True
    try:
        result = run_fl_simulation(
            num_rounds=req.num_rounds,
            target=req.target,
        )
        return FLTrainResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        _training_in_progress = False
