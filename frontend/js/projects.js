// frontend/js/projects.js
requireAuth();
const sidebarElement = document.getElementById('sidebar');
if (sidebarElement) sidebarElement.innerHTML = renderSidebar('projects');

let allProjects = [];
let currentProject = null;
let visitTimerInterval = null;
let visitSeconds = 0;
let cameraStream = null;
let currentSearch = "";
let currentFilter = "ALL";
let currentSortBy = 'id';
let currentSortOrder = 'desc';
let currentPmFilter = "ALL";
let storefrontBlob = null;
let selfieBlob = null;

// Smart PM Fatching from active Leads for sorting
function populatePmFilterDropdown() {
    const select = document.getElementById('pm-filter-select');
    if (!select) return;

    // Remember current selection
    const currentVal = select.value;

    // Extract unique PMs from the leads list
    const pmSet = new Set();
    allProjects.forEach(p => {
        const pmName = p.project_manager_name || p.pm_name || (p.project_manager && (p.project_manager.name || p.project_manager.full_name || p.project_manager.email));
        if (pmName) pmSet.add(pmName);
    });

    const uniquePMs = Array.from(pmSet).sort();

    let html = '<option value="ALL">All Project Managers</option>';
    html += '<option value="Unassigned">Unassigned Leads</option>';
    uniquePMs.forEach(pm => { html += `<option value="${pm}">${pm}</option>`; });

    select.innerHTML = html;
    select.value = currentPmFilter; // Restore previous selection if any
}

// 1. Fetch
async function loadHubData() {
    document.getElementById('queue-list').innerHTML = `<div class="p-4 text-center text-muted"><div class="spinner-border spinner-border-sm mb-2"></div><br>Loading...</div>`;
    try {
        const res = await window.ApiClient.request('/shops/');
        
        allProjects = (res || []).map(p => {
            let stage = p.pipeline_stage || p.status || 'LEAD';
            
            // 🚀 THE ULTIMATE FAILSAFE: If the backend says the deal is won, FORCE the UI to Maintenance!
            if (p.status === 'CONVERTED' || p.status === 'COMPLETED' || stage === 'CONVERTED' || stage === 'COMPLETED') {
                stage = 'MAINTENANCE';
            }

            return {
                ...p,
                pipeline_stage: stage,
                assignment_status: p.assignment_status || 'PENDING',
                name: p.name || p.shop_name || 'Unnamed Client',
                area_name: p.area_name || (p.area && p.area.name) || 'No Area Assigned',
                contact_person: p.contact_person || 'No Contact Person',
                phone: p.phone || 'No Phone'
            };
        });
        
        populatePmFilterDropdown();
        filterQueue();
        
        // Don't auto-switch if we are already viewing a specific project
        if (allProjects.length > 0 && !currentProject) {
            selectLead(allProjects[0].id);
        } else if (currentProject) {
            // Force a re-render of the currently selected lead to update its progress bar!
            selectLead(currentProject.id); 
        }
        
    } catch (err) {
        console.error("Load failed:", err);
        document.getElementById('queue-list').innerHTML = `<div class="p-3 text-danger text-center">Failed to load data</div>`;
    }
}

// 2. Filters & Sort
function handleSearch(e) { currentSearch = e.target.value.toLowerCase(); filterQueue(); }

function setFilter(filterType, element) {
    currentFilter = filterType;
    document.querySelectorAll('.filter-pill').forEach(el => { el.classList.remove('bg-dark', 'text-white'); el.classList.add('bg-light', 'text-dark', 'border'); });
    element.classList.remove('bg-light', 'text-dark', 'border'); element.classList.add('bg-dark', 'text-white');
    filterQueue();
}

// 🚀 New PM Filter Apply logic
window.applyPmFilter = (pmName) => {
    currentPmFilter = pmName;
    filterQueue();
};

// 🚀 Upgraded Sort function to handle the new button styles
window.applySort = (by, order, element) => {
    currentSortBy = by;
    currentSortOrder = order;

    // Reset all buttons to default grey state
    document.querySelectorAll('.sort-option').forEach(el => {
        el.classList.remove('shadow-sm');
        el.style.background = '#f8fafc';
        el.style.color = '#475569';
        el.style.borderColor = '#e2e8f0';
        el.style.fontWeight = '500';
    });

    // Highlight the clicked button in primary blue
    if (element) {
        element.classList.add('shadow-sm');
        element.style.background = '#eff6ff';
        element.style.color = '#1d4ed8';
        element.style.borderColor = '#bfdbfe';
        element.style.fontWeight = '600';
    }

    filterQueue();
};

// 🚀 Upgraded master filter loop
function filterQueue() {
    let filtered = allProjects.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(currentSearch) || p.contact_person.toLowerCase().includes(currentSearch) || p.phone.includes(currentSearch);

        let matchesFilter = true;
        if (currentFilter === 'IN_PROGRESS') matchesFilter = (p.pipeline_stage === 'PITCHING');
        else if (currentFilter === 'DEMO_SET') matchesFilter = (p.demo_scheduled_at != null || p.pipeline_stage === 'NEGOTIATION');

        // NEW: Check the PM Filter
        let matchesPm = true;
        if (currentPmFilter !== "ALL") {
            const pmName = p.project_manager_name || p.pm_name || (p.project_manager && (p.project_manager.name || p.project_manager.full_name || p.project_manager.email)) || 'Unassigned';
            matchesPm = (pmName === currentPmFilter);
        }

        return matchesSearch && matchesFilter && matchesPm && !p.is_deleted;
    });

    const stageOrder = ["LEAD", "PITCHING", "NEGOTIATION", "DELIVERY", "MAINTENANCE"];
    filtered.sort((a, b) => {
        let valA, valB;
        if (currentSortBy === 'id') { valA = a.id; valB = b.id; }
        else if (currentSortBy === 'status') { valA = stageOrder.indexOf(a.pipeline_stage); valB = stageOrder.indexOf(b.pipeline_stage); }
        let comparison = (valA > valB) ? 1 : ((valA < valB) ? -1 : 0);
        return currentSortOrder === 'desc' ? (comparison * -1) : comparison;
    });

    renderQueue(filtered);
}


