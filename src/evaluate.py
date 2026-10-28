import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve


def recall_at_fpr(y, p, fpr_target):
    fpr, tpr, _ = roc_curve(y, p)
    return tpr[np.searchsorted(fpr, fpr_target, side="right") - 1]


def report(name, y, p):
    y = np.asarray(y)
    base = y.mean()
    ap = average_precision_score(y, p)
    print(f"{name:30s} PR-AUC {ap:.4f} (base {base:.4f}, lift {ap / base:6.1f}x) | "
          f"ROC-AUC {roc_auc_score(y, p):.4f} | "
          f"recall@FPR1% {recall_at_fpr(y, p, 0.01):.3f} | "
          f"recall@FPR0.1% {recall_at_fpr(y, p, 0.001):.3f}")
    return ap


def bootstrap_ap_ci(y, p, n=300, seed=0):
    rng = np.random.default_rng(seed)
    y, p = np.asarray(y), np.asarray(p)
    idx = np.arange(len(y))
    aps = []
    for _ in range(n):
        s = rng.choice(idx, len(idx), replace=True)
        if y[s].sum() == 0:
            continue
        aps.append(average_precision_score(y[s], p[s]))
    return np.percentile(aps, [2.5, 97.5])