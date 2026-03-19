// frontend/js/ui_components.js
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

window.getRoleFlags = function (roleValue) {
    const role = (roleValue || '').toUpperCase();
    return {
        role,
        isAdmin: role === 'ADMIN',
        isSales: role === 'SALES' || role === 'PROJECT_MANAGER_AND_SALES',
        isTelesales: role === 'TELESALES',
        isPM: role === 'PROJECT_MANAGER' || role === 'PROJECT_MANAGER_AND_SALES',
        isClient: role === 'CLIENT'
    };
}

window.getQuickAddItems = function (roleValue) {
    const flags = getRoleFlags(roleValue);
    const items = [];

    if (flags.isAdmin || flags.isSales || flags.isTelesales || flags.isPM) {
        items.push({ href: 'clients.html', icon: 'bi-people', iconClass: 'text-info', label: 'New Client' });
    }
    if (flags.isAdmin || flags.isPM) {
        items.push({ href: 'projects.html?add=true', icon: 'bi-briefcase', iconClass: 'text-primary', label: 'New Project' });
    }
    if (flags.isAdmin || flags.isSales) {
        items.push({ href: 'areas.html?add=true', icon: 'bi-building', iconClass: '', iconStyle: 'color:#6366f1;', label: 'New Area / Shop' });
    }
    if (flags.isAdmin || flags.isSales || flags.isTelesales) {
        items.push({ href: 'visits.html?add=true', icon: flags.isTelesales ? 'bi-telephone' : 'bi-geo-alt', iconClass: 'text-success', label: flags.isTelesales ? 'New Call Log' : 'New Visit' });
    }
    if (flags.isAdmin || flags.isPM) {
        items.push({ href: 'meetings.html?add=true', icon: 'bi-calendar-event', iconClass: 'text-success', label: 'New Meeting' });
    }
    if (!flags.isClient) {
        items.push({ href: 'todo.html', icon: 'bi-check2-square', iconClass: 'text-primary', label: 'New Task' });
    }
    if (flags.isAdmin || flags.isSales || flags.isTelesales || flags.isPM) {
        items.push({ href: 'javascript:void(0)', onclick: 'if(window.openNewBillModal) window.openNewBillModal();', icon: 'bi-receipt', iconClass: 'text-danger', label: 'New Payment' });
    }
    if (flags.isAdmin || flags.isPM) {
        items.push({ href: 'issues.html?add=true', icon: 'bi-exclamation-triangle', iconClass: 'text-warning', label: 'New Issue' });
        items.push({ href: 'feedback.html?add=true', icon: 'bi-chat-square-text', iconClass: 'text-info', label: 'New Feedback' });
    }
    if (!flags.isClient) {
        items.push({ href: 'leaves.html?add=true', icon: 'bi-calendar3', iconClass: 'text-warning', label: 'New Leave Request' });
    }
    if (flags.isAdmin) {
        items.push({ divider: true });
        items.push({ href: 'admin.html', icon: 'bi-person-plus', iconClass: 'text-secondary', label: 'New User' });
    }

    return items;
}

window.renderQuickAddItems = function (roleValue) {
    return getQuickAddItems(roleValue).map(item => {
        if (item.divider) {
            return '<li><hr class="dropdown-divider my-1"></li>';
        }
        const action = item.onclick
            ? `href="${item.href}" onclick="${item.onclick}"`
            : `href="${item.href}"`;
        return `<li><a class="dropdown-item" ${action}><i class="bi ${item.icon} ${item.iconClass || ''}"></i> ${item.label}</a></li>`;
    }).join('');
}

