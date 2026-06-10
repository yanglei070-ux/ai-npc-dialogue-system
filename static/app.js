/**
 * 星辰学院 — Celestial Grimoire Frontend
 * Canvas constellation starfield + refined interactions
 */

// ── State ──────────────────────────────────────────────
const STORAGE_KEYS = {
    chatHistory: 'npc-chat-history',
    affinity: 'npc-affinity',
    currentNpc: 'npc-current-npc',
    theme: 'star-academy-theme',
    settings: 'npc-settings',
};

const MAX_MESSAGE_LENGTH = 500;
const WARNING_MESSAGE_LENGTH = 450;
const MAX_AVATAR_UPLOAD_BYTES = 2 * 1024 * 1024;
const ALLOWED_AVATAR_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'];
const PROVIDERS = {
    openai: {
        label: 'OpenAI',
        base_url: 'https://api.openai.com/v1',
        models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4o-preview', 'gpt-3.5-turbo'],
        registration_url: 'https://platform.openai.com/',
        docs_url: 'https://platform.openai.com/docs',
    },
    ollama: {
        label: 'Ollama (本地)',
        base_url: 'http://localhost:11434/v1',
        models: ['qwen2.5:7b', 'llama3.1:8b', 'mistral:7b', 'phi3:mini'],
        registration_url: 'https://ollama.com/',
        docs_url: 'https://github.com/ollama/ollama',
    },
    dashscope: {
        label: 'DashScope (通义)',
        base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        models: ['qwen-turbo', 'qwen-plus', 'qwen-max', 'qwen-long'],
        registration_url: 'https://dashscope.console.aliyun.com/',
        docs_url: 'https://help.aliyun.com/zh/dashscope/',
    },
    siliconflow: {
        label: 'SiliconFlow (硅基流动)',
        base_url: 'https://api.siliconflow.cn/v1',
        models: ['Qwen/Qwen2.5-7B-Instruct', 'Qwen/Qwen2.5-14B-Instruct', 'THUDM/glm-4-9b-chat'],
        registration_url: 'https://cloud.siliconflow.cn/',
        docs_url: 'https://docs.siliconflow.cn/',
    },
    deepseek: {
        label: 'DeepSeek',
        base_url: 'https://api.deepseek.com/v1',
        models: ['deepseek-chat', 'deepseek-coder'],
        registration_url: 'https://platform.deepseek.com/',
        docs_url: 'https://platform.deepseek.com/api-docs',
    },
    custom: {
        label: '自定义接口',
        base_url: '',
        models: [],
        registration_url: '',
        docs_url: '',
    },
    mock: {
        label: 'Mock 模式',
        base_url: '',
        models: [],
        registration_url: '',
        docs_url: '',
    },
};
const DEFAULT_SETTINGS = {
    provider: 'mock',
    base_url: '',
    api_key: '',
    model: 'gpt-4o-mini',
    temperature: 0.85,
    max_tokens: 512,
};

const state = {
    currentNpc: null,
    npcs: [],
    messages: {},
    renderedCount: {},
    startedSessions: {},
    isLoading: false,
    selectedAvatar: '⚔️',
    uploadedAvatarData: null,
    pendingConfirm: null,
    focusTrapCleanup: null,
    lastFocusedElement: null,
    newMsgCount: 0,
};

// ── DOM Helpers ────────────────────────────────────────
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

const DOM = {
    landingPage:   () => $('#landingPage'),
    landingStart:  () => $('#landingStart'),
    mainContent:   () => $('#mainContent'),
    cosmosCanvas:  () => $('#cosmosCanvas'),
    themeToggle:   () => $('#themeToggle'),
    themeIcon:     () => $('#themeIcon'),
    settingsToggle:() => $('#settingsToggle'),
    backToLanding: () => $('#backToLanding'),
    mobileToggle:  () => $('#mobileToggle'),
    mobileOverlay:  () => $('#mobileOverlay'),
    npcPanel:       () => $('#npcPanel'),
    npcList:        () => $('#npcList'),
    createNpcBtn:   () => $('#createNpcBtn'),
    welcomeScreen:  () => $('#welcomeScreen'),
    chatContainer:  () => $('#chatContainer'),
    chatPanel:      () => $('#chatPanel'),
    chatAvatar:     () => $('#chatAvatar'),
    chatAvatarRing: () => $('#chatAvatarRing'),
    chatName:       () => $('#chatName'),
    chatTitle:      () => $('#chatTitle'),
    affinityHeart:  () => $('#affinityHeart'),
    affinityLabel:  () => $('#affinityLabel'),
    affinityFill:   () => $('#affinityFill'),
    affinityShimmer:() => $('#affinityShimmer'),
    affinityValue:  () => $('#affinityValue'),
    messagesArea:   () => $('#messagesArea'),
    chatMenuBtn:    () => $('#chatMenuBtn'),
    chatMenuDropdown:() => $('#chatMenuDropdown'),
    clearChatBtnAlt:() => $('#clearChatBtnAlt'),
    resetBtnAlt:    () => $('#resetBtnAlt'),
    newSessionBtnAlt:() => $('#newSessionBtnAlt'),
    scrollBottomBtn:() => $('#scrollBottomBtn'),
    newMsgBadge:    () => $('#newMsgBadge'),
    suggestedResps: () => $('#suggestedResponses'),
    messageInput:   () => $('#messageInput'),
    charCounter:    () => $('#charCounter'),
    sendBtn:        () => $('#sendBtn'),
    memoryInfo:     () => $('#memoryInfo'),
    affinityLog:    () => $('#affinityLog'),
    clearChatBtn:   () => $('#clearChatBtn'),
    resetBtn:       () => $('#resetBtn'),
    newSessionBtn:  () => $('#newSessionBtn'),
    toastContainer: () => $('#toastContainer'),
    heartGradStart: () => $('.heart-grad-start'),
    heartGradEnd:   () => $('.heart-grad-end'),
    settingsModal:  () => $('#settingsModal'),
    settingsClose:  () => $('#settingsClose'),
    settingProvider:() => $('#settingProvider'),
    providerHelp:   () => $('#providerHelp'),
    settingBaseUrl: () => $('#settingBaseUrl'),
    settingApiKey:  () => $('#settingApiKey'),
    settingModel:   () => $('#settingModel'),
    settingTemp:    () => $('#settingTemp'),
    settingTempValue:() => $('#settingTempValue'),
    settingMaxTokens:() => $('#settingMaxTokens'),
    toggleApiKey:   () => $('#toggleApiKey'),
    testApiBtn:     () => $('#testApiBtn'),
    testApiResult:  () => $('#testApiResult'),
    saveSettingsBtn:() => $('#saveSettingsBtn'),
    resetSettingsBtn:() => $('#resetSettingsBtn'),
    settingsGoHome:() => $('#settingsGoHome'),
    createNpcModal: () => $('#createNpcModal'),
    createNpcClose: () => $('#createNpcClose'),
    cancelCreateNpc:() => $('#cancelCreateNpc'),
    confirmCreateNpc:() => $('#confirmCreateNpc'),
    npcName:        () => $('#npcName'),
    npcTitle:       () => $('#npcTitle'),
    npcAvatarCustom:() => $('#npcAvatarCustom'),
    avatarFileInput:() => $('#avatarFileInput'),
    avatarUploadTrigger:() => $('#avatarUploadTrigger'),
    avatarPreview:  () => $('#avatarPreview'),
    avatarPreviewImg:() => $('#avatarPreviewImg'),
    avatarRemove:   () => $('#avatarRemove'),
    npcPersonality: () => $('#npcPersonality'),
    npcBackstory:   () => $('#npcBackstory'),
    npcSpeechStyle: () => $('#npcSpeechStyle'),
    confirmModal:   () => $('#confirmModal'),
    confirmTitle:   () => $('#confirmTitle'),
    confirmMessage: () => $('#confirmMessage'),
    confirmClose:   () => $('#confirmClose'),
    confirmCancel:  () => $('#confirmCancel'),
    confirmOk:      () => $('#confirmOk'),
};

