from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # save plots to files, no window needed
import matplotlib.pyplot as plt
import shap

from explain import make_explainer, top_reasons

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

df = pd.read_parquet(ROOT / "data" / "features.parquet")
test = df[df.split == "test"]

THRESH = {"A_honest": 0.3041, "B_pre_txn": 0.5}  # from Step 10

for name, thr in THRESH.items():
    art = joblib.load(ROOT / "models" / f"xgb_{name}.joblib")
    model, cols = art["model"], art["features"]
    explainer = make_explainer(model)

    p = pd.Series(model.predict_proba(test[cols])[:, 1], index=test.index)
    y = test.is_fraud

    print(f"\n################ {name} (threshold {thr}) ################")

    # ---------- Global importance on a stratified sample ----------
    rows = pd.concat([test[y == 1].sample(500, random_state=0),
                      test[y == 0].sample(1500, random_state=0)])
    X = rows[cols]
    sv = explainer(X)

    # Additivity check: base value + sum of SHAP values must equal the model's margin output
    margin = model.predict(X, output_margin=True)
    ok = np.allclose(sv.values.sum(axis=1) + sv.base_values, margin, atol=1e-3)
    print("SHAP additivity check:", "PASS" if ok else "FAIL (tell me)")

    imp = pd.Series(np.abs(sv.values).mean(axis=0), index=cols).sort_values(ascending=False)
    print("\nMean |SHAP| (log-odds):")
    print(imp.round(3).to_string())

    shap.plots.bar(sv, max_display=12, show=False)
    plt.tight_layout()
    plt.savefig(REPORTS / f"shap_bar_{name}.png", dpi=150, bbox_inches="tight")
    plt.close()

    # Waterfall for one caught fraud
    caught_idx = [i for i, ix in enumerate(rows.index) if y[ix] == 1 and p[ix] > thr]
    if caught_idx:
        shap.plots.waterfall(sv[caught_idx[0]], max_display=10, show=False)
        plt.tight_layout()
        plt.savefig(REPORTS / f"shap_waterfall_{name}.png", dpi=150, bbox_inches="tight")
        plt.close()

    # ---------- Per-alert reasons: caught, false alarm, missed ----------
    groups = {
        "CAUGHT FRAUD (true positive)": test[(p > thr) & (y == 1)],
        "FALSE ALARM (false positive)": test[(p > thr) & (y == 0)],
        "MISSED FRAUD (false negative)": test[(p <= thr) & (y == 1)],
    }
    for title, g in groups.items():
        g = g.sample(min(3, len(g)), random_state=1) if len(g) else g
        print(f"\n-- {title}: {len(g)} shown --")
        if len(g) == 0:
            continue
        reasons = top_reasons(explainer, g[cols])
        for (ix, row), rs in zip(g.iterrows(), reasons):
            print(f"txn {int(row.txn_id)} | amount {row.amount:,.0f} | score {p[ix]:.3f}")
            for r in rs:
                print("     -", r)

print(f"\nPlots saved in {REPORTS}")