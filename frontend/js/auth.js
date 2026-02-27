// auth.js — shared across all pages
let API = 'http://127.0.0.1:8000/api'; // Fallback
fetch('http://127.0.0.1:8000/api/config')
    .then(r => r.json())
    .then(data => { API = data.API_BASE_URL; })
    .catch(e => console.warn('Using default API due to fetch error:', e));

// Inject global theme styles
document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="../css/theme.css">');

function getToken() { return localStorage.getItem('access_token'); }
function setTokens(a, r) {
    localStorage.setItem('access_token', a);
    if (r) localStorage.setItem('refresh_token', r);
}
function clearTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('crm_user');
}
function getUser() {
    try { return JSON.parse(localStorage.getItem('crm_user')); } catch { return null; }
}

// Guard: call on every protected page
function requireAuth() {
    // Development Bypass: Allow viewing template via ?dev=true ONLY on local environments
    const params = new URLSearchParams(window.location.search);
    const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) || window.location.protocol === 'file:';

    if (params.get('dev') === 'true' && isLocal) {
        console.warn('Auth check bypassed via dev flag (Local Only).');
        return;
    }

    const token = getToken();
    if (!token) {
        window.location.replace('index.html');
        return;
    }

    // Hide page while we verify the token is still valid
    document.body.style.visibility = 'hidden';

    fetch('http://127.0.0.1:8000/api/auth/profile', {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(r => {
        if (!r.ok) {
            // Token invalid or expired — kick to login
            clearTokens();
            window.location.replace('index.html');
            return;
        }
        // Token is valid — show the page
        document.body.style.visibility = 'visible';
        const u = getUser();
        const el = document.getElementById('username-display');
        if (el && u) el.textContent = u.name || u.email || 'User';

        // Auto-inject theme header
        let pageName = document.title.split('—')[0].trim();
        if (!pageName || pageName === 'CRM AI SETU') pageName = 'Dashboard';
        injectTopHeader(pageName);
    })
    .catch(() => {
        // Network error — fall back to token-only check (server may be starting up)
        document.body.style.visibility = 'visible';
        const u = getUser();
        const el = document.getElementById('username-display');
        if (el && u) el.textContent = u.name || u.email || 'User';

        let pageName = document.title.split('—')[0].trim();
        if (!pageName || pageName === 'CRM AI SETU') pageName = 'Dashboard';
        injectTopHeader(pageName);
    });
}


// Re-evaluate auth on back/forward navigation
window.addEventListener('pageshow', (event) => {
    const params = new URLSearchParams(window.location.search);
    const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) || window.location.protocol === 'file:';
    if (params.get('dev') === 'true' && isLocal) return;

    // If the page was restored from the bfcache and we have no token, kick them
    if (event.persisted && !getToken() && window.location.pathname.indexOf('index.html') === -1) {
        window.location.replace('index.html');
    }
});

// Logout
function logout() {
    clearTokens();
    window.location.replace('index.html');
}

// Session Management (Inactivity Timeout)
const INACTIVITY_LIMIT_MS = 7 * 24 * 60 * 60 * 1000; // 7 days (more persistent)
let inactivityTimer;

function resetInactivityTimer() {
    clearTimeout(inactivityTimer);
    if (getToken()) {
        inactivityTimer = setTimeout(() => {
            alert('Your session has expired due to inactivity. Please log in again.');
            logout();
        }, INACTIVITY_LIMIT_MS);
    }
}

// Attach activity listeners once DOM is ready
if (typeof document !== 'undefined') {
    ['click', 'mousemove', 'keydown', 'scroll', 'touchstart'].forEach(evt =>
        document.addEventListener(evt, resetInactivityTimer, { passive: true })
    );
}

// Call initially
resetInactivityTimer();

// Generic authenticated fetch
async function apiFetch(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(API + path, { ...options, headers });
    if (res.status === 401) {
        const params = new URLSearchParams(window.location.search);
        const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) || window.location.protocol === 'file:';
        if (params.get('dev') === 'true' && isLocal) {
            console.warn('API 401 suppressed in dev mode.');
            return res;
        }
        clearTokens();
        window.location.replace('index.html');
        return;
    }
    return res;
}

