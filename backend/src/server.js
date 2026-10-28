import app from './app.js';
import { config } from './config.js';
import { pingDb } from './db.js';

try {
  await pingDb();
  console.log('MySQL connection OK');
} catch (e) {
  console.error('MySQL connection FAILED:', e.message);
  process.exit(1);
}

app.listen(config.port, () => {
  console.log(`API listening on http://127.0.0.1:${config.port}`);
});