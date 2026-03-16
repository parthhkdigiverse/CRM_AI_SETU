// frontend/js/notifications.js
/**
 * SRM AI SETU — Notifications Page Logic
 * Handles fetching, rendering, and marking notifications as read.
 */

document.addEventListener('DOMContentLoaded', () => {
    loadNotifications();

    // Hook up the clear alerts button
    const clearBtn = document.querySelector('button[onclick="clearAlerts()"]');
    if (clearBtn) {
        clearBtn.setAttribute('onclick', 'clearNotifications()');
    }
});

async function loadNotifications() {
    const list = document.getElementById('notif-list');
    if (!list) return;

    try {
        const notifications = await apiGet('/notifications/');

        // Filter for unread only to ensure 'Master Feed' reflects current pending alerts
        const unreadOnly = (Array.isArray(notifications) ? notifications : []).filter(n => !n.is_read);

        if (unreadOnly.length === 0) {
            renderEmptyState();
            return;
        }

        renderNotifications(unreadOnly);
    } catch (error) {
        console.error('Failed to load notifications:', error);
        list.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-exclamation-circle text-danger" style="font-size: 3rem;"></i>
                <p class="text-muted mt-3">Failed to load notifications. Please try again later.</p>
            </div>
        `;
    }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notif-list');

    list.innerHTML = notifications.map(n => {
        // Dynamic title formatting similar to the dropdown
        let displayTitle = n.title;
        let iconClass = "bi-bell-fill";
        let iconBg = "bg-primary-subtle text-primary";

        if (n.title === "⏰ Upcoming Meeting") {
            const match = n.message.match(/with (.*?) starts/);
            const clientName = match ? match[1] : "Client";
            displayTitle = `Upcoming Session: ${clientName}`;
            iconClass = "bi-calendar-event";
            iconBg = "bg-warning-subtle text-warning";
        }

        // --- FIXED: Null-safe Timezone Parsing ---
        let timeStr = n.created_at;
        if (timeStr && typeof timeStr === 'string') {
            if (!timeStr.endsWith('Z') && !timeStr.includes('+')) {
                timeStr += 'Z';
            }
        } else {
            // Fallback for null/missing timestamps to prevent crash
            timeStr = new Date().toISOString();
        }
        const dateObj = new Date(timeStr);

        // Extract link and sanitize message for UI display
        let cleanMessage = n.message || "";
        let meetLink = null;
        let sessionClosed = false;

        if (cleanMessage.includes('STATUS:COMPLETED')) {
            sessionClosed = true;
            cleanMessage = cleanMessage.replace('STATUS:COMPLETED', '').trim();
        }

        if (cleanMessage.includes('LINK:')) {
            const parts = cleanMessage.split('LINK:');
            cleanMessage = parts[0].trim();
            meetLink = parts[1].trim();
        }

        return `
            <div class="d-flex align-items-start gap-3 p-4 border-bottom position-relative hover-light bg-primary-subtle" 
                 style="transition: background 0.2s;">
                <div class="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0 ${iconBg}"
                    style="width: 42px; height: 42px; z-index: 2;">
                    <i class="bi ${iconClass} fs-5"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="fw-bold text-dark fs-6">${displayTitle}</span>
                        <span class="text-muted small">${formatTimeAgo(n.created_at)}</span>
                    </div>
                    <p class="text-secondary mb-1">
                        ${cleanMessage.replace('STATUS:COMPLETED', '').trim()} 
                        ${sessionClosed ?
                            `<br><span class="badge text-bg-secondary mt-2" style="font-size:12px;"><i class="bi bi-clock-history me-1"></i>Session Ended</span>` :
                            meetLink ?
                            `<br><a href="${meetLink}" target="_blank" class="badge text-bg-primary text-decoration-none mt-2" style="font-size:12px;"><i class="bi bi-camera-video me-1"></i>Join Meeting</a>` : ''}
                    </p>
                    <div class="mt-2 text-end">
                        <span class="text-muted me-2 small"><i class="bi bi-clock me-1"></i>${dateObj.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}</span>
                        <span class="badge bg-light text-dark border rounded-pill small">${n.title ? n.title.replace(/⏰\s*/, '') : 'Alert'}</span>
                        <span class="badge bg-primary rounded-pill ms-1">New</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderEmptyState() {
    const list = document.getElementById('notif-list');
    list.innerHTML = `
        <div class="text-center py-5">
            <i class="bi bi-bell-slash text-muted" style="font-size: 3rem;"></i>
            <p class="text-muted mt-3">All caught up.</p>
        </div>
    `;
}

async function clearNotifications() {
    try {
        await apiPost('/notifications/mark-all-read');
        showToast('All notifications marked as read', 'success');

        // Update local DOM
        renderEmptyState();

        // Sync the nav bell immediately
        if (window.refreshBell) {
            window.refreshBell();
        }
    } catch (error) {
        console.error('Failed to clear notifications:', error);
        showToast('Failed to clear notifications', 'error');
    }
}

function formatTimeAgo(dateString) {
    // --- FIXED: Null-safe Time Ago logic ---
    if (!dateString) return 'Just now';

    let timeStr = dateString;
    if (typeof timeStr === 'string') {
        if (!timeStr.endsWith('Z') && !timeStr.includes('+')) {
            timeStr += 'Z';
        }
    }

    const date = new Date(timeStr);
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);

    if (diffInSeconds < 0 || isNaN(diffInSeconds)) return 'Just now';
    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 8400) return `${Math.floor(diffInSeconds / 3600)}h ago`;

    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}