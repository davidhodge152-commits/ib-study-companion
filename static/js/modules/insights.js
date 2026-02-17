/**
 * Insights page — charts, tables, weakness report, syllabus coverage,
 * misconceptions, predicted grades, mock exam reports.
 */

import { api } from './api.js';
import { escapeHtml } from './utils.js';

let trendChart = null;
let distChart = null;

export function loadInsights() {
    api.get('/api/insights')
        .then(res => res.json())
        .then(data => {
            if (data.error) return;

            renderTextInsights(data.insights || []);
            renderCommandTermTable(data.command_term_stats || {});
            renderGapTable(data.gaps || []);
            renderStudyAllocation(data.study_allocation || []);
            renderTrendChart(data);
            renderDistChart(data);
            renderSyllabusCoverage(data.syllabus_coverage || null);
            loadMisconceptions();
            loadPredictedGrades();
            loadMockReports();

            if (data.writing_profile) {
                const ws = document.getElementById('writing-section');
                ws.style.display = 'block';
                document.getElementById('writing-content').innerHTML = `
                    <p><strong class="text-slate-700">Summary:</strong> ${escapeHtml(data.writing_profile.summary)}</p>
                    <p><strong class="text-slate-700">Verbosity:</strong> ${escapeHtml(data.writing_profile.verbosity)}</p>
                    <p><strong class="text-slate-700">Terminology:</strong> ${escapeHtml(data.writing_profile.terminology_usage)}</p>
                    <p><strong class="text-slate-700">Argument Structure:</strong> ${escapeHtml(data.writing_profile.argument_structure)}</p>
                    ${data.writing_profile.common_patterns.length > 0
                        ? '<p><strong class="text-slate-700">Common Patterns:</strong></p><ul class="list-disc ml-5">'
                          + data.writing_profile.common_patterns.map(p => `<li>${escapeHtml(p)}</li>`).join('')
                          + '</ul>'
                        : ''}
                `;
            }
        })
        .catch(err => {
            const container = document.getElementById('insights-cards');
            if (container) {
                container.innerHTML = `
                    <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center col-span-3" role="alert">
                        <p class="text-red-700 dark:text-red-400 font-medium text-sm">Failed to load insights. Please try again.</p>
                        <button onclick="loadInsights()" class="mt-3 px-5 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors">
                            Try Again
                        </button>
                    </div>`;
            }
        });
}

function renderTextInsights(insights) {
    const container = document.getElementById('insights-cards');
    if (!insights || insights.length === 0) {
        container.innerHTML = `
            <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 col-span-3">
                <p class="text-sm text-slate-400 text-center">Start studying to generate insights about your performance.</p>
            </div>`;
        return;
    }

    const severityStyles = {
        red: 'border-l-4 border-l-red-500 bg-red-50',
        yellow: 'border-l-4 border-l-amber-500 bg-amber-50',
        green: 'border-l-4 border-l-green-500 bg-green-50',
        blue: 'border-l-4 border-l-blue-500 bg-blue-50',
    };
    const severityText = {
        red: 'text-red-800',
        yellow: 'text-amber-800',
        green: 'text-green-800',
        blue: 'text-blue-800',
    };

    container.innerHTML = insights.map(insight => `
        <div class="rounded-xl shadow-sm border border-slate-200 p-5 ${severityStyles[insight.severity] || ''}">
            <h4 class="text-sm font-semibold ${severityText[insight.severity] || 'text-slate-700'} mb-1">${escapeHtml(insight.title)}</h4>
            <p class="text-sm text-slate-600 mb-2">${escapeHtml(insight.body)}</p>
            <p class="text-xs text-slate-500">${escapeHtml(insight.action)}</p>
        </div>
    `).join('');
}

