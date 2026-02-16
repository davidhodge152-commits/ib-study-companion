/**
 * Study Groups & Social Learning Module
 */
import { api } from './api.js';

let currentGroupId = null;

// ── Load groups on page init ────────────────────────────────────────
async function loadGroups() {
    const res = await api('/api/groups');
    const container = document.getElementById('groups-list');
    if (!res.groups || res.groups.length === 0) {
        container.innerHTML = '<div class="text-center text-slate-500 py-12 col-span-full">No groups yet. Create or join one!</div>';
        return;
    }
    container.innerHTML = res.groups.map(g => `
        <div class="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm cursor-pointer hover:shadow-md transition-shadow"
             onclick="openGroup(${g.id})">
            <h3 class="font-semibold">${g.name}</h3>
            <p class="text-sm text-slate-500">${g.subject || 'General'} ${g.level || ''}</p>
            <div class="flex items-center justify-between mt-3 text-xs text-slate-400">
                <span>${g.member_count || 0} members</span>
                <span class="px-2 py-0.5 rounded-full ${g.my_role === 'owner' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300' : 'bg-slate-100 dark:bg-slate-700'}">${g.my_role}</span>
            </div>
        </div>
    `).join('');
}

window.openGroup = async function(groupId) {
    currentGroupId = groupId;
    const res = await api(`/api/groups/${groupId}`);
    const detail = document.getElementById('group-detail');
    detail.classList.remove('hidden');

    document.getElementById('group-name').textContent = res.group.name;
    document.getElementById('group-invite').textContent = res.group.invite_code;

    document.getElementById('group-members').innerHTML = res.members.map(m => `
        <div class="flex items-center justify-between py-1">
            <span class="text-sm">${m.name}</span>
            <span class="text-xs text-slate-400">${m.xp || 0} XP</span>
        </div>
    `).join('');

    document.getElementById('group-challenges').innerHTML = res.challenges.length
        ? res.challenges.map(c => `
            <div class="p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
                <div class="flex items-center justify-between">
                    <span class="text-sm font-medium">${c.title}</span>
                    <span class="text-xs px-2 py-0.5 rounded-full ${c.status === 'open' ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-600'}">${c.status}</span>
                </div>
                <p class="text-xs text-slate-500 mt-1">${c.participant_count} participants</p>
            </div>
        `).join('')
        : '<p class="text-sm text-slate-500">No challenges yet</p>';
};

window.closeGroupDetail = function() {
    document.getElementById('group-detail').classList.add('hidden');
    currentGroupId = null;
};

// ── Create group ────────────────────────────────────────────────────
window.showCreateModal = () => document.getElementById('create-modal').classList.remove('hidden');
window.showJoinModal = () => document.getElementById('join-modal').classList.remove('hidden');
window.showChallengeModal = () => document.getElementById('challenge-modal').classList.remove('hidden');
window.hideModal = (id) => document.getElementById(id).classList.add('hidden');

window.createGroup = async function() {
    const name = document.getElementById('new-group-name').value.trim();
    const subject = document.getElementById('new-group-subject').value.trim();
    if (!name) return;
    await api('/api/groups', { method: 'POST', body: JSON.stringify({ name, subject }) });
    hideModal('create-modal');
    loadGroups();
};

window.joinGroup = async function() {
    const code = document.getElementById('join-code').value.trim();
    if (!code) return;
    const res = await api('/api/groups/join', { method: 'POST', body: JSON.stringify({ invite_code: code }) });
    if (res.success) {
        hideModal('join-modal');
        loadGroups();
    } else {
        alert(res.error || 'Failed to join group');
    }
};

window.createChallenge = async function() {
    if (!currentGroupId) return;
    const title = document.getElementById('challenge-title').value.trim();
    const subject = document.getElementById('challenge-subject').value.trim();
    if (!title) return;
    await api('/api/challenges', { method: 'POST', body: JSON.stringify({ group_id: currentGroupId, title, subject }) });
    hideModal('challenge-modal');
    openGroup(currentGroupId);
};

// ── Leaderboard ─────────────────────────────────────────────────────
async function loadLeaderboard() {
    const res = await api('/api/leaderboard?scope=global');
    const container = document.getElementById('leaderboard');
    if (!res.leaderboard || res.leaderboard.length === 0) {
        container.innerHTML = '<p class="text-sm text-slate-500">No entries yet</p>';
        return;
    }
    container.innerHTML = res.leaderboard.slice(0, 10).map((e, i) => `
        <div class="flex items-center justify-between py-2 ${i < 3 ? 'font-semibold' : ''}">
            <div class="flex items-center gap-3">
                <span class="w-6 text-center text-sm ${i === 0 ? 'text-yellow-500' : i === 1 ? 'text-slate-400' : i === 2 ? 'text-orange-400' : 'text-slate-500'}">${e.rank}</span>
                <span class="text-sm">${e.name}</span>
            </div>
            <span class="text-sm text-indigo-600 dark:text-indigo-400">${e.xp} XP</span>
        </div>
    `).join('');
}

// Init
loadGroups();
loadLeaderboard();
