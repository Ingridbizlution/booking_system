/* Offision 前端 API client
 * - JWT 儲存於 localStorage
 * - 401 自動導向登入
 * ------------------------------------------------------------ */

window.OFF_API_BASE = window.OFF_API_BASE || 'http://localhost:8080/api/v1';
const TOKEN_KEY = 'off_token';
const USER_KEY  = 'off_user';

const OffAuth = {
  token()  { return localStorage.getItem(TOKEN_KEY); },
  user()   { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; } },
  save(tokenInfo) {
    localStorage.setItem(TOKEN_KEY, tokenInfo.access_token);
    localStorage.setItem(USER_KEY, JSON.stringify({
      id: tokenInfo.user_id,
      organization_id: tokenInfo.organization_id,
      display_name: tokenInfo.display_name,
    }));
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  redirectToLogin() {
    // 若目前不在 login 頁，導向 login
    if (!location.pathname.endsWith('/login.html')) {
      const back = encodeURIComponent(location.pathname.split('/').pop() || '');
      location.href = `login.html?next=${back}`;
    }
  },
  requireLogin() {
    if (!this.token()) this.redirectToLogin();
  },
};

async function offRequest(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  const t = OffAuth.token();
  if (t) headers['Authorization'] = `Bearer ${t}`;

  const res = await fetch(`${OFF_API_BASE}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    OffAuth.clear();
    OffAuth.redirectToLogin();
    throw new Error('未授權');
  }
  if (res.status === 204) return null;

  const isJson = (res.headers.get('content-type') || '').includes('application/json');
  const data = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const msg = (data && data.detail) || res.statusText;
    throw new Error(msg);
  }
  return data;
}

const OffAPI = {
  login: (email, password) => offRequest('POST', '/auth/login', { email, password }),
  me:    () => offRequest('GET',  '/users/me'),

  users: {
    list:  (q)       => offRequest('GET',  `/users${q ? `?q=${encodeURIComponent(q)}` : ''}`),
    get:   (id)      => offRequest('GET',  `/users/${id}`),
    create:(payload) => offRequest('POST', '/users', payload),
    patch: (id, p)   => offRequest('PATCH', `/users/${id}`, p),
  },
  branches: {
    list:   () => offRequest('GET', '/branches'),
    create: (p) => offRequest('POST', '/branches', p),
    patch:  (id, p) => offRequest('PATCH', `/branches/${id}`, p),
    remove: (id) => offRequest('DELETE', `/branches/${id}`),
  },
  locations: {
    list:   (branch_id) => offRequest('GET', `/locations${branch_id ? `?branch_id=${branch_id}` : ''}`),
    create: (p) => offRequest('POST', '/locations', p),
    patch:  (id, p) => offRequest('PATCH', `/locations/${id}`, p),
    remove: (id) => offRequest('DELETE', `/locations/${id}`),
  },
  categories: {
    list:   () => offRequest('GET', '/categories'),
    create: (p) => offRequest('POST', '/categories', p),
    patch:  (id, p) => offRequest('PATCH', `/categories/${id}`, p),
    remove: (id) => offRequest('DELETE', `/categories/${id}`),
  },
  roles: {
    list:   () => offRequest('GET', '/roles'),
    create: (p) => offRequest('POST', '/roles', p),
    patch:  (id, p) => offRequest('PATCH', `/roles/${id}`, p),
    remove: (id) => offRequest('DELETE', `/roles/${id}`),
  },
  groups: {
    list:   () => offRequest('GET', '/groups'),
    get:    (id) => offRequest('GET', `/groups/${id}`),
    create: (p) => offRequest('POST', '/groups', p),
    patch:  (id, p) => offRequest('PATCH', `/groups/${id}`, p),
    remove: (id) => offRequest('DELETE', `/groups/${id}`),
    listMembers: (id) => offRequest('GET', `/groups/${id}/members`),
    addMembers:  (id, user_ids) => offRequest('POST', `/groups/${id}/members`, { user_ids }),
    removeMember:(id, uid) => offRequest('DELETE', `/groups/${id}/members/${uid}`),
  },
  rooms: {
    list:   ()      => offRequest('GET', '/rooms'),
    get:    (id)    => offRequest('GET', `/rooms/${id}`),
    create: (p)     => offRequest('POST', '/rooms', p),
    patch:  (id, p) => offRequest('PATCH', `/rooms/${id}`, p),
    remove: (id)    => offRequest('DELETE', `/rooms/${id}`),
    blackouts: {
      list:   (rid)      => offRequest('GET', `/rooms/${rid}/blackouts`),
      create: (rid, p)   => offRequest('POST', `/rooms/${rid}/blackouts`, p),
      remove: (id)       => offRequest('DELETE', `/blackouts/${id}`),
    },
  },
  equipment: {
    list:   ()      => offRequest('GET', '/equipment'),
    get:    (id)    => offRequest('GET', `/equipment/${id}`),
    create: (p)     => offRequest('POST', '/equipment', p),
    patch:  (id, p) => offRequest('PATCH', `/equipment/${id}`, p),
    remove: (id)    => offRequest('DELETE', `/equipment/${id}`),
  },
  amenities: {
    list:   ()      => offRequest('GET', '/amenities'),
    get:    (id)    => offRequest('GET', `/amenities/${id}`),
    create: (p)     => offRequest('POST', '/amenities', p),
    patch:  (id, p) => offRequest('PATCH', `/amenities/${id}`, p),
    remove: (id)    => offRequest('DELETE', `/amenities/${id}`),
    setRooms:     (id, ids) => offRequest('PUT', `/amenities/${id}/rooms`, { resource_ids: ids }),
    setEquipment: (id, ids) => offRequest('PUT', `/amenities/${id}/equipment`, { resource_ids: ids }),
  },
  reservations: {
    list:   (params={}) => {
      const qs = new URLSearchParams(params).toString();
      return offRequest('GET', `/reservations${qs ? `?${qs}` : ''}`);
    },
    create: (p)     => offRequest('POST', '/reservations', p),
    patch:  (id, p) => offRequest('PATCH', `/reservations/${id}`, p),
    approve:(id, p) => offRequest('POST', `/reservations/${id}/approve`, p),
    cancel: (id)    => offRequest('DELETE', `/reservations/${id}`),
  },
  bookingPolicies: {
    list:   ()      => offRequest('GET', '/booking-policies'),
    get:    (id)    => offRequest('GET', `/booking-policies/${id}`),
    create: (p)     => offRequest('POST', '/booking-policies', p),
    patch:  (id, p) => offRequest('PATCH', `/booking-policies/${id}`, p),
    remove: (id)    => offRequest('DELETE', `/booking-policies/${id}`),
  },
  dashboard: {
    reservation: (from_date, to_date) =>
      offRequest('GET', `/dashboard/reservation?from_date=${from_date}&to_date=${to_date}`),
  },
};

window.OffAuth = OffAuth;
window.OffAPI  = OffAPI;
