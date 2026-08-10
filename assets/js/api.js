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
    // 一併清掉 /users/me 的權限快取，避免換人登入後沿用前一位使用者的權限
    try { sessionStorage.removeItem('off_me'); } catch { /* 無 sessionStorage 時忽略 */ }
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
    // 權限變更走獨立端點（需 user:write；授予 super admin 需 super admin）
    setPermissions: (id, perms) => offRequest('PUT', `/users/${id}/permissions`, perms),
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
    // 角色指派：branch_id 為 null 代表全組織範圍
    listAssignees: (id) => offRequest('GET', `/roles/${id}/assignees`),
    assign:   (id, user_id, branch_id = null) =>
      offRequest('POST', `/roles/${id}/assignees`, { user_id, branch_id }),
    unassign: (id, assignment_id) =>
      offRequest('DELETE', `/roles/${id}/assignees/${assignment_id}`),
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

/* ---------- 管理控制台存取權限 ----------
 * 後端只強制「寫入」權限（require_permission）；`read` 用於決定 UI 顯示什麼。
 * 資料來源為 GET /users/me 的 effective_permissions —— 該欄位已由後端合併群組
 * 繼承與 admin 群組的全域權，前端無法自行推導，務必用它而非 user.permissions。
 *
 * 下表把頁面／模組對應到 14 個權限鍵。以 href 前綴比對，最長者優先。
 * 值可為單一權限鍵、權限鍵陣列（具備其中任一即可）、null（不管制），
 * 或 OFF_PERM_SUPER（僅 super admin）。
 *
 * 陣列的用途：模組入口（如預約管理）底下含多種權限的頁面，只要使用者能讀其中
 * 任何一頁就該看得到入口，否則會出現「有子頁權限卻進不去模組」的死路。 */
const OFF_PERM_SUPER = '@super';
const OFF_MODULE_PERMISSION = {
  'reservation-': ['reservation', 'resource'],  // 預約單 + 資源（會議室/設備）
  'ticket-':      'support',         // 工單管理 → 支援管理者
  'signage-':     'panel',           // 電子標牌 → 面板管理者
  'media-library':'panel',           // 媒體庫（標牌內容）
  'room-control': 'av',              // 房間控制 → 音訊/視訊設備管理器
  'org-':         'user',            // 組織目錄 → 用戶管理者
  'system-':      OFF_PERM_SUPER,    // 系統設定/審計：14 鍵中無對應項，限 super admin
  'broadcast-':   null,              // 廣播：14 個權限鍵中無對應項
  'map':          null,              // 地圖：一般使用者導航功能
};

/** 由頁面路徑推出所需權限鍵；找不到對應則回 null（不管制）。 */
function offPermissionForHref(href) {
  const page = (href || '').split('/').pop().split('?')[0];
  const match = Object.entries(OFF_MODULE_PERMISSION)
    .filter(([prefix]) => page.startsWith(prefix))
    .sort(([a], [b]) => b.length - a.length)[0];   // 最長前綴優先
  return match ? match[1] : null;
}

const OFF_ME_KEY = 'off_me';

/** 取得並快取 /users/me（含有效權限）。回傳 null 表示未登入或取得失敗。 */
async function offLoadMe(force = false) {
  if (!OffAuth.token()) return null;
  if (!force) {
    try {
      const cached = sessionStorage.getItem(OFF_ME_KEY);
      if (cached) return JSON.parse(cached);
    } catch { /* 快取毀損則重新取得 */ }
  }
  try {
    const me = await OffAPI.me();
    try { sessionStorage.setItem(OFF_ME_KEY, JSON.stringify(me)); } catch { /* 忽略 */ }
    return me;
  } catch {
    return null;   // 取不到權限時不封鎖畫面；寫入仍由後端把關
  }
}

/** 是否具備讀取權（write 亦視為可讀）。permKey 可為字串、陣列或 null。 */
function offCanRead(me, permKey) {
  if (!permKey || (Array.isArray(permKey) && !permKey.length)) return true;  // 不管制
  if (!me) return true;                               // 資訊不足 → 不管制
  if (Array.isArray(permKey)) return permKey.some(k => offCanRead(me, k));   // 任一即可
  if (permKey === OFF_PERM_SUPER) return !!me.is_super_admin;
  if (me.is_admin || me.is_super_admin) return true;
  const flags = (me.effective_permissions || {})[permKey];
  return !!(flags && (flags.read || flags.write));
}

window.OffAuth = OffAuth;
window.OffAPI  = OffAPI;
window.offLoadMe = offLoadMe;
window.offCanRead = offCanRead;
window.offPermissionForHref = offPermissionForHref;
window.OFF_MODULE_PERMISSION = OFF_MODULE_PERMISSION;
