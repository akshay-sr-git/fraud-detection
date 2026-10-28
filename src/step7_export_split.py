import getpass
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "features.parquet"

pw = getpass.getpass("Enter your MySQL root password: ")
engine = create_engine(f"mysql+pymysql://root:{quote_plus(pw)}@localhost:3306/fraud")

# DECIMAL -> DOUBLE in SQL so pandas gets real floats (not slow Decimal objects)
# Account names and is_flagged are left out on purpose (not model inputs)
QUERY = """
SELECT
  txn_id, step, type,
  CAST(amount AS DOUBLE)       AS amount,
  CAST(old_bal_org AS DOUBLE)  AS old_bal_org,
  CAST(new_bal_org AS DOUBLE)  AS new_bal_org,
  CAST(old_bal_dest AS DOUBLE) AS old_bal_dest,
  CAST(new_bal_dest AS DOUBLE) AS new_bal_dest,
  is_fraud,
  dest_cnt_6h, dest_cnt_24h,
  CAST(dest_amt_24h AS DOUBLE) AS dest_amt_24h,
  dest_prior_cnt, dest_hrs_since_prev,
  CAST(err_orig AS DOUBLE)     AS err_orig,
  CAST(err_dest AS DOUBLE)     AS err_dest,
  orig_drained, dest_bal_zero_before,
  CAST(amt_ratio AS DOUBLE)    AS amt_ratio,
  is_cash_out, hour_of_day, dest_was_sender_before
FROM features_v2
ORDER BY step, txn_id
"""

print("Reading from MySQL... (1 to 3 minutes)")
df = pd.read_sql(QUERY, engine)
print("Loaded:", df.shape)

# ---------- Time-based split ----------
df["split"] = np.select(
    [df.step <= 500, df.step <= 620],
    ["train", "val"],
    default="test",
)

# ---------- Summary ----------
print("\n=== Split summary ===")
for name in ["train", "val", "test"]:
    d = df[df.split == name]
    nd = d[(d.orig_drained == 0) & (d.is_fraud == 1)]
    print(f"{name:5s} steps {d.step.min():3d}-{d.step.max():3d} | rows {len(d):8d} | "
          f"frauds {int(d.is_fraud.sum()):5d} ({d.is_fraud.mean() * 100:.3f}%) | "
          f"frauds NOT drained {len(nd)}")

tr_max = df[df.split == "train"].step.max()
va_min = df[df.split == "val"].step.min()
va_max = df[df.split == "val"].step.max()
te_min = df[df.split == "test"].step.min()
assert tr_max < va_min and va_max < te_min, "Splits overlap in time"
print("\nNo time overlap between splits.")

# ---------- Save ----------
df["type"] = df["type"].astype("category")
df.to_parquet(OUT, index=False)
print(f"Saved {OUT} ({OUT.stat().st_size / 1e6:.0f} MB)")

# ---------- Drift check: dest_prior_cnt grows over time (cumulative history) ----------
print("\n=== Mean dest_prior_cnt and first-time share by split ===")
print(df.groupby("split").agg(mean_prior=("dest_prior_cnt", "mean"),
                              first_time=("dest_prior_cnt", lambda s: (s == 0).mean())))