/**
 * Examiner Dashboard Module — Queue management, review form, stats.
 */
import { api } from './api.js';

async function loadQueue() {
    const res = await api('/api/reviews/queue');
    const el = document.getElementById('pending-queue');
    const statEl = document.getElementById('stat-pending');
    if (!res.reviews || res.reviews.length === 0) {
        el.innerHTML = '<p class="text-sm text-slate-500">No pending reviews</p>';
        if (statEl) statEl.textContent = '0';
        return;
    }
    if (statEl) statEl.textContent = res.reviews.length;
    el.innerHTML = res.reviews.map(r => `
        <div class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
            <div>
                <h3 class="font-medium text-sm">${r.title || r.doc_type}</h3>
                <p class="text-xs text-slate-500">${r.subject} &middot; ${r.doc_type} &middot; ${r.submitted_at || ''}</p>
            </div>
            <button onclick="assignReview(${r.id})" class="px-3 py-1 bg-indigo-600 text-white text-xs rounded-lg">Claim</button>
        </div>
    `).join('');
}

async function loadAssigned() {
    const res = await api('/api/reviews/assigned');
    const el = document.getElementById('assigned-list');
    const statEl = document.getElementById('stat-assigned');
    if (!res.reviews || res.reviews.length === 0) {
        el.innerHTML = '<p class="text-sm text-slate-500">No reviews assigned to you</p>';
        if (statEl) statEl.textContent = '0';
        return;
    }
    if (statEl) statEl.textContent = res.reviews.length;
    el.innerHTML = res.reviews.map(r => `
        <div class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
            <div>
                <h3 class="font-medium text-sm">${r.title || r.doc_type}</h3>
                <p class="text-xs text-slate-500">${r.subject} &middot; Assigned: ${r.assigned_at || ''}</p>
            </div>
            <button onclick="openReviewForm(${r.id})" class="px-3 py-1 bg-emerald-600 text-white text-xs rounded-lg">Review</button>
        </div>
    `).join('');
}

window.assignReview = async function(reviewId) {
    await api(`/api/reviews/${reviewId}/assign`, { method: 'POST' });
    loadQueue();
    loadAssigned();
};

window.openReviewForm = function(reviewId) {
    document.getElementById('review-id').value = reviewId;
    document.getElementById('review-form').classList.remove('hidden');
    document.getElementById('review-feedback').value = '';
    document.getElementById('review-grade').value = '';
    document.getElementById('review-video').value = '';
};

window.submitReview = async function() {
    const reviewId = document.getElementById('review-id').value;
    const feedback = document.getElementById('review-feedback').value.trim();
    if (!feedback) return alert('Feedback is required');

    await api(`/api/reviews/${reviewId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
            feedback,
            grade: document.getElementById('review-grade').value,
            video_url: document.getElementById('review-video').value.trim(),
        }),
    });
    document.getElementById('review-form').classList.add('hidden');
    loadAssigned();
};

// Init
loadQueue();
loadAssigned();