function renderQueue(projects) {
    const queueEl = document.getElementById('queue-list');
    if (projects.length === 0) { queueEl.innerHTML = `<div class="p-4 text-center text-muted">No leads found.</div>`; return; }

    let html = '';
    projects.forEach(p => {
        let badgeColor = "bg-secondary";
        if (p.pipeline_stage === "LEAD") badgeColor = "bg-primary";
        if (p.pipeline_stage === "PITCHING") badgeColor = "bg-warning text-dark";
        if (p.pipeline_stage === "NEGOTIATION") badgeColor = "bg-info text-dark";
        if (p.pipeline_stage === "DELIVERY") badgeColor = "bg-success";
        if (p.pipeline_stage === "MAINTENANCE") badgeColor = "bg-dark";

        const needsAccept = (p.pipeline_stage === 'LEAD' && p.assignment_status !== 'ACCEPTED');
        const acceptBadge = needsAccept ? `<span class="badge bg-danger rounded-pill" style="font-size:0.6rem;"><i class="bi bi-lightning-charge-fill"></i> Claim</span>` : '';

        html += `
                <div class="lead-card" id="card-${p.id}" onclick="selectLead(${p.id})">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div><span class="badge ${badgeColor}" style="font-size:0.65rem;">${p.pipeline_stage}</span> ${acceptBadge}</div>
                        <span class="text-muted" style="font-size:0.7rem;">ID: ${p.id}</span>
                    </div>
                    <div class="fw-bold text-dark">${p.name}</div>
                    <div class="small text-muted"><i class="bi bi-geo-alt me-1"></i>${p.area_name}</div>
                </div>`;
    });
    queueEl.innerHTML = html;
}

// 3. Selection
function selectLead(id) {
    document.querySelectorAll('.lead-card').forEach(c => c.classList.remove('active'));
    const selectedCard = document.getElementById(`card-${id}`);
    if (selectedCard) selectedCard.classList.add('active');

    currentProject = allProjects.find(p => p.id === id);
    if (!currentProject) return;

    document.getElementById('detail-title').innerText = currentProject.name;
    document.getElementById('detail-contact').innerText = `Contact: ${currentProject.contact_person} • ${currentProject.phone}`;

    renderProgressBar(currentProject.pipeline_stage);
    renderActionCenter(currentProject);
    // NEW: Fetch and show the history!
    loadVisitHistory(currentProject.id);
}

function renderProgressBar(stage) {
    const stages = ["LEAD", "PITCHING", "NEGOTIATION", "DELIVERY", "MAINTENANCE"];
    const currentIndex = stages.indexOf(stage) >= 0 ? stages.indexOf(stage) : 0;
    let html = '';
    stages.forEach((s, index) => {
        let statusClass = index < currentIndex ? "completed" : (index === currentIndex ? "active" : "");
        html += `<div class="step ${statusClass}"><div class="step-circle">${index < currentIndex ? '<i class="bi bi-check-lg"></i>' : index + 1}</div><div class="step-label">${s}</div></div>`;
    });
    document.querySelector('.progress-tracker').innerHTML = html;
}

// 4. Action Engine
function renderActionCenter(project) {
    const actionContainer = document.querySelector('.action-center');
    stopCamera();
    if (visitTimerInterval) { showActiveTimerUI(); return; }

    if (project.pipeline_stage === "LEAD") {
        if (project.assignment_status !== "ACCEPTED") {
            actionContainer.innerHTML = `
                        <div class="text-center py-5">
                            <div class="mb-3"><i class="bi bi-inbox text-warning" style="font-size: 3rem;"></i></div>
                            <h4 class="fw-bold">Claim This Lead</h4>
                            <p class="text-muted mb-4">You must accept this lead to lock it to your profile before starting a visit.</p>
                            <button class="btn btn-success px-5 fw-bold" onclick="acceptLead(${project.id})">Accept Lead</button>
                        </div>`;
        } else {
            actionContainer.innerHTML = `
                        <div class="text-center py-4">
                            <div class="mb-3"><i class="bi bi-play-circle text-primary" style="font-size: 3rem;"></i></div>
                            <h4 class="fw-bold">Ready for Visit</h4>
                            <div class="d-flex justify-content-center mt-4">
                                <button class="btn btn-primary px-4 fw-semibold" onclick="openCameraView('environment')"><i class="bi bi-camera me-2"></i>Start Visit (Take Photo)</button>
                            </div>
                        </div>`;
        }
    } else if (project.pipeline_stage === "PITCHING") {
        actionContainer.innerHTML = `
                    <div class="text-center py-4">
                        <div class="mb-3"><i class="bi bi-calendar-check text-warning" style="font-size: 3rem;"></i></div>
                        <h4 class="fw-bold">Pitching & Demo</h4>
                        <div class="d-flex justify-content-center gap-3 mt-4">
                            <button class="btn btn-warning text-dark px-4 fw-bold" onclick="window.openSmartScheduleModal(${project.id})"><i class="bi bi-calendar-plus me-2"></i>Schedule Demo</button>
                            <button class="btn btn-outline-dark px-4 fw-semibold" onclick="openCameraView('environment')"><i class="bi bi-person-walking me-2"></i>Log Follow-up Visit</button>
                        </div>
                    </div>`;
        // 👇 NEW NEGOTIATION BLOCK 👇
    } else if (project.pipeline_stage === "NEGOTIATION") {
        actionContainer.innerHTML = `
                    <div class="text-center py-4">
                        <div class="mb-3"><i class="bi bi-display text-info" style="font-size: 3rem;"></i></div>
                        <h4 class="fw-bold text-info">Demo & Negotiation</h4>
                        <p class="text-muted mb-4 px-3">The PM is handling the demo. You can log field follow-ups or reschedule the demo if the client requested a time change.</p>
                        <div class="d-flex justify-content-center gap-3 mt-4 flex-wrap">
                            <button class="btn btn-info text-dark px-4 fw-bold shadow-sm" onclick="window.openSmartScheduleModal(${project.id})"><i class="bi bi-calendar-event me-2"></i>Re-Schedule Demo</button>
                            <button class="btn btn-outline-dark px-4 fw-semibold" onclick="openCameraView('environment')"><i class="bi bi-person-walking me-2"></i>Log Follow-up Visit</button>
                        </div>
                    </div>`;
        // 👆 END NEW BLOCK 👆
    } else if (project.pipeline_stage === "DELIVERY") {
        actionContainer.innerHTML = `
                    <div class="text-center py-5">
                        <div class="mb-3"><i class="bi bi-receipt-cutoff text-success" style="font-size: 3rem;"></i></div>
                        <h4 class="fw-bold text-success">Ready for Billing</h4>
                        <p class="text-muted mb-4">This deal is won. Click below to generate an invoice and collect payment.</p>
                        <a href="billing.html?close_shop_id=${project.id}" class="btn btn-success px-5 fw-bold"><i class="bi bi-currency-rupee me-2"></i>Generate Invoice</a>
                    </div>`;
    } else if (project.pipeline_stage === "MAINTENANCE") {
        actionContainer.innerHTML = `
                    <div class="text-center py-5">
                        <div class="spinner-border text-success mb-3" role="status"></div>
                        <h5 class="fw-bold text-muted">Loading Live Billing Tracker...</h5>
                    </div>`;
    } else {
        actionContainer.innerHTML = `<div class="text-center py-4"><h4 class="fw-bold">${project.pipeline_stage} Stage</h4></div>`;
    }
}

