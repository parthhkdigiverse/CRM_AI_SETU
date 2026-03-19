// Access Control UI/UX - Refactored for CRM AI SETU
const ROLES = ['ADMIN', 'SALES', 'TELESALES', 'PROJECT_MANAGER', 'PROJECT_MANAGER_AND_SALES'];

// UI State
let rolePages = {
    ADMIN: ['*'],
    SALES: [],
    TELESALES: [],
    PROJECT_MANAGER: [],
    PROJECT_MANAGER_AND_SALES: []
};

const ACTIONS = [
    { key: 'issue_create_roles', name: 'Issue Create', sub: 'Create new issues' },
    { key: 'issue_manage_roles', name: 'Issue Manage', sub: 'View/Edit all issues' },
    { key: 'invoice_creator_roles', name: 'Invoice Create', sub: 'Generate new invoices' },
    { key: 'invoice_verifier_roles', name: 'Invoice Verify', sub: 'Verify/Send invoices' },
    { key: 'leave_apply_roles', name: 'Leave Apply', sub: 'Apply for own leaves' },
    { key: 'leave_manage_roles', name: 'Leave Manage', sub: 'Approve/Reject leaves' },
    { key: 'salary_manage_roles', name: 'Salary Manage', sub: 'Manage employee salaries' },
    { key: 'incentive_manage_roles', name: 'Incentive Manage', sub: 'Configure incentive slabs' },
    { key: 'employee_manage_roles', name: 'Employee Manage', sub: 'Add/Edit/Delete employees' }
];

let actionMatrix = {};

// Initialize matrix
ACTIONS.forEach(a => {
    actionMatrix[a.key] = {};
    ROLES.forEach(r => {
        actionMatrix[a.key][r] = (r === 'ADMIN');
    });
});

