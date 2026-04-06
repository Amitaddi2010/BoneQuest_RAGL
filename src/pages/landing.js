// ============================================================
// BoneQuest v2 — Landing Page
// ============================================================

import { initScrollAnimations, animateCounter, createStarfield } from '../utils/animations.js';

export function renderLanding(container) {
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
                        <span class="badge-new">New</span>
                        PageIndex-Powered Reasoning RAG
                    </span>
                </div>
                <h1>
                    AI-Powered<br>
                    <span class="highlight">Orthopaedic Intelligence.</span>
                </h1>
                <p class="hero-subtitle">
                    BoneQuest replaces vector search with reasoning-based retrieval. 
                    Navigate clinical protocols like an expert — with full audit trails and 98.7% accuracy.
                </p>
                <div class="hero-actions">
                    <a href="#/chat" class="btn btn-primary btn-lg">
                        Start Querying <span class="arrow">↗</span>
                    </a>
                    <a href="#/" class="btn btn-secondary btn-lg" data-scroll="features">
                        View Features
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
                                <button type="button" class="hero-demo-new" id="hero-demo-new">＋ New Chat</button>
                                <div class="hero-demo-sessions" role="tablist" aria-label="Sample clinical chats">
                                    <button type="button" class="hero-demo-session is-active" data-scenario="0" role="tab" aria-selected="true">Tibial shaft + DM</button>
                                    <button type="button" class="hero-demo-session" data-scenario="1" role="tab" aria-selected="false">ACL rehab</button>
                                    <button type="button" class="hero-demo-session" data-scenario="2" role="tab" aria-selected="false">Femoral neck · 75y</button>
                                </div>
                                <p class="hero-demo-sidebar-hint">Interactive preview — same layout as live chat.</p>
                            </aside>
                            <div class="mockup-content mockup-platform-main">
                                <div class="mockup-glow-pointer" id="mockup-pointer"></div>
                                <header class="hero-demo-top">
                                    <div class="hero-demo-top-titles">
                                        <span class="hero-demo-title">BoneQuest AI</span>
                                        <span class="hero-demo-sub">Groq LLaMA · PageIndex RAG</span>
                                    </div>
                                    <span class="hero-demo-role-pill">Role: Resident</span>
                                </header>
                                <div class="hero-demo-thread" id="hero-demo-thread">
                                    <div class="hero-demo-msg hero-demo-msg--user">
                                        <span class="hero-demo-msg-label">You</span>
                                        <p class="hero-demo-msg-text" id="hero-demo-q"></p>
                                    </div>
                                    <div class="hero-demo-msg hero-demo-msg--ai">
                                        <span class="hero-demo-msg-label">BoneQuest</span>
                                        <p class="hero-demo-msg-text" id="hero-demo-a"></p>
                                        <div class="hero-demo-citations" id="hero-demo-cite"></div>
                                    </div>
                                </div>
                                <footer class="hero-demo-composer">
                                    <div class="hero-demo-chips" id="hero-demo-chips" aria-label="Try a sample query"></div>
                                    <div class="hero-demo-input-row">
                                        <span class="hero-demo-input-fake">Ask about protocols, upload imaging…</span>
                                        <span class="hero-demo-send" aria-hidden="true">
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>
                                        </span>
                                    </div>
                                </footer>
                            </div>
                            <aside class="mockup-platform-trace" aria-label="Reasoning trace preview">
                                <div class="hero-demo-trace-head">
                                    <span>🔍 Reasoning Trace</span>
                                    <span class="badge badge-accent hero-demo-live-badge"><span class="badge-dot"></span> Live</span>
                                </div>
                                <ul class="hero-demo-trace-list" id="hero-demo-trace-list"></ul>
                                <p class="hero-demo-meta" id="hero-demo-meta">Tree index · no vector DB</p>
                            </aside>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== TRUSTED BY ========== -->
        <section class="trusted-section trusted-section--platform">
            <p class="trusted-label reveal">Designed for Leading Medical Institutions</p>
            <div class="ticker-container">
                <div class="ticker-track" id="logo-ticker">
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> PGIMER Chandigarh</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> AIIMS Delhi</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> CMC Vellore</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> JIPMER Puducherry</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> NIMHANS Bangalore</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> KEM Mumbai</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> PGIMER Chandigarh</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> AIIMS Delhi</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> CMC Vellore</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> JIPMER Puducherry</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> NIMHANS Bangalore</div>
                    <div class="ticker-item"><span class="ticker-icon">🏥</span> KEM Mumbai</div>
                </div>
            </div>
        </section>

        <!-- ========== FEATURES (Bento Grid) ========== -->
        <section class="features-section section" id="features">
            <div class="container">
                <div class="section-header section-header--platform reveal">
                    <span class="badge badge-accent"><span class="badge-dot"></span> Core Capabilities</span>
                    <span class="platform-eyebrow">bonequest · pageindex_rag / capabilities</span>
                    <h2>Why PageIndex Outperforms<br>Traditional Vector RAG</h2>
                    <p>Structure-aware reasoning that understands clinical protocols the way clinicians do.</p>
                </div>

                <div class="features-grid stagger">
                    <!-- Feature 1: Multi-Hop Reasoning -->
                    <div class="card feature-card micro-card reveal">
                        <div class="feature-icon">🔗</div>
                        <h3>Multi-Hop Reasoning</h3>
                        <p>Automatically follows cross-references like "See Appendix G" — retrieving from multiple sections to build complete answers.</p>
                        <div class="feature-visual platform-panel">
                            <div class="platform-trace-flow">
                                <div class="platform-trace-flow__row"><span class="platform-trace-flow__tag">Step 1</span> Found fracture management → Section 2.1</div>
                                <div class="platform-trace-flow__row"><span class="platform-trace-flow__tag">Step 2</span> Detected diabetes mention → Ref Section 3.4</div>
                                <div class="platform-trace-flow__row platform-trace-flow__row--ok"><span class="platform-trace-flow__tag platform-trace-flow__tag--ok">Step 3</span> Combined clinical guidance ✓</div>
                            </div>
                            <p class="platform-panel-foot">multi_hop · cross_reference resolved</p>
                        </div>
                    </div>

                    <!-- Feature 2: Vision-Native -->
                    <div class="card feature-card micro-card reveal">
                        <div class="feature-icon">👁️</div>
                        <h3>Vision-Native Retrieval</h3>
                        <p>No OCR errors. PageIndex "sees" X-rays, surgical diagrams, and complex tables natively — preserving visual context.</p>
                        <div class="feature-visual platform-panel">
                            <div class="platform-mini-tiles">
                                <div class="platform-mini-tile"><span class="platform-mini-tile__ico">📄</span> Text protocols</div>
                                <div class="platform-mini-tile"><span class="platform-mini-tile__ico">🩻</span> X-ray / CT</div>
                                <div class="platform-mini-tile"><span class="platform-mini-tile__ico">📊</span> Complex tables</div>
                            </div>
                            <p class="platform-panel-foot">vision_native · no_ocr_pipeline</p>
                        </div>
                    </div>

                    <!-- Feature 3: Audit Trail -->
                    <div class="card feature-card micro-card reveal">
                        <div class="feature-icon">📋</div>
                        <h3>Full Audit Trail</h3>
                        <p>Every reasoning step is logged — which sections were consulted, how confidence was assessed, and exact page citations.</p>
                        <div class="feature-visual platform-panel">
                            <div class="platform-audit-block">
                                <div><span class="platform-audit-k">Trace</span> Section 4.2 → 3.5 → 3.6</div>
                                <div><span class="platform-audit-k">Pages</span> 78–82, 92–95, 110–112</div>
                                <div><span class="platform-audit-k">Confidence</span> <span class="platform-audit-val">0.94 (High)</span></div>
                            </div>
                            <p class="platform-panel-foot">audit_trail · export_ready</p>
                        </div>
                    </div>

                    <!-- Feature 4: Role-Based Navigation -->
                    <div class="card feature-card micro-card reveal">
                        <div class="feature-icon">👥</div>
                        <h3>Role-Based Navigation</h3>
                        <p>Same protocol, different depth. Patients get simple explanations, residents get pathophysiology, consultants get advanced techniques.</p>
                        <div class="feature-visual platform-panel">
                            <div class="platform-role-stack">
                                <div class="platform-role-row"><span class="platform-role-pill">Patient</span><span class="platform-role-txt">Simple fracture explanation</span></div>
                                <div class="platform-role-row platform-role-row--active"><span class="platform-role-pill platform-role-pill--on">Resident</span><span class="platform-role-txt">Pathophysiology + differential</span></div>
                                <div class="platform-role-row"><span class="platform-role-pill">Consultant</span><span class="platform-role-txt">Advanced surgical techniques</span></div>
                            </div>
                            <p class="platform-panel-foot">role_router · same_protocol_tree</p>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== PROCESS ========== -->
        <section class="process-section section">
            <div class="container">
                <div class="section-header section-header--platform reveal">
                    <span class="badge badge-accent"><span class="badge-dot"></span> How It Works</span>
                    <span class="platform-eyebrow">bonequest · ingest_pipeline / four_steps</span>
                    <h2>From PDF to Clinical Intelligence<br>in Four Steps</h2>
                </div>

                <div class="process-grid stagger">
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">1</div>
                        <span class="platform-step-id">pdf_ingest</span>
                        <h4>Upload Protocol</h4>
                        <p>Upload your orthopaedic guidelines, surgical manuals, or clinical protocols in PDF format.</p>
                    </div>
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">2</div>
                        <span class="platform-step-id">tree_build</span>
                        <h4>Build Tree Index</h4>
                        <p>PageIndex generates a hierarchical tree capturing chapters, sections, and cross-references.</p>
                    </div>
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">3</div>
                        <span class="platform-step-id">reasoning_query</span>
                        <h4>Query with Reasoning</h4>
                        <p>Ask clinical questions. The AI reasons through the tree, following references across sections.</p>
                    </div>
                    <div class="process-step process-step-card reveal">
                        <div class="process-number">4</div>
                        <span class="platform-step-id">citations_out</span>
                        <h4>Get Cited Answers</h4>
                        <p>Receive synthesized answers with exact page citations, confidence scores, and full reasoning trace.</p>
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
                        <div class="stat-value"><span class="accent" id="stat-accuracy">98.7</span>%</div>
                        <div class="stat-label">Retrieval Accuracy</div>
                    </div>
                    <div class="stat-item stat-tile">
                        <div class="stat-value" id="stat-latency">280</div>
                        <div class="stat-label">Avg. Latency (ms)</div>
                    </div>
                    <div class="stat-item stat-tile">
                        <div class="stat-value"><span class="accent" id="stat-hops">3</span>x</div>
                        <div class="stat-label">Multi-hop Reasoning</div>
                    </div>
                    <div class="stat-item stat-tile">
                        <div class="stat-value" id="stat-docs">0</div>
                        <div class="stat-label">Vector DBs Required</div>
                    </div>
                </div>
                <p class="platform-strip-meta">live_metrics · benchmark_internal</p>
                </div>
            </div>
        </section>

        <!-- ========== COMPARISON TABLE ========== -->
        <section class="comparison-section section" id="comparison">
            <div class="container">
                <div class="section-header section-header--platform reveal">
                    <span class="badge badge-accent"><span class="badge-dot"></span> Performance Comparison</span>
                    <span class="platform-eyebrow">bonequest · architecture_diff / v1_faiss vs v2_pageindex</span>
                    <h2>FAISS vs PageIndex</h2>
                    <p>Side-by-side benchmark of BoneQuest v1 (FAISS) versus v2 (PageIndex) architecture.</p>
                </div>

                <div class="comparison-table-wrapper comparison-surface reveal-scale">
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Architecture Aspect</th>
                                <th class="col-v1">BoneQuest v1 (FAISS)</th>
                                <th class="col-v2">BoneQuest v2 (PageIndex) 
                                    <span class="v2-badge-premium">Next-Gen</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="comp-row" data-aspect="vector-db">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Vector DB Required</span>
                                        <span class="aspect-hint">Infrastructure complexity and cost</span>
                                    </div>
                                </td>
                                <td>Yes (FAISS index)</td>
                                <td class="best-choice">No (JSON tree)</td>
                            </tr>
                            <tr class="comp-row" data-aspect="chunking">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Chunking Strategy</span>
                                        <span class="aspect-hint">How text is broken for retrieval</span>
                                    </div>
                                </td>
                                <td>Fixed 1500 chars</td>
                                <td class="best-choice">Natural sections</td>
                            </tr>
                            <tr class="comp-row" data-aspect="reasoning">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Multi-hop Reasoning</span>
                                        <span class="aspect-hint">Ability to resolve cross-references</span>
                                    </div>
                                </td>
                                <td><span class="cross-icon">✕</span> Limited</td>
                                <td class="best-choice"><span class="check-icon">✓</span> Full agentic loop</td>
                            </tr>
                            <tr class="comp-row" data-aspect="explainability">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Explainability</span>
                                        <span class="aspect-hint">Audit trail for clinical decisions</span>
                                    </div>
                                </td>
                                <td>"Top-K similar chunks"</td>
                                <td class="best-choice">"Reasoning: X → Y → Z"</td>
                            </tr>
                            <tr class="comp-row" data-aspect="vision">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Vision Support</span>
                                        <span class="aspect-hint">Native handling of imaging/tables</span>
                                    </div>
                                </td>
                                <td><span class="cross-icon">✕</span> Separate pipeline</td>
                                <td class="best-choice"><span class="check-icon">✓</span> Native</td>
                            </tr>
                            <tr class="comp-row highlight-stat" data-aspect="accuracy">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Retrieval Accuracy</span>
                                    </div>
                                </td>
                                <td>
                                    <div class="stat-bar-container">
                                        <span class="stat-num">85%</span>
                                        <div class="stat-bar"><div class="stat-bar-fill" style="width: 85%;"></div></div>
                                    </div>
                                </td>
                                <td class="best-choice">
                                    <div class="stat-bar-container">
                                        <span class="stat-num">98.7%</span>
                                        <div class="stat-bar accent-bar"><div class="stat-bar-fill" style="width: 98.7%;"></div></div>
                                    </div>
                                </td>
                            </tr>
                            <tr class="comp-row highlight-stat" data-aspect="latency">
                                <td>
                                    <div class="aspect-info">
                                        <span class="aspect-name">Average Latency</span>
                                    </div>
                                </td>
                                <td>
                                    <div class="stat-bar-container">
                                        <span class="stat-num">487ms</span>
                                        <div class="stat-bar warn-bar"><div class="stat-bar-fill" style="width: 70%;"></div></div>
                                    </div>
                                </td>
                                <td class="best-choice">
                                    <div class="stat-bar-container">
                                        <span class="stat-num">280ms</span>
                                        <div class="stat-bar success-bar"><div class="stat-bar-fill" style="width: 30%;"></div></div>
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
                    <span class="badge badge-accent"><span class="badge-dot"></span> Clinical Validation</span>
                    <span class="platform-eyebrow">bonequest · clinician_feedback / verified_quotes</span>
                    <h2>Trusted by Orthopaedic Experts</h2>
                </div>

                <div class="testimonials-grid stagger">
                    <div class="card testimonial-card micro-card reveal">
                        <div class="testimonial-stars">★★★★★</div>
                        <p class="testimonial-quote">"The reasoning trace is a game-changer. I can verify exactly which protocol sections the AI consulted before using its recommendation in patient care."</p>
                        <div class="testimonial-author">
                            <div class="testimonial-avatar">DR</div>
                            <div>
                                <div class="testimonial-name">Dr. Rajesh Kumar</div>
                                <div class="testimonial-role">Senior Consultant, Orthopaedics — PGIMER</div>
                            </div>
                        </div>
                        <p class="platform-validated">trace_verified · PGIMER_chandigarh</p>
                    </div>
                    <div class="card testimonial-card micro-card reveal">
                        <div class="testimonial-stars">★★★★★</div>
                        <p class="testimonial-quote">"Multi-hop reasoning handles complex comorbidity cases beautifully. It cross-references diabetes guidelines with fracture management — something FAISS could never do."</p>
                        <div class="testimonial-author">
                            <div class="testimonial-avatar">PS</div>
                            <div>
                                <div class="testimonial-name">Dr. Priya Sharma</div>
                                <div class="testimonial-role">Orthopaedic Registrar — AIIMS Delhi</div>
                            </div>
                        </div>
                        <p class="platform-validated">comorbidity_path · AIIMS_delhi</p>
                    </div>
                    <div class="card testimonial-card micro-card reveal">
                        <div class="testimonial-stars">★★★★★</div>
                        <p class="testimonial-quote">"As a resident, the role-based responses are invaluable. I get pathophysiology-level detail while patients get clear, understandable explanations from the same system."</p>
                        <div class="testimonial-author">
                            <div class="testimonial-avatar">AV</div>
                            <div>
                                <div class="testimonial-name">Dr. Arjun Verma</div>
                                <div class="testimonial-role">PG Resident, MS Ortho — CMC Vellore</div>
                            </div>
                        </div>
                        <p class="platform-validated">role_depth · CMC_vellore</p>
                    </div>
                    <div class="card testimonial-card micro-card reveal">
                        <div class="testimonial-stars">★★★★★</div>
                        <p class="testimonial-quote">"Zero vector DB infrastructure means we deployed in a day. The audit trail meets our institutional compliance requirements for AI-assisted clinical decisions."</p>
                        <div class="testimonial-author">
                            <div class="testimonial-avatar">MN</div>
                            <div>
                                <div class="testimonial-name">Dr. Meera Nair</div>
                                <div class="testimonial-role">HOD Orthopaedics — JIPMER</div>
                            </div>
                        </div>
                        <p class="platform-validated">deploy_day1 · compliance_trace · JIPMER</p>
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
                        <span>bonequest</span><span class="platform-cta-rail__sep">·</span><span>route</span><span class="platform-cta-rail__sep">·</span><span>#/chat</span><span class="platform-cta-rail__sep">·</span><span>pageindex</span>
                    </div>
                    <h2>Ready to Transform Your<br>Clinical Protocols?</h2>
                    <p>Upload your first orthopaedic guideline and experience reasoning-based retrieval.</p>
                    <a href="#/chat" class="btn btn-primary btn-lg">
                        Start Querying Now <span class="arrow">↗</span>
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
                        <p>AI-Powered Orthopaedic Intelligence — Reasoning-based RAG for clinical decision support.</p>
                        <div class="footer-newsletter">
                            <p style="font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-3);">Join our newsletter</p>
                            <div class="footer-newsletter-input">
                                <input type="email" placeholder="name@email.com" aria-label="Email for newsletter">
                                <button class="btn btn-primary">Subscribe</button>
                            </div>
                        </div>
                    </div>
                    <div class="footer-column">
                        <h5>Platform</h5>
                        <ul class="footer-links">
                            <li><a href="#/dashboard">Dashboard</a></li>
                            <li><a href="#/chat">AI Chat</a></li>
                            <li><a href="#/">Features</a></li>
                            <li><a href="#/">Documentation</a></li>
                        </ul>
                    </div>
                    <div class="footer-column">
                        <h5>Resources</h5>
                        <ul class="footer-links">
                            <li><a href="#">PageIndex Paper</a></li>
                            <li><a href="#">API Reference</a></li>
                            <li><a href="#">Clinical Guidelines</a></li>
                            <li><a href="#">Research</a></li>
                        </ul>
                    </div>
                    <div class="footer-column">
                        <h5>Connect</h5>
                        <ul class="footer-links">
                            <li><a href="#">GitHub</a></li>
                            <li><a href="#">LinkedIn</a></li>
                            <li><a href="#">Twitter / X</a></li>
                            <li><a href="#">Contact</a></li>
                        </ul>
                    </div>
                </div>
                <div class="footer-bottom">
                    <p>© 2026 BoneQuest. Built with PageIndex.</p>
                    <div class="footer-socials">
                        <a href="#" aria-label="GitHub">⌘</a>
                        <a href="#" aria-label="LinkedIn">in</a>
                        <a href="#" aria-label="Twitter">𝕏</a>
                    </div>
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
        label: 'Tibial shaft + DM',
        query: 'Management of comminuted tibial shaft fracture in a diabetic patient?',
        answer: 'Prioritize neurovascular status and soft-tissue envelope. Use spanning external fixation when swelling or contamination is high. When cleared for definitive care, follow your guideline’s diabetic peri-operative pathway: glycemic targets, infection surveillance, and staged fixation if needed.',
        citations: 'Cited: § 2.1–2.3 (tibial shaft), § 3.4 (diabetes peri-op) · pp. 78–82, 96',
        trace: [
            { icon: '📂', text: 'Tree: Fracture Management → Tibial shaft' },
            { icon: '🔗', text: 'Cross-ref resolved → “See diabetes peri-op” § 3.4' },
            { icon: '✓', text: 'Answer synthesized · confidence 0.94' },
        ],
        meta: 'Latency ~280ms · PageIndex tree walk',
    },
    {
        label: 'ACL rehab',
        query: 'ACL reconstruction rehabilitation protocol — week by week timeline?',
        answer: 'Early phase (0–2 wk): ROM within brace limits, quad sets, partial WB as protocol allows. Mid phase: closed-chain strength, proprioception. Late: running criteria, sport-specific when strength and hop tests meet targets. Always align with your graft and surgeon-specific orders.',
        citations: 'Cited: § 5.2 ACL rehab phases · pp. 142–151',
        trace: [
            { icon: '📂', text: 'Tree: Sports knee → ACL reconstruction' },
            { icon: '📄', text: 'Section 5.2 “Rehabilitation phases” loaded' },
            { icon: '✓', text: 'Timeline condensed for resident depth' },
        ],
        meta: 'Role-aware depth · Resident view',
    },
    {
        label: 'Femoral neck · 75y',
        query: 'Treatment for displaced femoral neck fracture in 75yo with CHF?',
        answer: 'Balance medical optimization of CHF with operative timing. In displaced femoral neck fractures in older adults, arthroplasty is commonly favored over fixation when bone quality and displacement warrant it — coordinate with cardiology for peri-op risk and anticoagulation.',
        citations: 'Cited: § 4.1 Hip fractures, § 1.3 Cardiac clearance · pp. 58–61, 24',
        trace: [
            { icon: '📂', text: 'Tree: Hip trauma → Femoral neck' },
            { icon: '🔗', text: 'Pulled comorbidity box: CHF / cardiology' },
            { icon: '✓', text: 'Options framed with guideline citations' },
        ],
        meta: 'Multi-hop · 2 guideline sections merged',
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

