import pandas as pd

FINAL_FEATURES = [
    "amount", "is_cash_out", "old_bal_org", "old_bal_dest",
    "amt_ratio", "dest_bal_zero_before",
]


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    """raw columns: type, amount, old_bal_org, old_bal_dest.
    Used by BOTH training and the API, so they can never drift apart."""
    out = pd.DataFrame(index=raw.index)
    out["amount"] = raw["amount"].astype("float64")
    out["is_cash_out"] = (raw["type"] == "CASH_OUT").astype("int64")
    out["old_bal_org"] = raw["old_bal_org"].astype("float64")
    out["old_bal_dest"] = raw["old_bal_dest"].astype("float64")
    safe_bal = out["old_bal_org"].where(out["old_bal_org"] != 0)  # NaN when balance is 0
    out["amt_ratio"] = out["amount"] / safe_bal
    out["dest_bal_zero_before"] = (out["old_bal_dest"] == 0).astype("int64")
    return out[FINAL_FEATURES]