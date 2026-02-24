document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const loginView = document.getElementById('login-view');
    const appShell = document.getElementById('app-shell');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const logoutBtn = document.getElementById('logout-btn');
    const mainContent = document.getElementById('main-content');
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    const topbarTitle = document.getElementById('topbar-title');

    // Auth Guard
    function checkAuth() {
        const token = window.ApiClient.getAccessToken();
        if (token) {
            showApp();
            loadView('dashboard');
        } else {
            showLogin();
        }
    }

    function showLogin() {
        loginView.classList.remove('hidden');
        appShell.classList.add('hidden');
    }

    function showApp() {
        loginView.classList.add('hidden');
        appShell.classList.remove('hidden');
    }

    // Login Form
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        const submitBtn = loginForm.querySelector('button');

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Authenticating...';
        loginError.classList.add('hidden');

        try {
            await window.ApiClient.login(email, password);
            showApp();
            loadView('dashboard');
        } catch (error) {
            loginError.classList.remove('hidden');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<span>Sign In</span><i class="fa-solid fa-arrow-right"></i>';
        }
    });

    // Logout
    logoutBtn.addEventListener('click', () => {
        window.ApiClient.clearTokens();
        showLogin();
    });

    window.addEventListener('auth-failed', () => {
        window.ApiClient.clearTokens();
        showLogin();
    });

    // Sidebar Navigation - Accordion Logic
    const toggleSections = document.querySelectorAll('.toggle-section');
    toggleSections.forEach(section => {
        section.addEventListener('click', () => {
            const subItems = section.nextElementSibling;
            const arrow = section.querySelector('.section-arrow');

            if (subItems && subItems.classList.contains('nav-sub-items')) {
                const isHidden = subItems.classList.contains('hidden');

                // Close all other accordions
                document.querySelectorAll('.nav-sub-items').forEach(el => el.classList.add('hidden'));
                document.querySelectorAll('.section-arrow').forEach(arr => {
                    arr.classList.remove('fa-chevron-down');
                    arr.classList.add('fa-chevron-right');
                });

                // Open clicked accordion if it was closed
                if (isHidden) {
                    subItems.classList.remove('hidden');
                    if (arrow) {
                        arrow.classList.remove('fa-chevron-right');
                        arrow.classList.add('fa-chevron-down');
                    }
                }
            }
        });
    });

    // Sidebar Navigation - View Routing
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const viewName = e.currentTarget.getAttribute('data-view');
            if (viewName) {
                navItems.forEach(nav => nav.classList.remove('active'));
                e.currentTarget.classList.add('active');

                const sectionOuter = e.currentTarget.closest('.sidebar-section');
                const emojiSpan = sectionOuter ? sectionOuter.querySelector('.nav-icon') : null;
                const emojiHTML = emojiSpan ? emojiSpan.outerHTML : '';
                const text = e.currentTarget.innerText.trim();

                const topbarBreadcrumb = document.getElementById('topbar-breadcrumb');
                if (topbarBreadcrumb) {
                    topbarBreadcrumb.innerHTML = `${emojiHTML} <span style="margin-left:8px;">${text}</span>`;
                }

                loadView(viewName);
            }
        });
    });

    // View Routing
    async function loadView(viewName) {
        mainContent.innerHTML = '<div style="display:flex; justify-content:center; padding: 40px; color: var(--primary); font-size: 24px;"><i class="fa-solid fa-circle-notch fa-spin"></i></div>';

        try {
            if (viewName === 'dashboard') {
                await renderDashboard();
            } else if (viewName === 'clients') {
                await renderClients();
            } else if (viewName === 'leads') {
                await renderLeads();
            } else if (viewName === 'areas') {
                await renderAreas();
            } else if (viewName === 'visits') {
                await renderVisits();
            } else if (viewName === 'feedback') {
                await renderFeedback();
            } else if (viewName === 'projects') {
                await renderProjects();
            } else if (viewName === 'meetings') {
                await renderMeetings();
            } else if (viewName === 'issues') {
                await renderIssues();
            } else if (viewName === 'hrm' || viewName === 'employees' || viewName === 'salary' || viewName === 'incentives') {
                await renderHRM();
            } else if (viewName === 'admin') {
                await renderAdmin();
            } else {
                mainContent.innerHTML = `
                    <div class="card" style="text-align:center; padding: 60px;">
                        <i class="fa-solid fa-person-digging" style="font-size: 48px; color: var(--text-muted); margin-bottom: 16px;"></i>
                        <h2>${viewName.charAt(0).toUpperCase() + viewName.slice(1)} View is Under Construction</h2>
                        <p class="text-muted">Will be built out shortly.</p>
                    </div>
                `;
            }
        } catch (e) {
            mainContent.innerHTML = `<div class="card text-danger"><i class="fa-solid fa-triangle-exclamation"></i> Error loading view. Please verify backend connection.</div>`;
        }
    }
    window.loadView = loadView; // Expose globally for onclick= handlers in dynamically rendered HTML

    async function renderDashboard() {
        let stats = { total_clients: 0, open_issues: 0, total_projects: 0, new_leads: 0 };
        try {
            const res = await window.ApiClient.getDashboardStats();
            // Optional chaining and fallbacks mapping real backend keys to UI keys if they differ
            stats.total_clients = res.total_clients || 0;
            stats.open_issues = res.open_issues_count || res.open_issues || 0; // Accommodate backend naming variations
            stats.total_projects = res.total_projects || stats.total_clients; // If projects removed, map to clients
            stats.new_leads = res.total_visits || res.new_leads || 0;
        } catch (e) {
            console.warn("Failed to fetch dashboard stats", e);
        }

        const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

        mainContent.innerHTML = `
        <!-- Row 1: Greeting -->
        <div class="page-header" style="margin-bottom: 24px;">
            <div>
                <h1 style="margin-bottom: 8px;">Dashboard</h1>
                <p class="text-muted">Welcome back! Here's what's happening today.</p>
            </div>
        </div>
        
        <!-- Row 2: KPI Grid of 4 (Lovable Style) -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 24px; margin-bottom: 24px;">
            <div class="stat-card">
                <div class="stat-content-left">
                    <div class="stat-title">Total Leads</div>
                    <div class="stat-value">1,284</div>
                    <div class="stat-trend trend-up"><i class="fa-solid fa-arrow-trend-up"></i> +12.5% <span>vs last month</span></div>
                </div>
                <div class="stat-icon-wrapper icon-purple">
                    <i class="fa-solid fa-bullseye"></i>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-content-left">
                    <div class="stat-title">Active Clients</div>
                    <div class="stat-value">342</div>
                    <div class="stat-trend trend-up"><i class="fa-solid fa-arrow-trend-up"></i> +4.2% <span>vs last month</span></div>
                </div>
                <div class="stat-icon-wrapper icon-teal">
                    <i class="fa-solid fa-users"></i>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-content-left">
                    <div class="stat-title">Ongoing Projects</div>
                    <div class="stat-value">28</div>
                    <div class="stat-trend trend-down"><i class="fa-solid fa-arrow-trend-down"></i> -2.1% <span>vs last month</span></div>
                </div>
                <div class="stat-icon-wrapper icon-yellow">
                    <i class="fa-solid fa-briefcase"></i>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-content-left">
                    <div class="stat-title">Revenue (MTD)</div>
                    <div class="stat-value">₹24.5L</div>
                    <div class="stat-trend trend-up"><i class="fa-solid fa-arrow-trend-up"></i> +18.7% <span>vs last month</span></div>
                </div>
                <div class="stat-icon-wrapper icon-green">
                    <i class="fa-solid fa-dollar-sign"></i>
                </div>
            </div>
        </div>
        
        <!-- Row 3: Charts (3 columns) -->
        <div style="display: grid; grid-template-columns: repeat(3, minmax(300px, 1fr)); gap: 24px; margin-bottom: 24px;">
            <div class="card">
                <h2 style="margin-bottom: 24px; font-size: 16px;">Leads by Month</h2>
                <div style="position: relative; height: 250px; width: 100%;">
                    <canvas id="leadsMonthChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 24px; font-size: 16px;">Revenue Trend</h2>
                <div style="position: relative; height: 250px; width: 100%;">
                    <canvas id="revenueTrendChart"></canvas>
                </div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 24px; font-size: 16px;">Lead Sources</h2>
                <div style="position: relative; height: 250px; width: 100%; display: flex; justify-content: center;">
                    <canvas id="leadSourcesChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Row 4: Action Lists -->
        <div class="dashboard-lists-grid">
            <!-- Recent Activity -->
            <div class="card">
                <div class="panel-title" style="display:flex;justify-content:space-between;align-items:center;">Recent Activity <button onclick="loadView('visits')" class="btn btn-ghost" style="font-size:12px;padding:4px 8px;">View All</button></div>
                <div class="activity-list">
                    <div class="activity-item">
                        <div class="activity-icon-circle icon-circle-purple">
                            <i class="fa-solid fa-bullseye"></i>
                        </div>
                        <div class="activity-text-wrapper">
                            <div class="activity-primary-text">New lead added</div>
                            <div class="activity-secondary-text">Rajesh Kumar — Website Inquiry</div>
                        </div>
                        <div class="activity-time">
                            <i class="fa-regular fa-clock"></i> 2 min ago
                        </div>
                    </div>
                    <div class="activity-item">
                        <div class="activity-icon-circle icon-circle-purple">
                            <i class="fa-regular fa-calendar-check"></i>
                        </div>
                        <div class="activity-text-wrapper">
                            <div class="activity-primary-text">Meeting scheduled</div>
                            <div class="activity-secondary-text">Infosys — Project Review</div>
                        </div>
                        <div class="activity-time">
                            <i class="fa-regular fa-clock"></i> 15 min ago
                        </div>
                    </div>
                    <div class="activity-item">
                        <div class="activity-icon-circle icon-circle-purple">
                            <i class="fa-solid fa-triangle-exclamation"></i>
                        </div>
                        <div class="activity-text-wrapper">
                            <div class="activity-primary-text">Issue escalated</div>
                            <div class="activity-secondary-text">TCS Portal — High Severity</div>
                        </div>
                        <div class="activity-time">
                            <i class="fa-regular fa-clock"></i> 1 hr ago
                        </div>
                    </div>
                    <div class="activity-item">
                        <div class="activity-icon-circle icon-circle-purple">
                            <i class="fa-solid fa-user-check"></i>
                        </div>
                        <div class="activity-text-wrapper">
                            <div class="activity-primary-text">Client converted</div>
                            <div class="activity-secondary-text">Wipro Technologies</div>
                        </div>
                        <div class="activity-time">
                            <i class="fa-regular fa-clock"></i> 3 hrs ago
                        </div>
                    </div>
                    <div class="activity-item">
                        <div class="activity-icon-circle icon-circle-purple">
                            <i class="fa-solid fa-indian-rupee-sign"></i>
                        </div>
                        <div class="activity-text-wrapper">
                            <div class="activity-primary-text">Payment received</div>
                            <div class="activity-secondary-text">₹2.5L — HCL Project</div>
                        </div>
                        <div class="activity-time">
                            <i class="fa-regular fa-clock"></i> 5 hrs ago
                        </div>
                    </div>
                </div>
            </div>

            <!-- Pending Tasks -->
            <div class="card">
                <div class="panel-title" style="display:flex;justify-content:space-between;align-items:center;">Pending Tasks <button onclick="loadView('issues')" class="btn btn-ghost" style="font-size:12px;padding:4px 8px;">View All</button></div>
                <div class="task-list">
                    <div class="task-item">
                        <div class="task-dot dot-red"></div>
                        <div class="task-text">Follow up with Mahindra lead</div>
                        <div class="task-badge badge-red-light">Today</div>
                    </div>
                    <div class="task-item">
                        <div class="task-dot dot-yellow"></div>
                        <div class="task-text">Submit project milestone report</div>
                        <div class="task-badge badge-purple-light">Tomorrow</div>
                    </div>
                    <div class="task-item">
                        <div class="task-dot dot-green"></div>
                        <div class="task-text">Review salary slips for March</div>
                        <div class="task-badge badge-purple-light">In 2 days</div>
                    </div>
                    <div class="task-item">
                        <div class="task-dot dot-yellow"></div>
                        <div class="task-text">Schedule client feedback call</div>
                        <div class="task-badge badge-purple-light">In 3 days</div>
                    </div>
                </div>
            </div>
        </div>
    `;

        // Initialize Charts (Delaying 100ms to allow DOM injection to finish)
        setTimeout(() => {
            initCharts();
        }, 100);
    }

    function initCharts() {
        if (!window.Chart) return;

        // Common Grid Options for the light dashed lines in the screenshot
        const gridOptions = {
            color: '#E5E7EB',
            borderDash: [5, 5],
            drawBorder: false
        };

        // 1. Leads by Month (Bar Chart, Purple)
        const ctxLeadsMonth = document.getElementById('leadsMonthChart');
        if (ctxLeadsMonth) {
            new Chart(ctxLeadsMonth, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Leads',
                        data: [65, 70, 95, 100, 135, 125],
                        backgroundColor: '#6366f1',
                        borderRadius: 4,
                        barPercentage: 0.7
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 140,
                            ticks: { stepSize: 35, color: '#9CA3AF' },
                            grid: gridOptions,
                            border: { display: false }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#9CA3AF' },
                            border: { display: false }
                        }
                    }
                }
            });
        }

        // 2. Revenue Trend (Line Chart, Teal)
        const ctxRev = document.getElementById('revenueTrendChart');
        if (ctxRev) {
            new Chart(ctxRev, {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Revenue',
                        data: [180, 220, 190, 310, 280, 360],
                        borderColor: '#14b8a6',
                        backgroundColor: '#14b8a6',
                        pointBackgroundColor: '#14b8a6',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        tension: 0.4, // Smooth curvy line
                        borderWidth: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 360,
                            ticks: {
                                stepSize: 90,
                                callback: function (value) { return '₹' + value + 'K'; },
                                color: '#9CA3AF'
                            },
                            grid: gridOptions,
                            border: { display: false }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#9CA3AF' },
                            border: { display: false }
                        }
                    }
                }
            });
        }

        // 3. Lead Sources (Doughnut Chart)
        const ctxSources = document.getElementById('leadSourcesChart');
        if (ctxSources) {
            new Chart(ctxSources, {
                type: 'doughnut',
                data: {
                    labels: ['Website', 'Referral', 'Cold Call', 'Social', 'Other'],
                    datasets: [{
                        data: [40, 25, 20, 10, 5],
                        backgroundColor: ['#6366f1', '#14b8a6', '#f59e0b', '#10B981', '#9CA3AF'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '75%', // Make it thin like the screenshot
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                boxWidth: 8,
                                padding: 20,
                                color: '#6B7280'
                            }
                        }
                    }
                }
            });
        }
    }

    async function renderClients() {
        try {
            const clients = await window.ApiClient.getClients();

            let html = `
            <div class="page-header">
                    <div>
                        <h1 style="margin-bottom: 4px;">Clients</h1>
                        <p class="text-muted">Manage your onboarded customers and accounts.</p>
                    </div>
                    <button class="btn btn-primary"><i class="fa-solid fa-plus"></i> New Client</button>
                </div>

            <div class="card" style="padding: 0;">
                <div class="table-container">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Client Name</th>
                                <th>Contact</th>
                                <th>Organization</th>
                                <th>Assigned PM</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            `;

            if (clients.length === 0) {
                html += `<tr><td colspan="5" style="text-align:center; padding: 40px; color: var(--text-muted);">No clients found.</td></tr>`;
            } else {
                clients.forEach(c => {
                    html += `
                        <tr>
                            <td>
                                <div style="font-weight: 500;">${c.name}</div>
                                <div style="font-size: 12px; color: var(--text-muted);">${c.email}</div>
                            </td>
                            <td>${c.phone || '-'}</td>
                            <td>${c.organization || '-'}</td>
                            <td>
                                ${c.pm_id ? `<span class="badge badge-primary">PM #${c.pm_id}</span>` : `<span class="badge badge-warning">Unassigned</span>`}
                            </td>
                            <td>
                                <button class="btn btn-ghost" style="padding: 4px 8px;"><i class="fa-solid fa-eye text-primary"></i></button>
                            </td>
                        </tr>
                    `;
                });
            }

            html += `</tbody></table></div></div>`;
            mainContent.innerHTML = html;

        } catch (e) {
            throw e;
        }
    }

    async function renderLeads() {
        let shops = [];
        try { shops = await window.ApiClient.getShops(); } catch (e) { console.warn('Shops/Leads fetch failed', e); }

        // Group shops by their status (interested / not_interested / pending / converted)
        const columns = [
            { key: 'pending', label: 'New', color: 'badge-purple-light', border: '' },
            { key: 'contacted', label: 'Contacted', color: 'badge-purple-light', border: '' },
            { key: 'interested', label: 'Meeting Set', color: 'badge-purple-light', border: '3px solid var(--warning)' },
            { key: 'client', label: 'Converted', color: 'badge-green-light', border: '3px solid var(--success)' },
        ];
        const grouped = {};
        columns.forEach(c => { grouped[c.key] = []; });
        shops.forEach(s => {
            const st = s.status || 'pending';
            if (!grouped[st]) grouped[st] = [];
            grouped[st].push(s);
        });

        const makeCard = (s, border) => {
            const initials = (s.owner_name || s.name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
            return `<div class="card kanban-card" style="margin-bottom:12px;padding:16px;cursor:pointer;${border ? 'border-left:' + border + ';' : ''}">
                <div style="font-weight:600;margin-bottom:4px;">${s.name || 'Unnamed'}</div>
                <div class="text-muted" style="font-size:13px;margin-bottom:8px;"><i class="fa-regular fa-building"></i> ${s.owner_name || '—'}</div>
                <div class="text-muted" style="font-size:13px;margin-bottom:12px;"><i class="fa-solid fa-phone"></i> ${s.phone || '—'}</div>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span class="badge badge-purple-light" style="font-size:11px;">${s.area_name || s.area_id || 'Area'}</span>
                    <div style="width:24px;height:24px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-size:10px;" title="${s.owner_name || ''}">'
                        ${initials}
                    </div>
                </div>
            </div>`;
        };

        const kbCols = columns.map(col => `
            <div class="kanban-column" style="flex:1;min-width:280px;background:#F9FAFB;border-radius:12px;padding:16px;">
                <h3 style="margin-bottom:16px;display:flex;justify-content:space-between;">${col.label} <span class="badge ${col.color}">${grouped[col.key].length}</span></h3>
                ${grouped[col.key].length
                ? grouped[col.key].map(s => makeCard(s, col.border)).join('')
                : `<div class="text-muted" style="font-size:13px;text-align:center;padding:24px 0;">No shops here</div>`
            }
            </div>`).join('');

        mainContent.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <div><h1 style="margin-bottom:4px;">Leads</h1><p class="text-muted">${shops.length} shops in pipeline.</p></div>
            <button class="btn btn-primary"><i class="fa-solid fa-plus"></i> Add Shop</button>
        </div>
        <div class="kanban-board" style="display:flex;gap:24px;overflow-x:auto;padding-bottom:16px;min-height:500px;">${kbCols}</div>`;
    }

    async function renderAreas() {
        let areas = [], shops = [], selectedAreaId = null;
        try { areas = await window.ApiClient.getAreas(); } catch (e) { console.warn('Areas fetch failed', e); }
        try { shops = await window.ApiClient.getShops(); } catch (e) { console.warn('Shops fetch failed', e); }

        if (areas.length) selectedAreaId = areas[0].id;
        const filteredShops = selectedAreaId ? shops.filter(s => s.area_id === selectedAreaId) : shops;
        const activeArea = areas.find(a => a.id === selectedAreaId);

        const areaItems = areas.length
            ? areas.map(a => {
                const count = shops.filter(s => s.area_id === a.id).length;
                const isActive = a.id === selectedAreaId;
                return `<div class="area-item" data-area-id="${a.id}" style="padding:12px 16px;border-left:3px solid ${isActive ? 'var(--primary)' : 'transparent'};background:${isActive ? 'var(--primary-light)' : 'transparent'};cursor:pointer;transition:background 0.2s;">
                    <div style="font-weight:${isActive ? '600' : '500'};color:${isActive ? 'var(--primary)' : 'inherit'}">${a.name}</div>
                    <div style="font-size:13px;color:var(--text-muted);margin-top:4px;"><i class="fa-solid fa-store"></i> ${count} shops</div>
                </div>`;
            }).join('')
            : `<div class="text-muted" style="padding:24px;text-align:center;">No areas found.</div>`;

        const shopRows = filteredShops.length
            ? filteredShops.map(s => `
                <tr>
                    <td><div style="font-weight:500;">${s.name}</div><div style="font-size:12px;color:var(--text-muted);">${s.address || '\u2014'}</div></td>
                    <td>${s.owner_name || '\u2014'}</td>
                    <td>${s.phone || '\u2014'}</td>
                    <td><span class="badge badge-purple-light">${s.status || 'active'}</span></td>
                    <td><button class="btn btn-ghost" style="padding:4px;"><i class="fa-solid fa-ellipsis-vertical"></i></button></td>
                </tr>`).join('')
            : `<tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted);">No shops in this area.</td></tr>`;

        mainContent.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <div><h1 style="margin-bottom:4px;">Areas &amp; Shops</h1><p class="text-muted">Geographical tracking for field sales.</p></div>
            <div style="display:flex;gap:12px;">
                <button class="btn btn-secondary"><i class="fa-solid fa-location-dot"></i> New Area</button>
                <button class="btn btn-primary"><i class="fa-solid fa-store"></i> New Shop</button>
            </div>
        </div>
        <div style="display:flex;gap:24px;align-items:flex-start;">
            <div class="card" style="width:280px;flex-shrink:0;padding:0;">
                <div style="padding:16px;border-bottom:1px solid var(--border);"><input type="text" class="form-control" placeholder="Search areas..." id="area-search"></div>
                <div id="area-list" style="padding:8px 0;">${areaItems}</div>
            </div>
            <div class="card" style="flex:1;padding:0;">
                <div style="padding:20px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
                    <h3 style="margin:0;">Shops in ${activeArea ? activeArea.name : 'All Areas'}</h3>
                    <span class="badge badge-purple-light">${filteredShops.length} Total</span>
                </div>
                <div class="table-container"><table class="table">
                    <thead><tr><th>SHOP NAME</th><th>OWNER</th><th>PHONE</th><th>STATUS</th><th></th></tr></thead>
                    <tbody>${shopRows}</tbody>
                </table></div>
            </div>
        </div>`;

        document.querySelectorAll('.area-item').forEach(el => {
            el.addEventListener('click', () => {
                selectedAreaId = parseInt(el.dataset.areaId);
                renderAreas();
            });
        });
    }

    async function renderVisits() {
        let visits = [];
        try { visits = await window.ApiClient.getVisits(); } catch (e) { console.warn('Visits fetch failed', e); }

        const today = new Date().toISOString().slice(0, 10);
        const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10);
        const todayCount = visits.filter(v => (v.visit_date || '').slice(0, 10) === today).length;
        const weekCount = visits.filter(v => v.status === 'completed' && (v.visit_date || '') >= weekAgo).length;
        const missedCount = visits.filter(v => v.status === 'missed').length;

        const statusBadge = s => ({
            completed: '<span class="badge badge-green-light">Completed</span>',
            scheduled: '<span class="badge badge-purple-light">Scheduled</span>',
            missed: '<span class="badge badge-red-light">Missed</span>'
        }[s] || `<span class="badge">${s || '—'}</span>`);

        const rows = visits.length ? visits.map(v => `
            <tr>
                <td style="font-weight:500;">${v.shop_name || v.shop_id || '—'}</td>
                <td>${v.area_name || '—'}</td>
                <td>${v.agent_name || v.agent_id || '—'}</td>
                <td>${v.visit_date ? new Date(v.visit_date).toLocaleDateString() : '—'}</td>
                <td>${v.visit_time || '—'}</td>
                <td>${statusBadge(v.status)}</td>
                <td class="text-muted" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${v.notes || '—'}</td>
            </tr>`).join('') :
            `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);">No visits recorded yet.</td></tr>`;

        mainContent.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <div><h1 style="margin-bottom:4px;">Visits</h1><p class="text-muted">Track field visit schedules and outcomes.</p></div>
            <button class="btn btn-primary" onclick="openLogVisitModal()"><i class="fa-solid fa-location-dot"></i> Log Visit</button>
        </div>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-bottom:24px;">
            <div class="card" style="padding:20px;"><div class="text-muted" style="font-size:12px;font-weight:600;margin-bottom:8px;">TODAY'S VISITS</div><div style="font-size:28px;font-weight:700;color:var(--primary);">${todayCount}</div></div>
            <div class="card" style="padding:20px;"><div class="text-muted" style="font-size:12px;font-weight:600;margin-bottom:8px;">COMPLETED THIS WEEK</div><div style="font-size:28px;font-weight:700;color:var(--success);">${weekCount}</div></div>
            <div class="card" style="padding:20px;"><div class="text-muted" style="font-size:12px;font-weight:600;margin-bottom:8px;">MISSED VISITS</div><div style="font-size:28px;font-weight:700;color:var(--danger);">${missedCount}</div></div>
        </div>
        <div class="card" style="padding:0;">
            <div class="table-container">
                <table class="table">
                    <thead><tr><th>SHOP</th><th>AREA</th><th>AGENT</th><th>DATE</th><th>TIME</th><th>STATUS</th><th>NOTES</th></tr></thead>
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>`;
    }

    async function renderFeedback() {
        mainContent.innerHTML = `
        <div class="page-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
            <div>
                <h1 style="margin-bottom: 4px;">Client Feedback</h1>
                <p class="text-muted">Monitor satisfaction and gather insights.</p>
            </div>
            <button class="btn btn-secondary"><i class="fa-solid fa-download"></i> Export Report</button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 24px;">
            <div class="card" style="padding: 24px; text-align: center;">
                <div class="text-muted" style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">AVG RATING</div>
                <div style="font-size: 36px; font-weight: 700; color: var(--primary); margin-bottom: 8px;">4.2<span style="font-size: 18px; color: var(--text-muted);">/5</span></div>
                <div style="color: #F59E0B; font-size: 18px;"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star-half-stroke"></i></div>
            </div>
            <div class="card" style="padding: 24px; text-align: center; display: flex; flex-direction: column; justify-content: center;">
                <div class="text-muted" style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">POSITIVE</div>
                <div style="font-size: 36px; font-weight: 700; color: var(--success);"><i class="fa-regular fa-face-smile"></i> 15</div>
            </div>
            <div class="card" style="padding: 24px; text-align: center; display: flex; flex-direction: column; justify-content: center;">
                <div class="text-muted" style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">NEEDS ATTENTION</div>
                <div style="font-size: 36px; font-weight: 700; color: var(--danger);"><i class="fa-regular fa-face-frown"></i> 2</div>
            </div>
        </div>

        <h3 style="margin-bottom: 16px;">Recent Reviews</h3>
        
        <div style="display: flex; flex-direction: column; gap: 16px;">
            <!-- Review 1 -->
            <div class="card">
                <div style="display: flex; gap: 16px;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: var(--primary-light); color: var(--primary); font-weight: 700; font-size: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">I</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <div style="font-weight: 600; font-size: 16px;">Infosys <span style="font-weight: 400; font-size: 14px; color: var(--text-muted);">— Project Review</span></div>
                            <div class="text-muted" style="font-size: 13px;">2 days ago</div>
                        </div>
                        <div style="color: #F59E0B; font-size: 14px; margin-bottom: 12px;"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i></div>
                        <p style="color: var(--text-body); margin: 0; line-height: 1.6;">Excellent service and quick turnaround. The project manager was highly responsive and resolved all our technical queries within the SLA. Very satisfied.</p>
                    </div>
                </div>
            </div>
            
            <!-- Review 2 -->
            <div class="card">
                <div style="display: flex; gap: 16px;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: var(--secondary-light); color: var(--secondary); font-weight: 700; font-size: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">T</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <div style="font-weight: 600; font-size: 16px;">TCS Portal <span style="font-weight: 400; font-size: 14px; color: var(--text-muted);">— Mid-cycle Checkin</span></div>
                            <div class="text-muted" style="font-size: 13px;">5 days ago</div>
                        </div>
                        <div style="color: #F59E0B; font-size: 14px; margin-bottom: 12px;"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-regular fa-star"></i><i class="fa-regular fa-star"></i></div>
                        <p style="color: var(--text-body); margin: 0; line-height: 1.6;">Delivery was on time, but communication was lacking during the second phase. We expected better proactive updates. Still, the final output is good.</p>
                    </div>
                </div>
            </div>
            
            <!-- Review 3 -->
            <div class="card">
                <div style="display: flex; gap: 16px;">
                    <div style="width: 48px; height: 48px; border-radius: 50%; background: #FEE2E2; color: var(--danger); font-weight: 700; font-size: 20px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">W</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <div style="font-weight: 600; font-size: 16px;">Wipro Technologies <span style="font-weight: 400; font-size: 14px; color: var(--text-muted);">— Support Ticket</span></div>
                            <div class="text-muted" style="font-size: 13px;">1 week ago</div>
                        </div>
                        <div style="color: #F59E0B; font-size: 14px; margin-bottom: 12px;"><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star"></i><i class="fa-solid fa-star-half-stroke"></i></div>
                        <p style="color: var(--text-body); margin: 0; line-height: 1.6;">Support team was quick to address the critical bug in production. Appreciate the swift action.</p>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    // ─── Projects (Client-PM mapping) ─────────────────────────────
    async function renderProjects() {
        let clients = [];
        try { clients = await window.ApiClient.getClients(); } catch (e) { }
        const rows = clients.length ? clients.map(c => `
            <tr>
                <td style="font-weight:500;">${c.name}</td>
                <td>${c.email}</td>
                <td>${c.organization || '—'}</td>
                <td>${c.pm_id ? `<span class="badge badge-primary">PM #${c.pm_id}</span>` : '<span class="badge badge-warning">Unassigned</span>'}</td>
                <td>${c.status || 'active'}</td>
            </tr>`).join('') :
            `<tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted);">No clients found.</td></tr>`;
        mainContent.innerHTML = `
        <div class="page-header" style="margin-bottom:24px;"><h1>Projects</h1><p class="text-muted">Client-to-PM assignment overview.</p></div>
        <div class="card" style="padding:0;"><div class="table-container"><table class="table">
            <thead><tr><th>CLIENT</th><th>EMAIL</th><th>ORGANIZATION</th><th>ASSIGNED PM</th><th>STATUS</th></tr></thead>
            <tbody>${rows}</tbody>
        </table></div></div>`;
    }

    // ─── Meetings ─────────────────────────────────────────────
    async function renderMeetings() {
        let clients = [], allMeetings = [];
        try { clients = await window.ApiClient.getClients(); } catch (e) { }
        for (const c of clients.slice(0, 20)) {
            try {
                const ms = await window.ApiClient.getClientMeetings(c.id);
                (ms || []).forEach(m => allMeetings.push({ ...m, client_name: c.name }));
            } catch (e) { }
        }
        allMeetings.sort((a, b) => new Date(b.meeting_date || 0) - new Date(a.meeting_date || 0));
        const rows = allMeetings.length ? allMeetings.map(m => `
            <tr>
                <td style="font-weight:500;">${m.client_name}</td>
                <td>${m.title || m.summary?.slice(0, 40) || '—'}</td>
                <td>${m.meeting_date ? new Date(m.meeting_date).toLocaleDateString() : '—'}</td>
                <td>${m.meeting_time || '—'}</td>
                <td><span class="badge badge-purple-light">${m.status || 'scheduled'}</span></td>
                <td class="text-muted" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${m.notes || m.summary || '—'}</td>
            </tr>`).join('') :
            `<tr><td colspan="6" style="text-align:center;padding:40px;color:var(--text-muted);">No meetings found.</td></tr>`;
        mainContent.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <div><h1>Meetings</h1><p class="text-muted">All client meeting summaries.</p></div>
        </div>
        <div class="card" style="padding:0;"><div class="table-container"><table class="table">
            <thead><tr><th>CLIENT</th><th>TITLE</th><th>DATE</th><th>TIME</th><th>STATUS</th><th>NOTES</th></tr></thead>
            <tbody>${rows}</tbody>
        </table></div></div>`;
    }

    // ─── Issues ───────────────────────────────────────────────
    async function renderIssues() {
        let issues = [];
        try { issues = await window.ApiClient.getIssues(); } catch (e) { console.warn('Issues fetch failed', e); }
        const sevBadge = s => ({ high: '<span class="badge badge-red-light">High</span>', medium: '<span class="badge badge-yellow-light">Medium</span>', low: '<span class="badge badge-green-light">Low</span>' }[s] || `<span class="badge">${s || '—'}</span>`);
        const statusBadge = s => ({ open: '<span class="badge badge-red-light">Open</span>', in_progress: '<span class="badge badge-purple-light">In Progress</span>', resolved: '<span class="badge badge-green-light">Resolved</span>' }[s] || `<span class="badge">${s || '—'}</span>`);
        const rows = issues.length ? issues.map(i => `
            <tr>
                <td style="font-weight:500;">${i.title || '—'}</td>
                <td>Client #${i.client_id || '—'}</td>
                <td>${sevBadge(i.severity)}</td>
                <td>${statusBadge(i.status)}</td>
                <td>${i.assigned_pm_id ? `PM #${i.assigned_pm_id}` : '—'}</td>
                <td>${i.created_at ? new Date(i.created_at).toLocaleDateString() : '—'}</td>
                <td>
                    <button class="btn btn-ghost" style="padding:4px 8px;" onclick="markIssueResolved(${i.id})"><i class="fa-solid fa-check text-success"></i></button>
                </td>
            </tr>`).join('') :
            `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);">No issues found.</td></tr>`;
        mainContent.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <div><h1>Issues</h1><p class="text-muted">${issues.length} total issues.</p></div>
        </div>
        <div class="card" style="padding:0;"><div class="table-container"><table class="table">
            <thead><tr><th>TITLE</th><th>CLIENT</th><th>SEVERITY</th><th>STATUS</th><th>ASSIGNED PM</th><th>REPORTED</th><th></th></tr></thead>
            <tbody>${rows}</tbody>
        </table></div></div>`;
        window.markIssueResolved = async (id) => {
            try { await window.ApiClient.patchIssue(id, { status: 'resolved' }); renderIssues(); } catch (e) { alert('Could not update issue.'); }
        };
    }

    // ─── HRM ──────────────────────────────────────────────────
    async function renderHRM() {
        let employees = [];
        try { employees = await window.ApiClient.getEmployees(); } catch (e) { console.warn('HRM fetch failed', e); }
        const roleColors = { ADMIN: 'badge-red-light', SALES: 'badge-green-light', TELESALES: 'badge-purple-light', PROJECT_MANAGER: 'badge-yellow-light', PROJECT_MANAGER_AND_SALES: 'badge-purple-light' };
        const rows = employees.length ? employees.map(e => `
            <tr>
                <td>
                    <div style="display:flex;align-items:center;gap:12px;">
                        <div style="width:36px;height:36px;border-radius:50%;background:var(--primary-light);color:var(--primary);font-weight:700;display:flex;align-items:center;justify-content:center;">${(e.full_name || e.name || '?')[0]}</div>
                        <div><div style="font-weight:500;">${e.full_name || e.name || '—'}</div><div style="font-size:12px;color:var(--text-muted);">${e.email || '—'}</div></div>
                    </div>
                </td>
                <td>${e.phone || '—'}</td>
                <td><span class="badge ${roleColors[e.role] || 'badge-purple-light'}">${e.role || '—'}</span></td>
                <td>${e.department || '—'}</td>
                <td>${e.active_clients_count ?? '—'}</td>
            </tr>`).join('') :
            `<tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted);">No employees found.</td></tr>`;
        mainContent.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <div><h1>HR & Payroll</h1><p class="text-muted">${employees.length} employees on record.</p></div>
        </div>
        <div class="card" style="padding:0;"><div class="table-container"><table class="table">
            <thead><tr><th>EMPLOYEE</th><th>PHONE</th><th>ROLE</th><th>DEPARTMENT</th><th>ACTIVE CLIENTS</th></tr></thead>
            <tbody>${rows}</tbody>
        </table></div></div>`;
    }

    // ─── Admin (Users & Roles) ────────────────────────────────
    async function renderAdmin() {
        let users = [];
        try { users = await window.ApiClient.getEmployees(); } catch (e) { console.warn('Admin fetch failed', e); }
        const roleOptions = ['ADMIN', 'SALES', 'TELESALES', 'PROJECT_MANAGER', 'PROJECT_MANAGER_AND_SALES'];
        const rows = users.length ? users.map(u => `
            <tr>
                <td>
                    <div style="display:flex;align-items:center;gap:10px;">
                        <div style="width:32px;height:32px;border-radius:50%;background:var(--primary-light);color:var(--primary);font-weight:700;display:flex;align-items:center;justify-content:center;">${(u.full_name || u.name || '?')[0]}</div>
                        ${u.full_name || u.name || '—'}
                    </div>
                </td>
                <td>${u.email || '—'}</td>
                <td>
                    <select class="form-control" style="height:32px;font-size:13px;" onchange="changeUserRole(${u.user_id || u.id}, this.value)">
                        ${roleOptions.map(r => `<option value="${r}" ${r === u.role ? 'selected' : ''}>${r}</option>`).join('')}
                    </select>
                </td>
                <td><span class="badge ${u.is_active ? 'badge-green-light' : 'badge-red-light'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
            </tr>`).join('') :
            `<tr><td colspan="4" style="text-align:center;padding:40px;color:var(--text-muted);">No users found.</td></tr>`;
        mainContent.innerHTML = `
        <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
            <div><h1>Users & Roles</h1><p class="text-muted">Manage system access and role assignments.</p></div>
        </div>
        <div class="card" style="padding:0;"><div class="table-container"><table class="table">
            <thead><tr><th>USER</th><th>EMAIL</th><th>ROLE</th><th>STATUS</th></tr></thead>
            <tbody>${rows}</tbody>
        </table></div></div>`;
        window.changeUserRole = async (userId, role) => {
            try { await window.ApiClient.updateUserRole(userId, role); } catch (e) { alert('Could not update role.'); }
        };
    }

    // Kickoff
    checkAuth();
});
