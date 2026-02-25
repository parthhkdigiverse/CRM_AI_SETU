let API_BASE_URL = 'http://127.0.0.1:8000/api'; // Fallback
// Try to load dynamically from the backend Python config endpoint
fetch('http://127.0.0.1:8000/api/config')
    .then(r => r.json())
    .then(data => { API_BASE_URL = data.API_BASE_URL; ApiClient.API_BASE_URL = data.API_BASE_URL; })
    .catch(e => console.warn('Using default API_BASE_URL due to config fetch error:', e));

class ApiClient {
    static API_BASE_URL = API_BASE_URL;

    static getAccessToken() {
        return localStorage.getItem('access_token');
    }

    static getRefreshToken() {
        return localStorage.getItem('refresh_token');
    }

    static setTokens(accessToken, refreshToken) {
        localStorage.setItem('access_token', accessToken);
        if (refreshToken) {
            localStorage.setItem('refresh_token', refreshToken);
        }
    }

    static clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('current_user');
    }

    static setCurrentUser(user) {
        localStorage.setItem('current_user', JSON.stringify(user));
    }

    static getCurrentUser() {
        try { return JSON.parse(localStorage.getItem('current_user')); } catch { return null; }
    }

    static async request(path, options = {}) {
        const url = `${API_BASE_URL}${path}`;
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

        if (options.body && typeof options.body !== 'string') {
            config.body = JSON.stringify(options.body);
        } else if (options.body) {
            config.body = options.body;
        }

        try {
            let response = await fetch(url, config);

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
            console.error("Network or parsing error:", error);
            throw error;
        }
    }

    static async refreshTokens() {
        const refresh_token = this.getRefreshToken();
        if (!refresh_token) return false;

        try {
            const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
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
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
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

    // ─── Users ───────────────────────────────────────────────
    static async getUsers() {
        return this.request('/employees/');
    }
    static async updateUserRole(userId, role) {
        return this.request(`/users/${userId}/role`, { method: 'PATCH', body: { role } });
    }

    // ─── Dashboard ───────────────────────────────────────────
    static async getDashboardStats() {
        return this.request('/reports/dashboard');
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

    // ─── Areas ───────────────────────────────────────────────
    static async getAreas() {
        return this.request('/areas/');
    }
    static async createArea(data) {
        return this.request('/areas/', { method: 'POST', body: data });
    }
    static async assignAreaAgents(areaId, userId) {
        return this.request(`/areas/${areaId}/assign`, { method: 'PATCH', body: { user_id: userId } });
    }

    // ─── Shops ───────────────────────────────────────────────
    static async getShops(params = '') {
        return this.request(`/shops/${params}`);
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
    static async getShopsByArea(areaId) {
        return this.request(`/shops/?area_id=${areaId}&limit=200`);
    }

    // ─── Visits ──────────────────────────────────────────────
    static async getVisits(params = '') {
        return this.request(`/visits/${params}`);
    }
    static async createVisit(data) {
        return this.request('/visits/', { method: 'POST', body: data });
    }
    static async updateVisit(visitId, data) {
        return this.request(`/visits/${visitId}`, { method: 'PATCH', body: data });
    }

    // ─── Issues ──────────────────────────────────────────────
    static async getIssues(queryString = '') {
        return this.request(`/clients/issues${queryString}`);
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
    static async createFeedback(clientId, data) {
        return this.request(`/clients/${clientId}/feedback`, { method: 'POST', body: data });
    }

    // ─── Employees / HR ──────────────────────────────────────
    static async getEmployees() {
        return this.request('/employees/');
    }
    static async getEmployee(employeeId) {
        return this.request(`/employees/${employeeId}`);
    }
    static async createEmployee(data) {
        return this.request('/employees/', { method: 'POST', body: data });
    }
    static async updateEmployee(employeeId, data) {
        return this.request(`/employees/${employeeId}`, { method: 'PATCH', body: data });
    }

    // ─── Salary ──────────────────────────────────────────────
    static async getSalaryRecords(employeeId) {
        return this.request(`/hrm/salary/${employeeId}`);
    }
    static async generateSalary(data) {
        return this.request('/hrm/salary/generate', { method: 'POST', body: data });
    }

    // ─── Incentives ──────────────────────────────────────────
    static async getIncentiveSlabs() {
        return this.request('/incentives/slabs');
    }
    static async createIncentiveSlab(data) {
        return this.request('/incentives/slabs', { method: 'POST', body: data });
    }
    static async calculateIncentive(data) {
        return this.request('/incentives/calculate', { method: 'POST', body: data });
    }

    // ─── Payments ────────────────────────────────────────────
    static async generatePaymentQR(clientId, amount) {
        return this.request(`/clients/${clientId}/payments/generate-qr`, { method: 'POST', body: { amount } });
    }
    static async verifyPayment(paymentId) {
        return this.request(`/payments/${paymentId}/verify`, { method: 'PATCH' });
    }

    // ─── Activity Logs ───────────────────────────────────────
    static async getActivityLogs() {
        return this.request('/activity-logs/');
    }

    // ─── Reports ─────────────────────────────────────────────
    static async getReportsDashboard() {
        return this.request('/reports/dashboard');
    }
}

window.ApiClient = ApiClient;
