/* Offision 前端共通行為
 * - 為每個模組定義側邊導覽
 * - 依 body[data-module][data-page] 標示 active
 * - 提供 Modal 顯示/隱藏
 * ------------------------------------------------------------ */

const OFF_NAV = {
  reservation: {
    icon: 'calendar-event',
    color: 'linear-gradient(135deg, #58c7f5, #1f80f0)',
    title: '預約管理',
    items: [
      { key: 'dashboard', label: '資訊主頁', icon: 'layout-dashboard', href: 'reservation-dashboard.html' },
      { key: 'booking',   label: '預約',      icon: 'calendar', children: [
        { key: 'calendar', label: '管理日曆', href: 'reservation-calendar.html', isNew: true },
        { key: 'approval', label: '預約審批', href: 'reservation-approval.html', isNew: true }
      ]},
      { key: 'analytics', label: '分析',      icon: 'chart-bar', children: [
        { key: 'usage',    label: '資源使用分析', href: '#' },
        { key: 'absence',  label: '缺席分析',     href: '#' },
        { key: 'user',     label: '使用者資源使用', href: '#' },
        { key: 'insights', label: '迅速洞察',     href: '#' },
        { key: 'reserve',  label: '預約分析',     href: '#' },
        { key: 'report',   label: '報告',        href: '#' }
      ]},
      { key: 'records',   label: '紀錄',      icon: 'history', children: [
        { key: 'reservation', label: '預約記錄', href: '#' },
        { key: 'quota',       label: '配額使用歷史記錄', href: '#' }
      ]},
      { key: 'room',      label: '房間',      icon: 'door', badge: '11', children: [
        { key: 'standard',   label: '標準房間', href: 'reservation-rooms.html' },
        { key: 'combinable', label: '可合併房間', href: 'reservation-rooms-combinable.html', isNew: true }
      ]},
      { key: 'desk',      label: '共享辦公桌', icon: 'grid-dots', badge: '37', href: '#', disabled: true },
      { key: 'equipment', label: '設備',      icon: 'device-tv',  badge: '9',  href: 'reservation-equipment.html', isNew: true },
      { key: 'parking',   label: '車位',      icon: 'parking',    badge: '50', href: '#', disabled: true },
      { key: 'other',     label: '其他資源',   icon: 'box',        badge: '1',  href: '#' },
      { key: 'team',      label: '團隊空間',   icon: 'users',      href: 'reservation-team-spaces.html' },
      { key: 'display',   label: '顯示與篩選', icon: 'filter', children: [
        { key: 'display-amenities',  label: '附屬設備',   href: 'reservation-display-amenities.html' },
        { key: 'display-categories', label: '資源類別',   href: '#' },
        { key: 'display-timeslots',  label: '預約時間帶', href: '#' },
        { key: 'display-layouts',    label: '房間佈局',   href: '#', disabled: true },
      ] },
      { key: 'rules',     label: '預約規則',   icon: 'adjustments-alt', children: [] },
      { key: 'forms',     label: '預約表格',   icon: 'file-text', children: [] },
      { key: 'settings',  label: '設定/郵件提醒', icon: 'settings', href: '#' },
      { key: 'reports',   label: '郵件報表',   icon: 'mail', href: '#' }
    ]
  },

  ticket: {
    icon: 'ticket',
    color: 'linear-gradient(135deg, #ffb17a, #f26a5c)',
    title: '工單管理',
    items: [
      { key: 'dashboard', label: '資訊主頁',   icon: 'layout-dashboard', href: 'ticket-dashboard.html' },
      { key: 'reports',   label: '已匯報問題', icon: 'flag',   badge: '1', href: 'ticket-reports.html' },
      { key: 'logs',      label: '紀錄',      icon: 'history', href: '#' },
      { key: 'staff',     label: '支援職員',   icon: 'user-check', badge: '1', href: '#' },
      { key: 'policies',  label: '工單政策',   icon: 'shield-check', href: 'ticket-policies.html' }
    ]
  },

  broadcast: {
    icon: 'broadcast',
    color: 'linear-gradient(135deg, #f4c96b, #f39c3d)',
    title: '廣播',
    items: [
      { key: 'home',        label: '首頁',      icon: 'home', href: '#' },
      { key: 'announcements', label: '公告',    icon: 'speakerphone', href: 'broadcast-announcements.html' },
      { key: 'emergency',   label: '緊急',      icon: 'alert-triangle', href: 'broadcast-emergency.html' }
    ]
  },

  map: {
    icon: 'map',
    color: 'linear-gradient(135deg, #7cd6a7, #12a97e)',
    title: '地圖',
    items: [
      { key: 'home',    label: '首頁',        icon: 'home', href: '#' },
      { key: 'map',     label: '地圖',        icon: 'map-2', href: 'map.html' },
      { key: 'facility',label: '設施',        icon: 'building', href: '#' },
      { key: 'keys',    label: '位置存取金鑰', icon: 'key', href: '#' }
    ]
  },

  signage: {
    icon: 'device-tv',
    color: 'linear-gradient(135deg, #7c67f4, #4e3fd6)',
    title: '電子標牌',
    items: [
      { key: 'home',      label: '首頁',        icon: 'home',    href: 'signage-home.html' },
      { key: 'content',   label: '內容',        icon: 'photo',   badge: '3', href: '#' },
      { key: 'devices',   label: '設備',        icon: 'device-desktop', badge: '2', href: 'signage-devices.html' },
      { key: 'settings',  label: '設備設定',    icon: 'settings', href: '#' },
      { key: 'playlists', label: '播放列表',    icon: 'playlist', href: 'signage-playlists.html' },
      { key: 'media',     label: '已上傳的媒體', icon: 'folder', href: '#' },
      { key: 'monitor',   label: '設備監控',    icon: 'activity', href: '#' }
    ]
  },

  control: {
    icon: 'device-remote',
    color: 'linear-gradient(135deg, #58f5cd, #23c1a9)',
    title: '房間控制',
    items: [
      { key: 'home',   label: '首頁',        icon: 'home', href: 'room-control.html' },
      { key: 'spaces', label: '空間',        icon: 'square-plus', href: '#' }
    ]
  },

  org: {
    icon: 'users',
    color: 'linear-gradient(135deg, #ffa6c1, #e75d84)',
    title: '組織目錄',
    items: [
      { key: 'users',    label: '用戶',       icon: 'user',      href: 'org-users.html' },
      { key: 'groups',   label: '用戶群組',   icon: 'users',     href: 'org-groups.html' },
      { key: 'cards',    label: '門禁卡',     icon: 'credit-card', href: '#' },
      { key: 'devices',  label: '使用者裝置', icon: 'devices',   href: '#' },
      { key: 'branches', label: '分支機構管理', icon: 'building-community', href: 'org-branches.html' },
      { key: 'category', label: '分類',       icon: 'category', children: [
        { key: 'cat-groups', label: '用戶群組類別', href: 'org-cat-user-groups.html',      isNew: true },
        { key: 'cat-attrs',  label: '用戶屬性',    href: 'org-cat-user-attributes.html',  isNew: true },
        { key: 'cat-roles',  label: '可指派角色',  href: 'org-cat-assignable-roles.html', isNew: true }
      ]},
      { key: 'security', label: '安全性',     icon: 'shield', children: [
        { key: 'sec-password', label: '全域密碼政策',  href: 'org-security-password-policy.html', isNew: true },
        { key: 'sec-profile',  label: '用戶安全設定檔', href: 'org-security-profiles.html',        isNew: true }
      ]},
      { key: 'locations', label: '地點',      icon: 'map-pin',   href: 'org-locations.html' }
    ]
  },

  system: {
    icon: 'settings',
    color: 'linear-gradient(135deg, #a5b3c3, #5b6472)',
    title: '系統',
    items: [
      { key: 'media',    label: '媒體庫',        icon: 'folder', href: 'media-library.html' },
      { key: 'config',   label: '系統配置',      icon: 'adjustments', href: '#' },
      { key: 'security', label: '安全設定',      icon: 'shield-lock', href: '#' },
      { key: 'audit',    label: '審計追蹤',      icon: 'file-search', href: 'system-audit.html' },
      { key: 'email',    label: '電子郵件範本',  icon: 'mail-forward', href: 'system-email-templates.html' },
      { key: 'smtp',     label: '電郵相關設定',  icon: 'mail-cog', href: '#' }
    ]
  }
};

