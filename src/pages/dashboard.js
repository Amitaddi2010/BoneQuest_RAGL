// ============================================================
// BoneQuest v2.1 — Dashboard Page (3-Signal Pipeline Status)
// ============================================================

import { api } from '../utils/api.js';
import { auth } from '../utils/auth.js';

export async function renderDashboard(container) {
    const user = auth.user;
    const isAdmin = user && user.role === 'admin';

    container.innerHTML = `
        <div class="dashboard-layout">
            <aside class="sidebar" id="dashboard-sidebar">
                <div class="sidebar-header">
                    <a href="#/" class="logo" style="font-size: var(--text-base);">
                        <span>BoneQuest</span>
                        <span class="version-badge">v2.1</span>
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

            <main class="dashboard-main">
                <div class="dashboard-header">
                    <div>
                        <h1>Document Intelligence Hub</h1>
                        <p>Upload once, then every chat automatically uses the best matching context via 3-signal hybrid retrieval.</p>
                    </div>
                    <div class="dashboard-header-badges">
                        <span class="signal-badge signal-bm25">BM25</span>
                        <span class="signal-badge signal-semantic">Semantic</span>
                        <span class="signal-badge signal-tree">Tree</span>
                    </div>
                </div>

                <div class="stats-grid" id="stats-grid">
                    <div class="stat-card shimmer-gradient">
                        <div class="stat-icon">📄</div>
                        <div class="stat-number">...</div>
                        <div class="stat-desc">Documents Indexed</div>
                    </div>
                </div>

                ${isAdmin ? `
                <div class="upload-zone" id="upload-zone">
                    <div class="upload-icon">📤</div>
                    <h3>Upload Documents (Admin)</h3>
                    <p>Drag and drop PDF, DOCX, or TXT files. Auto-indexed for BM25, Semantic, and Tree signals.</p>
                    <div style="margin-top: 10px; z-index: 10; position: relative;">
                        <label style="font-size: 12px; margin-right: 10px;">Document Type:</label>
                        <select id="doc-type-select" class="input" style="display: inline-block; width: auto; padding: 5px 10px; font-size: 12px;">
                            <option value="guideline">Clinical Guideline</option>
                            <option value="general">Book / Case Study</option>
                        </select>
                    </div>
                    <input type="file" id="file-input" accept=".pdf,.docx,.txt" style="display: none;">
                </div>
                ` : `
                <div style="padding: 15px; background: var(--bg-card); border-radius: 8px; margin-bottom: 20px; font-size: 14px; color: var(--text-dim); border: 1px dashed var(--border-subtle);">
                    <i>Only administrators can upload or delete documents.</i>
                </div>
                `}

                <div class="documents-header">
                    <div>
                        <h3>Indexed Documents</h3>
                        <p style="font-size: 13px; color: var(--text-dim); margin-top: 5px;">Browse available clinical protocols · 3-Signal indexing</p>
                    </div>
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <input type="text" id="doc-search" class="input" placeholder="Search title or type..." style="width: 220px; font-size: 13px;">
                        <span class="badge badge-accent" id="doc-count-badge"><span class="badge-dot"></span> Loading...</span>
                    </div>
                </div>

                <div class="doc-grid" id="doc-grid">
                    <div style="padding: 20px; text-align: center; color: var(--text-dim); width: 100%;">
                        <div class="skeleton-item" style="width: 100%; height: 80px; margin-bottom: 8px;"></div>
                        <div class="skeleton-item" style="width: 100%; height: 80px; margin-bottom: 8px;"></div>
                        Loading document index...
                    </div>
                </div>
            </main>
        </div>
    `;

    // ── Load documents (independent of analytics) ──────────
    let docs = [];
    try {
        const docData = await api.getDocuments();
        docs = docData.documents || [];
    } catch (err) {
        container.querySelector('#doc-grid').innerHTML = `
            <div style="padding: 20px; text-align: center; color: var(--error); width: 100%;">
                Failed to load documents. ${err.message}
            </div>
        `;
        _wireUpload(container, isAdmin, docs);
        return;
    }

    // ── Load analytics (optional, never blocks documents) ──
    let analyticsData = null;
    if (isAdmin) {
        try { analyticsData = await api.getAnalytics(); } catch { analyticsData = null; }
    }

    // ── Stats grid ─────────────────────────────────────────
    const statsGrid = container.querySelector('#stats-grid');
    if (isAdmin && analyticsData) {
        statsGrid.innerHTML = `
            <div class="stat-card">
                <div class="stat-icon">📄</div>
                <div class="stat-number">${docs.length}</div>
                <div class="stat-desc">Documents Indexed</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💬</div>
                <div class="stat-number">${analyticsData.total_queries || 0}</div>
                <div class="stat-desc">Queries Resolved</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-number">${analyticsData.total_users || 0}</div>
                <div class="stat-desc">Active Clinicians</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🎯</div>
                <div class="stat-number">${((analyticsData.average_confidence || 0) * 100).toFixed(1)}%</div>
                <div class="stat-desc">Avg Confidence</div>
            </div>
        `;
    } else {
        statsGrid.innerHTML = `
            <div class="stat-card">
                <div class="stat-icon">📄</div>
                <div class="stat-number">${docs.length}</div>
                <div class="stat-desc">Protocols Indexed</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="font-size: 1.4rem;">🔤</div>
                <div class="stat-number" style="color: var(--signal-bm25);">BM25</div>
                <div class="stat-desc">Keyword Index</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="font-size: 1.4rem;">🧬</div>
                <div class="stat-number" style="color: var(--signal-semantic);">Semantic</div>
                <div class="stat-desc">Embedding Match</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon" style="font-size: 1.4rem;">🌲</div>
                <div class="stat-number" style="color: var(--signal-tree);">Tree</div>
                <div class="stat-desc">Hierarchical RAG</div>
            </div>
        `;
    }

    // ── Document count badge ───────────────────────────────
    container.querySelector('#doc-count-badge').innerHTML =
        `<span class="badge-dot"></span> ${docs.length} document${docs.length !== 1 ? 's' : ''}`;

    // ── Document grid ──────────────────────────────────────
    const docGrid = container.querySelector('#doc-grid');
    if (docs.length === 0) {
        docGrid.innerHTML = `
            <div style="padding: 30px; text-align: center; color: var(--text-dim); width: 100%; border: 1px dashed var(--border-subtle); border-radius: 8px;">
                No documents found. Upload your first file to enable automatic 3-signal context injection.
            </div>
        `;
    } else {
        docGrid.innerHTML = docs.map(doc => `
            <div class="card doc-card" data-doc-id="${doc.id}">
                <div class="doc-card-header">
                    <div class="doc-card-icon">📄</div>
                    <div>
                        <span class="doc-card-status ${doc.status}">${doc.status === 'indexed' ? 'Indexed' : doc.status === 'error' ? 'Error' : 'Processing'}</span>
                        <span class="doc-type-badge" style="font-size:10px; margin-left:5px; padding: 2px 6px; border-radius: 10px;
                            background: ${doc.doc_type === 'guideline' ? 'rgba(34,197,94,0.1)' : 'rgba(59,130,246,0.1)'};
                            color: ${doc.doc_type === 'guideline' ? 'var(--success)' : '#60a5fa'};
                            text-transform: uppercase;">
                            ${doc.doc_type || 'general'}
                        </span>
                    </div>
                </div>
                <h4 class="doc-title">${doc.title}</h4>
                <div class="doc-signals-row">
                    <span class="signal-badge signal-bm25" style="font-size:8px;padding:1px 6px;">BM25 ✓</span>
                    <span class="signal-badge signal-semantic" style="font-size:8px;padding:1px 6px;">Embed ✓</span>
                    <span class="signal-badge signal-tree" style="font-size:8px;padding:1px 6px;">Tree ✓</span>
                </div>
                <div class="doc-card-meta" style="justify-content: space-between; align-items: center; margin-top: 12px;">
                    <span>Last used: ${doc.last_queried || 'Recently'}</span>
                    ${isAdmin ? `
                        <button class="btn-delete-doc" data-id="${doc.id}"
                            style="background: none; border: 1px solid var(--error); color: var(--error);
                                   border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer;">
                            Delete
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');

        // Search
        const searchInput = container.querySelector('#doc-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                container.querySelectorAll('.doc-card').forEach(card => {
                    const title = card.querySelector('.doc-title').textContent.toLowerCase();
                    const type = card.querySelector('.doc-type-badge').textContent.toLowerCase();
                    card.style.display = (title.includes(term) || type.includes(term)) ? 'flex' : 'none';
                });
            });
        }

        // Delete handlers
        if (isAdmin) {
            container.querySelectorAll('.btn-delete-doc').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (!confirm('Delete this document from library?')) return;
                    try {
                        btn.textContent = '...';
                        await api.deleteDocument(btn.dataset.id);
                        renderDashboard(container);
                    } catch (err) {
                        alert('Delete failed: ' + err.message);
                        btn.textContent = 'Delete';
                    }
                });
            });
        }
    }

    _wireUpload(container, isAdmin, docs);
}

