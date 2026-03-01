// auth.js — shared across all pages
let API = localStorage.getItem('api_base') || 'http://127.0.0.1:8000/api';

// Background Refresh Config
fetch('http://127.0.0.1:8000/api/config')
    .then(r => r.json())
    .then(data => {
        if (data.API_BASE_URL) {
            API = data.API_BASE_URL;
            localStorage.setItem('api_base', API);
        }
    })
    .catch(e => console.warn('Config fetch error:', e));

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
    const params = new URLSearchParams(window.location.search);
    const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) || window.location.protocol === 'file:';
    const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/');

    if (params.get('dev') === 'true' && isLocal) {
        document.body.style.visibility = 'visible';
        let pageName = document.title.split('—')[0].trim();
        if (!pageName || pageName === 'CRM AI SETU') pageName = 'Dashboard';
        if (typeof injectTopHeader === 'function') injectTopHeader(pageName);
        return;
    }

    const token = getToken();
    const user = getUser();

    if (!token) {
        if (!isLoginPage) window.location.replace('index.html');
        return;
    }

    // --- OPTIMISTIC UI ---
    // If we have a user in session, show the page IMMEDIATELY.
    if (user) {
        document.body.style.visibility = 'visible';
        const el = document.getElementById('username-display');
        if (el) el.textContent = user.name || 'User';

        // Inject header immediately
        let pageName = document.title.split('—')[0].trim();
        if (!pageName || pageName === 'CRM AI SETU') pageName = 'Dashboard';
        if (typeof injectTopHeader === 'function') injectTopHeader(pageName);
    } else {
        // Fallback: hide until we get a profile (rare)
        document.body.style.visibility = 'hidden';
        // Emergency unhide after 3 seconds to prevent permanent black screen
        setTimeout(() => { document.body.style.visibility = 'visible'; }, 3000);
    }

    // Background Verification
    fetch(`${API}/auth/profile`, {
        headers: { 'Authorization': `Bearer ${token}` }
    })
        .then(r => {
            if (!r.ok) {
                if (r.status === 401) {
                    clearTokens();
                    if (!isLoginPage) window.location.replace('index.html');
                }
                return null;
            }
            return r.json();
        })
        .then(profile => {
            if (!profile) return;
            const userData = { id: profile.id, name: profile.name || profile.email, role: profile.role };
            localStorage.setItem('crm_user', JSON.stringify(userData));

            document.body.style.visibility = 'visible';
            const el = document.getElementById('username-display');
            if (el) el.textContent = profile.name || 'User';

            let pageName = document.title.split('—')[0].trim();
            if (typeof injectTopHeader === 'function') injectTopHeader(pageName);
        })
        .catch((err) => {
            console.warn('Background auth check failed:', err);
            document.body.style.visibility = 'visible';
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