/* ---------- Icon helper (uses Tabler Icons via CDN) ---------- */
function icon(name) {
  return `<i class="ti ti-${name}"></i>`;
}

/* ---------- Render top bar ---------- */
function renderTopBar(crumbs = []) {
  const initials = 'I';
  return `
  <header class="off-topbar">
    <span class="off-apps" title="模組切換">
      ${Array(9).fill(0).map(() => '<span></span>').join('')}
    </span>
    <a class="off-logo" href="launcher.html">
      <span class="off-logo-mark"></span>
      Offision
    </a>
    <div class="off-search">
      <i class="ti ti-search"></i>
      <span>搜尋 | 頁面</span>
    </div>
    <button class="off-ai-btn">AI 支援</button>
    <button class="off-user-view-btn">用戶界面 <i class="ti ti-arrow-right"></i></button>
    <span class="off-avatar">${initials}</span>
  </header>
  <div class="off-crumbs">
    <a href="#"><i class="ti ti-home"></i> bizlution</a>
    <span class="sep">/</span>
    <a href="#">HQ <i class="ti ti-chevron-down"></i></a>
    ${crumbs.map(c => `<span class="sep">/</span><a href="${c.href || '#'}">${c.label}</a>`).join('')}
  </div>`;
}

/* ---------- Render sidebar ---------- */
function renderSidebar(moduleKey, activePage) {
  const m = OFF_NAV[moduleKey];
  if (!m) return '';
  const item = (it) => {
    const hasChildren = it.children && it.children.length > 0;
    const activeParent = it.key === activePage || (hasChildren && it.children.some(c => c.href && c.href.includes(activePage)));
    if (!hasChildren) {
      const isActive = it.href && it.href.split('/').pop().replace('.html','') === (activePage || '');
      const cls = [isActive ? 'active' : '', it.disabled ? 'disabled' : ''].filter(Boolean).join(' ');
      const clickBlock = it.disabled ? ' onclick="event.preventDefault(); return false;" title="尚未開放"' : '';
      return `<li>
        <a class="${cls}" href="${it.disabled ? '#' : (it.href || '#')}"${clickBlock}>
          <span class="off-nav-icon">${icon(it.icon)}</span>
          <span>${it.label}</span>
          ${it.badge ? `<span class="off-badge ${it.badgeDot ? 'dot' : ''}">${it.badge}</span>` : ''}
        </a>
      </li>`;
    }
    // 判斷此群組是否包含 active 子項 — 若否，預設收合
    const containsActive = it.children.some(c =>
      c.href && c.href.split('/').pop().replace('.html','') === (activePage || ''));
    const collapsed = !containsActive;
    return `<li>
      <div class="off-nav-group${collapsed ? ' collapsed' : ''}" onclick="offToggleNavGroup(this)">
        <span class="off-nav-icon">${icon(it.icon)}</span>
        <span>${it.label}</span>
        ${it.badge ? `<span class="off-badge">${it.badge}</span>` : ''}
        <i class="ti ti-chevron-down" style="margin-left:auto"></i>
      </div>
      <ul class="off-sub${collapsed ? ' hidden' : ''}">
        ${it.children.map(c => {
          const active = c.href && c.href.split('/').pop().replace('.html','') === (activePage || '');
          const newBadge = c.isNew ? '<span class="off-new-tag">NEW</span>' : '';
          const cls = [active ? 'active' : '', c.disabled ? 'disabled' : ''].filter(Boolean).join(' ');
          const clickBlock = c.disabled ? ' onclick="event.preventDefault(); return false;" title="尚未開放"' : '';
          return `<li><a class="${cls}" href="${c.disabled ? '#' : (c.href || '#')}"${clickBlock}>${c.label}${newBadge}</a></li>`;
        }).join('')}
      </ul>
    </li>`;
  };

  return `
  <aside class="off-sidebar">
    <div class="off-module-title">
      <span class="off-module-icon" style="background:${m.color}">${icon(m.icon)}</span>
      <span>${m.title}</span>
    </div>
    <div class="off-collapse-btn" onclick="document.querySelector('.off-shell').classList.toggle('is-collapsed')">
      <span><i class="ti ti-chevrons-left"></i> 折疊</span>
      <span><i class="ti ti-pin"></i></span>
    </div>
    <ul class="off-nav">
      ${m.items.map(item).join('')}
    </ul>
  </aside>`;
}

