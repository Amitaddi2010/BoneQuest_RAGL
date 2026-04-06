// ============================================================
// BoneQuest v2 — AI Chat Page (Complete Overhaul)
// ============================================================

import { api } from '../utils/api.js';
import { auth } from '../utils/auth.js';
import { marked } from 'https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js';

const SUGGESTIONS = [
    "Management of comminuted tibial shaft fracture in a diabetic patient?",
    "ACL reconstruction rehabilitation protocol — week by week timeline?",
    "Treatment for displaced femoral neck fracture in 75yo with CHF?",
    "Compare anterolateral vs medial approach for total hip arthroplasty?"
];

let currentSessionId = null;
let currentRole = auth.role || 'resident';
let isLoading = false;
let sessions = [];

export function renderChat(container) {
    container.innerHTML = `
        <div class="chat-layout">
            <!-- Session History Sidebar -->
            <aside class="chat-sidebar" id="chat-sidebar">
                <div class="sidebar-top">
                    <button class="btn btn-primary btn-full new-chat-btn" id="new-chat-btn">
                        <span>＋</span> New Chat
                    </button>
                </div>
                <div class="session-list" id="session-list">
                    <div class="session-loading">Loading sessions...</div>
                </div>
                <div class="sidebar-bottom">
                    <div class="sidebar-user-card">
                        <div class="sidebar-user-avatar">${(auth.user?.full_name || 'U')[0].toUpperCase()}</div>
                        <div class="sidebar-user-info">
                            <span class="sidebar-user-name">${auth.user?.full_name || 'User'}</span>
                            <span class="sidebar-user-role">${auth.role}</span>
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
                        <span class="chat-header-model">Groq LLaMA · PageIndex RAG</span>
                    </div>
                    <div class="chat-header-actions" style="margin-left: auto;">
                        <button class="btn btn-ghost" id="export-ehr-btn" title="Export as Clinical Report" style="display:none; font-size: 13px; font-weight: 600; color: var(--accent-light);">📄 Export EHR</button>
                    </div>
                </div>

                <div class="chat-messages" id="chat-messages">
                    <div class="chat-welcome" id="chat-welcome">
                        <div class="welcome-icon-large">🦴</div>
                        <h2>BoneQuest AI</h2>
                        <p>Clinical-grade orthopaedic decision support with guideline validation.</p>
                        <div class="welcome-suggestions" id="suggestions">
                            ${SUGGESTIONS.map(s => `<button class="suggestion-chip" data-suggestion="${s}">${s}</button>`).join('')}
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

            <!-- Support Panel (Trace & Context) -->
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
                                <!-- Abstract Skeleton SVG -->
                                <svg viewBox="0 0 100 200" class="anatomy-svg">
                                    <!-- Head -->
                                    <circle cx="50" cy="20" r="12" class="bone-zone" data-prompt="What are the protocols for traumatic brain injury and skull fractures?"/>
                                    
                                    <!-- Spine -->
                                    <rect x="44" y="35" width="12" height="40" rx="3" class="bone-zone" data-prompt="Show AAOS guidelines for cervical and lumbar spine trauma."/>
                                    
                                    <!-- Pelvis -->
                                    <polygon points="35,75 65,75 55,95 45,95" class="bone-zone" data-prompt="Latest recommendations for pelvic ring fractures and acetabulum?"/>
                                    
                                    <!-- Arms -->
                                    <line x1="42" y1="40" x2="15" y2="65" stroke-width="6" class="bone-zone" data-prompt="Protocols for proximal humerus fractures in elderly?" stroke-linecap="round"/>
                                    <line x1="58" y1="40" x2="85" y2="65" stroke-width="6" class="bone-zone" data-prompt="Protocols for proximal humerus fractures in elderly?" stroke-linecap="round"/>
                                    
                                    <!-- Hands -->
                                    <circle cx="12" cy="72" r="4" class="bone-zone" data-prompt="Distal radius fracture management algorithm?"/>
                                    <circle cx="88" cy="72" r="4" class="bone-zone" data-prompt="Distal radius fracture management algorithm?"/>
                                    
                                    <!-- Legs (Femur) -->
                                    <line x1="45" y1="90" x2="32" y2="135" stroke-width="8" class="bone-zone" data-prompt="Management of displaced femoral neck fracture?" stroke-linecap="round"/>
                                    <line x1="55" y1="90" x2="68" y2="135" stroke-width="8" class="bone-zone" data-prompt="Management of displaced femoral neck fracture?" stroke-linecap="round"/>
                                    
                                    <!-- Knees -->
                                    <circle cx="32" cy="135" r="5" class="bone-zone" data-prompt="Post-op protocol for total knee arthroplasty?"/>
                                    <circle cx="68" cy="135" r="5" class="bone-zone" data-prompt="Post-op protocol for total knee arthroplasty?"/>
                                    
                                    <!-- Tibia/Fibula -->
                                    <line x1="32" y1="135" x2="32" y2="185" stroke-width="6" class="bone-zone" data-prompt="Comminuted tibial shaft fracture treatment options?" stroke-linecap="round"/>
                                    <line x1="68" y1="135" x2="68" y2="185" stroke-width="6" class="bone-zone" data-prompt="Comminuted tibial shaft fracture treatment options?" stroke-linecap="round"/>
                                    
                                    <!-- Feet -->
                                    <ellipse cx="32" cy="190" rx="8" ry="4" class="bone-zone" data-prompt="Operative indications for calcaneus fractures?"/>
                                    <ellipse cx="68" cy="190" rx="8" ry="4" class="bone-zone" data-prompt="Operative indications for calcaneus fractures?"/>
                                </svg>
                            </div>
                            <p style="font-size: 11px; color: var(--text-dim); text-align: center; margin-top: var(--space-4);">Click any region to auto-generate a clinical query.</p>
                        </div>
                    </div>
                </div>
            </aside>
        </div>
    `;

    // ── Element References ─────────────────────────────────
    const chatInput = container.querySelector('#chat-input');
    const sendBtn = container.querySelector('#chat-send');
    const messagesEl = container.querySelector('#chat-messages');
    const sessionList = container.querySelector('#session-list');
    const newChatBtn = container.querySelector('#new-chat-btn');
    const imageInput = container.querySelector('#image-file-input');
    const imageAttachBtn = container.querySelector('#image-attach-btn');
    const imagePreview = container.querySelector('#image-preview');
    const sidebarToggle = container.querySelector('#sidebar-toggle');
    const sidebar = container.querySelector('#chat-sidebar');
    const micBtn = container.querySelector('#chat-mic-btn');
    const exportEhrBtn = container.querySelector('#export-ehr-btn');

    let pendingImage = null;
    let isRecording = false;
    let recognition = null;

    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        
        recognition.onstart = () => {
            isRecording = true;
            micBtn.classList.add('recording');
            chatInput.placeholder = "Listening...";
        };
        
        recognition.onresult = (e) => {
            let transcript = '';
            for (let i = 0; i < e.results.length; i++) {
                transcript += e.results[i][0].transcript;
            }
            chatInput.value = transcript;
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
        };
        
        recognition.onerror = (e) => {
            console.error('Speech recognition error', e);
            stopRecording();
        };
        
        recognition.onend = () => {
            stopRecording();
            // Automatically send message when they stop talking if there is text
            if (chatInput.value.trim()) {
                sendMessage();
            }
        };
    }

    function stopRecording() {
        if (isRecording && recognition) {
            recognition.stop();
        }
        isRecording = false;
        micBtn.classList.remove('recording');
        chatInput.placeholder = "Dictate findings, ask about protocols, upload X-rays...";
    }

    micBtn.addEventListener('click', () => {
        if (!recognition) {
            alert("Speech recognition isn't supported in this browser. Please try Chrome, Edge, or Safari.");
            return;
        }
        if (isRecording) {
            stopRecording();
        } else {
            chatInput.value = '';
            recognition.start();
        }
    });

    // EHR Export
    exportEhrBtn.addEventListener('click', () => {
        if (!currentSessionId) return;
        const msgElements = messagesEl.querySelectorAll('.message');
        if (!msgElements.length) return;
        
        let reportText = "========================================================\n";
        reportText += "               BONEQUEST CLINICAL CONSULTATION           \n";
        reportText += "========================================================\n\n";
        reportText += "Date: " + new Date().toLocaleString() + "\n";
        reportText += "Clinician: " + (auth.user?.full_name || 'Dr. ' + auth.user?.email) + "\n";
        reportText += "Session ID: " + currentSessionId + "\n\n";
        reportText += "--------------------------------------------------------\n\n";
        
        msgElements.forEach(msg => {
            const isUser = msg.classList.contains('message-user');
            const roleStr = isUser ? "CLINICIAN QUERY" : "AI DECISION SUPPORT";
            const textContent = msg.querySelector('.message-bubble')?.innerText || '';
            
            reportText += `[${roleStr}]\n`;
            reportText += textContent + "\n\n";
            
            if (!isUser) {
                const confMeta = msg.querySelector('.confidence-badge');
                if (confMeta) {
                    reportText += `   >> ${confMeta.innerText}\n`;
                }
                const citations = msg.querySelectorAll('.citation-badge');
                if (citations.length) {
                    reportText += `   >> References: `;
                    citations.forEach(c => reportText += c.innerText + " | ");
                    reportText += "\n";
                }
                reportText += "\n--------------------------------------------------------\n\n";
            }
        });
        
        reportText += "\nDISCLAIMER: This is an AI-assisted consultation. Always verify protocols.\n";
        
        const blob = new Blob([reportText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BoneQuest_Consultation_${new Date().getTime()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    });

    // ── Auto-resize textarea ──────────────────────────────
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
    });

    // ── Sidebar toggle (mobile) ───────────────────────────
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
    });

    // ── Role selector ─────────────────────────────────────
    container.querySelectorAll('.role-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            container.querySelectorAll('.role-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentRole = chip.dataset.role;
        });
    });

    // ── Image attachment ──────────────────────────────────
    imageAttachBtn.addEventListener('click', () => imageInput.click());
    imageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        pendingImage = file;
        showImagePreview(file);
    });

    function showImagePreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const card = container.querySelector('#image-preview-card');
            card.innerHTML = `
                <img src="${e.target.result}" alt="Preview" class="preview-thumb">
                <div class="preview-info">
                    <span class="preview-name">${file.name}</span>
                    <span class="preview-size">${(file.size / 1024).toFixed(0)} KB</span>
                </div>
                <button class="preview-remove" id="remove-image">✕</button>
            `;
            imagePreview.style.display = 'block';
            card.querySelector('#remove-image').addEventListener('click', () => {
                pendingImage = null;
                imagePreview.style.display = 'none';
                imageInput.value = '';
            });
        };
        reader.readAsDataURL(file);
    }

    // ── Panel Tabs ────────────────────────────────────────
    container.querySelectorAll('.panel-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            container.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            container.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
            container.querySelector(`#${tab.dataset.target}`).style.display = 'block';
        });
    });

    // ── Anatomy Skeleton Selector ─────────────────────────
    container.querySelectorAll('.bone-zone').forEach(bone => {
        bone.addEventListener('click', () => {
            chatInput.value = bone.dataset.prompt;
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
            // Trigger focus effects
            chatInput.focus();
        });
    });

    // ── Suggestion chips ──────────────────────────────────
    container.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            chatInput.value = chip.dataset.suggestion;
            sendMessage();
        });
    });

    // ── Send message ──────────────────────────────────────
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    sendBtn.addEventListener('click', sendMessage);

    // ── New Chat ──────────────────────────────────────────
    newChatBtn.addEventListener('click', () => startNewChat());

    // ── Load sessions ─────────────────────────────────────
    loadSessions();

    // ── Functions ─────────────────────────────────────────

    async function loadSessions() {
        try {
            const result = await api.listSessions();
            sessions = result.sessions || [];
            renderSessionList();
        } catch (err) {
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

        // Click to load session
        sessionList.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('.session-delete-btn')) return;
                loadSession(item.dataset.sessionId);
                sidebar.classList.remove('open');
            });
        });

        // Delete button
        sessionList.querySelectorAll('.session-delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.dataset.deleteId;
                if (confirm('Delete this conversation?')) {
                    await api.deleteSession(id);
                    if (currentSessionId === id) {
                        currentSessionId = null;
                        showWelcome();
                    }
                    await loadSessions();
                }
            });
        });
    }

    async function loadSession(sessionId) {
        currentSessionId = sessionId;
        renderSessionList();

        const session = sessions.find(s => s.id === sessionId);
        if (session) {
            container.querySelector('#chat-title').textContent = session.title || 'Chat';
        }

        // Load messages
        try {
            const result = await api.getSessionMessages(sessionId);
            const welcome = container.querySelector('#chat-welcome');
            if (welcome) welcome.remove();

            // Clear and render messages
            messagesEl.innerHTML = '';
            for (const msg of (result.messages || [])) {
                if (msg.role === 'user') {
                    addMessageBubble('user', msg.content);
                } else {
                    addMessageBubble('ai', msg.content, msg.confidence_score, msg.citations, msg.reasoning_trace, msg.id, msg.user_feedback);
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
                    ${SUGGESTIONS.map(s => `<button class="suggestion-chip" data-suggestion="${s}">${s}</button>`).join('')}
                </div>
            </div>
        `;
        messagesEl.querySelectorAll('.suggestion-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                chatInput.value = chip.dataset.suggestion;
                sendMessage();
            });
        });
    }

    async function startNewChat() {
        currentSessionId = null;
        showWelcome();
        renderSessionList();
        chatInput.focus();
    }

    async function sendMessage() {
        const text = chatInput.value.trim();
        if ((!text && !pendingImage) || isLoading) return;

        // Remove welcome screen
        const welcome = container.querySelector('#chat-welcome');
        if (welcome) welcome.remove();

        // Create session if needed
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

        // Handle image upload
        if (pendingImage) {
            await handleImageUpload(text);
            return;
        }

        // Add user message
        addMessageBubble('user', text);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        isLoading = true;
        sendBtn.disabled = true;

        // Show typing indicator
        const typingEl = addTypingIndicator();

        // Reset trace panel
        const traceContent = container.querySelector('#trace-content');
        traceContent.innerHTML = '<div class="trace-steps"></div>';

        try {
            typingEl.remove();

            const msgEl = document.createElement('div');
            msgEl.className = 'message message-ai';
            msgEl.innerHTML = `
                <div class="message-avatar message-avatar-ai">🦴</div>
                <div class="message-content">
                    <div class="message-bubble" id="streaming-bubble"></div>
                    <div class="message-meta" id="streaming-meta" style="display:none;"></div>
                </div>
            `;
            messagesEl.appendChild(msgEl);

            const bubble = msgEl.querySelector('#streaming-bubble');
            const meta = msgEl.querySelector('#streaming-meta');
            let fullText = '';
            let liveTrace = [];
            let liveCitations = [];
            let confidence = 0;
            let finalMessageId = null;

            for await (const event of api.streamChatMessage({
                session_id: currentSessionId,
                message: text,
                role: currentRole,
                document_id: 'doc-1'
            })) {
                if (event.type === 'token') {
                    fullText += event.data;
                    bubble.innerHTML = renderMarkdown(fullText);
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                } else if (event.type === 'trace') {
                    const traceData = JSON.parse(event.data);
                    liveTrace.push(traceData);
                    updateTracePanel(liveTrace, liveCitations, confidence);
                } else if (event.type === 'citation') {
                    liveCitations = JSON.parse(event.data);
                    updateTracePanel(liveTrace, liveCitations, confidence);
                } else if (event.type === 'confidence') {
                    confidence = parseFloat(event.data);
                    showResponseMeta(meta, confidence, liveCitations, finalMessageId);
                    updateTracePanel(liveTrace, liveCitations, confidence);
                } else if (event.type === 'message_id') {
                    finalMessageId = event.data;
                    showResponseMeta(meta, confidence, liveCitations, finalMessageId);
                } else if (event.type === 'error') {
                    throw new Error(event.data);
                }
            }

            // Show meta with final data
            showResponseMeta(meta, confidence, liveCitations, finalMessageId);

        } catch (err) {
            console.error('Stream error:', err);
            typingEl?.remove();
            addMessageBubble('ai', '⚠️ Failed to generate response. Please try again.');
        }

        isLoading = false;
        sendBtn.disabled = false;
        messagesEl.scrollTop = messagesEl.scrollHeight;
        await loadSessions();
    }

    async function handleImageUpload(query) {
        addMessageBubble('user', `📎 [Image: ${pendingImage.name}]${query ? '\n' + query : ''}`);

        const typingEl = addTypingIndicator();
        isLoading = true;

        try {
            const formData = new FormData();
            formData.append('file', pendingImage);
            if (query) formData.append('query', query);
            if (currentSessionId) formData.append('session_id', currentSessionId);

            const result = await api.analyzeImage(formData);
            typingEl.remove();

            // Build analysis response
            let analysisHtml = `<div class="image-analysis-response">`;
            analysisHtml += `<div class="analysis-header"><span class="analysis-badge">🩻 Vision Analysis</span><span class="analysis-status ${result.validation_status}">${result.validation_status === 'pending_review' ? '⏳ Pending Review' : result.validation_status}</span></div>`;

            if (result.raw_analysis) {
                analysisHtml += `<div class="analysis-content">${renderMarkdown(result.raw_analysis)}</div>`;
            }

            if (result.findings?.length) {
                analysisHtml += `<div class="analysis-findings"><h4>Findings</h4>`;
                result.findings.forEach(f => {
                    analysisHtml += `<div class="finding-item"><strong>${escapeHtml(f.name)}</strong>${f.description ? ': ' + escapeHtml(f.description) : ''}</div>`;
                });
                analysisHtml += `</div>`;
            }

            if (result.recommendations?.length) {
                analysisHtml += `<div class="analysis-recommendations"><h4>Recommendations</h4><ul>`;
                result.recommendations.forEach(r => { analysisHtml += `<li>${escapeHtml(r)}</li>`; });
                analysisHtml += `</ul></div>`;
            }

            analysisHtml += `<div class="analysis-disclaimer">⚠️ ${escapeHtml(result.ai_disclaimer)}</div>`;
            analysisHtml += `</div>`;

            addMessageBubble('ai-raw', analysisHtml);

        } catch (err) {
            typingEl.remove();
            addMessageBubble('ai', `⚠️ Image analysis failed: ${err.message}`);
        }

        // Reset image state
        pendingImage = null;
        imagePreview.style.display = 'none';
        imageInput.value = '';
        chatInput.value = '';
        isLoading = false;
        sendBtn.disabled = false;
    }

    function addMessageBubble(type, content, confidence, citations, trace, messageId = null, feedbackScore = 0) {
        const msg = document.createElement('div');
        msg.className = `message message-${type === 'user' ? 'user' : 'ai'}`;

        if (type === 'user') {
            msg.innerHTML = `
                <div class="message-avatar message-avatar-user">${(auth.user?.full_name || 'U')[0].toUpperCase()}</div>
                <div class="message-content">
                    <div class="message-bubble">${escapeHtml(content)}</div>
                </div>
            `;
        } else if (type === 'ai-raw') {
            msg.innerHTML = `
                <div class="message-avatar message-avatar-ai">🦴</div>
                <div class="message-content">
                    <div class="message-bubble">${content}</div>
                </div>
            `;
        } else {
            let metaHtml = '';
            if (confidence) {
                metaHtml += `<span class="confidence-badge confidence-${confidence > 0.85 ? 'high' : confidence > 0.6 ? 'medium' : 'low'}">🎯 Confidence: ${(confidence * 100).toFixed(0)}%</span>`;
            }
            if (citations?.length) {
                citations.forEach(c => {
                    metaHtml += `<span class="citation-badge" style="margin-left: 5px;">📄 ${typeof c === 'string' ? c : c.page_range || 'Reference'}</span>`;
                });
            }
            if (messageId) {
                const upActive = feedbackScore === 1 ? 'active' : '';
                const downActive = feedbackScore === -1 ? 'active' : '';
                metaHtml += `
                    <div class="feedback-actions" data-id="${messageId}">
                        <button class="btn-feedback ${upActive}" data-score="1" title="Clinician Validated">👍</button>
                        <button class="btn-feedback ${downActive}" data-score="-1" title="Incorrect">👎</button>
                        ${feedbackScore === 1 ? '<span class="validated-label">✓ Clinician Validated</span>' : ''}
                    </div>
                `;
            }

            msg.innerHTML = `
                <div class="message-avatar message-avatar-ai">🦴</div>
                <div class="message-content">
                    <div class="message-bubble">${renderMarkdown(content)}</div>
                    ${metaHtml ? `<div class="message-meta">${metaHtml}</div>` : ''}
                </div>
            `;

            if (messageId) {
                setTimeout(() => {
                    msg.querySelectorAll('.btn-feedback').forEach(btn => {
                        btn.addEventListener('click', async () => {
                            const score = parseInt(btn.dataset.score);
                            try {
                                await api.sendFeedback(messageId, score);
                                msg.querySelectorAll('.btn-feedback').forEach(b => b.style.opacity = '0.5');
                                btn.style.opacity = '1';
                                const parent = btn.parentElement;
                                const existingSpan = parent.querySelector('span');
                                if (score === 1 && !existingSpan) {
                                    parent.insertAdjacentHTML('beforeend', '<span style="font-size:11px; color:var(--success); margin-left:8px; font-weight: bold;">✓ Clinician Validated</span>');
                                } else if (score === -1 && existingSpan) {
                                    existingSpan.remove();
                                }
                            } catch (err) { }
                        });
                    });
                }, 0);
            }
        }

        messagesEl.appendChild(msg);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function showResponseMeta(metaEl, confidence, citations, messageId = null) {
        if (!metaEl) return;
        let html = '';
        if (confidence) {
            const level = confidence > 0.85 ? 'high' : confidence > 0.6 ? 'medium' : 'low';
            html += `<span class="confidence-badge confidence-${level}">🎯 Confidence: ${(confidence * 100).toFixed(0)}%</span>`;
        }
        if (citations?.length) {
            citations.forEach(c => {
                html += `<span class="citation-badge" style="margin-left:5px;">📄 ${typeof c === 'string' ? c : c.page_range || 'Reference'}</span>`;
            });
        }
        if (messageId) {
            html += `
                <div class="feedback-actions" data-id="${messageId}">
                    <button class="btn-feedback" data-score="1" title="Clinician Validated">👍</button>
                    <button class="btn-feedback" data-score="-1" title="Incorrect">👎</button>
                </div>
            `;
        }
        if (html) {
            metaEl.innerHTML = html;
            metaEl.style.display = 'flex';

            if (messageId) {
                metaEl.querySelectorAll('.btn-feedback').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        const score = parseInt(btn.dataset.score);
                        try {
                            await api.sendFeedback(messageId, score);
                            metaEl.querySelectorAll('.btn-feedback').forEach(b => b.classList.remove('active'));
                            btn.classList.add('active');
                            const parent = btn.parentElement;
                            const existingSpan = parent.querySelector('span');
                            if (score === 1 && !existingSpan) {
                                parent.insertAdjacentHTML('beforeend', '<span class="validated-label">✓ Clinician Validated</span>');
                            } else if (score === -1 && existingSpan) {
                                existingSpan.remove();
                            }
                        } catch (err) { }
                    });
                });
            }
        }
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
                <div class="trace-step" style="animation-delay: ${i * 0.15}s;">
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
                html += `<div class="source-item"><span class="source-badge">${typeof c === 'string' ? c : c.page_range || 'Reference'}</span></div>`;
            });
            html += '</div>';
        }

        traceContent.innerHTML = html;
    }
}

// ── Helpers ───────────────────────────────────────────────

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderMarkdown(text) {
    try {
        return marked.parse(text || '', { breaks: true });
    } catch {
        return text.replace(/\n/g, '<br>');
    }
}

function formatDate(iso) {
    if (!iso) return '';
    try {
        // Ensure UTC interpretation by adding Z if missing
        const dateStr = iso.endsWith('Z') || iso.includes('+') ? iso : iso.replace(' ', 'T') + 'Z';
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now - d;

        if (isNaN(d.getTime())) return iso;
        if (diff < 60000) return 'just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch (e) {
        return iso;
    }
}