async function loadVisitHistory(shopId) {
    const historyContainer = document.getElementById('visit-history-section');
    if (!historyContainer) return;

    historyContainer.innerHTML = '<div class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm me-2"></span>Loading 360° timeline...</div>';

    try {
        // 🚀 NEW: Bulletproof Fetching with Error Logging
        let visitsRes = [];
        let invoicesRes = [];

        try {
            visitsRes = await window.ApiClient.request(`/visits/?shop_id=${shopId}`);
        } catch (e) {
            console.warn("Visits fetch failed:", e);
        }

        try {
            // If this fails, we will see it in the Chrome Console!
            invoicesRes = await window.ApiClient.request(`/billing?shop_id=${shopId}&archived=ALL`);
            console.log("📦 Raw Invoices Response:", invoicesRes);
        } catch (e) {
            console.error("❌ Invoices fetch failed! The endpoint might be /billing/invoices/ instead of /invoices/", e);
        }

        // Safely extract visits
        const visits = Array.isArray(visitsRes) ? visitsRes : (visitsRes.items || visitsRes.data || []);

        // 🚀 NEW: Bulletproof Invoice Extraction (Checks every possible JSON wrapper)
        let invoices = [];
        if (Array.isArray(invoicesRes)) {
            invoices = invoicesRes;
        } else if (invoicesRes) {
            invoices = invoicesRes.items || invoicesRes.data || invoicesRes.invoices || [];
        }

        // 🚀 OVERRIDE THE UI: If an invoice exists, morph the Action Center into the Live Tracker!
        // FIX: We now check for DELIVERY *OR* MAINTENANCE
        if (currentProject && currentProject.pipeline_stage === "DELIVERY" && invoices.length > 0) {
            const sortedInvs = [...invoices].sort((a, b) => new Date(b.created_at || new Date()) - new Date(a.created_at || new Date()));
            updateActionCenterForExistingInvoice(sortedInvs[0]);
        } 
        else if (currentProject && currentProject.pipeline_stage === "MAINTENANCE") {
            // NOTE: We will hook this up to an actual /meetings API call in the next step.
            // For now, we pass an empty array to show the "Schedule Session 1" UI!
            renderTrainingTracker(currentProject, []); 
        }

        let totalInteractions = visits.length + invoices.length;
        let demoCardHtml = '';

        // 1. Virtual Card for UPCOMING Demos
        if (currentProject && currentProject.demo_scheduled_at) {
            totalInteractions += 1;
            const demoDate = new Date(currentProject.demo_scheduled_at).toLocaleString('en-IN', {
                day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            const pmName = currentProject.project_manager_name || currentProject.pm_name || (currentProject.project_manager && currentProject.project_manager.name) || 'Assigned PM';

            demoCardHtml = `
                <div class="card mb-3 border-0 shadow-sm" style="border-radius: 12px; overflow: hidden; background: linear-gradient(to right, #f8fafc, #eef2ff); border-left: 4px solid #6366f1 !important;">
                    <div class="card-body p-4">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h6 class="fw-bold mb-1" style="color: #4f46e5;"><i class="bi bi-calendar-event me-1"></i> Upcoming Demo Session</h6>
                                <div class="text-muted small mb-1"><i class="bi bi-clock me-1"></i>${demoDate}</div>
                                <div class="text-muted mt-2" style="font-size: 0.8rem;"><i class="bi bi-person-badge text-secondary me-1"></i>Assigned PM: <span class="fw-bold text-dark">${pmName}</span></div>
                            </div>
                            <span class="badge bg-warning text-dark shadow-sm"><i class="bi bi-hourglass-split me-1"></i>Scheduled</span>
                        </div>
                    </div>
                </div>`;
        }

        // 2. Empty State
        if (totalInteractions === 0) {
            historyContainer.innerHTML = `
                <div class="text-center p-4 border rounded" style="background: #f8fafc; border-style: dashed !important;">
                    <i class="bi bi-clock-history text-muted mb-2" style="font-size: 1.5rem; display: block;"></i>
                    <span class="text-muted small">No past visits, demos, or invoices recorded yet.</span>
                </div>`;
            return;
        }

        const visitCountText = totalInteractions > 1 ? `${totalInteractions} Records` : `1 Record`;
        let html = `
            <div class="d-flex align-items-center mb-3">
                <h6 class="fw-bold mb-0 text-uppercase" style="letter-spacing: 0.5px; font-size: 0.8rem; color: #64748b;">360° Interaction Timeline</h6>
                <span class="badge bg-primary text-white rounded-pill ms-2 shadow-sm" style="font-size: 0.65rem; padding: 0.35em 0.65em;">${visitCountText}</span>
            </div>`;

        html += demoCardHtml; // Inject upcoming demo at the top

        // 3. MERGE AND SORT ALL TIMELINE EVENTS
        let timelineEvents = [];

        visits.forEach(v => {
            timelineEvents.push({ type: 'VISIT', dateObj: new Date(v.visit_date), data: v });
        });

        invoices.forEach(inv => {
            // Use created_at, issue_date, or fallback to current time
            timelineEvents.push({ type: 'INVOICE', dateObj: new Date(inv.created_at || inv.issue_date || new Date()), data: inv });
        });

        // Sort everything Newest First!
        timelineEvents.sort((a, b) => b.dateObj - a.dateObj);

        // 4. RENDER LOOP
        timelineEvents.forEach(event => {
            const dateStr = event.dateObj.toLocaleString('en-IN', {
                day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            // ==========================================
            // 📝 INVOICE CARD UI
            // ==========================================
            if (event.type === 'INVOICE') {
                const inv = event.data;
                
                // 🚀 FIX: We now explicitly check "invoice_status", which perfectly matches the Billing Dashboard!
                const st = inv.invoice_status || inv.status || 'DRAFT';
                const statusStr = String(st).toUpperCase();
                
                // Dynamic styling perfectly mirrored from billing.html
                let bgGradient = 'linear-gradient(to right, #f8fafc, #f1f5f9)';
                let borderLeft = '4px solid #94a3b8';
                let iconColor = '#475569';
                let badgeClass = 'bg-secondary';
                let statusIcon = 'bi-file-earmark-text';
                let finalBadgeText = st;

                if (statusStr === 'VERIFIED') {
                    // 🟩 Green for Verified
                    bgGradient = 'linear-gradient(to right, #f0fdf4, #dcfce7)'; borderLeft = '4px solid #10b981'; iconColor = '#047857'; badgeClass = 'bg-success'; statusIcon = 'bi-patch-check';
                    finalBadgeText = 'VERIFIED';
                } else if (statusStr === 'SENT' || statusStr === 'CONFIRMED') {
                    // 🟦 Blue for Sent via WhatsApp
                    bgGradient = 'linear-gradient(to right, #eff6ff, #dbeafe)'; borderLeft = '4px solid #3b82f6'; iconColor = '#1d4ed8'; badgeClass = 'bg-primary'; statusIcon = 'bi-whatsapp';
                    finalBadgeText = statusStr;
                } else if (statusStr === 'PENDING_VERIFICATION' || statusStr === 'PENDING') {
                    // 🟧 Orange for Pending Review
                    bgGradient = 'linear-gradient(to right, #fffbeb, #fef3c7)'; borderLeft = '4px solid #f59e0b'; iconColor = '#b45309'; badgeClass = 'bg-warning text-dark'; statusIcon = 'bi-hourglass-split';
                    finalBadgeText = 'PENDING REVIEW';
                } else if (statusStr === 'CANCELLED') {
                    // 🟥 Red for Cancelled
                    bgGradient = 'linear-gradient(to right, #fef2f2, #fee2e2)'; borderLeft = '4px solid #ef4444'; iconColor = '#b91c1c'; badgeClass = 'bg-danger'; statusIcon = 'bi-x-circle';
                    finalBadgeText = 'CANCELLED';
                }

                const amount = inv.total_amount || inv.amount || 0;
                const formattedAmount = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);

                html += `
                    <div class="card mb-3 border-0 shadow-sm" style="border-radius: 12px; overflow: hidden; background: ${bgGradient}; border-left: ${borderLeft} !important;">
                        <div class="card-body p-4">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <h6 class="fw-bold mb-1" style="color: ${iconColor};"><i class="bi bi-receipt me-1"></i> Billing Invoice Generated</h6>
                                    <div class="text-muted small mb-1"><i class="bi bi-calendar3 me-1"></i>${dateStr}</div>
                                    <div class="text-muted mt-2" style="font-size: 0.8rem;">Invoice #: <span class="fw-bold text-dark">${inv.invoice_number || 'Draft'}</span></div>
                                </div>
                                <div class="text-end">
                                    <span class="badge ${badgeClass} shadow-sm mb-2 text-uppercase" style="letter-spacing: 0.5px;"><i class="bi ${statusIcon} me-1"></i>${finalBadgeText}</span>
                                    <h5 class="fw-bold text-dark mb-0">${formattedAmount}</h5>
                                </div>
                            </div>
                        </div>
                    </div>`;
            }
            
            // ==========================================
            // 🏃‍♂️ VISIT & DEMO CARDS UI
            // ==========================================
            else if (event.type === 'VISIT') {
                const v = event.data;
                const repName = v.user_name || (v.user && (v.user.full_name || v.user.name)) || 'Unknown Rep';

                // Completed Demo
                if (v.status === 'COMPLETED') {
                    html += `
                        <div class="card mb-3 border-0 shadow-sm" style="border-radius: 12px; overflow: hidden; background: linear-gradient(to right, #f0fdf4, #dcfce7); border-left: 4px solid #10b981 !important;">
                            <div class="card-body p-4">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <h6 class="fw-bold mb-1" style="color: #047857;"><i class="bi bi-display me-1"></i> Product Demo Completed</h6>
                                        <div class="text-muted small mb-1"><i class="bi bi-calendar3 me-1"></i>${dateStr}</div>
                                        <div class="text-muted mt-2" style="font-size: 0.8rem;"><i class="bi bi-person-check text-secondary me-1"></i>Hosted by PM: <span class="fw-bold text-dark">${repName}</span></div>
                                    </div>
                                    <span class="badge bg-success shadow-sm"><i class="bi bi-check-circle-fill me-1"></i>Done</span>
                                </div>
                            </div>
                        </div>`;
                }
                // Cancelled Demo
                else if (v.status === 'CANCELLED') {
                    html += `
                        <div class="card mb-3 border-0 shadow-sm" style="border-radius: 12px; overflow: hidden; background: linear-gradient(to right, #fff1f2, #ffe4e6); border-left: 4px solid #e11d48 !important;">
                            <div class="card-body p-4">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <h6 class="fw-bold mb-1" style="color: #be123c;"><i class="bi bi-x-octagon me-1"></i> Product Demo Cancelled</h6>
                                        <div class="text-muted small mb-1"><i class="bi bi-calendar3 me-1"></i>${dateStr}</div>
                                        <div class="text-muted mt-2" style="font-size: 0.8rem;"><i class="bi bi-person-x text-secondary me-1"></i>Cancelled by: <span class="fw-bold text-dark">${repName}</span></div>
                                    </div>
                                    <span class="badge bg-danger shadow-sm"><i class="bi bi-x me-1"></i>Cancelled</span>
                                </div>
                            </div>
                        </div>`;
                }
                // Standard Physical Visit
                else {
                    const duration = v.duration_seconds ? formatTime(v.duration_seconds) : '00:00:00';
                    const statusColors = { 'SATISFIED': 'text-primary', 'ACCEPT': 'text-success', 'TAKE_TIME_TO_THINK': 'text-warning', 'DECLINE': 'text-danger', 'OTHER': 'text-secondary' };
                    const statusColor = statusColors[v.status] || 'text-dark';

                    const formatImgUrl = (path) => {
                        if (!path) return '';
                        if (path.startsWith('http')) return path;
                        const baseUrl = window.ApiClient.API_BASE_URL ? window.ApiClient.API_BASE_URL.split('/api')[0] : window.location.origin;
                        return baseUrl + path;
                    };

                    let photosHtml = '<div class="mt-3 d-flex gap-2 flex-wrap">';
                    if (v.storefront_photo_url) photosHtml += `<div class="text-center"><img src="${formatImgUrl(v.storefront_photo_url)}" alt="Storefront" class="img-thumbnail shadow-sm bg-white" style="max-height: 120px; border-radius: 8px; cursor: pointer; object-fit: cover;" onclick="window.open(this.src, '_blank')"><div class="small text-muted mt-1 fw-bold" style="font-size: 0.7rem; text-transform: uppercase;">Storefront</div></div>`;
                    if (v.selfie_photo_url) photosHtml += `<div class="text-center"><img src="${formatImgUrl(v.selfie_photo_url)}" alt="Selfie" class="img-thumbnail shadow-sm bg-white" style="max-height: 120px; border-radius: 8px; cursor: pointer; object-fit: cover;" onclick="window.open(this.src, '_blank')"><div class="small text-muted mt-1 fw-bold" style="font-size: 0.7rem; text-transform: uppercase;">Rep Selfie</div></div>`;
                    if (!v.storefront_photo_url && !v.selfie_photo_url && v.photo_url) photosHtml += `<div class="text-center"><img src="${formatImgUrl(v.photo_url)}" alt="Visit Photo" class="img-thumbnail shadow-sm bg-white" style="max-height: 120px; border-radius: 8px; cursor: pointer; object-fit: cover;" onclick="window.open(this.src, '_blank')"><div class="small text-muted mt-1 fw-bold" style="font-size: 0.7rem; text-transform: uppercase;">Photo</div></div>`;
                    photosHtml += '</div>';

                    html += `
                        <div class="card mb-3 border-0 shadow-sm" style="border-radius: 12px; overflow: hidden;">
                            <div class="card-body p-4">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <h6 class="fw-bold mb-1 ${statusColor}"><i class="bi bi-record-circle me-1"></i>${v.status || 'VISIT'}</h6>
                                        <div class="text-muted small mb-1"><i class="bi bi-calendar3 me-1"></i>${dateStr}</div>
                                        <div class="text-muted" style="font-size: 0.75rem;"><i class="bi bi-person-badge text-secondary me-1"></i>Visited by: <span class="fw-bold text-dark">${repName}</span></div>
                                    </div>
                                    <span class="badge bg-light text-dark border"><i class="bi bi-stopwatch me-1"></i>${duration}</span>
                                </div>
                                <div class="mt-3 p-3 bg-light rounded text-dark" style="font-size: 0.9rem;">
                                    <strong>Remarks:</strong> ${v.remarks || '<span class="text-muted fst-italic">No remarks provided.</span>'}
                                    ${v.decline_remarks ? `<br><strong class="text-danger mt-1 d-block">Decline Reason:</strong> ${v.decline_remarks}` : ''}
                                </div>
                                ${photosHtml}
                            </div>
                        </div>`;
                }
            }
        });

        historyContainer.innerHTML = html;
    } catch (error) {
        console.error("Failed to load 360 history:", error);
        historyContainer.innerHTML = '<div class="text-center text-danger py-3 small"><i class="bi bi-exclamation-triangle me-1"></i> Could not load full timeline.</div>';
    }
}

async function acceptLead(id) {
    try {
        await window.ApiClient.request(`/shops/${id}/accept`, { method: 'POST' });
        await loadHubData();
    } catch (err) {
        alert("Failed to accept lead. Someone else may have claimed it.");
    }
}

// 5. Hardware Controllers
function openCameraView(facingMode) {
    const actionContainer = document.querySelector('.action-center');
    const isStart = facingMode === 'environment';

    // Reset the blobs if we are starting a fresh visit
    if (isStart) {
        storefrontBlob = null;
        selfieBlob = null;
    }

    actionContainer.innerHTML = `
        <div class="text-center">
            <h5 class="fw-bold">${isStart ? "Step 1: Capture Storefront" : "Final Step: Capture Selfie"}</h5>
            <div class="camera-wrapper mx-auto mb-3" style="max-width: 400px; border-radius: 12px; overflow: hidden; background: #000; position: relative;">
                <video id="camera-preview" autoplay playsinline style="width: 100%; height: auto; display: block;"></video>
            </div>
            <button id="snap-btn" class="btn btn-${isStart ? 'primary' : 'success'} fw-bold px-4 py-2" onclick="${isStart ? 'snapStorefrontAndStart()' : 'snapSelfieAndFinish()'}">
                <i class="bi bi-camera me-2"></i>Snap Photo
            </button>
            <button class="btn btn-light fw-bold px-4 py-2 ms-2" onclick="renderActionCenter(currentProject)">Cancel</button>
        </div>`;
    initCamera(facingMode);
}

async function initCamera(facingMode) {
    const videoEl = document.getElementById('camera-preview');
    if (!videoEl) return;
    stopCamera();
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: facingMode } }, audio: false });
        videoEl.srcObject = cameraStream;
    } catch (err) {
        alert("Please enable camera permissions.");
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
}

