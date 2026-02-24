const API_BASE_URL = 'http://127.0.0.1:8123/api';

class ApiClient {
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

    // ─── Dashboard ───────────────────────────────────────────
    static async getDashboardStats() {
        return this.request('/reports/dashboard');
    }

    // ─── Clients ─────────────────────────────────────────────
    static async getClients() {
        return this.request('/clients/');
    }
    static async createClient(data) {
        return this.request('/clients/', { method: 'POST', body: data });
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

    // ─── Shops ───────────────────────────────────────────────
    static async getShops() {
        return this.request('/shops/');
    }
    static async createShop(data) {
        return this.request('/shops/', { method: 'POST', body: data });
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

    // ─── Issues ──────────────────────────────────────────────
    static async getIssues(queryString = '') {
        return this.request(`/issues/${queryString}`);
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

    // ─── Feedback ────────────────────────────────────────────
    static async getClientFeedback(clientId) {
        return this.request(`/clients/${clientId}/feedback`);
    }

    // ─── Employees / HR ──────────────────────────────────────
    static async getEmployees() {
        return this.request('/employees/');
    }
    static async getSalaryRecords() {
        return this.request('/hrm/salary/');
    }
    static async updateUserRole(userId, role) {
        return this.request(`/users/${userId}/role`, { method: 'PATCH', body: { role } });
    }
}

window.ApiClient = ApiClient;