// ── API ────────────────────────────────────────────────
async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try {
        payload = await response.json();
    } catch (e) {
        payload = {};
    }

    if (!response.ok) {
        const message = response.status === 429
            ? '施法太快了，请稍后再试'
            : (payload.error || '网络波动，请稍后再试');
        const error = new Error(message);
        error.status = response.status;
        error.payload = payload;
        throw error;
    }

    return payload;
}

async function streamRequest(url, body, handlers = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });

    if (!response.ok) {
        let payload = {};
        try { payload = await response.json(); } catch (e) { payload = {}; }
        const error = new Error(payload.error || '网络波动，请稍后再试');
        error.status = response.status;
        throw error;
    }

    if (!response.body) throw new Error('当前浏览器不支持流式响应');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const {done, value} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream:true});
        const chunks = buffer.split('\n\n');
        buffer = chunks.pop() || '';

        for (const chunk of chunks) {
            const line = chunk.split('\n').find(item => item.startsWith('data: '));
            if (!line) continue;
            const data = JSON.parse(line.slice(6));
            if (data.type === 'status') handlers.onStatus?.(data.message);
            else if (data.type === 'token') handlers.onToken?.(data.content);
            else if (data.type === 'done') handlers.onDone?.(data);
            else if (data.type === 'error') handlers.onError?.(data.message);
        }
    }
}

const API = {
    async fetchNpcs() { return requestJson('/api/npcs'); },
    async chat(id, msg) {
        return requestJson(`/api/npcs/${id}/chat`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({message:msg, settings: loadSettings()}),
        });
    },
    async chatStream(id, msg, handlers) {
        return streamRequest(`/api/npcs/${id}/chat/stream`, {
            message: msg,
            settings: loadSettings(),
        }, handlers);
    },
    async resetNpc(id) { return requestJson(`/api/npcs/${id}/reset`, {method:'POST'}); },
    async startSession(id) { return requestJson(`/api/npcs/${id}/session`, {method:'POST'}); },
    async testConnection(settings) {
        return requestJson('/api/test-connection', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify(settings),
        });
    },
    async createNpc(payload) {
        return requestJson('/api/npcs/custom', {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify(payload),
        });
    },
    async deleteNpc(id) {
        return requestJson(`/api/npcs/${id}/delete`, {method:'POST'});
    },
};

// ── Tier Colors ────────────────────────────────────────
const TIER_COLORS = {
    hostile: {start:'#7a2e2e', end:'#b84444'},
    cold:    {start:'#2e4a7a', end:'#5b8fd4'},
    neutral: {start:'#4a4a5a', end:'#7a7a8a'},
    warm:    {start:'#7a6a1e', end:'#c9a84c'},
    bonded:  {start:'#6a2e7a', end:'#b84ab8'},
};

// ══════════════════════════════════════════════════════
// CANVAS CONSTELLATION STARFIELD
// ══════════════════════════════════════════════════════
function initCosmos() {
    const canvas = DOM.cosmosCanvas();
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let stars = [];
    let w, h;

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }

    function createStars() {
        const count = Math.min(120, Math.floor((w * h) / 9000));
        stars = [];
        for (let i = 0; i < count; i++) {
            stars.push({
                x: Math.random() * w,
                y: Math.random() * h,
                r: Math.random() * 1.4 + 0.3,
                vx: (Math.random() - 0.5) * 0.08,
                vy: (Math.random() - 0.5) * 0.08,
                phase: Math.random() * Math.PI * 2,
                speed: Math.random() * 0.008 + 0.003,
                brightness: Math.random() * 0.5 + 0.3,
            });
        }
    }

    const CONSTELLATION_DIST = 130;

    function draw(time) {
        ctx.clearRect(0, 0, w, h);

        // draw constellation lines
        ctx.lineWidth = 0.4;
        for (let i = 0; i < stars.length; i++) {
            for (let j = i + 1; j < stars.length; j++) {
                const dx = stars[i].x - stars[j].x;
                const dy = stars[i].y - stars[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < CONSTELLATION_DIST) {
                    const alpha = (1 - dist / CONSTELLATION_DIST) * 0.12;
                    ctx.strokeStyle = `rgba(201,168,76,${alpha})`;
                    ctx.beginPath();
                    ctx.moveTo(stars[i].x, stars[i].y);
                    ctx.lineTo(stars[j].x, stars[j].y);
                    ctx.stroke();
                }
            }
        }

        // draw stars
        for (const s of stars) {
            s.x += s.vx;
            s.y += s.vy;
            s.phase += s.speed;

            // wrap around
            if (s.x < -10) s.x = w + 10;
            if (s.x > w + 10) s.x = -10;
            if (s.y < -10) s.y = h + 10;
            if (s.y > h + 10) s.y = -10;

            const flicker = Math.sin(s.phase) * 0.3 + 0.7;
            const alpha = s.brightness * flicker;
            const radius = s.r * (0.85 + flicker * 0.15);

            // glow
            if (radius > 1) {
                const grad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, radius * 4);
                grad.addColorStop(0, `rgba(232,220,196,${alpha * 0.15})`);
                grad.addColorStop(1, 'transparent');
                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(s.x, s.y, radius * 4, 0, Math.PI * 2);
                ctx.fill();
            }

            // core
            ctx.fillStyle = `rgba(232,220,196,${alpha})`;
            ctx.beginPath();
            ctx.arc(s.x, s.y, radius, 0, Math.PI * 2);
            ctx.fill();
        }

        requestAnimationFrame(draw);
    }

    resize();
    createStars();
    requestAnimationFrame(draw);

    window.addEventListener('resize', () => {
        resize();
        createStars();
    });
}

// ── Landing & Theme ────────────────────────────────────
function initLanding() {
    const landing = DOM.landingPage();
    const start = DOM.landingStart();
    if (!landing || !start) return;

    document.body.classList.toggle('landing-active', !landing.classList.contains('is-hidden'));
    start.addEventListener('click', hideLandingPage);
}

function resetPageScroll() {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
}

function hideLandingPage() {
    const landing = DOM.landingPage();
    if (!landing) return;
    resetPageScroll();
    landing.classList.remove('is-visible');
    landing.classList.add('is-hiding');
    landing.setAttribute('aria-hidden', 'true');
    window.setTimeout(() => {
        resetPageScroll();
        landing.classList.add('is-hidden');
        document.body.classList.remove('landing-active');
        DOM.mainContent()?.focus({preventScroll: true});
    }, 520);
}