// --- Image Capture Logic ---
function captureVideoFrame() {
    return new Promise(resolve => {
        const video = document.getElementById('camera-preview');
        // Ensure video exists and has loaded its dimensions
        if (!video || video.videoWidth === 0) {
            console.error("Camera not fully loaded yet!");
            return resolve(null);
        }

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert to JPEG
        canvas.toBlob(blob => {
            resolve(blob);
        }, 'image/jpeg', 0.8);
    });
}

async function snapStorefrontAndStart() {
    const btn = document.getElementById('snap-btn');
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
    btn.disabled = true;

    // 1. Await the photo capture FIRST
    storefrontBlob = await captureVideoFrame();

    if (!storefrontBlob) {
        alert("Failed to capture image. Please try again.");
        btn.innerHTML = '<i class="bi bi-camera me-2"></i>Snap Photo';
        btn.disabled = false;
        return;
    }

    // 2. Stop camera and move to timer
    stopCamera();
    startTimer();
    showActiveTimerUI();
}

function showActiveTimerUI() {
    document.querySelector('.action-center').innerHTML = `
        <div class="text-center py-4">
            <div class="mb-2"><span class="live-indicator"></span><span class="text-danger fw-bold text-uppercase" style="letter-spacing: 1px; font-size: 0.8rem;">Meeting In Progress</span></div>
            <div class="timer-display" id="visit-timer">${formatTime(visitSeconds)}</div>
            <p class="text-muted mb-4"><i class="bi bi-check-circle-fill text-success me-1"></i> Timer is running in background.</p>
            <button class="btn btn-danger fw-bold px-4 py-2" onclick="openCameraView('user')"><i class="bi bi-stop-circle me-2"></i>End Visit (Take Selfie)</button>
        </div>`;
}

