// ============================================================
// BoneQuest v2 — Navbar Component
// ============================================================

import { auth } from '../utils/auth.js';

export function createNavbar(page = 'landing') {
    const nav = document.getElementById('main-nav');
    if (!nav) return;

    const isAuth = auth.isAuthenticated;
    const user = auth.user;
    const isAdmin = auth.isAdmin;

    // Simplified navbar on auth pages
    if (page === 'auth') {
        nav.className = 'navbar glass';
        nav.innerHTML = `
            <div class="nav-container">
                <a href="#/" class="logo">
                    <span>BoneQuest</span>
                </a>
                <div class="nav-actions">
                    <a href="#/" class="btn btn-ghost">← Back to Home</a>
                </div>
            </div>
        `;
        return;
    }

    const isLanding = page === 'landing';

    nav.className = `navbar ${isLanding ? 'navbar-landing glass' : 'navbar-app glass-strong'}`;
    nav.innerHTML = `
        <div class="nav-container">
            <a href="#/" class="logo">
                <span class="text-gradient">BoneQuest</span>
            </a>
            <div class="nav-links">
                ${isLanding ? `
                    <a href="#/" class="nav-link" data-scroll="features">Features</a>
                    <a href="#/" class="nav-link" data-scroll="comparison">Comparison</a>
                    <a href="#/" class="nav-link" data-scroll="testimonials">Testimonials</a>
                ` : `
                    ${isAdmin ? `<a href="#/dashboard" class="nav-link ${page === 'dashboard' ? 'active' : ''}">Dashboard</a>` : ''}
                    <a href="#/chat" class="nav-link ${page === 'chat' ? 'active' : ''}">AI Chat</a>
                    <a href="#/profile" class="nav-link ${page === 'profile' ? 'active' : ''}">Profile</a>
                `}
            </div>
            <div class="nav-actions">
                ${isAuth ? `
                    <div class="nav-user">
                        <a href="#/profile" class="nav-user-avatar" title="View Profile">${(user?.full_name || 'U')[0].toUpperCase()}</a>
                        <div class="nav-user-info hide-mobile">
                            <span class="nav-user-name">${user?.full_name || 'User'}</span>
                            <span class="nav-user-role">${user?.role || 'resident'}</span>
                        </div>
                        <button class="btn btn-ghost nav-logout" id="nav-logout-btn" title="Sign out">⏻</button>
                    </div>
                ` : `
                    <div class="hide-mobile" style="display: flex; gap: var(--space-2);">
                        <a href="#/signin" class="btn btn-secondary">Sign In</a>
                        <a href="#/signup" class="btn btn-primary">Get Started <span class="arrow">↗</span></a>
                    </div>
                `}
                <button class="mobile-menu-btn" id="mobile-toggle" aria-label="Toggle Menu">
                    <span class="bar"></span>
                    <span class="bar"></span>
                    <span class="bar"></span>
                </button>
            </div>
        </div>
    `;

    // Mobile Toggle Logic
    const toggle = nav.querySelector('#mobile-toggle');
    const navLinks = nav.querySelector('.nav-links');
    
    if (toggle && navLinks) {
        toggle.addEventListener('click', () => {
            toggle.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
    }

    // Logout handler
    const logoutBtn = nav.querySelector('#nav-logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => auth.logout());
    }

    // Scroll links
    nav.querySelectorAll('[data-scroll]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.getElementById(link.dataset.scroll);
            if (target) target.scrollIntoView({ behavior: 'smooth' });
        });
    });
}
