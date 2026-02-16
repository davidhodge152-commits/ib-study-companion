/**
 * Study planner — generate plan, toggle task completion.
 */

import { api } from './api.js';

export function generatePlan() {
    const btn = document.getElementById('generate-plan-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Generating...';
    }

    api.post('/api/planner/generate', {})
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = 'Generate Plan';
                }
                return;
            }
            location.reload();
        })
        .catch(err => {
            alert('Error: ' + err.message);
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Generate Plan';
            }
        });
}

export function togglePlanTask(dayDate, taskIndex, el) {
    api.post('/api/planner/complete', { date: dayDate, task_index: taskIndex })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const checkbox = el.querySelector('div:first-child');
            const label = el.querySelector('.flex-1 span:first-child');

            if (data.completed) {
                checkbox.classList.add('bg-indigo-600', 'border-indigo-600');
                checkbox.classList.remove('border-slate-300');
                checkbox.innerHTML = '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';
                if (label) {
                    label.classList.add('text-slate-400', 'line-through');
                    label.classList.remove('text-slate-700');
                }
            } else {
                checkbox.classList.remove('bg-indigo-600', 'border-indigo-600');
                checkbox.classList.add('border-slate-300');
                checkbox.innerHTML = '';
                if (label) {
                    label.classList.remove('text-slate-400', 'line-through');
                    label.classList.add('text-slate-700');
                }
            }

            const dayCard = el.closest('.bg-white');
            if (dayCard) {
                const allCheckboxes = dayCard.querySelectorAll('[onclick^="togglePlanTask"]');
                const completedCount = dayCard.querySelectorAll('.bg-indigo-600.border-indigo-600').length;
                const counterEl = dayCard.querySelector('.text-xs.font-medium.text-slate-500');
                if (counterEl) {
                    counterEl.textContent = `${completedCount}/${allCheckboxes.length} done`;
                }
            }
        })
        .catch(err => alert('Error: ' + err.message));
}
