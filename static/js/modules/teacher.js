/**
 * Teacher Dashboard Module
 */
import { api } from './api.js';

window.showCreateClassModal = () => document.getElementById('create-class-modal')?.classList.remove('hidden');
window.showAssignmentModal = () => document.getElementById('assignment-modal')?.classList.remove('hidden');
window.hideModal = (id) => document.getElementById(id)?.classList.add('hidden');

window.createClass = async function() {
    const name = document.getElementById('class-name').value.trim();
    const subject = document.getElementById('class-subject').value.trim();
    const level = document.getElementById('class-level').value;
    if (!name) return;
    const res = await api('/teacher/classes', {
        method: 'POST',
        body: JSON.stringify({ name, subject, level }),
    });
    if (res.success) {
        alert(`Class created! Join code: ${res.join_code}`);
        location.reload();
    }
};

window.createAssignment = async function() {
    const classId = new URLSearchParams(window.location.search).get('class_id')
        || window.location.pathname.split('/').pop();
    const title = document.getElementById('assign-title').value.trim();
    const description = document.getElementById('assign-desc').value.trim();
    const dueDate = document.getElementById('assign-due').value;
    if (!title) return;
    const res = await api('/teacher/assignments', {
        method: 'POST',
        body: JSON.stringify({ class_id: parseInt(classId), title, description, due_date: dueDate }),
    });
    if (res.success) {
        hideModal('assignment-modal');
        location.reload();
    }
};
