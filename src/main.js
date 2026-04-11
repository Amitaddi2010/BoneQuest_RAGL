// ============================================================
// BoneQuest v2.1 — Main Entry Point (3-Signal Hybrid RAG)
// ============================================================

import { Router } from './utils/router.js';
import { auth } from './utils/auth.js';
import { theme } from './utils/theme.js';  // Init themes on first paint
import { createNavbar } from './components/navbar.js';
import { renderLanding } from './pages/landing.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderChat } from './pages/chat.js';
import { renderSignIn, renderSignUp } from './pages/auth.js';
import { renderAdmin } from './pages/admin.js';
import { renderProfile } from './pages/profile.js';

// ── Toast Notification System ──────────────────────────────
function ensureToastContainer() {
    let tc = document.getElementById('bq-toast-container');
    if (!tc) {
        tc = document.createElement('div');
        tc.id = 'bq-toast-container';
        tc.className = 'toast-container';
        document.body.appendChild(tc);
    }
    return tc;
}

window.bqToast = function(type = 'info', title = '', message = '', duration = 5000) {
    const container = ensureToastContainer();
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
        <div class="toast-body">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.classList.add('toast-exit'); setTimeout(() => this.parentElement.remove(), 300);">✕</button>
    `;
    container.appendChild(toast);
    if (duration > 0) {
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
};

// ── 404 Not Found Page ─────────────────────────────────────
function render404(container) {
    createNavbar('landing');
    container.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 70vh; text-align: center; padding: var(--space-8);">
            <div style="font-size: 5rem; margin-bottom: var(--space-4); opacity: 0.4;">🦴</div>
            <h1 style="font-size: var(--text-5xl); margin-bottom: var(--space-4);">404</h1>
            <p style="font-size: var(--text-lg); color: var(--text-dim); margin-bottom: var(--space-8); max-width: 400px;">
                This page doesn't exist in the BoneQuest library. Navigate back to continue your clinical session.
            </p>
            <div style="display: flex; gap: var(--space-4); flex-wrap: wrap; justify-content: center;">
                <a href="#/" class="btn btn-primary">Back to Home</a>
                <a href="#/chat" class="btn btn-secondary">Open AI Chat</a>
            </div>
        </div>
    `;
}

// ── Initialize Router ──────────────────────────────────────
const router = new Router([
    {
        path: '/',
        render: (container) => {
            createNavbar('landing');
            renderLanding(container);
        }
    },
    {
        path: '/signin',
        guestOnly: true,
        render: (container) => {
            createNavbar('auth');
            renderSignIn(container);
        }
    },
    {
        path: '/signup',
        guestOnly: true,
        render: (container) => {
            createNavbar('auth');
            renderSignUp(container);
        }
    },
    {
        path: '/dashboard',
        requiresAuth: true,
        requiresAdmin: true,
        render: (container) => {
            createNavbar('dashboard');
            renderDashboard(container);
        }
    },
    {
        path: '/chat',
        requiresAuth: true,
        render: (container) => {
            createNavbar('chat');
            renderChat(container);
        }
    },
    {
        path: '/admin',
        requiresAuth: true,
        requiresAdmin: true,
        render: (container) => {
            createNavbar('admin');
            renderAdmin(container);
        }
    },
    {
        path: '/profile',
        requiresAuth: true,
        render: (container) => {
            createNavbar('profile');
            renderProfile(container);
        }
    }
], render404);

// ── Global Error Boundary ──────────────────────────────────
window.addEventListener('unhandledrejection', (e) => {
    console.error('[BoneQuest] Unhandled promise rejection:', e.reason);
    if (window.bqToast && e.reason?.message) {
        window.bqToast('error', 'System Error', e.reason.message);
    }
});

// ── Startup Log ────────────────────────────────────────────
console.log('%c🦴 BoneQuest v2.2', 'font-size: 20px; font-weight: bold; color: #2EC4B6;');
console.log('%c3-Signal Hybrid RAG · BM25 · Semantic · Tree', 'color: #A8A29E;');