function renderCommandTermTable(ctStats) {
    const container = document.getElementById('ct-breakdown-content');
    const entries = Object.entries(ctStats);

    if (entries.length === 0) {
        container.innerHTML = '<p class="text-sm text-slate-400 text-center py-4">No command term data yet.</p>';
        return;
    }

    entries.sort((a, b) => a[1].avg_percentage - b[1].avg_percentage);

    container.innerHTML = '<div class="space-y-3">' + entries.map(([ct, stats]) => {
        const pct = stats.avg_percentage;
        let barColor = 'bg-green-500';
        let textColor = 'text-green-700';
        if (pct < 50) { barColor = 'bg-red-500'; textColor = 'text-red-700'; }
        else if (pct < 65) { barColor = 'bg-amber-500'; textColor = 'text-amber-700'; }

        return `
            <div class="flex items-center gap-3">
                <span class="text-sm font-medium text-slate-700 w-40 shrink-0">${escapeHtml(ct)}</span>
                <div class="flex-1 bg-slate-100 rounded-full h-3">
                    <div class="h-3 rounded-full ${barColor} transition-all" style="width: ${pct}%"></div>
                </div>
                <span class="text-sm font-semibold ${textColor} w-16 text-right">${pct}%</span>
                <span class="text-xs text-slate-400 w-16 text-right">(${stats.count})</span>
            </div>`;
    }).join('') + '</div>';
}

function renderGapTable(gaps) {
    const container = document.getElementById('gap-table-content');
    if (!gaps || gaps.length === 0) {
        container.innerHTML = '<p class="text-sm text-slate-400 text-center py-8">No gap data yet.</p>';
        return;
    }

    const rows = gaps.map(g => {
        const statusBadge = {
            on_track: '<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">On Track</span>',
            close: '<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-amber-100 text-amber-700">Close</span>',
            behind: '<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">Behind</span>',
            no_data: '<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-500">No Data</span>',
        };

        return `<tr class="hover:bg-slate-50 transition-colors">
            <td class="px-5 py-3 text-slate-700 text-sm">${escapeHtml(g.subject)}</td>
            <td class="px-5 py-3 text-center"><span class="px-2 py-0.5 text-xs font-semibold rounded-full ${g.level === 'HL' ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}">${g.level}</span></td>
            <td class="px-5 py-3 text-center text-slate-700 font-semibold">${g.target}</td>
            <td class="px-5 py-3 text-center text-slate-700 font-semibold">${g.predicted || '\u2014'}</td>
            <td class="px-5 py-3 text-center">${g.gap > 0 ? '<span class="text-red-600 font-semibold">-' + g.gap + '</span>' : (g.status === 'no_data' ? '\u2014' : '<span class="text-green-600">0</span>')}</td>
            <td class="px-5 py-3 text-center">${statusBadge[g.status] || ''}</td>
        </tr>`;
    }).join('');

    container.innerHTML = `
        <table class="w-full text-sm">
            <thead class="bg-slate-50 border-b border-slate-200">
                <tr>
                    <th class="text-left px-5 py-3 font-medium text-slate-600">Subject</th>
                    <th class="text-center px-5 py-3 font-medium text-slate-600">Level</th>
                    <th class="text-center px-5 py-3 font-medium text-slate-600">Target</th>
                    <th class="text-center px-5 py-3 font-medium text-slate-600">Predicted</th>
                    <th class="text-center px-5 py-3 font-medium text-slate-600">Gap</th>
                    <th class="text-center px-5 py-3 font-medium text-slate-600">Status</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">${rows}</tbody>
        </table>`;
}

function renderStudyAllocation(allocation) {
    const container = document.getElementById('allocation-content');
    if (!allocation || allocation.length === 0) {
        container.innerHTML = '<p class="text-sm text-slate-400 text-center py-4">No allocation data yet.</p>';
        return;
    }

    const colors = ['bg-indigo-500', 'bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-red-500', 'bg-purple-500'];

    container.innerHTML = '<div class="space-y-2">' + allocation.map((a, i) => `
        <div class="flex items-center gap-3">
            <span class="text-sm text-slate-700 w-48 shrink-0">${escapeHtml(a.subject)}</span>
            <div class="flex-1 bg-slate-100 rounded-full h-3">
                <div class="h-3 rounded-full ${colors[i % colors.length]} transition-all" style="width: ${a.percentage}%"></div>
            </div>
            <span class="text-sm font-semibold text-slate-600 w-12 text-right">${a.percentage}%</span>
        </div>
    `).join('') + '</div>';
}

