// Helper to get initials
window.getInitials = function (name) {
    if (!name) return '??';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
        return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
};

window.updateBulkActionBar = function (options) {
    const { count, onDelete, onCancel } = options || {};
    let bar = document.getElementById('bulk-action-bar');

    if (!bar) {
        const html = `
        <div id="bulk-action-bar" class="bulk-action-bar">
            <div class="d-flex align-items-center gap-3">
                <div class="bulk-select-badge"><span id="bulk-count-val">0</span> Selected</div>
                <button class="btn btn-link p-0" id="bulk-cancel-btn">Cancel</button>
            </div>
            <div class="bulk-action-btn-group">
                <button class="bulk-delete-confirm-btn" id="bulk-delete-confirm-btn">
                    <i class="bi bi-trash me-2"></i> Delete
                </button>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        bar = document.getElementById('bulk-action-bar');
    }

    const countVal = document.getElementById('bulk-count-val');
    const deleteBtn = document.getElementById('bulk-delete-confirm-btn');
    const cancelBtn = document.getElementById('bulk-cancel-btn');

    if (count > 0) {
        if (countVal) countVal.textContent = count;
        bar.classList.add('show');

        if (deleteBtn) deleteBtn.onclick = (e) => {
            e.preventDefault();
            if (onDelete) onDelete();
        };
        if (cancelBtn) cancelBtn.onclick = (e) => {
            e.preventDefault();
            if (onCancel) onCancel();
        };
    } else {
        bar.classList.remove('show');
    }
};
console.log('UI Components: updateBulkActionBar ready');

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
    nav += sbSection('db', 'Dashboard', 'bi-grid-1x2', [
        { id: 'dashboard', href: 'dashboard.html', icon: 'bi-bar-chart-line-fill', label: 'Overview' },
        { id: 'timetable', href: 'timetable.html', icon: 'bi-calendar3', label: 'Timetable' },
        { id: 'todo', href: 'todo.html', icon: 'bi-check2-square', label: 'To-Do List' }
    ]);

    // ADMINISTRATION
    if (isAdmin) {
        nav += sbSection('admin', 'Administration', 'bi-shield-check', [
            { id: 'admin', href: 'admin.html', icon: 'bi-people', label: 'Users & Roles' }
        ]);
    }

    // FIELD OPERATIONS
    const fieldItems = [
        { id: 'leads', href: 'leads.html', icon: 'bi-kanban', label: 'Project Overview' },
        { id: 'visits', href: 'visits.html', icon: 'bi-calendar3', label: 'Visits' }
    ];
    if (isAdmin || isSales || isPM) {
        fieldItems.splice(1, 0, { id: 'areas', href: 'areas.html', icon: 'bi-building', label: 'Areas & Shops' });
    }
    nav += sbSection('field', 'Field Operations', 'bi-geo-alt', fieldItems);

    // PROJECT MANAGEMENT
    nav += sbSection('pm', 'Project Management', 'bi-briefcase', [
        { id: 'demo', href: 'projects_demo.html', icon: 'bi-play-circle', label: 'Demo' },
        { id: 'projects', href: 'projects.html', icon: 'bi-briefcase', label: 'Projects' },
        { id: 'meetings', href: 'meetings.html', icon: 'bi-calendar-event', label: 'Meetings' },
        { id: 'issues', href: 'issues.html', icon: 'bi-exclamation-triangle', label: 'Issues' }
    ]);

    // CLIENT RELATIONS
    const crItems = [
        { id: 'clients', href: 'clients.html', icon: 'bi-people', label: 'Clients' },
        { id: 'payment', href: 'billing.html', icon: 'bi-receipt', label: 'Billing & Invoices' }
    ];
    if (isAdmin || isPM) {
        crItems.push({ id: 'feedback', href: 'feedback.html', icon: 'bi-chat-square-text', label: 'Feedback' });
    }
    nav += sbSection('cr', 'Client Relations', 'bi-people', crItems);

    // HR & PAYROLL
    const hrItems = [
        { id: 'leaves', href: 'leaves.html', icon: 'bi-calendar3', label: 'Leaves' }
    ];
    if (isAdmin) {
        hrItems.unshift({ id: 'employees', href: 'employees.html', icon: 'bi-people', label: 'Employees' });
        hrItems.splice(1, 0, { id: 'salary', href: 'salary.html', icon: 'bi-cash-stack', label: 'Salary' });
        hrItems.push({ id: 'incentives', href: 'incentives.html', icon: 'bi-trophy', label: 'Incentives' });
    }
    nav += sbSection('hr', 'HR & Payroll', 'bi-currency-dollar', hrItems);

    // REPORTS
    nav += sbSection('rpt', 'Reports & Analytics', 'bi-graph-up', [
        { id: 'reports', href: 'reports.html', icon: 'bi-graph-up', label: 'Reports' }
    ]);

    const userName = u?.name || u?.email || 'User';
    const initials = userName.slice(0, 2).toUpperCase();
    const userInitials = window.getInitials(userName);
    const userRole = (u?.role || 'USER').replace(/_/g, ' ');

    return `
    <div id="sidebar-container">
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon"><i class="bi bi-grid-fill"></i></div>
            <span>SRM AI SETU</span>
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
    const initials = window.getInitials(u?.name || u?.email || 'AD');

    const pageToParent = {
        'Users & Roles': 'Administration',
        'Project Overview': 'Field Operations',
        'Visits': 'Field Operations',
        'Areas & Shops': 'Field Operations',
        'Projects': 'Project Management',
        'Project Management Demo': 'Project Management',
        'Meeting Strategy': 'Project Management',
        'Meetings': 'Project Management',
        'Issues': 'Project Management',
        'Clients': 'Client Relations',
        'Billing & Invoices': 'Client Relations',
        'Employees': 'HR & Payroll',
        'Salary': 'HR & Payroll',
        'Leaves': 'HR & Payroll',
        'Incentives': 'HR & Payroll',
        'Demo': 'Project Management',
        'Reports': 'Reports & Analytics',
        'Timetable': 'Dashboard',
        'Timetable & Schedule': 'Dashboard',
        'To-Do List': 'Dashboard',
        'TO-DO List': 'Dashboard',
        'To-do': 'Dashboard',
        'Overview': 'Dashboard',
        'Dashboard': 'Home',
        'Profile': 'Account',
        'My Profile': 'Account',
        'Settings': 'Account',
        'Notifications': 'System',
        'Search Results': 'Search'
    };

    // Standardize key matching: trim and case-insensitive
    const normalizedTitle = (pageTitle || '').trim();
    let parent = pageToParent[normalizedTitle];

    if (!parent) {
        const lowerTitle = normalizedTitle.toLowerCase();
        const foundKey = Object.keys(pageToParent).find(k => k.toLowerCase() === lowerTitle);
        if (foundKey) parent = pageToParent[foundKey];
    }
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
            <!-- Add New Dropdown -->
            <div class="dropdown">
                <button class="btn btn-primary d-flex align-items-center gap-2 px-3 dropdown-toggle shadow-sm" type="button" id="addNewDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="font-size:0.875rem; border-radius: 8px; height: 40px; white-space: nowrap;">
                    <i class="bi bi-plus-lg"></i> Add New
                </button>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="addNewDropdown" style="font-size: 0.875rem; border-radius:12px; padding:8px; min-width:210px;">
                    <li><a class="dropdown-item rounded-2 py-2" href="clients.html"><i class="bi bi-people me-2 text-info"></i> New Client</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="projects.html?add=true"><i class="bi bi-briefcase me-2 text-primary"></i> New Project</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="areas.html?add=true"><i class="bi bi-building me-2" style="color:#6366f1;"></i> New Area / Shop</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="visits.html?add=true"><i class="bi bi-geo-alt me-2 text-success"></i> New Visit</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="meetings.html?add=true"><i class="bi bi-calendar-event me-2 text-success"></i> New Meeting</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="todo.html"><i class="bi bi-check2-square me-2 text-primary"></i> New Task</a></li>
                    <li><hr class="dropdown-divider my-1"></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="javascript:void(0)" onclick="if(window.openNewBillModal) window.openNewBillModal();"><i class="bi bi-receipt me-2 text-danger"></i> New Payment</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="issues.html?add=true"><i class="bi bi-exclamation-triangle me-2 text-warning"></i> New Issue</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="feedback.html?add=true"><i class="bi bi-chat-square-text me-2 text-info"></i> New Feedback</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="leaves.html?add=true"><i class="bi bi-calendar3 me-2 text-warning"></i> New Leave Request</a></li>
                    <li><hr class="dropdown-divider my-1"></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="admin.html"><i class="bi bi-person-plus me-2 text-secondary"></i> New User</a></li>
                </ul>
            </div>
            <!-- Notifications Bell -->
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
                <ul class="dropdown-menu dropdown-menu-end shadow border-0 p-2" aria-labelledby="profileDropdown" style="border-radius:12px; min-width:200px; font-size:0.875rem;">
                    <li class="px-2 pt-1 pb-2">
                        <div class="fw-bold text-dark" style="font-size:0.85rem; line-height:1.3;">${u?.name || 'Admin'}</div>
                        <div class="text-muted" style="font-size:0.73rem;">${u?.email || role}</div>
                    </li>
                    <li><hr class="dropdown-divider my-1"></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="profile.html"><i class="bi bi-person me-2 text-primary"></i> My Profile</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="settings.html"><i class="bi bi-gear me-2 text-secondary"></i> Settings</a></li>
                    <li><hr class="dropdown-divider my-1"></li>
                    <li><a class="dropdown-item rounded-2 py-2 text-danger" href="#" onclick="logout();return false;"><i class="bi bi-box-arrow-right me-2"></i> Logout</a></li>
                </ul>
            </div>
        </div>
    </div>`;

    const rightSide = document.querySelector('.flex-grow-1');
    if (rightSide) {
        rightSide.insertAdjacentHTML('afterbegin', headerHtml);
    }

    startNotificationPolling();
    checkHighPriorityIssues();
    if (typeof window.initLiveSearch === 'function') {
        window.initLiveSearch();
    }

    setTimeout(() => {
        if (window.checkUrlForQuickAdd) window.checkUrlForQuickAdd();
    }, 500);
}



// ─── GLOBAL QUICK ADD HANDLER ──────────────────────────────────────────
window.checkUrlForQuickAdd = function () {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('add') !== 'true') return;

    const path = window.location.pathname.toLowerCase();

    try {
        if (path.includes('visits.html')) {
            const modal = document.getElementById('visitModal');
            if (modal) modal.classList.add('show');
        }
        else if (path.includes('meetings.html')) {
            const modalEl = document.getElementById('addMeetingModal');
            if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
        else if (path.includes('issues.html')) {
            const modalEl = document.getElementById('addIssueModal');
            if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
        else if (path.includes('projects.html')) {
            const addBtn = document.querySelector('button[onclick*="openProjectUpdateModal"]') ||
                document.querySelector('.page-content button.btn-primary');
            if (addBtn) addBtn.click();
        }
        else if (path.includes('areas.html')) {
            const addBtn = document.querySelector('button[onclick*="openAreaModal"]') ||
                document.querySelector('.page-content button.btn-primary');
            if (addBtn) addBtn.click();
        }
        else if (path.includes('feedback.html')) {
            const modalEl = document.getElementById('addFeedbackModal');
            if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
        }
        else if (path.includes('leaves.html')) {
            if (window.openLeaveModal) window.openLeaveModal();
            else {
                const modal = document.getElementById('leaveModal');
                if (modal) modal.classList.add('show');
            }
        }
    } catch (e) {
        console.warn("Quick Add trigger failed:", e);
    }
};

// ─── NOTIFICATION BELL POLLING ────────────────────────────────────────
// State to track if polling is already active
window._notifPollStarted = window._notifPollStarted || false;

// Expose refreshBell globally so other pages (like notifications.html) can trigger an instant sync.
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

// ─── Global Live Search Logic ───
window.initLiveSearch = function () {
    const input = document.getElementById('global-search-input');
    const dropdown = document.getElementById('live-search-dropdown');
    if (!input || !dropdown) return;

    let debounceTimer;

    // Icons for different models
    const typeIcons = {
        client: '<i class="bi bi-person text-info"></i>',
        issue: '<i class="bi bi-exclamation-triangle text-warning"></i>',
        project: '<i class="bi bi-kanban text-primary"></i>',
        employee: '<i class="bi bi-person-badge text-secondary"></i>',
        lead: '<i class="bi bi-kanban text-danger"></i>',
        payment: '<i class="bi bi-receipt text-success"></i>',
        area: '<i class="bi bi-geo-alt" style="color:#6366f1;"></i>',
        meeting: '<i class="bi bi-calendar-event text-success"></i>'
    };

    // Base paths for redirection
    const typeLinks = {
        client: 'clients.html?id=',
        issue: 'issues.html?id=',
        project: 'projects.html?id=',
        employee: 'admin.html', // simplified for now
        lead: 'leads.html?id=',
        payment: 'clients.html', // payments don't have dedicated view page yet
        area: 'areas.html?id=',
        meeting: 'meetings.html?id='
    };

    input.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        if (query.length < 2) {
            dropdown.classList.remove('show');
            return; // Too short to search
        }

        debounceTimer = setTimeout(async () => {
            try {
                // Ensure apiGet is globally available (from api.js)
                const res = await apiGet(`/search/?q=${encodeURIComponent(query)}`);

                let html = '';
                let hasResults = false;

                // Simple helper to highlight matched text (case-insensitive)
                const highlight = (text) => {
                    if (!text) return '';
                    const strText = String(text);
                    const regex = new RegExp(`(${query})`, 'gi');
                    return strText.replace(regex, '<span class="search-highlight">$1</span>');
                };

                for (const [category, items] of Object.entries(res)) {
                    if (items && items.length > 0) {
                        hasResults = true;
                        const catLabel = category.charAt(0).toUpperCase() + category.slice(1);
                        html += `<div class="search-section-header">${catLabel}</div>`;

                        items.forEach(item => {
                            const icon = typeIcons[item.type] || '<i class="bi bi-search py-1"></i>';
                            const link = typeLinks[item.type] ? typeLinks[item.type] + item.id : 'search.html?q=' + encodeURIComponent(query);

                            html += `
                                <a href="${link}" class="search-result-item">
                                    <div class="search-result-icon">${icon}</div>
                                    <div class="search-result-info">
                                        <div class="search-result-name">${highlight(item.name || 'Unknown')}</div>
                                        <div class="search-result-sub">${highlight(item.subtext || '')}</div>
                                    </div>
                                </a>
                            `;
                        });
                    }
                }

                if (!hasResults) {
                    html = `<div class="p-3 text-center text-muted small">No results found for "${query}"</div>`;
                }

                dropdown.innerHTML = html;
                dropdown.classList.add('show');
            } catch (err) {
                console.error("Live search failed", err);
            }
        }, 300); // 300ms debounce
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });

    // Re-open if clicking back on input with value
    input.addEventListener('focus', () => {
        if (input.value.trim().length >= 2 && dropdown.innerHTML.trim() !== '') {
            dropdown.classList.add('show');
        }
    });
};



window.checkHighPriorityIssues = async function () {
    if (!localStorage.getItem('access_token')) return;
    try {
        const issues = await apiGet('/issues/');
        const unreadHigh = (Array.isArray(issues) ? issues : []).filter(i => i.severity === 'HIGH' && i.status === 'PENDING');

        const alertContainerId = 'high-priority-global-alert';
        let alertEl = document.getElementById(alertContainerId);

        if (unreadHigh.length > 0) {
            if (!alertEl) {
                const html = `
                <div id="${alertContainerId}" class="alert alert-danger d-flex align-items-center justify-content-between py-2 px-3 mb-0 border-0 rounded-0" style="background-color: #B91C1C; color: white; position: sticky; top: 0; z-index: 2000; font-size: 0.85rem; font-weight: 600;">
                    <div class="d-flex align-items-center gap-2">
                        <i class="bi bi-exclamation-triangle-fill"></i>
                        <span>System Alert: ${unreadHigh.length} Unresolved High Priority Issue(s) detected.</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <a href="issues.html" class="btn btn-sm btn-light py-0 px-2 fw-bold" style="font-size: 0.75rem; color: #B91C1C;">View Issues</a>
                        <button type="button" onclick="(function(){ var el=document.getElementById('${alertContainerId}'); if(el) el.remove(); var th=document.querySelector('.top-header'); if(th) th.style.top='0'; var sb=document.getElementById('sidebar-container'); if(sb){sb.style.height='100vh';sb.style.top='0';} })()" style="background:none;border:none;color:white;font-size:1.1rem;line-height:1;padding:0 2px;cursor:pointer;opacity:0.85;" title="Dismiss">&times;</button>
                    </div>
                </div>`;
                document.body.insertAdjacentHTML('afterbegin', html);

                // Adjust top header position if it exists
                const topHeader = document.querySelector('.top-header');
                if (topHeader) {
                    topHeader.style.top = document.getElementById(alertContainerId).offsetHeight + 'px';
                }
                const sidebar = document.getElementById('sidebar-container');
                if (sidebar) {
                    sidebar.style.height = `calc(100vh - ${document.getElementById(alertContainerId).offsetHeight}px)`;
                    sidebar.style.top = document.getElementById(alertContainerId).offsetHeight + 'px';
                }
            } else {
                alertEl.querySelector('span').textContent = `System Alert: ${unreadHigh.length} Unresolved High Priority Issue(s) detected.`;
                // Re-sync layout offsets in case header shifted
                const topHeader = document.querySelector('.top-header');
                if (topHeader) topHeader.style.top = alertEl.offsetHeight + 'px';
            }
        } else if (alertEl) {
            alertEl.remove();
            const topHeader = document.querySelector('.top-header');
            if (topHeader) topHeader.style.top = '0';
            const sidebar = document.getElementById('sidebar-container');
            if (sidebar) {
                sidebar.style.height = '100vh';
                sidebar.style.top = '0';
            }
        }
    } catch (e) {
        console.error("High Priority check failed", e);
    }
};

/**
 * Renders a unified filter panel based on a configuration object.
 * @param {Object} config - The configuration for the filter panel.
 * @param {string} config.containerId - The ID of the element where the panel will be rendered.
 * @param {Array} config.filters - Array of filter definitions.
 * @param {string} config.title - Optional title (default: 'Filters').
 * @param {Function} config.onApply - Callback function called with filter data.
 * @param {Function} config.onReset - Callback function called when filters are cleared.
 */
window.renderFilterPanel = function (config) {
    const { containerId, filters, title = 'Filters', onApply, onReset, headerContent = '' } = config;
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Filter container #${containerId} not found.`);
        return;
    }

    // Generate Filter Fields HTML
    const fieldsHtml = filters.map(f => {
        let inputHtml = '';
        if (f.type === 'select') {
            inputHtml = `
                <select id="${f.id}" class="form-select">
                    ${(f.options || []).map(opt => `<option value="${opt.value}" ${opt.selected ? 'selected' : ''}>${opt.label}</option>`).join('')}
                </select>`;
        } else if (f.type === 'date' || f.type === 'month') {
            inputHtml = `<input type="${f.type}" id="${f.id}" class="form-control" value="${f.value || ''}">`;
        } else { // Default to text input for 'text' and any other unspecified types
            inputHtml = `<input type="text" id="${f.id}" class="form-control" placeholder="${f.placeholder || ''}" value="${f.value || ''}">`;
        }

        return `
            <div class="filter-field">
                <label for="${f.id}">${f.label}</label>
                ${inputHtml}
            </div>`;
    }).join('');

    const html = `
        <div class="filter-panel">
            <div class="filter-panel-head" onclick="this.nextElementSibling.classList.toggle('open'); this.querySelector('.filter-toggle-btn').classList.toggle('open')">
                <div class="filter-panel-head-main">
                    <div class="filter-panel-head-left">
                        <i class="bi bi-filter"></i>
                        <span>${title}</span>
                    </div>
                    <div class="filter-active-pills" id="${containerId}-pills">
                        <!-- Active pills will be injected here -->
                    </div>
                </div>
                ${headerContent}
                <div class="filter-panel-head-meta">
                    <div class="filter-summary-text" id="${containerId}-summary">No filters active</div>
                    <button class="filter-toggle-btn">
                        <i class="bi bi-chevron-down"></i>
                    </button>
                </div>
            </div>
            <div class="filter-panel-body">
                <div class="filter-grid">
                    ${fieldsHtml}
                </div>
                <div class="filter-actions">
                    <button class="btn-filter-reset" id="${containerId}-reset">
                        <i class="bi bi-x-circle"></i> Clear
                    </button>
                    <button class="btn-filter-apply" id="${containerId}-apply">
                        <i class="bi bi-check2"></i> Apply Filters
                    </button>
                </div>
            </div>
        </div>`;

    container.innerHTML = html;

    const body = container.querySelector('.filter-panel-body');
    const pillsContainer = container.querySelector(`#${containerId}-pills`);
    const summaryText = container.querySelector(`#${containerId}-summary`);
    const applyBtn = container.querySelector(`#${containerId}-apply`);
    const resetBtn = container.querySelector(`#${containerId}-reset`);

    const updateUI = () => {
        const activeFilters = [];
        filters.forEach(f => {
            const el = document.getElementById(f.id);
            if (!el) return;
            const val = el.value;
            // Only consider as active if it's not empty or "ALL"
            if (val && val !== 'ALL' && val !== '') {
                let displayVal = val;
                if (f.type === 'select') {
                    const opt = f.options.find(o => o.value === val);
                    if (opt) displayVal = opt.label;
                }
                activeFilters.push({ id: f.id, label: f.label, value: displayVal });
            }
        });

        pillsContainer.innerHTML = activeFilters.map(af => `
            <div class="filter-pill">
                ${af.label}: ${af.value}
                <button class="filter-pill-remove" onclick="event.stopPropagation(); window.removeFilter('${containerId}', '${af.id}')">
                    <i class="bi bi-x"></i>
                </button>
            </div>`).join('');

        summaryText.textContent = activeFilters.length > 0 
            ? `${activeFilters.length} filter${activeFilters.length > 1 ? 's' : ''} active` 
            : 'No filters active';
    };

    // Global helper for pill removal
    window.removeFilter = (cid, fid) => {
        const el = document.getElementById(fid);
        if (el) {
            const filterDef = filters.find(f => f.id === fid);
            if (filterDef && filterDef.type === 'select') {
                el.value = filterDef.options[0]?.value || 'ALL';
            } else {
                el.value = '';
            }
            applyBtn.click();
        }
    };

    applyBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const data = {};
        filters.forEach(f => {
            const el = document.getElementById(f.id);
            if (el) data[f.id.replace('f-', '')] = el.value;
        });
        updateUI();
        body.classList.remove('open');
        container.querySelector('.filter-toggle-btn').classList.remove('open');
        if (onApply) onApply(data);
    });

    resetBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        filters.forEach(f => {
            const el = document.getElementById(f.id);
            if (el) {
                if (f.type === 'select') {
                    el.value = f.options[0]?.value || 'ALL';
                } else {
                    el.value = '';
                }
            }
        });
        updateUI();
        body.classList.remove('open');
        container.querySelector('.filter-toggle-btn').classList.remove('open');
        if (onReset) onReset();
    });

    // Initial UI update - ensure closed by default
    updateUI();
    body.classList.remove('open');
    container.querySelector('.filter-toggle-btn').classList.remove('open');
};

// Start both polls
function startAllPolling() {
    startNotificationPolling();
    // High priority check every 60s
    setInterval(window.checkHighPriorityIssues, 60000);
}
