import 'dotenv/config';
import bcrypt from 'bcryptjs';
import { pool } from '../src/db.js';
import { config } from '../src/config.js';

const email = (process.env.SEED_ADMIN_EMAIL || '').trim().toLowerCase();
const password = process.env.SEED_ADMIN_PASSWORD || '';
if (!email || password.length < 10) {
  console.error('Set SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD (min 10 chars) in backend/.env');
  process.exit(1);
}

const hash = await bcrypt.hash(password, config.bcryptRounds);
await pool.query(
  `INSERT INTO users (email, password_hash, full_name, role)
   VALUES (?, ?, 'Admin', 'admin') AS new_row
   ON DUPLICATE KEY UPDATE password_hash = new_row.password_hash, role = 'admin',
     is_active = 1, failed_login_attempts = 0, locked_until = NULL`,
  [email, hash],
);
console.log(`Admin ready: ${email}`);
await pool.end();