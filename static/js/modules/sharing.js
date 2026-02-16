/**
 * Question sharing — share single question, export session, import questions.
 */

import { api } from './api.js';
import { escapeHtml, showToast, copyToClipboard } from './utils.js';
import { studyState, showSection, displayQuestion } from './study.js';

export function shareQuestion() {
    if (!studyState.questions.length) return;
    const q = studyState.questions[studyState.index];
    if (!q) return;

    const shareData = {
        ib_study_companion_version: '1.0',
        type: 'single_question',
        question_text: q.question_text,
        command_term: q.command_term,
        marks: q.marks,
        topic: q.topic,
        model_answer: q.model_answer,
        subject: studyState.subject,
        level: studyState.level,
    };

    const jsonStr = JSON.stringify(shareData, null, 2);

    if (navigator.share) {
        navigator.share({
            title: `IB ${shareData.subject} Question`,
            text: jsonStr,
        }).catch(() => copyToClipboard(jsonStr));
    } else {
        copyToClipboard(jsonStr);
    }
}

export function exportSessionQuestions() {
    if (!studyState.questions.length) {
        showToast('No questions to export');
        return;
    }

    const exportData = {
        ib_study_companion_version: '1.0',
        type: 'question_set',
        subject: studyState.subject,
        level: studyState.level,
        questions: studyState.questions.map(q => ({
            question_text: q.question_text,
            command_term: q.command_term,
            marks: q.marks,
            topic: q.topic || '',
            model_answer: q.model_answer || '',
        })),
    };

    api.post('/api/questions/export', {
        title: `${exportData.subject} Practice Session`,
        description: `${exportData.questions.length} questions`,
        questions: exportData.questions,
        subject: exportData.subject,
        level: exportData.level,
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const jsonStr = JSON.stringify(data.json_data, null, 2);
            copyToClipboard(jsonStr);
        }
    })
    .catch(() => {
        copyToClipboard(JSON.stringify(exportData, null, 2));
    });
}

export function importQuestions() {
    const input = document.getElementById('import-json-input');
    if (!input || !input.value.trim()) {
        showToast('Please paste question JSON first');
        return;
    }

    let data;
    try {
        data = JSON.parse(input.value.trim());
    } catch {
        showToast('Invalid JSON format');
        return;
    }

    let questions = [];
    let subject = '';
    let level = 'HL';

    if (data.type === 'single_question') {
        questions = [{
            question_text: data.question_text,
            command_term: data.command_term,
            marks: data.marks,
            topic: data.topic || '',
            model_answer: data.model_answer || '',
        }];
        subject = data.subject || '';
        level = data.level || 'HL';
    } else if (data.questions && Array.isArray(data.questions)) {
        questions = data.questions;
        subject = data.subject || '';
        level = data.level || 'HL';
    }

    if (!questions.length) {
        showToast('No valid questions found');
        return;
    }

    api.post('/api/questions/import', {
        title: data.title || 'Imported Questions',
        description: data.description || '',
        author: data.author || 'Unknown',
        subject: subject,
        topic: data.topic || '',
        level: level,
        questions: questions,
    })
    .then(res => res.json())
    .then(result => {
        if (result.success) {
            showToast(`Imported ${result.question_count} questions!`);
            studyState.questions = questions;
            studyState.index = 0;
            studyState.subject = subject;
            studyState.level = level;
            showSection('study-question');
            displayQuestion();
            input.value = '';
            document.getElementById('study-import-panel').classList.add('hidden');
        } else {
            showToast(result.error || 'Import failed');
        }
    })
    .catch(() => showToast('Import failed'));
}