/* ---------- Boot ---------- */
document.addEventListener('DOMContentLoaded', () => {
  const body = document.body;
  const moduleKey = body.dataset.module;
  const pageKey   = body.dataset.page;

  const top = document.getElementById('off-top');
  if (top) top.innerHTML = renderTopBar(JSON.parse(body.dataset.crumbs || '[]'));

  const side = document.getElementById('off-sidebar');
  if (side) side.outerHTML = renderSidebar(moduleKey, pageKey);

  // 頂部頭像 → 點擊開 dropdown（內含登出）
  const avatar = document.querySelector('.off-topbar .off-avatar');
  if (avatar && window.OffAuth) {
    avatar.style.cursor = 'pointer';
    avatar.title = '帳戶選單';
    // 顯示登入用戶名首字
    const u = (OffAuth.user && OffAuth.user()) || null;
    if (u && u.display_name) avatar.textContent = u.display_name.slice(0, 1);

    // 建立 dropdown（一次性 append 到 body）
    const dd = document.createElement('div');
    dd.className = 'off-user-dropdown';
    dd.innerHTML = `
      <div class="udd-head">
        <div class="udd-avatar">${u && u.display_name ? u.display_name.slice(0,1) : '?'}</div>
        <div>
          <div class="udd-name">${u && u.display_name ? escapeHtml(u.display_name) : '(未登入)'}</div>
          <div class="udd-sub">${u && u.email ? escapeHtml(u.email) : ''}</div>
        </div>
      </div>
      <div class="udd-sep"></div>
      <button class="udd-item" data-act="logout">
        <i class="ti ti-logout"></i> 登出
      </button>
    `;
    document.body.appendChild(dd);

    function positionDropdown() {
      const rect = avatar.getBoundingClientRect();
      dd.style.top = `${rect.bottom + 8}px`;
      dd.style.right = `${window.innerWidth - rect.right}px`;
    }

    avatar.addEventListener('click', (ev) => {
      ev.stopPropagation();
      positionDropdown();
      dd.classList.toggle('open');
    });
    document.addEventListener('click', (ev) => {
      if (dd.classList.contains('open') && !dd.contains(ev.target)) {
        dd.classList.remove('open');
      }
    });
    dd.querySelector('[data-act="logout"]').addEventListener('click', () => {
      dd.classList.remove('open');
      if (confirm('確定要登出？')) {
        OffAuth.clear();
        location.href = 'login.html';
      }
    });
  }

  function escapeHtml(s) {
    return (s || '').replace(/[&<>"']/g, c =>
      ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
});

/* ---------- Modal helpers ---------- */
window.offOpenModal = id => document.getElementById(id).classList.add('open');
window.offCloseModal = id => document.getElementById(id).classList.remove('open');

/* ---------- Sidebar nav group toggle ---------- */
window.offToggleNavGroup = (el) => {
  const sub = el.nextElementSibling;
  if (!sub) return;
  const willCollapse = !sub.classList.contains('hidden');
  sub.classList.toggle('hidden', willCollapse);
  el.classList.toggle('collapsed', willCollapse);
};
