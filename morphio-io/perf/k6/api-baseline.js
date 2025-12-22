import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_duration: ['p(95)<400'],
    http_req_failed: ['rate<0.01'],
  },
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 20),
      duration: __ENV.DURATION || '2m',
    },
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export function setup() {
  const email = `k6_${Math.random().toString(36).slice(2, 8)}@example.com`;
  const payload = JSON.stringify({
    email,
    password: 'StrongP@ssw0rd!',
    display_name: 'k6_user',
  });
  const headers = { 'Content-Type': 'application/json' };
  const res = http.post(`${BASE_URL}/auth/register`, payload, { headers });
  check(res, { 'register 200': (r) => r.status === 200 });
  const data = res.json();
  const token = data?.data?.access_token || '';
  return { token };
}

export default function (data) {
  // 1) Health
  const h = http.get(`${BASE_URL}/health/`);
  check(h, { 'health 200': (r) => r.status === 200 });

  // 2) CSRF + refresh-token cookie flow
  const csrf = http.get(`${BASE_URL}/auth/csrf-token`);
  check(csrf, { 'csrf 200': (r) => r.status === 200 });
  const token = csrf.json()?.data?.csrf_token;
  if (token) {
    const r = http.post(`${BASE_URL}/auth/refresh-token`, null, {
      headers: { 'X-CSRF-Token': token },
    });
    check(r, { 'refresh 200/401/429 acceptable': (resp) => [200, 401, 429].includes(resp.status) });
  }

  // 3) Authenticated profile
  const authHeaders = { Authorization: `Bearer ${data.token}` };
  const me = http.get(`${BASE_URL}/user/profile`, { headers: authHeaders });
  check(me, { 'profile 200/401 acceptable': (r) => [200, 401].includes(r.status) });

  sleep(1);
}

