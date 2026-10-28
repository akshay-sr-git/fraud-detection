import 'dotenv/config';

const required = ['DB_HOST', 'DB_PORT', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'JWT_ACCESS_SECRET'];
const missing = required.filter((k) => !process.env[k]);
if (missing.length) {
  throw new Error(`Missing env vars: ${missing.join(', ')} (check backend/.env)`);
}
if (process.env.JWT_ACCESS_SECRET.length < 32) {
  throw new Error('JWT_ACCESS_SECRET must be at least 32 characters');
}

const env = process.env.NODE_ENV || 'development';

export const config = {
  env,
  port: Number(process.env.PORT) || 4000,
  corsOrigin: process.env.CORS_ORIGIN || 'http://localhost:5173',
  db: {
    host: process.env.DB_HOST,
    port: Number(process.env.DB_PORT),
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME,
  },
  jwt: {
    accessSecret: process.env.JWT_ACCESS_SECRET,
    accessTtl: process.env.ACCESS_TOKEN_TTL || '15m',
  },
  refresh: { ttlDays: Number(process.env.REFRESH_TOKEN_TTL_DAYS) || 7 },
  cookieSecure: process.env.COOKIE_SECURE === 'true' || env === 'production',
  bcryptRounds: Number(process.env.BCRYPT_ROUNDS) || 12,
  allowRegistration: process.env.ALLOW_REGISTRATION !== 'false',
  lockout: { maxAttempts: 5, minutes: 15 },
};