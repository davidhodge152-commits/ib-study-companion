/**
 * Teacher Analytics — Chart.js visualizations for class detail page.
 */
import { api } from './api.js';

// Extract class ID from the URL: /teacher/classes/<id>
const pathParts = window.location.pathname.split('/');
const classId = pathParts[pathParts.length - 1];

async function loadGradeDistribution() {
    const canvas = document.getElementById('grade-dist-chart');
    if (!canvas || !classId) return;

    const res = await api(`/api/teacher/class/${classId}/grade-distribution`);
    if (!res.grade_distribution || res.grade_distribution.length === 0) {
        canvas.parentElement.querySelector('h2').insertAdjacentHTML(
            'afterend', '<p class="text-sm text-slate-500">No grade data yet</p>'
        );
        return;
    }

    const counts = [0, 0, 0, 0, 0, 0, 0];
    for (const row of res.grade_distribution) {
        if (row.grade >= 1 && row.grade <= 7) {
            counts[row.grade - 1] += row.cnt;
        }
    }

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: ['1', '2', '3', '4', '5', '6', '7'],
            datasets: [{
                label: 'Count',
                data: counts,
                backgroundColor: [
                    '#ef4444', '#f97316', '#eab308', '#84cc16',
                    '#22c55e', '#06b6d4', '#6366f1'
                ],
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
        },
    });
}

async function loadCommandTermBreakdown() {
    const canvas = document.getElementById('command-term-chart');
    if (!canvas || !classId) return;

    const res = await api(`/api/teacher/class/${classId}/command-term-breakdown`);
    if (!res.command_term_breakdown || res.command_term_breakdown.length === 0) {
        canvas.parentElement.querySelector('h2').insertAdjacentHTML(
            'afterend', '<p class="text-sm text-slate-500">No command term data yet</p>'
        );
        return;
    }

    const labels = res.command_term_breakdown.map(r => r.command_term);
    const data = res.command_term_breakdown.map(r => Math.round(r.avg_pct));

    new Chart(canvas, {
        type: 'radar',
        data: {
            labels,
            datasets: [{
                label: 'Avg %',
                data,
                backgroundColor: 'rgba(99, 102, 241, 0.2)',
                borderColor: '#6366f1',
                pointBackgroundColor: '#6366f1',
            }],
        },
        options: {
            responsive: true,
            scales: { r: { beginAtZero: true, max: 100 } },
        },
    });
}

async function loadActivityHeatmap() {
    const container = document.getElementById('activity-heatmap');
    if (!container || !classId) return;

    const res = await api(`/api/teacher/class/${classId}/activity-heatmap`);
    if (!res.activity_heatmap || res.activity_heatmap.length === 0) {
        container.innerHTML = '<p class="text-sm text-slate-500">No activity data in the last 30 days</p>';
        return;
    }

    // Group by student
    const students = {};
    for (const row of res.activity_heatmap) {
        if (!students[row.name]) students[row.name] = {};
        students[row.name][row.date] = row.minutes;
    }

    // Get unique dates
    const dates = [...new Set(res.activity_heatmap.map(r => r.date))].sort();

    let html = '<table class="w-full text-xs"><thead><tr><th class="text-left pb-1">Student</th>';
    for (const d of dates) {
        html += `<th class="pb-1 px-0.5">${d.slice(5)}</th>`;
    }
    html += '</tr></thead><tbody>';

    for (const [name, days] of Object.entries(students)) {
        html += `<tr><td class="py-1 font-medium pr-2 whitespace-nowrap">${name}</td>`;
        for (const d of dates) {
            const mins = days[d] || 0;
            const intensity = mins === 0 ? 'bg-slate-100 dark:bg-slate-700'
                : mins < 30 ? 'bg-green-200 dark:bg-green-900'
                : mins < 60 ? 'bg-green-400 dark:bg-green-700'
                : 'bg-green-600 dark:bg-green-500';
            html += `<td class="px-0.5"><div class="w-5 h-5 rounded-sm ${intensity}" title="${name}: ${mins}m on ${d}"></div></td>`;
        }
        html += '</tr>';
    }
    html += '</tbody></table>';
    container.innerHTML = html;
}

// Load SOS alerts for teacher dashboard
async function loadSOSAlerts() {
    const section = document.getElementById('sos-alerts-section');
    const list = document.getElementById('sos-alerts-list');
    if (!section || !list) return;

    const res = await api('/api/teacher/sos-alerts');
    if (!res.alerts || res.alerts.length === 0) return;

    section.classList.remove('hidden');
    list.innerHTML = res.alerts.map(a => `
        <div class="flex items-center justify-between p-2 bg-white dark:bg-slate-800 rounded-lg">
            <div>
                <span class="font-medium text-sm">${a.student_name}</span>
                <span class="text-xs text-slate-500 ml-2">${a.subject} — ${a.topic}</span>
            </div>
            <span class="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full">${a.failure_count} failures</span>
        </div>
    `).join('');
}

// Init
loadGradeDistribution();
loadCommandTermBreakdown();
loadActivityHeatmap();
loadSOSAlerts();
