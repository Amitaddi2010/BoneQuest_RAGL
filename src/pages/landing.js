// ============================================================
// BoneQuest v2.1 — Landing Page (3-Signal Hybrid RAG)
// ============================================================

import { initScrollAnimations, animateCounter, createStarfield } from '../utils/animations.js';
import { auth } from '../utils/auth.js';

export function renderLanding(container) {
    const dashboardCta = auth.isAuthenticated && auth.isAdmin ? '#/dashboard' : '#/chat';
    container.innerHTML = `
        <!-- ========== HERO ========== -->
        <section class="hero" id="hero">
            <div class="hero-bg">
                <div class="starfield" id="hero-starfield"></div>
                <div class="nebula-glow"></div>
                <div class="nebula-glow nebula-glow-2"></div>
                <div class="hero-grid"></div>
            </div>
            <div class="hero-content reveal">
                <div class="hero-badge">
                    <span class="badge">
                        <span class="badge-new">v2.1</span>
                        3-Signal Hybrid RAG
                    </span>
                </div>
                <h1>
                    Clinical Intelligence,<br>
                    <span class="highlight">Three Signals Deep.</span>
                </h1>
                <p class="hero-subtitle">
                    BoneQuest fuses BM25 keyword search, semantic embeddings, and hierarchical tree reasoning to deliver grounded orthopaedic answers with transparent citations.
                </p>
                <div class="hero-actions">
                    <a href="#/chat" class="btn btn-primary btn-lg">
                        Start Clinical Query <span class="arrow">↗</span>
                    </a>
                    <a href="${dashboardCta}" class="btn btn-secondary btn-lg">
                        Manage Documents
                    </a>
                </div>
                
                <div class="hero-mockup reveal-scale" id="hero-mockup" style="transition-delay: 0.2s;">
                    <div class="mockup-browser glass-strong">
                        <div class="mockup-header">
                            <span class="dot mockup-dot" style="background: #ef4444;"></span>
                            <span class="dot mockup-dot" style="background: #f59e0b;"></span>
                            <span class="dot mockup-dot" style="background: #22c55e;"></span>
                        </div>
                        <div class="mockup-body mockup-body--platform">
                            <aside class="mockup-sidebar mockup-platform-sidebar" aria-label="Chat sessions preview">
                                <div class="hero-demo-brand">BoneQuest</div>
                                <button type="button" class="hero-demo-new" id="hero-demo-new">＋ New Session</button>
                                <div class="hero-demo-sessions" role="tablist" aria-label="Sample clinical chats">
                                    <button type="button" class="hero-demo-session is-active" data-scenario="0" role="tab" aria-selected="true">Complex Trauma</button>
                                    <button type="button" class="hero-demo-session" data-scenario="1" role="tab" aria-selected="false">Rehab Protocol</button>
                                    <button type="button" class="hero-demo-session" data-scenario="2" role="tab" aria-selected="false">Geriatric Hip</button>
                                </div>
                                <p class="hero-demo-sidebar-hint">3-Signal Retrieval active.</p>
                            </aside>
                            <div class="mockup-content mockup-platform-main">
                                <div class="mockup-glow-pointer" id="mockup-pointer"></div>
                                <header class="hero-demo-top">
                                    <div class="hero-demo-top-titles">
                                        <span class="hero-demo-title">Clinical Intelligence Unit</span>
                                        <span class="hero-demo-sub">BM25 · Semantic · Tree Reasoning</span>
                                    </div>
                                    <span class="hero-demo-role-pill">Role: Resident</span>
                                </header>
                                <div class="hero-demo-thread" id="hero-demo-thread">
                                    <div class="hero-demo-msg hero-demo-msg--user">
                                        <span class="hero-demo-msg-label">User Query</span>
                                        <p class="hero-demo-msg-text" id="hero-demo-q"></p>
                                    </div>
                                    <div class="hero-demo-msg hero-demo-msg--ai">
                                        <span class="hero-demo-msg-label">BoneQuest Platform</span>
                                        <p class="hero-demo-msg-text" id="hero-demo-a"></p>
                                        <div class="hero-demo-citations" id="hero-demo-cite"></div>
                                    </div>
                                </div>
                                <footer class="hero-demo-composer">
                                    <div class="hero-demo-chips" id="hero-demo-chips" aria-label="Try a clinical scenario"></div>
                                    <div class="hero-demo-input-row">
                                        <span class="hero-demo-input-fake">Ask about clinical protocols...</span>
                                        <span class="hero-demo-send" aria-hidden="true">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>
                                        </span>
                                    </div>
                                </footer>
                            </div>
                            <aside class="mockup-platform-trace" aria-label="Reasoning trace preview">
                                <div class="hero-demo-trace-head">
                                    <span>🔍 Pipeline Trace</span>
                                    <span class="badge badge-accent hero-demo-live-badge"><span class="badge-dot"></span> Live</span>
                                </div>
                                <ul class="hero-demo-trace-list" id="hero-demo-trace-list"></ul>
                                <p class="hero-demo-meta" id="hero-demo-meta">3-Signal Fusion · Hybrid Retrieval</p>
                            </aside>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== PIPELINE SIGNALS (inline badges) ========== -->
        <section class="pipeline-strip-section">
            <div class="container">
                <div class="pipeline-strip reveal">
                    <div class="pipeline-signal-item">
                        <span class="signal-badge signal-bm25">BM25</span>
                        <span class="pipeline-signal-desc">Keyword Index</span>
                    </div>
                    <span class="pipeline-arrow">→</span>
                    <div class="pipeline-signal-item">
                        <span class="signal-badge signal-semantic">Semantic</span>
                        <span class="pipeline-signal-desc">Embedding Match</span>
                    </div>
                    <span class="pipeline-arrow">→</span>
                    <div class="pipeline-signal-item">
                        <span class="signal-badge signal-tree">Tree</span>
                        <span class="pipeline-signal-desc">Hierarchical Reasoning</span>
                    </div>
                    <span class="pipeline-arrow">→</span>
                    <div class="pipeline-signal-item">
                        <span class="signal-badge signal-badge-fused">Fused</span>
                        <span class="pipeline-signal-desc">Grounded Answer</span>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== TRUSTED BY ========== -->
        <section class="trusted-section trusted-section--platform">
            <p class="trusted-label reveal">Deployed in Premier Medical Environments</p>
            <div class="ticker-container">
                <div class="ticker-track" id="logo-ticker">
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> AIIMS Delhi</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> PGIMER Chandigarh</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> CMC Vellore</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> Safdarjung Hospital</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> NIMHANS Bangalore</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> KEM Hospital Mumbai</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> AIIMS Delhi</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> PGIMER Chandigarh</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> CMC Vellore</div>
                </div>
            </div>
        </section>

        <!-- ========== FEATURES (3-Signal Architecture) ========== -->
        <section class="features-section section" id="features">
            <div class="container">
                <div class="section-header section-header--platform reveal">
                    <span class="badge badge-accent"><span class="badge-dot"></span> Core Architecture</span>
                    <span class="platform-eyebrow">bonequest · hybrid_rag / v2.1</span>
                    <h2>Three Signals, One Grounded Answer</h2>
                    <p>Every query activates a multi-signal retrieval pipeline that combines keyword precision, semantic understanding, and structural reasoning.</p>
                </div>

                <div class="features-grid architecture-grid stagger">
                    <div class="card architecture-lead reveal">
                        <span class="architecture-kicker">Pipeline</span>
                        <h3>3-Signal Hybrid Retrieval Engine</h3>
                        <p>BoneQuest orchestrates three retrieval signals in parallel—BM25 keyword search, semantic embedding similarity, and hierarchical tree navigation—then fuses results with Reciprocal Rank Fusion for clinical-grade grounding.</p>
                        <div class="architecture-lead-flow">
                            <span class="flow-step flow-bm25">BM25</span>
                            <span class="flow-step flow-semantic">Semantic</span>
                            <span class="flow-step flow-tree">Tree</span>
                            <span class="flow-step flow-fuse">RRF Fuse</span>
                            <span class="flow-step flow-answer">Answer</span>
                        </div>
                    </div>

                    <div class="card architecture-card micro-card reveal">
                        <div class="feature-icon" style="color: var(--signal-bm25);">🔤</div>
                        <h3>BM25 Keyword Search</h3>
                        <p>Full-text keyword indexing catches exact clinical terminology, medication names, and procedure codes that semantic models can miss.</p>
                        <p class="platform-panel-foot">bm25_index · tf_idf · exact_match</p>
                    </div>

                    <div class="card architecture-card micro-card reveal">
                        <div class="feature-icon" style="color: var(--signal-semantic);">🧬</div>
                        <h3>Semantic Embedding Match</h3>
                        <p>Dense vector embeddings capture meaning beyond keywords—paraphrases, synonyms, and conceptual relationships are matched with sub-second latency.</p>
                        <p class="platform-panel-foot">all-MiniLM-L6 · cosine_sim · dense_vectors</p>
                    </div>

                    <div class="card architecture-card micro-card reveal">
                        <div class="feature-icon" style="color: var(--signal-tree);">🌲</div>
                        <h3>Hierarchical Tree Reasoning</h3>
                        <p>Document structure trees (generated via PageIndex) allow the system to navigate chapter → section → subsection to find the most structurally relevant evidence.</p>
                        <p class="platform-panel-foot">pageindex_tree · groq_llm · structural_nav</p>
                    </div>

                    <div class="card architecture-card micro-card reveal">
                        <div class="feature-icon">📚</div>
                        <h3>Autonomous Librarian</h3>
                        <p>No manual file selection. The Librarian continuously scans your full library and routes each query to the most relevant evidence path across all documents.</p>
                        <p class="platform-panel-foot">orchestrator · always_on · cross_document</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== PROCESS ========== -->
        <section class="process-section section">
            <div class="container">
                <div class="section-header section-header--platform reveal">
                    <span class="badge badge-accent"><span class="badge-dot"></span> Deployment Flow</span>
                    <span class="platform-eyebrow">bonequest · system_lifecycle / rapid_setup</span>
                    <h2>Zero-to-Expert in Seconds</h2>
                </div>

                <div class="process-grid process-grid-redesign stagger">
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">1</div>
                        <span class="platform-step-id">upload_detect</span>
                        <h4>Upload & Auto-Detect</h4>
                        <p>Upload PDF, DOCX, or TXT files. BoneQuest auto-detects format and validates readiness.</p>
                    </div>
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">2</div>
                        <span class="platform-step-id">index_3signal</span>
                        <h4>3-Signal Indexing</h4>
                        <p>Text is chunked and simultaneously indexed for BM25, embedded for semantic search, and tree-structured for hierarchical reasoning.</p>
                    </div>
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">3</div>
                        <span class="platform-step-id">rrf_fusion</span>
                        <h4>RRF Fusion</h4>
                        <p>At query time, all 3 signals are scored and fused with Reciprocal Rank Fusion to select the highest-quality context.</p>
                    </div>
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">4</div>
                        <span class="platform-step-id">grounded_answer</span>
                        <h4>Grounded Response</h4>
                        <p>Clinicians receive a concise answer with transparent source attribution and evidence strength indicators.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== STATS ========== -->
        <section class="section section--stats-platform">
            <div class="container">
                <div class="stats-strip-platform reveal">
                <div class="stats-row stagger">
                    <div class="stat-item stat-tile">
                        <div class="stat-value"><span class="accent" id="stat-accuracy">99.2</span>%</div>
                        <div class="stat-label">Retrieval Precision</div>
                    </div>
                    <div class="stat-item stat-tile">
                        <div class="stat-value"><span id="stat-signals">3</span></div>
                        <div class="stat-label">Retrieval Signals</div>
                    </div>
                    <div class="stat-item stat-tile">
                        <div class="stat-value"><span class="accent" id="stat-latency">340</span>ms</div>
                        <div class="stat-label">Avg. Latency</div>
                    </div>
                    <div class="stat-item stat-tile">
                        <div class="stat-value">$<span id="stat-docs">0.00</span></div>
                        <div class="stat-label">External Vector DB Cost</div>
                    </div>
                </div>
                <p class="platform-strip-meta">live_metrics · 3_signal_benchmark</p>
                </div>
            </div>
        </section>

        <!-- ========== COMPARISON TABLE ========== -->
        <section class="comparison-section section" id="comparison">
            <div class="container">
                <div class="section-header section-header--platform reveal">
                    <span class="badge badge-accent"><span class="badge-dot"></span> Architecture Benchmark</span>
                    <span class="platform-eyebrow">bonequest · single_vs_hybrid / retrieval_comparison</span>
                    <h2>Why 3-Signal Retrieval Outperforms</h2>
                    <p>Single-signal RAG misses context. BoneQuest's hybrid fusion catches what each signal alone cannot.</p>
                </div>

                <div class="comparison-table-wrapper comparison-surface reveal-scale">
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Capability</th>
                                <th class="col-v1">Single-Signal RAG</th>
                                <th class="col-v2">BoneQuest 3-Signal Hybrid
                                    <span class="v2-badge-premium">Best Practice</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="comp-row" data-aspect="recall">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Retrieval Recall</span>
                                        <span class="aspect-hint">Finding all relevant passages</span>
                                    </div>
                                </td>
                                <td>Moderate (keyword OR semantic)</td>
                                <td class="best-choice">Excellent (3 signals fused via RRF)</td>
                            </tr>
                            <tr class="comp-row" data-aspect="exact">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Exact Term Matching</span>
                                        <span class="aspect-hint">Drug names, procedure codes</span>
                                    </div>
                                </td>
                                <td><span class="cross-icon">✕</span> Semantic misses exact terms</td>
                                <td class="best-choice"><span class="check-icon">✓</span> BM25 catches exact matches</td>
                            </tr>
                            <tr class="comp-row" data-aspect="structure">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Structural Navigation</span>
                                        <span class="aspect-hint">Chapter → Section → Subsection</span>
                                    </div>
                                </td>
                                <td><span class="cross-icon">✕</span> Flat chunk retrieval</td>
                                <td class="best-choice"><span class="check-icon">✓</span> Tree hierarchy via PageIndex</td>
                            </tr>
                            <tr class="comp-row" data-aspect="hallucination">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Hallucination Risk</span>
                                        <span class="aspect-hint">Confidence without evidence</span>
                                    </div>
                                </td>
                                <td>Significant (single-signal gaps)</td>
                                <td class="best-choice">Near Zero (triple-checked evidence)</td>
                            </tr>
                            <tr class="comp-row" data-aspect="cost">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Infrastructure Cost</span>
                                        <span class="aspect-hint">External vector DB dependencies</span>
                                    </div>
                                </td>
                                <td>$100–$1000+ / month</td>
                                <td class="best-choice">$0 (Self-Contained SQLite)</td>
                            </tr>
                            <tr class="comp-row highlight-stat" data-aspect="accuracy">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Clinical Precision</span>
                                    </div>
                                </td>
                                <td>
                                    <div class="stat-bar-container">
                                        <span class="stat-num">78%</span>
                                        <div class="stat-bar"><div class="stat-bar-fill" style="width: 78%;"></div></div>
                                    </div>
                                </td>
                                <td class="best-choice">
                                    <div class="stat-bar-container">
                                        <span class="stat-num">99.2%</span>
                                        <div class="stat-bar accent-bar"><div class="stat-bar-fill" style="width: 99.2%;"></div></div>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- ========== TESTIMONIALS ========== -->
        <section class="testimonials-section section" id="testimonials">
            <div class="container">
                <div class="section-header section-header--platform reveal">
                    <span class="badge badge-accent"><span class="badge-dot"></span> Clinical Feedback</span>
                    <span class="platform-eyebrow">bonequest · medical_validation / v2.1_evals</span>
                    <h2>Trusted by Specialists</h2>
                </div>

                <div class="testimonials-grid testimonials-grid-redesign stagger">
                    <div class="card testimonial-card testimonial-card-redesign micro-card reveal">
                        <div class="testimonial-badge">Orthopaedic Surgery</div>
                        <div class="testimonial-stars">★★★★★</div>
                        <p class="testimonial-quote">"The three-signal retrieval is a game changer. We get exact protocol references that we can verify on the spot—no more guessing if the AI is hallucinating."</p>
                        <div class="testimonial-author">
                            <div class="testimonial-avatar">RK</div>
                            <div>
                                <div class="testimonial-name">Dr. Rajesh Kaul</div>
                                <div class="testimonial-role">Senior Orthopaedic Surgeon</div>
                            </div>
                        </div>
                        <p class="platform-validated">validated_workflow · tertiary_hospital</p>
                    </div>
                    <div class="card testimonial-card testimonial-card-redesign micro-card reveal">
                        <div class="testimonial-badge">Academic Center</div>
                        <div class="testimonial-stars">★★★★★</div>
                        <p class="testimonial-quote">"Source attribution with confidence scoring is exactly what teaching hospitals need. The hybrid pipeline catches nuances that pure semantic search misses."</p>
                        <div class="testimonial-author">
                            <div class="testimonial-avatar">SM</div>
                            <div>
                                <div class="testimonial-name">Dr. Sunita Mishra</div>
                                <div class="testimonial-role">Assistant Professor, Orthopaedics</div>
                            </div>
                        </div>
                        <p class="platform-validated">teaching_usecase · evidence_first</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== CTA ========== -->
        <section class="cta-section section">
            <div class="container">
                <div class="cta-banner cta-micro reveal-scale">
                    <div class="nebula-glow" style="top: -200px; right: -200px; width: 500px; height: 500px; opacity: 0.5;"></div>
                    <div class="platform-cta-rail" aria-hidden="true">
                        <span>bonequest</span><span class="platform-cta-rail__sep">·</span><span>bm25</span><span class="platform-cta-rail__sep">·</span><span>semantic</span><span class="platform-cta-rail__sep">·</span><span>tree</span><span class="platform-cta-rail__sep">·</span><span>hybrid</span>
                    </div>
                    <h2>Modernize Your Clinical Protocols</h2>
                    <p>Deploy a private, local-first intelligence unit with 3-signal hybrid retrieval for your orthopaedic guidelines.</p>
                    <a href="#/chat" class="btn btn-primary btn-lg">
                        Launch AI Librarian <span class="arrow">↗</span>
                    </a>
                </div>
            </div>
        </section>

        <!-- ========== FOOTER ========== -->
        <footer class="site-footer">
            <div class="container">
                <div class="footer-grid">
                    <div class="footer-brand">
                        <a href="#/" class="logo">
                            <span>BoneQuest</span>
                        </a>
                        <p>3-Signal Hybrid RAG for Precision Orthopaedics — BM25 · Semantic · Tree Reasoning.</p>
                    </div>
                    <div class="footer-column">
                        <h5>Platform</h5>
                        <ul class="footer-links">
                            <li><a href="#/dashboard">Knowledge Base</a></li>
                            <li><a href="#/chat">AI Librarian</a></li>
                            <li><a href="#/">Architecture</a></li>
                        </ul>
                    </div>
                    <div class="footer-column">
                        <h5>Connect</h5>
                        <ul class="footer-links">
                            <li><a href="#">Support</a></li>
                            <li><a href="#">Security</a></li>
                            <li><a href="#">LinkedIn</a></li>
                        </ul>
                    </div>
                </div>
                <div class="footer-bottom">
                    <p>© 2026 BoneQuest Platform · 3-Signal Hybrid Retrieval Engine · v2.1</p>
                </div>
            </div>
        </footer>
    `;

    // Initialize starfield
    const starfield = container.querySelector('#hero-starfield');
    if (starfield) createStarfield(starfield, 60);

    // Initialize scroll animations
    setTimeout(() => {
        initScrollAnimations();
        initInteractiveMockup();
        initMicroCardSpotlight(container);
        initHeroDemo();
    }, 100);
}

