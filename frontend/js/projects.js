// frontend/js/projects.js

requireAuth();
const sidebarElement = document.getElementById('sidebar');
if (sidebarElement) sidebarElement.innerHTML = renderSidebar('projects');

// --- State Management ---
let allProjects = [];
let currentProject = null;
let visitTimerInterval = null;
let visitSeconds = 0;
let cameraStream = null;

let currentSearch = "";
let currentFilter = "ALL";

// --- 1. Master Init & Data Fetching ---
async function loadHubData() {
    document.getElementById('queue-list').innerHTML = `<div class="p-4 text-center text-muted"><div class="spinner-border spinner-border-sm mb-2"></div><br>Loading pipeline...</div>`;
    try {
        const res = await window.ApiClient.request('/shops/');

        allProjects = (res || []).map(p => ({
            ...p,
            pipeline_stage: p.pipeline_stage || p.status || 'LEAD',
            name: p.name || p.shop_name || 'Unnamed Client',
            area_name: p.area_name || (p.area && p.area.name) || 'No Area Assigned',
            contact_person: p.contact_person || 'No Contact Person',
            phone: p.phone || 'No Phone'
        }));

        filterQueue(); // Renders the queue based on default filters

        if (allProjects.length > 0) selectLead(allProjects[0].id);
    } catch (err) {
        console.error("Failed to load hub data:", err);
        document.getElementById('queue-list').innerHTML = `<div class="p-3 text-danger text-center"><i class="bi bi-exclamation-triangle"></i> Failed to load data</div>`;
    }
}

// --- 2. Search & Filtering ---
function handleSearch(e) {
    currentSearch = e.target.value.toLowerCase();
    filterQueue();
}

function setFilter(filterType, element) {
    currentFilter = filterType;
    // Update UI pill classes
    document.querySelectorAll('.filter-pill').forEach(el => {
        el.classList.remove('bg-dark', 'text-white');
        el.classList.add('bg-light', 'text-dark', 'border');
    });
    element.classList.remove('bg-light', 'text-dark', 'border');
    element.classList.add('bg-dark', 'text-white');
    filterQueue();
}

function filterQueue() {
    let filtered = allProjects.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(currentSearch) ||
            p.contact_person.toLowerCase().includes(currentSearch) ||
            p.phone.includes(currentSearch);
        let matchesFilter = true;
        if (currentFilter === 'IN_PROGRESS') {
            matchesFilter = (p.pipeline_stage === 'PITCHING');
        } else if (currentFilter === 'DEMO_SET') {
            matchesFilter = (p.demo_scheduled_at != null || p.pipeline_stage === 'NEGOTIATION');
        }
        return matchesSearch && matchesFilter;
    });
    renderQueue(filtered);
}

// --- 3. Render Left Queue ---
function renderQueue(projects) {
    const queueEl = document.getElementById('queue-list');
    if (projects.length === 0) {
        queueEl.innerHTML = `<div class="p-4 text-center text-muted">No matching leads found.</div>`;
        return;
    }

    let html = '';
    projects.forEach(p => {
        let badgeColor = "bg-secondary";
        if (p.pipeline_stage === "LEAD") badgeColor = "bg-primary";
        if (p.pipeline_stage === "PITCHING") badgeColor = "bg-warning text-dark";
        if (p.pipeline_stage === "NEGOTIATION") badgeColor = "bg-info text-dark";
        if (p.pipeline_stage === "DELIVERY") badgeColor = "bg-success";

        html += `
                <div class="lead-card" id="card-${p.id}" onclick="selectLead(${p.id})">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="badge ${badgeColor}" style="font-size:0.65rem;">${p.pipeline_stage}</span>
                        <span class="text-muted" style="font-size:0.7rem;">ID: ${p.id}</span>
                    </div>
                    <div class="fw-bold text-dark">${p.name}</div>
                    <div class="small text-muted mb-2"><i class="bi bi-geo-alt me-1"></i>${p.area_name}</div>
                </div>`;
    });
    queueEl.innerHTML = html;
}

// --- 4. Handle Selection & Dynamic UI ---
function selectLead(id) {
    document.querySelectorAll('.lead-card').forEach(c => c.classList.remove('active'));
    const selectedCard = document.getElementById(`card-${id}`);
    if (selectedCard) selectedCard.classList.add('active');

    currentProject = allProjects.find(p => p.id === id);
    if (!currentProject) return;

    // Inject Real Data
    document.getElementById('detail-title').innerText = currentProject.name;
    document.getElementById('detail-contact').innerText = `Contact: ${currentProject.contact_person} • ${currentProject.phone}`;

    renderProgressBar(currentProject.pipeline_stage);
    renderActionCenter(currentProject);
}

function renderProgressBar(stage) {
    const stages = ["LEAD", "PITCHING", "NEGOTIATION", "DELIVERY", "MAINTENANCE"];
    const currentIndex = stages.indexOf(stage) >= 0 ? stages.indexOf(stage) : 0;
    let html = '';
    stages.forEach((s, index) => {
        let statusClass = index < currentIndex ? "completed" : (index === currentIndex ? "active" : "");
        html += `
                <div class="step ${statusClass}">
                    <div class="step-circle">${index < currentIndex ? '<i class="bi bi-check-lg"></i>' : index + 1}</div>
                    <div class="step-label">${s}</div>
                </div>`;
    });
    document.querySelector('.progress-tracker').innerHTML = html;
}