// GET shorthand
async function apiGet(path) {
    const res = await apiFetch(path);
    if (!res || !res.ok) throw new Error(`GET ${path} failed: ${res?.status}`);
    return res.json();
}

// POST shorthand
async function apiPost(path, body) {
    const res = await apiFetch(path, { method: 'POST', body: JSON.stringify(body) });
    if (!res || !res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `POST ${path} failed`);
    }
    return res.json();
}

// PATCH shorthand
async function apiPatch(path, body) {
    const res = await apiFetch(path, { method: 'PATCH', body: JSON.stringify(body) });
    if (!res || !res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `PATCH ${path} failed`);
    }
    return res.json();
}

// Show bootstrap toast
function showToast(msg, type = 'success') {
    const bg = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
    const id = 'toast_' + Date.now();
    const toastHtml = `
        <div id="${id}" class="toast align-items-center text-white ${bg} border-0 mb-2" role="alert">
            <div class="d-flex">
                <div class="toast-body">${msg}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>`;
    let c = document.getElementById('toast-container');
    if (!c) {
        c = document.createElement('div');
        c.id = 'toast-container';
        c.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        c.style.zIndex = 9999;
        document.body.appendChild(c);
    }
    c.insertAdjacentHTML('beforeend', toastHtml);
    const el = document.getElementById(id);
    new bootstrap.Toast(el, { delay: 3500 }).show();
    el.addEventListener('hidden.bs.toast', () => el.remove());
}

