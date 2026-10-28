USE fraud;

DROP TABLE IF EXISTS features;

CREATE TABLE features AS
SELECT
  t.txn_id, t.step, t.type, t.amount,
  t.name_orig, t.old_bal_org, t.new_bal_org,
  t.name_dest, t.old_bal_dest, t.new_bal_dest,
  t.is_fraud, t.is_flagged,

  COUNT(*) OVER (w RANGE BETWEEN 6 PRECEDING AND 1 PRECEDING) AS dest_cnt_6h,
  COUNT(*) OVER (w RANGE BETWEEN 24 PRECEDING AND 1 PRECEDING) AS dest_cnt_24h,
  COALESCE(SUM(t.amount) OVER (w RANGE BETWEEN 24 PRECEDING AND 1 PRECEDING), 0) AS dest_amt_24h,
  COUNT(*) OVER (w RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS dest_prior_cnt,
  t.step - MAX(t.step) OVER (w RANGE BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS dest_hrs_since_prev
FROM transactions t
WHERE t.type IN ('TRANSFER', 'CASH_OUT')
WINDOW w AS (PARTITION BY t.name_dest ORDER BY t.step);

ALTER TABLE features ADD PRIMARY KEY (txn_id), ADD INDEX idx_f_step (step);