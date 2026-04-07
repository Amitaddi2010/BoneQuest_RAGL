// ============================================================
// BoneQuest v2 — AI Chat Page (V2: Thinking Block + Rich Citations + Sections)
// ============================================================

import { api }    from '../utils/api.js';
import { auth }   from '../utils/auth.js';
import { marked }  from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';

const SUGGESTIONS = [
    "Management of comminuted tibial shaft fracture in a diabetic patient?",
    "ACL reconstruction rehabilitation protocol — week by week timeline?",
    "Treatment for displaced femoral neck fracture in 75yo with CHF?",
    "Compare anterolateral vs medial approach for total hip arthroplasty?"
];

// ── Section icons & display names ─────────────────────────
const SECTION_MAP = {
    '📋': { label: 'Clinical Recommendation', color: 'var(--accent-primary)' },
    '🔬': { label: 'Guideline Evidence',       color: '#06b6d4' },
    '💡': { label: 'Clinical Reasoning',       color: '#f59e0b' },
    '⚠️': { label: 'Considerations',           color: '#ef4444' },
    '🎯': { label: 'Key Takeaway',             color: '#10b981' },
};

const SECTION_REGEX = /^(📋|🔬|💡|⚠️|🎯)\s+[A-Z\s]+$/m;

let currentSessionId = null;
let currentRole      = auth.role || 'resident';
let isLoading        = false;
let sessions         = [];
let lastUserMessage  = '';   // for regenerate

