// ============================================================
// BoneQuest v2 — Main Entry Point
// ============================================================

import { Router } from './utils/router.js';
import { auth } from './utils/auth.js';
import { createNavbar } from './components/navbar.js';
import { renderLanding } from './pages/landing.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderChat } from './pages/chat.js';
import { renderSignIn, renderSignUp } from './pages/auth.js';
import { renderAdmin } from './pages/admin.js';
import { renderProfile } from './pages/profile.js';

// Initialize router with auth guards
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
]);

// Log startup
console.log('%c🦴 BoneQuest v2', 'font-size: 20px; font-weight: bold; color: #7C3AED;');
console.log('%cClinical-Grade Orthopaedic Decision Support', 'color: #94A3B8;');