// ─── SIDEBAR ──────────────────────────────────────────────────────────
window.renderSidebar = function (active) {
    const u = getUser();
    const role = u?.role || 'TELESALES';
    const { isAdmin, isSales, isTelesales, isPM, isClient } = getRoleFlags(role);

    const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    if (isCollapsed) {
        setTimeout(() => {
            document.getElementById('sidebar-container')?.classList.add('collapsed');
        }, 0);
    }

    const roleName = String(role || '').toUpperCase();
    const fallbackPages = {
        ADMIN: ['*'],
        SALES: ['dashboard.html', 'timetable.html', 'todo.html', 'leads.html', 'visits.html', 'areas.html', 'clients.html', 'billing.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html', 'issues.html', 'incentives.html'],
        TELESALES: ['dashboard.html', 'timetable.html', 'todo.html', 'leads.html', 'visits.html', 'clients.html', 'billing.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html', 'issues.html', 'incentives.html'],
        PROJECT_MANAGER: ['dashboard.html', 'timetable.html', 'todo.html', 'projects.html', 'projects_demo.html', 'meetings.html', 'issues.html', 'clients.html', 'billing.html', 'feedback.html', 'reports.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html', 'incentives.html'],
        PROJECT_MANAGER_AND_SALES: ['dashboard.html', 'timetable.html', 'todo.html', 'leads.html', 'visits.html', 'areas.html', 'projects.html', 'projects_demo.html', 'meetings.html', 'issues.html', 'clients.html', 'billing.html', 'feedback.html', 'reports.html', 'leaves.html', 'salary.html', 'search.html', 'notifications.html', 'profile.html', 'settings.html', 'incentives.html'],
        CLIENT: ['dashboard.html']
    };
    const effectivePolicy = window.__crmEffectiveAccessPolicy;
    const allowedPages = Array.isArray(effectivePolicy?.allowed_pages)
        ? effectivePolicy.allowed_pages
        : (effectivePolicy?.policy?.page_access?.[roleName] || fallbackPages[roleName] || []);
    const allowAllPages = roleName === 'ADMIN' || allowedPages.includes('*');
    const canShowPage = (href) => {
        const page = String(href || '').split('?')[0];
        if (!page) return false;
        if (allowAllPages) return true;
        return allowedPages.includes(page);
    };

    const sbSection = (id, title, icon, items) => {
        const filteredItems = items.filter(item => canShowPage(item.href));
        if (filteredItems.length === 0) return '';
        const isAnyActive = filteredItems.some(item => item.id === active);
        const isOpen = isAnyActive; // Auto-open if active item is inside

        return `
        <div class="sb-section" id="sb-sec-${id}">
            <div class="sb-section-header ${isOpen ? 'open' : ''}" onclick="toggleSbSection('${id}')">
                <i class="bi ${icon} sb-sec-icon"></i>
                <span>${title}</span>
                <i class="bi bi-chevron-right sb-arrow"></i>
            </div>
            <div class="sb-section-items ${isOpen ? 'open' : ''}">
                ${filteredItems.map(item => `
                    <a href="${item.href}" class="sb-link ${item.id === active ? 'active' : ''}">
                        <i class="bi ${item.icon}"></i>
                        <span>${item.label}</span>
                    </a>
                `).join('')}
            </div>
        </div>`;
    };

    return `
    <div id="sidebar-container">
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">
                <div class="sidebar-logo-ai"></div>
            </div>
            <div class="ms-2 d-flex flex-column">
                <span>SRM AI SETU</span>
            </div>
        </div>

        <div class="sb-scroll-area">
            ${sbSection('db', 'Dashboard', 'bi-grid-1x2', [
                { id: 'dashboard', href: 'dashboard.html', icon: 'bi-bar-chart-line-fill', label: 'Overview' },
                { id: 'timetable', href: 'timetable.html', icon: 'bi-calendar3', label: 'Timetable' },
                { id: 'todo', href: 'todo.html', icon: 'bi-check2-square', label: 'To-Do List' }
            ])}

            ${sbSection('admin', 'Administration', 'bi-shield-check', [
                { id: 'admin', href: 'admin.html', icon: 'bi-people', label: 'Users & Roles' }
            ])}
            ${sbSection('fo', 'Field Operations', 'bi-geo-alt', [
                { id: 'projects', href: 'projects.html', icon: 'bi-kanban', label: 'Projects' },
                { id: 'visits', href: 'visits.html', icon: 'bi-geo-alt-fill', label: 'Visits' },
                { id: 'areas', href: 'areas.html', icon: 'bi-shop', label: 'Areas & Shops' }
            ])}
            ${sbSection('pm', 'Project Management', 'bi-briefcase', [
                { id: 'demo', href: 'projects_demo.html', icon: 'bi-play-circle', label: 'Demo' },
                { id: 'projects', href: 'projects.html', icon: 'bi-briefcase', label: 'Projects' },
                { id: 'meetings', href: 'meetings.html', icon: 'bi-calendar-event', label: 'Meetings' },
                { id: 'issues', href: 'issues.html', icon: 'bi-exclamation-triangle', label: 'Issues' }
            ])}
            ${sbSection('client', 'Client Relations', 'bi-person-badge', [
                { id: 'clients', href: 'clients.html', icon: 'bi-people', label: 'Clients' },
                { id: 'payment', href: 'billing.html', icon: 'bi-receipt', label: 'Billing & Invoices' },
                { id: 'feedback', href: 'feedback.html', icon: 'bi-chat-square-text', label: 'Feedback' }
            ])}
            ${sbSection('hr', 'HR & Payroll', 'bi-people-fill', [
                { id: 'employees', href: 'employees.html', icon: 'bi-people', label: 'Employees' },
                { id: 'salary', href: 'salary.html', icon: 'bi-cash-stack', label: 'Salary & Payroll' },
                { id: 'leaves', href: 'leaves.html', icon: 'bi-calendar-x', label: 'Leaves' },
                { id: 'incentives', href: 'incentives.html', icon: 'bi-award', label: 'Incentives' }
            ])}
            ${sbSection('rpt', 'Reports & Analytics', 'bi-graph-up', [
                { id: 'reports', href: 'reports.html', icon: 'bi-graph-up', label: 'Reports' }
            ])}
        </div>
        
        <div class="sb-bottom">
            <a href="settings.html" class="sb-bottom-link ${active === 'settings' ? 'active' : ''}" title="Settings">
                <i class="bi bi-gear"></i> <span>Settings</span>
            </a>
            <a href="#" class="sb-bottom-link logout" onclick="logout();return false;" title="Logout">
                <i class="bi bi-box-arrow-right"></i> <span class="d-none d-sm-inline">Logout</span>
            </a>
        </div>

        <!-- Floating Toggle Button -->
        <div class="sb-toggle-btn" onclick="toggleSidebarState()" title="Toggle Sidebar">
            <i class="bi bi-chevron-left"></i>
        </div>
    </div>
    <div id="sb-overlay" class="sidebar-overlay" onclick="toggleMobileSidebar()"></div>
    `;
}

