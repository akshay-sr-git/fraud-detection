from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from evaluate import report

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(ROOT / "data" / "features.parquet")
val = df[df.split == "val"]
test = df[df.split == "test"]
y_val, y_test = val.is_fraud.values, test.is_fraud.values
amt_val, amt_test = val.amount.values, test.amount.values


def load_scores(name):
    art = joblib.load(ROOT / "models" / f"xgb_{name}.joblib")
    m, cols = art["model"], art["features"]
    return m.predict_proba(val[cols])[:, 1], m.predict_proba(test[cols])[:, 1]


def metrics(y, p, thr):
    alert = p > thr
    tp = int((alert & (y == 1)).sum())
    fp = int((alert & (y == 0)).sum())
    fn = int((~alert & (y == 1)).sum())
    tn = int((~alert & (y == 0)).sum())
    return {"alerts": int(alert.sum()),
            "precision": tp / max(tp + fp, 1),
            "recall": tp / max(tp + fn, 1),
            "fpr": fp / max(fp + tn, 1)}


def total_cost(y, amount, p, thr, review_cost):
    alert = p > thr
    missed = amount[(~alert) & (y == 1)].sum()
    return missed + review_cost * alert.sum()


for name in ["A_honest", "B_pre_txn"]:
    p_val, p_test = load_scores(name)
    print(f"\n################ {name} ################")

    # ---------- 1. Fixed-FPR operating points (threshold from VAL) ----------
    print("\n-- Fixed FPR: threshold chosen on val, applied to test --")
    print(f"{'target FPR':>10} {'thr':>8} | {'val recall':>10} {'val prec':>9} | "
          f"{'test recall':>11} {'test prec':>10} {'test FPR':>9} {'test alerts':>11}")
    for target in [0.001, 0.005, 0.01]:
        thr = np.quantile(p_val[y_val == 0], 1 - target)
        mv, mt = metrics(y_val, p_val, thr), metrics(y_test, p_test, thr)
        print(f"{target:10.3f} {thr:8.4f} | {mv['recall']:10.3f} {mv['precision']:9.3f} | "
              f"{mt['recall']:11.3f} {mt['precision']:10.3f} {mt['fpr']:9.4f} {mt['alerts']:11d}")

    # ---------- 2. Cost-based threshold (chosen on VAL) ----------
    print("\n-- Cost-based: threshold minimizing val cost, applied to test --")
    print(f"(no-model test cost = {amt_test[y_test == 1].sum():,.0f}, "
          f"total fraud amount in test)")
    grid = np.unique(np.concatenate([np.linspace(0.001, 0.999, 999),
                                     np.quantile(p_val, np.linspace(0.5, 0.9999, 1000))]))
    print(f"{'review cost':>12} {'thr':>8} | {'test cost':>14} {'fraud $ caught':>14} "
          f"{'recall':>7} {'precision':>9} {'alerts':>7}")
    for rc in [1_000, 10_000, 50_000, 200_000]:
        costs = [total_cost(y_val, amt_val, p_val, t, rc) for t in grid]
        thr = grid[int(np.argmin(costs))]
        mt = metrics(y_test, p_test, thr)
        alert = p_test > thr
        caught = amt_test[alert & (y_test == 1)].sum() / amt_test[y_test == 1].sum()
        print(f"{rc:12,d} {thr:8.4f} | {total_cost(y_test, amt_test, p_test, thr, rc):14,.0f} "
              f"{caught:13.1%} {mt['recall']:7.3f} {mt['precision']:9.3f} {mt['alerts']:7d}")

# ---------- 3. Sanity check: how much does the model add over ONE pre-txn rule? ----------
print("\n################ Sanity check: single pre-transaction rule ################")
rule = (np.abs(test.amt_ratio - 1) < 1e-6).astype(int).values  # amount == sender's whole balance
report("TEST rule: amount==old balance", y_test, rule)