function renderTrendChart(data) {
    if (data.trend && data.trend.length > 0) {
        const emptyEl = document.getElementById('trend-empty');
        if (emptyEl) emptyEl.classList.add('hidden');
        const ctx = document.getElementById('trend-chart').getContext('2d');
        if (trendChart) trendChart.destroy();
        trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.trend.map((_, i) => i + 1),
                datasets: [{
                    label: 'Score %',
                    data: data.trend,
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                    pointBackgroundColor: '#4f46e5',
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { min: 0, max: 100, ticks: { callback: v => v + '%' } },
                    x: { title: { display: true, text: 'Answer #' } }
                }
            }
        });
        const descEl = document.getElementById('trend-chart-desc');
        if (descEl && data.trend) {
            descEl.textContent = `Grade trend: ${data.trend.map((v, i) => `Answer ${i+1}: ${v}%`).join(', ')}`;
        }
    } else {
        const chartEl = document.getElementById('trend-chart');
        if (chartEl) chartEl.style.display = 'none';
        const emptyEl = document.getElementById('trend-empty');
        if (emptyEl) emptyEl.classList.remove('hidden');
    }
}

function renderDistChart(data) {
    if (data.grade_distribution && Object.keys(data.grade_distribution).length > 0) {
        const emptyEl = document.getElementById('dist-empty');
        if (emptyEl) emptyEl.classList.add('hidden');
        const labels = ['1', '2', '3', '4', '5', '6', '7'];
        const values = labels.map(l => data.grade_distribution[l] || data.grade_distribution[parseInt(l)] || 0);
        const colors = ['#ef4444', '#ef4444', '#f59e0b', '#f59e0b', '#eab308', '#22c55e', '#22c55e'];

        const ctx2 = document.getElementById('dist-chart').getContext('2d');
        if (distChart) distChart.destroy();
        distChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Count',
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } },
                    x: { title: { display: true, text: 'Grade' } }
                }
            }
        });
        const descEl = document.getElementById('dist-chart-desc');
        if (descEl && data.grade_distribution) {
            const entries = Object.entries(data.grade_distribution).map(([g, c]) => `Grade ${g}: ${c}`).join(', ');
            descEl.textContent = `Grade distribution: ${entries}`;
        }
    } else {
        const chartEl = document.getElementById('dist-chart');
        if (chartEl) chartEl.style.display = 'none';
        const emptyEl = document.getElementById('dist-empty');
        if (emptyEl) emptyEl.classList.remove('hidden');
    }
}

export function generateWeaknessReport() {
    const btn = document.getElementById('weakness-btn');
    const content = document.getElementById('weakness-content');

    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    content.innerHTML = '<div class="flex items-center gap-3"><div class="w-5 h-5 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div><span class="text-sm text-slate-500">Generating weakness report...</span></div>';

    api.post('/api/analytics/weakness', {})
        .then(res => res.json())
        .then(data => {
            btn.disabled = false;
            btn.textContent = 'Generate Report';
            if (data.error) {
                content.innerHTML = `<p class="text-sm text-red-600">${escapeHtml(data.error)}</p>`;
            } else {
                const html = data.report
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n- /g, '\n<li class="ml-4">')
                    .replace(/\n(\d+)\. /g, '\n<li class="ml-4">$1. ')
                    .replace(/\n/g, '<br>');
                content.innerHTML = `<div class="text-sm text-slate-700 leading-relaxed">${html}</div>`;
            }
        })
        .catch(err => {
            btn.disabled = false;
            btn.textContent = 'Generate Report';
            content.innerHTML = `<p class="text-sm text-red-600">Error: ${escapeHtml(err.message)}</p>`;
        });
}

