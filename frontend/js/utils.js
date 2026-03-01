/**
 * Shared utilities for CRM AI SETU Frontend
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

// Export to window
window.toast = toast;
window.requireAuth = requireAuth;
window.showOfflineBanner = showOfflineBanner;
