/**
 * Community Analytics Dashboard Module
 */
import { api } from './api.js';

async function loadGlobalStats() {
    try {
        const res = await api('/api/analytics/global');
        document.getElementById('stat-users').textContent = res.total_users || 0;
        document.getElementById('stat-questions').textContent = res.total_questions || 0;
        document.getElementById('stat-avg-score').textContent = res.avg_score ? `${res.avg_score}%` : '-';
        document.getElementById('stat-active').textContent = res.active_today || 0;

        // Subject popularity chart
        if (res.subject_counts && Object.keys(res.subject_counts).length > 0) {
            const ctx = document.getElementById('subject-chart');
            if (ctx) {
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(res.subject_counts),
                        datasets: [{
                            data: Object.values(res.subject_counts),
                            backgroundColor: [
                                '#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd',
                                '#818cf8', '#4f46e5', '#7c3aed', '#6d28d9',
                            ],
                        }],
                    },
                    options: {
                        responsive: true,
                        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } },
                    },
                });
            }
        }
    } catch (e) {
        console.error('Failed to load global stats:', e);
    }
}

async function loadTrending() {
    try {
        const res = await api('/api/analytics/trending');
        const container = document.getElementById('trending-list');
        if (!container || !res.topics || res.topics.length === 0) {
            if (container) container.innerHTML = '<p class="text-sm text-slate-500">Not enough data yet</p>';
            return;
        }
        container.innerHTML = res.topics.slice(0, 10).map((t, i) => `
            <div class="flex items-center justify-between py-2">
                <div class="flex items-center gap-3">
                    <span class="w-5 text-sm font-medium text-slate-400">${i + 1}</span>
                    <span class="text-sm">${t.topic || t.subject || 'Unknown'}</span>
                </div>
                <span class="text-xs text-slate-500">${t.count || 0} practices</span>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load trending:', e);
    }
}

// Init
loadGlobalStats();
loadTrending();
