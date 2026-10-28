import { verifyAccessToken } from '../utils/tokens.js';

export function authenticate(req, res, next) {
  const [scheme, token] = (req.headers.authorization || '').split(' ');
  if (scheme !== 'Bearer' || !token) {
    return res.status(401).json({ error: 'Missing or malformed Authorization header' });
  }
  try {
    const payload = verifyAccessToken(token);
    req.user = { id: Number(payload.sub), role: payload.role };
    next();
  } catch (e) {
    const expired = e.name === 'TokenExpiredError';
    return res.status(401).json({
      error: expired ? 'Access token expired' : 'Invalid token',
      code: expired ? 'TOKEN_EXPIRED' : 'TOKEN_INVALID',
    });
  }
}

export const authorize = (...roles) => (req, res, next) => {
  if (!req.user || !roles.includes(req.user.role)) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  next();
};