// ============================================================
// BoneQuest v2.2 — Theme Manager
// 3 themes: scrub-room (dark), reading-room (light), radiology (high-contrast)
// Persists selection in localStorage
// ============================================================

const THEME_KEY = 'bq_theme';
const THEMES = [
    { id: 'scrub-room',   label: '🔬 Scrub',     title: 'Scrub Room — Dark clinical theme' },
    { id: 'reading-room', label: '📖 Reading',    title: 'Reading Room — Light study theme' },
    { id: 'radiology',    label: '🩻 Radiology',  title: 'Radiology — High contrast PACS theme' },
];

const DEFAULT_THEME = 'scrub-room';

function getTheme() {
    return localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
}

function setTheme(themeId) {
    const valid = THEMES.find(t => t.id === themeId);
    if (!valid) return;
    
    document.documentElement.setAttribute('data-theme', themeId);
    localStorage.setItem(THEME_KEY, themeId);
    
    // Update any active switcher buttons
    document.querySelectorAll('.theme-switcher-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === themeId);
    });
    
    // Update meta theme-color
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
        const colors = {
            'scrub-room': '#0E7C6B',
            'reading-room': '#0A6D5E',
            'radiology': '#00D4AA',
        };
        meta.content = colors[themeId] || '#0E7C6B';
    }
}

function initTheme() {
    const saved = getTheme();
    document.documentElement.setAttribute('data-theme', saved);
}

/**
 * Creates the theme switcher HTML and wires up event listeners.
 * @returns {string} HTML string for the theme switcher
 */
function createThemeSwitcherHTML() {
    const current = getTheme();
    return `
        <div class="theme-switcher" title="Switch clinical theme">
            ${THEMES.map(t => `
                <button class="theme-switcher-btn ${t.id === current ? 'active' : ''}" 
                        data-theme="${t.id}" 
                        title="${t.title}">
                    ${t.label}
                </button>
            `).join('')}
        </div>
    `;
}

function attachThemeSwitcherListeners(container) {
    container.querySelectorAll('.theme-switcher-btn').forEach(btn => {
        btn.addEventListener('click', () => setTheme(btn.dataset.theme));
    });
}

// Initialize theme on module load
initTheme();

export const theme = {
    get: getTheme,
    set: setTheme,
    init: initTheme,
    THEMES,
    createSwitcherHTML: createThemeSwitcherHTML,
    attachSwitcherListeners: attachThemeSwitcherListeners,
};
