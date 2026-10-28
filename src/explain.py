import numpy as np
import shap

READABLE = {
    "amount": "transaction amount",
    "is_cash_out": "is CASH_OUT (1) vs TRANSFER (0)",
    "hour_of_day": "hour of day",
    "dest_cnt_6h": "txns into destination, last 6h",
    "dest_cnt_24h": "txns into destination, last 24h",
    "dest_amt_24h": "amount into destination, last 24h",
    "dest_prior_cnt": "earlier txns into destination",
    "dest_hrs_since_prev": "hours since destination's previous txn",
    "old_bal_org": "sender balance before",
    "old_bal_dest": "destination balance before",
    "amt_ratio": "amount / sender balance",
    "dest_bal_zero_before": "destination balance was zero (1/0)",
}


def make_explainer(model):
    # Early stopping leaves extra trees in the booster, so keep only the trees predict() uses
    booster = model.get_booster()[: model.best_iteration + 1]
    return shap.TreeExplainer(booster)


def top_reasons(explainer, X, k=3):
    """X: DataFrame with the model's feature columns. Returns one list of reason strings per row."""
    sv = explainer(X)
    out = []
    for i in range(len(X)):
        order = np.argsort(-np.abs(sv.values[i]))[:k]
        reasons = []
        for j in order:
            f = X.columns[j]
            direction = "raises" if sv.values[i, j] > 0 else "lowers"
            val = X.iloc[i, j]
            shown = "none (never seen before)" if np.isnan(val) else f"{val:.4g}"
            reasons.append(f"{READABLE.get(f, f)} = {shown} ({direction} risk)")
        out.append(reasons)
    return out