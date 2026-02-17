/**
 * AI Tutor Conversation Module
 * Features: Markdown + LaTeX rendering, image upload, typing indicator, follow-up suggestions.
 */
import { api } from './api.js';

let currentConvId = null;

/**
 * Render AI message content with Markdown and LaTeX, sanitized against XSS.
 */
function renderContent(text) {
    if (!text) return '';
    let html = text;
    // Parse Markdown if marked.js is available
    if (typeof marked !== 'undefined') {
        html = marked.parse(html);
    }
    // Sanitize HTML to prevent XSS
    if (typeof DOMPurify !== 'undefined') {
        html = DOMPurify.sanitize(html);
    }
    return html;
}

function postRenderMath(el) {
    // Render LaTeX if KaTeX auto-render is available
    if (typeof renderMathInElement !== 'undefined') {
        renderMathInElement(el, {
            delimiters: [
                { left: '$$', right: '$$', display: true },
                { left: '$', right: '$', display: false },
                { left: '\\(', right: '\\)', display: false },
                { left: '\\[', right: '\\]', display: true },
            ],
            throwOnError: false,
        });
    }
}

function createAIBubble(content, followUps) {
    let html = `
        <div class="flex gap-3">
            <div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center flex-shrink-0">
                <span class="text-sm">AI</span>
            </div>
            <div>
                <div class="tutor-msg bg-slate-50 dark:bg-slate-700 rounded-lg p-3 max-w-lg text-sm">${renderContent(content)}</div>`;
    if (followUps && followUps.length > 0) {
        html += '<div class="flex flex-wrap gap-1.5 mt-2">';
        for (const q of followUps) {
            html += `<button onclick="sendFollowUp(this)" class="follow-up-chip px-3 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs rounded-full border border-indigo-200 dark:border-indigo-800">${q}</button>`;
        }
        html += '</div>';
    }
    html += '</div></div>';
    return html;
}

function createUserBubble(content) {
    return `
        <div class="flex gap-3 justify-end">
            <div class="bg-indigo-600 text-white rounded-lg p-3 max-w-lg">
                <p class="text-sm">${content}</p>
            </div>
        </div>`;
}

function createTypingIndicator(id) {
    return `
        <div id="${id}" class="flex gap-3">
            <div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center flex-shrink-0">
                <span class="text-sm">AI</span>
            </div>
            <div class="bg-slate-50 dark:bg-slate-700 rounded-lg p-3">
                <div class="typing-indicator flex gap-1">
                    <span class="w-2 h-2 bg-slate-400 rounded-full"></span>
                    <span class="w-2 h-2 bg-slate-400 rounded-full"></span>
                    <span class="w-2 h-2 bg-slate-400 rounded-full"></span>
                </div>
            </div>
        </div>`;
}

window.showNewConversation = function() {
    currentConvId = null;
    document.getElementById('tutor-setup').classList.remove('hidden');
    document.getElementById('tutor-messages').classList.add('hidden');
    document.getElementById('tutor-input').classList.add('hidden');
};

window.quickStart = function(subject, topic) {
    document.getElementById('tutor-subject').value = subject;
    document.getElementById('tutor-topic').value = topic;
    startConversation();
};

window.startConversation = async function() {
    const subject = document.getElementById('tutor-subject').value.trim();
    const topic = document.getElementById('tutor-topic').value.trim();
    if (!subject) return;

    const res = await api('/api/tutor/start', {
        method: 'POST',
        body: JSON.stringify({ subject, topic }),
    });
    if (res.success) {
        currentConvId = res.conversation_id;
        document.getElementById('tutor-setup').classList.add('hidden');
        const messagesDiv = document.getElementById('tutor-messages');
        messagesDiv.classList.remove('hidden');
        document.getElementById('tutor-input').classList.remove('hidden');
        messagesDiv.innerHTML = createAIBubble(
            `Hello! I'm your IB ${subject} tutor. Let's explore **${topic || 'this subject'}** together. What would you like to understand better?`
        );
        postRenderMath(messagesDiv);
        loadHistory();
    }
};

window.sendMessage = async function() {
    if (!currentConvId) return;
    const input = document.getElementById('tutor-message');
    const message = input.value.trim();
    if (!message) return;

    const messagesDiv = document.getElementById('tutor-messages');
    messagesDiv.innerHTML += createUserBubble(message);
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Typing indicator
    const loadingId = 'loading-' + Date.now();
    messagesDiv.innerHTML += createTypingIndicator(loadingId);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    const res = await api('/api/tutor/message', {
        method: 'POST',
        body: JSON.stringify({ conversation_id: currentConvId, message }),
    });

    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) {
        const bubble = createAIBubble(
            res.response || 'Sorry, I encountered an error.',
            res.follow_ups || []
        );
        loadingEl.outerHTML = bubble;
    }
    // Re-render math for new content
    postRenderMath(messagesDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

window.sendFollowUp = function(btn) {
    const text = btn.textContent.trim();
    document.getElementById('tutor-message').value = text;
    sendMessage();
};

window.uploadTutorImage = async function(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];

    const formData = new FormData();
    formData.append('image', file);

    const messagesDiv = document.getElementById('tutor-messages');
    // Show image preview
    const previewUrl = URL.createObjectURL(file);
    messagesDiv.innerHTML += `
        <div class="flex gap-3 justify-end">
            <div class="bg-indigo-600 text-white rounded-lg p-3 max-w-lg">
                <img src="${previewUrl}" alt="Uploaded image" class="max-w-full rounded mb-1" style="max-height:200px">
                <p class="text-xs opacity-75">Extracting text...</p>
            </div>
        </div>`;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        const resp = await fetch('/api/tutor/upload-image', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();
        if (data.text) {
            document.getElementById('tutor-message').value = data.text;
        } else {
            document.getElementById('tutor-message').value = data.error || 'Could not extract text from image.';
        }
    } catch (e) {
        document.getElementById('tutor-message').value = 'Error uploading image.';
    }
    input.value = '';
};

async function loadHistory() {
    const res = await api('/api/tutor/history');
    const container = document.getElementById('conv-history');
    if (!container || !res.conversations) return;
    container.innerHTML = res.conversations.map(c => `
        <button onclick="loadConversation(${c.id})" class="w-full text-left px-2 py-1.5 rounded text-xs hover:bg-slate-100 dark:hover:bg-slate-700 ${c.id === currentConvId ? 'bg-slate-100 dark:bg-slate-700' : ''}">
            <p class="font-medium truncate">${c.subject}: ${c.topic || 'General'}</p>
            <p class="text-slate-400 truncate">${c.updated_at}</p>
        </button>
    `).join('');
}

window.loadConversation = async function(convId) {
    const res = await api(`/api/tutor/${convId}`);
    if (!res.conversation) return;
    currentConvId = convId;
    document.getElementById('tutor-setup').classList.add('hidden');
    const messagesDiv = document.getElementById('tutor-messages');
    messagesDiv.classList.remove('hidden');
    document.getElementById('tutor-input').classList.remove('hidden');

    messagesDiv.innerHTML = res.conversation.messages.map(m => {
        if (m.role === 'user') {
            return createUserBubble(m.content);
        }
        return createAIBubble(m.content);
    }).join('');
    postRenderMath(messagesDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    loadHistory();
};

// Init
loadHistory();
