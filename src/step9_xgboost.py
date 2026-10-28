from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score

from evaluate import bootstrap_ap_ci, report
from features import ALL_FEATURES, HONEST_FEATURES, PRE_TXN_FEATURES

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "models").mkdir(exist_ok=True)

df = pd.read_parquet(ROOT / "data" / "features.parquet")
train = df[df.split == "train"]
val = df[df.split == "val"]
test = df[df.split == "test"]

neg = int((train.is_fraud == 0).sum())
pos = int((train.is_fraud == 1).sum())
WEIGHTS = {"none": 1.0, "sqrt": float(np.sqrt(neg / pos))}  # sqrt = middle ground vs full neg/pos

FEATURE_SETS = {
    "A_honest": HONEST_FEATURES,
    "B_pre_txn": PRE_TXN_FEATURES,
    "C_all_leaky": ALL_FEATURES,
}


def fit(cols, spw):
    model = xgb.XGBClassifier(
        n_estimators=1000, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8,
        scale_pos_weight=spw, tree_method="hist",
        eval_metric="aucpr", early_stopping_rounds=50,
        n_jobs=-1, random_state=42,
    )
    model.fit(train[cols], train.is_fraud,
              eval_set=[(val[cols], val.is_fraud)], verbose=False)
    return model


for set_name, cols in FEATURE_SETS.items():
    print(f"\n################ {set_name} ({len(cols)} features) ################")
    best = None
    # Pick the class weight on VAL only (test stays untouched until after the choice)
    for w_name, spw in WEIGHTS.items():
        m = fit(cols, spw)
        p_val = m.predict_proba(val[cols])[:, 1]
        ap = average_precision_score(val.is_fraud, p_val)
        print(f"weight={w_name:4s} (spw={spw:6.1f}) trees={m.best_iteration + 1:4d}  val PR-AUC={ap:.4f}")
        if best is None or ap > best[0]:
            best = (ap, w_name, m)

    _, w_name, model = best
    p_test = model.predict_proba(test[cols])[:, 1]
    y_test = test.is_fraud.values
    print(f"\nChosen weight: {w_name}")
    report("TEST full", y_test, p_test)
    lo, hi = bootstrap_ap_ci(y_test, p_test)
    print(f"{'':30s} PR-AUC 95% CI [{lo:.4f}, {hi:.4f}]")

    m0 = (test.orig_drained == 0).values
    report("TEST residual (not drained)", y_test[m0], p_test[m0])

    imp = model.get_booster().get_score(importance_type="gain")
    top = sorted(imp.items(), key=lambda kv: -kv[1])[:5]
    print("Top features by gain:", [(k, round(v, 1)) for k, v in top])

    joblib.dump({"model": model, "features": cols}, ROOT / "models" / f"xgb_{set_name}.joblib")

print("\nSaved models to models/")