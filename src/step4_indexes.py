import getpass
import time

import pymysql

pw = getpass.getpass("Enter your MySQL root password: ")
conn = pymysql.connect(host="localhost", user="root", password=pw,
                       database="fraud", autocommit=True)
cur = conn.cursor()


def run(sql):
    cur.execute(sql)
    return cur.fetchall()


def timed(sql):
    t = time.time()
    cur.execute(sql)
    rows = cur.fetchall()
    return rows, time.time() - t


# ---------- 1. Row count check ----------
n, frauds = run("SELECT COUNT(*), SUM(is_fraud) FROM transactions")[0]
print("rows, frauds:", n, int(frauds))
assert n == 6362620, "Row count wrong, redo Step 3"

# ---------- 2. Sanity checks ----------
print("\n--- Nulls ---")
print(run("""SELECT SUM(type IS NULL), SUM(amount IS NULL), SUM(name_orig IS NULL),
                    SUM(name_dest IS NULL), SUM(is_fraud IS NULL)
             FROM transactions"""))

print("\n--- step range ---")
print(run("SELECT MIN(step), MAX(step) FROM transactions"))

print("\n--- amount <= 0 (count, of which fraud) ---")
print(run("SELECT COUNT(*), SUM(is_fraud) FROM transactions WHERE amount <= 0"))

print("\n--- txns and fraud per type ---")
for row in run("""SELECT type, COUNT(*), SUM(is_fraud) FROM transactions
                  GROUP BY type ORDER BY 2 DESC"""):
    print(row)

# ---------- 3. Lookup speed BEFORE indexes ----------
LOOKUP = """SELECT COUNT(*), SUM(amount) FROM transactions
            WHERE name_dest = 'C1286084959' AND step BETWEEN 1 AND 743"""

print("\n--- Lookup BEFORE index ---")
rows, secs = timed(LOOKUP)
print(rows, f"-> {secs:.3f}s")
print("EXPLAIN:", run("EXPLAIN " + LOOKUP)[0][3:8])  # table, partitions, type, possible_keys, key

# ---------- 4. Create indexes ----------
print("\nCreating indexes... (3 to 10 minutes, don't close the terminal)")
t = time.time()
try:
    cur.execute("""ALTER TABLE transactions
                   ADD INDEX idx_dest_step (name_dest, step),
                   ADD INDEX idx_orig_step (name_orig, step),
                   ADD INDEX idx_step (step)""")
    print(f"Indexes created in {time.time() - t:.0f}s")
except pymysql.err.OperationalError as e:
    print("Index step skipped:", e)  # e.g. duplicate key name if you rerun
cur.execute("ANALYZE TABLE transactions")
cur.fetchall()

# ---------- 5. Lookup speed AFTER indexes ----------
print("\n--- Lookup AFTER index ---")
rows, secs = timed(LOOKUP)
print(rows, f"-> {secs:.4f}s")
print("EXPLAIN:", run("EXPLAIN " + LOOKUP)[0][3:8])

print("\n--- Indexes on table ---")
for r in run("SHOW INDEX FROM transactions"):
    print(r[2], r[4])

conn.close()