// ApiClient initialization for dynamic configuration
window.API = window.location.origin + '/api';

class ApiClient {
    static API_BASE_URL = window.API;
    static _configParsed = false;

    static async initConfig() {
        if (this._configParsed) return;
        try {
            const r = await fetch(window.location.origin + '/api/config');
            const data = await r.json();
            if (data.API_BASE_URL) {
                this.API_BASE_URL = data.API_BASE_URL;
                // Sync with global for legacy compatibility
                window.API = data.API_BASE_URL;
            }
            this._configParsed = true;
        } catch (e) {
            console.warn('Using default API_BASE_URL due to config fetch error:', e);
            this._configParsed = true;
        }
    }

    static getAccessToken() {
        return sessionStorage.getItem('access_token');
    }

    static getRefreshToken() {
        return sessionStorage.getItem('refresh_token');
    }

    static setTokens(accessToken, refreshToken) {
        sessionStorage.setItem('access_token', accessToken);
        if (refreshToken) {
            sessionStorage.setItem('refresh_token', refreshToken);
        }
    }

    static clearTokens() {
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('refresh_token');
        sessionStorage.removeItem('srm_user');
        sessionStorage.removeItem('current_user');
    }

    static setCurrentUser(user) {
        sessionStorage.setItem('srm_user', JSON.stringify(user));
    }

    static getCurrentUser() {
        try { return JSON.parse(sessionStorage.getItem('srm_user')); } catch { return null; }
    }

    static async request(path, options = {}) {
        if (!this._configParsed) await this.initConfig();
        const url = `${this.API_BASE_URL}${path}`;
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        const token = this.getAccessToken();
        if (token && !options.noAuth) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            method: options.method || 'GET',
            headers,
        };

        if (options.body instanceof FormData) {
            config.body = options.body;
            delete headers['Content-Type']; // Let browser set boundary
        } else if (options.body && typeof options.body !== 'string') {
            config.body = JSON.stringify(options.body);
        } else if (options.body) {
            config.body = options.body;
        }

