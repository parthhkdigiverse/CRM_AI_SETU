// Access Control UI/UX
const ROLES = ['ADMIN','SALES','TELESALES','PROJECT_MANAGER','PROJECT_MANAGER_AND_SALES'];
const rolePages = {
  ADMIN: ['*'],
  SALES: ['dashboard.html','leads.html','billing.html'],
  TELESALES: ['dashboard.html','leads.html'],
  PROJECT_MANAGER: ['dashboard.html','projects.html'],
  PROJECT_MANAGER_AND_SALES: ['dashboard.html','leads.html','projects.html']
};
const ACTIONS = [
  { name: 'Issue Create', sub: 'Create new issues' },
  { name: 'Issue Edit', sub: 'Modify existing issues' },
  { name: 'Issue Delete', sub: 'Remove issues permanently' },
  { name: 'Lead Create', sub: 'Add new leads' },
  { name: 'Lead Edit', sub: 'Update lead details' },
  { name: 'Invoice Generate', sub: 'Generate and send invoices' },
  { name: 'Report Export', sub: 'Export data reports' }
];
const actionMatrix = {};
ACTIONS.forEach(a => {
  actionMatrix[a.name] = {
    ADMIN: true,
    SALES: true,
    TELESALES: false,
    PROJECT_MANAGER: false,
    PROJECT_MANAGER_AND_SALES: true
  };
});