function showLandingPage() {
    const landing = DOM.landingPage();
    if (!landing) return;
    resetPageScroll();
    landing.scrollTo(0, 0);
    document.body.classList.add('landing-active');
    landing.classList.remove('is-hidden', 'is-hiding');
    landing.classList.add('is-visible');
    landing.setAttribute('aria-hidden', 'false');
    clearActiveNpcView();
    window.setTimeout(() => landing.classList.remove('is-visible'), 20);
}

function initTheme() {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    const saved = readStorage(STORAGE_KEYS.theme, null);
    const initial = saved || (media?.matches ? 'dark' : 'light');
    applyTheme(initial);
    DOM.themeToggle()?.addEventListener('click', () => {
        const current = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next);
        writeStorage(STORAGE_KEYS.theme, next);
        DOM.themeToggle()?.classList.add('is-switching');
        window.setTimeout(() => DOM.themeToggle()?.classList.remove('is-switching'), 360);
    });
    media?.addEventListener?.('change', (e) => {
        if (!readStorage(STORAGE_KEYS.theme, null)) {
            applyTheme(e.matches ? 'dark' : 'light');
        }
    });
}

function applyTheme(theme) {
    const normalized = theme === 'light' ? 'light' : 'dark';
    if (normalized === 'light') {
        document.documentElement.dataset.theme = 'light';
    } else {
        document.documentElement.removeAttribute('data-theme');
    }
    const toggle = DOM.themeToggle();
    const icon = DOM.themeIcon();
    if (icon) icon.innerHTML = normalized === 'dark' ? getSunIconSvg() : getMoonIconSvg();
    if (toggle) toggle.setAttribute('aria-label', normalized === 'dark' ? '切换浅色模式' : '切换深色模式');
}

function getSunIconSvg() {
    return '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"></path></svg>';
}

function getMoonIconSvg() {
    return '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z"></path></svg>';
}

// ── Persistence ────────────────────────────────────────
function readStorage(key, fallback) {
    try {
        const value = localStorage.getItem(key);
        return value ? JSON.parse(value) : fallback;
    } catch (e) {
        return fallback;
    }
}

function writeStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        showToast('本地状态暂时无法保存', 'error');
    }
}

function removeStorage(key) {
    try {
        localStorage.removeItem(key);
    } catch (e) {
        showToast('本地状态暂时无法更新', 'error');
    }
}

function loadPersistedState() {
    const messages = readStorage(STORAGE_KEYS.chatHistory, {});
    state.messages = normalizeStoredMessages(messages);
    Object.keys(state.messages).forEach(id => {
        state.renderedCount[id] = state.messages[id].length;
    });
}

function normalizeStoredMessages(raw) {
    if (!raw || typeof raw !== 'object') return {};
    return Object.entries(raw).reduce((acc, [npcId, messages]) => {
        if (!Array.isArray(messages)) return acc;
        acc[npcId] = messages
            .filter(msg => msg && typeof msg.content === 'string' && typeof msg.role === 'string')
            .map(msg => ({
                role: msg.role,
                content: msg.content,
                time: msg.time || null,
            }));
        return acc;
    }, {});
}

function saveMessages() {
    writeStorage(STORAGE_KEYS.chatHistory, state.messages);
}

function getSavedAffinity() {
    return readStorage(STORAGE_KEYS.affinity, {});
}

function saveAffinityFromNpcs() {
    const affinityByNpc = {};
    state.npcs.forEach(npc => {
        if (npc?.id && npc?.affinity) affinityByNpc[npc.id] = npc.affinity;
    });
    writeStorage(STORAGE_KEYS.affinity, affinityByNpc);
}

function mergeSavedAffinity(npcs) {
    const saved = getSavedAffinity();
    return npcs.map(npc => ({
        ...npc,
        affinity: saved[npc.id] || npc.affinity,
    }));
}

// ══════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════
async function init() {
    initCosmos();
    initTheme();
    initLanding();
    loadPersistedState();
    bindEvents();
    renderNpcSkeleton();
    updateCharCounter();
    await loadNpcList({restoreSelection: true});
}

async function loadNpcList(options = {}) {
    const {restoreSelection = false, preferredNpcId = null} = options;
    renderNpcSkeleton();
    try {
        const data = await API.fetchNpcs();
        if (data.success) {
            state.npcs = mergeSavedAffinity(data.npcs);
            renderNpcList();
            saveAffinityFromNpcs();
            const targetNpc = preferredNpcId || (restoreSelection ? readStorage(STORAGE_KEYS.currentNpc, null) : state.currentNpc);
            if (targetNpc && state.npcs.some(npc => npc.id === targetNpc)) {
                await selectNpc(targetNpc);
            } else if (state.currentNpc && !state.npcs.some(npc => npc.id === state.currentNpc)) {
                clearActiveNpcView();
            }
        } else {
            renderNpcLoadError();
            showToast('学院人物暂时无法加载', 'error');
        }
    } catch (e) {
        renderNpcLoadError();
        showToast('学院人物暂时无法加载', 'error');
    }
}

function bindEvents() {
    DOM.sendBtn().addEventListener('click', sendMessage);
    DOM.messageInput().addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    DOM.messageInput().addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        updateCharCounter();
    });
    DOM.clearChatBtn().addEventListener('click', clearCurrentChat);
    DOM.resetBtn().addEventListener('click', resetCurrentNpc);
    DOM.newSessionBtn().addEventListener('click', startNewSession);
    DOM.mobileToggle().addEventListener('click', toggleMobilePanel);
    DOM.mobileOverlay().addEventListener('click', closeMobilePanel);
    DOM.backToLanding().addEventListener('click', showLandingPage);
    DOM.settingsToggle().addEventListener('click', openSettingsModal);
    DOM.settingsClose().addEventListener('click', closeSettingsModal);
    DOM.settingsModal().addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeSettingsModal();
    });
    DOM.settingProvider().addEventListener('change', applyProviderPreset);
    DOM.settingTemp().addEventListener('input', () => {
        DOM.settingTempValue().textContent = DOM.settingTemp().value;
    });
    DOM.toggleApiKey().addEventListener('click', toggleApiKeyVisibility);
    DOM.saveSettingsBtn().addEventListener('click', handleSaveSettings);
    DOM.resetSettingsBtn().addEventListener('click', handleResetSettings);
    DOM.settingsGoHome().addEventListener('click', handleSettingsGoHome);
    DOM.testApiBtn().addEventListener('click', handleTestConnection);
    DOM.createNpcBtn().addEventListener('click', openCreateNpcModal);
    DOM.createNpcClose().addEventListener('click', closeCreateNpcModal);
    DOM.cancelCreateNpc().addEventListener('click', closeCreateNpcModal);
    DOM.createNpcModal().addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeCreateNpcModal();
    });
    $$('.avatar-option').forEach(btn => btn.addEventListener('click', () => selectAvatar(btn)));
    DOM.npcAvatarCustom().addEventListener('input', handleCustomAvatarInput);
    DOM.avatarUploadTrigger().addEventListener('click', () => DOM.avatarFileInput().click());
    DOM.avatarFileInput().addEventListener('change', handleAvatarFileChange);
    DOM.avatarRemove().addEventListener('click', resetUploadedAvatar);
    DOM.confirmCreateNpc().addEventListener('click', handleCreateNpc);
    DOM.confirmClose().addEventListener('click', () => resolveConfirm(false));
    DOM.confirmCancel().addEventListener('click', () => resolveConfirm(false));
    DOM.confirmOk().addEventListener('click', () => resolveConfirm(true));
    DOM.confirmModal().addEventListener('click', (e) => {
        if (e.target === e.currentTarget) resolveConfirm(false);
    });
    DOM.chatMenuBtn().addEventListener('click', toggleChatMenu);
    DOM.clearChatBtnAlt().addEventListener('click', () => { closeChatMenu(); clearCurrentChat(); });
    DOM.resetBtnAlt().addEventListener('click', () => { closeChatMenu(); resetCurrentNpc(); });
    DOM.newSessionBtnAlt().addEventListener('click', () => { closeChatMenu(); startNewSession(); });
    DOM.messagesArea().addEventListener('scroll', handleMessagesScroll);
    DOM.scrollBottomBtn().addEventListener('click', scrollToBottomFromButton);
    document.addEventListener('click', handleDocumentClick);
    document.addEventListener('keydown', handleGlobalKeydown);
}

