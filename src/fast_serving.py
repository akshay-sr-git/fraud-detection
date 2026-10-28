import numpy as np
import xgboost as xgb

try:  # works when imported by the API (project root on path) and by scripts in src/
    from src.explain import READABLE
    from src.serving_features import FINAL_FEATURES
except ModuleNotFoundError:
    from explain import READABLE
    from serving_features import FINAL_FEATURES


def build_row(tx_type: str, amount: float, old_bal_org: float, old_bal_dest: float) -> np.ndarray:
    """Pure-numpy twin of serving_features.build_features. Column order = FINAL_FEATURES."""
    ratio = amount / old_bal_org if old_bal_org != 0 else np.nan
    return np.array([[
        amount,
        1.0 if tx_type == "CASH_OUT" else 0.0,
        old_bal_org,
        old_bal_dest,
        ratio,
        1.0 if old_bal_dest == 0 else 0.0,
    ]], dtype=np.float64)


class FastScorer:
    def __init__(self, model):
        self.booster = model.get_booster()
        self.n_trees = model.best_iteration + 1

    def score(self, row: np.ndarray) -> float:
        p = self.booster.inplace_predict(row, iteration_range=(0, self.n_trees),
                                         validate_features=False)
        return float(p[0])

    def reasons(self, row: np.ndarray, k: int = 3) -> list:
        dm = xgb.DMatrix(row, feature_names=FINAL_FEATURES)
        contrib = self.booster.predict(dm, pred_contribs=True,
                                       iteration_range=(0, self.n_trees),
                                       validate_features=False)[0]
        vals = contrib[:-1]  # last column is the bias term
        out = []
        for j in np.argsort(-np.abs(vals))[:k]:
            f = FINAL_FEATURES[j]
            v = row[0, j]
            shown = "none (never seen before)" if np.isnan(v) else f"{v:.4g}"
            direction = "raises" if vals[j] > 0 else "lowers"
            out.append(f"{READABLE.get(f, f)} = {shown} ({direction} risk)")
        return out