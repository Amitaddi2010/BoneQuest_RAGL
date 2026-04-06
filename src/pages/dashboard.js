// ============================================================
// BoneQuest v2 — Dashboard Page 
// ============================================================

import { initScrollAnimations } from '../utils/animations.js';
import { api } from '../utils/api.js';
import { auth } from '../utils/auth.js';

export async function renderDashboard(container) {
    const user = auth.user;
    const isAdmin = user && user.role === 'admin';

    container.innerHTML = `
        <div class="dashboard-layout">
            <!-- Sidebar -->
            <aside class="sidebar" id="dashboard-sidebar">
                <div class="sidebar-header">
                    <a href="#/" class="logo" style="font-size: var(--text-base);">
                        <span>BoneQuest</span>
                    </a>
                </div>
                <div class="sidebar-section-label">Navigation</div>
                <ul class="sidebar-nav">
                    ${isAdmin ? `
                    <li class="sidebar-item">
                        <a class="sidebar-link active" data-view="overview">
                            <span class="icon">📊</span> Overview
                        </a>
                    </li>` : ''}
                    <li class="sidebar-item">
                        <a href="#/chat" class="sidebar-link">
                            <span class="icon">💬</span> AI Chat
                        </a>
                    </li>
                    ${isAdmin ? `
                    <li class="sidebar-item">
                        <a href="#/admin" class="sidebar-link">
                            <span class="icon">⚙️</span> Admin Panel
                        </a>
                    </li>` : ''}
                </ul>
            </aside>

            <!-- Main Content -->
            <main class="dashboard-main">
                <div class="dashboard-header">
                    <h1>Document Library</h1>
                    <p>Clinical protocols, guidelines, and reference materials.</p>
                </div>

                <!-- Stats Grid -->
                <div class="stats-grid" id="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon">📄</div>
                        <div class="stat-number" id="dash-stat-docs">...</div>
                        <div class="stat-desc">Documents Indexed</div>
                    </div>
                </div>

                <!-- Admin Upload Zone -->
                ${isAdmin ? `
                <div class="upload-zone" id="upload-zone">
                    <div class="upload-icon">📤</div>
                    <h3>Upload Clinical Document (Admin)</h3>
                    <p>Drag & drop your PDF here, or click to browse.</p>
                    
                    <div style="margin-top: 10px; z-index: 10; position: relative;">
                        <label style="font-size: 12px; margin-right: 10px;">Select Document Type:</label>
                        <select id="doc-type-select" style="padding: 5px; border-radius: 4px; background: var(--bg-input); color: var(--text-primary); border: 1px solid var(--border-subtle);">
                            <option value="guideline">Clinical Guideline</option>
                            <option value="general">Book / Case Study</option>
                        </select>
                    </div>

                    <input type="file" id="file-input" accept=".pdf" style="display: none;">
                </div>
                ` : `
                <div style="padding: 15px; background: var(--bg-card); border-radius: 8px; margin-bottom: 20px; font-size: 14px; color: var(--text-dim); border: 1px dashed var(--border-subtle);">
                    <i>Only administrators can upload or delete master documents.</i>
                </div>
                `}

                <!-- Documents List -->
                <div class="documents-header">
                    <div>
                        <h3>Indexed Documents</h3>
                        <p style="font-size: 13px; color: var(--text-dim); margin-top: 5px;">Browse and search available clinic protocols</p>
                    </div>
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <input type="text" id="doc-search" placeholder="Search title or type..." style="padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-medium); background: var(--bg-input); color: var(--text-primary); font-size: 13px; width: 220px;">
                        <span class="badge badge-accent" id="doc-count-badge"><span class="badge-dot"></span> Loading...</span>
                    </div>
                </div>
                
                <div class="doc-grid" id="doc-grid">
                    <div style="padding: 20px; text-align: center; color: var(--text-dim); width: 100%;">
                        Loading documents from server...
                    </div>
                </div>

            </main>
        </div>
    `;

    // Fetch live documents and stats
    try {
        const [docData, analyticsData] = await Promise.all([
            api.getDocuments(),
            isAdmin ? api.getAnalytics().catch(() => null) : Promise.resolve(null)
        ]);

        const docs = docData.documents || [];
        
        // Render Stats Grid
        const statsGrid = container.querySelector('#stats-grid');
        if (isAdmin && analyticsData) {
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-icon">📄</div>
                    <div class="stat-number">${docs.length}</div>
                    <div class="stat-desc">Target Documents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">💬</div>
                    <div class="stat-number">${analyticsData.total_queries}</div>
                    <div class="stat-desc">Queries Resolved</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">👥</div>
                    <div class="stat-number">${analyticsData.total_users}</div>
                    <div class="stat-desc">Active Clinicians</div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon">🎯</div>
                    <div class="stat-number">${(analyticsData.average_confidence * 100).toFixed(1)}%</div>
                    <div class="stat-desc">Response Confidence</div>
                </div>
            `;
        } else {
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-icon">📄</div>
                    <div class="stat-number">${docs.length}</div>
                    <div class="stat-desc">Protocols Indexed</div>
                </div>
                <div class="stat-card" style="opacity: 0.8;">
                    <div class="stat-icon">🔐</div>
                    <div class="stat-number">Real-Time</div>
                    <div class="stat-desc">Analytics (Admin Only)</div>
                </div>
            `;
        }

        container.querySelector('#doc-count-badge').innerHTML = `<span class="badge-dot"></span> ${docs.length} documents`;

        const docGrid = container.querySelector('#doc-grid');
        
        if (docs.length === 0) {
            docGrid.innerHTML = `
                <div style="padding: 30px; text-align: center; color: var(--text-dim); width: 100%; border: 1px dashed var(--border-subtle); border-radius: 8px;">
                    No documents found in the database.
                </div>
            `;
        } else {
            docGrid.innerHTML = docs.map(doc => `
                <div class="card doc-card" data-doc-id="${doc.id}">
                    <div class="doc-card-header">
                        <div class="doc-card-icon">📄</div>
                        <div>
                            <span class="doc-card-status ${doc.status}">${doc.status === 'indexed' ? '✓ Indexed' : '⏳ Processing'}</span>
                            <span class="doc-type-badge" style="font-size:10px; margin-left:5px; padding: 2px 6px; border-radius: 10px; background: ${doc.doc_type === 'guideline' ? 'rgba(34,197,94,0.1)' : 'rgba(59,130,246,0.1)'}; color: ${doc.doc_type === 'guideline' ? 'var(--success)' : '#60a5fa'}; text-transform: uppercase;">
                                ${doc.doc_type}
                            </span>
                        </div>
                    </div>
                    <h4 class="doc-title">${doc.title}</h4>
                    <div class="doc-card-meta" style="justify-content: space-between; align-items: center; margin-top: 15px;">
                        <span>🕒 ${doc.last_queried || 'Recently'}</span>
                        ${isAdmin ? `
                            <button class="btn-delete-doc" data-id="${doc.id}" style="background: none; border: 1px solid var(--error); color: var(--error); border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer;">Delete</button>
                        ` : ''}
                    </div>
                </div>
            `).join('');

            // Search filtering logic
            const searchInput = container.querySelector('#doc-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    const term = e.target.value.toLowerCase();
                    container.querySelectorAll('.doc-card').forEach(card => {
                        const title = card.querySelector('.doc-title').textContent.toLowerCase();
                        const type = card.querySelector('.doc-type-badge').textContent.toLowerCase();
                        if (title.includes(term) || type.includes(term)) {
                            card.style.display = 'flex';
                        } else {
                            card.style.display = 'none';
                        }
                    });
                });
            }
            
            // Delete Handlers
            if (isAdmin) {
                container.querySelectorAll('.btn-delete-doc').forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        e.stopPropagation(); // prevent clicking the card
                        if(confirm('Are you sure you want to delete this document?')) {
                            try {
                                btn.textContent = '...';
                                await api.deleteDocument(btn.dataset.id);
                                renderDashboard(container); // reload
                            } catch (err) {
                                alert('Error deleting: ' + err.message);
                                btn.textContent = 'Delete';
                            }
                        }
                    });
                });
            }
        }
        
    } catch (err) {
        container.querySelector('#doc-grid').innerHTML = `
            <div style="padding: 20px; text-align: center; color: var(--error); width: 100%;">
                Failed to load documents: ${err.message}
            </div>
        `;
    }

    if (isAdmin) {
        const uploadZone = container.querySelector('#upload-zone');
        const fileInput = container.querySelector('#file-input');
        const docTypeSelect = container.querySelector('#doc-type-select');

        uploadZone.addEventListener('click', (e) => {
            // don't trigger file input if clicking the select dropout
            if (e.target !== docTypeSelect) {
                fileInput.click();
            }
        });
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('drag-over');
        });
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('drag-over');
        });
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length) handleUpload(files[0], docTypeSelect.value);
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) handleUpload(e.target.files[0], docTypeSelect.value);
        });
    }
}

