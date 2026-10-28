import 'dotenv/config';

const BASE = process.env.BASE_URL || 'http://127.0.0.1:4000';
let failures = 0;

function check(name, cond, extra = '') {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${cond ? '' : '  -> ' + extra}`);
  if (!cond) failures++;
}

async function call(method, path, { body, token, cookie } = {}) {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  if (cookie) headers.Cookie = cookie;
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  let json = null;
  try { json = await res.json(); } catch { /* empty body */ }
  const setCookie = res.headers.getSetCookie().find((c) => c.startsWith('refresh_token=')) ?? null;
  return { status: res.status, json, setCookie, cookie: setCookie ? setCookie.split(';')[0] : null };
}

const email = `smoke_${Date.now()}@example.com`;
const pw = 'Sup3r-secret-pass';
const user = { email, password: pw, full_name: 'Smoke Test' };

let r = await call('POST', '/api/auth/register', { body: { ...user, password: 'short' } });
check('register: short password rejected (400)', r.status === 400, r.status);

r = await call('POST', '/api/auth/register', { body: user });
check('register: ok (201), role analyst', r.status === 201 && r.json?.user?.role === 'analyst', JSON.stringify(r.json));

r = await call('POST', '/api/auth/register', { body: user });
check('register: duplicate email (409)', r.status === 409, r.status);

r = await call('POST', '/api/auth/login', { body: { email, password: 'wrong-password-1' } });
check('login: wrong password (401)', r.status === 401, r.status);

r = await call('POST', '/api/auth/login', { body: { email, password: pw } });
check('login: ok (200) with token + cookie', r.status === 200 && !!r.json?.accessToken && !!r.cookie, r.status);
check('cookie is HttpOnly + SameSite=Strict', /HttpOnly/i.test(r.setCookie ?? '') && /SameSite=Strict/i.test(r.setCookie ?? ''), r.setCookie);
const token1 = r.json.accessToken;
const cookie1 = r.cookie;

r = await call('GET', '/api/auth/me', { token: token1 });
check('me: ok with token', r.status === 200 && r.json?.user?.email === email, r.status);

r = await call('GET', '/api/auth/me');
check('me: no token (401)', r.status === 401, r.status);

r = await call('GET', '/api/auth/me', { token: token1.slice(0, -2) + 'xx' });
check('me: tampered token (401)', r.status === 401 && r.json?.code === 'TOKEN_INVALID', JSON.stringify(r.json));

r = await call('GET', '/api/users', { token: token1 });
check('users: analyst forbidden (403)', r.status === 403, r.status);

r = await call('POST', '/api/auth/refresh', { cookie: cookie1 });
check('refresh: rotates (200, new cookie)', r.status === 200 && !!r.cookie && r.cookie !== cookie1, r.status);
const cookie2 = r.cookie;

r = await call('POST', '/api/auth/refresh', { cookie: cookie1 });
check('refresh: reused old token rejected (401)', r.status === 401, r.status);

r = await call('POST', '/api/auth/refresh', { cookie: cookie2 });
check('refresh: reuse revoked ALL sessions (401)', r.status === 401, r.status);

r = await call('POST', '/api/auth/login', { body: { email, password: pw } });
const cookie3 = r.cookie;
r = await call('POST', '/api/auth/logout', { cookie: cookie3 });
check('logout: 204', r.status === 204, r.status);
r = await call('POST', '/api/auth/refresh', { cookie: cookie3 });
check('refresh after logout rejected (401)', r.status === 401, r.status);

for (let i = 0; i < 5; i++) {
  await call('POST', '/api/auth/login', { body: { email, password: `wrong-password-${i}` } });
}
r = await call('POST', '/api/auth/login', { body: { email, password: pw } });
check('lockout: correct password blocked after 5 failures (423)', r.status === 423, r.status);

const adminEmail = process.env.SEED_ADMIN_EMAIL;
const adminPw = process.env.SEED_ADMIN_PASSWORD;
if (adminEmail && adminPw) {
  r = await call('POST', '/api/auth/login', { body: { email: adminEmail.toLowerCase(), password: adminPw } });
  check('admin login (200)', r.status === 200 && r.json?.user?.role === 'admin', r.status);
  const adminToken = r.json?.accessToken;
  r = await call('GET', '/api/users', { token: adminToken });
  check('users: admin allowed (200), smoke user listed', r.status === 200 && r.json?.users?.some((u) => u.email === email), r.status);
} else {
  console.log('SKIP  admin checks (SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD not set)');
}

console.log(failures ? `\n${failures} check(s) FAILED` : '\nAll checks passed');
process.exit(failures ? 1 : 0);