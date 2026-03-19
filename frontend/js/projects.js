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
        allProjects = (res || []).map(p => ({
            ...p,
            pipeline_stage: p.pipeline_stage || p.status || 'LEAD',
            assignment_status: p.assignment_status || 'PENDING',
            name: p.name || p.shop_name || 'Unnamed Client',
            area_name: p.area_name || (p.area && p.area.name) || 'No Area Assigned',
            contact_person: p.contact_person || 'No Contact Person',
            phone: p.phone || 'No Phone'
        }));
        populatePmFilterDropdown();
        filterQueue();
        if (allProjects.length > 0 && !currentProject) selectLead(allProjects[0].id);
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
    } else {
        actionContainer.innerHTML = `<div class="text-center py-4"><h4 class="fw-bold">${project.pipeline_stage} Stage</h4></div>`;
    }
}

async function loadVisitHistory(shopId) {
    const historyContainer = document.getElementById('visit-history-section');
    if (!historyContainer) return;

    historyContainer.innerHTML = '<div class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm me-2"></span>Loading visit history...</div>';

    try {
        const visits = await window.ApiClient.request(`/visits/?shop_id=${shopId}`);
        let totalInteractions = visits ? visits.length : 0;
        let demoCardHtml = '';

        // 1. Virtual Card for UPCOMING Demos only
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
                    <span class="text-muted small">No past visits or demos recorded for this lead yet.</span>
                </div>`;
            return;
        }

        const visitCountText = totalInteractions > 1 ? `${totalInteractions} Interactions` : `1 Interaction`;
        let html = `
            <div class="d-flex align-items-center mb-3">
                <h6 class="fw-bold mb-0 text-uppercase" style="letter-spacing: 0.5px; font-size: 0.8rem; color: #64748b;">Past Interactions</h6>
                <span class="badge bg-primary text-white rounded-pill ms-2 shadow-sm" style="font-size: 0.65rem; padding: 0.35em 0.65em;">${visitCountText}</span>
            </div>`;

        html += demoCardHtml; // Inject upcoming demo at the top

        // 3. Render Historical Visits & Completed Demos
        if (visits && visits.length > 0) {
            visits.forEach(v => {
                const visitDate = new Date(v.visit_date).toLocaleString('en-IN', {
                    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
                });
                const repName = v.user_name || (v.user && (v.user.full_name || v.user.name)) || 'Unknown Rep';

                // 🚀 NEW: Special green card for completed demos logged by the backend!
                if (v.status === 'COMPLETED') {
                    html += `
                        <div class="card mb-3 border-0 shadow-sm" style="border-radius: 12px; overflow: hidden; background: linear-gradient(to right, #f0fdf4, #dcfce7); border-left: 4px solid #10b981 !important;">
                            <div class="card-body p-4">
                                <div class="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <h6 class="fw-bold mb-1" style="color: #047857;"><i class="bi bi-display me-1"></i> Product Demo Completed</h6>
                                        <div class="text-muted small mb-1"><i class="bi bi-calendar3 me-1"></i>${visitDate}</div>
                                        <div class="text-muted mt-2" style="font-size: 0.8rem;"><i class="bi bi-person-check text-secondary me-1"></i>Hosted by PM: <span class="fw-bold text-dark">${repName}</span></div>
                                    </div>
                                    <span class="badge bg-success shadow-sm"><i class="bi bi-check-circle-fill me-1"></i>Done</span>
                                </div>
                            </div>
                        </div>`;
                    return; // Skip drawing the regular visit layout
                }

                // Standard Field Visit Layout
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
                                    <div class="text-muted small mb-1"><i class="bi bi-calendar3 me-1"></i>${visitDate}</div>
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
            });
        }
        historyContainer.innerHTML = html;
    } catch (error) {
        console.error("Failed to load history:", error);
        historyContainer.innerHTML = '<div class="text-center text-danger py-3 small"><i class="bi bi-exclamation-triangle me-1"></i> Could not load visit history.</div>';
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
