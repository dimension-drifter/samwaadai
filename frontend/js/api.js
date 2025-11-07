/**
 * API Service - Handles all backend API calls
 */

const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000';

class APIService {
    constructor() {
        this.token = localStorage.getItem('token');
    }

    /**
     * Generic fetch wrapper with error handling
     */
    async fetch(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'API request failed');
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    // ===================================
    // Auth Endpoints
    // ===================================

    async register(userData) {
        return this.fetch('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    async login(email, password) {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        const data = await response.json();
        this.token = data.access_token;
        localStorage.setItem('token', this.token);
        return data;
    }

    logout() {
        this.token = null;
        localStorage.removeItem('token');
    }

    // ===================================
    // Call Endpoints
    // ===================================

    async createCall(callData) {
        return this.fetch('/api/calls/', {
            method: 'POST',
            body: JSON.stringify(callData)
        });
    }

    async getCalls(status = null, limit = 50) {
        let endpoint = `/api/calls/?limit=${limit}`;
        if (status) {
            endpoint += `&status=${status}`;
        }
        return this.fetch(endpoint);
    }

    async getCall(callId) {
        return this.fetch(`/api/calls/${callId}`);
    }

    async updateCall(callId, updateData) {
        return this.fetch(`/api/calls/${callId}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
    }

    async deleteCall(callId) {
        return this.fetch(`/api/calls/${callId}`, {
            method: 'DELETE'
        });
    }

    async getCallInsights(callId) {
        return this.fetch(`/api/calls/${callId}/insights`);
    }

    // ===================================
    // Task Endpoints
    // ===================================

    async getTasks(status = null) {
        let endpoint = '/api/tasks/';
        if (status) {
            endpoint += `?status=${status}`;
        }
        return this.fetch(endpoint);
    }

    async getPendingTasks() {
        return this.fetch('/api/tasks/pending');
    }

    async approveTask(taskId) {
        return this.fetch(`/api/tasks/${taskId}/approve`, {
            method: 'POST'
        });
    }

    async rejectTask(taskId) {
        return this.fetch(`/api/tasks/${taskId}/reject`, {
            method: 'POST'
        });
    }

    async executeTask(taskId) {
        return this.fetch(`/api/tasks/${taskId}/execute`, {
            method: 'POST'
        });
    }

    // ===================================
    // Analytics Endpoints
    // ===================================

    async getStats() {
        return this.fetch('/api/analytics/stats');
    }

    async getRecentActivity(limit = 10) {
        return this.fetch(`/api/analytics/recent-activity?limit=${limit}`);
    }

    // ===================================
    // Health Check
    // ===================================

    async healthCheck() {
        return this.fetch('/health');
    }
}

// Export singleton instance
const api = new APIService();