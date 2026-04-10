// ============================================================
// BoneQuest v2.1 — Auth Pages (Sign In / Sign Up)
// ============================================================

import { api } from '../utils/api.js';
import { auth } from '../utils/auth.js';

export function renderSignIn(container) {
    container.innerHTML = `
        <div class="auth-page">
            <div class="auth-panel-left">
                <div class="auth-brand-content">
                    <div class="auth-logo">
                        <span>BoneQuest</span>
                    </div>
                    <h1>3-Signal Hybrid RAG for<br><span class="highlight">Precision Orthopaedics.</span></h1>
                    <p>BM25 keyword precision, semantic embeddings, and tree-based reasoning—fused for every clinical query.</p>
                    <div class="auth-features">
                        <div class="auth-feature">
                            <span class="auth-feature-icon">🔤</span>
                            <div>
                                <strong>BM25 Keyword Index</strong>
                                <p>Exact terminological retrieval</p>
                            </div>
                        </div>
                        <div class="auth-feature">
                            <span class="auth-feature-icon">🧬</span>
                            <div>
                                <strong>Semantic Embedding</strong>
                                <p>Conceptual similarity matching</p>
                            </div>
                        </div>
                        <div class="auth-feature">
                            <span class="auth-feature-icon">🌲</span>
                            <div>
                                <strong>Tree Reasoning</strong>
                                <p>Hierarchical document navigation</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="auth-panel-right">
                <div class="auth-form-container">
                    <div class="auth-form-header">
                        <h2>Welcome back</h2>
                        <p>Sign in to your account to continue</p>
                    </div>
                    <form id="signin-form" class="auth-form" autocomplete="off">
                        <div class="form-group">
                            <label for="signin-email">Email Address</label>
                            <input type="email" id="signin-email" class="form-input" placeholder="doctor@hospital.org" required autocomplete="email">
                        </div>
                        <div class="form-group">
                            <label for="signin-password">Password</label>
                            <input type="password" id="signin-password" class="form-input" placeholder="••••••••" required autocomplete="current-password">
                        </div>
                        <div id="signin-error" class="form-error" style="display:none;"></div>
                        <button type="submit" class="btn btn-primary btn-full" id="signin-btn">
                            Sign In <span class="arrow">↗</span>
                        </button>
                    </form>
                    <div class="auth-footer">
                        <p>Don't have an account? <a href="#/signup" class="auth-link">Create account</a></p>
                    </div>
                    <div class="auth-demo-hint">
                        <p>🔬 <strong>Demo:</strong> Sign up with any email to explore</p>
                    </div>
                </div>
            </div>
        </div>
    `;

    const form = container.querySelector('#signin-form');
    const errorEl = container.querySelector('#signin-error');
    const btnEl = container.querySelector('#signin-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.style.display = 'none';
        btnEl.disabled = true;
        btnEl.innerHTML = '<span class="spinner"></span> Signing in...';

        try {
            const result = await api.signin({
                email: container.querySelector('#signin-email').value.trim(),
                password: container.querySelector('#signin-password').value,
            });
            auth.login(result);
            window.location.hash = '#/chat';
        } catch (err) {
            errorEl.textContent = err.message || 'Sign in failed';
            errorEl.style.display = 'block';
            btnEl.disabled = false;
            btnEl.innerHTML = 'Sign In <span class="arrow">↗</span>';
        }
    });
}