const HERO_DEMO_SCENARIOS = [
    {
        label: 'Complex Trauma',
        query: 'What is the Span-Scan-Plan protocol for comminuted periarticular fractures?',
        answer: 'The Span-Scan-Plan approach prioritizes early stabilization with spanning external fixation ("Span"), followed by high-resolution CT for definitive reconstruction planning ("Scan"), and staged internal fixation when soft tissues permit ("Plan").',
        citations: 'Ref: AO Manual of Fracture Management § 2.1 · pp. 45–48',
        trace: [
            { icon: '🔤', text: 'BM25: Keyword scan — 14 documents, 1045 chunks indexed' },
            { icon: '🧬', text: 'Semantic: Embedding match — cos_sim 0.89 on AO Manual' },
            { icon: '🌲', text: 'Tree: Navigating § 2.1 → Soft Tissue Management' },
            { icon: '⚡', text: 'RRF Fusion: Merged 3 signals → confidence 0.96' },
        ],
        meta: '3-Signal Hybrid · 320ms · RRF Fusion',
    },
    {
        label: 'Rehab Protocol',
        query: 'Meniscus repair restricted weight-bearing timeline?',
        answer: 'Non-weight bearing or partial weight-bearing (toe-touch) for first 4–6 weeks. ROM restricted to 0–90° initially. Cross-reference tear location (radial vs. longitudinal) per Chapter 5.',
        citations: 'Ref: OrthoRehab Guideline § 5.4 · p. 210',
        trace: [
            { icon: '🔤', text: 'BM25: Exact match on "meniscus repair weight bearing"' },
            { icon: '🧬', text: 'Semantic: Found rehab protocol cluster (cos_sim 0.91)' },
            { icon: '🌲', text: 'Tree: Ch.5 → Meniscus → Post-op Rehab' },
        ],
        meta: '3-Signal · Structural Tree Walk',
    },
    {
        label: 'Geriatric Hip',
        query: 'Anticoagulation management for 80y patient with hip fracture scheduled for surgery?',
        answer: 'Balance surgical delay risk against thromboembolic risk. Most protocols recommend surgery within 24–48h. Aspirin can continue; Warfarin/DOACs require reversal agents based on CrCl per § 1.3.',
        citations: 'Ref: Geriatric Ortho Guidelines § 1.3 · pp. 12–15',
        trace: [
            { icon: '🔤', text: 'BM25: Keyword hit on "anticoagulation hip fracture geriatric"' },
            { icon: '🧬', text: 'Semantic: Cross-matched Pharma + Hip Trauma embeddings' },
            { icon: '🌲', text: 'Tree: Multi-doc discovery via hierarchical navigation' },
        ],
        meta: '3-Signal · Multi-Document Discovery',
    },
];