function handleGlobalKeydown(e) {
    if (e.key !== 'Escape') return;
    if (!DOM.confirmModal().hidden) {
        resolveConfirm(false);
    } else if (!DOM.createNpcModal().hidden) {
        closeCreateNpcModal();
    } else if (!DOM.settingsModal().hidden) {
        closeSettingsModal();
    } else if (!DOM.chatMenuDropdown().hidden) {
        closeChatMenu();
    }
}

function handleDocumentClick(e) {
    const btn = DOM.chatMenuBtn();
    const menu = DOM.chatMenuDropdown();
    if (!btn || !menu || menu.hidden) return;
    if (btn.contains(e.target) || menu.contains(e.target)) return;
    closeChatMenu();
}

function toggleChatMenu(e) {
    e.stopPropagation();
    const menu = DOM.chatMenuDropdown();
    const nextHidden = !menu.hidden;
    menu.hidden = nextHidden;
    DOM.chatMenuBtn().setAttribute('aria-expanded', nextHidden ? 'false' : 'true');
}

function closeChatMenu() {
    const menu = DOM.chatMenuDropdown();
    if (!menu) return;
    menu.hidden = true;
    DOM.chatMenuBtn()?.setAttribute('aria-expanded', 'false');
}

function setActionButtonsDisabled(disabled) {
    [
        DOM.clearChatBtn(),
        DOM.resetBtn(),
        DOM.newSessionBtn(),
        DOM.clearChatBtnAlt(),
        DOM.resetBtnAlt(),
        DOM.newSessionBtnAlt(),
    ].forEach(btn => {
        if (btn) btn.disabled = disabled;
    });
    if (DOM.chatMenuBtn()) {
        DOM.chatMenuBtn().hidden = disabled;
    }
    if (disabled) closeChatMenu();
}

function trapFocus(modalElement, initialFocusElement = null) {
    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

    function getFocusableElements() {
        return Array.from(modalElement.querySelectorAll(focusableSelector))
            .filter(el => !el.disabled && !el.hidden && el.offsetParent !== null);
    }

    function handleTab(e) {
        if (e.key !== 'Tab') return;
        const focusable = getFocusableElements();
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
        }
    }

    modalElement.addEventListener('keydown', handleTab);
    const focusTarget = initialFocusElement || getFocusableElements()[0];
    focusTarget?.focus();
    return () => modalElement.removeEventListener('keydown', handleTab);
}

function openManagedModal(modalElement, initialFocusElement = null) {
    state.focusTrapCleanup?.();
    state.lastFocusedElement = document.activeElement;
    modalElement.hidden = false;
    state.focusTrapCleanup = trapFocus(modalElement, initialFocusElement);
}

function closeManagedModal(modalElement, {restoreFocus = true} = {}) {
    state.focusTrapCleanup?.();
    state.focusTrapCleanup = null;
    modalElement.hidden = true;
    if (restoreFocus && state.lastFocusedElement && typeof state.lastFocusedElement.focus === 'function') {
        state.lastFocusedElement.focus();
    }
    state.lastFocusedElement = null;
}

// ── API Settings ───────────────────────────────────────
function loadSettings() {
    const saved = readStorage(STORAGE_KEYS.settings, {});
    return {...DEFAULT_SETTINGS, ...saved};
}

function saveSettings(settings) {
    writeStorage(STORAGE_KEYS.settings, settings);
}

function populateSettingsForm(settings = loadSettings()) {
    DOM.settingProvider().value = PROVIDERS[settings.provider] ? settings.provider : DEFAULT_SETTINGS.provider;
    DOM.settingBaseUrl().value = settings.base_url;
    DOM.settingApiKey().value = settings.api_key;
    DOM.settingModel().value = settings.model;
    DOM.settingTemp().value = settings.temperature;
    DOM.settingTempValue().textContent = settings.temperature;
    DOM.settingMaxTokens().value = settings.max_tokens;
    DOM.testApiResult().textContent = '';
    updateProviderHelp();
}

function collectSettingsFromForm() {
    const temperature = parseFloat(DOM.settingTemp().value);
    const maxTokens = parseInt(DOM.settingMaxTokens().value, 10);
    return {
        provider: DOM.settingProvider().value,
        base_url: DOM.settingBaseUrl().value.trim(),
        api_key: DOM.settingApiKey().value.trim(),
        model: DOM.settingModel().value.trim(),
        temperature: Number.isFinite(temperature) ? temperature : DEFAULT_SETTINGS.temperature,
        max_tokens: Number.isFinite(maxTokens) ? maxTokens : DEFAULT_SETTINGS.max_tokens,
    };
}

function openSettingsModal() {
    populateSettingsForm();
    openManagedModal(DOM.settingsModal(), DOM.settingProvider());
}

function closeSettingsModal() {
    closeManagedModal(DOM.settingsModal());
}

function applyProviderPreset(e) {
    const provider = PROVIDERS[e.target.value] || PROVIDERS.mock;
    DOM.settingBaseUrl().value = provider.base_url;
    DOM.settingModel().value = provider.models[0] || '';
    updateProviderHelp();
}

function updateProviderHelp() {
    const providerId = DOM.settingProvider().value;
    const provider = PROVIDERS[providerId];
    const helpEl = DOM.providerHelp();
    if (!provider || !helpEl) return;

    if (!provider.registration_url) {
        helpEl.classList.toggle('is-mock', providerId === 'mock');
        helpEl.textContent = providerId === 'mock'
            ? '无需 API，直接体验 UI 功能'
            : '请自行填写 API 地址和密钥';
        return;
    }

    helpEl.classList.remove('is-mock');
    helpEl.innerHTML = `
        <a href="${provider.registration_url}" target="_blank" rel="noopener">前往 ${provider.label} 官网注册 ↗</a>
        ${provider.docs_url ? ` · <a href="${provider.docs_url}" target="_blank" rel="noopener">查看文档 ↗</a>` : ''}
    `;
}

