// frontend/js/auth.js
// auth.js — shared across all pages
let API = window.location.origin + '/api';

// Background Refresh Config
fetch(window.location.origin + '/api/config')
    .then(r => r.json())
    .then(data => {
        if (data.API_BASE_URL) {
            API = data.API_BASE_URL;
        }
    })
    .catch(e => console.warn('Config fetch error:', e));

// Inject global theme styles (but NOT on the login page to avoid style degradation)
const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/') || window.location.pathname === '';
if (!isLoginPage) {
    document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="../css/theme.css?v=2.6">');
    document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="../css/components.css?v=2.6">');
    document.head.insertAdjacentHTML('beforeend', '<link rel="stylesheet" href="../css/global.css?v=2.6">');
}

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

function showAccessDeniedState(role, path) {
    const target = document.getElementById('main-content') || document.querySelector('.page-content');
    if (!target || document.getElementById('access-denied-state')) return;

    const roleLabel = (role || 'USER').replace(/_/g, ' ');
    const pageLabel = (path || 'this page').replace('.html', '').replace(/[-_]/g, ' ');
    const card = document.createElement('div');
    card.id = 'access-denied-state';
    card.style.cssText = 'position:relative;z-index:20;margin:0 auto 24px auto;max-width:720px;background:#fff7ed;border:1px solid #fed7aa;border-radius:20px;padding:32px;box-shadow:0 20px 40px rgba(15,23,42,.08);';
    card.innerHTML = `
        <div style="display:flex;align-items:flex-start;gap:16px;">
            <div style="width:56px;height:56px;border-radius:16px;background:#ffedd5;color:#ea580c;display:flex;align-items:center;justify-content:center;font-size:24px;flex-shrink:0;">
                <i class="bi bi-shield-lock"></i>
            </div>
            <div>
                <div style="font-size:1.35rem;font-weight:700;color:#9a3412;line-height:1.2;">You don't have enough access</div>
                <p style="margin:10px 0 0 0;color:#7c2d12;font-size:.95rem;line-height:1.6;">Your current role, ${roleLabel}, cannot open ${pageLabel}. The sidebar stays visible so you can move to pages that are available to you.</p>
                <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px;">
                    <a href="dashboard.html" style="text-decoration:none;background:#ea580c;color:#fff;padding:10px 14px;border-radius:12px;font-weight:600;">Go to Dashboard</a>
                    <a href="profile.html" style="text-decoration:none;background:#fff;color:#9a3412;padding:10px 14px;border-radius:12px;border:1px solid #fdba74;font-weight:600;">Open Profile</a>
                </div>
            </div>
        </div>`;

    target.style.position = target.style.position || 'relative';
    target.insertBefore(card, target.firstChild);
    Array.from(target.children).forEach(child => {
        if (child.id === 'access-denied-state') return;
        child.style.opacity = '0.18';
        child.style.pointerEvents = 'none';
        child.setAttribute('aria-hidden', 'true');
    });
    window.__accessDenied = true;
}

