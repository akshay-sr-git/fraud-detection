import mysql from 'mysql2/promise';
import { config } from './config.js';

export const pool = mysql.createPool({
  ...config.db,
  waitForConnections: true,
  connectionLimit: 10,
  namedPlaceholders: true,
  decimalNumbers: true, // DECIMAL columns come back as numbers, not strings
  timezone: 'Z',
});

// Keep every session in UTC so CURRENT_TIMESTAMP defaults match what Node expects
pool.pool.on('connection', (conn) => {
  conn.query("SET time_zone = '+00:00'");
});

export async function pingDb() {
  const [rows] = await pool.query('SELECT 1 AS ok');
  return rows[0].ok === 1;
}

