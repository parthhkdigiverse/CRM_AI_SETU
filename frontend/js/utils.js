// frontend/js/utils.js
/**
 * Shared utilities for SRM AI SETU Frontend
 */

// ── Authentication ──
function requireAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.replace('index.html');
        return false;
    }
    return true;
}

// ── UI Components ──

/**
 * Shows a toast notification
 * @param {string} msg 
 * @param {'success' | 'error' | 'warning' | 'info'} type 
 */
function toast(msg, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);

        // Add styles if missing
        if (!document.getElementById('toast-styles')) {
            const style = document.createElement('style');
            style.id = 'toast-styles';
            style.textContent = `
                #toast-container {
                    position: fixed;
                    bottom: 24px;
                    right: 24px;
                    z-index: 10000;
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }
                .custom-toast {
                    background: #0f172a;
                    color: #fff;
                    padding: 12px 20px;
                    border-radius: 12px;
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    animation: toastSlideUp 0.3s ease-out;
                    min-width: 200px;
                }
                @keyframes toastSlideUp {
                    from { transform: translateY(100%); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    const t = document.createElement('div');
    t.className = `custom-toast toast-${type}`;

    let icon = 'bi-check-circle-fill text-success';
    if (type === 'error') icon = 'bi-exclamation-circle-fill text-danger';
    if (type === 'warning') icon = 'bi-exclamation-triangle-fill text-warning';
    if (type === 'info') icon = 'bi-info-circle-fill text-info';

    t.innerHTML = `<i class="bi ${icon}"></i><span>${msg}</span>`;
    container.appendChild(t);

    setTimeout(() => {
        t.style.opacity = '0';
        t.style.transition = 'opacity 0.5s ease-out';
        setTimeout(() => t.remove(), 500);
    }, 4000);
}

/**
 * Shows a global "Offline" banner if the server is unreachable
 */
function showOfflineBanner(show = true) {
    let banner = document.getElementById('offline-banner');
    if (show) {
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'offline-banner';
            banner.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #ef4444;
                color: white;
                text-align: center;
                padding: 8px;
                font-weight: 600;
                z-index: 10001;
                font-size: 0.9rem;
            `;
            banner.innerHTML = '<i class="bi bi-wifi-off me-2"></i> Server Disconnected. Some features may be unavailable.';
            document.body.appendChild(banner);
        }
    } else {
        if (banner) banner.remove();
    }
}

/**
 * Toggles password visibility for a given input element
 * @param {string} inputId The ID of the password input
 * @param {string} iconId The ID of the icon to toggle
 */
function togglePasswordVisibility(inputId, iconId) {
    const inp = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (!inp || !icon) return;
    
    if (inp.type === 'password') {
        inp.type = 'text';
        icon.className = 'bi bi-eye-slash';
    } else {
        inp.type = 'password';
        icon.className = 'bi bi-eye';
    }
}

// Export to window
window.togglePasswordVisibility = togglePasswordVisibility;
window.requireAuth = requireAuth;
window.showOfflineBanner = showOfflineBanner;

// ── API Helper Functions ──

/**
 * Global convenience function for GET requests
 * Wraps ApiClient.request() for simpler usage
 */
async function apiGet(path) {
    try {
        return await ApiClient.request(path, { method: 'GET' });
    } catch (error) {
        console.error(`apiGet failed for ${path}:`, error);
        throw error;
    }
}

/**
 * Global convenience function for POST/PATCH requests
 * Wraps fetch with proper auth headers
 */
async function apiFetch(path, options = {}) {
    const url = `${ApiClient.API_BASE_URL}${path}`;
    const headers = {
        ...(options.headers || {})
    };

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
    }

    const token = ApiClient.getAccessToken();
    if (token && !options.noAuth) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        return await fetch(url, {
            ...options,
            headers
        });
    } catch (error) {
        console.error(`apiFetch failed for ${path}:`, error);
        if (window.showOfflineBanner) window.showOfflineBanner(true);
        throw error;
    }
}

// Export to window
window.apiGet = apiGet;
window.apiFetch = apiFetch;

/**
 * Alias for toast() - some pages use showToast() instead
 */
function showToast(msg, type = 'success') {
    return toast(msg, type);
}
window.showToast = showToast;