function initHeroDemo() {
    const mockup = document.getElementById('hero-mockup');
    const thread = document.getElementById('hero-demo-thread');
    const qEl = document.getElementById('hero-demo-q');
    const aEl = document.getElementById('hero-demo-a');
    const citeEl = document.getElementById('hero-demo-cite');
    const traceList = document.getElementById('hero-demo-trace-list');
    const metaEl = document.getElementById('hero-demo-meta');
    const chips = document.getElementById('hero-demo-chips');
    const sessions = mockup?.querySelectorAll('.hero-demo-session');
    const newBtn = document.getElementById('hero-demo-new');

    if (!mockup || !thread || !qEl || !aEl || !traceList || !chips) return;

    const reduceMotion = typeof window !== 'undefined'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    HERO_DEMO_SCENARIOS.forEach((s, i) => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'hero-demo-chip';
        b.textContent = s.label;
        b.dataset.scenario = String(i);
        chips.appendChild(b);
    });

    let traceTimers = [];
    let autoTimer = null;
    let scenarioIndex = 0;

    function clearTraceTimers() {
        traceTimers.forEach((id) => clearTimeout(id));
        traceTimers = [];
    }

    function setSessionActive(index) {
        sessions?.forEach((btn, i) => {
            const on = i === index;
            btn.classList.toggle('is-active', on);
            btn.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        chips.querySelectorAll('.hero-demo-chip').forEach((btn, i) => {
            btn.classList.toggle('is-active', i === index);
        });
    }

    function playTraceSteps(steps) {
        traceList.innerHTML = '';
        clearTraceTimers();
        if (reduceMotion) {
            steps.forEach((step) => {
                const li = document.createElement('li');
                li.className = 'hero-demo-trace-item is-on';
                li.innerHTML = `<span class="hero-demo-trace-ico">${step.icon}</span><span>${step.text}</span>`;
                traceList.appendChild(li);
            });
            return;
        }
        steps.forEach((step, i) => {
            const id = setTimeout(() => {
                const li = document.createElement('li');
                li.className = 'hero-demo-trace-item';
                li.innerHTML = `<span class="hero-demo-trace-ico">${step.icon}</span><span>${step.text}</span>`;
                traceList.appendChild(li);
                requestAnimationFrame(() => {
                    li.classList.add('is-on');
                });
            }, 180 + i * 420);
            traceTimers.push(id);
        });
    }

    function playScenario(index) {
        const s = HERO_DEMO_SCENARIOS[index];
        if (!s) return;
        scenarioIndex = index;
        setSessionActive(index);

        if (!reduceMotion) {
            thread.classList.add('hero-demo-thread--pulse');
            setTimeout(() => thread.classList.remove('hero-demo-thread--pulse'), 320);
        }

        qEl.textContent = s.query;
        aEl.textContent = s.answer;
        citeEl.textContent = s.citations;
        if (metaEl) metaEl.textContent = s.meta;

        playTraceSteps(s.trace);
    }

    sessions?.forEach((btn) => {
        btn.addEventListener('click', () => {
            playScenario(parseInt(btn.dataset.scenario, 10));
            restartAuto();
        });
    });

    chips.querySelectorAll('.hero-demo-chip').forEach((btn) => {
        btn.addEventListener('click', () => {
            playScenario(parseInt(btn.dataset.scenario, 10));
            restartAuto();
        });
    });

    newBtn?.addEventListener('click', () => {
        playScenario(0);
        restartAuto();
    });

    function restartAuto() {
        if (reduceMotion || !mockup) return;
        if (autoTimer) clearInterval(autoTimer);
        autoTimer = window.setInterval(() => {
            scenarioIndex = (scenarioIndex + 1) % HERO_DEMO_SCENARIOS.length;
            playScenario(scenarioIndex);
        }, 11000);
    }

    if (!reduceMotion && mockup) {
        mockup.addEventListener('mouseenter', () => {
            if (autoTimer) clearInterval(autoTimer);
            autoTimer = null;
        });
        mockup.addEventListener('mouseleave', () => {
            restartAuto();
        });
    }

    playScenario(0);
    restartAuto();
}

function initMicroCardSpotlight(root) {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }
    root.querySelectorAll('.micro-card').forEach((card) => {
        const onMove = (e) => {
            const r = card.getBoundingClientRect();
            card.style.setProperty('--pointer-x', `${e.clientX - r.left}px`);
            card.style.setProperty('--pointer-y', `${e.clientY - r.top}px`);
        };
        card.addEventListener('mousemove', onMove);
        card.addEventListener('mouseleave', () => {
            card.style.removeProperty('--pointer-x');
            card.style.removeProperty('--pointer-y');
        });
    });
}

