USE fraud;

DROP TABLE IF EXISTS features_v2;

CREATE TABLE features_v2 AS
SELECT
  f.*,
  (f.old_bal_org - f.amount - f.new_bal_org)   AS err_orig,
  (f.old_bal_dest + f.amount - f.new_bal_dest) AS err_dest,
  (f.new_bal_org = 0 AND f.amount = f.old_bal_org) AS orig_drained,
  (f.old_bal_dest = 0)                         AS dest_bal_zero_before,
  f.amount / NULLIF(f.old_bal_org, 0)          AS amt_ratio,
  (f.type = 'CASH_OUT')                        AS is_cash_out,
  (f.step % 24)                                AS hour_of_day,
  EXISTS (SELECT 1 FROM transactions o
          WHERE o.name_orig = f.name_dest AND o.step < f.step) AS dest_was_sender_before
FROM features f;

ALTER TABLE features_v2 ADD PRIMARY KEY (txn_id), ADD INDEX idx_v2_step (step);