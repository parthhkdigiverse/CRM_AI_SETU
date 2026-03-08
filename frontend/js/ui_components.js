// Centralized UI components for CRM AI SETU

function getUser() {
    try { return JSON.parse(localStorage.getItem('crm_user')); } catch { return null; }
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('crm_user');
    window.location.replace('index.html');
}

// ─── SIDEBAR ──────────────────────────────────────────────────────────
function renderSidebar(active) {
    const u = getUser();
    const role = u?.role || 'TELESALES';
    console.log('Sidebar Debug - Role:', role);

    const isAdmin = role === 'ADMIN';
    const isSales = role === 'SALES' || role === 'PROJECT_MANAGER_AND_SALES';
    const isTelesales = role === 'TELESALES';
    const isPM = role === 'PROJECT_MANAGER' || role === 'PROJECT_MANAGER_AND_SALES';
    const isClient = role === 'CLIENT';

    let nav = '';

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

    // DASHBOARD
    if (!isClient) {
        nav += sbSection('db', 'Dashboard', 'bi-grid-1x2', [
            { id: 'dashboard', href: 'dashboard.html', icon: 'bi-bar-chart-line-fill', label: 'Overview' },
            { id: 'timetable', href: 'timetable.html', icon: 'bi-calendar3', label: 'Timetable' },
            { id: 'todo', href: 'todo.html', icon: 'bi-check2-square', label: 'To-Do List' }
        ]);
    }

    // ADMINISTRATION
    if (isAdmin) {
        nav += sbSection('admin', 'Administration', 'bi-shield-check', [
            { id: 'admin', href: 'admin.html', icon: 'bi-people', label: 'Users & Roles' }
        ]);
    }

    // FIELD OPERATIONS
    if (isAdmin || isSales || isTelesales) {
        const fieldItems = [
            { id: 'leads', href: 'leads.html', icon: 'bi-bullseye', label: 'Project Overview' },
            { id: 'visits', href: 'visits.html', icon: 'bi-calendar3', label: 'Visits' }
        ];
        if (isAdmin || isSales || isPM) {
            fieldItems.splice(1, 0, { id: 'areas', href: 'areas.html', icon: 'bi-building', label: 'Areas & Shops' });
        }
        nav += sbSection('field', 'Field Operations', 'bi-geo-alt', fieldItems);
    }

    // PROJECT MANAGEMENT
    if (isAdmin || isPM) {
        nav += sbSection('pm', 'Project Management', 'bi-briefcase', [
            { id: 'projects', href: 'projects.html', icon: 'bi-briefcase', label: 'Projects' },
            { id: 'meetings', href: 'meetings.html', icon: 'bi-calendar-event', label: 'Meetings' },
            { id: 'issues', href: 'issues.html', icon: 'bi-exclamation-triangle', label: 'Issues' }
        ]);
    }

    // CLIENT RELATIONS
    if (isAdmin || isSales || isTelesales || isPM) {
        const crItems = [
            { id: 'clients', href: 'clients.html', icon: 'bi-people', label: 'Clients' },
            { id: 'payment', href: 'billing.html', icon: 'bi-receipt', label: 'Billing & Invoices' }
        ];
        if (isAdmin || isPM) {
            crItems.push({ id: 'feedback', href: 'feedback.html', icon: 'bi-chat-square-text', label: 'Feedback' });
        }
        nav += sbSection('cr', 'Client Relations', 'bi-people', crItems);
    }

    // HR & PAYROLL
    if (isAdmin) {
        nav += sbSection('hr', 'HR & Payroll', 'bi-currency-dollar', [
            { id: 'employees', href: 'employees.html', icon: 'bi-people', label: 'Employees' },
            { id: 'salary', href: 'salary.html', icon: 'bi-calendar3', label: 'Salary & Leaves' },
            { id: 'incentives', href: 'incentives.html', icon: 'bi-trophy', label: 'Incentives' }
        ]);
    }

    // REPORTS
    if (isAdmin || isPM) {
        nav += sbSection('rpt', 'Reports & Analytics', 'bi-graph-up', [
            { id: 'reports', href: 'reports.html', icon: 'bi-graph-up', label: 'Reports' }
        ]);
    }

    const userName = u?.name || u?.email || 'User';
    const initials = userName.slice(0, 2).toUpperCase();
    const userRole = (u?.role || 'USER').replace(/_/g, ' ');

    return `
    <div id="sidebar-container">
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon"><i class="bi bi-grid-fill"></i></div>
            <span>CRM AI SETU</span>
        </div>
        <div class="sb-scroll-area mt-2">${nav}</div>
        <div class="sb-bottom">
            <a href="settings.html" class="sb-bottom-link"><i class="bi bi-gear-fill"></i> Settings</a>
            <a href="#" class="sb-bottom-link logout" onclick="logout();return false;"><i class="bi bi-box-arrow-right"></i> Logout</a>
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
        if (isMe) {
            hdr.classList.toggle('open');
            lst && lst.classList.toggle('open');
            if (arr) arr.className = `bi ${hdr.classList.contains('open') ? 'bi-chevron-down' : 'bi-chevron-right'} sb-arrow`;
        }
    });
};

// ─── TOP HEADER ───────────────────────────────────────────────────────
function injectTopHeader(pageTitle) {
    if (document.querySelector('.top-header')) return;
    const u = getUser();
    const role = (u?.role || '').replace(/_/g, ' ');
    const initials = (u?.name || u?.email || 'AD').slice(0, 2).toUpperCase();

    const pageToParent = {
        'Users & Roles': 'Administration',
        'Project Overview': 'Field Operations',
        'Visits': 'Field Operations',
        'Areas & Shops': 'Field Operations',
        'Projects': 'Project Management',
        'Meetings': 'Project Management',
        'Issues': 'Project Management',
        'Clients': 'Client Relations',
        'Billing & Invoices': 'Client Relations',
        'Employees': 'HR & Payroll',
        'Salary & Leaves': 'HR & Payroll',
        'Incentives': 'HR & Payroll',
        'Reports': 'Reports & Analytics',
        'Timetable': 'Dashboard',
        'To-Do List': 'Dashboard',
        'Overview': 'Dashboard'
    };

    const parent = pageToParent[pageTitle];
    const breadcrumbHtml = parent ? `
        <div class="d-flex align-items-center gap-2">
            <span class="text-muted" style="font-size: 0.875rem;">${parent}</span>
            <i class="bi bi-chevron-right text-muted" style="font-size: 0.7rem;"></i>
            <div class="page-nav-title">${pageTitle}</div>
        </div>
    ` : `<div class="page-nav-title">${pageTitle}</div>`;

    const alertsRedDot = '<span id="nav-notif-dot" class="position-absolute bg-danger border border-white rounded-circle d-none" style="width:10px;height:10px;top:8px;right:8px;"></span>';

    const headerHtml = `
    <div class="top-header">
        <div class="d-flex align-items-center">${breadcrumbHtml}</div>
        <div class="top-header-search" style="position:relative; z-index:1000;">
            <div class="position-relative w-100">
                <button class="btn p-0 position-absolute text-muted" style="left:12px; top:50%; transform:translateY(-50%); border:none; background:none; z-index:5;" onclick="const val = document.getElementById('global-search-input').value.trim(); if(val) window.location.href = 'search.html?q=' + encodeURIComponent(val);">
                    <i class="bi bi-search" style="font-size:0.9rem;"></i>
                </button>
                <input type="text" id="global-search-input" class="form-control bg-light border-0 shadow-none" placeholder="Search..." style="padding-left: 40px; border-radius: 10px; font-size: 0.9rem; height: 42px;">
                <div id="live-search-dropdown" class="search-results-dropdown"></div>
            </div>
        </div>
        <div class="d-flex align-items-center justify-content-end gap-3">
            <div class="dropdown">
                <div class="position-relative text-muted" data-bs-toggle="dropdown" aria-expanded="false" style="cursor:pointer; font-size:1.25rem; width:40px; height:40px; display:flex; align-items:center; justify-content:center; background:#f8fafc; border-radius:50%;">
                    <i class="bi bi-bell"></i>
                    ${alertsRedDot}
                </div>
                <div class="dropdown-menu dropdown-menu-end shadow-lg border-0 p-0" style="width: 320px; border-radius: 12px; overflow: hidden; z-index: 9999;">
                    <div class="bg-light px-3 py-2 border-bottom d-flex justify-content-between align-items-center">
                        <span class="fw-bold fs-6">Notifications</span>
                    </div>
                    <div id="bell-notif-list">
                        <div class="p-3 text-center">
                            <i class="bi bi-bell-slash text-muted" style="font-size: 2rem;"></i>
                            <p class="text-muted small mt-2 mb-0">No new alerts.</p>
                        </div>
                    </div>
                    <div class="bg-light px-3 py-2 border-top text-center" style="cursor: pointer;" onclick="window.location.href='notifications.html'">
                        <span class="text-decoration-none small fw-semibold">View Master Feed</span>
                    </div>
                </div>
            </div>
            <div class="d-flex align-items-center gap-2 ps-2 dropdown border-start ms-1">
                <div class="rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center fw-bold dropdown-toggle shadow-sm" id="profileDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="width:38px;height:38px;font-size:13px;cursor:pointer;">${initials}</div>
                <div class="d-none d-lg-block">
                    <div class="fw-bold text-dark" style="font-size:0.85rem; line-height:1;">${u?.name || 'Admin'}</div>
                    <div class="text-muted small" style="font-size:0.70rem; line-height:1.5;">${role}</div>
                </div>
            </div>
        </div>
    </div>`;

    const rightSide = document.querySelector('.flex-grow-1');
    if (rightSide) rightSide.insertAdjacentHTML('afterbegin', headerHtml);
    startNotificationPolling();
}

// ─── NOTIFICATION BELL POLLING ────────────────────────────────────────
window.refreshBell = async function () {
    if (!localStorage.getItem('access_token')) return;
    try {
        const { unread } = await apiGet('/notifications/unread-count');
        const dot = document.getElementById('nav-notif-dot');
        if (dot) unread > 0 ? dot.classList.remove('d-none') : dot.classList.add('d-none');

        const all = await apiGet('/notifications/?limit=100');
        const bellBody = document.getElementById('bell-notif-list');
        if (!bellBody) return;

        bellBody.innerHTML = '';

        const unreadList = (Array.isArray(all) ? all : []).filter(n => !n.is_read).slice(0, 5);
        if (unreadList.length === 0) {
            bellBody.innerHTML = `<div class="p-3 text-center"><p class="text-muted small mb-0">No new alerts.</p></div>`;
            return;
        }

        bellBody.innerHTML = unreadList.map(n => {
            try {
                let displayTitle = n.title;
                if (n.title === "⏰ Upcoming Meeting") {
                    const match = n.message.match(/with (.*?) starts/);
                    displayTitle = `Upcoming Session: ${match ? match[1] : "Client"}`;
                }

                let timeStr = n.created_at;
                if (timeStr && typeof timeStr === 'string') {
                    if (!timeStr.endsWith('Z') && !timeStr.includes('+')) timeStr += 'Z';
                } else timeStr = new Date().toISOString();
                const dateObj = new Date(timeStr);

                let cleanMessage = n.message || "";
                let meetLink = null;
                let sessionClosed = false;

                // --- FIXED: Detect and Strip Completion Payload ---
                if (cleanMessage.includes('STATUS:COMPLETED')) {
                    sessionClosed = true;
                    cleanMessage = cleanMessage.replace('STATUS:COMPLETED', '').trim();
                }

                if (cleanMessage.includes('LINK:')) {
                    const parts = cleanMessage.split('LINK:');
                    cleanMessage = parts[0].trim();
                    meetLink = parts[1].trim();
                }

                showBrowserNotification(n.id, displayTitle, cleanMessage, meetLink);

                return `
                <div class="d-flex gap-2 px-3 py-2 border-bottom bg-primary-subtle">
                    <div class="w-100 overflow-hidden">
                        <div class="fw-bold text-truncate text-dark" style="font-size:.82rem;">${displayTitle}</div>
                        <div class="text-muted text-wrap small mt-1" style="line-height: 1.3;">
                            ${cleanMessage}
                            ${sessionClosed ?
                        `<br><span class="badge text-bg-secondary mt-1" style="font-size:10px;">Ended</span>` :
                        meetLink ?
                            `<br><a href="${meetLink}" target="_blank" class="badge text-bg-primary text-decoration-none mt-1" style="font-size:10px;">Join Meeting</a>` : ''}
                        </div>
                        <div class="text-muted mt-1 small" style="font-size:.68rem;">
                            <i class="bi bi-clock"></i> ${dateObj.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
                        </div>
                    </div>
                </div>`;
            } catch (err) { return ""; }
        }).join('');
    } catch (e) { console.error(e); }
};

window._shownPushes = window._shownPushes || new Set();

function showBrowserNotification(notifId, title, bodyStr, link) {
    if (window._shownPushes.has(notifId) || !('Notification' in window)) return;
    window._shownPushes.add(notifId);
    if (Notification.permission === 'granted') {
        const popup = new Notification(title, { body: bodyStr });
        popup.onclick = () => { link ? window.open(link, '_blank') : window.location.href = 'notifications.html'; popup.close(); };
    }
}

function startNotificationPolling() {
    if (window._notifPollStarted) return;
    window._notifPollStarted = true;
    if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission();
    window.refreshBell();
    setInterval(window.refreshBell, 30000);
}