from pathlib import Path
from typing import Literal

import joblib
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.fast_serving import FastScorer, build_row

ROOT = Path(__file__).resolve().parents[1]
ART = joblib.load(ROOT / "models" / "final_model.joblib")
MODEL, THRESHOLD, VERSION = ART["model"], ART["threshold"], ART["version"]
SCORER = FastScorer(MODEL)

app = FastAPI(title="Fraud Detection API", version=VERSION)


class Txn(BaseModel):
    type: Literal["TRANSFER", "CASH_OUT"]
    amount: float = Field(ge=0)
    old_bal_org: float = Field(ge=0, description="Sender balance before the transaction")
    old_bal_dest: float = Field(ge=0, description="Destination balance before the transaction")


class Score(BaseModel):
    risk_score: float
    alert: bool
    threshold: float
    reasons: list[str]
    model_version: str


@app.get("/health")
def health():
    return {"status": "ok", "model_version": VERSION, "threshold": THRESHOLD}


@app.post("/score", response_model=Score)
def score(txn: Txn, explain: bool = True):
    row = build_row(txn.type, txn.amount, txn.old_bal_org, txn.old_bal_dest)
    risk = SCORER.score(row)
    alert = risk > THRESHOLD
    reasons = SCORER.reasons(row) if (alert and explain) else []
    return Score(risk_score=round(risk, 4), alert=alert, threshold=THRESHOLD,
                 reasons=reasons, model_version=VERSION)