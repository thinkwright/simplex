// Planner application JavaScript
// Depends on: simplex-spec.js (system prompt constants)

const MODEL_NAME = 'mistralai/Mixtral-8x7B-Instruct-v0.1';

// State management
const state = {
    currentStep: 1,
    projectType: 'greenfield',
    description: '',
    refinementMessages: [],
    generatedSpec: '',
    lintResult: null
};

// --- Project Type ---

const PLACEHOLDERS = {
    greenfield: 'Example: A function that authenticates users by email and password, returning user data on success or an error on failure...',
    brownfield: 'Example: Modernize session-based auth to support JWT tokens. Existing session clients must continue to work...'
};

function setProjectType(type) {
    state.projectType = type;
    document.getElementById('type-greenfield').classList.toggle('active', type === 'greenfield');
    document.getElementById('type-brownfield').classList.toggle('active', type === 'brownfield');
    var input = document.getElementById('describe-input');
    if (input) input.placeholder = PLACEHOLDERS[type] || PLACEHOLDERS.greenfield;
}

// --- Step Navigation ---

function goToStep(stepName) {
    const stepMap = { describe: 1, refine: 2, generate: 3 };
    const step = typeof stepName === 'number' ? stepName : stepMap[stepName];
    if (!step) return;

    // Validate before advancing
    if (step === 2 && state.currentStep === 1) {
        const input = document.getElementById('describe-input');
        if (input && !input.value.trim()) return;
        state.description = input.value.trim();
    }

    state.currentStep = step;

    // Update step indicators
    document.querySelectorAll('.planner-step').forEach((stepEl, index) => {
        const stepNum = index + 1;
        stepEl.classList.remove('active', 'step-completed');
        if (stepNum < step) {
            stepEl.classList.add('step-completed');
        } else if (stepNum === step) {
            stepEl.classList.add('active');
        }
    });

    // Show/hide step containers
    const containers = ['step-describe', 'step-refine', 'step-generate'];
    containers.forEach((id, index) => {
        const el = document.getElementById(id);
        if (el) {
            if (index + 1 === step) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        }
    });

    // Start refinement when entering step 2
    if (step === 2 && state.refinementMessages.length === 0) {
        startRefinement();
    }

    // Generate when entering step 3
    if (step === 3) {
        generateSpecification();
    }
}

// --- Chat / Refinement ---

function addMessage(type, text) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    const div = document.createElement('div');
    div.className = 'chat-message chat-message-' + type;
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoadingMessage() {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    const div = document.createElement('div');
    div.className = 'chat-message chat-message-assistant chat-message-loading';
    div.id = 'loading-dots';
    div.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeLoadingMessage() {
    const el = document.getElementById('loading-dots');
    if (el) el.remove();
}

async function startRefinement() {
    addLoadingMessage();

    try {
        const response = await fetch('/api/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: MODEL_NAME,
                temperature: 0.7,
                max_tokens: 1024,
                messages: [
                    { role: 'system', content: REFINE_SYSTEM_PROMPT },
                    { role: 'user', content: 'I want to create a specification for: ' + state.description }
                ]
            })
        });

        if (!response.ok) throw new Error('API request failed');

        const data = await response.json();
        const assistantMessage = data.choices[0].message.content;

        removeLoadingMessage();
        addMessage('assistant', assistantMessage);
        state.refinementMessages.push({ role: 'assistant', content: assistantMessage });
    } catch (error) {
        removeLoadingMessage();
        addMessage('system', 'Describe your requirements further, or skip to generation.');
        console.error('Refinement error:', error);
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    if (!chatInput) return;
    const message = chatInput.value.trim();
    if (!message) return;

    addMessage('user', message);
    chatInput.value = '';
    state.refinementMessages.push({ role: 'user', content: message });
    addLoadingMessage();

    try {
        const response = await fetch('/api/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: MODEL_NAME,
                temperature: 0.7,
                max_tokens: 1024,
                messages: [
                    { role: 'system', content: REFINE_SYSTEM_PROMPT },
                    { role: 'user', content: 'I want to create a specification for: ' + state.description },
                    ...state.refinementMessages
                ]
            })
        });

        if (!response.ok) throw new Error('API request failed');

        const data = await response.json();
        const assistantMessage = data.choices[0].message.content;
        removeLoadingMessage();
        addMessage('assistant', assistantMessage);
        state.refinementMessages.push({ role: 'assistant', content: assistantMessage });
    } catch (error) {
        removeLoadingMessage();
        addMessage('error', 'Failed to get response. Ensure the API proxy is configured.');
        console.error('Chat error:', error);
    }
}

