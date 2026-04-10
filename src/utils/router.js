// ============================================================
// BoneQuest v2 — SPA Router with Auth Guards
// ============================================================

import { auth } from './auth.js';

export class Router {
    constructor(routes, fallback = null) {
        this.routes = routes;
        this.fallback = fallback;
        this.currentPage = null;

        window.addEventListener('hashchange', () => this.resolve());
        window.addEventListener('load', () => this.resolve());
    }

    resolve() {
        const hash = window.location.hash.slice(1) || '/';
        let route = this.routes.find(r => r.path === hash);

        if (!route && hash === '/') {
            route = this.routes[0]; // default to first route
        }

        if (!route) {
            // 404 fallback
            if (this.fallback) {
                this.currentPage = null;
                const container = document.getElementById('page-content');
                container.innerHTML = '';
                this.fallback(container);
            }
            return;
        }

        // Auth guard
        if (route.requiresAuth && !auth.isAuthenticated) {
            window.location.hash = '#/signin';
            return;
        }

        // Admin guard
        if (route.requiresAdmin && !auth.isAdmin) {
            window.location.hash = '#/chat';
            return;
        }

        // Redirect authenticated users away from auth pages
        if (route.guestOnly && auth.isAuthenticated) {
            window.location.hash = auth.isAdmin ? '#/dashboard' : '#/chat';
            return;
        }

        if (route.path !== this.currentPage) {
            this.currentPage = route.path;
            const container = document.getElementById('page-content');
            container.innerHTML = '';
            container.className = 'page-enter';
            route.render(container);
            window.scrollTo(0, 0);
        }
    }

    navigate(path) {
        window.location.hash = path;
    }
}
