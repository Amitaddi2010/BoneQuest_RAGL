// ============================================================
// BoneQuest v2 — Admin Dashboard Page
// ============================================================

import { api } from '../utils/api.js';
import { auth } from '../utils/auth.js';

export function renderAdmin(container) {
    container.innerHTML = `
        <div class="admin-layout">
            <aside class="admin-sidebar">
                <div class="sidebar-header">
                    <a href="#/" class="logo" style="font-size: var(--text-base);">
                        <span>BoneQuest</span>
                    </a>
                    <span class="badge badge-accent" style="font-size:10px;">Admin</span>
                </div>
                <ul class="sidebar-nav">
                    <li class="sidebar-item"><a class="sidebar-link active" data-view="analytics"><span class="icon">📊</span> Analytics</a></li>
                    <li class="sidebar-item"><a class="sidebar-link" data-view="users"><span class="icon">👥</span> Users</a></li>
                    <li class="sidebar-item"><a class="sidebar-link" data-view="audit"><span class="icon">📋</span> Audit Log</a></li>
                    <li class="sidebar-item"><a class="sidebar-link" data-view="qa"><span class="icon">✅</span> QA Feed</a></li>
                    <li class="sidebar-item"><a href="#/chat" class="sidebar-link"><span class="icon">💬</span> AI Chat</a></li>
                </ul>
            </aside>

            <main class="admin-main">
                <div class="admin-header">
                    <h1>Admin Dashboard</h1>
                    <p>System analytics, user management, and compliance audit.</p>
                </div>

                <div id="admin-content">
                    <div class="admin-loading">Loading analytics...</div>
                </div>
            </main>
        </div>
    `;

    let currentView = 'analytics';

    // Sidebar nav
    container.querySelectorAll('.sidebar-link[data-view]').forEach(link => {
        link.addEventListener('click', () => {
            container.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            currentView = link.dataset.view;
            loadView(currentView);
        });
    });

    loadView('analytics');

    async function loadView(view) {
        const content = container.querySelector('#admin-content');
        content.innerHTML = '<div class="admin-loading">Loading...</div>';

        try {
            switch (view) {
                case 'analytics': await renderAnalytics(content); break;
                case 'users': await renderUsers(content); break;
                case 'audit': await renderAuditLog(content); break;
                case 'qa': await renderQAFeed(content); break;
            }
        } catch (err) {
            content.innerHTML = `<div class="admin-error">Failed to load: ${err.message}</div>`;
        }
    }

    async function renderAnalytics(el) {
        const data = await api.getAnalytics(7);

        el.innerHTML = `
            <div class="admin-stats-grid">
                <div class="admin-stat-card">
                    <div class="admin-stat-icon">👥</div>
                    <div class="admin-stat-number">${data.total_users}</div>
                    <div class="admin-stat-label">Total Users</div>
                </div>
                <div class="admin-stat-card">
                    <div class="admin-stat-icon">💬</div>
                    <div class="admin-stat-number">${data.total_sessions}</div>
                    <div class="admin-stat-label">Chat Sessions</div>
                </div>
                <div class="admin-stat-card">
                    <div class="admin-stat-icon">❓</div>
                    <div class="admin-stat-number">${data.total_queries}</div>
                    <div class="admin-stat-label">Total Queries</div>
                </div>
                <div class="admin-stat-card">
                    <div class="admin-stat-icon">🎯</div>
                    <div class="admin-stat-number">${(data.average_confidence * 100).toFixed(1)}%</div>
                    <div class="admin-stat-label">Avg Confidence</div>
                </div>
                <div class="admin-stat-card">
                    <div class="admin-stat-icon" style="color:var(--success)">✅</div>
                    <div class="admin-stat-number">${data.total_validated || 0}</div>
                    <div class="admin-stat-label">Clinician Validated</div>
                </div>
                <div class="admin-stat-card">
                    <div class="admin-stat-icon" style="color:var(--error)">⚠️</div>
                    <div class="admin-stat-number">${data.total_flagged || 0}</div>
                    <div class="admin-stat-label">Clinician Flagged</div>
                </div>
            </div>

            <div class="admin-charts-row">
                <div class="admin-chart-card">
                    <h3>Queries by Day (Last 7 Days)</h3>
                    <div class="chart-bars" id="daily-chart">
                        ${(data.queries_by_day || []).map(d => {
                            const maxCount = Math.max(...(data.queries_by_day || []).map(x => x.count), 1);
                            const pct = (d.count / maxCount) * 100;
                            return `
                                <div class="chart-bar-item">
                                    <div class="chart-bar-fill" style="height: ${Math.max(pct, 4)}%"></div>
                                    <div class="chart-bar-label">${d.date?.slice(5) || ''}</div>
                                    <div class="chart-bar-value">${d.count}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>

                <div class="admin-chart-card">
                    <h3>Queries by Role</h3>
                    <div class="role-breakdown">
                        ${Object.entries(data.queries_by_role || {}).map(([role, count]) => {
                            const total = Object.values(data.queries_by_role).reduce((a, b) => a + b, 1);
                            return `
                                <div class="role-bar-item">
                                    <div class="role-bar-header">
                                        <span class="role-bar-name">${role}</span>
                                        <span class="role-bar-count">${count}</span>
                                    </div>
                                    <div class="role-bar-track">
                                        <div class="role-bar-fill" style="width: ${(count / total) * 100}%"></div>
                                    </div>
                                </div>
                            `;
                        }).join('') || '<p style="color:var(--text-dim)">No data yet</p>'}
                    </div>
                </div>
            </div>
        `;
    }

    async function renderUsers(el) {
        const data = await api.getUsers();

        el.innerHTML = `
            <div class="admin-table-card">
                <div class="admin-table-header">
                    <h3>Users (${data.total})</h3>
                </div>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Role</th>
                            <th>Hospital</th>
                            <th>Status</th>
                            <th>Last Login</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(data.users || []).map(u => `
                            <tr>
                                <td><strong>${u.full_name || '—'}</strong></td>
                                <td>${u.email}</td>
                                <td><span class="role-badge role-${u.role}">${u.role}</span></td>
                                <td>${u.hospital_id || '—'}</td>
                                <td><span class="status-badge ${u.is_active ? 'active' : 'inactive'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
                                <td>${u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    async function renderAuditLog(el) {
        const data = await api.getAuditLog(1, 50);

        el.innerHTML = `
            <div class="admin-table-card">
                <div class="admin-table-header">
                    <h3>Audit Log (${data.total} entries)</h3>
                    <span class="badge badge-accent"><span class="badge-dot"></span> Immutable Record</span>
                </div>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>User</th>
                            <th>Action</th>
                            <th>Resource</th>
                            <th>IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(data.entries || []).map(e => `
                            <tr>
                                <td class="monospace">${new Date(e.created_at).toLocaleString()}</td>
                                <td>${e.user_email || e.user_id?.slice(0, 8) || '—'}</td>
                                <td><span class="action-badge action-${e.action}">${e.action}</span></td>
                                <td>${e.resource_type || '—'}</td>
                                <td class="monospace">${e.ip_address || '—'}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }
    async function renderQAFeed(el) {
        const data = await api.getQAFeed();

        el.innerHTML = `
            <div class="admin-table-card">
                <div class="admin-table-header">
                    <h3>Clinician QA Feed (${data.total} feedback entries)</h3>
                    <p style="font-size: 12px; color: var(--text-dim);">Reviewing AI responses validated or flagged by clinicians.</p>
                </div>
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Response Snippet</th>
                            <th>Confidence</th>
                            <th>Time</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(data.messages || []).map(m => `
                            <tr>
                                <td>
                                    <span class="badge ${m.feedback === 1 ? 'badge-success' : 'badge-danger'}">
                                        ${m.feedback === 1 ? '👍 Validated' : '👎 Flagged'}
                                    </span>
                                </td>
                                <td><div class="text-truncate" style="max-width: 400px; color: var(--text-secondary);">${m.content.substring(0, 120)}...</div></td>
                                <td><strong>${(m.confidence * 100).toFixed(0)}%</strong></td>
                                <td class="monospace">${new Date(m.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button class="btn btn-ghost btn-sm" onclick="location.hash='#/chat?session=${m.session_id}'">View Case</button>
                                </td>
                            </tr>
                        `).join('') || '<tr><td colspan="5" style="text-align:center; padding:40px; color:var(--text-dim);">No feedback data available yet.</td></tr>'}
                    </tbody>
                </table>
            </div>
        `;
    }
}
