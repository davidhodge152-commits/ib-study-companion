/**
 * IB Lifecycle management — milestone toggles, CAS reflections,
 * EE/TOK section updates.
 */

import { api } from './api.js';

export function toggleMilestone(milestoneId, el) {
    api.post('/api/lifecycle/milestone', { milestone_id: milestoneId })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const checkbox = el.querySelector('div:first-child');
            const label = el.querySelector('span');
            if (data.completed) {
                checkbox.classList.add('bg-indigo-600', 'border-indigo-600', 'bg-purple-600', 'border-purple-600',
                                      'bg-cyan-600', 'border-cyan-600', 'bg-amber-500', 'border-amber-500');
                checkbox.classList.remove('border-slate-300');
                checkbox.innerHTML = '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';
                if (label) {
                    label.classList.add('text-slate-400', 'line-through');
                    label.classList.remove('text-slate-700', 'text-slate-600');
                }
            } else {
                checkbox.classList.remove('bg-indigo-600', 'border-indigo-600', 'bg-purple-600', 'border-purple-600',
                                         'bg-cyan-600', 'border-cyan-600', 'bg-amber-500', 'border-amber-500');
                checkbox.classList.add('border-slate-300');
                checkbox.innerHTML = '';
                if (label) {
                    label.classList.remove('text-slate-400', 'line-through');
                    label.classList.add('text-slate-700');
                }
            }
        })
        .catch(err => alert('Error: ' + err.message));
}

export function addCASReflection() {
    const strand = document.getElementById('cas-strand')?.value;
    const title = document.getElementById('cas-title')?.value?.trim();
    const description = document.getElementById('cas-description')?.value?.trim();
    const outcome = document.getElementById('cas-outcome')?.value;
    const hours = parseFloat(document.getElementById('cas-hours')?.value) || 0;

    if (!strand || !title) {
        alert('Please select a strand and enter a title.');
        return;
    }

    api.post('/api/lifecycle/cas', { strand, title, description, learning_outcome: outcome, hours })
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            location.reload();
        })
        .catch(err => alert('Error: ' + err.message));
}

export function updateLifecycleSection(section) {
    let payload = { section };

    if (section === 'ee') {
        payload.subject = document.getElementById('ee-subject')?.value || '';
        payload.research_question = document.getElementById('ee-rq')?.value || '';
        payload.supervisor = document.getElementById('ee-supervisor')?.value || '';
    } else if (section === 'tok') {
        payload.essay_title = document.getElementById('tok-title')?.value || '';
        payload.exhibition_theme = document.getElementById('tok-exhibition')?.value || '';
    }

    api.post('/api/lifecycle/update', payload)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const btn = event?.target;
            if (btn) {
                const origText = btn.textContent;
                btn.textContent = 'Saved!';
                btn.classList.add('bg-green-600');
                setTimeout(() => {
                    btn.textContent = origText;
                    btn.classList.remove('bg-green-600');
                }, 1500);
            }
        })
        .catch(err => alert('Error: ' + err.message));
}
