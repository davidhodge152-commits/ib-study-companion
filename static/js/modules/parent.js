/**
 * Parent portal settings — toggle sharing, copy link, privacy.
 */

import { api } from './api.js';

export function toggleParentSharing() {
    const btn = document.getElementById('parent-toggle-btn');
    const isEnabled = btn.classList.contains('bg-indigo-600');
    const action = isEnabled ? 'disable' : 'enable';

    api.post('/api/parent/toggle', { action })
        .then(res => res.json())
        .then(data => {
            const linkSection = document.getElementById('parent-link-section');
            const privacySection = document.getElementById('privacy-settings');
            const knob = btn.querySelector('span');

            if (data.enabled) {
                btn.classList.remove('bg-slate-300');
                btn.classList.add('bg-indigo-600');
                knob.classList.remove('translate-x-1');
                knob.classList.add('translate-x-6');
                linkSection.classList.remove('hidden');
                privacySection.classList.remove('hidden');
                if (data.token) {
                    document.getElementById('parent-link-input').value =
                        window.location.origin + '/parent/' + data.token;
                }
            } else {
                btn.classList.remove('bg-indigo-600');
                btn.classList.add('bg-slate-300');
                knob.classList.remove('translate-x-6');
                knob.classList.add('translate-x-1');
                linkSection.classList.add('hidden');
                privacySection.classList.add('hidden');
            }
        })
        .catch(err => alert('Error: ' + err.message));
}

export function copyParentLink() {
    const input = document.getElementById('parent-link-input');
    if (!input || !input.value) return;

    navigator.clipboard.writeText(input.value).then(() => {
        const btn = event?.target;
        if (btn) {
            const origText = btn.textContent;
            btn.textContent = 'Copied!';
            setTimeout(() => { btn.textContent = origText; }, 1500);
        }
    }).catch(() => {
        input.select();
        document.execCommand('copy');
    });
}

export function regenerateToken() {
    if (!confirm('Regenerate the link? The old link will stop working.')) return;

    api.post('/api/parent/toggle', { action: 'regenerate' })
        .then(res => res.json())
        .then(data => {
            if (data.token) {
                document.getElementById('parent-link-input').value =
                    window.location.origin + '/parent/' + data.token;
            }
        })
        .catch(err => alert('Error: ' + err.message));
}

export function savePrivacySettings() {
    const payload = {
        student_display_name: document.getElementById('parent-display-name')?.value || '',
        show_subject_grades: document.getElementById('priv-grades')?.checked || false,
        show_recent_activity: document.getElementById('priv-activity')?.checked || false,
        show_study_consistency: document.getElementById('priv-consistency')?.checked || false,
        show_command_term_stats: document.getElementById('priv-ct')?.checked || false,
        show_insights: document.getElementById('priv-insights')?.checked || false,
        show_exam_countdown: document.getElementById('priv-countdown')?.checked || false,
    };

    api.post('/api/parent/privacy', payload)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const btn = event?.target;
                if (btn) {
                    const origText = btn.textContent;
                    btn.textContent = 'Saved!';
                    btn.classList.replace('bg-indigo-600', 'bg-green-600');
                    setTimeout(() => {
                        btn.textContent = origText;
                        btn.classList.replace('bg-green-600', 'bg-indigo-600');
                    }, 1500);
                }
            }
        })
        .catch(err => alert('Error: ' + err.message));
}