// Shared sidebar HTML
function renderSidebar(active) {
    const u = getUser();
    const role = u?.role || 'TELESALES';

    const isAdmin = role === 'ADMIN';
    const isSales = role === 'SALES' || role === 'PROJECT_MANAGER_AND_SALES';
    const isTelesales = role === 'TELESALES';
    const isPM = role === 'PROJECT_MANAGER' || role === 'PROJECT_MANAGER_AND_SALES';
    const isClient = role === 'CLIENT';

    function sbSection(id, label, icon, items) {
        const isActiveSection = items.some(i => i.id === active);
        return `
        <div class="sb-section">
            <div class="sb-section-header ${isActiveSection ? 'open' : ''}" onclick="toggleSbSection('${id}')">
                <i class="bi ${icon} sb-sec-icon"></i>
                <span>${label}</span>
                <i class="bi bi-chevron-right sb-arrow"></i>
            </div>
            <ul class="sb-section-items ${isActiveSection ? 'open' : ''}">
                ${items.map(item => `
                <li><a href="${item.href}" class="sb-link ${active === item.id ? 'active' : ''}">
                    <i class="bi ${item.icon}"></i><span>${item.label}</span></a></li>`).join('')}
            </ul>
        </div>`;
    }

    // ─── ALWAYS: Dashboard ───────────────────────────────────────
    let nav = `
    <div class="sb-section">
        <div class="sb-section-header ${active === 'dashboard' ? 'open' : ''}" onclick="toggleSbSection('db')">
            <i class="bi bi-grid-1x2 sb-sec-icon"></i><span>Dashboard</span>
            <i class="bi bi-chevron-${active === 'dashboard' ? 'down' : 'right'} sb-arrow"></i>
        </div>
        <ul class="sb-section-items ${active === 'dashboard' ? 'open' : ''}">
            <li><a href="dashboard.html" class="sb-link ${active === 'dashboard' ? 'active' : ''}">
                <i class="bi bi-bar-chart-line-fill"></i><span>Overview</span></a></li>
            <li><a href="javascript:void(0)" onclick="if(window.loadView) window.loadView('timetable');" class="sb-link ${active === 'timetable' ? 'active' : ''}">
                <i class="bi bi-calendar3"></i><span>Timetable</span></a></li>
        </ul>
    </div>`;

    // ─── ADMINISTRATION ──────────────────────────────────────────
    nav += sbSection('admin', 'Administration', 'bi-shield-check', [
        { id: 'admin', href: 'admin.html', icon: 'bi-people', label: 'Users & Roles' }
    ]);

    // ─── FIELD OPERATIONS ────────────────────────────────────────
    nav += sbSection('field', 'Field Operations', 'bi-geo-alt', [
        { id: 'visits', href: 'visits.html', icon: 'bi-bullseye', label: 'Leads' },
        { id: 'areas', href: 'areas.html', icon: 'bi-building', label: 'Areas & Shops' },
        { id: 'visits_log', href: 'visits.html', icon: 'bi-calendar3', label: 'Visits' }
    ]);

    // ─── PROJECT MANAGEMENT ──────────────────────────────────────
    nav += sbSection('pm', 'Project Management', 'bi-briefcase', [
        { id: 'projects', href: 'reports.html', icon: 'bi-briefcase', label: 'Projects' },
        { id: 'meetings', href: 'meetings.html', icon: 'bi-calendar-event', label: 'Meetings' },
        { id: 'issues', href: 'issues.html', icon: 'bi-exclamation-triangle', label: 'Issues' }
    ]);

    // ─── CLIENT RELATIONS ────────────────────────────────────────
    nav += sbSection('cr', 'Client Relations', 'bi-people', [
        { id: 'clients', href: 'clients.html', icon: 'bi-people', label: 'Clients' },
        { id: 'billing', href: 'javascript:void(0)" onclick="if(window.loadView) window.loadView(\'billing\');', icon: 'bi-file-earmark-medical', label: 'Billing' },
        { id: 'feedback', href: 'feedback.html', icon: 'bi-chat-square-text', label: 'Feedback' }
    ]);

    // ─── HR & PAYROLL ────────────────────────────────────────────
    nav += sbSection('hr', 'HR & Payroll', 'bi-currency-dollar', [
        { id: 'hrm', href: 'hrm.html', icon: 'bi-people', label: 'Employees' },
        { id: 'salary', href: 'hrm.html#tab-salary', icon: 'bi-calendar3', label: 'Salary & Leaves' },
        { id: 'incentives', href: 'hrm.html#tab-incentives', icon: 'bi-trophy', label: 'Incentives' }
    ]);

    // ─── REPORTS & ANALYTICS ─────────────────────────────────────
    nav += sbSection('rpt', 'Reports & Analytics', 'bi-graph-up', [
        { id: 'reports', href: 'reports.html', icon: 'bi-graph-up', label: 'Reports' }
    ]);

    return `
    <div id="sidebar-container">
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon"><i class="bi bi-diagram-3-fill"></i></div>
            <span>CRM AI SETU</span>
        </div>
        <div class="sb-scroll-area">${nav}</div>
        <div class="sb-bottom">
            <a href="#" class="sb-bottom-link"><i class="bi bi-gear"></i> Settings</a>
            <a href="#" class="sb-bottom-link" onclick="logout();return false;"><i class="bi bi-box-arrow-right"></i> Logout</a>
        </div>
    </div>`;
}

window.toggleSbSection = function (id) {
    document.querySelectorAll('.sb-section').forEach(sec => {
        const hdr = sec.querySelector('.sb-section-header');
        const lst = sec.querySelector('.sb-section-items');
        const arr = sec.querySelector('.sb-arrow');
        if (!hdr) return;
        const isMe = (hdr.getAttribute('onclick') || '').includes(`'${id}'`);
        const isOpen = hdr.classList.contains('open');
        if (isMe) {
            hdr.classList.toggle('open');
            lst && lst.classList.toggle('open');
            if (arr) arr.className = `bi ${hdr.classList.contains('open') ? 'bi-chevron-down' : 'bi-chevron-right'} sb-arrow`;
        }
    });
};