window.toggleMobileSidebar = function() {
    const sb = document.getElementById('sidebar-container');
    const overlay = document.getElementById('sb-overlay');
    if (!sb) return;
    
    const isOpen = sb.classList.toggle('mobile-open');
    if (overlay) {
        overlay.style.opacity = isOpen ? '1' : '0';
        overlay.style.visibility = isOpen ? 'visible' : 'hidden';
    }
    
    // Lock body scroll when mobile sidebar is open
    document.body.style.overflow = isOpen ? 'hidden' : '';
};

window.toggleMobileSearch = function() {
    let mobileSearch = document.getElementById('mobile-search-overlay');
    
    if (!mobileSearch) {
        const html = `
            <div id="mobile-search-overlay" class="position-fixed top-0 start-0 w-100 bg-white shadow-sm d-flex align-items-center px-3" style="height: 68px; z-index: 2000; transform: translateY(-100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);">
                <i class="bi bi-search text-muted me-2"></i>
                <input type="text" id="mobile-search-input" class="form-control border-0 bg-transparent p-0 shadow-none" placeholder="Search..." onkeyup="if(event.key === 'Enter') { const val = this.value.trim(); if(val) window.location.href = 'search.html?q=' + encodeURIComponent(val); }">
                <button class="btn btn-link text-muted p-2" onclick="toggleMobileSearch()">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', html);
        mobileSearch = document.getElementById('mobile-search-overlay');
    }
    
    const isShowing = mobileSearch.style.transform === 'translateY(0%)';
    mobileSearch.style.transform = isShowing ? 'translateY(-100%)' : 'translateY(0%)';
    
    if (!isShowing) {
        setTimeout(() => document.getElementById('mobile-search-input').focus(), 300);
    }
};

window.toggleSidebarState = function() {
    const sb = document.getElementById('sidebar-container');
    if (!sb) return;
    const isCollapsed = sb.classList.toggle('collapsed');
    localStorage.setItem('sidebar-collapsed', isCollapsed);
    
    // Close all sections when collapsing
    if (isCollapsed) {
        document.querySelectorAll('.sb-section-items').forEach(el => el.classList.remove('open'));
        document.querySelectorAll('.sb-section-header').forEach(el => el.classList.remove('open'));
    }
};

window.toggleSbSection = function (id) {
    const sb = document.getElementById('sidebar-container');
    if (sb && sb.classList.contains('collapsed')) {
        sb.classList.remove('collapsed');
        localStorage.setItem('sidebar-collapsed', 'false');
    }

    const sec = document.getElementById(`sb-sec-${id}`);
    if (!sec) return;
    
    const hdr = sec.querySelector('.sb-section-header');
    const lst = sec.querySelector('.sb-section-items');
    
    const isOpen = lst.classList.toggle('open');
    hdr.classList.toggle('open', isOpen);
};

// ─── TOP HEADER ───────────────────────────────────────────────────────
window.injectTopHeader = function (pageTitle) {
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
    const chevronSvg = `<svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" style="opacity: 0.5;"><path d="M4.5 9L7.5 6L4.5 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    const breadcrumbHtml = parent ? `
        <div class="d-flex align-items-center gap-2" style="font-size: 15px;">
            <span style="color: var(--text-2);">${parent}</span>
            ${chevronSvg}
            <div class="fw-bold" style="color: var(--text-1);">${pageTitle}</div>
        </div>
    ` : `<div class="fw-bold" style="color: var(--text-1); font-size: 15px;">${pageTitle}</div>`;

    const alertsRedDot = '<span id="nav-notif-dot" class="position-absolute bg-danger border border-white rounded-circle d-none" style="width:8px;height:8px;top:8px;right:8px;"></span>';

    const quickAddItems = renderQuickAddItems(u?.role);

    const logoHtml = `
        <div class="nav-logo align-items-center gap-2 me-2 d-none" style="cursor: pointer;" onclick="window.location.href='dashboard.html'">
            <div class="sidebar-brand-icon" style="width: 32px; height: 32px; border-radius: 8px; background: var(--nav-search-bg);">
                <div class="sidebar-logo-ai"></div>
            </div>
            <span class="fw-bold" style="font-family: 'Outfit', sans-serif; font-size: 16px; letter-spacing: -0.02em; color: var(--nav-text-active);">SRM AI SETU</span>
        </div>`;

    const headerHtml = `
    <div class="top-header">
        <div class="top-header-left">
            <button class="btn btn-dark-soft d-lg-none me-1" onclick="toggleMobileSidebar()" style="width: 38px; height: 38px; padding: 0; display: flex; align-items: center; justify-content: center; background: rgba(37, 99, 235, 0.05); border: 1px solid rgba(37, 99, 235, 0.1); border-radius: 8px;">
                <i class="bi bi-list" style="font-size: 1.4rem; color: #2563eb;"></i>
            </button>
            ${logoHtml}
            <div class="nav-breadcrumb">
                <div class="d-none d-sm-block">${breadcrumbHtml}</div>
                <div class="d-block d-sm-none page-nav-title" style="color: var(--nav-text-active); font-weight: 600;">${pageTitle}</div>
            </div>
        </div>

        <div class="top-header-center">
            <div class="nav-search" style="max-width: 320px; width: 100%;">
                <div class="position-relative w-100">
                    <button class="btn p-0 position-absolute text-muted search-btn" style="left: 12px; top: 50%; transform: translateY(-50%); z-index: 10;" onclick="const val = document.getElementById('global-search-input').value.trim(); if(val) window.location.href = 'search.html?q=' + encodeURIComponent(val);">
                        <i class="bi bi-search" style="color: var(--nav-text-muted);"></i>
                    </button>
                    <input type="text" id="global-search-input" class="form-control" placeholder="Search..." style="padding-left: 38px; border-radius: 20px; height: 38px; background: rgba(37, 99, 235, 0.03); border: 1px solid rgba(37, 99, 235, 0.1); color: #1e40af; font-weight: 500;">
                    <div id="live-search-dropdown" class="search-results-dropdown"></div>
                </div>
            </div>
        </div>

        <div class="top-header-right d-flex align-items-center gap-2">
            <!-- Mobile Search Icon (only visible on tablet) -->
            <button class="btn d-md-none p-0 d-flex align-items-center justify-content-center hover-hit-target search-icon-btn" style="width:40px; height:40px; color: var(--nav-text);" onclick="toggleMobileSearch()">
                <i class="bi bi-search"></i>
            </button>

            <!-- Add New Gradient Button -->
            <div class="dropdown d-none d-sm-block nav-add">
                <button class="btn d-flex align-items-center gap-2 px-3 dropdown-toggle shadow-sm" type="button" id="addNewDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="font-size:13px; font-weight:700; border-radius: 10px; height: 40px; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #ffffff !important; border: 1px solid rgba(255,255,255,0.2); padding: 10px 18px; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);">
                    <i class="bi bi-plus-lg" style="color: #ffffff !important;"></i> <span style="color: #ffffff !important;">Add New</span>
                </button>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" aria-labelledby="addNewDropdown" style="font-size: 0.85rem; border-radius:12px; padding:8px; min-width:200px; background: var(--bg-surface); border: 1px solid var(--border) !important;">
                    ${quickAddItems}
                </ul>
            </div>

            <!-- Notifications Bell -->
            <div class="dropdown">
                <div class="position-relative d-flex align-items-center justify-content-center hover-hit-target" data-bs-toggle="dropdown" aria-expanded="false" style="cursor:pointer; width:40px; height:40px; border-radius: 50%; color: #2563eb; background: rgba(37, 99, 235, 0.05);">
                    <i class="bi bi-bell" style="font-size: 1.1rem;"></i>
                    ${alertsRedDot}
                </div>
                <div class="dropdown-menu dropdown-menu-end shadow-lg border-0 p-0" style="width: 300px; border-radius: 12px; overflow: hidden; z-index: 9999; background: var(--bg-surface); border: 1px solid var(--border) !important;">
                    <div class="px-3 py-2 border-bottom d-flex justify-content-between align-items-center" style="background: var(--bg-page); border-color: var(--border) !important;">
                        <span class="fw-bold small" style="color: var(--text-1);">Notifications</span>
                    </div>
                    <div id="bell-notif-list">
                        <div class="p-3 text-center">
                            <i class="bi bi-bell-slash text-muted" style="font-size: 1.5rem;"></i>
                            <p class="text-muted extra-small mt-2 mb-0">No new alerts.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Profile -->
            <div class="d-flex align-items-center gap-2 ps-2 dropdown border-start ms-1" style="border-color: var(--border) !important;">
                <div class="rounded-circle d-flex align-items-center justify-content-center fw-bold shadow-sm" style="width:36px; height:36px; font-size:11px; border: 1px solid var(--border); background: var(--primary-soft); color: var(--primary);">${initials}</div>
                <div class="d-flex align-items-center dropdown-toggle" id="profileDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="cursor:pointer;">
                    <div class="d-none d-xl-block fw-bold mb-0 nav-uname" style="font-size:13px; line-height:1; color: #2563eb;">${u?.name || 'User'}</div>
                </div>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0 p-2" aria-labelledby="profileDropdown" style="border-radius:12px; min-width:180px; font-size:0.85rem; background: var(--bg-surface); border: 1px solid var(--border) !important;">
                    <li class="px-2 pt-1 pb-2">
                        <div class="fw-bold" style="font-size:0.8rem; line-height:1.3; color: var(--text-1);">${u?.name || 'User'}</div>
                        <div style="font-size:0.7rem; color: #cbd5e1;">${u?.email || 'Admin'}</div>
                    </li>
                    <li><hr class="dropdown-divider my-1" style="border-color: var(--border);"></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="profile.html" style="color: var(--text-2);"><i class="bi bi-person me-2 text-primary"></i> Profile</a></li>
                    <li><a class="dropdown-item rounded-2 py-2" href="settings.html" style="color: var(--text-2);"><i class="bi bi-gear me-2 text-secondary"></i> Settings</a></li>
                    <li><hr class="dropdown-divider my-1" style="border-color: var(--border);"></li>
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

    // Inject overlay if not present
    if (!document.getElementById('sb-overlay')) {
        document.body.insertAdjacentHTML('beforeend', '<div id="sb-overlay" class="sidebar-overlay" onclick="toggleMobileSidebar()"></div>');
    }
}

window.getInitials = function (name) {
    if (!name) return '??';
    const parts = name.split(' ').filter(p => p.trim() !== '');
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

window.updateTopHeaderProfile = function (name, role) {
    const initials = window.getInitials(name || 'User');
    const u = getUser() || {};
    
    // Update initials bubble
    const profileBubble = document.getElementById('profileDropdown');
    if (profileBubble) profileBubble.textContent = initials;

    // Update name and role in the text display
    const labelContainer = profileBubble?.nextElementSibling;
    if (labelContainer) {
        const nameEl = labelContainer.querySelector('.fw-bold');
        if (nameEl) nameEl.textContent = name || 'Admin';
        const roleEl = labelContainer.querySelector('.text-muted');
        if (roleEl) roleEl.textContent = (role || u.role || 'User').replace(/_/g, ' ');
    }

    // Update dropdown header
    const dropdownMenu = profileBubble?.parentElement?.querySelector('.dropdown-menu');
    if (dropdownMenu) {
        const dropName = dropdownMenu.querySelector('.fw-bold');
        if (dropName) dropName.textContent = name || 'Admin';
        const dropEmailRole = dropdownMenu.querySelector('.text-muted');
        if (dropEmailRole) dropEmailRole.textContent = u.email || role || 'User';
    }
};



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
    if (!sessionStorage.getItem('access_token')) return;
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

window.showBrowserNotification = function (notifId, title, bodyStr, link) {
    if (window._shownPushes.has(notifId) || !('Notification' in window)) return;
    window._shownPushes.add(notifId);
    if (Notification.permission === 'granted') {
        const popup = new Notification(title, { body: bodyStr });
        popup.onclick = () => { link ? window.open(link, '_blank') : window.location.href = 'notifications.html'; popup.close(); };
    }
}

window.startNotificationPolling = function () {
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
    if (!sessionStorage.getItem('access_token')) return;
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
window.startAllPolling = function () {
    startNotificationPolling();
    // High priority check every 60s
    setInterval(window.checkHighPriorityIssues, 60000);
};

// ─── Dark Mode ────────────────────────────────────────────────
;(function applyInitialTheme() {
    let saved = localStorage.getItem('srm-theme');
    // Default to dark theme for consistency with redesign if no preference is set
    if (!saved) {
        saved = 'dark';
        localStorage.setItem('srm-theme', 'dark');
    }
    
    if (saved === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
})();

// ─── Header & Context ────────────────────────────────────────────────
window.updateHeaderContext = function () {
    const u = typeof getUser === 'function' ? getUser() : (window.ApiClient ? window.ApiClient.getCurrentUser() : null);
    if (!u) return;

    // 1. Update Top Navigation (initially set by injectTopHeader, but here for sync)
    const nameEls = document.querySelectorAll('.nav-uname');
    nameEls.forEach(el => el.textContent = u.name || u.username || 'User');

    // 2. Update Dashboard/Page Greetings
    const now = new Date();
    const hours = now.getHours();
    let greeting = "Good Morning";
    if (hours >= 12 && hours < 17) greeting = "Good Afternoon";
    else if (hours >= 17) greeting = "Good Evening";

    const dateStr = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

    // Handle multiple possible IDs used across different page versions
    const greetingIds = ['dash-greeting', 'dash-greeting-v2', 'greetingUser'];
    greetingIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = `${greeting}, ${u.name || 'User'}`;
    });

    const dateIds = ['dash-date', 'dash-date-v2', 'dash-date-header'];
    dateIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = dateStr;
    });

    // 3. Role-based Header Visibility
    // The user specifically requested that the "greeting header" (gradient) stays only on Overview.
    const isOverview = window.location.pathname.includes('dashboard.html');
    const dashHeaders = document.querySelectorAll('.dash-header');
    
    dashHeaders.forEach(header => {
        if (!isOverview) {
             // In other pages, we can hide it OR keep it but only for staff if it contains the widget
             // Here we just ensure the text is updated if it exists
        }
    });

    // Sync initials if found
    const avatarEls = document.querySelectorAll('.rounded-circle.fw-bold');
    avatarEls.forEach(el => {
        if (el.textContent.length <= 2 && typeof window.getInitials === 'function') {
            el.textContent = window.getInitials(u.name || u.email || 'AD');
        }
    });
};

// ─── Attendance Widget ───────────────────────────────────────────────
window.initAttendance = async function () {
    const widget = document.getElementById('employee-header-widget');
    if (!widget) return Promise.resolve();

    widget.classList.remove('d-none');

    const u = window.ApiClient ? window.ApiClient.getCurrentUser() : null;
    if (!u) return Promise.resolve();

    // 1. Populate Left Zone: Date + Greeting
    const now = new Date();
    const hrs = now.getHours();
    let greeting = 'Good Morning';
    if (hrs >= 12 && hrs < 17) greeting = 'Good Afternoon';
    else if (hrs >= 17) greeting = 'Good Evening';

    const dateStr = now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).toUpperCase();
    const firstName = (u.name || 'User').split(' ')[0];

    const dateEl        = document.getElementById('att-v2-date');
    const greetLineEl   = document.getElementById('att-v2-greeting-line');
    const leftNameEl    = document.getElementById('att-v2-left-name');
    if (dateEl)      dateEl.textContent = dateStr;
    if (greetLineEl) greetLineEl.textContent = greeting + ',';
    if (leftNameEl)  leftNameEl.textContent = firstName;

    // 2. Populate Right Zone: Avatar + Name
    const nameEl   = document.getElementById('att-v2-name');
    const avatarEl = document.getElementById('att-v2-avatar');
    if (nameEl) nameEl.textContent = u.name || 'User';
    if (avatarEl && typeof window.getInitials === 'function') {
        const initials = window.getInitials(u.name || u.email || 'U');
        if (u.photo_url) {
            avatarEl.innerHTML = `<img src="${u.photo_url}" alt="${initials}" onerror="this.parentElement.innerHTML='${initials}'">`;
        } else {
            avatarEl.textContent = initials;
        }
    }

    let status = null;
    try {
        status = await window.ApiClient.getPunchStatus();
    } catch (e) {
        console.error('Failed to get punch status', e);
        return Promise.resolve();
    }

    const updateUI = (s) => {
        const badge      = document.getElementById('att-v2-badge');
        const btn        = document.getElementById('header-punch-btn-new');
        const hh         = document.getElementById('att-v2-hh');
        const mm         = document.getElementById('att-v2-mm');
        const ss         = document.getElementById('att-v2-ss');
        const firstIn    = document.getElementById('att-v2-first-in');
        const liveBadge  = document.getElementById('att-v2-live-badge');
        const livePulse  = document.getElementById('att-v2-pulse');
        const liveText   = document.getElementById('att-v2-live-text');
        const statusDot  = document.getElementById('att-v2-status-dot');
        const lNameEl    = document.getElementById('att-v2-left-name');

        if (s.is_punched_in) {
            if (badge)     { badge.textContent = 'Punched In'; badge.className = 'pro-att-punch-badge in'; }
            if (btn)       { btn.innerHTML = 'Punch<br>Out'; btn.className = 'pro-att-btn punch-out'; }
            if (liveBadge) liveBadge.className = 'pro-att-live-badge live';
            if (livePulse) livePulse.style.display = '';
            if (liveText)  liveText.textContent = 'Live';
            if (statusDot) statusDot.className = 'pro-att-status-dot online';
            if (lNameEl)   lNameEl.className = 'pro-att-name punched-in';
        } else {
            if (badge)     { badge.textContent = 'Not Punched'; badge.className = 'pro-att-punch-badge out'; }
            if (btn)       { btn.innerHTML = 'Punch<br>In'; btn.className = 'pro-att-btn punch-in'; }
            if (liveBadge) liveBadge.className = 'pro-att-live-badge offline';
            if (livePulse) livePulse.style.display = 'none';
            if (liveText)  liveText.textContent = 'Offline';
            if (statusDot) statusDot.className = 'pro-att-status-dot offline';
            if (lNameEl)   lNameEl.className = 'pro-att-name punched-out';
        }

        // Punch-in time
        if (firstIn) {
            if (s.first_punch_in) {
                const d = new Date(s.first_punch_in);
                firstIn.textContent = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
            } else {
                firstIn.textContent = '--:--';
            }
        }

        // Timer Logic: Fixed
        if (window._attTimer) clearInterval(window._attTimer);
        
        const tick = () => {
            let totalSec = s.today_hours_secs || 0;
            if (s.is_punched_in && s.last_punch_ts) {
                const elapsed = Math.max(0, (Date.now() - s.last_punch_ts) / 1000);
                totalSec += elapsed;
            }

            const h = Math.floor(totalSec / 3600);
            const m = Math.floor((totalSec % 3600) / 60);
            const sec = Math.floor(totalSec % 60);
            
            if (hh) hh.textContent = h.toString().padStart(2, '0');
            if (mm) mm.textContent = m.toString().padStart(2, '0');
            if (ss) ss.textContent = sec.toString().padStart(2, '0');
        };

        if (s.is_punched_in || (s.today_hours_secs > 0)) {
            tick();
            if (s.is_punched_in) {
                window._attTimer = setInterval(tick, 1000);
            }
        } else {
            if (hh) hh.textContent = '--';
            if (mm) mm.textContent = '--';
            if (ss) ss.textContent = '--';
        }
    };

    updateUI(status);
    
    // 3. Punch Button Action
    const punchBtn = document.getElementById('header-punch-btn-new');
    if (punchBtn) {
        punchBtn.onclick = async () => {
            if (punchBtn.classList.contains('loading')) return;
            punchBtn.classList.add('loading');
            const origHTML = punchBtn.innerHTML;
            punchBtn.textContent = '...';
            try {
                const res = await window.ApiClient.punch();
                const newStatus = await window.ApiClient.getPunchStatus();
                updateUI(newStatus);
                if (typeof window.showToast === 'function') {
                    window.showToast(res.message || 'Action successful');
                }
                if (typeof window.refreshDashboardKPIs === 'function') {
                    window.refreshDashboardKPIs();
                }
            } catch (e) {
                console.error('Punch failed', e);
                if (typeof window.showToast === 'function') {
                    window.showToast(e.data?.detail || 'Punch failed', 'error');
                }
                punchBtn.innerHTML = origHTML;
            } finally {
                punchBtn.classList.remove('loading');
            }
        };
    }

    return Promise.resolve();
};



window.setTheme = function (mode) {
    let applyDark = false;
    if (mode === 'dark') {
        applyDark = true;
    } else if (mode === 'system') {
        applyDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    if (applyDark) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('srm-theme', 'dark');
    } else {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('srm-theme', 'light');
    }

    const icon = document.getElementById('dark-mode-icon');
    if (icon) {
        icon.className = applyDark ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }
};

window.toggleDarkMode = function () {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const newMode = isDark ? 'light' : 'dark';
    window.setTheme(newMode);
    
    const themeSelect = document.getElementById('theme-select');
    if (themeSelect) {
        themeSelect.value = newMode;
        if (typeof saveSetting === 'function') {
            saveSetting('theme', newMode);
        }
    } else {
        localStorage.setItem('srm_setting_theme', newMode);
    }
};

// Sync icon with current mode on load (after header injection)
document.addEventListener('DOMContentLoaded', function () {
    const icon = document.getElementById('dark-mode-icon');
    if (icon) {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        icon.className = isDark ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }
});
