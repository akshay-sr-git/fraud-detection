import { Router } from 'express';
import bcrypt from 'bcryptjs';
import { z } from 'zod';
import { pool } from '../db.js';
import { config } from '../config.js';
import { validate } from '../middleware/validate.js';
import { authenticate } from '../middleware/auth.js';
import { signAccessToken, newRefreshToken, hashToken } from '../utils/tokens.js';
import { audit } from '../utils/audit.js';

const router = Router();

const email = z.string().trim().toLowerCase().email().max(255);
const password = z
  .string()
  .min(10, 'Password must be at least 10 characters')
  .refine((p) => Buffer.byteLength(p, 'utf8') <= 72, 'Password must be at most 72 bytes');

const registerSchema = z.object({ email, password, full_name: z.string().trim().min(2).max(120) });
const loginSchema = z.object({ email, password: z.string().min(1).max(200) });

// Used when the email is unknown, so "no such user" takes as long as "wrong password"
const DUMMY_HASH = bcrypt.hashSync('dummy-password-for-timing', config.bcryptRounds);

const REFRESH_COOKIE = 'refresh_token';
const cookieBase = { httpOnly: true, secure: config.cookieSecure, sameSite: 'strict', path: '/api/auth' };
const setRefreshCookie = (res, token) =>
  res.cookie(REFRESH_COOKIE, token, { ...cookieBase, maxAge: config.refresh.ttlDays * 86400000 });
const clearRefreshCookie = (res) => res.clearCookie(REFRESH_COOKIE, cookieBase);

const publicUser = (u) => ({ id: u.id, email: u.email, full_name: u.full_name, role: u.role });

async function issueSession(res, user, conn = pool) {
  const refresh = newRefreshToken();
  const expiresAt = new Date(Date.now() + config.refresh.ttlDays * 86400000);
  await conn.query(
    'INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)',
    [user.id, hashToken(refresh), expiresAt],
  );
  setRefreshCookie(res, refresh);
  return signAccessToken(user);
}

router.post('/register', validate(registerSchema), async (req, res) => {
  if (!config.allowRegistration) {
    return res.status(403).json({ error: 'Registration is disabled' });
  }
  const { email: mail, password: pw, full_name } = req.body;
  const hash = await bcrypt.hash(pw, config.bcryptRounds);
  try {
    const [result] = await pool.query(
      "INSERT INTO users (email, password_hash, full_name, role) VALUES (?, ?, ?, 'analyst')",
      [mail, hash, full_name],
    );
    await audit(req, { userId: result.insertId, action: 'register', entity: 'user', entityId: result.insertId });
    return res.status(201).json({ user: { id: result.insertId, email: mail, full_name, role: 'analyst' } });
  } catch (e) {
    if (e.code === 'ER_DUP_ENTRY') return res.status(409).json({ error: 'Email already registered' });
    throw e;
  }
});

router.post('/login', validate(loginSchema), async (req, res) => {
  const { email: mail, password: pw } = req.body;
  const [rows] = await pool.query('SELECT * FROM users WHERE email = ?', [mail]);
  const user = rows[0];

  if (!user) {
    await bcrypt.compare(pw, DUMMY_HASH);
    await audit(req, { action: 'login_failed', details: { email: mail, reason: 'unknown_user' } });
    return res.status(401).json({ error: 'Invalid email or password' });
  }

  if (user.locked_until && user.locked_until > new Date()) {
    const mins = Math.ceil((user.locked_until - new Date()) / 60000);
    await audit(req, { userId: user.id, action: 'login_blocked_locked' });
    return res.status(423).json({ error: `Account locked. Try again in ${mins} minute(s).` });
  }

  const ok = await bcrypt.compare(pw, user.password_hash);
  if (!ok) {
    const attempts = user.failed_login_attempts + 1;
    const lock = attempts >= config.lockout.maxAttempts;
    await pool.query('UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?', [
      lock ? 0 : attempts,
      lock ? new Date(Date.now() + config.lockout.minutes * 60000) : null,
      user.id,
    ]);
    await audit(req, { userId: user.id, action: lock ? 'account_locked' : 'login_failed' });
    return res.status(401).json({ error: 'Invalid email or password' });
  }

  if (!user.is_active) {
    return res.status(403).json({ error: 'Account disabled' });
  }

  await pool.query(
    'UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login_at = NOW() WHERE id = ?',
    [user.id],
  );
  const accessToken = await issueSession(res, user);
  await audit(req, { userId: user.id, action: 'login_success' });
  res.json({ accessToken, user: publicUser(user) });
});

router.post('/refresh', async (req, res) => {
  const raw = req.cookies?.[REFRESH_COOKIE];
  if (!raw) return res.status(401).json({ error: 'No refresh token' });

  const conn = await pool.getConnection();
  try {
    await conn.beginTransaction();
    const [rows] = await conn.query(
      'SELECT * FROM refresh_tokens WHERE token_hash = ? FOR UPDATE',
      [hashToken(raw)],
    );
    const row = rows[0];

    if (!row) {
      await conn.rollback();
      clearRefreshCookie(res);
      return res.status(401).json({ error: 'Invalid refresh token' });
    }

    if (row.revoked_at) {
      // An already-rotated token came back: treat it as stolen and kill every session of this user
      await conn.query(
        'UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = ? AND revoked_at IS NULL',
        [row.user_id],
      );
      await conn.commit();
      await audit(req, { userId: row.user_id, action: 'refresh_reuse_detected' });
      clearRefreshCookie(res);
      return res.status(401).json({ error: 'Session invalid. Please log in again.' });
    }

    if (row.expires_at < new Date()) {
      await conn.rollback();
      clearRefreshCookie(res);
      return res.status(401).json({ error: 'Session expired. Please log in again.' });
    }

    const [users] = await conn.query('SELECT * FROM users WHERE id = ?', [row.user_id]);
    const user = users[0];
    if (!user || !user.is_active) {
      await conn.query('UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = ?', [row.id]);
      await conn.commit();
      clearRefreshCookie(res);
      return res.status(401).json({ error: 'Account unavailable' });
    }

    await conn.query('UPDATE refresh_tokens SET revoked_at = NOW() WHERE id = ?', [row.id]);
    const accessToken = await issueSession(res, user, conn);
    await conn.commit();
    return res.json({ accessToken, user: publicUser(user) });
  } catch (e) {
    await conn.rollback();
    throw e;
  } finally {
    conn.release();
  }
});

router.post('/logout', async (req, res) => {
  const raw = req.cookies?.[REFRESH_COOKIE];
  if (raw) {
    await pool.query(
      'UPDATE refresh_tokens SET revoked_at = NOW() WHERE token_hash = ? AND revoked_at IS NULL',
      [hashToken(raw)],
    );
  }
  clearRefreshCookie(res);
  res.status(204).end();
});

router.get('/me', authenticate, async (req, res) => {
  const [rows] = await pool.query(
    'SELECT id, email, full_name, role, is_active FROM users WHERE id = ?',
    [req.user.id],
  );
  const user = rows[0];
  if (!user || !user.is_active) return res.status(401).json({ error: 'Account unavailable' });
  res.json({ user: publicUser(user) });
});

export default router;