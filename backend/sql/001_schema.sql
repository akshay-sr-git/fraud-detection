CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  role ENUM('admin','analyst') NOT NULL DEFAULT 'analyst',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  failed_login_attempts INT NOT NULL DEFAULT 0,
  locked_until DATETIME NULL,
  last_login_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  token_hash CHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_rt_hash (token_hash),
  KEY idx_rt_user (user_id),
  CONSTRAINT fk_rt_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS scored_transactions (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  submitted_by BIGINT UNSIGNED NOT NULL,
  tx_type ENUM('TRANSFER','CASH_OUT') NOT NULL,
  amount DECIMAL(15,2) NOT NULL,
  old_bal_org DECIMAL(15,2) NOT NULL,
  old_bal_dest DECIMAL(15,2) NOT NULL,
  risk_score DECIMAL(6,4) NOT NULL,
  is_alert TINYINT(1) NOT NULL,
  threshold DECIMAL(6,4) NOT NULL,
  reasons JSON NULL,
  model_version VARCHAR(20) NOT NULL,
  review_status ENUM('not_required','pending','confirmed_fraud','false_positive') NOT NULL,
  scored_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_st_queue (review_status, scored_at),
  KEY idx_st_scored_at (scored_at),
  KEY idx_st_user (submitted_by),
  CONSTRAINT fk_st_user FOREIGN KEY (submitted_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reviews (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  transaction_id BIGINT UNSIGNED NOT NULL,
  reviewer_id BIGINT UNSIGNED NOT NULL,
  decision ENUM('confirmed_fraud','false_positive') NOT NULL,
  note VARCHAR(500) NULL,
  reviewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_rv_tx (transaction_id),
  KEY idx_rv_reviewer (reviewer_id, reviewed_at),
  CONSTRAINT fk_rv_tx FOREIGN KEY (transaction_id) REFERENCES scored_transactions(id) ON DELETE CASCADE,
  CONSTRAINT fk_rv_user FOREIGN KEY (reviewer_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT UNSIGNED NULL,
  action VARCHAR(50) NOT NULL,
  entity VARCHAR(50) NULL,
  entity_id BIGINT UNSIGNED NULL,
  ip VARCHAR(45) NULL,
  details JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_al_user (user_id, created_at),
  KEY idx_al_action (action, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;    