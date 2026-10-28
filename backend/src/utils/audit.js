import { pool } from '../db.js';

export async function audit(req, { userId = null, action, entity = null, entityId = null, details = null }) {
  try {
    await pool.query(
      'INSERT INTO audit_log (user_id, action, entity, entity_id, ip, details) VALUES (?, ?, ?, ?, ?, ?)',
      [userId, action, entity, entityId, req.ip ?? null, details ? JSON.stringify(details) : null],
    );
  } catch (e) {
    // A logging failure must never break the request
    console.error('audit log failed:', e.message);
  }
}