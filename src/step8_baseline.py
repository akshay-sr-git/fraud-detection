from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from evaluate import bootstrap_ap_ci, report
from features import ALL_FEATURES, HONEST_FEATURES

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(ROOT / "data" / "features.parquet")
train = df[df.split == "train"]
val = df[df.split == "val"]
test = df[df.split == "test"]


def prep(d, cols):
    x = d[cols].astype("float64").copy()
    x = x.fillna({"dest_hrs_since_prev": 744, "amt_ratio": 0})  # NaN = never seen / undefined
    return np.sign(x) * np.log1p(np.abs(x))                      # signed log tames heavy tails


def fit_lr(cols):
    model = make_pipeline(StandardScaler(),
                          LogisticRegression(max_iter=300, class_weight="balanced"))
    model.fit(prep(train, cols), train.is_fraud)
    return model


print("Training logistic regression (honest features)... ")
lr_honest = fit_lr(HONEST_FEATURES)
print("Training logistic regression (all features)... ")
lr_all = fit_lr(ALL_FEATURES)


def evaluate_split(name, d):
    p_honest = lr_honest.predict_proba(prep(d, HONEST_FEATURES))[:, 1]
    p_all = lr_all.predict_proba(prep(d, ALL_FEATURES))[:, 1]

    print(f"\n=== {name.upper()} (all {len(d)} rows) ===")
    report("rule: orig_drained", d.is_fraud, d.orig_drained)
    report("LR honest (no balance)", d.is_fraud, p_honest)
    report("LR all features", d.is_fraud, p_all)

    m = (d.orig_drained == 0).values
    y0 = d.is_fraud.values[m]
    print(f"\n=== {name.upper()} RESIDUAL: rule says nothing "
          f"({m.sum()} rows, {int(y0.sum())} frauds) ===")
    report("LR honest (no balance)", y0, p_honest[m])
    report("LR all features", y0, p_all[m])
    return p_honest[m], y0


evaluate_split("val", val)
p_res, y_res = evaluate_split("test", test)

lo, hi = bootstrap_ap_ci(y_res, p_res)
print(f"\nTEST residual, LR honest: PR-AUC 95% CI [{lo:.4f}, {hi:.4f}] "
      f"(only {int(y_res.sum())} frauds, expect a wide interval)")