// --- Specification Generation ---

async function generateSpecification() {
    const specOutput = document.getElementById('spec-output');
    if (!specOutput) return;

    specOutput.innerHTML = '<div class="loading">Generating Simplex specification...</div>';
    specOutput.classList.add('loading');
    specOutput.classList.remove('error');
    hideLintResults();

    // Build system prompt with brownfield fragment if needed
    let systemPrompt = BASE_SYSTEM_PROMPT;
    if (state.projectType === 'brownfield') {
        systemPrompt += BROWNFIELD_PROMPT_FRAGMENT;
    }

    // Build user prompt
    let userPrompt = 'Generate a Simplex specification for: ' + state.description;
    if (state.projectType === 'brownfield') {
        userPrompt += '\n\nThis is a BROWNFIELD project — evolving an existing system. Include BASELINE and EVAL landmarks.';
    }
    if (state.refinementMessages.length > 0) {
        userPrompt += '\n\nRefinement conversation:\n' +
            state.refinementMessages.map(function(m) { return m.role + ': ' + m.content; }).join('\n\n');
    }

    try {
        const response = await fetch('/api/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: MODEL_NAME,
                temperature: 0.3,
                max_tokens: 2048,
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: userPrompt }
                ]
            })
        });

        if (!response.ok) throw new Error('API request failed');

        const data = await response.json();
        state.generatedSpec = data.choices[0].message.content;
        specOutput.innerHTML = formatSpecOutput(state.generatedSpec);
        specOutput.classList.remove('loading');

        // Run linter via server-side Go linter
        try {
            const lintResp = await fetch('/api/lint', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ spec: state.generatedSpec })
            });
            if (lintResp.ok) {
                state.lintResult = await lintResp.json();
                renderLintResults();
            }
        } catch (lintErr) {
            console.error('Lint error:', lintErr);
        }
    } catch (error) {
        specOutput.innerHTML = '<div class="error">Failed to generate specification. Ensure the API proxy is configured.</div>';
        specOutput.classList.remove('loading');
        specOutput.classList.add('error');
        console.error('Generation error:', error);
    }
}

// --- Lint Results ---

function renderLintResults() {
    const container = document.getElementById('lint-results');
    const badge = document.getElementById('lint-badge');
    const items = document.getElementById('lint-items');
    if (!container || !badge || !items || !state.lintResult) return;

    const result = state.lintResult;
    const allIssues = result.errors.concat(result.warnings);

    if (result.valid && result.warnings.length === 0) {
        badge.textContent = 'Pass';
        badge.className = 'lint-badge lint-badge-pass';
        items.innerHTML = '<div class="lint-item"><span class="lint-message" style="color: var(--success-color);">Specification passes all validation checks.</span></div>';
    } else if (result.valid && result.warnings.length > 0) {
        badge.textContent = result.warnings.length + ' warning' + (result.warnings.length !== 1 ? 's' : '');
        badge.className = 'lint-badge lint-badge-warn';
        items.innerHTML = allIssues.map(renderLintItem).join('');
    } else {
        badge.textContent = result.errors.length + ' error' + (result.errors.length !== 1 ? 's' : '');
        badge.className = 'lint-badge lint-badge-fail';
        items.innerHTML = allIssues.map(renderLintItem).join('');
    }

    container.style.display = 'block';

    // Auto-open details on errors, keep collapsed on pass
    if (!result.valid) {
        container.open = true;
    } else {
        container.open = false;
    }
}

function renderLintItem(issue) {
    var isError = issue.code && issue.code.startsWith('E');
    return '<div class="lint-item">' +
        '<span class="lint-code ' + (isError ? 'lint-code-error' : 'lint-code-warning') + '">' + issue.code + '</span>' +
        '<span class="lint-message">' + issue.message + '</span>' +
        '<span class="lint-location">' + issue.location + '</span>' +
        '</div>';
}

function hideLintResults() {
    var container = document.getElementById('lint-results');
    if (container) container.style.display = 'none';
}

// --- Output Formatting ---