async function snapSelfieAndFinish() {
    const btn = document.getElementById('snap-btn');
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';
    btn.disabled = true;

    // 1. Await the final selfie
    selfieBlob = await captureVideoFrame();

    // 2. Stop everything and render the outcome form
    stopCamera();
    stopTimer();

    document.querySelector('.action-center').innerHTML = `
        <div class="text-center py-4">
            <h5 class="fw-bold mb-2">Visit Completed!</h5>
            <p class="text-muted mb-4">Duration: <span class="fw-bold text-dark">${formatTime(visitSeconds)}</span></p>
            
            <div class="mx-auto text-start" style="max-width: 400px;">
                <label class="form-label fw-bold text-dark mb-2">Interaction Outcome <span class="text-danger">*</span></label>
                <input type="hidden" id="visit-outcome" value="">

                <div class="outcome-grid" id="outcome-grid-container">
                    <div class="outcome-card" onclick="selectOutcome('SATISFIED', this, 'active-satisfied')"><i class="bi bi-calendar-check text-primary"></i><span>Schedule Demo</span></div>
                    <div class="outcome-card" onclick="selectOutcome('ACCEPT', this, 'active-accept')"><i class="bi bi-check-circle text-success"></i><span>Accepted</span></div>
                    <div class="outcome-card" onclick="selectOutcome('TAKE_TIME_TO_THINK', this, 'active-thinking')"><i class="bi bi-hourglass-split text-warning"></i><span>Needs Time</span></div>
                    <div class="outcome-card" onclick="selectOutcome('DECLINE', this, 'active-decline')"><i class="bi bi-x-circle text-danger"></i><span>Declined</span></div>
                    <div class="outcome-card outcome-full-width" onclick="selectOutcome('OTHER', this, 'active-other')"><i class="bi bi-three-dots text-secondary"></i><span>Other Reason</span></div>
                </div>

                <div id="decline-reason-container" class="d-none mb-3 p-3 rounded" style="background: #fef2f2; border: 1px dashed #fca5a5;">
                    <label class="form-label fw-bold text-danger mb-2" style="font-size: 0.8rem;">Why did they decline? <span class="text-danger">*</span></label>
                    <select class="form-select border-danger text-danger shadow-sm" id="decline-reason" style="font-weight: 500;">
                        <option value="" disabled selected>— Select Reason —</option>
                        <option value="Not interested">Not interested</option>
                        <option value="Price is too high">Price is too high</option>
                        <option value="Already using a competitor">Already using a competitor</option>
                        <option value="Need more time to decide">Need more time to decide</option>
                        <option value="Other reason">Other reason</option>
                    </select>
                </div>

                <div id="accept-message-container" class="d-none mb-3 p-3 rounded text-center shadow-sm" style="background: #ecfdf5; border: 1px dashed #34d399;">
                    <div class="fw-bold mb-1" style="color: #047857;"><i class="bi bi-patch-check-fill me-1"></i> Lead Accepted!</div>
                    <div style="color: #065f46; font-size: 0.8rem;">The system will now start the billing flow.</div>
                </div>

                <label class="form-label fw-bold text-dark mb-2">Remarks / Notes <span class="text-danger">*</span></label>
                <textarea class="form-control mb-4 shadow-sm" id="visit-remarks" rows="3" placeholder="Key concerns raised?" style="border-radius: 12px; resize: none;"></textarea>

                <button class="btn btn-dark fw-bold w-100 py-3 rounded-pill shadow" onclick="submitFinalVisit(event)"><i class="bi bi-cloud-arrow-up me-2"></i>Save Visit Record</button>
            </div>
        </div>
    `;
}

