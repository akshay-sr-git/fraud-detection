import { Router } from 'express';
import { pool } from '../db.js';
import { authenticate, authorize } from '../middleware/auth.js';

const router = Router();
router.use(authenticate, authorize('admin'));

router.get('/', async (req, res) => {
  const [rows] = await pool.query(
    'SELECT id, email, full_name, role, is_active, last_login_at, created_at FROM users ORDER BY id',
  );
  res.json({ users: rows });
});

export default router;