function formatSpecOutput(text) {
    return text
        .replace(/\n(FUNCTION|RULES|DONE_WHEN|EXAMPLES|ERRORS|DATA|CONSTRAINT|BASELINE|EVAL|READS|WRITES|TRIGGERS|NOT_ALLOWED|HANDOFF|UNCERTAIN|DETERMINISM):/g,
            '\n<span class="landmark-keyword">$1:</span>')
        .replace(/^(FUNCTION|RULES|DONE_WHEN|EXAMPLES|ERRORS|DATA|CONSTRAINT|BASELINE|EVAL|READS|WRITES|TRIGGERS|NOT_ALLOWED|HANDOFF|UNCERTAIN|DETERMINISM):/gm,
            '<span class="landmark-keyword">$1:</span>')
        .replace(/^(\s*)- (.*)/gm, '$1<span class="bullet">- </span>$2')
        .replace(/\n/g, '<br>');
}

// --- Actions ---

function copySpec() {
    navigator.clipboard.writeText(state.generatedSpec).then(function() {
        var btn = event.target;
        btn.textContent = 'Copied!';
        setTimeout(function() { btn.textContent = 'Copy'; }, 2000);
    });
}

function specFilename() {
    var match = state.generatedSpec.match(/FUNCTION:\s*(\w+)/);
    if (match) return match[1] + '.simplex';
    // Fall back to first few words of the description
    if (state.description) {
        var slug = state.description.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);
        if (slug) return slug + '.simplex';
    }
    return 'spec.simplex';
}

function downloadSpec() {
    var blob = new Blob([state.generatedSpec], { type: 'text/plain' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = specFilename();
    a.click();
    URL.revokeObjectURL(url);
}

function startOver() {
    state.currentStep = 1;
    state.projectType = 'greenfield';
    state.description = '';
    state.refinementMessages = [];
    state.generatedSpec = '';
    state.lintResult = null;

    var input = document.getElementById('describe-input');
    if (input) input.value = '';
    var chatMessages = document.getElementById('chat-messages');
    if (chatMessages) chatMessages.innerHTML = '';
    var specOutput = document.getElementById('spec-output');
    if (specOutput) { specOutput.innerHTML = ''; specOutput.classList.remove('loading', 'error'); }
    hideLintResults();
    setProjectType('greenfield');
    goToStep(1);
}

function loadExample(type) {
    var examples = {
        'minimal': 'A function that greets a user by name, returning a friendly greeting string.',
        'auth': 'User authentication that verifies email and password, returning user data on success or an error message on failure. Include data type definitions for User and AuthResult.',
        'cart': 'A shopping cart system with functions to add items, remove items, and calculate the total price. Items have id, name, price, and quantity. Keep each function to 3-4 rules maximum and provide one example per rule branch.',
        'evolution': 'Modernize an existing session-based authentication system to support JWT tokens alongside sessions, with refresh token rotation and rate limiting. Existing session-based clients must continue to work.'
    };

    var projectTypes = {
        'minimal': 'greenfield',
        'auth': 'greenfield',
        'cart': 'greenfield',
        'evolution': 'brownfield'
    };

    var input = document.getElementById('describe-input');
    if (input && examples[type]) {
        input.value = examples[type];
        setProjectType(projectTypes[type] || 'greenfield');
    }
}

// --- Reference Modal ---

function toggleRefModal() {
    var modal = document.getElementById('ref-modal');
    if (modal) modal.classList.toggle('hidden');
}

function closeRefModalOnOverlay(event) {
    if (event.target === event.currentTarget) {
        toggleRefModal();
    }
}

function switchRefTab(tabName) {
    document.querySelectorAll('.ref-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('.ref-tab-content').forEach(function(c) { c.classList.remove('active'); });
    // Find the clicked tab button and activate it
    document.querySelectorAll('.ref-tab').forEach(function(t) {
        if (t.textContent.trim().toLowerCase() === tabName) {
            t.classList.add('active');
        }
    });
    var content = document.getElementById('ref-tab-' + tabName);
    if (content) content.classList.add('active');
}

// --- Event Listeners ---

document.addEventListener('DOMContentLoaded', function() {
    var chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }

    // Close reference modal on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            var modal = document.getElementById('ref-modal');
            if (modal && !modal.classList.contains('hidden')) {
                toggleRefModal();
            }
        }
    });
});
