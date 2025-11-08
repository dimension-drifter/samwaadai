/**
 * API Service for Call Tracker AI
 * Handles all HTTP requests to the backend
 */

const API_BASE_URL = 'http://localhost:8000';

class APIService {
    constructor(baseURL = API_BASE_URL) {
        this.baseURL = baseURL;
    }

    /**
     * Make a fetch request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        try {
            console.log(`🌐 API Request: ${options.method || 'GET'} ${endpoint}`);
            
            const response = await fetch(url, defaultOptions);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log(`✅ API Response:`, data);
            return data;

        } catch (error) {
            console.error(`❌ API Error (${endpoint}):`, error);
            throw error;
        }
    }

    /**
     * Create a new call
     */
    async createCall(callData) {
        return await this.request('/api/calls/', {
            method: 'POST',
            body: JSON.stringify({
                platform: callData.platform || 'web',
                contact_name: callData.contact_name || 'Unknown',
                contact_email: callData.contact_email || '',
                contact_phone: callData.contact_phone || ''
            })
        });
    }

    /**
     * Get all calls
     */
    async getCalls(limit = 50, offset = 0) {
        return await this.request(`/api/calls/?limit=${limit}&offset=${offset}`);
    }

    /**
     * Get a specific call by ID
     */
    async getCall(callId) {
        return await this.request(`/api/calls/${callId}`);
    }

    /**
     * Update a call
     */
    async updateCall(callId, updateData) {
        return await this.request(`/api/calls/${callId}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
    }

    /**
     * Delete a call
     */
    async deleteCall(callId) {
        return await this.request(`/api/calls/${callId}`, {
            method: 'DELETE'
        });
    }

    /**
     * Get analytics/stats (if endpoint exists)
     */
    async getAnalytics() {
        try {
            return await this.request('/api/analytics/stats');
        } catch (error) {
            console.warn('Analytics endpoint not available yet');
            return {
                total_calls: 0,
                total_duration: 0,
                average_sentiment: 'NEUTRAL'
            };
        }
    }

    /**
     * Check API health
     */
    async checkHealth() {
        try {
            const response = await fetch(`${this.baseURL}/health`);
            return response.ok;
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }

    /**
     * Get upcoming calendar events
     */
    async getCalendarEvents(maxResults = 50) {
        return await this.request(`/api/calendar/events?max_results=${maxResults}`);
    }

    /**
     * Delete a calendar event
     */
    async deleteCalendarEvent(eventId) {
        return await this.request(`/api/calendar/events/${eventId}`, {
            method: 'DELETE'
        });
    }

    /**
     * Check calendar service health
     */
    async checkCalendarHealth() {
        try {
            return await this.request('/api/calendar/health');
        } catch (error) {
            console.warn('Calendar health check failed:', error);
            return { authenticated: false, error: error.message };
        }
    }
     async getSentEmails(limit = 100, offset = 0) {
        return await this.request(`/api/emails/?limit=${limit}&offset=${offset}`);
    }
}



// Create global API instance
const API = new APIService();

// Make it available globally
window.API = API;

// Check API health on load
API.checkHealth().then(healthy => {
    if (healthy) {
        console.log('✅ Backend API is healthy');
    } else {
        console.error('❌ Backend API is not responding. Please start the server.');
        alert('Cannot connect to backend server. Please ensure the server is running on http://localhost:8000');
    }
});