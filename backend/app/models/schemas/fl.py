from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class FLRound(BaseModel):
    round_number: int
    started_at: str
    completed_at: Optional[str]
    participating_nodes: int
    status: str                # RUNNING / COMPLETED / FAILED
    train_loss: Optional[float]
    val_loss: Optional[float]


class FLStatusResponse(BaseModel):
    model_version: str
    last_trained: Optional[str]
    total_rounds: int
    current_round: Optional[FLRound]
    history: List[FLRound]
    node_status: str           # ONLINE / OFFLINE


class FLTrainRequest(BaseModel):
    num_rounds: int = 3
    target: str = "op_count"  # op_count | ip_count


class FLTrainResponse(BaseModel):
    status: str
    message: str
    rounds_completed: int
    final_loss: Optional[float]
    model_version: str