// Guard: call on every protected page
function requireAuth() {
    window.__accessDenied = false;
    const params = new URLSearchParams(window.location.search);
    const isLocal = ['localhost', '127.0.0.1', ''].includes(window.location.hostname) || window.location.protocol === 'file:';
    const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/');

    if (params.get('dev') === 'true' && isLocal) {
        document.body.style.visibility = 'visible';
        let pageName = document.title.split('—')[0].trim();
        if (!pageName || pageName === 'SRM AI SETU') pageName = 'Dashboard';
        if (typeof injectTopHeader === 'function') injectTopHeader(pageName);
        return;
    }

    const token = getToken();
    const user = getUser();

    if (!token) {
        if (!isLoginPage) window.location.replace('index.html');
        return;
    }

    // --- ROLE BASED ROUTING GUARD ---
    const ROLE_PERMISSIONS_FALLBACK = {
        'ADMIN': ['*'],
        'SALES': ['dashboard.html', 'timetable.html', 'todo.html', 'leads.html', 'visits.html', 'areas.html', 'clients.html', 'billing.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html', 'issues.html', 'incentives.html'],
        'TELESALES': ['dashboard.html', 'timetable.html', 'todo.html', 'leads.html', 'visits.html', 'clients.html', 'billing.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html', 'issues.html', 'incentives.html'],
        'PROJECT_MANAGER': ['dashboard.html', 'timetable.html', 'todo.html', 'projects.html', 'projects_demo.html', 'meetings.html', 'issues.html', 'clients.html', 'billing.html', 'feedback.html', 'reports.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html'],
        'PROJECT_MANAGER_AND_SALES': ['dashboard.html', 'timetable.html', 'todo.html', 'leads.html', 'visits.html', 'areas.html', 'projects.html', 'projects_demo.html', 'meetings.html', 'issues.html', 'clients.html', 'billing.html', 'feedback.html', 'reports.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html'],
        'CLIENT': ['dashboard.html']
    };

    window.__crmEffectiveAccessPolicy = window.__crmEffectiveAccessPolicy || null;

    const FEATURE_ACCESS_FALLBACK = {
        issue_create_roles: ['ADMIN', 'SALES', 'TELESALES', 'PROJECT_MANAGER', 'PROJECT_MANAGER_AND_SALES'],
        issue_manage_roles: ['ADMIN', 'PROJECT_MANAGER', 'PROJECT_MANAGER_AND_SALES', 'SALES', 'TELESALES'],
        invoice_creator_roles: ['ADMIN', 'SALES', 'TELESALES', 'PROJECT_MANAGER_AND_SALES'],
        invoice_verifier_roles: ['ADMIN'],
        leave_apply_roles: ['SALES', 'TELESALES', 'PROJECT_MANAGER', 'PROJECT_MANAGER_AND_SALES'],
        leave_edit_own_roles: ['SALES', 'TELESALES', 'PROJECT_MANAGER', 'PROJECT_MANAGER_AND_SALES'],
        leave_cancel_own_roles: ['SALES', 'TELESALES', 'PROJECT_MANAGER', 'PROJECT_MANAGER_AND_SALES'],
        leave_manage_roles: ['ADMIN'],
        salary_manage_roles: ['ADMIN'],
        salary_view_all_roles: ['ADMIN'],
        incentive_manage_roles: ['ADMIN'],
        incentive_view_all_roles: ['ADMIN'],
        employee_manage_roles: ['ADMIN'],
    };

    window.hasFeatureAccess = function(featureKey, roleInput) {
        const roleName = String(roleInput || getUser()?.role || '').toUpperCase();
        if (!roleName) return false;
        const effective = window.__crmEffectiveAccessPolicy;
        const featureAccess = effective?.feature_access || effective?.policy?.feature_access || FEATURE_ACCESS_FALLBACK;
        const allowedRoles = featureAccess?.[featureKey] || FEATURE_ACCESS_FALLBACK[featureKey] || [];
        return Array.isArray(allowedRoles) && allowedRoles.map(v => String(v).toUpperCase()).includes(roleName);
    };

    function getAllowedPagesForRole(role) {
        const roleName = (role || '').toUpperCase();
        const effective = window.__crmEffectiveAccessPolicy;
        if (effective && Array.isArray(effective.allowed_pages) && effective.role === roleName) {
            return effective.allowed_pages;
        }
        const policyMap = effective?.policy?.page_access;
        if (policyMap && policyMap[roleName]) {
            return policyMap[roleName];
        }
        return ROLE_PERMISSIONS_FALLBACK[roleName] || [];
    }

    function enforceRoleAccess(role) {
        if (!role || role === 'ADMIN') return true;
        const path = window.location.pathname.split('/').pop();
        if (!path || path === 'index.html') return true;

        const allowed = getAllowedPagesForRole(role);
        if (!allowed.includes(path) && !allowed.includes('*')) {
            showAccessDeniedState(role, path);
            return false;
        }
        return true;
    }

    // --- OPTIMISTIC UI ---
    // If we have a user in session, show the page IMMEDIATELY.
    if (user) {
        enforceRoleAccess(user.role);
        document.body.style.visibility = 'visible';
        const el = document.getElementById('username-display');
        if (el) el.textContent = user.name || 'User';
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
        .then(async profile => {
            if (!profile) return;
            const userData = {
                id: profile.id,
                name: profile.name || profile.email,
                role: profile.role,
                referral_code: profile.referral_code
            };
            localStorage.setItem('crm_user', JSON.stringify(userData));

            if (window.ApiClient && window.ApiClient.getEffectiveAccessPolicy) {
                try {
                    const effective = await window.ApiClient.getEffectiveAccessPolicy();
                    window.__crmEffectiveAccessPolicy = effective;
                } catch (e) {
                    console.warn('Failed to load effective access policy, using fallback map', e);
                }
            }

            enforceRoleAccess(userData.role);
            document.body.style.visibility = 'visible';
            const el = document.getElementById('username-display');
            if (el) el.textContent = profile.name || 'User';

            // Fetch and check for critical issues across the app
            checkCriticalIssues();
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

// Global Critical Issue Check
async function checkCriticalIssues() {
    // Only check if we are on a valid inner page
    const isLoginPage = window.location.pathname.endsWith('index.html') || window.location.pathname.endsWith('/');
    if (isLoginPage) return;

    try {
        const issues = await apiGet('/issues/?limit=100');
        const criticalIssues = issues.filter(i => i.severity === 'HIGH' && i.status === 'PENDING');

        if (criticalIssues.length > 0) {
            // 1. Highlight the sidebar link
            // Wait for sidebar to render just in case
            setTimeout(() => {
                const issuesLink = document.querySelector('a.sb-link[href="issues.html"]');
                if (issuesLink) {
                    issuesLink.classList.add('has-critical-issue');
                    // Optional: auto-expand the PM section if it's hidden
                    const parentSection = issuesLink.closest('.sb-section');
                    if (parentSection) {
                        const hdr = parentSection.querySelector('.sb-section-header');
                        const lst = parentSection.querySelector('.sb-section-items');
                        if (hdr && !hdr.classList.contains('open')) {
                            hdr.classList.add('open');
                            if (lst) lst.classList.add('open');
                        }
                    }
                }
            }, 500);

            // 2. Inject into the notification dropdown
            setTimeout(() => {
                const bellIcon = document.querySelector('.bi-bell')?.parentElement;
                if (bellIcon) {
                    // Make sure the red dot is visible
                    let dot = bellIcon.querySelector('.bg-danger');
                    if (!dot) {
                        bellIcon.insertAdjacentHTML('beforeend', '<span class="position-absolute bg-danger border border-white rounded-circle" style="width:10px;height:10px;top:8px;right:8px;"></span>');
                    }

                    // Update the dropdown menu content
                    const dropdownMenu = bellIcon.nextElementSibling;
                    if (dropdownMenu && dropdownMenu.classList.contains('dropdown-menu')) {
                        const notifCountBadge = dropdownMenu.querySelector('.badge.bg-danger');
                        if (notifCountBadge) {
                            notifCountBadge.textContent = criticalIssues.length;
                        }

                        // Replace the "No new alerts" text with the critical issue alert
                        const contentBody = dropdownMenu.querySelector('.p-3.text-center');
                        if (contentBody) {
                            contentBody.className = 'p-0';
                            contentBody.innerHTML = `
                                <div class="px-3 py-3 border-bottom d-flex gap-3 align-items-start" style="background-color: #FEF2F2; cursor: pointer;" onclick="window.location.href='issues.html'">
                                    <i class="bi bi-exclamation-octagon-fill text-danger mt-1 fs-5"></i>
                                    <div>
                                        <div class="fw-bold text-dark mb-1">Critical Issue Alert</div>
                                        <p class="mb-0 text-muted small" style="line-height: 1.4;">There ${criticalIssues.length === 1 ? 'is' : 'are'} ${criticalIssues.length} unresolved high-severity issue(s) requiring immediate attention.</p>
                                    </div>
                                </div>
                            `;
                        }
                    }
                }
            }, 600);
        }
    } catch (e) {
        console.warn("Could not check critical issues", e);
    }
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

// DELETE shorthand
async function apiDelete(path) {
    const res = await apiFetch(path, { method: 'DELETE' });
    if (!res || !res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `DELETE ${path} failed`);
    }
    // DELETE often returns 204 No Content, so we don't always expect JSON
    return res.status === 204 ? null : res.json();
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

