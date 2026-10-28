import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from explain import make_explainer, top_reasons
from fast_serving import FastScorer, build_row
from serving_features import build_features

ROOT = Path(__file__).resolve().parents[1]
RAW = ["type", "amount", "old_bal_org", "old_bal_dest"]

art = joblib.load(ROOT / "models" / "final_model.joblib")
model, thr = art["model"], art["threshold"]
scorer = FastScorer(model)
explainer = make_explainer(model)

df = pd.read_parquet(ROOT / "data" / "features.parquet")
test = df[df.split == "test"]
sample = pd.concat([test[test.is_fraud == 1].sample(300, random_state=0),
                    test[test.is_fraud == 0].sample(700, random_state=0)])

X = build_features(sample[RAW])
p_ref = model.predict_proba(X)[:, 1]

p_fast = np.empty(len(sample))
rows, nan_ok, max_feat_diff = [], True, 0.0
for i, r in enumerate(sample[RAW].itertuples(index=False)):
    row = build_row(str(r.type), float(r.amount), float(r.old_bal_org), float(r.old_bal_dest))
    ref = X.iloc[i].to_numpy(dtype="float64")
    nan_ok &= bool(np.array_equal(np.isnan(row[0]), np.isnan(ref)))
    mask = ~np.isnan(ref)
    max_feat_diff = max(max_feat_diff, float(np.abs(row[0][mask] - ref[mask]).max()))
    p_fast[i] = scorer.score(row)
    rows.append(row)

print("=== Parity on 1000 test rows ===")
print(f"NaN positions identical: {nan_ok} | max feature diff: {max_feat_diff:.2e}")
print(f"max |p_fast - p_ref|: {np.abs(p_fast - p_ref).max():.2e}")

alerts = np.where(p_ref > thr)[0][:100]
mismatch = sum(top_reasons(explainer, X.iloc[[i]])[0] != scorer.reasons(rows[i]) for i in alerts)
print(f"reason lists differing from the shap path: {mismatch} of {len(alerts)} alerts")


def bench(fn, n=500, warm=30):
    for _ in range(warm):
        fn()
    out = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t0) * 1000)
    return np.percentile(out, [50, 95])


row = build_row("TRANSFER", 803441.0, 803441.0, 0.0)
print("\n=== Timing (ms) ===")
for name, fn, before in [
    ("build_row (was DataFrame+build_features)", lambda: build_row("TRANSFER", 803441.0, 803441.0, 0.0), 8.77),
    ("scorer.score (was predict_proba)", lambda: scorer.score(row), 3.07),
    ("scorer.reasons (was shap top_reasons)", lambda: scorer.reasons(row), 5.73),
]:
    p50, p95 = bench(fn)
    print(f"{name:42s} p50 {p50:6.3f} | p95 {p95:6.3f} | before p50 {before}")