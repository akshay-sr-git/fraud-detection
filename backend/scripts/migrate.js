import 'dotenv/config';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import mysql from 'mysql2/promise';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'sql');

const conn = await mysql.createConnection({
  host: process.env.DB_HOST,
  port: Number(process.env.DB_PORT),
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  multipleStatements: true,
});

// 000_init_db.sql needs root, so it's run manually and skipped here
const files = (await fs.readdir(dir))
  .filter((f) => /^\d{3}_.*\.sql$/.test(f) && !f.startsWith('000_'))
  .sort();

for (const f of files) {
  console.log('Running', f);
  await conn.query(await fs.readFile(path.join(dir, f), 'utf8'));
}

const [tables] = await conn.query('SHOW TABLES');
console.log('Tables:', tables.map((t) => Object.values(t)[0]).join(', '));
await conn.end();