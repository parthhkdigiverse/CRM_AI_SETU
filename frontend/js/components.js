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
        nav += `
        <div class="sb-section">
            <div class="sb-section-header ${active === 'dashboard' ? 'open' : ''}" onclick="toggleSbSection('db')">
                <i class="bi bi-grid-1x2 sb-sec-icon"></i><span>Dashboard</span>
                <i class="bi bi-chevron-${active === 'dashboard' ? 'down' : 'right'} sb-arrow"></i>
            </div>
            <ul class="sb-section-items ${active === 'dashboard' ? 'open' : ''}">
                <li><a href="dashboard.html" class="sb-link ${active === 'dashboard' ? 'active' : ''}">
                    <i class="bi bi-bar-chart-line-fill"></i><span>Overview</span></a></li>
                <li><a href="javascript:void(0)" onclick="if(window.loadView) window.loadView('timetable');" class="sb-link ${active === 'timetable' ? 'active' : ''}">
                    <i class="bi bi-calendar3"></i><span>Timetable</span></a></li>
            </ul>
        </div>`;
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
            { id: 'payment', href: 'javascript:void(0)', onclick: "if(window.loadView) window.loadView('billing');", icon: 'bi-file-earmark-medical', label: 'Payment' }
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

    return `
    <div id="sidebar-container">
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon"><i class="bi bi-grid-fill"></i></div>
            <span>CRM AI SETU</span>
        </div>
        <div class="sb-scroll-area">${nav}</div>
        <div class="sb-bottom">
            <a href="#" class="sb-bottom-link"><i class="bi bi-gear"></i> Settings</a>
            <a href="#" class="sb-bottom-link" onclick="logout();return false;"><i class="bi bi-box-arrow-right"></i> Logout</a>
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
        'Meetings': 'Project Management',
        'Issues': 'Project Management',
        'Clients': 'Client Relations',
        'Payment': 'Client Relations',
        'Feedback': 'Client Relations',
        'Employees': 'HR & Payroll',
        'Salary & Leaves': 'HR & Payroll',
        'Incentives': 'HR & Payroll',
        'Reports': 'Reports & Analytics',
        'Timetable': 'Dashboard',
        'Overview': 'Dashboard',
        'Profile': 'Dashboard',
        'Search Results': 'Search'
    };

    const parent = pageToParent[pageTitle];
    const breadcrumbHtml = parent ? `
        <div class="d-flex align-items-center gap-2">
            <span class="text-muted" style="font-size: 0.95rem;">${parent}</span>
            <i class="bi bi-chevron-right text-muted" style="font-size: 0.75rem;"></i>
            <div class="fw-bold fs-4 text-dark" style="text-transform: capitalize; letter-spacing: -0.5px; white-space: nowrap;">${pageTitle}</div>
        </div>
    ` : `
        <div class="fw-bold fs-4 text-dark" style="text-transform: capitalize; letter-spacing: -0.5px; white-space: nowrap;">${pageTitle}</div>
    `;

    const alertsRedDot = '<span class="position-absolute bg-danger border border-white rounded-circle" style="width:10px;height:10px;top:8px;right:8px;"></span>';

    const headerHtml = `
    <div class="top-header" style="padding: 0.75rem 1.5rem; background: #fff; border-bottom: 1px solid #f1f5f9; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; min-height: 70px;">
        <!-- Left: Breadcrumb Title -->
        <div class="d-flex align-items-center">
            ${breadcrumbHtml}
        </div>

        <!-- Center: Global Search -->
        <div class="d-flex justify-content-center" style="min-width: 300px; width: 40%;">
            <div class="position-relative w-100" style="max-width: 500px;">
                <button class="btn p-0 position-absolute text-muted" style="left:12px; top:50%; transform:translateY(-50%); border:none; background:none; z-index:5;" onclick="const val = document.getElementById('global-search-input').value.trim(); if(val) window.location.href = 'search.html?q=' + encodeURIComponent(val);">
                    <i class="bi bi-search" style="font-size:0.9rem;"></i>
                </button>
                <input type="text" id="global-search-input" class="form-control bg-light border-0 shadow-none" placeholder="Search everything..." style="padding-left: 40px; border-radius: 10px; font-size: 0.9rem; height: 42px;" onkeypress="if(event.key === 'Enter' && this.value.trim()) { window.location.href = 'search.html?q=' + encodeURIComponent(this.value.trim()); }">
            </div>
        </div>

        <!-- Right: Actions & Profile -->
        <div class="d-flex align-items-center justify-content-end gap-3">
            <div class="dropdown">
                <button class="btn btn-primary d-flex align-items-center gap-2 px-3 dropdown-toggle shadow-sm" type="button" id="addNewDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="font-size:0.875rem; border-radius: 8px; height: 40px;">
                    <i class="bi bi-plus-lg"></i> Add New
                </button>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="addNewDropdown" style="font-size: 0.875rem; border-radius:12px; padding:8px;">
                    <li><a class="dropdown-item py-2" href="leads.html?add=true" style="border-radius:8px;"><i class="bi bi-bullseye me-2 text-primary"></i> New Project</a></li>
                    <li><a class="dropdown-item py-2" href="areas.html?add=true" style="border-radius:8px;"><i class="bi bi-building me-2 text-primary" style="color: #6366f1 !important;"></i> New Area/Shop</a></li>
                    <li><a class="dropdown-item py-2" href="clients.html" style="border-radius:8px;"><i class="bi bi-people me-2 text-info"></i> New Client</a></li>
                    <li><a class="dropdown-item py-2" href="javascript:void(0)" onclick="if(window.openNewBillModal) window.openNewBillModal();" style="border-radius:8px;"><i class="bi bi-file-invoice-dollar me-2 text-danger"></i> New Payment</a></li>
                    <li><a class="dropdown-item py-2" href="issues.html" style="border-radius:8px;"><i class="bi bi-exclamation-triangle me-2 text-warning"></i> New Issue</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item py-2" href="admin.html" style="border-radius:8px;"><i class="bi bi-person-plus me-2 text-success"></i> New User</a></li>
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
                        <span class="badge bg-danger rounded-pill">Sys</span>
                    </div>
                    <div class="p-3 text-center">
                        <i class="bi bi-bell-slash text-muted" style="font-size: 2rem;"></i>
                        <p class="text-muted small mt-2 mb-0">No new system alerts right now.</p>
                    </div>
                    <div class="bg-light px-3 py-2 border-top text-center" style="cursor: pointer;" onclick="window.location.href='notifications.html'">
                        <a href="notifications.html" class="text-decoration-none small fw-semibold">View Master Feed</a>
                    </div>
                </div>
            </div>
            <div class="d-flex align-items-center gap-2 ps-2 dropdown border-start pl-3 ms-1">
                <div class="rounded-circle bg-primary-subtle text-primary d-flex align-items-center justify-content-center fw-bold dropdown-toggle shadow-sm" id="profileDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="width:38px;height:38px;font-size:13px;cursor:pointer;">${initials}</div>
                <div class="d-none d-lg-block">
                    <div class="fw-bold text-dark" style="font-size:0.85rem; line-height:1;">${u?.name || 'Admin'}</div>
                    <div class="text-muted small" style="font-size:0.70rem; line-height:1.5;">${role}</div>
                </div>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="profileDropdown" style="font-size: 0.875rem; border-radius:12px; padding:8px; z-index: 9999;">
                    <li><a class="dropdown-item py-2" href="javascript:void(0)" onclick="if(window.loadView) window.loadView('profile');" style="border-radius:8px;"><i class="bi bi-person me-2 text-primary"></i> My Profile</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item py-2" href="javascript:void(0)" onclick="logout()" style="border-radius:8px; color:var(--danger);"><i class="bi bi-box-arrow-right me-2"></i> Logout</a></li>
                </ul>
            </div>
        </div>
    </div>`;
    const rightSide = document.querySelector('.flex-grow-1');
    if (rightSide) {
        rightSide.classList.remove('p-4');
        rightSide.classList.add('d-flex', 'flex-column', 'bg-light');
        rightSide.style.minHeight = '100vh';
        rightSide.insertAdjacentHTML('afterbegin', headerHtml);
        const nodesToMove = [];
        for (const child of rightSide.childNodes) {
            if (child.nodeType === 1 && child.classList.contains('top-header')) continue;
            nodesToMove.push(child);
        }
        const contentContainer = document.createElement('div');
        contentContainer.className = 'page-content';
        contentContainer.style.flexGrow = '1';
        nodesToMove.forEach(node => contentContainer.appendChild(node));
        rightSide.appendChild(contentContainer);
    }
}
