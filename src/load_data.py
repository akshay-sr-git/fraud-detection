import getpass
import time
from pathlib import Path

import pymysql

CSV = (Path(__file__).resolve().parents[1] / "data" / "paysim.csv").as_posix()
pw = getpass.getpass("Enter your MySQL root password: ")

conn = pymysql.connect(host="localhost", user="root", password=pw,
                       local_infile=True, autocommit=True)
cur = conn.cursor()

cur.execute("SET GLOBAL local_infile = 1")
cur.execute("CREATE DATABASE IF NOT EXISTS fraud")
cur.execute("USE fraud")
cur.execute("DROP TABLE IF EXISTS transactions")
cur.execute("""
CREATE TABLE transactions (
  txn_id        BIGINT AUTO_INCREMENT PRIMARY KEY,
  step          INT,
  type          VARCHAR(20),
  amount        DECIMAL(15,2),
  name_orig     VARCHAR(20),
  old_bal_org   DECIMAL(15,2),
  new_bal_org   DECIMAL(15,2),
  name_dest     VARCHAR(20),
  old_bal_dest  DECIMAL(15,2),
  new_bal_dest  DECIMAL(15,2),
  is_fraud      TINYINT,
  is_flagged    TINYINT
) ENGINE=InnoDB
""")

print("Loading... (a few minutes, don't close the terminal)")
t = time.time()
cur.execute(f"""
LOAD DATA LOCAL INFILE '{CSV}'
INTO TABLE transactions
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\\n'
IGNORE 1 LINES
(step, type, amount, name_orig, old_bal_org, new_bal_org,
 name_dest, old_bal_dest, new_bal_dest, is_fraud, @flag)
SET is_flagged = REPLACE(@flag, '\\r', '')
""")
print(f"Loaded in {time.time() - t:.0f}s")

cur.execute("SELECT COUNT(*), SUM(is_fraud), SUM(is_flagged) FROM transactions")
print("rows, frauds, flagged:", cur.fetchone())
conn.close()