function renderRoleChips() {
  const container = document.querySelector('.role-list');
  if (!container) return;
  container.innerHTML = '';
  ROLES.forEach(role => {
    const chip = document.createElement('div');
    chip.className = 'role-chip';
    chip.textContent = role.replace(/_/g,' ');
    chip.dataset.role = role;
    chip.addEventListener('click', () => {
      document.querySelectorAll('.role-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      renderPageChips(role);
      renderMatrix(role);
      // Force UI update for ADMIN
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
  container.firstChild.classList.add('active');
  renderPageChips(ROLES[0]);
  renderMatrix(ROLES[0]);
  // Force UI update for ADMIN on initial load
  const select = document.getElementById('add-page-select');
  const addBtn = document.getElementById('btn-add-page');
  if (ROLES[0] === 'ADMIN') {
    if (select) select.disabled = true;
    if (addBtn) addBtn.disabled = true;
  } else {
    if (select) select.disabled = false;
    if (addBtn) addBtn.disabled = false;
  }
}

function renderPageChips(role) {
  const list = document.getElementById('page-chip-list');
  const select = document.getElementById('add-page-select');
  const addBtn = document.getElementById('btn-add-page');
  if (!list) return;
  list.innerHTML = '';
  if (role === 'ADMIN') {
    // Always show * chip for ADMIN, disable dropdown and add button
    const chip = document.createElement('div');
    chip.className = 'page-chip';
    chip.textContent = '*';
    chip.title = 'Full access';
    list.appendChild(chip);
    if (select) select.disabled = true;
    if (addBtn) addBtn.disabled = true;
  } else {
    if (select) select.disabled = false;
    if (addBtn) addBtn.disabled = false;
    (rolePages[role]||[]).forEach(page => {
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

document.getElementById('btn-add-page').addEventListener('click', () => {
  const role = document.querySelector('.role-chip.active').dataset.role;
  const select = document.getElementById('add-page-select');
  const val = select.value;
  if (val && !rolePages[role].includes(val)) {
    rolePages[role].push(val);
    renderPageChips(role);
  }
  select.value = '';
});

function renderMatrix(role) {
  const body = document.getElementById('matrix-body');
  if (!body) return;
  body.innerHTML = '';
  ACTIONS.forEach(action => {
    const row = document.createElement('tr');
    const tdAction = document.createElement('td');
    tdAction.innerHTML = `<div class="matrix-action-name">${action.name}</div><div class="matrix-action-sub">${action.sub}</div>`;
    row.appendChild(tdAction);
    ROLES.forEach(r => {
      const td = document.createElement('td');
      const cell = document.createElement('div');
      cell.className = 'matrix-cell';
      const toggle = document.createElement('div');
      toggle.className = 'matrix-toggle';
      if (r === 'ADMIN') {
        toggle.classList.add('matrix-toggle--lock');
        toggle.innerHTML = '<svg width="9" height="9" viewBox="0 0 16 16" fill="none" stroke="#9ca3af" stroke-width="1.8" stroke-linecap="round"><rect x="4" y="7" width="8" height="6" rx="1.2"/><path d="M6 7V5a2 2 0 014 0v2"/></svg>';
      } else {
        if (actionMatrix[action.name][r]) {
          toggle.classList.add('matrix-toggle--on');
          toggle.innerHTML = '<svg width="10" height="10" viewBox="0 0 9 9" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round"><path d="M1.5 4.5l2 2 4-4"/></svg>';
        }
        toggle.addEventListener('click', () => {
          actionMatrix[action.name][r] = !actionMatrix[action.name][r];
          renderMatrix(role);
        });
      }
      cell.appendChild(toggle);
      td.appendChild(cell);
      row.appendChild(td);
    });
    body.appendChild(row);
  });
}

document.getElementById('btn-save-access').addEventListener('click', () => {
  const btn = document.getElementById('btn-save-access');
  btn.textContent = 'Saving...';
  btn.disabled = true;
  fetch('/api/settings/access-control', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rolePages, actionMatrix })
  })
  .then(r => r.json())
  .then(() => {
    btn.textContent = 'Saved!';
    setTimeout(() => { btn.textContent = 'Save Access Policy'; btn.disabled = false; }, 1800);
  })
  .catch(() => {
    btn.textContent = 'Error — try again';
    btn.disabled = false;
  });
});

document.addEventListener('DOMContentLoaded', function() {
  // Load from backend first
  fetch('/api/settings/access-control')
    .then(r => r.json())
    .then(data => {
      if (data && data.rolePages && data.actionMatrix) {
        // Overwrite local data with backend data
        Object.keys(rolePages).forEach(k => delete rolePages[k]);
        Object.assign(rolePages, data.rolePages);
        Object.keys(actionMatrix).forEach(k => delete actionMatrix[k]);
        Object.assign(actionMatrix, data.actionMatrix);
      }
    })
    .catch(() => {/* fallback to defaults */})
    .finally(() => {
      renderRoleChips();
      // Remove all previous event listeners by replacing the elements
      const addBtnOld = document.getElementById('btn-add-page');
      const addBtnNew = addBtnOld.cloneNode(true);
      addBtnOld.parentNode.replaceChild(addBtnNew, addBtnOld);
      const saveBtnOld = document.getElementById('btn-save-access');
      const saveBtnNew = saveBtnOld.cloneNode(true);
      saveBtnOld.parentNode.replaceChild(saveBtnNew, saveBtnOld);

      addBtnNew.addEventListener('click', () => {
        const role = document.querySelector('.role-chip.active').dataset.role;
        const select = document.getElementById('add-page-select');
        const val = select.value;
        if (val && !rolePages[role].includes(val)) {
          rolePages[role].push(val);
          renderPageChips(role);
          renderMatrix(role);
        }
        select.value = '';
      });

      saveBtnNew.addEventListener('click', () => {
        saveBtnNew.textContent = 'Saving...';
        saveBtnNew.disabled = true;
        fetch('/api/settings/access-control', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rolePages, actionMatrix })
        })
        .then(r => r.json())
        .then(() => {
          saveBtnNew.textContent = 'Saved!';
          setTimeout(() => { saveBtnNew.textContent = 'Save Access Policy'; saveBtnNew.disabled = false; }, 1800);
        })
        .catch(() => {
          saveBtnNew.textContent = 'Error — try again';
          saveBtnNew.disabled = false;
        });
      });
    });
});