export function renderSignUp(container) {
    container.innerHTML = `
        <div class="auth-page">
            <div class="auth-panel-left">
                <div class="auth-brand-content">
                    <div class="auth-logo">
                        <span>BoneQuest</span>
                    </div>
                    <h1>Join the Future of<br><span class="highlight">Hybrid RAG Intelligence.</span></h1>
                    <p>Create your account and harness 3-signal hybrid retrieval for clinical evidence discovery.</p>
                    <div class="auth-stats-row">
                        <div class="auth-stat">
                            <div class="auth-stat-value">99.2%</div>
                            <div class="auth-stat-label">Precision</div>
                        </div>
                        <div class="auth-stat">
                            <div class="auth-stat-value">340ms</div>
                            <div class="auth-stat-label">Latency</div>
                        </div>
                        <div class="auth-stat">
                            <div class="auth-stat-value">3</div>
                            <div class="auth-stat-label">Signals</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="auth-panel-right">
                <div class="auth-form-container">
                    <div class="auth-form-header">
                        <h2>Create Account</h2>
                        <p>Set up your clinical profile</p>
                    </div>
                    <form id="signup-form" class="auth-form" autocomplete="off">
                        <div class="form-group">
                            <label for="signup-name">Full Name</label>
                            <input type="text" id="signup-name" class="form-input" placeholder="Dr. Jane Smith" required autocomplete="name">
                        </div>
                        <div class="form-group">
                            <label for="signup-email">Email Address</label>
                            <input type="email" id="signup-email" class="form-input" placeholder="doctor@hospital.org" required autocomplete="email">
                        </div>
                        <div class="form-group">
                            <label for="signup-hospital">Hospital ID <span class="form-optional">(optional)</span></label>
                            <input type="text" id="signup-hospital" class="form-input" placeholder="e.g., PGIMER-CHD">
                        </div>
                        <div class="form-group">
                            <label>Clinical Role</label>
                            <div class="role-cards" id="role-cards">
                                <div class="role-card" data-role="patient">
                                    <div class="role-card-icon">👤</div>
                                    <div class="role-card-title">Patient</div>
                                    <div class="role-card-desc">Simple explanations</div>
                                </div>
                                <div class="role-card selected" data-role="resident">
                                    <div class="role-card-icon">🩺</div>
                                    <div class="role-card-title">Resident</div>
                                    <div class="role-card-desc">Detailed pathophysiology</div>
                                </div>
                                <div class="role-card" data-role="consultant">
                                    <div class="role-card-icon">⚕️</div>
                                    <div class="role-card-title">Consultant</div>
                                    <div class="role-card-desc">Advanced techniques</div>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="signup-password">Password</label>
                            <input type="password" id="signup-password" class="form-input" placeholder="Min 6 characters" required minlength="6">
                        </div>
                        <div id="signup-error" class="form-error" style="display:none;"></div>
                        <button type="submit" class="btn btn-primary btn-full" id="signup-btn">
                            Create Account <span class="arrow">↗</span>
                        </button>
                    </form>
                    <div class="auth-footer">
                        <p>Already have an account? <a href="#/signin" class="auth-link">Sign in</a></p>
                    </div>
                </div>
            </div>
        </div>
    `;

    let selectedRole = 'resident';

    // Role card selection
    container.querySelectorAll('.role-card').forEach(card => {
        card.addEventListener('click', () => {
            container.querySelectorAll('.role-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            selectedRole = card.dataset.role;
        });
    });

    const form = container.querySelector('#signup-form');
    const errorEl = container.querySelector('#signup-error');
    const btnEl = container.querySelector('#signup-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.style.display = 'none';
        btnEl.disabled = true;
        btnEl.innerHTML = '<span class="spinner"></span> Creating account...';

        try {
            const result = await api.signup({
                full_name: container.querySelector('#signup-name').value.trim(),
                email: container.querySelector('#signup-email').value.trim(),
                hospital_id: container.querySelector('#signup-hospital').value.trim() || null,
                role: selectedRole,
                password: container.querySelector('#signup-password').value,
            });
            auth.login(result);
            window.location.hash = '#/chat';
        } catch (err) {
            errorEl.textContent = err.message || 'Sign up failed';
            errorEl.style.display = 'block';
            btnEl.disabled = false;
            btnEl.innerHTML = 'Create Account <span class="arrow">↗</span>';
        }
    });
}