function toggleApiKeyVisibility() {
    const input = DOM.settingApiKey();
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    DOM.toggleApiKey().setAttribute('aria-label', show ? '隐藏密钥' : '显示密钥');
}

function handleSaveSettings() {
    const settings = collectSettingsFromForm();
    saveSettings(settings);
    closeSettingsModal();
    showToast('设置已保存', 'success');
}

function handleResetSettings() {
    removeStorage(STORAGE_KEYS.settings);
    populateSettingsForm({...DEFAULT_SETTINGS});
    showToast('已恢复默认设置', 'info');
}

function handleSettingsGoHome() {
    closeSettingsModal();
    showLandingPage();
}

async function handleTestConnection() {
    const result = DOM.testApiResult();
    const settings = collectSettingsFromForm();
    result.textContent = '测试中...';
    result.className = 'test-api-result';
    DOM.testApiBtn().disabled = true;
    try {
        const data = await API.testConnection(settings);
        if (data.ok) {
            result.textContent = settings.provider === 'mock' ? 'Mock 模式可用' : '连接成功';
            result.classList.add('success');
        } else {
            result.textContent = data.error || '连接失败';
            result.classList.add('error');
        }
    } catch (e) {
        result.textContent = e.message || '网络错误';
        result.classList.add('error');
    } finally {
        DOM.testApiBtn().disabled = false;
    }
}

// ── Mobile Panel ───────────────────────────────────────
function toggleMobilePanel() {
    const p = DOM.npcPanel(), o = DOM.mobileOverlay();
    if (p.classList.contains('open')) { closeMobilePanel(); }
    else {
        p.classList.add('open');
        o.classList.add('show');
        DOM.mobileToggle()?.setAttribute('aria-expanded', 'true');
    }
}
function closeMobilePanel() {
    DOM.npcPanel().classList.remove('open');
    DOM.mobileOverlay().classList.remove('show');
    DOM.mobileToggle()?.setAttribute('aria-expanded', 'false');
}

// ── NPC List ───────────────────────────────────────────
function renderNpcSkeleton() {
    const list = DOM.npcList();
    if (!list) return;
    list.innerHTML = Array.from({length: 3}).map(() => `
        <div class="npc-skeleton" aria-hidden="true">
            <span></span><div><b></b><i></i></div><em></em>
        </div>
    `).join('');
}

function renderNpcLoadError() {
    const list = DOM.npcList();
    if (!list) return;
    list.innerHTML = '<p class="empty-hint npc-load-error">人物名单被星雾遮住了，请稍后再试</p>';
}

function getNpcById(npcId) {
    return state.npcs.find(npc => npc.id === npcId);
}

function isImageAvatar(avatar) {
    return typeof avatar === 'string' && (avatar.startsWith('/static/') || avatar.startsWith('data:image/'));
}

function getAvatarHtml(npc) {
    if (npc?.is_custom) {
        if (isImageAvatar(npc.avatar)) {
            return `<img class="npc-uploaded-avatar" src="${esc(npc.avatar)}" alt="">`;
        }
        return `<span class="npc-avatar-emoji">${esc(npc.avatar || '✨')}</span>`;
    }
    return `<div class="npc-avatar-img" data-npc="${esc(npc?.id || '')}"></div>`;
}

function renderNpcList() {
    const list = DOM.npcList();
    list.innerHTML = '';
    state.npcs.forEach((npc, idx) => {
        const card = document.createElement('div');
        card.className = `npc-card${state.currentNpc === npc.id ? ' active' : ''}`;
        card.dataset.npc = npc.id;
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.setAttribute('aria-label', `选择 ${npc.name}`);
        card.setAttribute('aria-pressed', state.currentNpc === npc.id ? 'true' : 'false');
        const tier = npc.affinity.tier;
        const val = npc.affinity.value;
        const tc = TIER_COLORS[tier] || TIER_COLORS.neutral;

        card.innerHTML = `
            ${npc.is_custom ? `<button class="npc-delete-btn" type="button" data-id="${esc(npc.id)}" aria-label="删除 ${esc(npc.name)}">×</button>` : ''}
            <div class="npc-card-header">
                <div class="npc-card-avatar">${getAvatarHtml(npc)}</div>
                <div class="npc-card-info">
                    <h4>${esc(npc.name)}</h4>
                    <span class="npc-role">${esc(npc.title)}</span>
                </div>
            </div>
            <p class="npc-card-desc">${esc(npc.description)}</p>
            <div class="npc-card-affinity">
                <span class="mini-heart" style="color:${tc.end}">&#9829;</span>
                <div class="mini-affinity-bar">
                    <div class="mini-affinity-fill mini-fill-${tier}" style="width:${val}%"></div>
                </div>
                <span class="mini-affinity-label">${val}</span>
            </div>`;

        // staggered entry animation
        card.style.animation = `msg-rise 0.4s var(--ease-out) ${idx * 0.08}s both`;

        card.addEventListener('click', () => selectNpc(npc.id));
        const deleteBtn = card.querySelector('.npc-delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                handleDeleteNpc(npc);
            });
        }
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectNpc(npc.id);
            }
        });
        list.appendChild(card);
    });
}