export function renderChat(container) {
    container.innerHTML = `
        <div class="chat-layout">
            <!-- Session History Sidebar -->
            <aside class="chat-sidebar" id="chat-sidebar">
                <div class="sidebar-top">
                    <button class="btn btn-primary btn-full new-chat-btn" id="new-chat-btn">
                         <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        <span>New Consult</span>
                    </button>
                </div>
                <div class="session-list" id="session-list">
                    <div class="session-loading">
                        <div class="skeleton-item"></div>
                        <div class="skeleton-item"></div>
                        <div class="skeleton-item"></div>
                    </div>
                </div>
                <div class="sidebar-bottom">
                    <div class="sidebar-user-card glass">
                        <div class="sidebar-user-avatar">${(auth.user?.full_name || 'U')[0].toUpperCase()}</div>
                        <div class="sidebar-user-info">
                            <span class="sidebar-user-name">${auth.user?.full_name || 'Clinician'}</span>
                            <span class="sidebar-user-role">${auth.role === 'resident' ? 'Orthopaedic Resident' : auth.role}</span>
                        </div>
                    </div>
                </div>
            </aside>

            <!-- Chat Main Area -->
            <div class="chat-main">
                <div class="chat-header" id="chat-header">
                    <button class="btn btn-ghost sidebar-toggle" id="sidebar-toggle">☰</button>
                    <div class="chat-header-info">
                        <h3 id="chat-title">New Chat</h3>
                        <span class="chat-header-model">Groq LLaMA · PageIndex RAG · V2</span>
                    </div>
                    <div class="chat-header-actions" style="margin-left: auto;">
                        <button class="btn btn-ghost" id="export-ehr-btn" title="Export as Clinical Report" style="display:none; font-size: 13px; font-weight: 600; color: var(--accent-light);">📄 Export EHR</button>
                    </div>
                </div>

                <div class="chat-messages" id="chat-messages">
                    <div class="chat-welcome" id="chat-welcome">
                        <div class="welcome-badge">
                            <span class="badge-dot"></span>
                            Clinical AI Active · V2
                        </div>
                        <div class="welcome-icon-large">
                            <div class="icon-glow"></div>
                            🦴
                        </div>
                        <h2 class="text-gradient">BoneQuest Assistant</h2>
                        <p>Specialized orthopaedic RAG engine with visible reasoning, structured evidence, and guideline validation.</p>
                        <div class="welcome-suggestions" id="suggestions">
                            ${SUGGESTIONS.map(s => `
                                <button class="suggestion-chip" data-suggestion="${s}">
                                    <span class="suggestion-icon">⚕️</span>
                                    <span class="suggestion-text">${s}</span>
                                </button>
                            `).join('')}
                        </div>
                    </div>
                </div>

                <div class="chat-input-area">
                    <div class="chat-input-wrapper">
                        <button class="chat-attach-btn" id="image-attach-btn" title="Upload X-ray / MRI">
                            <span>📎</span>
                        </button>
                        <button class="chat-mic-btn" id="chat-mic-btn" title="Clinical Voice Dictation">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="22"></line></svg>
                        </button>
                        <textarea class="chat-input" id="chat-input" placeholder="Dictate findings, ask about protocols, upload X-rays..." rows="1"></textarea>
                        <button class="chat-send-btn" id="chat-send" title="Send message">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>
                        </button>
                    </div>
                    <input type="file" id="image-file-input" accept="image/*" style="display:none;">
                    <div class="image-preview-area" id="image-preview" style="display:none;">
                        <div class="image-preview-card" id="image-preview-card"></div>
                    </div>
                    <div class="chat-disclaimer">
                        AI-assisted clinical decision support. Always verify with institutional guidelines.
                    </div>
                </div>
            </div>

            <!-- Right Panel: Reasoning Trace & Anatomy -->
            <aside class="reasoning-panel" id="reasoning-panel">
                <div class="reasoning-header" style="flex-direction: column; align-items: stretch; padding-bottom: 0;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4);">
                        <h3>🔬 Analysis & Context</h3>
                        <span class="badge badge-accent" style="font-size: 10px;">Live</span>
                    </div>
                    <div class="panel-tabs">
                        <button class="panel-tab active" data-target="trace-content">Trace</button>
                        <button class="panel-tab" data-target="patient-context">Anatomy</button>
                    </div>
                </div>
                <div class="panel-body">
                    <!-- Tab 1: Reasoning Trace -->
                    <div id="trace-content" class="tab-content active">
                        <p class="trace-placeholder">Send a query to see reasoning steps...</p>
                    </div>
                    <!-- Tab 2: Anatomy Selector -->
                    <div id="patient-context" class="tab-content" style="display: none;">
                        <div class="anatomy-widget">
                            <h4 style="margin-bottom: var(--space-4); font-size: var(--text-sm); color: var(--text-secondary); text-align: center;">Interactive Body Map</h4>
                            <div class="anatomy-svg-wrapper">
                                <svg viewBox="0 0 100 200" class="anatomy-svg">
                                    <defs>
                                        <radialGradient id="bone-glow" cx="50%" cy="50%" r="50%">
                                            <stop offset="0%" stop-color="var(--accent-light)" stop-opacity="0.6" />
                                            <stop offset="100%" stop-color="var(--accent-light)" stop-opacity="0" />
                                        </radialGradient>
                                    </defs>
                                    <circle cx="50" cy="20" r="12" class="bone-zone" data-prompt="What are the protocols for traumatic brain injury and skull fractures?"/>
                                    <rect x="44" y="35" width="12" height="40" rx="3" class="bone-zone" data-prompt="Show AAOS guidelines for cervical and lumbar spine trauma."/>
                                    <path d="M35,75 L65,75 L58,95 L42,95 Z" class="bone-zone" data-prompt="Latest recommendations for pelvic ring fractures and acetabulum?"/>
                                    <line x1="42" y1="42" x2="15" y2="65" stroke-width="8" class="bone-zone" data-prompt="Protocols for proximal humerus fractures in elderly?" stroke-linecap="round"/>
                                    <line x1="58" y1="42" x2="85" y2="65" stroke-width="8" class="bone-zone" data-prompt="Protocols for proximal humerus fractures in elderly?" stroke-linecap="round"/>
                                    <circle cx="12" cy="72" r="5" class="bone-zone" data-prompt="Distal radius fracture management algorithm?"/>
                                    <circle cx="88" cy="72" r="5" class="bone-zone" data-prompt="Distal radius fracture management algorithm?"/>
                                    <line x1="45" y1="95" x2="32" y2="135" stroke-width="10" class="bone-zone" data-prompt="Management of displaced femoral neck fracture?" stroke-linecap="round"/>
                                    <line x1="55" y1="95" x2="68" y2="135" stroke-width="10" class="bone-zone" data-prompt="Management of displaced femoral neck fracture?" stroke-linecap="round"/>
                                    <circle cx="32" cy="140" r="6" class="bone-zone" data-prompt="Post-op protocol for total knee arthroplasty?"/>
                                    <circle cx="68" cy="140" r="6" class="bone-zone" data-prompt="Post-op protocol for total knee arthroplasty?"/>
                                    <line x1="32" y1="145" x2="32" y2="185" stroke-width="8" class="bone-zone" data-prompt="Comminuted tibial shaft fracture treatment options?" stroke-linecap="round"/>
                                    <line x1="68" y1="145" x2="68" y2="185" stroke-width="8" class="bone-zone" data-prompt="Comminuted tibial shaft fracture treatment options?" stroke-linecap="round"/>
                                    <ellipse cx="32" cy="192" rx="10" ry="5" class="bone-zone" data-prompt="Operative indications for calcaneus fractures?"/>
                                    <ellipse cx="68" cy="192" rx="10" ry="5" class="bone-zone" data-prompt="Operative indications for calcaneus fractures?"/>
                                </svg>
                            </div>
                            <p style="font-size: 11px; color: var(--text-dim); text-align: center; margin-top: var(--space-6); padding: 0 var(--space-4);">Select a region to load clinical trauma protocols.</p>
                        </div>
                    </div>
                </div>
            </aside>
        </div>
    `;

    // ── Element References ──────────────────────────────────
    const chatInput      = container.querySelector('#chat-input');
    const sendBtn        = container.querySelector('#chat-send');
    const messagesEl     = container.querySelector('#chat-messages');
    const sessionList    = container.querySelector('#session-list');
    const newChatBtn     = container.querySelector('#new-chat-btn');
    const imageInput     = container.querySelector('#image-file-input');
    const imageAttachBtn = container.querySelector('#image-attach-btn');
    const imagePreview   = container.querySelector('#image-preview');
    const sidebarToggle  = container.querySelector('#sidebar-toggle');
    const sidebar        = container.querySelector('#chat-sidebar');
    const micBtn         = container.querySelector('#chat-mic-btn');
    const exportEhrBtn   = container.querySelector('#export-ehr-btn');

    let pendingImage  = null;
    let isRecording   = false;
    let recognition   = null;

    // ── Speech Recognition ──────────────────────────────────
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SR();
        recognition.continuous    = false;
        recognition.interimResults = true;
        recognition.onstart  = () => { isRecording = true; micBtn.classList.add('recording'); chatInput.placeholder = "Listening..."; };
        recognition.onresult = (e) => {
            let t = '';
            for (let i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
            chatInput.value = t;
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
        };
        recognition.onerror = () => stopRecording();
        recognition.onend   = () => { stopRecording(); if (chatInput.value.trim()) sendMessage(); };
    }

    function stopRecording() {
        if (isRecording && recognition) recognition.stop();
        isRecording = false;
        micBtn.classList.remove('recording');
        chatInput.placeholder = "Dictate findings, ask about protocols, upload X-rays...";
    }

    micBtn.addEventListener('click', () => {
        if (!recognition) { alert("Speech recognition not supported. Try Chrome, Edge or Safari."); return; }
        isRecording ? stopRecording() : (chatInput.value = '', recognition.start());
    });

    // ── EHR Export ─────────────────────────────────────────
    exportEhrBtn.addEventListener('click', () => {
        if (!currentSessionId) return;
        const msgElements = messagesEl.querySelectorAll('.message');
        if (!msgElements.length) return;
        let report = `${'='.repeat(56)}\n       BONEQUEST CLINICAL CONSULTATION V2\n${'='.repeat(56)}\n\n`;
        report += `Date: ${new Date().toLocaleString()}\nClinician: ${auth.user?.full_name || auth.user?.email}\nSession ID: ${currentSessionId}\n\n${'-'.repeat(56)}\n\n`;
        msgElements.forEach(msg => {
            const isUser = msg.classList.contains('message-user');
            const label  = isUser ? "CLINICIAN QUERY" : "AI DECISION SUPPORT";
            const text   = msg.querySelector('.message-bubble')?.innerText || '';
            report += `[${label}]\n${text}\n\n`;
            if (!isUser) {
                const conf = msg.querySelector('.confidence-badge');
                if (conf) report += `   >> ${conf.innerText}\n`;
                const cits = msg.querySelectorAll('.citation-card-title');
                if (cits.length) { report += `   >> References: `; cits.forEach(c => report += c.innerText + " | "); report += "\n"; }
                report += `\n${'-'.repeat(56)}\n\n`;
            }
        });
        report += "\nDISCLAIMER: AI-assisted consultation. Always verify protocols.\n";
        const blob = new Blob([report], { type: 'text/plain' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url; a.download = `BoneQuest_V2_${Date.now()}.txt`; a.click();
        URL.revokeObjectURL(url);
    });

    // ── Auto-resize textarea ────────────────────────────────
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
    });

    // ── Sidebar toggle ──────────────────────────────────────
    sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));

    // ── Image attachment ────────────────────────────────────
    imageAttachBtn.addEventListener('click', () => imageInput.click());
    imageInput.addEventListener('change', (e) => {
        const file = e.target.files[0]; if (!file) return;
        pendingImage = file; showImagePreview(file);
    });

    function showImagePreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const card = container.querySelector('#image-preview-card');
            card.innerHTML = `
                <img src="${e.target.result}" alt="Preview" class="preview-thumb">
                <div class="preview-info">
                    <span class="preview-name">${file.name}</span>
                    <span class="preview-size">${(file.size/1024).toFixed(0)} KB</span>
                </div>
                <button class="preview-remove" id="remove-image">✕</button>
            `;
            imagePreview.style.display = 'block';
            card.querySelector('#remove-image').addEventListener('click', () => {
                pendingImage = null; imagePreview.style.display = 'none'; imageInput.value = '';
            });
        };
        reader.readAsDataURL(file);
    }

    // ── Panel Tabs ──────────────────────────────────────────
    container.querySelectorAll('.panel-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            container.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            container.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
            container.querySelector(`#${tab.dataset.target}`).style.display = 'block';
        });
    });

    // ── Anatomy selector ────────────────────────────────────
    container.querySelectorAll('.bone-zone').forEach(bone => {
        bone.addEventListener('click', () => {
            chatInput.value = bone.dataset.prompt;
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
            chatInput.focus();
        });
    });

    // ── Suggestion chips ────────────────────────────────────
    container.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => { chatInput.value = chip.dataset.suggestion; sendMessage(); });
    });

    // ── Send handlers ───────────────────────────────────────
    chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });
    sendBtn.addEventListener('click', sendMessage);
    newChatBtn.addEventListener('click', () => startNewChat());

    // ── Load sessions ───────────────────────────────────────
    loadSessions();

    // ════════════════════════════════════════════════════════
    // CORE FUNCTIONS
    // ════════════════════════════════════════════════════════

    async function loadSessions() {
        try {
            const result = await api.listSessions();
            sessions = result.sessions || [];
            renderSessionList();
        } catch {
            sessionList.innerHTML = '<div class="session-empty">Failed to load sessions</div>';
        }
    }

    function renderSessionList() {
        if (!sessions.length) {
            sessionList.innerHTML = '<div class="session-empty">No conversations yet.<br>Start a new chat!</div>';
            return;
        }
        sessionList.innerHTML = sessions.map(s => `
            <div class="session-item ${s.id === currentSessionId ? 'active' : ''}" data-session-id="${s.id}">
                <div class="session-item-content">
                    <div class="session-item-title">${escapeHtml(s.title || 'New Chat')}</div>
                    <div class="session-item-meta">
                        <span>${s.message_count || 0} msgs</span>
                        <span>${formatDate(s.updated_at)}</span>
                    </div>
                </div>
                <button class="session-delete-btn" data-delete-id="${s.id}" title="Delete">🗑</button>
            </div>
        `).join('');

        sessionList.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('.session-delete-btn')) return;
                loadSession(item.dataset.sessionId);
                sidebar.classList.remove('open');
            });
        });
        sessionList.querySelectorAll('.session-delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.dataset.deleteId;
                if (confirm('Delete this conversation?')) {
                    await api.deleteSession(id);
                    if (currentSessionId === id) { currentSessionId = null; showWelcome(); }
                    await loadSessions();
                }
            });
        });
    }

    async function loadSession(sessionId) {
        currentSessionId = sessionId;
        renderSessionList();
        const session = sessions.find(s => s.id === sessionId);
        if (session) container.querySelector('#chat-title').textContent = session.title || 'Chat';

        try {
            const result = await api.getSessionMessages(sessionId);
            const welcome = container.querySelector('#chat-welcome');
            if (welcome) welcome.remove();
            messagesEl.innerHTML = '';
            for (const msg of (result.messages || [])) {
                if (msg.role === 'user') {
                    addUserMessage(msg.content);
                } else {
                    addAiMessageComplete(msg.content, msg.confidence_score, msg.citations, msg.id, msg.user_feedback);
                }
            }
            messagesEl.scrollTop = messagesEl.scrollHeight;
            exportEhrBtn.style.display = result.messages?.length ? 'block' : 'none';
        } catch (err) {
            console.error('Failed to load messages:', err);
        }
    }

    function showWelcome() {
        container.querySelector('#chat-title').textContent = 'New Chat';
        exportEhrBtn.style.display = 'none';
        messagesEl.innerHTML = `
            <div class="chat-welcome" id="chat-welcome">
                <div class="welcome-icon-large">🦴</div>
                <h2>BoneQuest AI</h2>
                <p>Clinical-grade orthopaedic decision support with guideline validation.</p>
                <div class="welcome-suggestions">
                    ${SUGGESTIONS.map(s => `<button class="suggestion-chip" data-suggestion="${s}"><span class="suggestion-icon">⚕️</span><span>${s}</span></button>`).join('')}
                </div>
            </div>
        `;
        messagesEl.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => { chatInput.value = chip.dataset.suggestion; sendMessage(); });
        });
    }

    async function startNewChat() {
        currentSessionId = null;
        showWelcome();
        renderSessionList();
        chatInput.focus();
    }

    // ── MAIN SEND MESSAGE ───────────────────────────────────
    async function sendMessage() {
        const text = chatInput.value.trim();
        if ((!text && !pendingImage) || isLoading) return;

        const welcome = container.querySelector('#chat-welcome');
        if (welcome) welcome.remove();

        if (!currentSessionId) {
            try {
                const session = await api.createSession({ title: text.slice(0, 80) });
                currentSessionId = session.id;
                container.querySelector('#chat-title').textContent = session.title;
                await loadSessions();
            } catch (err) {
                console.error('Failed to create session:', err);
                return;
            }
        }
        exportEhrBtn.style.display = 'block';

        if (pendingImage) { await handleImageUpload(text); return; }

        lastUserMessage = text;
        addUserMessage(text);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        isLoading = true;
        sendBtn.disabled = true;

        // Reset trace panel
        const traceContent = container.querySelector('#trace-content');
        traceContent.innerHTML = '<div class="trace-steps"></div>';

        // Create streaming AI message shell
        const msgEl      = createStreamingMessageShell();
        const thinkingEl = msgEl.querySelector('.thinking-block');
        const thinkingBody = msgEl.querySelector('.thinking-body');
        const bubble     = msgEl.querySelector('#streaming-bubble');
        const meta       = msgEl.querySelector('#streaming-meta');

        let fullText     = '';
        let liveTrace    = [];
        let liveCitations = [];
        let confidence   = 0;
        let finalMsgId   = null;
        let thinkingDone = false;

        try {
            for await (const event of api.streamChatMessage({
                session_id:  currentSessionId,
                message:     text,
                role:        currentRole,
                document_id: 'doc-1'
            })) {

                // ── Thinking block ──────────────────────────
                if (event.type === 'thinking') {
                    appendThinkingLine(thinkingBody, event.data);
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                }
                else if (event.type === 'thinking_done') {
                    collapseThinkingBlock(thinkingEl);
                    thinkingDone = true;
                }

                // ── Trace steps ─────────────────────────────
                else if (event.type === 'trace') {
                    try {
                        const traceData = JSON.parse(event.data);
                        liveTrace.push(traceData);
                        updateTracePanel(liveTrace, liveCitations, confidence);
                    } catch {}
                }

                // ── Streaming tokens ─────────────────────────
                else if (event.type === 'token') {
                    fullText += event.data;
                    renderStreamingContent(bubble, fullText);
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                }

                // ── Rich citations ───────────────────────────
                else if (event.type === 'citation') {
                    try {
                        liveCitations = JSON.parse(event.data);
                        updateTracePanel(liveTrace, liveCitations, confidence);
                    } catch {}
                }

                // ── Confidence score ─────────────────────────
                else if (event.type === 'confidence') {
                    confidence = parseFloat(event.data);
                    updateTracePanel(liveTrace, liveCitations, confidence);
                }

                // ── Message ID (finalize meta) ───────────────
                else if (event.type === 'message_id') {
                    finalMsgId = event.data;
                }

                // ── Error ────────────────────────────────────
                else if (event.type === 'error') {
                    throw new Error(event.data);
                }
            }

            // Finalize: parse sections, render citations, action toolbar
            finalizeAiMessage(msgEl, bubble, meta, fullText, confidence, liveCitations, finalMsgId);

            // Ensure thinking block is collapsed at end
            if (!thinkingDone) collapseThinkingBlock(thinkingEl);

        } catch (err) {
            console.error('Stream error:', err);
            bubble.innerHTML = renderMarkdown('⚠️ Failed to generate response. Please try again.');
            if (meta) meta.style.display = 'none';
        }

        isLoading = false;
        sendBtn.disabled = false;
        messagesEl.scrollTop = messagesEl.scrollHeight;
        await loadSessions();
    }

    // ── Create the AI message skeleton (with thinking block) ─
    function createStreamingMessageShell() {
        const msgEl = document.createElement('div');
        msgEl.className = 'message message-ai';
        msgEl.innerHTML = `
            <div class="message-avatar message-avatar-ai">🦴</div>
            <div class="message-content">
                <!-- Thinking block (Claude-style) -->
                <div class="thinking-block" id="thinking-block">
                    <button class="thinking-header" id="thinking-toggle">
                        <span class="thinking-icon">🧠</span>
                        <span class="thinking-label">BoneQuest is reasoning...</span>
                        <span class="thinking-spinner"></span>
                        <svg class="thinking-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </button>
                    <div class="thinking-body" id="thinking-body"></div>
                </div>
                <!-- Streaming response bubble -->
                <div class="message-bubble" id="streaming-bubble">
                    <div class="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
                </div>
                <div class="message-meta" id="streaming-meta" style="display:none;"></div>
            </div>
        `;
        messagesEl.appendChild(msgEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        // Thinking block toggle
        const toggle = msgEl.querySelector('#thinking-toggle');
        const body   = msgEl.querySelector('#thinking-body');
        toggle.addEventListener('click', () => {
            const isOpen = !body.classList.contains('collapsed');
            body.classList.toggle('collapsed', isOpen);
            toggle.classList.toggle('collapsed', isOpen);
        });

        return msgEl;
    }

    // ── Append a thinking step line ─────────────────────────
    function appendThinkingLine(thinkingBody, line) {
        const trimmed = line.trim();
        if (!trimmed) return;
        const step = document.createElement('div');
        step.className = 'thinking-step';
        step.textContent = trimmed;
        thinkingBody.appendChild(step);
    }

    // ── Collapse thinking block when response starts ────────
    function collapseThinkingBlock(thinkingEl) {
        const label   = thinkingEl.querySelector('.thinking-label');
        const spinner = thinkingEl.querySelector('.thinking-spinner');
        const body    = thinkingEl.querySelector('.thinking-body');
        const toggle  = thinkingEl.querySelector('.thinking-header');
        if (label)   label.textContent = "BoneQuest's Reasoning (tap to expand)";
        if (spinner) spinner.style.display = 'none';
        if (body)    body.classList.add('collapsed');
        if (toggle)  toggle.classList.add('collapsed');
    }

    // ── Render streaming content — parse sections on-the-fly ─
    function renderStreamingContent(bubble, fullText) {
        if (hasSections(fullText)) {
            bubble.innerHTML = renderSections(fullText, true /* streaming */);
        } else {
            bubble.innerHTML = renderMarkdown(fullText);
        }
    }

    // ── Finalize after stream completes ────────────────────
    function finalizeAiMessage(msgEl, bubble, meta, fullText, confidence, citations, messageId) {
        // Parse and render structured sections
        if (hasSections(fullText)) {
            bubble.innerHTML = renderSections(fullText, false);
            // Attach toggle listeners
            bubble.querySelectorAll('.section-header').forEach(header => {
                header.addEventListener('click', () => {
                    const section = header.closest('.response-section');
                    section.classList.toggle('open');
                });
            });
        } else {
            bubble.innerHTML = renderMarkdown(fullText);
        }

        // Confidence badge
        let metaHtml = '';
        if (confidence) {
            const level = confidence > 0.85 ? 'high' : confidence > 0.6 ? 'medium' : 'low';
            const pct   = (confidence * 100).toFixed(0);
            metaHtml += `<span class="confidence-badge confidence-${level}">🎯 ${pct}% Confidence</span>`;
        }

        // Rich citations panel
        if (citations && citations.length) {
            metaHtml += renderCitationsPanel(citations);
        }

        // Feedback + Action toolbar
        if (messageId) {
            metaHtml += renderActionToolbar(messageId, fullText);
        }

        if (metaHtml) {
            meta.innerHTML = metaHtml;
            meta.style.display = 'flex';
            meta.style.flexDirection = 'column';
            meta.style.gap = '8px';
        }

        // Wire feedback buttons
        if (messageId) wireFeedbackButtons(meta, messageId);

        // Wire action toolbar
        wireActionToolbar(meta, fullText, () => {
            chatInput.value = lastUserMessage;
            sendMessage();
        });

        // Wire citation expansion
        wireCitationCards(meta);
    }

    // ── Check if response has section headers ───────────────
    function hasSections(text) {
        return /^(📋|🔬|💡|⚠️|🎯)\s+/m.test(text);
    }

    // ── Parse and render structured sections ───────────────
    function renderSections(text, isStreaming) {
        const sectionEmojis = ['📋', '🔬', '💡', '⚠️', '🎯'];
        const lines = text.split('\n');
        const sections = [];
        let currentSection = null;

        for (const line of lines) {
            const emojiMatch = sectionEmojis.find(e => line.trim().startsWith(e));
            if (emojiMatch) {
                if (currentSection) sections.push(currentSection);
                currentSection = { emoji: emojiMatch, title: line.trim(), body: [] };
            } else if (currentSection) {
                currentSection.body.push(line);
            }
        }
        if (currentSection) sections.push(currentSection);

        // Filter out empty sections
        const validSections = sections.filter(sec => sec.body.join('\n').trim().length > 0);

        if (!validSections.length) return renderMarkdown(text);

        return validSections.map((sec, idx) => {
            const bodyText = sec.body.join('\n').trim();
            // First section open, rest collapsed (unless streaming — all open)
            const isOpen = isStreaming ? true : idx === 0;
            return `
                <div class="response-section ${isOpen ? 'open' : ''}">
                    <button class="section-header">
                        <span class="section-emoji">${sec.emoji}</span>
                        <span class="section-title">${sec.title.replace(sec.emoji, '').trim()}</span>
                        <svg class="section-chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </button>
                    <div class="section-body">${renderMarkdown(bodyText)}</div>
                </div>
            `;
        }).join('');
    }

    // ── Render rich citations panel ─────────────────────────
    function renderCitationsPanel(citations) {
        const STRENGTH_BADGE = {
            strong:       'evidence-strong',
            moderate:     'evidence-moderate',
            limited:      'evidence-limited',
            inconclusive: 'evidence-inconclusive'
        };

        const cardsHtml = citations.map((c, idx) => {
            // Support both rich objects and legacy plain strings
            if (typeof c === 'string') {
                return `<div class="citation-card">
                    <div class="citation-card-header">
                        <span class="citation-card-title">📄 ${c}</span>
                        <span class="evidence-badge evidence-moderate">Moderate</span>
                    </div>
                </div>`;
            }
            const badgeClass = STRENGTH_BADGE[c.evidence_strength] || 'evidence-moderate';
            const strength   = c.evidence_strength
                ? c.evidence_strength.charAt(0).toUpperCase() + c.evidence_strength.slice(1)
                : 'Moderate';

            return `
                <div class="citation-card" data-idx="${idx}">
                    <div class="citation-card-header">
                        <div class="citation-card-info">
                            <span class="citation-card-title">${escapeHtml(c.section || c.guideline || 'Reference')}</span>
                            <span class="citation-card-sub">${escapeHtml(c.guideline || '')}${c.page_range ? ' · ' + c.page_range : ''}</span>
                        </div>
                        <span class="evidence-badge ${badgeClass}">${strength}</span>
                    </div>
                    ${c.reasoning ? `
                    <div class="citation-reasoning" style="display:none;">
                        <p><strong>Why this applies:</strong> ${escapeHtml(c.reasoning)}</p>
                    </div>` : ''}
                </div>
            `;
        }).join('');

        return `
            <div class="citations-panel">
                <div class="citations-panel-header">
                    <span>📚 Clinical Evidence & Guidelines</span>
                    <span class="citations-count">${citations.length} source${citations.length !== 1 ? 's' : ''}</span>
                </div>
                <div class="citations-list">${cardsHtml}</div>
            </div>
        `;
    }

    // ── Render action toolbar ───────────────────────────────
    function renderActionToolbar(messageId, fullText) {
        return `
            <div class="message-actions" data-msg-id="${messageId}">
                <button class="action-btn copy-btn" title="Copy response">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    Copy
                </button>
                <button class="action-btn regen-btn" title="Regenerate response">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                    Regenerate
                </button>
                <div class="feedback-actions" data-id="${messageId}" style="margin-left: auto;">
                    <button class="btn-feedback" data-score="1" title="Clinician Validated">👍</button>
                    <button class="btn-feedback" data-score="-1" title="Incorrect">👎</button>
                </div>
            </div>
        `;
    }

    // ── Wire citation card expand/collapse ──────────────────
    function wireCitationCards(container) {
        container.querySelectorAll('.citation-card').forEach(card => {
            const reasoning = card.querySelector('.citation-reasoning');
            if (!reasoning) return;
            card.addEventListener('click', () => {
                const isOpen = reasoning.style.display !== 'none';
                reasoning.style.display = isOpen ? 'none' : 'block';
                card.classList.toggle('expanded', !isOpen);
            });
        });
    }

    // ── Wire feedback buttons ───────────────────────────────
    function wireFeedbackButtons(metaEl, messageId) {
        metaEl.querySelectorAll('.btn-feedback').forEach(btn => {
            btn.addEventListener('click', async () => {
                const score = parseInt(btn.dataset.score);
                try {
                    await api.sendFeedback(messageId, score);
                    metaEl.querySelectorAll('.btn-feedback').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const parent = btn.parentElement;
                    const existing = parent.querySelector('.validated-label');
                    if (score === 1 && !existing) {
                        parent.insertAdjacentHTML('beforeend', '<span class="validated-label">✓ Clinician Validated</span>');
                    } else if (score === -1 && existing) {
                        existing.remove();
                    }
                } catch {}
            });
        });
    }

    // ── Wire action toolbar buttons ─────────────────────────
    function wireActionToolbar(metaEl, fullText, onRegenerate) {
        const copyBtn  = metaEl.querySelector('.copy-btn');
        const regenBtn = metaEl.querySelector('.regen-btn');

        if (copyBtn) {
            copyBtn.addEventListener('click', async () => {
                try {
                    await navigator.clipboard.writeText(fullText);
                    copyBtn.textContent = '✓ Copied!';
                    setTimeout(() => { copyBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg> Copy`; }, 2000);
                } catch {}
            });
        }
        if (regenBtn) {
            regenBtn.addEventListener('click', () => {
                if (isLoading) return;
                chatInput.value = lastUserMessage;
                sendMessage();
            });
        }
    }

    // ── Add static user message bubble ─────────────────────
    function addUserMessage(content) {
        const msg = document.createElement('div');
        msg.className = 'message message-user';
        msg.innerHTML = `
            <div class="message-avatar message-avatar-user">${(auth.user?.full_name || 'U')[0].toUpperCase()}</div>
            <div class="message-content">
                <div class="message-bubble">${escapeHtml(content)}</div>
            </div>
        `;
        messagesEl.appendChild(msg);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    // ── Add completed AI message (used when loading session) ─
    function addAiMessageComplete(content, confidence, citations, messageId, feedbackScore) {
        const msg = document.createElement('div');
        msg.className = 'message message-ai';

        let bubbleHtml = hasSections(content) ? renderSections(content, false) : renderMarkdown(content);

        let metaHtml = '';
        if (confidence) {
            const level = confidence > 0.85 ? 'high' : confidence > 0.6 ? 'medium' : 'low';
            metaHtml += `<span class="confidence-badge confidence-${level}">🎯 ${(confidence * 100).toFixed(0)}% Confidence</span>`;
        }
        if (citations && citations.length) {
            metaHtml += renderCitationsPanel(citations);
        }
        if (messageId) {
            const upActive   = feedbackScore === 1  ? 'active' : '';
            const downActive = feedbackScore === -1 ? 'active' : '';
            metaHtml += `
                <div class="message-actions" data-msg-id="${messageId}">
                    <button class="action-btn copy-btn" title="Copy">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                        Copy
                    </button>
                    <div class="feedback-actions" data-id="${messageId}" style="margin-left: auto;">
                        <button class="btn-feedback ${upActive}" data-score="1">👍</button>
                        <button class="btn-feedback ${downActive}" data-score="-1">👎</button>
                        ${feedbackScore === 1 ? '<span class="validated-label">✓ Clinician Validated</span>' : ''}
                    </div>
                </div>
            `;
        }

        msg.innerHTML = `
            <div class="message-avatar message-avatar-ai">🦴</div>
            <div class="message-content">
                <div class="message-bubble">${bubbleHtml}</div>
                ${metaHtml ? `<div class="message-meta" style="display:flex;flex-direction:column;gap:8px;">${metaHtml}</div>` : ''}
            </div>
        `;

        messagesEl.appendChild(msg);

        // Wire interactions
        if (messageId) {
            const metaEl = msg.querySelector('.message-meta');
            if (metaEl) {
                wireFeedbackButtons(metaEl, messageId);
                wireActionToolbar(metaEl, content, () => {});
                wireCitationCards(metaEl);
            }
        }

        // Wire section toggles
        msg.querySelectorAll('.section-header').forEach(header => {
            header.addEventListener('click', () => header.closest('.response-section').classList.toggle('open'));
        });

        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    // ── Image upload handler ────────────────────────────────
    async function handleImageUpload(query) {
        addUserMessage(`📎 [Image: ${pendingImage.name}]${query ? '\n' + query : ''}`);
        const typingEl = addTypingIndicator();
        isLoading = true;

        try {
            const formData = new FormData();
            formData.append('file', pendingImage);
            if (query) formData.append('query', query);
            if (currentSessionId) formData.append('session_id', currentSessionId);

            const result = await api.analyzeImage(formData);
            typingEl.remove();

            let analysisHtml = `<div class="image-analysis-response">`;
            analysisHtml += `<div class="analysis-header"><span class="analysis-badge">🩻 Vision Analysis</span><span class="analysis-status ${result.validation_status}">${result.validation_status === 'pending_review' ? '⏳ Pending Review' : result.validation_status}</span></div>`;
            if (result.raw_analysis) analysisHtml += `<div class="analysis-content">${renderMarkdown(result.raw_analysis)}</div>`;
            if (result.findings?.length) {
                analysisHtml += `<div class="analysis-findings"><h4>Findings</h4>`;
                result.findings.forEach(f => { analysisHtml += `<div class="finding-item"><strong>${escapeHtml(f.name)}</strong>${f.description ? ': ' + escapeHtml(f.description) : ''}</div>`; });
                analysisHtml += `</div>`;
            }
            if (result.recommendations?.length) {
                analysisHtml += `<div class="analysis-recommendations"><h4>Recommendations</h4><ul>`;
                result.recommendations.forEach(r => { analysisHtml += `<li>${escapeHtml(r)}</li>`; });
                analysisHtml += `</ul></div>`;
            }
            analysisHtml += `<div class="analysis-disclaimer">⚠️ ${escapeHtml(result.ai_disclaimer)}</div></div>`;

            const msg = document.createElement('div');
            msg.className = 'message message-ai';
            msg.innerHTML = `<div class="message-avatar message-avatar-ai">🦴</div><div class="message-content"><div class="message-bubble">${analysisHtml}</div></div>`;
            messagesEl.appendChild(msg);
        } catch (err) {
            typingEl.remove();
            addUserMessage(`⚠️ Image analysis failed: ${err.message}`);
        }

        pendingImage = null; imagePreview.style.display = 'none'; imageInput.value = '';
        chatInput.value = ''; isLoading = false; sendBtn.disabled = false;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function addTypingIndicator() {
        const el = document.createElement('div');
        el.className = 'message message-ai typing-message';
        el.innerHTML = `
            <div class="message-avatar message-avatar-ai">🦴</div>
            <div class="message-content">
                <div class="message-bubble">
                    <div class="typing-indicator"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
                </div>
            </div>
        `;
        messagesEl.appendChild(el);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        return el;
    }

    function updateTracePanel(trace, citations, confidence) {
        const traceContent = container.querySelector('#trace-content');
        if (!traceContent) return;

        let html = '<div class="trace-steps">';
        trace.forEach((t, i) => {
            html += `
                <div class="trace-step" style="animation-delay: ${i * 0.1}s;">
                    <div class="trace-step-number">Step ${i + 1}</div>
                    <div class="trace-step-action">${t.action || t}</div>
                    ${t.detail ? `<div class="trace-step-detail">${t.detail}</div>` : ''}
                </div>
            `;
        });
        html += '</div>';

        if (confidence > 0) {
            const level = confidence > 0.85 ? 'high' : confidence > 0.6 ? 'medium' : 'low';
            html += `<div class="trace-confidence"><span class="confidence-badge confidence-${level}">🎯 ${(confidence * 100).toFixed(0)}%</span></div>`;
        }

        if (citations?.length) {
            html += '<div class="sources-list"><h4>📚 Sources</h4>';
            citations.forEach(c => {
                const label = typeof c === 'string' ? c : (c.page_range || c.section || 'Reference');
                html += `<div class="source-item"><span class="source-badge">${label}</span></div>`;
            });
            html += '</div>';
        }

        traceContent.innerHTML = html;
    }
}

// ── Helpers ───────────────────────────────────────────────

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    try { return marked.parse(text || '', { breaks: true }); }
    catch { return (text || '').replace(/\n/g, '<br>'); }
}

function formatDate(iso) {
    if (!iso) return '';
    try {
        const dateStr = iso.endsWith('Z') || iso.includes('+') ? iso : iso.replace(' ', 'T') + 'Z';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;
        if (isNaN(d.getTime())) return iso;
        if (diff < 60000)    return 'just now';
        if (diff < 3600000)  return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        if (diff < 604800000)return `${Math.floor(diff / 86400000)}d ago`;
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch { return iso; }
}
