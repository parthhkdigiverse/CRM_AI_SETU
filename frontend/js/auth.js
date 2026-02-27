// auth.js — shared across all pages
let API = 'http://127.0.0.1:8000/api'; // Fallback
fetch('http://127.0.0.1:8000/api/config')
    .then(r => r.json())
    .then(data => { API = data.API_BASE_URL; })
    .catch(e => console.warn('Using default API due to fetch error:', e));

// Inject global theme styles
document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="../css/theme.css">');

function getToken() {
    const t = localStorage.getItem('access_token');
    if (!t || t === 'null' || t === 'undefined' || t === '') return null;
    return t;
}
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
        document.body.style.visibility = 'visible';
        // Still inject header for development visibility
        let pageName = document.title.split('—')[0].trim();
        if (!pageName || pageName === 'CRM AI SETU') pageName = 'Dashboard';
        injectTopHeader(pageName);
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
                // Token invalid/expired OR server returned an error — kick to login
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
        .catch((err) => {
            // Network error — server is completely unreachable
            // Instead of redirecting to login (which assumes bad credentials),
            // show the page but maybe with a warning or just let the API calls fail.
            // If we redirect to login while server is down, it creates an infinite loop.
            console.error('Auth check failed: Server unreachable', err);
            document.body.style.visibility = 'visible';
            showToast('Server connection unstable', 'error');
        });
}


// Re-evaluate auth on back/forward navigation
window.addEventListener('pageshow', (event) => {
    const params = new URLSearchParams(window.location.search);
    const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) || window.location.protocol === 'file:';
    if (params.get('dev') === 'true' && isLocal) return;

    const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/');

    // If the page was restored from the bfcache and we have no token, kick them
    if (event.persisted && !getToken() && !isLoginPage) {
        window.location.replace('index.html');
    }

    // If we land on the login page but already have a VALID token, go to dashboard.
    // DISABLE: This can cause redirect loops if the dashboard is failing or if the user wants to switch accounts.
    /*
    const isBypass = params.get('dev') === 'true' || params.get('msg') === 'logged_out';

    if (isLoginPage && getToken() && !isBypass) {
        // Debounce: wait a tiny bit to ensure API is set from config
        setTimeout(() => {
            fetch(API + '/auth/profile', {
                headers: { 'Authorization': `Bearer ${getToken()}` }
            }).then(r => {
                if (r.ok) window.location.replace('dashboard.html');
                else clearTokens();
            }).catch(() => clearTokens());
        }, 300);
    }
    */
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

// Components are now housed in js/components.js