// ── Select NPC ─────────────────────────────────────────
async function selectNpc(npcId) {
    const prev = state.currentNpc;
    state.currentNpc = npcId;
    writeStorage(STORAGE_KEYS.currentNpc, npcId);
    closeMobilePanel();

    $$('.npc-card').forEach(c => {
        const active = c.dataset.npc === npcId;
        c.classList.toggle('active', active);
        c.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    const npc = getNpcById(npcId);
    if (!npc) return;

    DOM.chatPanel().setAttribute('data-npc-theme', npcId);

    if (prev && prev !== npcId) {
        const c = DOM.chatContainer();
        c.style.animation = 'none'; c.offsetHeight;
        c.style.animation = 'slide-down 0.4s var(--ease-out)';
    }

    DOM.welcomeScreen().style.display = 'none';
    DOM.chatContainer().style.display = 'flex';

    DOM.chatAvatarRing().setAttribute('data-npc', npcId);
    DOM.chatAvatar().innerHTML = getAvatarHtml(npc);
    DOM.chatName().textContent = npc.name;
    DOM.chatTitle().textContent = npc.title;
    updateAffinityDisplay(npc.affinity);

    if (!Array.isArray(state.messages[npcId])) {
        state.messages[npcId] = [];
        state.renderedCount[npcId] = 0;
    }

    if (state.messages[npcId].length === 0) {
        renderChatWelcome(npc);
    } else {
        renderAllMessages(npcId);
    }

    updateMemoryPanel(npc.memory);
    updateSuggestedResponses(npc.suggested_responses);
    setActionButtonsDisabled(false);
    syncSendState();
    scrollToBottom();
}

function clearActiveNpcView() {
    state.currentNpc = null;
    removeStorage(STORAGE_KEYS.currentNpc);
    $$('.npc-card').forEach(c => {
        c.classList.remove('active');
        c.setAttribute('aria-pressed', 'false');
    });
    DOM.chatPanel().removeAttribute('data-npc-theme');
    DOM.chatContainer().style.display = 'none';
    DOM.welcomeScreen().style.display = '';
    hideScrollBottomBadge();
    DOM.memoryInfo().innerHTML = '<p class="empty-hint">选择一个 NPC 查看记忆状态</p>';
    DOM.affinityLog().innerHTML = '<p class="empty-hint">对话后将显示好感度变化</p>';
    DOM.suggestedResps().innerHTML = '';
    DOM.messageInput().value = '';
    updateCharCounter();
    setActionButtonsDisabled(true);
}

// ── Affinity ───────────────────────────────────────────
function updateAffinityDisplay(aff) {
    const tier = aff.tier;
    const colors = TIER_COLORS[tier] || TIER_COLORS.neutral;

    DOM.affinityLabel().textContent = aff.tier_label;
    DOM.affinityValue().textContent = `${aff.value}/100`;

    const fill = DOM.affinityFill();
    fill.style.width = `${aff.value}%`;
    fill.className = `affinity-fill tier-${tier}`;

    // shimmer position follows fill
    const shimmer = DOM.affinityShimmer();
    if (shimmer) shimmer.style.left = `calc(${aff.value}% - 15px)`;

    const s = DOM.heartGradStart(), e = DOM.heartGradEnd();
    if (s && e) { s.setAttribute('stop-color', colors.start); e.setAttribute('stop-color', colors.end); }
}

function triggerHeartBeat() {
    const h = DOM.affinityHeart();
    if (!h) return;
    h.classList.remove('beat'); h.offsetHeight; h.classList.add('beat');
}

// ── Messages ───────────────────────────────────────────
function renderChatWelcome(npc) {
    const area = DOM.messagesArea();
    area.innerHTML = '';
    hideScrollBottomBadge();
    const welcome = document.createElement('div');
    welcome.className = 'chat-welcome-state';
    welcome.id = 'chatWelcomeState';
    welcome.innerHTML = `
        <div class="cw-avatar${npc.is_custom ? ' custom-avatar' : ''}" data-npc="${esc(npc.id)}">${npc.is_custom ? getAvatarHtml(npc) : ''}</div>
        <div class="cw-divider"></div>
        <h2 class="cw-name">${esc(npc.name)}</h2>
        <span class="cw-title">${esc(npc.title)}</span>
        <p class="cw-desc">${esc(npc.description)}</p>
        <p class="cw-hint">在下方输入框开始对话</p>`;
    area.appendChild(welcome);
}

function appendMessage(msg, options = {}) {
    const id = state.currentNpc;
    if (!id) return;
    const shouldAutoScroll = options.forceScroll || isUserNearBottom();
    state.messages[id].push(msg);
    // Remove welcome state on first message
    const ws = document.getElementById('chatWelcomeState');
    if (ws) ws.remove();
    DOM.messagesArea().appendChild(createMsgEl(msg, true));
    state.renderedCount[id] = state.messages[id].length;
    saveMessages();
    handleNewMessageScroll(shouldAutoScroll);
}

function renderAllMessages(npcId) {
    const area = DOM.messagesArea();
    area.innerHTML = '';
    (state.messages[npcId] || []).forEach(m => area.appendChild(createMsgEl(m, false)));
    state.renderedCount[npcId] = (state.messages[npcId] || []).length;
    scrollToBottom();
}

function createMsgEl(msg, animate) {
    const el = document.createElement('div');
    el.className = `message ${msg.role}${animate ? ' msg-enter' : ''}`;
    const msgTime = msg.time instanceof Date ? msg.time : (msg.time ? new Date(msg.time) : null);
    const ts = msgTime && !Number.isNaN(msgTime.getTime())
        ? msgTime.toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'}) : '';

    if (msg.role === 'system') {
        el.innerHTML = `<div class="message-bubble">${esc(msg.content)}</div>`;
    } else {
        const npc = getNpcById(state.currentNpc);
        const avatarHtml = msg.role === 'npc'
            ? getAvatarHtml(npc)
            : '&#129497;';
        el.innerHTML = `
            <div class="message-avatar" data-npc="${esc(state.currentNpc || '')}">${avatarHtml}</div>
            <div>
                <div class="message-bubble">${fmtMsg(msg.content)}</div>
                <div class="message-time">${ts}</div>
            </div>`;
    }
    return el;
}

function createStreamingNpcMessage() {
    const ws = document.getElementById('chatWelcomeState');
    if (ws) ws.remove();

    const msg = {role:'npc', content:'', time:new Date()};
    const el = createMsgEl(msg, true);
    DOM.messagesArea().appendChild(el);
    const bubble = el.querySelector('.message-bubble');
    return {el, bubble, msg};
}

function updateStreamingNpcMessage(streamMessage, content) {
    streamMessage.msg.content = content;
    streamMessage.bubble.innerHTML = fmtMsg(content || '…');
}

function finalizeStreamingNpcMessage(streamMessage, content) {
    const id = state.currentNpc;
    if (!id) return;
    streamMessage.msg.content = content;
    streamMessage.msg.time = new Date();
    updateStreamingNpcMessage(streamMessage, content);
    state.messages[id].push(streamMessage.msg);
    state.renderedCount[id] = state.messages[id].length;
    saveMessages();
}

function showTyping() {
    const area = DOM.messagesArea();
    const npcId = state.currentNpc;
    const npc = getNpcById(npcId);
    const el = document.createElement('div');
    el.className = 'message npc msg-enter';
    el.id = 'typingIndicator';
    el.innerHTML = `
        <div class="message-avatar" data-npc="${esc(npcId || '')}">${getAvatarHtml(npc)}</div>
        <div><div class="message-bubble">
            <div class="typing-indicator">
                <span class="typing-text">正在思考</span>
                <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
            </div>
        </div></div>`;
    area.appendChild(el); scrollToBottom();
}

function removeTyping() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

// ── Send ───────────────────────────────────────────────
function updateCharCounter() {
    const input = DOM.messageInput();
    const counter = DOM.charCounter();
    if (!input || !counter) return;
    const count = input.value.length;
    counter.textContent = `${count}/${MAX_MESSAGE_LENGTH}`;
    counter.classList.toggle('is-warning', count >= WARNING_MESSAGE_LENGTH && count < MAX_MESSAGE_LENGTH);
    counter.classList.toggle('is-limit', count >= MAX_MESSAGE_LENGTH);
    syncSendState();
}

function syncSendState() {
    const input = DOM.messageInput();
    const btn = DOM.sendBtn();
    if (!input || !btn) return;
    const count = input.value.length;
    btn.disabled = state.isLoading || !state.currentNpc || !input.value.trim() || count >= MAX_MESSAGE_LENGTH;
    btn.classList.toggle('is-loading', state.isLoading);
}

async function sendMessage() {
    const inp = DOM.messageInput();
    const msg = inp.value.trim();
    if (!msg || !state.currentNpc || state.isLoading) return;
    if (inp.value.length >= MAX_MESSAGE_LENGTH) {
        showToast('消息已到 500 字上限，请缩短后再发送', 'error');
        syncSendState();
        return;
    }

    inp.value = ''; inp.style.height = 'auto';
    updateCharCounter();
    appendMessage({role:'player', content:msg, time:new Date()}, {forceScroll:true});

    state.isLoading = true;
    syncSendState();
    showTyping();

    const activeNpcId = state.currentNpc;
    let streamMessage = null;
    let fullText = '';
    let badgeShownForStream = false;

    try {
        await ensureSessionStarted(activeNpcId);
        await API.chatStream(activeNpcId, msg, {
            onStatus(message) {
                const typingText = document.querySelector('#typingIndicator .typing-text');
                if (typingText && message) typingText.textContent = message;
            },
            onToken(token) {
                if (!streamMessage) {
                    removeTyping();
                    streamMessage = createStreamingNpcMessage();
                }
                fullText += token;
                updateStreamingNpcMessage(streamMessage, fullText);
                if (isUserNearBottom()) {
                    scrollToBottom();
                } else if (!badgeShownForStream) {
                    showScrollBottomBadge();
                    badgeShownForStream = true;
                }
            },
            onDone(data) {
                removeTyping();
                if (!streamMessage) streamMessage = createStreamingNpcMessage();
                const finalText = data.full_content || fullText || '……';
                finalizeStreamingNpcMessage(streamMessage, finalText);

                const oldTier = state.npcs.find(n => n.id === activeNpcId)?.affinity?.tier;
                updateAffinityDisplay(data.affinity);
                if (oldTier !== data.affinity?.tier || data.affinity_change?.delta !== 0) triggerHeartBeat();

                const npcInList = state.npcs.find(n => n.id === activeNpcId);
                if (npcInList) {
                    npcInList.affinity = data.affinity;
                    npcInList.memory = data.memory_summary;
                    renderNpcList();
                }
                saveAffinityFromNpcs();
                if (data.affinity_change) addAffinityLog(data.affinity_change);
                if (data.memory_summary) updateMemoryPanel(data.memory_summary);
            },
            onError(message) {
                throw new Error(message || '网络波动，请稍后再试');
            },
        });
    } catch (e) {
        removeTyping();
        if (streamMessage && !fullText) streamMessage.el.remove();
        showToast(e.status === 429 ? e.message : '网络波动，请稍后再试', 'error');
    } finally {
        state.isLoading = false;
        syncSendState();
    }
}

async function ensureSessionStarted(npcId) {
    if (!npcId || state.startedSessions[npcId]) return;
    try {
        const res = await API.startSession(npcId);
        state.startedSessions[npcId] = true;
        if (res?.npc) {
            const npcInList = state.npcs.find(n => n.id === npcId);
            if (npcInList) npcInList.memory = res.npc.memory;
        }
    } catch (e) {
        // 会话计数失败不阻断对话，后续 chat API 仍可独立工作。
    }
}

// ── Suggestions ────────────────────────────────────────
function updateSuggestedResponses(sugs) {
    const c = DOM.suggestedResps(); c.innerHTML = '';
    if (!sugs || !sugs.length) return;
    sugs.forEach(s => {
        const b = document.createElement('button');
        b.className = 'suggestion-btn';
        b.type = 'button';
        b.innerHTML = `${esc(s.text)} <span class="effect-tag">${s.effect}</span>`;
        b.addEventListener('click', () => {
            const input = DOM.messageInput();
            input.value = s.text;
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 100) + 'px';
            updateCharCounter();
            sendMessage();
        });
        c.appendChild(b);
    });
}

// ── Side Panels ────────────────────────────────────────
function updateMemoryPanel(mem) {
    const p = DOM.memoryInfo();
    if (!mem) { p.innerHTML = '<p class="empty-hint">暂无记忆数据</p>'; return; }
    p.innerHTML = `
        <div class="info-row"><span>对话轮数</span><span class="info-value">${mem.conversation_turns||0}</span></div>
        <div class="info-row"><span>会话次数</span><span class="info-value">${mem.session_count||0}</span></div>
        <div class="info-row"><span>记住的事实</span><span class="info-value">${mem.facts_count||0}</span></div>
        <div class="info-row"><span>总交互数</span><span class="info-value">${mem.total_interactions||0}</span></div>`;
}

function addAffinityLog(ch) {
    const log = DOM.affinityLog();
    const hint = log.querySelector('.empty-hint'); if (hint) hint.remove();
    const d = ch.delta;
    const cls = d > 0 ? 'delta-positive' : d < 0 ? 'delta-negative' : 'delta-neutral';
    const txt = d > 0 ? `+${d}` : `${d}`;
    const el = document.createElement('div');
    el.className = 'log-entry';
    el.innerHTML = `<span class="${cls}">${txt}</span><span style="margin-left:6px">${esc(ch.reason)}</span>`;
    log.insertBefore(el, log.firstChild);
    while (log.children.length > 10) log.removeChild(log.lastChild);
}

// ── Actions ────────────────────────────────────────────
function openCreateNpcModal() {
    resetCreateNpcForm();
    openManagedModal(DOM.createNpcModal(), DOM.npcName());
}

function closeCreateNpcModal() {
    closeManagedModal(DOM.createNpcModal());
    resetCreateNpcForm();
}

function resetCreateNpcForm() {
    DOM.npcName().value = '';
    DOM.npcTitle().value = '';
    DOM.npcAvatarCustom().value = '';
    DOM.npcPersonality().value = '';
    DOM.npcBackstory().value = '';
    DOM.npcSpeechStyle().value = '';
    state.selectedAvatar = '⚔️';
    $$('.avatar-option').forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.emoji === state.selectedAvatar);
    });
    resetUploadedAvatar();
}