function renderSyllabusCoverage(coverageData) {
    const section = document.getElementById('coverage-section');
    const content = document.getElementById('coverage-content');
    if (!section || !content || !coverageData) return;

    const subjects = Object.entries(coverageData);
    if (subjects.length === 0) return;

    section.style.display = 'block';
    content.innerHTML = subjects.map(([subject, data]) => {
        const pct = data.overall || 0;
        let barColor = 'bg-green-500';
        if (pct < 30) barColor = 'bg-red-500';
        else if (pct < 60) barColor = 'bg-amber-500';

        let topicsList = '';
        if (data.topics && data.topics.length > 0) {
            topicsList = '<div class="flex flex-wrap gap-1 mt-2">' +
                data.topics.map(t => {
                    const practiced = t.practiced > 0;
                    return `<span class="px-2 py-0.5 text-xs rounded-full ${practiced ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}">${escapeHtml(t.name)}</span>`;
                }).join('') + '</div>';
        }

        return `
            <div class="p-3 border border-slate-100 rounded-lg">
                <div class="flex items-center gap-3 mb-1">
                    <span class="text-sm font-medium text-slate-700 w-48">${escapeHtml(subject)}</span>
                    <div class="flex-1 bg-slate-100 rounded-full h-2.5">
                        <div class="h-2.5 rounded-full ${barColor} transition-all" style="width: ${pct}%"></div>
                    </div>
                    <span class="text-xs font-semibold text-slate-600 w-12 text-right">${pct}%</span>
                </div>
                ${topicsList}
            </div>`;
    }).join('');
}

function loadMisconceptions() {
    api.get('/api/misconceptions')
        .then(res => res.json())
        .then(data => {
            const section = document.getElementById('misconception-section');
            const content = document.getElementById('misconception-content');
            if (!section || !content) return;

            const misconceptions = data.misconceptions || [];
            if (misconceptions.length === 0) return;

            section.style.display = 'block';

            content.innerHTML = misconceptions.map(m => {
                const trendIcon = m.trend === 'improving' ? '&#8595;' : m.trend === 'persisting' ? '&#8594;' : '&#8593;';
                const trendColor = m.trend === 'improving' ? 'text-green-600' : m.trend === 'persisting' ? 'text-amber-600' : 'text-red-600';
                const severityWidth = Math.min(m.count * 15, 100);

                return `
                    <div class="p-4 border border-slate-100 dark:border-slate-700 rounded-lg">
                        <div class="flex items-center justify-between mb-2">
                            <h4 class="text-sm font-medium text-slate-800 dark:text-slate-200">${escapeHtml(m.pattern)}</h4>
                            <div class="flex items-center gap-2">
                                <span class="text-xs text-slate-500 dark:text-slate-400">${m.count} occurrences</span>
                                <span class="text-sm ${trendColor}" title="${m.trend}">${trendIcon}</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-xs text-slate-500 dark:text-slate-400">${escapeHtml(m.subject)}</span>
                        </div>
                        <div class="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5">
                            <div class="h-1.5 rounded-full ${m.trend === 'improving' ? 'bg-green-500' : 'bg-amber-500'} transition-all" style="width: ${severityWidth}%"></div>
                        </div>
                    </div>`;
            }).join('');
        })
        .catch(err => console.error('Misconceptions load error:', err));
}