function renderRoleChips() {
    const container = document.querySelector('.role-list');
    if (!container) return;
    container.innerHTML = '';
    ROLES.forEach((role, idx) => {
        const chip = document.createElement('div');
        chip.className = 'role-chip' + (idx === 0 ? ' active' : '');
        chip.textContent = role.replace(/_/g, ' ');
        chip.dataset.role = role;
        chip.addEventListener('click', () => {
            document.querySelectorAll('.role-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            renderPageChips(role);
            renderMatrix(role);
            
            const select = document.getElementById('add-page-select');
            const addBtn = document.getElementById('btn-add-page');
            if (role === 'ADMIN') {
                if (select) select.disabled = true;
                if (addBtn) addBtn.disabled = true;
            } else {
                if (select) select.disabled = false;
                if (addBtn) addBtn.disabled = false;
            }
        });
        container.appendChild(chip);
    });
    
    // Initial render for first role (ADMIN usually)
    const firstRole = ROLES[0];
    renderPageChips(firstRole);
    renderMatrix(firstRole);
}

function renderPageChips(role) {
    const list = document.getElementById('page-chip-list');
    if (!list) return;
    list.innerHTML = '';
    
    if (role === 'ADMIN') {
        const chip = document.createElement('div');
        chip.className = 'page-chip';
        chip.textContent = '*';
        chip.title = 'Full access';
        list.appendChild(chip);
    } else {
        (rolePages[role] || []).forEach(page => {
            const chip = document.createElement('div');
            chip.className = 'page-chip';
            chip.textContent = page;
            chip.title = 'Click to remove';
            chip.addEventListener('click', () => {
                rolePages[role] = rolePages[role].filter(p => p !== page);
                renderPageChips(role);
            });
            list.appendChild(chip);
        });
    }
}

function renderMatrix(activeRole) {
    const body = document.getElementById('matrix-body');
    if (!body) return;
    body.innerHTML = '';
    
    ACTIONS.forEach(action => {
        const row = document.createElement('tr');
        const tdAction = document.createElement('td');
        tdAction.innerHTML = `<div class="matrix-action-name">${action.name}</div><div class="matrix-action-sub">${action.sub}</div>`;
        row.appendChild(tdAction);
        
        ROLES.forEach(role => {
            const td = document.createElement('td');
            const cell = document.createElement('div');
            cell.className = 'matrix-cell';
            const toggle = document.createElement('div');
            toggle.className = 'matrix-toggle';
            
            if (role === 'ADMIN') {
                toggle.classList.add('matrix-toggle--lock');
                toggle.innerHTML = '<svg width="9" height="9" viewBox="0 0 16 16" fill="none" stroke="#9ca3af" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="7" width="8" height="6" rx="1.2"/><path d="M6 7V5a2 2 0 014 0v2"/></svg>';
            } else {
                if (actionMatrix[action.key][role]) {
                    toggle.classList.add('matrix-toggle--on');
                    toggle.innerHTML = '<svg width="10" height="10" viewBox="0 0 9 9" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round"><path d="M1.5 4.5l2 2 4-4"/></svg>';
                }
                toggle.addEventListener('click', () => {
                    actionMatrix[action.key][role] = !actionMatrix[action.key][role];
                    renderMatrix(activeRole);
                });
            }
            cell.appendChild(toggle);
            td.appendChild(cell);
            row.appendChild(td);
        });
        body.appendChild(row);
    });
}

async function loadAccessConfig() {
    try {
        const data = await ApiClient.getAccessPolicy();
        if (data && data.page_access) {
            rolePages = data.page_access;
        }
        if (data && data.feature_access) {
            // Convert backend feature_access (object of lists) to UI actionMatrix (object of objects)
            ACTIONS.forEach(action => {
                const rolesWithAccess = data.feature_access[action.key] || [];
                ROLES.forEach(role => {
                    actionMatrix[action.key][role] = rolesWithAccess.includes(role);
                });
            });
        }
    } catch (err) {
        console.warn('Failed to load access policy, using defaults', err);
    } finally {
        renderRoleChips();
    }
}

async function saveAccessConfig() {
    const btn = document.getElementById('btn-save-access');
    const msg = document.getElementById('access-policy-save-msg');
    
    // Preparation: UI actionMatrix -> Backend feature_access
    const featureAccess = {};
    ACTIONS.forEach(action => {
        featureAccess[action.key] = ROLES.filter(r => actionMatrix[action.key][r]);
    });

    const payload = {
        page_access: rolePages,
        feature_access: featureAccess
    };

    try {
        if (typeof toggleLoading === 'function') {
            toggleLoading('btn-save-access', 'spn-save-access', 'icon-save-access', true);
        } else {
            btn.disabled = true;
            btn.textContent = 'Saving...';
        }

        await ApiClient.updateAccessPolicy(payload);
        
        if (msg) {
            msg.textContent = 'Saved!';
            msg.classList.remove('d-none');
            setTimeout(() => msg.classList.add('d-none'), 2500);
        }
        if (typeof showToast === 'function') showToast('Access policy saved');

    } catch (err) {
        console.error('Save failed', err);
        if (typeof showToast === 'function') {
            showToast(err.data?.detail || err.message || 'Failed to save access policy', true);
        }
    } finally {
        if (typeof toggleLoading === 'function') {
            toggleLoading('btn-save-access', 'spn-save-access', 'icon-save-access', false);
        } else {
            btn.disabled = false;
            btn.textContent = 'Save Access Policy';
        }
    }
}

// Initial Wireup
document.addEventListener('DOMContentLoaded', () => {
    // Add page logic
    const addBtn = document.getElementById('btn-add-page');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            const activeChip = document.querySelector('.role-chip.active');
            if (!activeChip) return;
            const role = activeChip.dataset.role;
            const select = document.getElementById('add-page-select');
            const val = select.value;
            if (val && !rolePages[role].includes(val)) {
                rolePages[role].push(val);
                renderPageChips(role);
            }
            select.value = '';
        });
    }

    // Save logic
    const saveBtn = document.getElementById('btn-save-access');
    if (saveBtn) {
        // Remove direct onclick if any (we already did this in settings.html)
        saveBtn.addEventListener('click', saveAccessConfig);
    }

    loadAccessConfig();
});
