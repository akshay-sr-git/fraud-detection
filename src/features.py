# Tier A: no balance information at all
HONEST_FEATURES = [
    "amount", "is_cash_out", "hour_of_day",
    "dest_cnt_6h", "dest_cnt_24h", "dest_amt_24h",
    "dest_prior_cnt", "dest_hrs_since_prev",
]

# Tier B: A + balances known BEFORE the transaction executes (headline model)
PRE_TXN_FEATURES = HONEST_FEATURES + [
    "old_bal_org", "old_bal_dest", "amt_ratio", "dest_bal_zero_before",
]

# Tier C extras: post-transaction values and simulator artifacts (leak demo only)
POST_TXN_FEATURES = [
    "new_bal_org", "new_bal_dest", "err_orig", "err_dest", "orig_drained",
]

ALL_FEATURES = PRE_TXN_FEATURES + POST_TXN_FEATURES
# Never used: dest_was_sender_before (no signal), is_flagged (dataset's own rule)