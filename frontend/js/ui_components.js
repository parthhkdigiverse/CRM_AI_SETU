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
        // Only Admin, Sales and PM can manage Areas & Shops
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

    // Build user identity card
    const userName = u?.name || u?.email || 'User';
    const userInitials = userName.slice(0, 2).toUpperCase();
    const userRole = (u?.role || 'USER').replace(/_/g, ' ');

    return `
    <div id="sidebar-container">
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon"><i class="bi bi-grid-fill"></i></div>
            <span>CRM AI SETU</span>
        </div>
        <div class="sidebar-user-card">
            <div class="sidebar-user-avatar">${userInitials}</div>
            <div class="sidebar-user-info">
                <div class="sidebar-user-name">${userName}</div>
                <div class="sidebar-user-role">${userRole}</div>
            </div>
        </div>
        <div class="sb-scroll-area">${nav}</div>
        <div class="sb-bottom">
            <a href="#" class="sb-bottom-link"><i class="bi bi-gear-fill"></i> Settings</a>
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

// Toggle password visibility helper
window.togglePasswordVisibility = function (inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input && icon) {
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.remove('bi-eye');
            icon.classList.add('bi-eye-slash');
        } else {
            input.type = 'password';
            icon.classList.remove('bi-eye-slash');
            icon.classList.add('bi-eye');
        }
    }
};

// ─── TOP HEADER ───────────────────────────────────────────────────────
function injectTopHeader(pageTitle) {
    if (document.querySelector('.top-header')) return;
    const u = getUser();
    const role = (u?.role || '').replace(/_/g, ' ');
    const initials = (u?.name || u?.email || 'AD').slice(0, 2).toUpperCase();

    // Map pages to their parent sections for breadcrumbs
    const pageToParent = {
        'Users & Roles': 'Administration',
        'Project Overview': 'Field Operations',
        'Visits': 'Field Operations',
        'Areas & Shops': 'Field Operations',
        'Projects': 'Project Management',
        'Meeting Strategy': 'Project Management',
        'Meetings': 'Project Management',
        'Issues': 'Project Management',
        'Clients': 'Client Relations',
        'Billing & Invoices': 'Client Relations',
        'Payment': 'Client Relations',
        'Feedback': 'Client Relations',
        'Employees': 'HR & Payroll',
        'Salary & Leaves': 'HR & Payroll',
        'Incentives': 'HR & Payroll',
        'Reports': 'Reports & Analytics',
        'Timetable': 'Dashboard',
        'To-Do List': 'Dashboard',
        'Overview': 'Dashboard',
        'Dashboard': 'Home',
        'Profile': 'Dashboard',
        'Search Results': 'Search'
    };

    const parent = pageToParent[pageTitle];
    const breadcrumbHtml = parent ? `
        <div class="d-flex align-items-center gap-2">
            <span class="text-muted" style="font-size: 0.875rem;">${parent}</span>
            <i class="bi bi-chevron-right text-muted" style="font-size: 0.7rem;"></i>
            <div class="page-nav-title">${pageTitle}</div>
        </div>
    ` : `
        <div class="page-nav-title">${pageTitle}</div>
    `;

    const alertsRedDot = '<span id="nav-notif-dot" class="position-absolute bg-danger border border-white rounded-circle d-none" style="width:10px;height:10px;top:8px;right:8px;"></span>';

    const headerHtml = `
    <div class="top-header">
        <!-- Left: Breadcrumb Title -->
        <div class="d-flex align-items-center">
            ${breadcrumbHtml}
        </div>

        <!-- Center: Global Search -->
        <div class="top-header-search" style="position:relative; z-index:1000;">
            <div class="position-relative w-100">
                <button class="btn p-0 position-absolute text-muted" style="left:12px; top:50%; transform:translateY(-50%); border:none; background:none; z-index:5;" onclick="const val = document.getElementById('global-search-input').value.trim(); if(val) window.location.href = 'search.html?q=' + encodeURIComponent(val);">
                    <i class="bi bi-search" style="font-size:0.9rem;"></i>
                </button>
                <input type="text" id="global-search-input" class="form-control bg-light border-0 shadow-none" placeholder="Search clients, projects, payments..." style="padding-left: 40px; border-radius: 10px; font-size: 0.9rem; height: 42px;" onkeypress="if(event.key === 'Enter' && this.value.trim()) { window.location.href = 'search.html?q=' + encodeURIComponent(this.value.trim()); }" autocomplete="off">
                
                <!-- Live Search Dropdown -->
                <div id="live-search-dropdown" class="search-results-dropdown">
                    <!-- Results injected here by JS -->
                </div>
            </div>
        </div>

        <!-- Right: Actions & Profile -->
        <div class="d-flex align-items-center justify-content-end gap-3">
            <!-- Add New Dropdown -->
            <div class="dropdown">
                <button class="btn btn-primary d-flex align-items-center gap-2 px-3 dropdown-toggle shadow-sm" type="button" id="addNewDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="font-size:0.875rem; border-radius: 8px; height: 40px; white-space: nowrap;">
                    <i class="bi bi-plus-lg"></i> Add New
                </button>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="addNewDropdown" style="font-size: 0.875rem; border-radius:12px; padding:8px; min-width:210px;">
                    <li><a class="dropdown-item rounded-2 py-2" href="leads.html?add=true"><i class="bi bi-bullseye me-2 text-primary"></i> New Project Lead</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="areas.html?add=true"><i class="bi bi-building me-2" style="color:#6366f1;"></i> New Area / Shop</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="clients.html"><i class="bi bi-people me-2 text-info"></i> New Client</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="meetings.html"><i class="bi bi-calendar-event me-2 text-success"></i> New Meeting</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="javascript:void(0)" onclick="if(window.openNewBillModal) window.openNewBillModal();"><i class="bi bi-file-invoice-dollar me-2 text-danger"></i> New Payment</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="issues.html"><i class="bi bi-exclamation-triangle me-2 text-warning"></i> New Issue</a></li>
                    <li><hr class="dropdown-divider my-1"></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="admin.html"><i class="bi bi-person-plus me-2 text-secondary"></i> New User</a></li>
                </ul>
            </div>
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
                            <p class="text-muted small mt-2 mb-0">No new system alerts right now.</p>
                        </div>
                    </div>
                    <div class="bg-light px-3 py-2 border-top text-center" style="cursor: pointer;" onclick="window.location.href='notifications.html'">
                        <a href="notifications.html" class="text-decoration-none small fw-semibold">View Master Feed</a>
                    </div>
                </div>
            </div>
            <!-- Profile Dropdown -->
            <div class="d-flex align-items-center gap-2 ps-2 dropdown border-start ms-1">
                <div class="rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center fw-bold dropdown-toggle shadow-sm" id="profileDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="width:38px;height:38px;font-size:13px;cursor:pointer;">${initials}</div>
                <div class="d-none d-lg-block">
                    <div class="fw-bold text-dark" style="font-size:0.85rem; line-height:1;">${u?.name || 'Admin'}</div>
                    <div class="text-muted small" style="font-size:0.70rem; line-height:1.5;">${role}</div>
                </div>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="profileDropdown" style="font-size: 0.875rem; border-radius:12px; padding:8px; z-index: 9999;">
                    <li><a class="dropdown-item py-2 rounded-2" href="javascript:void(0)" onclick="if(window.loadView) window.loadView('profile');"><i class="bi bi-person me-2 text-primary"></i> My Profile</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item py-2 rounded-2" href="javascript:void(0)" onclick="logout()" style="color:var(--danger);"><i class="bi bi-box-arrow-right me-2"></i> Logout</a></li>
                </ul>
            </div>
        </div>
    </div>`;
    const rightSide = document.querySelector('.flex-grow-1');
    if (rightSide) {
        // Inject header at top of the column
        rightSide.insertAdjacentHTML('afterbegin', headerHtml);
    }

    startNotificationPolling(); // ensure we start checking alerts
    if (typeof window.initLiveSearch === 'function') {
        window.initLiveSearch();
    }
}

// ─── NOTIFICATION BELL POLLING ────────────────────────────────────────
// State to track if polling is already active
window._notifPollStarted = window._notifPollStarted || false;

// Expose refreshBell globally so other pages (like notifications.html) can trigger an instant sync.
window.refreshBell = async function () {
    // Only fetch if we have a token
    if (!localStorage.getItem('access_token')) return;

    try {
        const { unread } = await apiGet('/notifications/unread-count');
        const dot = document.getElementById('nav-notif-dot');
        if (dot) {
            if (unread > 0) dot.classList.remove('d-none');
            else dot.classList.add('d-none');
        }

        // Populate the dropdown preview (unread only, top 5 max)
        const all = await apiGet('/notifications/?limit=100');
        const bellBody = document.getElementById('bell-notif-list');
        if (!bellBody) return;

        // Filter for unread only
        const unreadList = (Array.isArray(all) ? all : []).filter(n => !n.is_read).slice(0, 5);

        // Protect against no unread alerts
        if (unreadList.length === 0) {
            bellBody.innerHTML = `
                <div class="p-3 text-center">
                    <i class="bi bi-bell-slash text-muted" style="font-size:2rem;"></i>
                    <p class="text-muted small mt-2 mb-0">No new alerts right now.</p>
                </div>`;
            return;
        }

        bellBody.innerHTML = unreadList.map(n => {
            // Determine client name from message if possible, or fallback
            let displayTitle = n.title;
            if (n.title === "⏰ Upcoming Meeting") {
                const match = n.message.match(/with (.*?) starts/);
                const clientName = match ? match[1] : "Client";
                displayTitle = `Upcoming Session: ${clientName}`;
            }

            // Force UTC parsing: Append 'Z' if missing to ensure browser converts correctly to local time
            const dateObj = new Date(n.created_at.endsWith('Z') || n.created_at.includes('+') ? n.created_at : n.created_at + 'Z');

            return `
            <div class="d-flex gap-2 px-3 py-2 border-bottom bg-primary-subtle"
                 style="cursor:default; transition: background 0.2s;">
                <i class="bi bi-bell-fill text-primary mt-1 flex-shrink-0" style="font-size:.85rem;"></i>
                <div class="w-100 overflow-hidden">
                    <div class="fw-bold text-truncate text-dark" style="font-size:.82rem;">${displayTitle}</div>
                    <div class="text-muted text-wrap small mt-1" style="line-height: 1.3;">${n.message}</div>
                    <div class="text-muted mt-1 d-flex align-items-center gap-1" style="font-size:.68rem;">
                        <i class="bi bi-clock" style="font-size:.65rem;"></i>
                        ${dateObj.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}
                    </div>
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        // silently ignore — user may not be on a page that loads auth yet
    }
};

function startNotificationPolling() {
    if (window._notifPollStarted) return;
    window._notifPollStarted = true;

    // Run immediately
    window.refreshBell();
    // Then every 30 seconds
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
        lead: '<i class="bi bi-bullseye text-danger"></i>',
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

