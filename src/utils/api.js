// ============================================================
// BoneQuest v2 — API Client (Full)
// ============================================================

import { auth } from './auth.js';

const BASE_URL = '/api';
const AUTH_URL = '/auth';

class ApiClient {
    async request(endpoint, options = {}, baseUrl = BASE_URL) {
        const url = `${baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...auth.getAuthHeaders(),
                ...options.headers,
            },
            ...options,
        };

        try {
            const response = await fetch(url, config);

            if (response.status === 401) {
                auth.logout();
                throw new Error('Session expired. Please sign in again.');
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (err) {
            console.error(`API Error [${endpoint}]:`, err);
            throw err;
        }
    }

    // ── Documents ───────────────────────────────────────────
    async getDocuments() {
        return this.request('/documents');
    }

    async uploadDocument(file, docType = 'general') {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('doc_type', docType);

        // We can't use Content-Type: application/json for FormData
        // We have to let the browser set it automatically with boundary.
        const headers = { ...auth.getAuthHeaders() };

        try {
            const response = await fetch(`${BASE_URL}/documents/upload`, {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (err) {
            console.error(`API Error [upload]:`, err);
            throw err;
        }
    }

    async deleteDocument(id) {
        return this.request(`/documents/${id}`, { method: 'DELETE' });
    }

    // ── Auth ────────────────────────────────────────────────
    async signup(data) {
        return this.request('/signup', {
            method: 'POST',
            body: JSON.stringify(data),
        }, AUTH_URL);
    }

    async signin(data) {
        return this.request('/signin', {
            method: 'POST',
            body: JSON.stringify(data),
        }, AUTH_URL);
    }

    async getMe() {
        return this.request('/me', {}, AUTH_URL);
    }

    async updateMe(data) {
        return this.request('/me', {
            method: 'PATCH',
            body: JSON.stringify(data),
        }, AUTH_URL);
    }

    // ── Chat Sessions ───────────────────────────────────────
    async createSession(data = {}) {
        return this.request('/chat/sessions', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async listSessions(skip = 0, limit = 50) {
        return this.request(`/chat/sessions?skip=${skip}&limit=${limit}`);
    }

    async getSession(sessionId) {
        return this.request(`/chat/sessions/${sessionId}`);
    }

    async deleteSession(sessionId) {
        return this.request(`/chat/sessions/${sessionId}`, { method: 'DELETE' });
    }

    async renameSession(sessionId, title) {
        return this.request(`/chat/sessions/${sessionId}/rename?title=${encodeURIComponent(title)}`, {
            method: 'PATCH',
        });
    }

    async getSessionMessages(sessionId) {
        return this.request(`/chat/sessions/${sessionId}/messages`);
    }

    async sendFeedback(messageId, score) {
        return this.request(`/chat/messages/${messageId}/feedback`, {
            method: 'POST',
            body: JSON.stringify({ score })
        });
    }

    // ── Chat Message (streaming) ────────────────────────────
    async *streamChatMessage(data) {
        const response = await fetch(`${BASE_URL}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...auth.getAuthHeaders(),
            },
            body: JSON.stringify(data),
        });

        if (response.status === 401) {
            auth.logout();
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') return;
                    try {
                        yield JSON.parse(data);
                    } catch { }
                }
            }
        }
    }

    // ── Legacy Query (no auth) ──────────────────────────────
    async query(data) {
        return this.request('/query', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async *streamQuery(data) {
        const response = await fetch(`${BASE_URL}/query/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') return;
                    try {
                        yield JSON.parse(data);
                    } catch { }
                }
            }
        }
    }

    // Document methods are now correctly defined at the top

    // ── Image Analysis ──────────────────────────────────────
    async analyzeImage(formData) {
        const response = await fetch(`${BASE_URL}/image/analyze`, {
            method: 'POST',
            headers: auth.getAuthHeaders(),
            body: formData,
        });
        if (response.status === 401) {
            auth.logout();
            throw new Error('Session expired');
        }
        return response.json();
    }

    // ── Admin ───────────────────────────────────────────────
    async getAnalytics(days = 7) {
        return this.request(`/admin/analytics?days=${days}`);
    }

    async getAuditLog(page = 1, perPage = 50) {
        return this.request(`/admin/audit-log?page=${page}&per_page=${perPage}`);
    }

    async getUsers(page = 1) {
        return this.request(`/admin/users?page=${page}`);
    }

    async updateUser(userId, data) {
        const params = new URLSearchParams();
        if (data.role) params.set('role', data.role);
        if (data.is_active !== undefined) params.set('is_active', data.is_active);
        return this.request(`/admin/users/${userId}?${params}`, { method: 'PATCH' });
    }

    async getQAFeed(page = 1, perPage = 50) {
        return this.request(`/admin/qa-feed?page=${page}&per_page=${perPage}`);
    }
}

export const api = new ApiClient();