function selectOutcome(val, element, activeClass) {
    document.getElementById('visit-outcome').value = val;
    document.getElementById('outcome-grid-container').style.border = "none";
    document.getElementById('outcome-grid-container').style.padding = "0";
    const classesToRemove = ['active-satisfied', 'active-accept', 'active-thinking', 'active-decline', 'active-other'];
    document.querySelectorAll('.outcome-card').forEach(c => classesToRemove.forEach(cls => c.classList.remove(cls)));
    element.classList.add(activeClass);
    toggleDynamicUI();
}

function toggleDynamicUI() {
    const out = document.getElementById('visit-outcome').value;
    const dec = document.getElementById('decline-reason-container');
    const acc = document.getElementById('accept-message-container');
    if (out === 'DECLINE') dec.classList.remove('d-none'); else { dec.classList.add('d-none'); document.getElementById('decline-reason').value = ""; }
    if (out === 'ACCEPT') acc.classList.remove('d-none'); else acc.classList.add('d-none');
}

// 6. Submit API
async function submitFinalVisit(event) {
    const outEl = document.getElementById('visit-outcome');
    const remEl = document.getElementById('visit-remarks');
    const decEl = document.getElementById('decline-reason');

    const outcome = outEl.value;
    const remarks = remEl.value.trim();
    let declineReason = "";

    // 1. Validate Form
    if (!outcome) { document.getElementById('outcome-grid-container').style.border = "2px dashed #ef4444"; return alert("Select Outcome"); }
    if (outcome === 'DECLINE') { declineReason = decEl.value; if (!declineReason) { decEl.classList.add('is-invalid'); return alert("Select Decline Reason"); } }
    if (!remarks) { remEl.classList.add('is-invalid'); return alert("Enter Remarks"); }

    // 2. Safely grab images (Prevents the script from crashing if variables are missing)
    const sFrontPhoto = typeof storefrontBlob !== 'undefined' ? storefrontBlob : null;
    const sFiePhoto = typeof selfieBlob !== 'undefined' ? selfieBlob : null;

    // 3. UI Safety Check
    if (!sFrontPhoto && !sFiePhoto) {
        alert("Wait! You must snap at least one photo (Storefront or Selfie) before saving.");
        return; // Stops here, no crash!
    }

    // 4. Build FormData
    const formData = new FormData();
    formData.append('shop_id', currentProject.id);
    formData.append('status', outcome);
    formData.append('remarks', remarks);
    formData.append('duration_seconds', typeof visitSeconds !== 'undefined' ? visitSeconds : 0);
    if (declineReason) formData.append('decline_remarks', declineReason);

    // Attach the physical image files!
    if (sFrontPhoto) formData.append('storefront_photo', sFrontPhoto, 'storefront.jpg');
    if (sFiePhoto) formData.append('selfie_photo', sFiePhoto, 'selfie.jpg');

    // 5. Lock UI
    const saveBtn = event.currentTarget;
    const originalBtnHtml = saveBtn.innerHTML;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
    saveBtn.classList.add('disabled');

    try {
        // 6. Send the raw fetch request (Bypasses JSON converters)
        const token = window.ApiClient.getAccessToken();
        const baseUrl = window.ApiClient.API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

        const response = await fetch(`${baseUrl}/visits/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
                // CRITICAL: We do NOT set 'Content-Type' manually!
            },
            body: formData
        });

        // Check if backend rejected it
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server returned ${response.status}`);
        }

        // 7. Handle Success UI Transition
        if (outcome === 'ACCEPT') {
            document.querySelector('.action-center').innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-trophy-fill text-warning" style="font-size: 4rem;"></i>
                    <h3 class="fw-bold text-success mb-2">Deal Won!</h3>
                    <p class="text-muted mb-4">You can now generate the invoice and collect payment.</p>
                    <a href="billing.html?close_shop_id=${currentProject.id}" class="btn btn-success btn-lg fw-bold rounded-pill px-5"><i class="bi bi-receipt-cutoff me-2"></i>Generate Invoice Now</a>
                    <div class="mt-3"><button class="btn btn-link text-muted small" onclick="loadHubData()">Skip for now</button></div>
                </div>`;
        } else {
            if (outcome === 'DECLINE') alert("Lead Archived.");

            await loadHubData(); // Refresh Left Queue

            // Refresh Right Pane to show new stage and History Timeline!
            const stillExists = allProjects.find(p => p.id === currentProject.id);
            if (stillExists) {
                selectLead(currentProject.id);
            } else {
                document.querySelector('.action-center').innerHTML = '<h4 class="text-muted py-5">Lead archived. Please select another.</h4>';
            }
        }
    } catch (error) {
        console.error("Save error:", error);
        alert("Backend Error: " + error.message);

        // Unlock UI so they can try again
        saveBtn.innerHTML = originalBtnHtml;
        saveBtn.classList.remove('disabled');
    }
}

// Timer Utils
function startTimer() { visitSeconds = 0; clearInterval(visitTimerInterval); visitTimerInterval = setInterval(() => { visitSeconds++; const t = document.getElementById('visit-timer'); if (t) t.textContent = formatTime(visitSeconds); }, 1000); }
function stopTimer() { clearInterval(visitTimerInterval); visitTimerInterval = null; }
function formatTime(sec) { return `${String(Math.floor(sec / 3600)).padStart(2, '0')}:${String(Math.floor((sec % 3600) / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`; }

document.addEventListener('DOMContentLoaded', loadHubData);

// 🚀 NEW: Futuristic Billing Status Dashboard
function updateActionCenterForExistingInvoice(inv) {
    const actionContainer = document.querySelector('.action-center');
    if (!actionContainer) return;

    // Grab the true status exactly like our timeline does
    const st = inv.invoice_status || inv.status || 'DRAFT';
    const statusStr = String(st).toUpperCase();

    // Logic for the glowing progress tracker
    let step1 = 'active', step2 = '', step3 = '';
    let badgeClass = 'bg-warning text-dark', statusText = 'PENDING ADMIN REVIEW';
    let glowColor = 'rgba(245, 158, 11, 0.3)'; // Neon Orange Glow

    if (statusStr === 'VERIFIED') {
        step2 = 'active';
        badgeClass = 'bg-success';
        statusText = 'VERIFIED - READY TO SEND';
        glowColor = 'rgba(16, 185, 129, 0.3)'; // Neon Green Glow
    } else if (statusStr === 'SENT' || statusStr === 'CONFIRMED') {
        step2 = 'active'; step3 = 'active';
        badgeClass = 'bg-primary';
        statusText = 'DISPATCHED TO CLIENT';
        glowColor = 'rgba(59, 130, 246, 0.3)'; // Neon Blue Glow
    } else if (statusStr === 'CANCELLED') {
        badgeClass = 'bg-danger';
        statusText = 'INVOICE CANCELLED';
        glowColor = 'rgba(239, 68, 68, 0.3)'; // Neon Red Glow
    }

    const html = `
        <div class="text-start p-4 rounded-4 position-relative overflow-hidden" style="background: linear-gradient(145deg, #0f172a, #1e293b); box-shadow: 0 10px 40px ${glowColor}; border: 1px solid #334155; transition: all 0.4s ease;">
            <div class="position-absolute" style="top: -60px; right: -60px; width: 180px; height: 180px; background: ${glowColor}; filter: blur(60px); border-radius: 50%;"></div>

            <div class="d-flex justify-content-between align-items-center mb-4 position-relative" style="z-index: 2;">
                <div class="d-flex align-items-center gap-3">
                    <div class="bg-white bg-opacity-10 p-3 rounded-circle d-flex align-items-center justify-content-center" style="width: 54px; height: 54px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1);">
                        <i class="bi bi-receipt text-white fs-4"></i>
                    </div>
                    <div>
                        <h5 class="fw-bold mb-0 text-white" style="letter-spacing: 0.5px;">Live Billing Tracker</h5>
                        <div class="small" style="color: #94a3b8; font-family: monospace; font-size: 0.8rem;">${inv.invoice_number || 'Processing...'}</div>
                    </div>
                </div>
                <span class="badge ${badgeClass} px-3 py-2 shadow-sm" style="font-size: 0.7rem; letter-spacing: 0.8px; border-radius: 8px;">${statusText}</span>
            </div>

            <div class="px-2 position-relative mb-4 mt-2" style="z-index: 2;">
                <div class="d-flex justify-content-between position-relative">
                    <div class="position-absolute" style="top: 16px; left: 10%; right: 10%; height: 2px; background: #334155; z-index: 0;"></div>
                    <div class="position-absolute" style="top: 16px; left: 10%; height: 2px; background: #fff; box-shadow: 0 0 10px #fff; z-index: 0; width: ${step3 ? '80%' : (step2 ? '40%' : '0%')}; transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);"></div>

                    <div class="text-center position-relative" style="width: 30%; z-index: 1;">
                        <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-2 shadow-lg" style="width: 34px; height: 34px; background: ${step1 ? '#fff' : '#1e293b'}; color: ${step1 ? '#0f172a' : '#64748b'}; border: 2px solid ${step1 ? '#fff' : '#334155'}; transition: all 0.4s ease;">
                            <i class="bi bi-file-earmark-plus-fill"></i>
                        </div>
                        <div class="small fw-bold text-uppercase" style="color: ${step1 ? '#f8fafc' : '#64748b'}; font-size: 0.65rem; letter-spacing: 1px;">Generated</div>
                    </div>

                    <div class="text-center position-relative" style="width: 30%; z-index: 1;">
                        <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-2 shadow-lg" style="width: 34px; height: 34px; background: ${step2 ? '#fff' : '#1e293b'}; color: ${step2 ? '#0f172a' : '#64748b'}; border: 2px solid ${step2 ? '#fff' : '#334155'}; transition: all 0.4s ease; transition-delay: 0.1s;">
                            <i class="bi bi-shield-check"></i>
                        </div>
                        <div class="small fw-bold text-uppercase" style="color: ${step2 ? '#f8fafc' : '#64748b'}; font-size: 0.65rem; letter-spacing: 1px;">Verified</div>
                    </div>

                    <div class="text-center position-relative" style="width: 30%; z-index: 1;">
                        <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-2 shadow-lg" style="width: 34px; height: 34px; background: ${step3 ? '#fff' : '#1e293b'}; color: ${step3 ? '#0f172a' : '#64748b'}; border: 2px solid ${step3 ? '#fff' : '#334155'}; transition: all 0.4s ease; transition-delay: 0.2s;">
                            <i class="bi bi-whatsapp"></i>
                        </div>
                        <div class="small fw-bold text-uppercase" style="color: ${step3 ? '#f8fafc' : '#64748b'}; font-size: 0.65rem; letter-spacing: 1px;">Dispatched</div>
                    </div>
                </div>
            </div>

            <div class="d-flex gap-2 position-relative" style="z-index: 2;">
                <button class="btn btn-light fw-bold flex-grow-1 shadow" style="border-radius: 10px; transition: transform 0.2s;" onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'" onclick="window.location.href='billing.html'">
                    Open Billing Dashboard <i class="bi bi-arrow-right ms-2"></i>
                </button>
            </div>
        </div>
    `;

    actionContainer.innerHTML = html;
}

// 🚀 NEW: Post-Sales Training & Onboarding Dashboard
function renderTrainingTracker(project, meetings = []) {
    const actionContainer = document.querySelector('.action-center');
    if (!actionContainer) return;

    // 1. Dynamically fetch the Assigned PM
    const pmName = project.project_manager_name || project.pm_name || 
                  (project.project_manager && (project.project_manager.name || project.project_manager.full_name)) || 
                  'Admin / Pending Assignment';

    // 2. Sort meetings oldest to newest
    const sortedMeetings = [...meetings].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // 3. Progress Math
    const targetSessions = 3; 
    let successCount = 0;
    let scheduledCount = 0;
    let nodes = [];

    // Build timeline nodes based on actual meetings
    sortedMeetings.forEach((m, idx) => {
        if (m.status === 'RESOLVED') {
            nodes.push({ num: idx + 1, label: 'Successful', color: '#10b981', icon: 'bi-check-lg', bg: '#ecfdf5', border: '#10b981' });
            successCount++;
        } else if (m.status === 'CANCELLED' || m.status === 'CANCEL') {
            nodes.push({ num: idx + 1, label: 'Rescheduled', color: '#ef4444', icon: 'bi-x-lg', bg: '#fef2f2', border: '#ef4444' });
        } else {
            nodes.push({ num: idx + 1, label: 'Scheduled', color: '#3b82f6', icon: 'bi-clock', bg: '#eff6ff', border: '#3b82f6' });
            scheduledCount++;
        }
    });

    // Add "Pending" nodes to guarantee we show the path to 3 successes
    let needed = targetSessions - successCount;
    let pendingToAdd = Math.max(0, needed - scheduledCount);

    for (let i = 0; i < pendingToAdd; i++) {
        nodes.push({ num: nodes.length + 1, label: 'Pending', color: '#94a3b8', icon: 'bi-dash', bg: '#f8fafc', border: '#cbd5e1' });
    }

    const isFullyOnboarded = successCount >= targetSessions;

    // 4. Generate the Progress Bar HTML
    let stepperHtml = `
        <div class="position-relative mb-5 mt-4 px-2">
            <div class="position-absolute" style="top: 16px; left: 8%; right: 8%; height: 3px; background: #e2e8f0; z-index: 0;"></div>

            <div class="d-flex justify-content-between position-relative" style="z-index: 1;">
    `;

    nodes.forEach(node => {
        stepperHtml += `
                <div class="text-center position-relative" style="flex: 1;">
                    <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-2 shadow-sm"
                         style="width: 34px; height: 34px; background: ${node.bg}; color: ${node.color}; border: 2px solid ${node.border}; transition: all 0.3s;">
                        <i class="bi ${node.icon} fw-bold"></i>
                    </div>
                    <div class="fw-bold text-uppercase" style="font-size: 0.65rem; color: ${node.color}; letter-spacing: 0.5px;">${node.label}</div>
                    <div class="text-muted" style="font-size: 0.6rem; font-weight: 700;">Sess ${node.num}</div>
                </div>
        `;
    });

    stepperHtml += `
            </div>
        </div>
    `;

    // 5. Build the Full UI
    let html = `
        <div class="text-start p-4 rounded-4 shadow-sm" style="background: #ffffff; border: 1px solid #e2e8f0;">
            <div class="d-flex justify-content-between align-items-center mb-2 pb-3 border-bottom">
                <div>
                    <h5 class="fw-bold mb-1" style="color: #0f172a;">
                        <i class="bi bi-rocket-takeoff text-primary me-2"></i>Client Onboarding Tracker
                    </h5>
                    <div class="small text-muted fw-medium">
                        <i class="bi bi-person-badge me-1"></i>Assigned Manager: <span class="text-dark fw-bold">${pmName}</span>
                    </div>
                </div>
                <div class="text-end">
                    <div class="badge ${isFullyOnboarded ? 'bg-success' : 'bg-primary'} bg-opacity-10 text-${isFullyOnboarded ? 'success' : 'primary'} border border-${isFullyOnboarded ? 'success' : 'primary'} px-3 py-2 rounded-pill" style="font-size: 0.75rem; letter-spacing: 0.5px;">
                        <i class="bi ${isFullyOnboarded ? 'bi-check-circle-fill' : 'bi-arrow-repeat'} me-1"></i>
                        ${isFullyOnboarded ? 'ONBOARDING COMPLETE' : `${successCount} / ${targetSessions} SESSIONS DONE`}
                    </div>
                </div>
            </div>

            ${stepperHtml}

            <div class="sessions-container mt-3">
    `;

    let sessionCounter = 1;
    let hasPendingSchedule = false;

    // 6. Render the List of Meetings
    sortedMeetings.forEach((m) => {
        const dateStr = new Date(m.date).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
        
        let statusClass = 'scheduled';
        let icon = 'bi-calendar-event';
        let statusBadge = `<span class="badge bg-primary bg-opacity-10 text-primary border border-primary"><i class="bi bi-clock me-1"></i>Scheduled</span>`;
        
        if (m.status === 'RESOLVED') {
            statusClass = 'completed'; icon = 'bi-check-lg';
            statusBadge = `<span class="badge bg-success text-white"><i class="bi bi-check2-all me-1"></i>Completed</span>`;
        } else if (m.status === 'CANCELLED' || m.status === 'CANCEL') {
            statusClass = 'cancelled'; icon = 'bi-x-lg';
            statusBadge = `<span class="badge bg-danger text-white"><i class="bi bi-x-circle me-1"></i>Cancelled</span>`;
        } else {
            hasPendingSchedule = true;
        }

        html += `
            <div class="training-card ${statusClass} shadow-sm">
                <div class="d-flex align-items-center justify-content-between">
                    <div class="d-flex align-items-center gap-3">
                        <div class="session-icon"><i class="bi ${icon}"></i></div>
                        <div>
                            <h6 class="fw-bold mb-1" style="color: #1e293b;">Session ${sessionCounter}: ${m.title || 'Product Training'}</h6>
                            <div class="small text-muted"><i class="bi bi-camera-video me-1"></i>${m.meeting_type || 'Virtual'} • ${dateStr}</div>
                        </div>
                    </div>
                    <div>${statusBadge}</div>
                </div>
            </div>
        `;
        sessionCounter++;
    });

    // 7. Render Next Available Slot
    if (!isFullyOnboarded && !hasPendingSchedule) {
        html += `
            <div class="training-card pending d-flex align-items-center justify-content-between">
                <div class="d-flex align-items-center gap-3">
                    <div class="session-icon"><i class="bi bi-calendar-plus"></i></div>
                    <div>
                        <h6 class="fw-bold mb-1 text-dark">Session ${sessionCounter}: Pending Schedule</h6>
                        <div class="small text-muted">Awaiting PM Availability</div>
                    </div>
                </div>
                <button class="btn btn-primary fw-bold shadow-sm" onclick="openTrainingScheduleModal(${project.id})">
                    <i class="bi bi-calendar-plus me-2"></i>Schedule Session
                </button>
            </div>
        `;
    }

    // 8. Optional 4th+ Session
    if (isFullyOnboarded && !hasPendingSchedule) {
        html += `
            <div class="text-center mt-4 pt-3 border-top">
                <p class="text-muted small mb-2"><i class="bi bi-info-circle me-1"></i>Client has completed the mandatory 3 sessions.</p>
                <button class="btn btn-outline-secondary btn-sm fw-bold rounded-pill px-4" onclick="openTrainingScheduleModal(${project.id})">
                    <i class="bi bi-plus-lg me-1"></i>Schedule Optional Session ${sessionCounter}
                </button>
            </div>
        `;
    }

    html += `
            </div> 
        </div>
    `;

    actionContainer.innerHTML = html;
}