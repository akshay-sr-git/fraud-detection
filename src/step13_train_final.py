from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from evaluate import bootstrap_ap_ci, report
from serving_features import FINAL_FEATURES, build_features

ROOT = Path(__file__).resolve().parents[1]
RAW = ["type", "amount", "old_bal_org", "old_bal_dest"]
SEED = 0

df = pd.read_parquet(ROOT / "data" / "features.parquet")
train = df[df.split == "train"]
val = df[df.split == "val"]
test = df[df.split == "test"]

# Same protocol as the ablation: all frauds + 10% of legit rows
neg = train[train.is_fraud == 0].sample(frac=0.1, random_state=SEED)
pos = train[train.is_fraud == 1]
tr = pd.concat([neg, pos]).sample(frac=1, random_state=SEED)

X_tr, y_tr = build_features(tr[RAW]), tr.is_fraud.values
X_val, y_val = build_features(val[RAW]), val.is_fraud.values
X_te, y_te = build_features(test[RAW]), test.is_fraud.values

# Info check: Python-computed ratio vs the SQL-computed one (SQL rounds to 6 decimals)
diff = np.nanmax(np.abs(X_te.amt_ratio.values - test.amt_ratio.values))
print(f"max |python - SQL| amt_ratio on test: {diff:.2e}")

model = xgb.XGBClassifier(
    n_estimators=1000, learning_rate=0.05, max_depth=6,
    subsample=0.8, colsample_bytree=0.8, tree_method="hist",
    eval_metric="aucpr", early_stopping_rounds=50,
    n_jobs=-1, random_state=SEED,
)
model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
print("trees used:", model.best_iteration + 1)

p_val = model.predict_proba(X_val)[:, 1]
p_te = model.predict_proba(X_te)[:, 1]


def op_metrics(y, p, thr):
    a = p > thr
    tp = int((a & (y == 1)).sum())
    fp = int((a & (y == 0)).sum())
    fn = int((~a & (y == 1)).sum())
    tn = int((~a & (y == 0)).sum())
    return {"tp": tp, "fp": fp, "fn": fn, "alerts": tp + fp,
            "precision": tp / max(tp + fp, 1), "recall": tp / max(tp + fn, 1),
            "fpr": fp / max(fp + tn, 1)}


# Threshold chosen on VAL ONLY: middle of the plateau where F1 is within 0.002 of its max
grid = np.linspace(0.01, 0.99, 99)


def f1_at(t):
    m = op_metrics(y_val, p_val, t)
    return 2 * m["tp"] / max(2 * m["tp"] + m["fp"] + m["fn"], 1)


f1s = np.array([f1_at(t) for t in grid])
plateau = grid[f1s >= f1s.max() - 0.002]
threshold = round(float(np.median(plateau)), 3)
print(f"\nval best F1 {f1s.max():.4f} | plateau thresholds {plateau.min():.2f}..{plateau.max():.2f} "
      f"| chosen threshold {threshold}")

print("\n=== Operating point at chosen threshold ===")
for name, y, p in [("val", y_val, p_val), ("test", y_te, p_te)]:
    m = op_metrics(y, p, threshold)
    print(f"{name:5s} recall {m['recall']:.4f} precision {m['precision']:.4f} FPR {m['fpr']:.5f} "
          f"| caught {m['tp']} missed {m['fn']} false alarms {m['fp']} (alerts {m['alerts']})")

print("\n=== Final model, TEST ===")
report("final B6", y_te, p_te)
lo, hi = bootstrap_ap_ci(y_te, p_te)
print(f"PR-AUC 95% CI [{lo:.4f}, {hi:.4f}]")

mt = op_metrics(y_te, p_te, threshold)
joblib.dump({
    "model": model, "features": FINAL_FEATURES, "threshold": threshold, "version": "b6-v1",
    "test_metrics": {"recall": mt["recall"], "precision": mt["precision"], "fpr": mt["fpr"]},
}, ROOT / "models" / "final_model.joblib")
print("\nSaved models/final_model.joblib")