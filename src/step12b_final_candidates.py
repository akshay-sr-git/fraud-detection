from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score

from evaluate import recall_at_fpr
from features import HONEST_FEATURES, PRE_TXN_FEATURES

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_parquet(ROOT / "data" / "features.parquet")
train = df[df.split == "train"]
val = df[df.split == "val"]
test = df[df.split == "test"]
y_test = test.is_fraud.values
SEEDS = [0, 1, 2]

VELOCITY = ["dest_cnt_6h", "dest_cnt_24h", "dest_amt_24h"]
DEST_ALL = VELOCITY + ["dest_prior_cnt", "dest_hrs_since_prev"]


def without(cols, drop):
    return [c for c in cols if c not in drop]


EXPERIMENTS = {
    "A5 A - velocity":                        without(HONEST_FEATURES, VELOCITY),
    "A4 A - velocity - hour":                 without(HONEST_FEATURES, VELOCITY + ["hour_of_day"]),
    "B8 B - velocity - hour":                 without(PRE_TXN_FEATURES, VELOCITY + ["hour_of_day"]),
    "B6 B - dest history - hour (stateless)": without(PRE_TXN_FEATURES, DEST_ALL + ["hour_of_day"]),
}


def subsample_train(seed, frac=0.1):
    neg = train[train.is_fraud == 0].sample(frac=frac, random_state=seed)
    pos = train[train.is_fraud == 1]
    return pd.concat([neg, pos]).sample(frac=1, random_state=seed)


subs = {s: subsample_train(s) for s in SEEDS}


def run(cols, seed):
    tr = subs[seed]
    m = xgb.XGBClassifier(
        n_estimators=1000, learning_rate=0.05, max_depth=6,
        subsample=0.8, colsample_bytree=0.8, tree_method="hist",
        eval_metric="aucpr", early_stopping_rounds=50,
        n_jobs=-1, random_state=seed,
    )
    m.fit(tr[cols], tr.is_fraud, eval_set=[(val[cols], val.is_fraud)], verbose=False)
    p = m.predict_proba(test[cols])[:, 1]
    return {"ap": average_precision_score(y_test, p),
            "r1": recall_at_fpr(y_test, p, 0.01),
            "r01": recall_at_fpr(y_test, p, 0.001),
            "trees": m.best_iteration + 1}


rows = []
for name, cols in EXPERIMENTS.items():
    print(f"{name}: {cols}")
    r = pd.DataFrame([run(cols, s) for s in SEEDS])
    rows.append({"experiment": name, "n_feats": len(cols),
                 "PR-AUC": r.ap.mean(), "std": r.ap.std(),
                 "rec@1%FPR": r.r1.mean(), "rec@0.1%FPR": r.r01.mean(),
                 "trees": r.trees.mean()})

out = pd.DataFrame(rows)
print("\n=== FINAL CANDIDATES (test, mean over 3 seeds) ===")
print(out.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
out.to_csv(ROOT / "reports" / "ablation_final_candidates.csv", index=False)