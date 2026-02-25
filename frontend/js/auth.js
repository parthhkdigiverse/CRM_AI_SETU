// auth.js — shared across all pages
let API = 'http://127.0.0.1:8000/api'; // Fallback
fetch('http://127.0.0.1:8000/api/config')
    .then(r => r.json())
    .then(data => { API = data.API_BASE_URL; })
    .catch(e => console.warn('Using default API due to fetch error:', e));

// Inject global theme styles
document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="../css/theme.css">');

function getToken() { return sessionStorage.getItem('access_token'); }
function setTokens(a, r) {
    sessionStorage.setItem('access_token', a);
    if (r) sessionStorage.setItem('refresh_token', r);
}
function clearTokens() {
    sessionStorage.removeItem('access_token');
    sessionStorage.removeItem('refresh_token');
    sessionStorage.removeItem('crm_user');
}
function getUser() {
    try { return JSON.parse(sessionStorage.getItem('crm_user')); } catch { return null; }
}

// Guard: call on every protected page
function requireAuth() {
    if (!getToken()) { window.location.replace('index.html'); return; }
    const u = getUser();
    const el = document.getElementById('username-display');
    if (el && u) el.textContent = u.name || u.email || 'User';

    // Auto-inject theme header
    let pageName = document.title.split('—')[0].trim();
    if (!pageName || pageName === 'CRM AI SETU') pageName = 'Dashboard';
    injectTopHeader(pageName);
}

