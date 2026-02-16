/**
 * AI Tutor Conversation Module
 */
import { api } from './api.js';

let currentConvId = null;

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
        document.getElementById('tutor-messages').classList.remove('hidden');
        document.getElementById('tutor-input').classList.remove('hidden');
        document.getElementById('tutor-messages').innerHTML = `
            <div class="flex gap-3">
                <div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center flex-shrink-0">
                    <span class="text-sm">AI</span>
                </div>
                <div class="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 max-w-lg">
                    <p class="text-sm">Hello! I'm your IB ${subject} tutor. Let's explore <strong>${topic || 'this subject'}</strong> together. What would you like to understand better?</p>
                </div>
            </div>
        `;
        loadHistory();
    }
};

window.sendMessage = async function() {
    if (!currentConvId) return;
    const input = document.getElementById('tutor-message');
    const message = input.value.trim();
    if (!message) return;

    const messagesDiv = document.getElementById('tutor-messages');

    // Add user message
    messagesDiv.innerHTML += `
        <div class="flex gap-3 justify-end">
            <div class="bg-indigo-600 text-white rounded-lg p-3 max-w-lg">
                <p class="text-sm">${message}</p>
            </div>
        </div>
    `;
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // Add loading indicator
    const loadingId = 'loading-' + Date.now();
    messagesDiv.innerHTML += `
        <div id="${loadingId}" class="flex gap-3">
            <div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center flex-shrink-0">
                <span class="text-sm">AI</span>
            </div>
            <div class="bg-slate-50 dark:bg-slate-700 rounded-lg p-3">
                <p class="text-sm text-slate-400">Thinking...</p>
            </div>
        </div>
    `;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    const res = await api('/api/tutor/message', {
        method: 'POST',
        body: JSON.stringify({ conversation_id: currentConvId, message }),
    });

    // Replace loading with response
    const loadingEl = document.getElementById(loadingId);
    if (loadingEl) {
        loadingEl.innerHTML = `
            <div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center flex-shrink-0">
                <span class="text-sm">AI</span>
            </div>
            <div class="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 max-w-lg">
                <p class="text-sm whitespace-pre-wrap">${res.response || 'Sorry, I encountered an error.'}</p>
            </div>
        `;
    }
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
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
    document.getElementById('tutor-messages').classList.remove('hidden');
    document.getElementById('tutor-input').classList.remove('hidden');

    const messagesDiv = document.getElementById('tutor-messages');
    messagesDiv.innerHTML = res.conversation.messages.map(m => {
        if (m.role === 'user') {
            return `<div class="flex gap-3 justify-end"><div class="bg-indigo-600 text-white rounded-lg p-3 max-w-lg"><p class="text-sm">${m.content}</p></div></div>`;
        }
        return `<div class="flex gap-3"><div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900 rounded-full flex items-center justify-center flex-shrink-0"><span class="text-sm">AI</span></div><div class="bg-slate-50 dark:bg-slate-700 rounded-lg p-3 max-w-lg"><p class="text-sm whitespace-pre-wrap">${m.content}</p></div></div>`;
    }).join('');
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    loadHistory();
};

// Init
loadHistory();
