import { Router } from 'express';
import { pingDb } from '../db.js';

const router = Router();

router.get('/', async (req, res) => {
  let db = 'down';
  try {
    db = (await pingDb()) ? 'up' : 'down';
  } catch {
    // leave as 'down'
  }
  res.status(db === 'up' ? 200 : 503).json({
    status: db === 'up' ? 'ok' : 'degraded',
    db,
    uptime_s: Math.round(process.uptime()),
  });
});

export default router;