function loadPredictedGrades() {
    api.get('/api/insights')
        .then(res => res.json())
        .then(data => {
            const section = document.getElementById('predicted-grade-section');
            const content = document.getElementById('predicted-grade-content');
            if (!section || !content) return;

            const gaps = data.gaps || [];
            const subjectsWithData = gaps.filter(g => g.predicted && g.predicted !== '\u2014');
            if (subjectsWithData.length === 0) return;

            section.style.display = 'block';

            content.innerHTML = subjectsWithData.map(g => {
                const predicted = g.predicted || 0;
                const target = g.target || 0;
                const onTrack = predicted >= target;

                return `
                    <div class="flex items-center gap-4">
                        <span class="text-sm font-medium text-slate-700 dark:text-slate-300 w-40 shrink-0">${escapeHtml(g.subject)}</span>
                        <div class="flex-1">
                            <div class="relative bg-slate-100 dark:bg-slate-700 rounded-full h-4">
                                <div class="absolute h-4 rounded-full ${onTrack ? 'bg-green-500' : 'bg-amber-500'} transition-all"
                                     style="width: ${(predicted / 7) * 100}%"></div>
                                ${target > 0 ? `<div class="absolute h-6 w-0.5 bg-red-500 -top-1" style="left: ${(target / 7) * 100}%" title="Target: ${target}"></div>` : ''}
                            </div>
                        </div>
                        <span class="text-sm font-bold ${onTrack ? 'text-green-600' : 'text-amber-600'} w-8 text-right">${predicted}</span>
                        <span class="text-xs text-slate-400 dark:text-slate-500 w-20">${g.status === 'on_track' ? 'On Track' : g.status === 'close' ? 'Close' : g.status === 'behind' ? 'Behind' : ''}</span>
                    </div>`;
            }).join('');
        })
        .catch(err => console.error('Predicted grades load error:', err));
}

function loadMockReports() {
    api.get('/api/mock-reports')
        .then(res => res.json())
        .then(data => {
            const section = document.getElementById('mock-reports-section');
            const content = document.getElementById('mock-reports-content');
            if (!section || !content) return;

            const reports = data.reports || [];
            if (reports.length === 0) return;

            section.style.display = 'block';

            content.innerHTML = reports.map(r => {
                const gradeColor = r.grade >= 6 ? 'bg-green-100 text-green-700' : r.grade >= 4 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700';

                let ctHtml = '';
                if (r.command_term_breakdown && Object.keys(r.command_term_breakdown).length > 0) {
                    ctHtml = '<div class="mt-3 space-y-1">' + Object.entries(r.command_term_breakdown).map(([ct, stats]) => {
                        const pct = stats.total > 0 ? Math.round((stats.earned / stats.total) * 100) : 0;
                        let barColor = pct >= 70 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
                        return `<div class="flex items-center gap-2">
                            <span class="text-xs text-slate-500 dark:text-slate-400 w-28 shrink-0">${escapeHtml(ct)}</span>
                            <div class="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                                <div class="h-2 rounded-full ${barColor}" style="width: ${pct}%"></div>
                            </div>
                            <span class="text-xs text-slate-500 dark:text-slate-400 w-8 text-right">${pct}%</span>
                        </div>`;
                    }).join('') + '</div>';
                }

                let impHtml = '';
                if (r.improvements && r.improvements.length > 0) {
                    impHtml = `<div class="mt-3 text-xs text-slate-600 dark:text-slate-400">
                        <p class="font-medium text-slate-700 dark:text-slate-300 mb-1">Areas to improve:</p>
                        <ul class="list-disc ml-4 space-y-0.5">${r.improvements.slice(0, 3).map(i => `<li>${escapeHtml(i)}</li>`).join('')}</ul>
                    </div>`;
                }

                return `
                    <div class="p-4 border border-slate-100 dark:border-slate-700 rounded-xl">
                        <div class="flex items-center justify-between mb-2">
                            <div class="flex items-center gap-3">
                                <span class="inline-flex items-center justify-center w-10 h-10 rounded-full ${gradeColor} text-lg font-bold">${r.grade}</span>
                                <div>
                                    <h4 class="text-sm font-medium text-slate-800 dark:text-slate-200">${escapeHtml(r.subject)} (${r.level})</h4>
                                    <p class="text-xs text-slate-500 dark:text-slate-400">${r.date}</p>
                                </div>
                            </div>
                            <div class="text-right">
                                <p class="text-lg font-bold text-slate-800 dark:text-slate-200">${r.percentage}%</p>
                                <p class="text-xs text-slate-500 dark:text-slate-400">${r.total_marks_earned}/${r.total_marks_possible} marks</p>
                            </div>
                        </div>
                        ${ctHtml}
                        ${impHtml}
                    </div>`;
            }).join('');
        })
        .catch(err => console.error('Mock reports load error:', err));
}
