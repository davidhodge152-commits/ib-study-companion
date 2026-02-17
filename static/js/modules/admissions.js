/**
 * Admissions Module — Profile, personal statement, university suggestions, deadlines.
 */
import { api } from './api.js';

const STATUS_COLORS = {
    upcoming: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    submitted: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    accepted: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    rejected: 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300',
};

window.generateProfile = async function() {
    const btn = document.getElementById('gen-profile-btn');
    btn.textContent = 'Generating...';
    btn.disabled = true;
    const res = await api('/api/admissions/profile');
    const el = document.getElementById('profile-summary');
    if (res.content) {
        el.innerHTML = `<div class="whitespace-pre-line">${res.content}</div>`;
    } else if (res.predicted_total) {
        el.innerHTML = `<p><strong>Predicted Total:</strong> ${res.predicted_total}</p>`;
    }
    btn.textContent = 'Refresh Profile';
    btn.disabled = false;
};

window.generateStatement = async function() {
    const target = document.getElementById('ps-target').value;
    const resultEl = document.getElementById('ps-result');
    resultEl.classList.remove('hidden');
    resultEl.textContent = 'Generating personal statement...';
    const res = await api('/api/admissions/personal-statement', {
        method: 'POST',
        body: JSON.stringify({ target }),
    });
    resultEl.textContent = res.statement || res.error || 'Could not generate statement.';
};

window.suggestUniversities = async function() {
    const el = document.getElementById('uni-suggestions');
    el.innerHTML = '<p class="text-sm text-slate-500">Loading suggestions...</p>';
    const res = await api('/api/admissions/suggest-universities', {
        method: 'POST',
        body: JSON.stringify({ preferences: {} }),
    });
    if (res.content) {
        el.innerHTML = `<div class="text-sm whitespace-pre-line">${res.content}</div>`;
    } else {
        el.innerHTML = '<p class="text-sm text-slate-500">No suggestions available yet.</p>';
    }
};

window.showDeadlineForm = function() {
    document.getElementById('deadline-form').classList.remove('hidden');
};

window.addDeadline = async function() {
    const university = document.getElementById('dl-university').value.trim();
    const deadline_date = document.getElementById('dl-date').value;
    if (!university || !deadline_date) return alert('University and date are required.');

    await api('/api/admissions/deadlines', {
        method: 'POST',
        body: JSON.stringify({
            university,
            program: document.getElementById('dl-program').value.trim(),
            deadline_date,
            deadline_type: document.getElementById('dl-type').value,
            notes: document.getElementById('dl-notes').value.trim(),
        }),
    });
    document.getElementById('deadline-form').classList.add('hidden');
    loadDeadlines();
};

window.updateDeadlineStatus = async function(id, status) {
    await api(`/api/admissions/deadlines/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
    });
    loadDeadlines();
};

async function loadDeadlines() {
    const res = await api('/api/admissions/deadlines');
    const el = document.getElementById('deadlines-list');
    if (!res.deadlines || res.deadlines.length === 0) {
        el.innerHTML = '<p class="text-sm text-slate-500">No deadlines added yet.</p>';
        return;
    }
    el.innerHTML = res.deadlines.map(d => `
        <div class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
            <div>
                <h3 class="font-medium text-sm">${d.university}</h3>
                <p class="text-xs text-slate-500">${d.program || ''} &middot; ${d.deadline_date} &middot; ${d.deadline_type}</p>
                ${d.notes ? `<p class="text-xs text-slate-400 mt-0.5">${d.notes}</p>` : ''}
            </div>
            <div class="flex items-center gap-2">
                <span class="text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[d.status] || STATUS_COLORS.upcoming}">${d.status}</span>
                <select onchange="updateDeadlineStatus(${d.id}, this.value)" class="text-xs border rounded px-1 py-0.5 dark:bg-slate-600 dark:border-slate-500">
                    <option value="upcoming" ${d.status === 'upcoming' ? 'selected' : ''}>Upcoming</option>
                    <option value="submitted" ${d.status === 'submitted' ? 'selected' : ''}>Submitted</option>
                    <option value="accepted" ${d.status === 'accepted' ? 'selected' : ''}>Accepted</option>
                    <option value="rejected" ${d.status === 'rejected' ? 'selected' : ''}>Rejected</option>
                </select>
            </div>
        </div>
    `).join('');
}

loadDeadlines();