function injectTopHeader(pageTitle) {
    const u = getUser();
    const role = (u?.role || '').replace(/_/g, ' ');
    const initials = (u?.name || u?.email || 'AD').slice(0, 2).toUpperCase();
    const headerHtml = `
    <div class="top-header">
        <div class="d-flex align-items-center">
            <div class="fw-semibold fs-5 text-dark" style="text-transform: capitalize;">${pageTitle}</div>
        </div>
        <div class="d-flex align-items-center gap-3">
            <div class="position-relative d-none d-md-block">
                <i class="bi bi-search position-absolute text-muted" style="left:12px;top:10px;font-size:0.85rem;"></i>
                <input type="text" class="search-bar" placeholder="Search anything...">
            </div>
            <div class="dropdown">
                <button class="btn btn-primary d-flex align-items-center gap-2 px-3 dropdown-toggle" type="button" id="addNewDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="font-size:0.875rem;">
                    <i class="bi bi-plus-lg"></i> Add New
                </button>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="addNewDropdown" style="font-size: 0.875rem; border-radius:12px; padding:8px;">
                    <li><a class="dropdown-item py-2" href="visits.html" style="border-radius:8px;"><i class="bi bi-bullseye me-2 text-primary"></i> New Lead / Visit</a></li>
                    <li><a class="dropdown-item py-2" href="clients.html" style="border-radius:8px;"><i class="bi bi-people me-2 text-info"></i> New Client</a></li>
                    <li><a class="dropdown-item py-2" href="javascript:void(0)" onclick="if(window.openNewBillModal) window.openNewBillModal();" style="border-radius:8px;"><i class="bi bi-file-invoice-dollar me-2 text-danger"></i> New Bill</a></li>
                    <li><a class="dropdown-item py-2" href="issues.html" style="border-radius:8px;"><i class="bi bi-exclamation-triangle me-2 text-warning"></i> New Issue</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item py-2" href="admin.html" style="border-radius:8px;"><i class="bi bi-person-plus me-2 text-success"></i> New User</a></li>
                </ul>
            </div>
            <div class="position-relative text-muted" style="cursor:pointer; font-size:1.25rem; width:40px; height:40px; display:flex; align-items:center; justify-content:center;">
                <i class="bi bi-bell"></i>
                <span class="position-absolute bg-danger border border-white rounded-circle" style="width:8px;height:8px;top:8px;right:8px;"></span>
            </div>
            <div class="d-flex align-items-center gap-2 ps-2 dropdown">
                <div class="rounded-circle bg-primary-light text-primary d-flex align-items-center justify-content-center fw-bold dropdown-toggle" id="profileDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="width:36px;height:36px;font-size:13px;cursor:pointer;">${initials}</div>
                <div class="d-none d-lg-block">
                    <div class="fw-bold text-dark" style="font-size:0.85rem; line-height:1;">${u?.name || 'Admin'}</div>
                    <div class="text-muted small" style="font-size:0.75rem; line-height:1.5;">${role}</div>
                </div>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="profileDropdown" style="font-size: 0.875rem; border-radius:12px; padding:8px;">
                    <li><a class="dropdown-item py-2" href="javascript:void(0)" onclick="if(window.loadView) window.loadView('profile');" style="border-radius:8px;"><i class="bi bi-person me-2 text-primary"></i> My Profile</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item py-2" href="javascript:void(0)" onclick="logout()" style="border-radius:8px; color:var(--danger);"><i class="bi bi-box-arrow-right me-2"></i> Logout</a></li>
                </ul>
            </div>
        </div>
    </div>`;
    const rightSide = document.querySelector('.flex-grow-1');
    if (rightSide) {
        rightSide.classList.remove('p-4');
        rightSide.classList.add('d-flex', 'flex-column', 'bg-light');
        rightSide.style.minHeight = '100vh';
        rightSide.insertAdjacentHTML('afterbegin', headerHtml);
        const nodesToMove = [];
        for (const child of rightSide.childNodes) {
            if (child.nodeType === 1 && child.classList.contains('top-header')) continue;
            nodesToMove.push(child);
        }
        const contentContainer = document.createElement('div');
        contentContainer.className = 'page-content';
        nodesToMove.forEach(node => contentContainer.appendChild(node));
        rightSide.appendChild(contentContainer);
    }
}