        try {
            let response = await fetch(url, config);

            // If we successfully get a response, hide offline banner if it exists
            if (window.showOfflineBanner) window.showOfflineBanner(false);

            // Handle token expiry transparently
            if (response.status === 401 && !options.isRetry && this.getRefreshToken()) {
                const refreshed = await this.refreshTokens();
                if (refreshed) {
                    options.isRetry = true;
                    options.headers = { ...options.headers, 'Authorization': `Bearer ${this.getAccessToken()}` };
                    return this.request(path, options);
                } else {
                    window.dispatchEvent(new Event('auth-failed'));
                    throw new Error('Authentication expired');
                }
            }

            const isJson = response.headers.get('content-type')?.includes('application/json');
            const data = isJson ? await response.json() : await response.text();

            if (!response.ok) {
                console.error(`API Error [${response.status}] ${path}:`, data);
                throw { status: response.status, data };
            }

            return data;

        } catch (error) {
            // Check if it's a network error (server down)
            if (error instanceof TypeError && error.message === 'Failed to fetch') {
                console.warn("Server appears to be offline:", error);
                if (window.showOfflineBanner) window.showOfflineBanner(true);
            }
            console.error("Network or parsing error:", error);
            throw error;
        }
    }


    static async refreshTokens() {
        if (!this._configParsed) await this.initConfig();
        const refresh_token = this.getRefreshToken();
        if (!refresh_token) return false;

        try {
            const response = await fetch(`${this.API_BASE_URL}/auth/refresh`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${refresh_token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.setTokens(data.access_token, data.refresh_token);
                return true;
            }
        } catch (e) {
            console.error("Failed to refresh token", e);
        }

        this.clearTokens();
        return false;
    }

    // ─── Auth ────────────────────────────────────────────────
    static async login(username, password) {
        if (!this._configParsed) await this.initConfig();
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${this.API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData.toString()
        });

        if (!response.ok) throw new Error('Invalid credentials');

        const data = await response.json();
        this.setTokens(data.access_token, data.refresh_token);
        return data;
    }

    static async logout() {
        try { await this.request('/auth/logout', { method: 'POST' }); } catch (e) { }
        this.clearTokens();
    }

    static async getMe() {
        return this.request('/auth/me');
    }
    static async getProfile() {
        return this.request('/auth/profile');
    }
    static async updateProfile(data) {
        return this.request('/auth/profile', { method: 'PATCH', body: data });
    }

    // ─── Users ───────────────────────────────────────────────
    static async getUsers() {
        return this.request('/users/');
    }
    static async updateUserRole(userId, role) {
        return this.request(`/users/${userId}/role`, { method: 'PATCH', body: { role } });
    }
    static async updateUserStatus(userId, isActive) {
        return this.request(`/users/${userId}/status`, { method: 'PATCH', body: { is_active: isActive } });
    }
    static async getAccessPolicy() {
        return this.request('/users/access-policy');
    }
    static async updateAccessPolicy(data) {
        return this.request('/users/access-policy', { method: 'PUT', body: data });
    }
    static async getEffectiveAccessPolicy() {
        return this.request('/users/access-policy/effective');
    }

    // ─── Dashboard ───────────────────────────────────────────
    static async getDashboardStats() {
        return this.request('/reports/dashboard');
    }

    // ─── Attendance ──────────────────────────────────────────
    static async getPunchStatus() {
        return this.request('/attendance/status');
    }
    static async punch() {
        return this.request('/attendance/punch', { method: 'POST' });
    }
    static async getAttendanceSummary(params = {}) {
        let query = '';
        if (typeof params === 'object') {
            const queryParams = new URLSearchParams();
            for (const [key, value] of Object.entries(params)) {
                if (value !== undefined && value !== null) {
                    queryParams.append(key, value);
                }
            }
            query = queryParams.toString() ? `?${queryParams.toString()}` : '';
        } else if (typeof params === 'string' && params) {
            query = params.startsWith('?') ? params : `?${params}`;
        }
        return this.request(`/attendance/summary${query}`);
    }

    static async getAttendanceSettings() {
        return this.request('/attendance/settings');
    }

    static async updateAttendanceSettings(data) {
        return this.request('/attendance/settings', { method: 'PUT', body: data });
    }

    // ─── Clients ─────────────────────────────────────────────
    static async getClients(params = '') {
        return this.request(`/clients/${params}`);
    }
    static async getClient(clientId) {
        return this.request(`/clients/${clientId}`);
    }
    static async createClient(data) {
        return this.request('/clients/', { method: 'POST', body: data });
    }
    static async updateClient(clientId, data) {
        return this.request(`/clients/${clientId}`, { method: 'PATCH', body: data });
    }
    static async deleteClient(clientId) {
        return this.request(`/clients/${clientId}`, { method: 'DELETE' });
    }
    static async assignPM(clientId, pmId) {
        return this.request(`/clients/${clientId}/assign-pm`, { method: 'POST', body: { pm_id: pmId } });
    }
    static async getMyClients(params = '') {
        return this.request(`/clients/my-clients?${params}`);
    }

    // ─── Areas ───────────────────────────────────────────────
    static async getAreas() {
        return this.request('/areas/');
    }
    static async createArea(data) {
        return this.request('/areas/', { method: 'POST', body: data });
    }
    static async updateArea(areaId, data) {
        return this.request(`/areas/${areaId}`, { method: 'PATCH', body: data });
    }
    static async deleteArea(areaId) {
        return this.request(`/areas/${areaId}`, { method: 'DELETE' });
    }
    static async getArchivedAreas() {
        return this.request('/areas/archived');
    }
    static async unarchiveArea(areaId) {
        return this.request(`/areas/${areaId}/unarchive`, { method: 'PATCH' });
    }
    static async hardDeleteArea(areaId) {
        return this.request(`/areas/${areaId}/hard-delete`, { method: 'DELETE' });
    }
    static async assignArea(areaId, userIds, shopIds = []) {
        // userIds should be an array of IDs
        return this.request(`/areas/${areaId}/assign`, { method: 'PATCH', body: { user_ids: userIds, shop_ids: shopIds } });
    }

    // ─── Shops ───────────────────────────────────────────────
    static async getShops(params = '') {
        return this.request(`/shops/${params}`);
    }
    static async getShop(shopId) {
        return this.request(`/shops/${shopId}`);
    }
    static async createShop(data) {
        return this.request('/shops/', { method: 'POST', body: data });
    }
    static async updateShop(shopId, data) {
        return this.request(`/shops/${shopId}`, { method: 'PATCH', body: data });
    }
    static async deleteShop(shopId) {
        return this.request(`/shops/${shopId}`, { method: 'DELETE' });
    }
    static async getArchivedShops() {
        return this.request('/shops/archived');
    }
    static async unarchiveShop(shopId) {
        return this.request(`/shops/${shopId}/unarchive`, { method: 'PATCH' });
    }
    static async hardDeleteShop(shopId) {
        return this.request(`/shops/${shopId}/hard-delete`, { method: 'DELETE' });
    }
    static async approvePipelineEntry(shopId) {
        return this.request(`/shops/${shopId}/approve`, { method: 'POST' });
    }
    static async getShopsByArea(areaId) {
        return this.request(`/shops/?area_id=${areaId}&limit=200`);
    }

    // ─── Visits ──────────────────────────────────────────────
    static async getVisits(params = '') {
        return this.request(`/visits/${params}`);
    }
    static async createVisit(formData) {
        return this.request('/visits/', { method: 'POST', body: formData });
    }
    static async updateVisit(visitId, data) {
        return this.request(`/visits/${visitId}`, { method: 'PATCH', body: data });
    }

    // ─── Issues ──────────────────────────────────────────────
    static async getIssues(queryString = '') {
        const query = queryString.startsWith('?') ? queryString : (queryString ? `?${queryString}` : '');
        return this.request(`/issues/${query}`);
    }
    static async getClientIssues(clientId) {
        return this.request(`/clients/${clientId}/issues`);
    }
    static async createIssue(clientId, data) {
        return this.request(`/clients/${clientId}/issues`, { method: 'POST', body: data });
    }
    static async patchIssue(issueId, data) {
        return this.request(`/clients/issues/${issueId}`, { method: 'PATCH', body: data });
    }

    // ─── Meetings ────────────────────────────────────────────
    static async getClientMeetings(clientId) {
        return this.request(`/clients/${clientId}/meetings`);
    }
    static async createMeeting(clientId, data) {
        return this.request(`/clients/${clientId}/meetings`, { method: 'POST', body: data });
    }
    static async updateMeeting(meetingId, data) {
        return this.request(`/clients/meetings/${meetingId}`, { method: 'PATCH', body: data });
    }
    static async cancelMeeting(meetingId, reason) {
        return this.request(`/clients/meetings/${meetingId}/cancel`, { method: 'POST', body: { reason } });
    }
    static async deleteMeeting(meetingId) {
        return this.request(`/clients/meetings/${meetingId}`, { method: 'DELETE' });
    }
    static async importMeetingSummary(meetingId) {
        return this.request(`/clients/meetings/${meetingId}/import-summary`, { method: 'POST' });
    }

    // ─── Feedback ────────────────────────────────────────────
    static async getClientFeedback(clientId) {
        return this.request(`/clients/${clientId}/feedback`);
    }
    static async getAllClientFeedbacks() {
        return this.request('/clients/feedbacks/all');
    }
    static async getClientFeedbacks(clientId) {
        return this.request(`/clients/${clientId}/feedback`);
    }
    static async createFeedback(clientId, data) {
        return this.request(`/clients/${clientId}/feedback`, { method: 'POST', body: data });
    }
    static async createUserFeedback(data) {
        return this.request('/clients/user', { method: 'POST', body: data });
    }
    static async getUserFeedbacks() {
        return this.request('/clients/user');
    }

    // ─── Employees / HR ──────────────────────────────────────
    static async getEmployees() {
        return this.request('/users/');
    }
    static async getEmployee(employeeId) {
        return this.request(`/users/${employeeId}`);
    }
    static async createEmployee(data) {
        return this.request('/employees/', { method: 'POST', body: data });
    }
    static async updateEmployee(employeeId, data) {
        return this.request(`/employees/${employeeId}`, { method: 'PATCH', body: data });
    }
    static async deleteEmployee(employeeId) {
        return this.request(`/employees/${employeeId}`, { method: 'DELETE' });
    }

    // ─── Salary ──────────────────────────────────────────────
    static async getSalaryRecords(employeeId) {
        return this.request(`/hrm/salary/${employeeId}`);
    }
    static async getAllSalarySlips() {
        return this.request('/hrm/salary/all');
    }
    static async getMySalarySlips() {
        return this.request('/hrm/salary/me');
    }
    static async previewSalary(userId, month, extraDeduction = 0, baseSalary = null) {
        let url = `/hrm/salary/preview?user_id=${userId}&month=${encodeURIComponent(month)}&extra_deduction=${extraDeduction}`;
        if (baseSalary !== null && !isNaN(baseSalary)) url += `&base_salary=${baseSalary}`;
        return this.request(url);
    }
    static async generateSalary(data) {
        return this.request('/hrm/salary/generate', { method: 'POST', body: data });
    }
    static async regenerateSalarySlip(data) {
        return this.request('/hrm/salary/regenerate', { method: 'POST', body: data });
    }
    static async updateDraftSalarySlip(slipId, data) {
        return this.request(`/hrm/salary/update-draft/${slipId}`, { method: 'PATCH', body: data });
    }
    static async confirmSalarySlip(slipId) {
        return this.request(`/hrm/salary/confirm/${slipId}`, { method: 'PATCH' });
    }
    static async updateSalarySlipRemarks(slipId, data) {
        return this.request(`/hrm/salary/slip/${slipId}/remarks`, { method: 'PATCH', body: data });
    }
    static async updateSalarySlipVisibility(slipId, data) {
        return this.request(`/hrm/salary/slip/${slipId}/visibility`, { method: 'PATCH', body: data });
    }
    static async getPayslipSettings() {
        return this.request('/hrm/payslip-settings');
    }
    static async updatePayslipSettings(data) {
        return this.request('/hrm/payslip-settings', { method: 'PUT', body: data });
    }

    // ─── Leave ───────────────────────────────────────────────
    static async getMyLeaves() {
        return this.request('/hrm/leave');
    }
    static async getAllLeaves() {
        return this.request('/hrm/leave/all');
    }
    static async applyLeave(data) {
        return this.request('/hrm/leave', { method: 'POST', body: data });
    }
    static async updateLeave(leaveId, data) {
        return this.request(`/hrm/leave/${leaveId}`, { method: 'PATCH', body: data });
    }
    static async deleteLeave(leaveId) {
        return this.request(`/hrm/leave/${leaveId}`, { method: 'DELETE' });
    }
    static async approveRejectLeave(leaveId, status, remarks = null) {
        const body = { status };
        if (remarks) body.remarks = remarks;
        return this.request(`/hrm/leave/${leaveId}/approve`, { method: 'PATCH', body });
    }
    static async getLeaveSummary(userId, month) {
        return this.request(`/hrm/leave/summary/${userId}?month=${encodeURIComponent(month)}`);
    }

    // ─── Incentives ──────────────────────────────────────────
    static async getIncentiveSlabs() {
        return this.request('/incentives/slabs');
    }
    static async createIncentiveSlab(data) {
        return this.request('/incentives/slabs', { method: 'POST', body: data });
    }
    static async updateIncentiveSlab(id, data) {
        return this.request(`/incentives/slabs/${id}`, { method: 'PUT', body: data });
    }
    static async deleteIncentiveSlab(id) {
        return this.request(`/incentives/slabs/${id}`, { method: 'DELETE' });
    }
    static async previewIncentive(data) {
        return this.request('/incentives/calculate/preview', { method: 'POST', body: data });
    }
    static async calculateIncentive(data) {
        return this.request('/incentives/calculate', { method: 'POST', body: data });
    }
    static async recalculateIncentive(data) {
        return this.request('/incentives/calculate', { method: 'POST', body: { ...data, force_recalculate: true } });
    }
    static async calculateIncentiveBulk(data) {
        return this.request('/incentives/calculate/bulk', { method: 'POST', body: data });
    }
    static async getAllIncentiveSlips() {
        return this.request('/incentives/slips');
    }
    static async getMyIncentiveSlips() {
        return this.request('/incentives/my-slips');
    }
    static async getUserIncentiveSlips(userId) {
        return this.request(`/incentives/slips/${userId}`);
    }
    static async updateIncentiveSlipRemarks(slipId, data) {
        return this.request(`/incentives/slips/${slipId}/remarks`, { method: 'PATCH', body: data });
    }
    static async updateIncentiveSlipVisibility(slipId, data) {
        return this.request(`/incentives/slips/${slipId}/visibility`, { method: 'PATCH', body: data });
    }

    // ─── Payments ────────────────────────────────────────────
    static async generatePaymentQR(clientId, amount) {
        return this.request(`/clients/${clientId}/payments/generate-qr`, { method: 'POST', body: { amount } });
    }
    static async generatePaymentQRFromShop(shopId, amount) {
        return this.request(`/shops/${shopId}/payments/generate-qr`, { method: 'POST', body: { amount } });
    }
    static async verifyPayment(paymentId) {
        return this.request(`/payments/${paymentId}/verify`, { method: 'PATCH' });
    }
    // ─── Billing / Invoices ──────────────────────────────────
    /** @deprecated use createInvoice instead */
    static async generateBill(data) {
        return this.request('/billing/', { method: 'POST', body: data });
    }
    static async createInvoice(data) {
        return this.request('/billing/', { method: 'POST', body: data });
    }
    static async getBills(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params || {}).forEach(([k, v]) => {
            if (v === undefined || v === null || v === '') return;
            query.set(k, String(v));
        });
        const qs = query.toString();
        return this.request(`/billing/${qs ? `?${qs}` : ''}`);
    }
    static async getInvoice(billId) {
        return this.request(`/billing/${billId}`);
    }
    static async getInvoiceActions(billId) {
        return this.request(`/billing/${billId}/actions`);
    }
    static async verifyInvoice(billId) {
        return this.request(`/billing/${billId}/verify`, { method: 'PATCH' });
    }
    static async archiveInvoice(billId) {
        return this.request(`/billing/${billId}/archive`, { method: 'PATCH' });
    }
    static async unarchiveInvoice(billId) {
        return this.request(`/billing/${billId}/unarchive`, { method: 'PATCH' });
    }
    static async archiveInvoicesBulk(ids = []) {
        return this.request('/billing/archive/bulk', { method: 'PATCH', body: { ids } });
    }
    static async deleteArchivedInvoice(billId) {
        return this.request(`/billing/${billId}/archive-delete`, { method: 'DELETE' });
    }
    static async deleteArchivedInvoicesBulk(ids = []) {
        return this.request('/billing/archive/delete-bulk', { method: 'POST', body: { ids } });
    }
    static async sendInvoiceWhatsApp(billId) {
        return this.request(`/billing/${billId}/send-whatsapp`, { method: 'POST' });
    }
    static async getWhatsAppHealth() {
        return this.request('/billing/whatsapp-health');
    }
    static async getInvoiceSettings() {
        return this.request('/billing/settings');
    }
    static async updateInvoiceSettings(data) {
        return this.request('/billing/settings', { method: 'PUT', body: data });
    }
    static async getInvoiceWorkflowOptions() {
        return this.request('/billing/workflow/options');
    }
    static async getBillingAutofillSource(source) {
        return this.request(`/billing/autofill-sources?source=${encodeURIComponent(source)}`);
    }
    static async resolveInvoiceWorkflow(data) {
        return this.request('/billing/workflow/resolve', { method: 'POST', body: data });
    }
    static async generateInvoicePaymentQR(data) {
        return this.request('/billing/generate-qr', { method: 'POST', body: data });
    }


    // ─── Projects ────────────────────────────────────────────
    static async getProjects(params = '') {
        return this.request(`/projects/${params}`);
    }
    static async getProject(projectId) {
        return this.request(`/projects/${projectId}`);
    }
    static async createProject(data) {
        return this.request('/projects/', { method: 'POST', body: data });
    }
    static async updateProject(projectId, data) {
        return this.request(`/projects/${projectId}`, { method: 'PATCH', body: data });
    }
    static async deleteProject(projectId) {
        return this.request(`/projects/${projectId}`, { method: 'DELETE' });
    }

    // ─── Todos ───────────────────────────────────────────────
    static async getTodos(params = '') {
        return this.request(`/todos/${params}`);
    }
    static async createTodo(data) {
        return this.request('/todos/', { method: 'POST', body: data });
    }
    static async updateTodo(todoId, data) {
        return this.request(`/todos/${todoId}`, { method: 'PATCH', body: data });
    }
    static async deleteTodo(todoId) {
        return this.request(`/todos/${todoId}`, { method: 'DELETE' });
    }

    // ─── Notifications ───────────────────────────────────────
    static async getNotifications(params = '') {
        return this.request(`/notifications/${params}`);
    }
    static async markNotificationRead(notifId) {
        return this.request(`/notifications/${notifId}/read`, { method: 'PATCH' });
    }

    // ─── Timetable ───────────────────────────────────────────
    static async getTimetable(startDate, endDate) {
        let params = '';
        if (startDate) params += `?start_date=${startDate}`;
        if (endDate) params += (params ? '&' : '?') + `end_date=${endDate}`;
        return this.request(`/timetable/${params}`);
    }
    static async createTimetableEvent(data) {
        return this.request('/timetable/', { method: 'POST', body: data });
    }
    static async updateTimetableEvent(eventId, data) {
        return this.request(`/timetable/${eventId}`, { method: 'PATCH', body: data });
    }
    static async deleteTimetableEvent(eventId) {
        return this.request(`/timetable/${eventId}`, { method: 'DELETE' });
    }

    // ─── Activity Logs ───────────────────────────────────────
    static async getActivityLogs() {
        return this.request('/activity-logs/');
    }

    // ─── Reports ─────────────────────────────────────────────
    static async getReportsDashboard() {
        return this.request('/reports/dashboard');
    }

    // ─── Generic Soft Delete (Archive) ───────────────────────
    static async fetchArchived(moduleName) {
        return this.request(`/${moduleName}/archived`);
    }
    static async archiveItem(moduleName, id) {
        return this.request(`/${moduleName}/${id}`, { method: 'DELETE' });
    }
    static async unarchiveItem(moduleName, id) {
        return this.request(`/${moduleName}/${id}/unarchive`, { method: 'PATCH' });
    }
    static async hardDeleteItem(moduleName, id) {
        return this.request(`/${moduleName}/${id}/hard-delete`, { method: 'DELETE' });
    }

    // ─── Generic Accept Assignment ───────────────────────────
    static async acceptItem(moduleName, id) {
        return this.request(`/${moduleName}/${id}/accept`, { method: 'POST' });
    }
    static async getAcceptedLeads() {
        return this.request('/shops/accepted/history');
    }
}

window.ApiClient = ApiClient;
