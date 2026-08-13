/* Bizlution FMS 前端 API client —— 後端為 FMS Platform API（/api/v1）
 * ------------------------------------------------------------
 * 契約：bizlution-fms-phase1-main/api/openapi.yaml
 *
 * 三件與舊版（Bizlution FMS 自帶的 FastAPI 後端）不同、而且會咬人的事：
 *
 * 1. **登入是 OAuth 風格的 grant，不是 /auth/login。**
 *    POST /auth/token  { grant_type:'password', tenant_code, username, password }
 *    → { access_token, refresh_token, expires_in, token_type,
 *        tenant_id, user_id, must_change_password }
 *    `username` 這個欄位名是契約定的，但後端的查詢收 **email 或 username**
 *    （fms-identity 的 find_auth_user_by_identifier），本前端一律送 email。
 *
 * 2. **每一個需認證的請求都必須帶 `X-Tenant-ID`。** 伺服器會拿它跟 token 裡的
 *    `tid` 交叉比對，不符回 403 `TENANT_MISMATCH` —— 不是靜默忽略。漏帶是
 *    400 `BAD_REQUEST`。因此 tenant_id 必須跟 token 一起存下來。
 *
 * 3. **access token 很短命。** 實測 `expires_in` 是 900 秒（契約的 example 寫
 *    3600，別照那個算）。因此 401 要能自動用 refresh token 換一次再重試，
 *    否則使用者每 15 分鐘被踢回登入頁。換發會**輪替**：舊的 refresh token
 *    當場失效，新的一定要存回去。
 *
 * 錯誤是 RFC 9457 problem+json，要對 `code` 分支（`detail` 會隨版本改）。
 */

/* config.js 應該先載入；沒載到時給一組本機預設值，讓頁面不會整頁壞掉。 */
window.OFF_API_BASE = window.OFF_API_BASE || 'http://localhost:8080/api/v1';
window.OFF_TENANT_CODE = window.OFF_TENANT_CODE || 'DEMO_GROUP';

const ACCESS_KEY  = 'off_access_token';
const REFRESH_KEY = 'off_refresh_token';
const TENANT_KEY  = 'off_tenant_id';
const USER_ID_KEY = 'off_user_id';
const EXPIRES_KEY = 'off_expires_at';
const USER_KEY    = 'off_user';
const OFF_ME_KEY  = 'off_me';

/** problem+json 帶著結構化資訊，塞進 Error.message 會把 code 弄丟。 */
class OffApiError extends Error {
  constructor(message, { status, code, problem, requestId } = {}) {
    super(message);
    this.name = 'OffApiError';
    this.status = status;
    this.code = code;         // 穩定的機器可讀值，UI 要對這個分支
    this.problem = problem;   // 原始 problem+json，登入頁會整包顯示
    this.requestId = requestId;
  }
}

function offUuid() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  // http://localhost 是 secure context，randomUUID 一般都有；這條只是保險。
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