function _wireUpload(container, isAdmin, docs) {
    if (!isAdmin) return;
    const uploadZone  = container.querySelector('#upload-zone');
    const fileInput   = container.querySelector('#file-input');
    const docTypeSelect = container.querySelector('#doc-type-select');
    if (!uploadZone || !fileInput) return;

    uploadZone.addEventListener('click', (e) => {
        if (e.target.closest('#doc-type-select')) return;
        fileInput.click();
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
        const file = e.dataTransfer.files[0];
        if (file) _handleUpload(uploadZone, fileInput, file, docTypeSelect.value);
    });
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) _handleUpload(uploadZone, fileInput, file, docTypeSelect.value);
    });
}

async function _handleUpload(uploadZone, fileInput, file, docType) {
    if (!/\.(pdf|docx|txt)$/i.test(file.name)) {
        alert('Supported file types: PDF, DOCX, TXT');
        return;
    }

    uploadZone.innerHTML = `
        <div class="upload-icon">🦴</div>
        <h3>Uploading ${file.name}...</h3>
        <p>Type: <strong>${docType}</strong> · Indexing for BM25 + Semantic + Tree</p>
        <div style="width: 200px; height: 4px; background: var(--bg-elevated); border-radius: 4px; margin: 12px auto; overflow: hidden;">
            <div style="width: 0%; height: 100%; background: var(--accent-gradient); border-radius: 4px; animation: _bq_upload_progress 8s ease forwards;"></div>
        </div>
    `;

    if (!document.getElementById('_bq_upload_style')) {
        const s = document.createElement('style');
        s.id = '_bq_upload_style';
        s.textContent = '@keyframes _bq_upload_progress { to { width: 95%; } }';
        document.head.appendChild(s);
    }

    try {
        await api.uploadDocument(file, docType);
        uploadZone.innerHTML = `
            <div class="upload-icon">✅</div>
            <h3>Upload Complete</h3>
            <p><strong>${file.name}</strong> is now indexed across all 3 retrieval signals.</p>
        `;
        setTimeout(() => location.reload(), 1500);
    } catch (err) {
        uploadZone.innerHTML = `
            <div class="upload-icon">❌</div>
            <h3>Upload Failed</h3>
            <p style="color: var(--error);">${err.message}</p>
            <button onclick="location.reload()" class="btn btn-secondary" style="margin-top: 10px;">Retry</button>
        `;
    }
}