function selectAvatar(btn) {
    state.selectedAvatar = btn.dataset.emoji || '✨';
    DOM.npcAvatarCustom().value = '';
    resetUploadedAvatar();
    $$('.avatar-option').forEach(option => option.classList.toggle('selected', option === btn));
}

function handleCustomAvatarInput(e) {
    if (!e.target.value.trim()) return;
    state.selectedAvatar = e.target.value.trim();
    resetUploadedAvatar();
    $$('.avatar-option').forEach(option => option.classList.remove('selected'));
}

function resetUploadedAvatar() {
    state.uploadedAvatarData = null;
    DOM.avatarPreviewImg().src = '';
    DOM.avatarPreview().hidden = true;
    DOM.avatarUploadTrigger().hidden = false;
    DOM.avatarFileInput().value = '';
}

function handleAvatarFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
        showToast('头像仅支持 JPG、PNG、WEBP、GIF', 'error');
        DOM.avatarFileInput().value = '';
        return;
    }

    if (file.size > MAX_AVATAR_UPLOAD_BYTES) {
        showToast('头像图片不能超过 2MB', 'error');
        DOM.avatarFileInput().value = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
        state.uploadedAvatarData = ev.target?.result || null;
        if (!state.uploadedAvatarData) {
            showToast('头像读取失败，请重新选择', 'error');
            return;
        }
        DOM.avatarPreviewImg().src = state.uploadedAvatarData;
        DOM.avatarPreview().hidden = false;
        DOM.avatarUploadTrigger().hidden = true;
        DOM.npcAvatarCustom().value = '';
        state.selectedAvatar = null;
        $$('.avatar-option').forEach(option => option.classList.remove('selected'));
    };
    reader.onerror = () => showToast('头像读取失败，请重新选择', 'error');
    reader.readAsDataURL(file);
}

