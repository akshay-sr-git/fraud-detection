import getpass
import time
from pathlib import Path

import pymysql

pw = getpass.getpass("Enter your MySQL root password: ")
conn = pymysql.connect(host="localhost", user="root", password=pw,
                       database="fraud", autocommit=True)
cur = conn.cursor()

# ---------- 1. Build the features table ----------
sql_file = Path(__file__).resolve().parents[1] / "sql" / "03_window_features.sql"
statements = [s.strip() for s in sql_file.read_text(encoding="utf-8").split(";") if s.strip()]

print("Building features... (1 to 5 minutes, don't close the terminal)")
t = time.time()
for s in statements:
    cur.execute(s)
print(f"Done in {time.time() - t:.0f}s")

# ---------- 2. Counts ----------
cur.execute("SELECT COUNT(*), SUM(is_fraud), SUM(dest_hrs_since_prev IS NULL) FROM features")
n, frauds, null_prev = cur.fetchone()
print(f"\nrows={n}, frauds={int(frauds)}, first-time dests (NULL hrs_since_prev)={int(null_prev)}")
assert n == 2770409 and int(frauds) == 8213, "Counts wrong, check the SQL"

# ---------- 3. Correctness spot-check against a manual recompute ----------
cur.execute("""
    SELECT txn_id, name_dest, step, dest_cnt_24h, dest_amt_24h, dest_prior_cnt
    FROM features
    WHERE txn_id % 1009 = 0 AND dest_prior_cnt > 0
    LIMIT 40
""")
rows = cur.fetchall()
checked = 0
for txn_id, dest, step, cnt24, amt24, prior in rows:
    cur.execute("""SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM transactions
                   WHERE name_dest = %s AND type IN ('TRANSFER','CASH_OUT')
                     AND step BETWEEN %s AND %s""", (dest, step - 24, step - 1))
    c, a = cur.fetchone()
    cur.execute("""SELECT COUNT(*) FROM transactions
                   WHERE name_dest = %s AND type IN ('TRANSFER','CASH_OUT')
                     AND step < %s""", (dest, step))
    p = cur.fetchone()[0]
    assert c == cnt24 and abs(float(a) - float(amt24)) < 0.01 and p == prior, \
        f"MISMATCH on txn_id {txn_id}"
    checked += 1
print(f"\nSpot-check passed on {checked} rows (manual recompute matches window SQL)")
assert checked > 0, "No rows were checked"

# ---------- 4. Does the signal show up? ----------
print("\n--- Fraud rate: first-time vs repeat destination ---")
cur.execute("""SELECT (dest_prior_cnt = 0) AS first_time, COUNT(*), SUM(is_fraud), AVG(is_fraud)
               FROM features GROUP BY 1""")
for r in cur.fetchall():
    print(r)

print("\n--- Fraud rate by dest_cnt_24h bucket ---")
cur.execute("""SELECT CASE WHEN dest_cnt_24h = 0 THEN '0'
                           WHEN dest_cnt_24h <= 2 THEN '1-2'
                           WHEN dest_cnt_24h <= 5 THEN '3-5'
                           ELSE '6+' END AS bucket,
                      COUNT(*), SUM(is_fraud), AVG(is_fraud)
               FROM features GROUP BY 1 ORDER BY 1""")
for r in cur.fetchall():
    print(r)

conn.close()