async function handleUpload(file, docType) {
    if (!file.name.endsWith('.pdf')) {
        alert('Please upload a PDF file.');
        return;
    }
    const uploadZone = document.querySelector('#upload-zone');
    uploadZone.innerHTML = `
        <div class="upload-icon" style="animation: float 2s ease-in-out infinite;">🦴</div>
        <h3>Uploading ${file.name}...</h3>
        <p>Type: <strong>${docType}</strong> | Uploading to PageIndex cloud engine...</p>
        <div style="width: 200px; height: 4px; background: var(--bg-elevated); border-radius: 4px; margin: var(--space-4) auto; overflow: hidden;">
            <div style="width: 0%; height: 100%; background: var(--accent-gradient); border-radius: 4px; animation: upload-progress 6s ease forwards;"></div>
        </div>
    `;
    
    if (!document.getElementById('upload-anim')) {
        const style = document.createElement('style');
        style.id = 'upload-anim';
        style.textContent = `@keyframes upload-progress { to { width: 100%; } }`;
        document.head.appendChild(style);
    }

    try {
        await api.uploadDocument(file, docType);
        uploadZone.innerHTML = `
            <div class="upload-icon">✅</div>
            <h3>Upload Complete</h3>
            <p>Document is now indexed by PageIndex.</p>
        `;
        setTimeout(() => location.reload(), 1500);
    } catch (err) {
        uploadZone.innerHTML = `
            <div class="upload-icon" style="color: var(--status-error)">❌</div>
            <h3>Upload Failed</h3>
            <p>${err.message}</p>
            <button onclick="location.reload()" class="btn btn-secondary" style="margin-top: 10px;">Retry</button>
        `;
    }
}
