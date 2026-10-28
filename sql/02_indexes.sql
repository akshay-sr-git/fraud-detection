USE fraud;
ALTER TABLE transactions
  ADD INDEX idx_dest_step (name_dest, step),
  ADD INDEX idx_orig_step (name_orig, step),
  ADD INDEX idx_step (step);
ANALYZE TABLE transactions;