// Re-evaluate auth on back/forward navigation
window.addEventListener('pageshow', (event) => {
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
const INACTIVITY_LIMIT_MS = 15 * 60 * 1000; // 15 minutes
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
    if (res.status === 401) { clearTokens(); window.location.replace('index.html'); return; }
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
    const links = [
        { id: 'dashboard', icon: 'bi-speedometer2', label: 'Dashboard', href: 'dashboard.html' },
        { id: 'clients', icon: 'bi-people', label: 'Clients', href: 'clients.html' },
        { id: 'visits', icon: 'bi-geo-alt', label: 'Visits', href: 'visits.html' },
        { id: 'meetings', icon: 'bi-calendar-check', label: 'Meetings', href: 'meetings.html' },
        { id: 'issues', icon: 'bi-exclamation-triangle', label: 'Issues', href: 'issues.html' },
        { id: 'feedback', icon: 'bi-star', label: 'Feedback', href: 'feedback.html' },
        { id: 'areas', icon: 'bi-map', label: 'Areas', href: 'areas.html' },
        { id: 'hrm', icon: 'bi-person-badge', label: 'HRM', href: 'hrm.html' },
        { id: 'reports', icon: 'bi-bar-chart-line', label: 'Reports', href: 'reports.html' },
        { id: 'admin', icon: 'bi-shield-lock', label: 'Admin', href: 'admin.html' },
    ];
    const u = getUser();
    return `
    <div id="sidebar-container">
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">
                <i class="bi bi-diagram-3-fill"></i>
            </div>
            <span>CRM AI SETU</span>
        </div>
        
        <!-- Navigation Section -->
        <h6 class="text-muted small px-4 mb-2 mt-2 fw-bold" style="letter-spacing:0.5px">DASHBOARD</h6>
        <ul class="sidebar-nav">
            <li class="sidebar-nav-item"><a href="dashboard.html" class="sidebar-link ${active === 'dashboard' ? 'active' : ''}"><i class="bi bi-speedometer2"></i>Overview</a></li>
        </ul>
        
        <h6 class="text-muted small px-4 mb-2 mt-4 fw-bold" style="letter-spacing:0.5px">ADMINISTRATION</h6>
        <ul class="sidebar-nav">
            <li class="sidebar-nav-item"><a href="admin.html" class="sidebar-link ${active === 'admin' ? 'active' : ''}"><i class="bi bi-shield-lock"></i>User Management</a></li>
        </ul>
        
        <h6 class="text-muted small px-4 mb-2 mt-4 fw-bold" style="letter-spacing:0.5px">FIELD OPERATIONS</h6>
        <ul class="sidebar-nav">
            <li class="sidebar-nav-item"><a href="areas.html" class="sidebar-link ${active === 'areas' ? 'active' : ''}"><i class="bi bi-map"></i>Areas & Shops</a></li>
            <li class="sidebar-nav-item"><a href="visits.html" class="sidebar-link ${active === 'visits' ? 'active' : ''}"><i class="bi bi-geo-alt"></i>Visits</a></li>
        </ul>
        
        <h6 class="text-muted small px-4 mb-2 mt-4 fw-bold" style="letter-spacing:0.5px">PROJECT MANAGEMENT</h6>
        <ul class="sidebar-nav">
            <li class="sidebar-nav-item"><a href="#" class="sidebar-link"><i class="bi bi-briefcase"></i>Projects</a></li>
            <li class="sidebar-nav-item"><a href="meetings.html" class="sidebar-link ${active === 'meetings' ? 'active' : ''}"><i class="bi bi-calendar-check"></i>Meetings</a></li>
        </ul>

        <h6 class="text-muted small px-4 mb-2 mt-4 fw-bold" style="letter-spacing:0.5px">CLIENT RELATIONS</h6>
        <ul class="sidebar-nav">
            <li class="sidebar-nav-item"><a href="clients.html" class="sidebar-link ${active === 'clients' ? 'active' : ''}"><i class="bi bi-people"></i>Clients</a></li>
            <li class="sidebar-nav-item"><a href="issues.html" class="sidebar-link ${active === 'issues' ? 'active' : ''}"><i class="bi bi-exclamation-triangle"></i>Issues</a></li>
            <li class="sidebar-nav-item"><a href="feedback.html" class="sidebar-link ${active === 'feedback' ? 'active' : ''}"><i class="bi bi-star"></i>Feedback</a></li>
        </ul>

        <!--
        <h6 class="text-muted small px-4 mb-2 mt-4 fw-bold" style="letter-spacing:0.5px">HR & PAYROLL</h6>
        <ul class="sidebar-nav">
            <li class="sidebar-nav-item"><a href="hrm.html" class="sidebar-link ${active === 'hrm' ? 'active' : ''}"><i class="bi bi-person-badge"></i>HRM</a></li>
        </ul>
        -->

        <h6 class="text-muted small px-4 mb-2 mt-4 fw-bold" style="letter-spacing:0.5px">REPORTS & ANALYTICS</h6>
        <ul class="sidebar-nav">
            <li class="sidebar-nav-item"><a href="reports.html" class="sidebar-link ${active === 'reports' ? 'active' : ''}"><i class="bi bi-bar-chart-line"></i>Reports</a></li>
        </ul>
                
        <div style="padding: 24px;">
            <div class="d-flex align-items-center gap-3">
                <div class="rounded-circle bg-light d-flex align-items-center justify-content-center text-primary" style="width:36px;height:36px;font-weight:700;">
                    ${(u?.name || 'U')[0].toUpperCase()}
                </div>
                <div class="flex-grow-1 overflow-hidden">
                    <div class="fw-semibold text-truncate small" id="username-display" style="color:var(--text-main);">${u?.name || '-'}</div>
                    <div class="text-muted" style="font-size:11px;">${u?.role || ''}</div>
                </div>
            </div>
            <hr class="my-3 border-secondary" style="opacity:0.1;">
            <button onclick="logout()" class="btn btn-sm btn-light w-100 text-start text-muted d-flex align-items-center gap-2">
                <i class="bi bi-box-arrow-right"></i> Logout
            </button>
        </div>
    </div>`;
}

function injectTopHeader(pageTitle) {
    const headerHtml = `
    <div class="top-header">
        <div class="fw-semibold fs-5 text-dark" style="text-transform: capitalize;">
            ${pageTitle}
        </div>
        <div class="d-flex align-items-center gap-4">
            <div class="position-relative">
                <i class="bi bi-search position-absolute text-muted" style="left:12px;top:10px;"></i>
                <input type="text" class="search-bar" placeholder="Search anything...">
            </div>
            <button class="btn btn-primary d-flex align-items-center gap-2">
                <i class="bi bi-plus"></i> Add New
            </button>
            <div class="position-relative" style="cursor:pointer; color:var(--text-muted); font-size:1.2rem;">
                <i class="bi bi-bell"></i>
                <span class="position-absolute top-0 start-100 translate-middle p-1 bg-danger border border-light rounded-circle">
                    <span class="visually-hidden">New alerts</span>
                </span>
            </div>
            <div class="rounded-circle bg-light d-flex align-items-center justify-content-center fw-bold text-primary" style="width:36px;height:36px;font-size:14px;cursor:pointer;">
                AD
            </div>
        </div>
    </div>`;
    const rightSide = document.querySelector('.flex-grow-1');
    if (rightSide) {
        // Remove old basic p-4 padding logic and inject header + scrollable content area wrapper
        rightSide.classList.remove('p-4');
        rightSide.classList.add('d-flex', 'flex-column', 'bg-light');
        rightSide.style.minHeight = '100vh';
        rightSide.insertAdjacentHTML('afterbegin', headerHtml);

        // Wrap existing content from rightSide into a .page-content div
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
