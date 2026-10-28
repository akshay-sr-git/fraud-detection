import getpass
import time
from pathlib import Path

import pymysql

pw = getpass.getpass("Enter your MySQL root password: ")
conn = pymysql.connect(host="localhost", user="root", password=pw,
                       database="fraud", autocommit=True)
cur = conn.cursor()

sql_file = Path(__file__).resolve().parents[1] / "sql" / "04_balance_link_features.sql"
statements = [s.strip() for s in sql_file.read_text(encoding="utf-8").split(";") if s.strip()]

print("Building features_v2... (5 to 15 minutes, don't close the terminal)")
t = time.time()
for s in statements:
    cur.execute(s)
print(f"Done in {time.time() - t:.0f}s")

cur.execute("SELECT COUNT(*), SUM(is_fraud) FROM features_v2")
n, frauds = cur.fetchone()
print(f"\nrows={n}, frauds={int(frauds)}")
assert n == 2770409 and int(frauds) == 8213, "Counts wrong"

print("\n--- Account link: dest was a sender before (flag, rows, frauds, fraud rate) ---")
cur.execute("""SELECT dest_was_sender_before, COUNT(*), SUM(is_fraud), AVG(is_fraud)
               FROM features_v2 GROUP BY 1""")
for r in cur.fetchall():
    print(r)

print("\n--- Sender fully drained (flag, rows, frauds, fraud rate) ---")
cur.execute("""SELECT orig_drained, COUNT(*), SUM(is_fraud), AVG(is_fraud)
               FROM features_v2 GROUP BY 1""")
for r in cur.fetchall():
    print(r)

print("\n--- Share of rows with a balance mismatch (is_fraud, orig, dest) ---")
cur.execute("""SELECT is_fraud, AVG(err_orig <> 0), AVG(err_dest <> 0)
               FROM features_v2 GROUP BY is_fraud""")
for r in cur.fetchall():
    print(r)

print("\n--- Dest balance zero before (flag, rows, frauds, fraud rate) ---")
cur.execute("""SELECT dest_bal_zero_before, COUNT(*), SUM(is_fraud), AVG(is_fraud)
               FROM features_v2 GROUP BY 1""")
for r in cur.fetchall():
    print(r)

conn.close()