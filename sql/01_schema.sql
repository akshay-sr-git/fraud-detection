CREATE DATABASE IF NOT EXISTS fraud;
USE fraud;

DROP TABLE IF EXISTS transactions;
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
) ENGINE=InnoDB;