/**
 * Community Past Paper Library Module
 */
import { api } from './api.js';

window.showUploadModal = () => document.getElementById('upload-modal').classList.remove('hidden');
window.hideModal = (id) => document.getElementById(id).classList.add('hidden');

async function loadPapers() {
    const subject = document.getElementById('filter-subject')?.value || '';
    const level = document.getElementById('filter-level')?.value || '';
    const params = new URLSearchParams();
    if (subject) params.set('subject', subject);
    if (level) params.set('level', level);

    const res = await api(`/api/papers?${params}`);
    const grid = document.getElementById('papers-grid');

    if (!res.papers || res.papers.length === 0) {
        grid.innerHTML = '<div class="text-center text-slate-500 py-12 col-span-full">No papers yet. Be the first to upload!</div>';
        return;
    }

    grid.innerHTML = res.papers.map(p => `
        <div class="bg-white dark:bg-slate-800 rounded-xl p-5 shadow-sm space-y-3">
            <h3 class="font-semibold">${p.title}</h3>
            <div class="flex flex-wrap gap-2 text-xs">
                <span class="px-2 py-0.5 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300">${p.subject}</span>
                <span class="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700">${p.level}</span>
                ${p.year ? `<span class="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700">${p.year}</span>` : ''}
            </div>
            <div class="flex items-center justify-between text-xs text-slate-500">
                <span>by ${p.uploader_name}</span>
                <span>${p.download_count || 0} downloads</span>
            </div>
            <div class="flex items-center gap-2">
                <div class="flex text-yellow-400 text-sm">${'★'.repeat(Math.round(p.avg_rating || 0))}${'☆'.repeat(5 - Math.round(p.avg_rating || 0))}</div>
                <span class="text-xs text-slate-400">(${p.rating_count || 0})</span>
            </div>
            <div class="flex gap-2">
                <button onclick="viewPaper(${p.id})" class="flex-1 px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs hover:bg-indigo-700">View</button>
                <button onclick="ratePaper(${p.id})" class="px-3 py-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg text-xs">Rate</button>
                <button onclick="reportPaper(${p.id})" class="px-3 py-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-xs">Report</button>
            </div>
        </div>
    `).join('');
}
window.loadPapers = loadPapers;

window.viewPaper = async function(paperId) {
    const res = await api(`/api/papers/${paperId}`);
    if (!res.paper) return alert('Paper not found');
    const questions = res.paper.questions || [];
    alert(`Paper: ${res.paper.title}\n\n${questions.length} questions\n\n${questions.map((q, i) => `Q${i+1}: ${typeof q === 'string' ? q : q.question || JSON.stringify(q)}`).join('\n')}`);
};

window.ratePaper = async function(paperId) {
    const rating = prompt('Rate this paper (1-5):');
    if (!rating) return;
    await api(`/api/papers/${paperId}/rate`, {
        method: 'POST',
        body: JSON.stringify({ rating: parseInt(rating) }),
    });
    loadPapers();
};

window.reportPaper = async function(paperId) {
    const reason = prompt('Why are you reporting this paper?');
    if (!reason) return;
    await api(`/api/papers/${paperId}/report`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
    });
    alert('Report submitted. Thank you.');
};

window.uploadPaper = async function() {
    const title = document.getElementById('paper-title').value.trim();
    const subject = document.getElementById('paper-subject').value.trim();
    const level = document.getElementById('paper-level').value;
    const year = parseInt(document.getElementById('paper-year').value) || 0;
    const questionsRaw = document.getElementById('paper-questions').value.trim();

    if (!title || !subject) return alert('Title and subject are required');

    const questions = questionsRaw.split('\n').filter(q => q.trim()).map(q => ({ question: q.trim() }));
    await api('/api/papers', {
        method: 'POST',
        body: JSON.stringify({ title, subject, level, year, questions }),
    });
    hideModal('upload-modal');
    loadPapers();
};

// Init
loadPapers();