// --- 5. THE ACTION ENGINE (Morphing Panel) ---
function renderActionCenter(project) {
    const actionContainer = document.querySelector('.action-center');
    stopCamera();

    // If timer is already running for THIS project, keep showing the timer UI
    if (visitTimerInterval) {
        showActiveTimerUI();
        return;
    }

    if (project.pipeline_stage === "LEAD") {
        actionContainer.innerHTML = `
                    <div class="text-center py-4">
                        <div class="mb-3"><i class="bi bi-inbox text-primary" style="font-size: 3rem;"></i></div>
                        <h4 class="fw-bold">New Lead Assigned</h4>
                        <div class="d-flex justify-content-center gap-3 mt-4">
                            <button class="btn btn-outline-danger px-4 fw-semibold">Reject</button>
                            <button class="btn btn-primary px-4 fw-semibold" onclick="openCameraView('environment')"><i class="bi bi-play-circle me-2"></i>Start Visit (Take Photo)</button>
                        </div>
                    </div>`;
    } else if (project.pipeline_stage === "PITCHING") {
        actionContainer.innerHTML = `
                    <div class="text-center py-4">
                        <div class="mb-3"><i class="bi bi-calendar-check text-warning" style="font-size: 3rem;"></i></div>
                        <h4 class="fw-bold">Pitching & Demo</h4>
                        <div class="d-flex justify-content-center gap-3 mt-4">
                            <button class="btn btn-warning text-dark px-4 fw-bold"><i class="bi bi-calendar-plus me-2"></i>Schedule Demo</button>
                            <button class="btn btn-outline-dark px-4 fw-semibold" onclick="openCameraView('environment')"><i class="bi bi-person-walking me-2"></i>Log Follow-up Visit</button>
                        </div>
                    </div>`;
    } else {
        actionContainer.innerHTML = `<div class="text-center py-4"><h4 class="fw-bold">${project.pipeline_stage} Stage</h4></div>`;
    }
}

// --- 6. The Hardware Controllers (Camera & Timer) ---

// Step A: Open Camera to Start Visit
function openCameraView(facingMode) {
    const actionContainer = document.querySelector('.action-center');
    const isStart = facingMode === 'environment';

    actionContainer.innerHTML = `
                <div class="text-center">
                    <h5 class="fw-bold">${isStart ? "Step 1: Capture Storefront" : "Final Step: Capture Selfie"}</h5>
                    <p class="text-muted mb-3">${isStart ? "Take a photo to officially start the visit timer." : "Take a selfie to verify visit completion."}</p>
                    <div class="camera-wrapper mx-auto mb-3" style="max-width: 400px; border-radius: 12px; overflow: hidden; background: #000; position: relative;">
                        <video id="camera-preview" autoplay playsinline style="width: 100%; height: auto; display: block;"></video>
                    </div>
                    <button class="btn btn-${isStart ? 'primary' : 'success'} fw-bold px-4 py-2" onclick="${isStart ? 'snapStorefrontAndStart()' : 'snapSelfieAndFinish()'}">
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
        console.error("Camera denied", err);
        alert("Please enable camera permissions.");
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
}

// Step B: Photo taken, close camera, start timer running in background
function snapStorefrontAndStart() {
    stopCamera();
    startTimer();
    showActiveTimerUI();
}

// Step C: The Active Timer UI (No Camera)
function showActiveTimerUI() {
    const actionContainer = document.querySelector('.action-center');
    actionContainer.innerHTML = `
                <div class="text-center py-3">
                    <div class="mb-2"><span class="live-indicator"></span><span class="text-danger fw-bold text-uppercase" style="letter-spacing: 1px; font-size: 0.8rem;">Meeting In Progress</span></div>
                    <div class="timer-display" id="visit-timer">00:00:00</div>
                    <p class="text-muted mb-4"><i class="bi bi-check-circle-fill text-success me-1"></i> Storefront photo saved. Timer is running in the background.</p>
                    <button class="btn btn-danger fw-bold px-4 py-2" onclick="openCameraView('user')">
                        <i class="bi bi-stop-circle me-2"></i>End Visit (Take Selfie)
                    </button>
                </div>`;
}

// Step D: Finish Visit
function snapSelfieAndFinish() {
    stopCamera();
    stopTimer();

    document.querySelector('.action-center').innerHTML = `
                <div class="text-center py-4">
                    <h5 class="fw-bold mb-3">Visit Completed!</h5>
                    <p class="text-muted">Duration: <span class="fw-bold text-dark">${formatTime(visitSeconds)}</span></p>
                    <div class="mx-auto" style="max-width: 300px;">
                        <select class="form-select mb-3" id="visit-outcome">
                            <option value="SATISFIED">Outcome: Satisfied / Positive</option>
                            <option value="TAKE_TIME_TO_THINK">Outcome: Needs Time to Think</option>
                            <option value="DECLINE">Outcome: Declined</option>
                        </select>
                        <button class="btn btn-success fw-bold w-100" onclick="submitFinalVisit()"><i class="bi bi-cloud-arrow-up me-2"></i>Save to Database</button>
                    </div>
                </div>
            `;
}

function submitFinalVisit() {
    alert(`Visit saved!\nOutcome: ${document.getElementById('visit-outcome').value}\nDuration: ${formatTime(visitSeconds)}`);
    // Phase 3: POST to API here
    renderActionCenter(currentProject);
}

// --- 7. Timer Utilities ---
function startTimer() {
    visitSeconds = 0;
    clearInterval(visitTimerInterval);
    visitTimerInterval = setInterval(() => {
        visitSeconds++;
        const timerEl = document.getElementById('visit-timer');
        if (timerEl) timerEl.textContent = formatTime(visitSeconds);
    }, 1000);
}

function stopTimer() {
    clearInterval(visitTimerInterval);
    visitTimerInterval = null;
}

function formatTime(totalSeconds) {
    const h = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
    const s = String(totalSeconds % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
}

// --- Boot Up ---
document.addEventListener('DOMContentLoaded', loadHubData);
