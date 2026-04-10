// ============================================================
// BoneQuest v2 — Auth State Manager
// ============================================================

const AUTH_KEY = 'bonequest_auth';
const RAW_BASE = (import.meta.env.VITE_API_URL || '').toString().trim().replace(/\/+$/, '');
const AUTH_BASE = RAW_BASE
    ? (RAW_BASE.toLowerCase().endsWith('/auth') ? RAW_BASE : `${RAW_BASE}/auth`)
    : '/auth';

function _jwtExpiry(token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        return payload.exp ? payload.exp * 1000 : null; // ms
    } catch { return null; }
}

class AuthManager {
    constructor() {
        this._user = null;
        this._token = null;
        this._refreshToken = null;
        this._listeners = [];
        this._restore();
    }

    _restore() {
        try {
            const stored = localStorage.getItem(AUTH_KEY);
            if (stored) {
                const data = JSON.parse(stored);
                this._user = data.user || null;
                this._token = data.access_token || null;
                this._refreshToken = data.refresh_token || null;
            }
        } catch { }
    }

    _persist() {
        if (this._user && this._token) {
            localStorage.setItem(AUTH_KEY, JSON.stringify({
                user: this._user,
                access_token: this._token,
                refresh_token: this._refreshToken,
            }));
        } else {
            localStorage.removeItem(AUTH_KEY);
        }
    }

    _notify() {
        this._listeners.forEach(fn => fn(this.isAuthenticated, this._user));
    }

    get isAuthenticated() {
        return !!this._token && !!this._user;
    }

    isTokenExpired() {
        if (!this._token) return true;
        const exp = _jwtExpiry(this._token);
        if (!exp) return false;
        return Date.now() >= exp - 30_000; // 30s buffer
    }

    async ensureFreshToken() {
        if (!this.isTokenExpired()) return true;
        if (!this._refreshToken) { this.logout(); return false; }
        try {
            const res = await fetch(`${AUTH_BASE}/refresh-token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this._refreshToken }),
            });
            if (!res.ok) { this.logout(); return false; }
            const data = await res.json();
            this._token = data.access_token;
            this._persist();
            return true;
        } catch {
            this.logout();
            return false;
        }
    }

    get user() {
        return this._user;
    }

    get token() {
        return this._token;
    }

    get role() {
        return this._user?.role || 'resident';
    }

    get isAdmin() {
        return this._user?.role === 'admin';
    }

    login(tokenResponse) {
        this._token = tokenResponse.access_token;
        this._refreshToken = tokenResponse.refresh_token;
        this._user = tokenResponse.user;
        this._persist();
        this._notify();
    }

    logout() {
        // Try server logout
        if (this._token) {
            fetch(`${AUTH_BASE}/logout`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this._token}` }
            }).catch(() => { });
        }
        this._token = null;
        this._refreshToken = null;
        this._user = null;
        this._persist();
        this._notify();
        window.location.hash = '#/signin';
    }

    updateUser(user) {
        this._user = user;
        this._persist();
        this._notify();
    }

    onAuthChange(fn) {
        this._listeners.push(fn);
        return () => {
            this._listeners = this._listeners.filter(l => l !== fn);
        };
    }

    getAuthHeaders() {
        if (!this._token) return {};
        return { 'Authorization': `Bearer ${this._token}` };
    }
}

export const auth = new AuthManager();
