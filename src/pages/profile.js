// ============================================================
// BoneQuest v2 — User Profile Page (Enhanced UI)
// ============================================================

import { auth } from '../utils/auth.js';
import { api } from '../utils/api.js';

export function renderProfile(container) {
    const user = auth.user;
    if (!user) {
        window.location.hash = '#/signin';
        return;
    }

    const icons = {
        user: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`,
        security: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>`,
        settings: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>`,
        activity: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
        edit: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path></svg>`,
        hospital: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3v-4h-3V7a1 1 0 0 1 1-1h3z"></path></svg>`,
        mail: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>`,
        calendar: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>`,
    };

    container.innerHTML = `
        <div class="profile-container animate-fade-in">
            <div class="profile-layout">
                <!-- Sidebar Nav -->
                <aside class="profile-sidebar glass">
                    <div class="sidebar-header">
                        <span class="sidebar-title">Clinical Settings</span>
                    </div>
                    <nav class="profile-nav">
                        <button class="profile-nav-item active" data-section="account">
                            <i class="nav-icon">${icons.user}</i> 
                            <span>Account Details</span>
                        </button>
                        <button class="profile-nav-item" data-section="security">
                            <i class="nav-icon">${icons.security}</i> 
                            <span>Privacy & Security</span>
                        </button>
                        <button class="profile-nav-item" data-section="preferences">
                            <i class="nav-icon">${icons.settings}</i> 
                            <span>Display Preferences</span>
                        </button>
                        <button class="profile-nav-item" data-section="audit">
                            <i class="nav-icon">${icons.activity}</i> 
                            <span>Audit & Logs</span>
                        </button>
                    </nav>
                </aside>

                <!-- Main Content -->
                <div class="profile-main">
                    <!-- Hero Section -->
                    <section class="profile-hero premium-card">
                        <div class="hero-glow-effect"></div>
                        <div class="profile-avatar-container">
                            <div class="profile-avatar-outer">
                                <div class="profile-avatar-inner">
                                    ${user.full_name?.charAt(0) || user.email.charAt(0)}
                                </div>
                            </div>
                            <button class="avatar-edit-btn" title="Change Avatar">
                                ${icons.edit}
                            </button>
                        </div>
                        
                        <div class="profile-info-group">
                            <div class="role-badge-row">
                                <span class="clinical-badge">
                                    <span class="badge-pulse"></span>
                                    ${user.role?.toUpperCase() || 'CLINICIAN'}
                                </span>
                                <span class="verification-badge">
                                    Verified Practitioner
                                </span>
                            </div>
                            <h1 class="profile-display-name">${user.full_name || 'BoneQuest Member'}</h1>
                            <p class="profile-email-subtext">${user.email}</p>
                            
                            <div class="profile-quick-stats">
                                <div class="quick-stat">
                                    <span class="stat-label">HOSPITAL ID</span>
                                    <span class="stat-value highlight">${user.hospital_id || 'Not Assigned'}</span>
                                </div>
                                <div class="quick-stat">
                                    <span class="stat-label">JOINED</span>
                                    <span class="stat-value">${new Date().toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</span>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Profile Form Section -->
                    <section id="section-account" class="profile-section profile-card glass-strong animate-slide-up" style="--delay: 100ms">
                        <div class="card-header-premium">
                            <div class="header-text">
                                <h2>Clinical Identification</h2>
                                <p>Ensure your professional credentials are accurate for auditing and reporting.</p>
                            </div>
                            <div class="header-action">
                                <span class="sync-status">Last synced: Just now</span>
                            </div>
                        </div>

                        <form id="profile-form" class="premium-form">
                            <div class="form-grid-layout">
                                <div class="form-field">
                                    <label>Account Email</label>
                                    <div class="input-wrapper-premium readonly">
                                        <i class="field-icon">${icons.mail}</i>
                                        <input type="email" value="${user.email}" disabled />
                                        <span class="field-lock-tag">LOCKED</span>
                                    </div>
                                    <p class="field-help">Managed by system administrator</p>
                                </div>

                                <div class="form-field">
                                    <label>Professional Status</label>
                                    <div class="input-wrapper-premium readonly">
                                        <i class="field-icon">${icons.hospital}</i>
                                        <input type="text" value="${user.role}" disabled />
                                    </div>
                                </div>

                                <div class="form-field">
                                    <label>Full Legal Name</label>
                                    <div class="input-wrapper-premium">
                                        <i class="field-icon">${icons.user}</i>
                                        <input type="text" id="profile-name" value="${user.full_name || ''}" placeholder="Dr. Jane Doe" required />
                                    </div>
                                </div>

                                <div class="form-field">
                                    <label>Hospital Affiliation ID</label>
                                    <div class="input-wrapper-premium">
                                        <i class="field-icon">${icons.calendar}</i>
                                        <input type="text" id="profile-hospital" value="${user.hospital_id || ''}" placeholder="HOSP-2024-X" />
                                    </div>
                                </div>
                            </div>

                            <div class="form-actions-premium">
                                <button type="reset" class="btn-cancel">Discard Changes</button>
                                <button type="submit" id="save-profile" class="btn-save-glow">
                                    <span class="btn-text">Save Professional Profile</span>
                                    <span class="btn-arrow">→</span>
                                </button>
                            </div>
                        </form>
                    </section>

                    <!-- Security Section -->
                    <section id="section-security" class="profile-section profile-card glass-strong animate-slide-up hidden" style="--delay: 100ms">
                        <div class="card-header-premium">
                            <div class="header-text">
                                <h2>Privacy & Security</h2>
                                <p>Manage your login credentials and security protocols.</p>
                            </div>
                        </div>
                        <form id="security-form" class="premium-form">
                            <div class="form-grid-layout single-col">
                                <div class="form-field max-w-sm">
                                    <label>Update Passkey</label>
                                    <div class="input-wrapper-premium">
                                        <i class="field-icon">${icons.security}</i>
                                        <input type="password" id="profile-pass" placeholder="••••••••" minlength="6" required />
                                    </div>
                                    <p class="field-help">Enter a new secure access key (min. 6 characters).</p>
                                </div>
                            </div>
                            <div class="form-actions-premium">
                                <button type="reset" class="btn-cancel">Clear</button>
                                <button type="submit" id="save-security" class="btn-save-glow">
                                    <span class="btn-text">Update Security</span>
                                    <span class="btn-arrow">→</span>
                                </button>
                            </div>
                        </form>
                    </section>

                    <!-- Preferences Section -->
                    <section id="section-preferences" class="profile-section profile-card glass-strong animate-slide-up hidden" style="--delay: 100ms">
                         <div class="card-header-premium">
                            <div class="header-text">
                                <h2>Display Preferences</h2>
                                <p>Customize your BoneQuest interface for optimal clinical viewing.</p>
                            </div>
                        </div>
                        <div class="premium-form">
                            <div class="form-grid-layout">
                                <div class="form-field">
                                    <label>Interface Theme</label>
                                    <div class="input-wrapper-premium readonly">
                                        <i class="field-icon">${icons.settings}</i>
                                        <input type="text" value="Clinical Dark Theme" disabled />
                                        <span class="field-lock-tag">DEFAULT</span>
                                    </div>
                                </div>
                                <div class="form-field">
                                    <label>Language</label>
                                    <div class="input-wrapper-premium readonly">
                                        <i class="field-icon">${icons.settings}</i>
                                        <input type="text" value="English (US)" disabled />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    <!-- Audit Section -->
                    <section id="section-audit" class="profile-section profile-card glass-strong animate-slide-up hidden" style="--delay: 100ms">
                         <div class="card-header-premium">
                            <div class="header-text">
                                <h2>Audit & Logs</h2>
                                <p>View your recent activity. Full logs available to admins.</p>
                            </div>
                        </div>
                        <div class="audit-list">
                            <div class="audit-item">
                                <div class="audit-icon">${icons.activity}</div>
                                <div class="audit-details">
                                    <span class="audit-action">Last Login</span>
                                    <span class="audit-time">${user.last_login ? new Date(user.last_login).toLocaleString() : 'Just now'}</span>
                                </div>
                            </div>
                            <div class="audit-item">
                                <div class="audit-icon">${icons.user}</div>
                                <div class="audit-details">
                                    <span class="audit-action">Account Created</span>
                                    <span class="audit-time">${user.created_at ? new Date(user.created_at).toLocaleString() : 'Unknown'}</span>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>

        <div id="profile-toast" class="premium-toast hidden">
            <div class="toast-content">
                <span class="toast-icon"></span>
                <span class="toast-message"></span>
            </div>
            <div class="toast-progress"></div>
        </div>
    `;

    // --- Interaction Logic ---
    const accountForm = container.querySelector('#profile-form');
    const securityForm = container.querySelector('#security-form');
    const toast = container.querySelector('#profile-toast');
    const saveBtn = container.querySelector('#save-profile');
    const saveSecBtn = container.querySelector('#save-security');

    const showToast = (message, type = 'success') => {
        toast.className = `premium-toast toast-${type}`;
        toast.querySelector('.toast-icon').innerHTML = type === 'success' ? '✓' : '✕';
        toast.querySelector('.toast-message').textContent = message;
        toast.classList.remove('hidden');
        
        // Reset and start progression
        const progress = toast.querySelector('.toast-progress');
        progress.style.transition = 'none';
        progress.style.width = '100%';
        
        setTimeout(() => {
            progress.style.transition = 'width 5000ms linear';
            progress.style.width = '0%';
        }, 10);
        
        setTimeout(() => {
            toast.classList.add('hidden');
        }, 5000);
    };

    accountForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        saveBtn.disabled = true;
        const originalContent = saveBtn.innerHTML;
        saveBtn.innerHTML = `<span class="spinner-premium"></span> Syncing...`;

        const data = {
            full_name: container.querySelector('#profile-name').value,
            hospital_id: container.querySelector('#profile-hospital').value,
        };

        try {
            const updatedUser = await api.updateMe(data);
            auth.updateUser(updatedUser);
            
            showToast('Professional profile synchronized successfully!');
            
            // Update UI elements
            container.querySelector('.profile-avatar-inner').textContent = updatedUser.full_name?.charAt(0) || updatedUser.email.charAt(0);
            container.querySelector('.profile-display-name').textContent = updatedUser.full_name || 'BoneQuest Member';
            container.querySelector('.stat-value.highlight').textContent = updatedUser.hospital_id || 'Not Assigned';
        } catch (err) {
            showToast(err.message || 'Synchronization failed. Network error.', 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalContent;
        }
    });

    securityForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        saveSecBtn.disabled = true;
        const originalContent = saveSecBtn.innerHTML;
        saveSecBtn.innerHTML = `<span class="spinner-premium"></span> Updating...`;

        const newPass = container.querySelector('#profile-pass').value;

        try {
            await api.updateMe({ password: newPass });
            showToast('Security credentials updated successfully!');
            container.querySelector('#profile-pass').value = '';
        } catch (err) {
            showToast(err.message || 'Security update failed.', 'error');
        } finally {
            saveSecBtn.disabled = false;
            saveSecBtn.innerHTML = originalContent;
        }
    });

    // Navigation switching
    container.querySelectorAll('.profile-nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const sectionId = btn.dataset.section;
            
            // Update active state on nav
            container.querySelectorAll('.profile-nav-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Hide all sections, show target
            container.querySelectorAll('.profile-section').forEach(sec => {
                sec.classList.add('hidden');
            });
            
            const targetSection = container.querySelector(`#section-${sectionId}`);
            if (targetSection) {
                targetSection.classList.remove('hidden');
            }
        });
    });
}
