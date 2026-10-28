import crypto from 'node:crypto';
import jwt from 'jsonwebtoken';
import { config } from '../config.js';

export function signAccessToken(user) {
  return jwt.sign({ role: user.role }, config.jwt.accessSecret, {
    algorithm: 'HS256',
    expiresIn: config.jwt.accessTtl,
    subject: String(user.id),
  });
}

export function verifyAccessToken(token) {
  // Pinning the algorithm prevents "alg: none" and algorithm-confusion attacks
  return jwt.verify(token, config.jwt.accessSecret, { algorithms: ['HS256'] });
}

export const newRefreshToken = () => crypto.randomBytes(48).toString('base64url');
export const hashToken = (t) => crypto.createHash('sha256').update(t).digest('hex');