// ── Shared Archive UI Component ──
class ArchivedDataOffcanvas {
    constructor(options) {
        this.moduleName = options.moduleName;
        this.title = options.title || `Archived ${this.moduleName}`;
        this.columns = options.columns || [{ key: 'name', label: 'Name' }];
        this.onRestore = options.onRestore || null;
        this.offcanvasId = `archived-offcanvas-${this.moduleName}`;
        
        this._injectHtml();
        this.offcanvasEl = document.getElementById(this.offcanvasId);
        this.bsOffcanvas = new bootstrap.Offcanvas(this.offcanvasEl);
        window.ArchivedDataOffcanvas.instances[this.offcanvasId] = this;
    }

    _injectHtml() {
        if (!document.getElementById(this.offcanvasId)) {
            const html = `
            <div class="offcanvas offcanvas-end" tabindex="-1" id="${this.offcanvasId}" style="width: 500px; z-index: 1055;">
                <div class="offcanvas-header bg-light border-bottom">
                    <h5 class="offcanvas-title fw-bold">
                        <i class="bi bi-archive text-muted me-2"></i>${this.title}
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Close"></button>
                </div>
                <div class="offcanvas-body p-0">
                    <div class="p-3">
                        <p class="text-muted small mb-0">Restore items previously removed. They will reappear in your active lists.</p>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-hover align-middle mb-0" id="${this.offcanvasId}-table">
                            <thead class="bg-light">
                                <tr class="x-small text-uppercase text-muted fw-bold">
                                    ${this.columns.map(c => `<th>${c.label}</th>`).join('')}
                                    <th class="text-end pe-4">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="${this.offcanvasId}-body">
                                <tr>
                                    <td colspan="${this.columns.length + 1}" class="text-center py-4 text-muted">
                                        <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
                                        <span class="ms-2">Loading...</span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>`;
            document.body.insertAdjacentHTML('beforeend', html);
        }
    }

    async open() {
        this.bsOffcanvas.show();
        await this.loadData();
    }

    async loadData() {
        const tbody = document.getElementById(`${this.offcanvasId}-body`);
        tbody.innerHTML = `<tr><td colspan="${this.columns.length + 1}" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;
        
        try {
            const data = await ApiClient.fetchArchived(this.moduleName);
            this.renderTable(data || []);
        } catch (err) {
            console.error('Failed to fetch archived data', err);
            tbody.innerHTML = `<tr><td colspan="${this.columns.length + 1}" class="text-center py-4 text-danger">Error loading data</td></tr>`;
        }
    }

    renderTable(data) {
        const tbody = document.getElementById(`${this.offcanvasId}-body`);
        if (!data || data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${this.columns.length + 1}" class="text-center py-5">
                <i class="bi bi-inbox text-muted" style="font-size:2rem;"></i>
                <p class="text-muted mt-2 mb-0">No archived items found</p>
            </td></tr>`;
            return;
        }

        const user = ApiClient.getCurrentUser();
        const isAdmin = user && user.role && user.role.toUpperCase() === 'ADMIN';

        tbody.innerHTML = data.map(item => {
            const colsHtml = this.columns.map(col => {
                const val = col.render ? col.render(item) : (item[col.key] || '—');
                return `<td>${val}</td>`;
            }).join('');
            
            return `
            <tr>
                ${colsHtml}
                <td class="text-end pe-4 text-nowrap">
                    <button class="btn btn-sm btn-outline-primary rounded-3 me-1" onclick="window.ArchivedDataOffcanvas.instances['${this.offcanvasId}'].restoreItem(${item.id})">
                        <i class="bi bi-arrow-90deg-up"></i> Restore
                    </button>
                    ${isAdmin ? `
                    <button class="btn btn-sm btn-outline-danger rounded-3" onclick="window.ArchivedDataOffcanvas.instances['${this.offcanvasId}'].hardDeleteItem(${item.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                    ` : ''}
                </td>
            </tr>`;
        }).join('');
    }

    async restoreItem(id) {
        try {
            await ApiClient.unarchiveItem(this.moduleName, id);
            toast('Item restored successfully');
            await this.loadData();
            if (this.onRestore) this.onRestore();
        } catch (err) {
            console.error('Error restoring item', err);
            toast(err?.data?.detail || 'Failed to restore item', 'error');
        }
    }

    async hardDeleteItem(id) {
        if (!confirm("Are you sure? This cannot be undone.")) return;
        try {
            await ApiClient.hardDeleteItem(this.moduleName, id);
            toast('Item permanently deleted');
            await this.loadData();
            if (this.onRestore) this.onRestore();
        } catch (err) {
            console.error('Error permanently deleting item', err);
            toast(err?.data?.detail || 'Failed to permanently delete item', 'error');
        }
    }
}
window.ArchivedDataOffcanvas = ArchivedDataOffcanvas;
window.ArchivedDataOffcanvas.instances = {};