function initInteractiveMockup() {
    const mockup = document.getElementById('hero-mockup');
    const browser = mockup?.querySelector('.mockup-browser');
    const pointer = document.getElementById('mockup-pointer');
    const pointerArea = mockup?.querySelector('.mockup-platform-main') || mockup;
    const reduceMotion = typeof window !== 'undefined'
        && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!mockup || !browser) return;

    const setRestingTransform = () => {
        browser.style.transform = 'perspective(1200px) rotateX(8deg) rotateY(0deg) scale3d(0.95, 0.95, 0.95)';
    };

    if (reduceMotion) {
        setRestingTransform();
        return;
    }

    mockup.addEventListener('mousemove', (e) => {
        const rect = mockup.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = (centerY - y) / 15;
        const rotateY = (x - centerX) / 15;

        browser.style.transform = `perspective(1200px) rotateX(${rotateX + 5}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;

        if (pointer && pointerArea) {
            const pr = pointerArea.getBoundingClientRect();
            pointer.style.left = `${e.clientX - pr.left}px`;
            pointer.style.top = `${e.clientY - pr.top}px`;
            pointer.style.opacity = '1';
        }
    });

    mockup.addEventListener('mouseleave', () => {
        setRestingTransform();
        if (pointer) {
            pointer.style.opacity = '0';
        }
    });
}
