from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/doctors", tags=["Doctors"])

DOCTORS_CSV = Path(__file__).resolve().parents[4] / "data" / "synthetic" / "doctors.csv"


class Doctor(BaseModel):
    doctor_id: str
    name: str
    specialization: str
    join_date: str
    max_patients_per_day: int
    is_active: int


@router.get("", response_model=List[Doctor])
def list_doctors():
    df = pd.read_csv(DOCTORS_CSV)
    return df.to_dict(orient="records")


@router.get("/{doctor_id}", response_model=Doctor)
def get_doctor(doctor_id: str):
    df = pd.read_csv(DOCTORS_CSV)
    row = df[df["doctor_id"] == doctor_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Doctor {doctor_id} not found.")
    return row.iloc[0].to_dict()