const OffAuth = {
  token()        { return localStorage.getItem(ACCESS_KEY); },
  refreshToken() { return localStorage.getItem(REFRESH_KEY); },
  tenantId()     { return localStorage.getItem(TENANT_KEY); },
  userId()       { return localStorage.getItem(USER_ID_KEY); },
  user()         { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch { return null; } },

  /** 存 POST /auth/token 或 /auth/token/refresh 的回應。 */
  save(tok) {
    localStorage.setItem(ACCESS_KEY, tok.access_token);
    if (tok.refresh_token) localStorage.setItem(REFRESH_KEY, tok.refresh_token);
    if (tok.tenant_id) localStorage.setItem(TENANT_KEY, tok.tenant_id);
    if (tok.user_id)   localStorage.setItem(USER_ID_KEY, tok.user_id);
    if (tok.expires_in) {
      localStorage.setItem(EXPIRES_KEY, String(Date.now() + tok.expires_in * 1000));
    }
  },

  /** 存 GET /auth/me 的摘要，供頂列頭像／問候語直接讀（不必每頁再打一次 API）。 */
  saveProfile(me) {
    if (!me || !me.user) return;
    localStorage.setItem(USER_KEY, JSON.stringify({
      id: me.user.id,
      username: me.user.username,
      email: me.user.email,
      display_name: me.user.display_name,
      job_title: me.user.job_title,
      tenant_id: me.tenant && me.tenant.id,
      tenant_name: me.tenant && me.tenant.name,
      default_facility_id: me.user.default_facility_id,
    }));
  },

  clear() {
    [ACCESS_KEY, REFRESH_KEY, TENANT_KEY, USER_ID_KEY, EXPIRES_KEY, USER_KEY]
      .forEach(k => localStorage.removeItem(k));
    // 一併清掉 /auth/me 的權限快取，避免換人登入後沿用前一位使用者的權限
    try { sessionStorage.removeItem(OFF_ME_KEY); } catch { /* 無 sessionStorage 時忽略 */ }
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

  /** 撤銷這一個 refresh token 再清本地狀態。撤銷失敗也照樣登出。 */
  async logout() {
    const rt = this.refreshToken();
    if (rt) {
      try { await offRequest('POST', '/auth/logout', { refresh_token: rt }); }
      catch { /* 本地登出不該被伺服器的狀況擋住 */ }
    }
    this.clear();
  },
};

/* ---------- refresh：單一飛行中請求 ----------
 * 一個頁面常常同時發好幾個請求，token 過期時它們會同時拿到 401。若各自去
 * 換發，第一個成功的會把其餘幾個手上的 refresh token 作廢（後端輪替），
 * 結果是使用者被踢出去。因此換發共用同一個 promise。 */
let offRefreshInFlight = null;

async function offRefreshTokens() {
  if (offRefreshInFlight) return offRefreshInFlight;

  const rt = OffAuth.refreshToken();
  if (!rt) return null;

  offRefreshInFlight = (async () => {
    try {
      // 這支端點不需認證，且刻意不走 offRequest —— 否則 401 會遞迴回來換發。
      const res = await fetch(`${OFF_API_BASE}/auth/token/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Request-ID': offUuid() },
        body: JSON.stringify({ refresh_token: rt }),
      });
      if (!res.ok) return null;
      const tok = await res.json();
      OffAuth.save(tok);
      return tok.access_token;
    } catch {
      return null;   // 網路問題與 refresh 失效在此不必區分，兩者都回登入頁
    } finally {
      offRefreshInFlight = null;
    }
  })();

  return offRefreshInFlight;
}

/**
 * 發一個請求。`opts.raw` 為 true 時回 { status, headers, data }，不丟錯 ——
 * 登入畫面要把原始回應（含失敗的）顯示出來，那跟正常業務呼叫的需求相反。
 */
async function offRequest(method, path, body, opts = {}) {
  const send = async () => {
    const headers = { 'Accept': 'application/json', 'X-Request-ID': offUuid() };
    if (body != null) headers['Content-Type'] = 'application/json';

    const t = OffAuth.token();
    if (t) headers['Authorization'] = `Bearer ${t}`;

    // 契約：所有需認證的請求都必須帶 X-Tenant-ID，漏帶是 400。
    const tid = OffAuth.tenantId();
    if (tid) headers['X-Tenant-ID'] = tid;

    return fetch(`${OFF_API_BASE}${path}`, {
      method,
      headers,
      body: body != null ? JSON.stringify(body) : undefined,
    });
  };

  let res = await send();

  // 401 → 換發一次再重試。`opts.noRetry` 給不該重試的呼叫（例如登入本身）。
  if (res.status === 401 && !opts.noRetry && OffAuth.refreshToken()) {
    const fresh = await offRefreshTokens();
    if (fresh) res = await send();
  }

  const ctype = res.headers.get('content-type') || '';
  const isJson = ctype.includes('json');          // application/json 與 problem+json 都吃
  const data = res.status === 204 ? null : (isJson ? await res.json() : await res.text());

  if (opts.raw) {
    return { ok: res.ok, status: res.status, data, requestId: res.headers.get('x-request-id') };
  }

  if (res.status === 401) {
    OffAuth.clear();
    OffAuth.redirectToLogin();
    throw new OffApiError('未授權', { status: 401, code: 'UNAUTHENTICATED', problem: data });
  }

  if (!res.ok) {
    const p = (data && typeof data === 'object') ? data : {};
    throw new OffApiError(p.detail || p.title || res.statusText, {
      status: res.status,
      code: p.code,
      problem: data,
      requestId: res.headers.get('x-request-id') || p.request_id,
    });
  }

  return data;
}

const OffAPI = {
  /**
   * 以 email 登入。契約的欄位名是 `username`，語意是識別碼（email 或
   * username 皆可，見後端 find_auth_user_by_identifier）。
   *
   * 回 { ok, status, data, requestId }，**不丟錯** —— 登入畫面要把 401／422／
   * 429 的 problem+json 原樣顯示給人看。
   */
  login: (email, password, tenantCode) => offRequest('POST', '/auth/token', {
    grant_type: 'password',
    tenant_code: tenantCode || OFF_TENANT_CODE,
    username: email,
    password,
  }, { raw: true, noRetry: true }),

  refresh: () => offRefreshTokens(),

  /** 使用者 + 租戶 + 可用場館 + 角色 + 已展開的權限字串。 */
  me: () => offRequest('GET', '/auth/me'),
  meRaw: () => offRequest('GET', '/auth/me', undefined, { raw: true }),
};

/* ---------- 租戶管理模組 API（2026-08-13 新增）----------
 * 供 tenant-list.html / tenant-payments.html / tenant-categories.html 使用。
 * 目前前端頁面仍為 mock 資料，待後端契約定案後逐頁接上。 */
Object.assign(OffAPI, {
  tenants: {
    list:   (params={}) => {
      const qs = new URLSearchParams(params).toString();
      return offRequest('GET', `/tenants${qs ? `?${qs}` : ''}`);
    },
    get:    (id)    => offRequest('GET',    `/tenants/${id}`),
    create: (p)     => offRequest('POST',   '/tenants', p),
    patch:  (id, p) => offRequest('PATCH',  `/tenants/${id}`, p),
    remove: (id)    => offRequest('DELETE', `/tenants/${id}`),
  },
  tenantPayments: {
    list:   (params={}) => {
      const qs = new URLSearchParams(params).toString();
      return offRequest('GET', `/tenant-payments${qs ? `?${qs}` : ''}`);
    },
    get:      (id)    => offRequest('GET',  `/tenant-payments/${id}`),
    create:   (p)     => offRequest('POST', '/tenant-payments', p),
    summary:  (params={}) => {
      const qs = new URLSearchParams(params).toString();
      return offRequest('GET', `/tenant-payments/summary${qs ? `?${qs}` : ''}`);
    },
  },
  tenantCategories: {
    list:   ()      => offRequest('GET',    '/tenant-categories'),
    get:    (id)    => offRequest('GET',    `/tenant-categories/${id}`),
    create: (p)     => offRequest('POST',   '/tenant-categories', p),
    patch:  (id, p) => offRequest('PATCH',  `/tenant-categories/${id}`, p),
    remove: (id)    => offRequest('DELETE', `/tenant-categories/${id}`),
  },
});

/* ---------- 以下是 Bizlution FMS 舊後端的資源端點，**尚未搬到 FMS 契約** ----------
 * 這一段這次沒有動。它們的路徑與 payload 是舊 FastAPI 後端的形狀，FMS 的
 * 契約不同（分頁是游標不是頁碼、寫入要 If-Match、部分資源根本改了名字：
 * 會議室是 bookable_resources、部門是 organizations、工單是 work-orders）。
 * 因此呼叫它們現在會失敗 —— 多數是 404，少數路徑名稱剛好相同的會因為欄位
 * 不同而 422。
 *
 * 保留而不刪除的理由只有一個：14 個頁面（org-*、reservation-*）直接呼叫
 * 這些方法，刪掉會讓那些頁面在載入時就 TypeError，比一個看得懂的網路錯誤
 * 更難查。搬遷是逐頁對契約的獨立工作，這次的範圍只有登入。 */
Object.assign(OffAPI, {
  users: {
    list:  (q)       => offRequest('GET',  `/users${q ? `?q=${encodeURIComponent(q)}` : ''}`),
    get:   (id)      => offRequest('GET',  `/users/${id}`),
    create:(payload) => offRequest('POST', '/users', payload),
    patch: (id, p)   => offRequest('PATCH', `/users/${id}`, p),
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
});

/* ---------- 管理控制台存取權限 ----------
 * 頁面 → 權限鍵的對照。以 href 前綴比對，最長者優先。
 *
 * **這張表的值還是 Bizlution FMS 舊後端的 14 個權限鍵，FMS 不認得它們。**
 * FMS 的 GET /auth/me 回的是 `permissions: ["work_order:assign@FACILITY:<uuid>",
 * …]`（權限碼@範圍型別:範圍id）與 `roles: [{role_code, scope_type, scope_id}]`，
 * 與這裡的鍵沒有任何交集。把兩邊硬對起來需要一份逐頁決定的對照表，那是獨立
 * 的一件事（且對錯了的症狀是「有權限的人看不到模組」）。
 *
 * 因此現在的行為是：**不隱藏任何模組**（見 offCanRead 對 FMS 形狀的處理）。
 * 寫入權限仍由後端 require_permission 獨立把關，因此這不是安全缺口，只是
 * UI 還沒收斂。表格與 offPermissionForHref 保留，等對照表定案就能接上。 */
const OFF_PERM_SUPER = '@super';
const OFF_MODULE_PERMISSION = {
  'reservation-': ['reservation', 'resource'],  // 預約單 + 資源（會議室/設備）
  'ticket-':      'support',         // 工單管理 → 支援管理者
  'signage-':     'panel',           // 電子標牌 → 面板管理者
  'media-library':'panel',           // 媒體庫（標牌內容）
  'room-control': 'av',              // 房間控制 → 音訊/視訊設備管理器
  'org-':         'user',            // 組織目錄 → 用戶管理者
  'system-':      OFF_PERM_SUPER,    // 系統設定/審計
  'broadcast-':   null,              // 廣播
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

/** 取得並快取 GET /auth/me。回傳 null 表示未登入或取得失敗。 */
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
    OffAuth.saveProfile(me);
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

  // FMS 的 /auth/me（有 permissions 陣列、沒有 effective_permissions）：
  // 這張對照表的鍵在 FMS 不存在，硬比對會把每個模組都判成無權。見上方說明。
  if (Array.isArray(me.permissions) && !me.effective_permissions) return true;

  if (Array.isArray(permKey)) return permKey.some(k => offCanRead(me, k));   // 任一即可
  if (permKey === OFF_PERM_SUPER) return !!me.is_super_admin;
  if (me.is_admin || me.is_super_admin) return true;
  const flags = (me.effective_permissions || {})[permKey];
  return !!(flags && (flags.read || flags.write));
}

window.OffAuth = OffAuth;
window.OffAPI  = OffAPI;
window.OffApiError = OffApiError;
window.offRequest = offRequest;
window.offLoadMe = offLoadMe;
window.offCanRead = offCanRead;
window.offPermissionForHref = offPermissionForHref;
window.OFF_MODULE_PERMISSION = OFF_MODULE_PERMISSION;