async function handleCreateNpc() {
    const payload = {
        name: DOM.npcName().value.trim(),
        title: DOM.npcTitle().value.trim(),
        avatar: state.uploadedAvatarData || DOM.npcAvatarCustom().value.trim() || state.selectedAvatar || '✨',
        personality: DOM.npcPersonality().value.trim(),
        backstory: DOM.npcBackstory().value.trim(),
        speech_style: DOM.npcSpeechStyle().value.trim(),
    };

    if (!payload.name) { showToast('请输入角色名称', 'error'); return; }
    if (!payload.personality) { showToast('请输入性格描述', 'error'); return; }

    DOM.confirmCreateNpc().disabled = true;
    try {
        const data = await API.createNpc(payload);
        if (data.ok) {
            closeCreateNpcModal();
            showToast('角色创建成功', 'success');
            await loadNpcList({preferredNpcId: data.npc_id});
        } else {
            showToast(data.error || '创建失败', 'error');
        }
    } catch (e) {
        showToast(e.status === 429 ? e.message : '创建失败，请稍后再试', 'error');
    } finally {
        DOM.confirmCreateNpc().disabled = false;
    }
}

async function handleDeleteNpc(npc) {
    const ok = await showConfirm({
        title: '删除角色',
        message: `确定删除「${npc.name}」吗？这会移除该自定义角色和它的本地记忆。`,
        confirmText: '删除',
        danger: true,
    });
    if (!ok) return;

    try {
        const data = await API.deleteNpc(npc.id);
        if (data.ok) {
            delete state.messages[npc.id];
            delete state.startedSessions[npc.id];
            saveMessages();
            showToast('角色已删除', 'success');
            await loadNpcList();
        } else {
            showToast(data.error || '删除失败', 'error');
        }
    } catch (e) {
        showToast(e.status === 429 ? e.message : '删除失败，请稍后再试', 'error');
    }
}

function clearCurrentChat() {
    if (!state.currentNpc) return;
    state.messages[state.currentNpc] = [];
    state.renderedCount[state.currentNpc] = 0;
    saveMessages();
    const npc = state.npcs.find(n => n.id === state.currentNpc);
    if (npc) renderChatWelcome(npc);
    DOM.affinityLog().innerHTML = '<p class="empty-hint">对话后将显示好感度变化</p>';
    hideScrollBottomBadge();
    showToast('本地对话已清除', 'success');
}

async function resetCurrentNpc() {
    if (!state.currentNpc) return;
    const npc = getNpcById(state.currentNpc);
    const ok = await showConfirm({
        title: '重置对话',
        message: `确定重置「${npc?.name || '当前 NPC'}」的所有记忆和好感度吗？`,
        confirmText: '重置',
        danger: true,
    });
    if (!ok) return;
    try {
        const r = await API.resetNpc(state.currentNpc);
        if (r.success) {
            state.messages[state.currentNpc] = [];
            state.renderedCount[state.currentNpc] = 0;
            DOM.messagesArea().innerHTML = '';
            hideScrollBottomBadge();
            DOM.affinityLog().innerHTML = '<p class="empty-hint">对话后将显示好感度变化</p>';
            saveMessages();
            await loadNpcList({preferredNpcId: state.currentNpc});
            showToast('NPC 已重置', 'success');
        }
    } catch (e) { showToast('重置失败，请稍后再试', 'error'); }
}

async function startNewSession() {
    if (!state.currentNpc) return;
    try {
        const res = await API.startSession(state.currentNpc);
        if (res?.npc) {
            const npcInList = state.npcs.find(n => n.id === state.currentNpc);
            if (npcInList) {
                npcInList.memory = res.npc.memory;
                updateMemoryPanel(res.npc.memory);
            }
        }
        state.startedSessions[state.currentNpc] = true;
        appendMessage({role:'system', content:'—— 新的对话会话开始 ——', time:new Date()}, {forceScroll:true});
        showToast('新会话已开始', 'info');
    } catch (e) { showToast('新会话暂时无法开始', 'error'); }
}

function showConfirm({title, message, confirmText = '确认', danger = false}) {
    DOM.confirmTitle().textContent = title;
    DOM.confirmMessage().textContent = message;
    DOM.confirmOk().textContent = confirmText;
    DOM.confirmOk().classList.toggle('danger', danger);
    DOM.confirmOk().classList.toggle('primary', !danger);
    openManagedModal(DOM.confirmModal(), DOM.confirmOk());
    return new Promise(resolve => {
        state.pendingConfirm = resolve;
    });
}

function resolveConfirm(value) {
    if (!state.pendingConfirm) return;
    closeManagedModal(DOM.confirmModal());
    const resolve = state.pendingConfirm;
    state.pendingConfirm = null;
    resolve(value);
}

// ── Utils ──────────────────────────────────────────────
function esc(t) { const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }

function fmtMsg(t) {
    let h = esc(t).replace(/\n/g, '<br>');
    h = h.replace(/「([^」]+)」/g, '<span style="color:var(--gold);font-family:var(--ff-brush);font-size:1.05em;">「$1」</span>');
    return h;
}

function isUserNearBottom() {
    const a = DOM.messagesArea();
    if (!a) return true;
    return a.scrollHeight - a.scrollTop - a.clientHeight < 80;
}

function handleNewMessageScroll(shouldAutoScroll) {
    if (shouldAutoScroll) {
        scrollToBottom();
        hideScrollBottomBadge();
        return;
    }
    showScrollBottomBadge();
}

function handleMessagesScroll() {
    if (isUserNearBottom()) hideScrollBottomBadge();
}

function showScrollBottomBadge() {
    const btn = DOM.scrollBottomBtn();
    const badge = DOM.newMsgBadge();
    if (!btn || !badge) return;
    state.newMsgCount += 1;
    btn.hidden = false;
    badge.textContent = state.newMsgCount > 9 ? '9+' : String(state.newMsgCount);
    badge.hidden = false;
}

function hideScrollBottomBadge() {
    const btn = DOM.scrollBottomBtn();
    const badge = DOM.newMsgBadge();
    if (!btn || !badge) return;
    state.newMsgCount = 0;
    btn.hidden = true;
    badge.hidden = true;
}

function scrollToBottomFromButton() {
    scrollToBottom();
    hideScrollBottomBadge();
}

function scrollToBottom() {
    const a = DOM.messagesArea();
    requestAnimationFrame(() => {
        a.scrollTo({top:a.scrollHeight, behavior:'smooth'});
        hideScrollBottomBadge();
    });
}

function showToast(msg, type='info') {
    const c = DOM.toastContainer();
    const t = document.createElement('div');
    t.className = `toast ${type}`; t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => { t.classList.add('toast-out'); t.addEventListener('animationend', () => t.remove()); }, 3000);
}

// ── Boot ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
