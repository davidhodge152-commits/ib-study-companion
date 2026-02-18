/**
 * Study module — three-mode system, question flow, grading, results,
 * session summary, exam timer, speech-to-text, hints, answer upload,
 * subject topic sync.
 */

import { api } from './api.js';
import { escapeHtml, COMMAND_TERM_DEFINITIONS } from './utils.js';
import { requestNotificationPermission } from './notifications.js';

// ── Shared study state (exported for sharing.js) ─────────────────

export const studyState = {
    questions: [],
    index: 0,
    subject: '',
    topic: '',
    level: 'HL',
    mode: 'smart',
};

let responseMode = 'full';
let examTimerInterval = null;
let examTimeRemaining = 0;

// Session tracking
let sessionScores = [];
let sessionXpEarned = 0;
let sessionNewBadges = [];
let sessionFlashcardsCreated = 0;
let sessionHintsUsed = 0;
let sessionGradeResults = [];
let examPaperInfo = null;

const STUDY_SECTIONS = [
    'study-mode-select', 'study-setup', 'study-loading',
    'study-question', 'grading-loading', 'study-result', 'study-error',
    'study-session-summary'
];

export function showSection(id) {
    STUDY_SECTIONS.forEach(s => {
        const el = document.getElementById(s);
        if (!el) return;
        if (s !== id) {
            el.classList.add('hidden');
            el.classList.remove('animate-fade-in');
        } else {
            el.classList.remove('hidden');
            el.classList.add('animate-fade-in');
            el.addEventListener('animationend', () => el.classList.remove('animate-fade-in'), { once: true });
        }
    });
}

// ── Mode selection ───────────────────────────────────────────────

export function selectMode(mode) {
    studyState.mode = mode;

    const titles = {
        smart: 'Smart Practice',
        command_term: 'Command Term Trainer',
        exam_sim: 'Exam Simulation',
    };
    const descriptions = {
        smart: 'AI-recommended subject and focus area based on your gaps.',
        command_term: 'Master specific IB command terms — where students lose the most marks.',
        exam_sim: 'Timed exam conditions with 5+ questions. Build exam stamina.',
    };

    document.getElementById('setup-title').textContent = titles[mode];
    document.getElementById('setup-description').textContent = descriptions[mode];

    const ctGroup = document.getElementById('ct-select-group');
    const timeGroup = document.getElementById('time-limit-group');
    const countGroup = document.getElementById('count-group');
    const smartBanner = document.getElementById('smart-rec-banner');
    const ctDefCard = document.getElementById('ct-definition-card');

    ctGroup.classList.toggle('hidden', mode !== 'command_term');
    timeGroup.classList.toggle('hidden', mode !== 'exam_sim');
    countGroup.classList.toggle('hidden', mode === 'exam_sim');
    ctDefCard.classList.add('hidden');

    if (mode === 'smart' && window.RECOMMENDATION && window.RECOMMENDATION.subject) {
        smartBanner.classList.remove('hidden');
        document.getElementById('smart-rec-text').textContent =
            `Recommended: ${window.RECOMMENDATION.reason}`;
        const subjectEl = document.getElementById('study-subject');
        if (subjectEl) {
            for (const opt of subjectEl.options) {
                if (opt.value === window.RECOMMENDATION.subject) {
                    opt.selected = true;
                    break;
                }
            }
        }
    } else {
        smartBanner.classList.add('hidden');
    }

    showSection('study-setup');
}

export function backToModes() {
    showSection('study-mode-select');
}

export function onCommandTermChange() {
    const ct = document.getElementById('study-command-term').value;
    const card = document.getElementById('ct-definition-card');

    if (ct && COMMAND_TERM_DEFINITIONS[ct]) {
        const def = COMMAND_TERM_DEFINITIONS[ct];
        document.getElementById('ct-def-title').textContent = `${ct} (${def.marks})`;
        document.getElementById('ct-def-body').textContent = def.expect;
        document.getElementById('ct-def-mistake').textContent = `Common mistake: ${def.common_mistake}`;
        card.classList.remove('hidden');
    } else {
        card.classList.add('hidden');
    }
}

// ── Generate questions ───────────────────────────────────────────

export function generateStudy() {
    const subjectEl = document.getElementById('study-subject');
    const topicEl = document.getElementById('study-topic');
    const topicSelectEl = document.getElementById('study-topic-select');

    if (!subjectEl || !topicEl) return;

    studyState.subject = subjectEl.value;
    studyState.level = subjectEl.selectedOptions[0]?.dataset?.level || 'HL';

    let topic = '';
    if (topicSelectEl && !topicSelectEl.classList.contains('hidden') && topicSelectEl.value && topicSelectEl.value !== '__custom__') {
        topic = topicSelectEl.value;
    } else {
        topic = topicEl.value.trim();
    }

    if (!topic) {
        if (topicSelectEl && !topicSelectEl.classList.contains('hidden')) {
            topicSelectEl.classList.add('border-red-400');
        } else {
            topicEl.focus();
            topicEl.classList.add('border-red-400');
        }
        return;
    }
    topicEl.classList.remove('border-red-400');
    if (topicSelectEl) topicSelectEl.classList.remove('border-red-400');
    studyState.topic = topic;

    const count = studyState.mode === 'exam_sim' ? 5 : parseInt(document.getElementById('study-count').value);
    const style = studyState.mode === 'command_term'
        ? (document.getElementById('study-command-term').value || 'mixed')
        : 'mixed';

    // Reset session tracking
    sessionScores = [];
    sessionXpEarned = 0;
    sessionNewBadges = [];
    sessionFlashcardsCreated = 0;
    sessionHintsUsed = 0;
    sessionGradeResults = [];
    examPaperInfo = null;

    showSection('study-loading');

    api.post('/api/study/generate', {
        subject: studyState.subject,
        topic,
        count,
        level: studyState.level,
        mode: studyState.mode,
        style,
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            document.getElementById('error-message').textContent = data.error;
            showSection('study-error');
            return;
        }
        studyState.questions = data.questions;
        studyState.index = 0;
        examPaperInfo = data.exam_paper_info || null;

        if (studyState.mode === 'exam_sim') {
            const minutes = parseInt(document.getElementById('study-time-limit').value) || 20;
            startExamTimer(minutes);
        }

        displayQuestion();
    })
    .catch(err => {
        document.getElementById('error-message').textContent = err.message;
        showSection('study-error');
    });
}

// ── Response mode ────────────────────────────────────────────────

export function selectResponseMode(mode) {
    responseMode = mode;
    const buttons = document.querySelectorAll('.response-mode-btn');
    buttons.forEach(btn => {
        btn.classList.remove('border-indigo-500', 'border-amber-500', 'border-emerald-500');
        btn.classList.add('border-slate-200');
    });

    const colors = { full: 'border-indigo-500', bullet: 'border-amber-500', model: 'border-emerald-500' };
    const idx = { full: 0, bullet: 1, model: 2 };
    if (buttons[idx[mode]]) {
        buttons[idx[mode]].classList.remove('border-slate-200');
        buttons[idx[mode]].classList.add(colors[mode]);
    }

    const answerSection = document.getElementById('answer-section');
    const modelSection = document.getElementById('model-answer-section');
    const submitBtn = document.getElementById('submit-btn');
    const answerInput = document.getElementById('answer-input');

    if (mode === 'model') {
        answerSection.classList.add('hidden');
        submitBtn.textContent = 'Next Question';
        submitBtn.onclick = nextQuestion;
        const q = studyState.questions[studyState.index];
        if (q && q.model_answer) {
            document.getElementById('model-answer-text').textContent = q.model_answer;
            modelSection.classList.remove('hidden');
        } else {
            document.getElementById('model-answer-text').textContent = 'Model answer not available for this question.';
            modelSection.classList.remove('hidden');
        }
    } else {
        answerSection.classList.remove('hidden');
        modelSection.classList.add('hidden');
        submitBtn.textContent = 'Submit Answer';
        submitBtn.onclick = submitAnswer;
        if (mode === 'bullet') {
            answerInput.placeholder = 'List your key points:\n- Point 1\n- Point 2\n- Point 3';
            answerInput.rows = 6;
        } else {
            answerInput.placeholder = 'Write your answer here...';
            answerInput.rows = 8;
        }
        answerInput.focus();
    }
}

// ── Display question ─────────────────────────────────────────────

export function displayQuestion() {
    if (studyState.index >= studyState.questions.length) {
        resetStudy();
        return;
    }

    const q = studyState.questions[studyState.index];
    document.getElementById('q-current').textContent = studyState.index + 1;
    document.getElementById('q-total').textContent = studyState.questions.length;
    document.getElementById('q-badge').textContent = `${q.marks} marks`;
    document.getElementById('q-command-term').textContent = q.command_term;
    document.getElementById('q-marks').textContent = `${q.marks} marks`;
    document.getElementById('q-text').textContent = q.question_text;
    document.getElementById('answer-input').value = '';

    // Exam paper banner
    const examBanner = document.getElementById('exam-paper-banner');
    const examText = document.getElementById('exam-paper-text');
    if (examBanner && examPaperInfo && examPaperInfo.papers && examPaperInfo.papers.length > 0) {
        const totalMarks = examPaperInfo.total_marks;
        const paperNames = examPaperInfo.papers.map(p => `${p.name} (${p.description})`).join(' | ');
        examText.textContent = `Exam Simulation: ${paperNames} \u2014 Total: ${totalMarks} marks`;
        examBanner.classList.remove('hidden');
    } else if (examBanner) {
        examBanner.classList.add('hidden');
    }

    // Reset response mode UI
    responseMode = 'full';
    const answerSection = document.getElementById('answer-section');
    const modelSection = document.getElementById('model-answer-section');
    const submitBtn = document.getElementById('submit-btn');
    if (answerSection) answerSection.classList.remove('hidden');
    if (modelSection) modelSection.classList.add('hidden');
    if (submitBtn) {
        submitBtn.textContent = 'Submit Answer';
        submitBtn.onclick = submitAnswer;
    }

    const buttons = document.querySelectorAll('.response-mode-btn');
    buttons.forEach((btn) => {
        btn.classList.remove('border-indigo-500', 'border-amber-500', 'border-emerald-500');
        btn.classList.add('border-slate-200');
    });
    if (buttons[0]) {
        buttons[0].classList.remove('border-slate-200');
        buttons[0].classList.add('border-indigo-500');
    }

    const answerInput = document.getElementById('answer-input');
    if (answerInput) {
        answerInput.placeholder = 'Write your answer here...';
        answerInput.rows = 8;
    }

    // Reset hint state
    currentHintLevel = 0;
    const hintPanel = document.getElementById('hint-panel');
    const hintContent = document.getElementById('hint-content');
    const hintBtn = document.getElementById('hint-btn');
    const hintCount = document.getElementById('hint-count');
    if (hintPanel) hintPanel.classList.add('hidden');
    if (hintContent) hintContent.innerHTML = '';
    if (hintBtn) { hintBtn.disabled = false; hintBtn.textContent = 'Need a hint?'; }
    if (hintCount) hintCount.textContent = '';

    showSection('study-question');
    if (answerInput) answerInput.focus();
}

// ── Submit & grade answer ────────────────────────────────────────

export function submitAnswer() {
    const answer = document.getElementById('answer-input').value.trim();
    if (!answer) {
        document.getElementById('answer-input').focus();
        return;
    }

    const q = studyState.questions[studyState.index];
    showSection('grading-loading');

    api.post('/api/study/grade', {
        question: q.question_text,
        answer: answer,
        subject: studyState.subject,
        topic: studyState.topic,
        marks: q.marks,
        command_term: q.command_term,
        level: studyState.level,
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            document.getElementById('error-message').textContent = data.error;
            showSection('study-error');
            return;
        }
        displayEnhancedResult(data);
    })
    .catch(err => {
        document.getElementById('error-message').textContent = err.message;
        showSection('study-error');
    });
}

// ── Display enhanced result ──────────────────────────────────────

function displayEnhancedResult(data) {
    const badge = document.getElementById('result-grade-badge');
    badge.textContent = data.grade;
    badge.className = 'inline-flex items-center justify-center w-12 h-12 rounded-full text-lg font-bold ';
    if (data.grade >= 6) badge.className += 'bg-green-100 text-green-700';
    else if (data.grade >= 4) badge.className += 'bg-yellow-100 text-yellow-700';
    else badge.className += 'bg-red-100 text-red-700';

    document.getElementById('result-mark').textContent = `${data.mark_earned}/${data.mark_total}`;
    document.getElementById('result-percentage').textContent = `${data.percentage}%`;

    const bar = document.getElementById('result-bar');
    bar.style.width = '0%';
    if (data.percentage >= 70) bar.className = 'h-3 rounded-full transition-all duration-700 bg-green-500';
    else if (data.percentage >= 50) bar.className = 'h-3 rounded-full transition-all duration-700 bg-yellow-500';
    else bar.className = 'h-3 rounded-full transition-all duration-700 bg-red-500';
    setTimeout(() => { bar.style.width = data.percentage + '%'; }, 100);

    // Target context
    const targetPanel = document.getElementById('target-context-panel');
    const targetText = document.getElementById('target-context-text');
    if (data.target_grade) {
        const targetPct = data.target_pct || 60;
        const gap = data.grade_gap || 0;
        if (gap > 0) {
            targetText.textContent = `Your target is Grade ${data.target_grade} (needs ~${targetPct}%). You scored ${data.percentage}%. Gap: ${gap} percentage points.`;
        } else {
            targetText.textContent = `Your target is Grade ${data.target_grade} (needs ~${targetPct}%). You scored ${data.percentage}% \u2014 above target!`;
        }
        targetPanel.classList.remove('hidden');
    } else {
        targetPanel.classList.add('hidden');
    }

    // Command term check
    const ctPanel = document.getElementById('ct-check-panel');
    const ctText = document.getElementById('ct-check-text');
    if (data.command_term_check) {
        ctText.textContent = data.command_term_check;
        ctPanel.classList.remove('hidden');
    } else {
        ctPanel.classList.add('hidden');
    }

    // Strengths
    document.getElementById('result-strengths').innerHTML = data.strengths.map(s =>
        `<li class="flex items-start gap-2"><span class="text-green-500 mt-0.5">&#10003;</span> ${escapeHtml(s)}</li>`
    ).join('');

    // Improvements
    document.getElementById('result-improvements').innerHTML = data.improvements.map(s =>
        `<li class="flex items-start gap-2"><span class="text-amber-500 mt-0.5">&#9679;</span> ${escapeHtml(s)}</li>`
    ).join('');

    // Tip & Commentary
    document.getElementById('result-tip').textContent = data.examiner_tip;
    document.getElementById('result-commentary').textContent = data.full_commentary;

    // Model answer
    const modelPanel = document.getElementById('result-model-answer');
    const modelText = document.getElementById('result-model-text');
    const modelAnswer = data.model_answer || (studyState.questions[studyState.index] && studyState.questions[studyState.index].model_answer) || '';
    if (modelAnswer) {
        modelText.textContent = modelAnswer;
        modelPanel.classList.remove('hidden');
    } else {
        modelPanel.classList.add('hidden');
    }

    // XP & Gamification
    const xpPanel = document.getElementById('result-xp-panel');
    if (xpPanel && data.xp_earned) {
        sessionScores.push(data.percentage);
        sessionXpEarned += data.xp_earned;
        if (data.new_badges && data.new_badges.length > 0) {
            sessionNewBadges.push(...data.new_badges);
        }
        if (data.flashcard_created) {
            sessionFlashcardsCreated++;
        }
        sessionGradeResults.push({
            question: studyState.questions[studyState.index]?.question_text || '',
            marks: data.mark_total,
            mark_earned: data.mark_earned,
            percentage: data.percentage,
            command_term: studyState.questions[studyState.index]?.command_term || '',
            improvements: data.improvements || [],
        });

        let xpHtml = `<span class="text-indigo-700 font-bold">+${data.xp_earned} XP</span>`;
        if (data.new_badges && data.new_badges.length > 0) {
            xpHtml += data.new_badges.map(b => ` <span class="ml-2 px-2 py-0.5 text-xs font-bold rounded-full bg-amber-100 text-amber-700">&#127942; ${escapeHtml(b)}</span>`).join('');
        }
        if (data.flashcard_created) {
            xpHtml += ' <span class="ml-2 text-xs text-violet-600">&#128196; Flashcard created</span>';
        }
        document.getElementById('result-xp-content').innerHTML = xpHtml;
        xpPanel.classList.remove('hidden');
    } else if (xpPanel) {
        xpPanel.classList.add('hidden');
    }

    // Next button text
    const nextBtn = document.getElementById('next-btn');
    if (studyState.index >= studyState.questions.length - 1) {
        nextBtn.textContent = 'Finish Session';
    } else {
        nextBtn.textContent = 'Next Question';
    }

    // Request notification permission after first grade
    requestNotificationPermission();

    showSection('study-result');
}

// ── Navigation ───────────────────────────────────────────────────

export function nextQuestion() {
    studyState.index++;
    if (studyState.index >= studyState.questions.length) {
        resetStudy();
    } else {
        displayQuestion();
    }
}

export function skipQuestion() {
    nextQuestion();
}

function resetStudy() {
    stopExamTimer();

    if (sessionScores.length > 0) {
        showSessionSummary();
        return;
    }

    studyState.questions = [];
    studyState.index = 0;
    showSection('study-mode-select');
}

// ── Session summary ──────────────────────────────────────────────

function showSessionSummary() {
    const container = document.getElementById('session-summary-content');
    if (!container) {
        studyState.questions = [];
        studyState.index = 0;
        sessionScores = [];
        sessionXpEarned = 0;
        sessionNewBadges = [];
        sessionFlashcardsCreated = 0;
        sessionHintsUsed = 0;
        showSection('study-mode-select');
        return;
    }

    const totalQuestions = studyState.questions.length;
    const answered = sessionScores.length;
    const avgScore = answered > 0
        ? Math.round(sessionScores.reduce((a, b) => a + b, 0) / sessionScores.length)
        : 0;
    const bestScore = answered > 0 ? Math.max(...sessionScores) : 0;

    let perfMsg = '';
    let perfColor = '';
    if (avgScore >= 80) { perfMsg = 'Outstanding performance!'; perfColor = 'text-green-700'; }
    else if (avgScore >= 60) { perfMsg = 'Solid work \u2014 keep building on this.'; perfColor = 'text-blue-700'; }
    else if (avgScore >= 40) { perfMsg = 'Good effort \u2014 review weak areas and try again.'; perfColor = 'text-amber-700'; }
    else { perfMsg = 'Keep practicing \u2014 every attempt builds understanding.'; perfColor = 'text-red-700'; }

    let html = `
        <div class="text-center mb-6">
            <div class="text-5xl font-bold ${perfColor} mb-2">${avgScore}%</div>
            <p class="text-sm text-slate-500">${perfMsg}</p>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
            <div class="bg-slate-50 dark:bg-slate-700 rounded-xl p-4 text-center">
                <div class="text-2xl font-bold text-slate-800 dark:text-slate-200">${answered}/${totalQuestions}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">Questions Answered</div>
            </div>
            <div class="bg-slate-50 dark:bg-slate-700 rounded-xl p-4 text-center">
                <div class="text-2xl font-bold text-slate-800 dark:text-slate-200">${bestScore}%</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">Best Score</div>
            </div>
            <div class="bg-indigo-50 dark:bg-indigo-900/30 rounded-xl p-4 text-center">
                <div class="text-2xl font-bold text-indigo-600 dark:text-indigo-400">+${sessionXpEarned}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">XP Earned</div>
            </div>
            <div class="bg-violet-50 dark:bg-violet-900/30 rounded-xl p-4 text-center">
                <div class="text-2xl font-bold text-violet-600 dark:text-violet-400">${sessionFlashcardsCreated}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">Flashcards Created</div>
            </div>
        </div>`;

    if (sessionNewBadges.length > 0) {
        html += `<div class="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
            <h3 class="text-sm font-semibold text-amber-800 dark:text-amber-400 mb-2">&#127942; Badges Earned!</h3>
            <div class="flex flex-wrap gap-2">${sessionNewBadges.map(b =>
                `<span class="px-3 py-1 bg-amber-100 dark:bg-amber-800 text-amber-800 dark:text-amber-200 text-sm font-medium rounded-full">${escapeHtml(b)}</span>`
            ).join('')}</div>
        </div>`;
    }

    if (sessionScores.length > 1) {
        html += `<div class="mb-6">
            <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Score Breakdown</h3>
            <div class="space-y-2">${sessionScores.map((score, i) => {
                let barColor = score >= 70 ? 'bg-green-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500';
                return `<div class="flex items-center gap-3">
                    <span class="text-xs text-slate-500 dark:text-slate-400 w-8">Q${i + 1}</span>
                    <div class="flex-1 bg-slate-100 dark:bg-slate-700 rounded-full h-2.5">
                        <div class="h-2.5 rounded-full ${barColor} transition-all" style="width: ${score}%"></div>
                    </div>
                    <span class="text-xs font-semibold text-slate-600 dark:text-slate-300 w-10 text-right">${score}%</span>
                </div>`;
            }).join('')}</div>
        </div>`;
    }

    const weakestScore = Math.min(...sessionScores);
    const weakestIdx = sessionScores.indexOf(weakestScore);
    if (weakestScore < 60 && studyState.questions[weakestIdx]) {
        const weakQ = studyState.questions[weakestIdx];
        html += `<div class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
            <h3 class="text-sm font-semibold text-blue-800 dark:text-blue-400 mb-1">Focus Next Time</h3>
            <p class="text-sm text-blue-700 dark:text-blue-300">Practice more <strong>${escapeHtml(weakQ.command_term)}</strong> questions \u2014 you scored ${weakestScore}% on Q${weakestIdx + 1}.</p>
        </div>`;
    }

    container.innerHTML = html;

    // Auto-create mock report for exam sim mode
    if (studyState.mode === 'exam_sim' && sessionGradeResults.length > 0) {
        api.post('/api/mock-reports/create', {
            subject: studyState.subject,
            level: studyState.level,
            results: sessionGradeResults,
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const reportBanner = document.createElement('div');
                reportBanner.className = 'mt-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl';
                reportBanner.innerHTML = `<p class="text-sm text-green-700 dark:text-green-400"><strong>Mock Exam Report saved!</strong> Grade ${data.report.grade} (${data.report.percentage}%) &mdash; <a href="/insights" class="underline">View in Insights</a></p>`;
                container.appendChild(reportBanner);
            }
        })
        .catch(err => console.error('Mock report creation error:', err));
    }

    showSection('study-session-summary');
}

export function dismissSessionSummary() {
    studyState.questions = [];
    studyState.index = 0;
    sessionScores = [];
    sessionXpEarned = 0;
    sessionNewBadges = [];
    sessionFlashcardsCreated = 0;
    sessionHintsUsed = 0;
    sessionGradeResults = [];
    examPaperInfo = null;
    showSection('study-mode-select');
}

// ── Exam Timer ───────────────────────────────────────────────────

function startExamTimer(minutes) {
    examTimeRemaining = minutes * 60;
    const timerEl = document.getElementById('exam-timer');
    if (timerEl) timerEl.classList.remove('hidden');
    updateTimerDisplay();

    examTimerInterval = setInterval(() => {
        examTimeRemaining--;
        if (examTimeRemaining <= 0) {
            examTimeRemaining = 0;
            stopExamTimer();
        }
        updateTimerDisplay();
    }, 1000);
}

function stopExamTimer() {
    if (examTimerInterval) {
        clearInterval(examTimerInterval);
        examTimerInterval = null;
    }
    const timerEl = document.getElementById('exam-timer');
    if (timerEl) timerEl.classList.add('hidden');
}

function updateTimerDisplay() {
    const display = document.getElementById('timer-display');
    const timerEl = document.getElementById('exam-timer');
    if (!display || !timerEl) return;

    const mins = Math.floor(examTimeRemaining / 60);
    const secs = examTimeRemaining % 60;
    display.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;

    timerEl.classList.remove('bg-slate-100', 'text-slate-700', 'bg-amber-100', 'text-amber-700', 'bg-red-100', 'text-red-700', 'pulse-red');
    if (examTimeRemaining <= 60) {
        timerEl.classList.add('bg-red-100', 'text-red-700', 'pulse-red');
    } else if (examTimeRemaining <= 300) {
        timerEl.classList.add('bg-amber-100', 'text-amber-700');
    } else {
        timerEl.classList.add('bg-slate-100', 'text-slate-700');
    }
}

// ── Subject Topic Dropdown & Tips ────────────────────────────────

function initSubjectTopicSync() {
    const subjectEl = document.getElementById('study-subject');
    if (!subjectEl) return;

    subjectEl.addEventListener('change', () => {
        const subject = subjectEl.value;
        const level = subjectEl.selectedOptions[0]?.dataset?.level || 'HL';
        loadTopicsForSubject(subject, level);
        loadSubjectTips(subject, level);
    });

    if (subjectEl.value) {
        const level = subjectEl.selectedOptions[0]?.dataset?.level || 'HL';
        loadTopicsForSubject(subjectEl.value, level);
        loadSubjectTips(subjectEl.value, level);
    }

    // Auto-fill from URL query params
    const params = new URLSearchParams(window.location.search);
    const paramSubject = params.get('subject');
    const paramTopic = params.get('topic');
    if (paramSubject) {
        for (const opt of subjectEl.options) {
            if (opt.value === paramSubject) {
                opt.selected = true;
                const level = opt.dataset?.level || 'HL';
                loadTopicsForSubject(paramSubject, level);
                loadSubjectTips(paramSubject, level);
                break;
            }
        }
        if (paramTopic) {
            const topicInput = document.getElementById('study-topic');
            if (topicInput) topicInput.value = paramTopic;
        }
        selectMode('smart');
    }
}

function loadTopicsForSubject(subject, level) {
    const selectEl = document.getElementById('study-topic-select');
    const inputEl = document.getElementById('study-topic');
    if (!selectEl || !inputEl) return;

    // Use embedded data (instant) or fall back to API call
    const embedded = window.SYLLABUS_TOPICS && window.SYLLABUS_TOPICS[subject];
    if (embedded) {
        _populateTopicDropdown(selectEl, inputEl, embedded, level);
    } else {
        fetch(`/api/topics?subject=${encodeURIComponent(subject)}&level=${level}`)
            .then(res => res.json())
            .then(data => _populateTopicDropdown(selectEl, inputEl, data.topics || [], level))
            .catch(() => {
                selectEl.classList.add('hidden');
                inputEl.classList.remove('hidden');
            });
    }
}

function _populateTopicDropdown(selectEl, inputEl, topics, level) {
    // Filter HL-only topics for SL students
    const filtered = topics.filter(t => !(t.hl_only && level === 'SL'));

    if (filtered.length === 0) {
        selectEl.classList.add('hidden');
        inputEl.classList.remove('hidden');
        return;
    }

    selectEl.innerHTML = '<option value="">Select a topic...</option>';
    filtered.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.name;
        opt.textContent = t.hl_only ? `${t.name} (HL)` : t.name;
        selectEl.appendChild(opt);
    });
    const freeOpt = document.createElement('option');
    freeOpt.value = '__custom__';
    freeOpt.textContent = 'Other (type your own)...';
    selectEl.appendChild(freeOpt);

    selectEl.classList.remove('hidden');
    inputEl.classList.add('hidden');

    selectEl.onchange = () => {
        if (selectEl.value === '__custom__') {
            selectEl.classList.add('hidden');
            inputEl.classList.remove('hidden');
            inputEl.value = '';
            inputEl.focus();
        } else {
            inputEl.value = selectEl.value;
        }
    };
}

function loadSubjectTips(subject, level) {
    const panel = document.getElementById('subject-tips-panel');
    const content = document.getElementById('subject-tips-content');
    if (!panel || !content) return;

    fetch(`/api/subject-config/${encodeURIComponent(subject)}?level=${level}`)
        .then(res => {
            if (!res.ok) throw new Error('No config');
            return res.json();
        })
        .then(data => {
            let html = '';
            if (data.study_strategies && data.study_strategies.length > 0) {
                html += '<p class="font-medium text-xs text-blue-800">Study Tips:</p>';
                html += '<ul class="list-disc ml-4 text-xs">';
                data.study_strategies.slice(0, 3).forEach(s => {
                    html += `<li>${escapeHtml(s)}</li>`;
                });
                html += '</ul>';
            }
            if (data.ia_description) {
                html += `<p class="mt-2 text-xs"><strong>IA:</strong> ${escapeHtml(data.ia_description)}</p>`;
            }
            if (html) {
                content.innerHTML = html;
                panel.classList.remove('hidden');
            } else {
                panel.classList.add('hidden');
            }
        })
        .catch(() => {
            panel.classList.add('hidden');
        });
}

// ── Speech-to-Text ───────────────────────────────────────────────

let speechRecognition = null;
let isSpeechActive = false;

export function toggleSpeechToText() {
    if (isSpeechActive) {
        stopSpeechToText();
    } else {
        startSpeechToText();
    }
}

function startSpeechToText() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('Speech recognition is not supported in this browser. Try Chrome, Edge, or Safari.');
        return;
    }

    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = true;
    speechRecognition.interimResults = true;
    speechRecognition.lang = 'en-US';

    const textarea = document.getElementById('answer-input');
    const existingText = textarea.value;
    let finalTranscript = '';

    speechRecognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interim += transcript;
            }
        }
        const separator = existingText && !existingText.endsWith(' ') && !existingText.endsWith('\n') ? ' ' : '';
        textarea.value = existingText + separator + finalTranscript + interim;
    };

    speechRecognition.onerror = (event) => {
        if (event.error !== 'no-speech') {
            console.error('Speech recognition error:', event.error);
        }
        stopSpeechToText();
    };

    speechRecognition.onend = () => {
        if (isSpeechActive) {
            const separator = existingText && !existingText.endsWith(' ') && !existingText.endsWith('\n') ? ' ' : '';
            textarea.value = existingText + separator + finalTranscript;
            stopSpeechToText();
        }
    };

    speechRecognition.start();
    isSpeechActive = true;

    const micBtn = document.getElementById('mic-btn');
    const micStatus = document.getElementById('mic-status');
    if (micBtn) {
        micBtn.classList.remove('border-slate-300', 'text-slate-500');
        micBtn.classList.add('border-red-400', 'text-red-500', 'bg-red-50');
    }
    if (micStatus) micStatus.classList.remove('hidden');
}

function stopSpeechToText() {
    if (speechRecognition) {
        speechRecognition.stop();
        speechRecognition = null;
    }
    isSpeechActive = false;

    const micBtn = document.getElementById('mic-btn');
    const micStatus = document.getElementById('mic-status');
    if (micBtn) {
        micBtn.classList.remove('border-red-400', 'text-red-500', 'bg-red-50');
        micBtn.classList.add('border-slate-300', 'text-slate-500');
    }
    if (micStatus) micStatus.classList.add('hidden');
}

function checkSpeechSupport() {
    const micBtn = document.getElementById('mic-btn');
    if (!micBtn) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        micBtn.disabled = true;
        micBtn.classList.add('opacity-40', 'cursor-not-allowed');
        micBtn.title = 'Speech recognition not supported in this browser';
    }
}

// ── Answer File Upload ───────────────────────────────────────────

export function uploadAnswerFile(input) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById('upload-answer-status');
    const statusText = document.getElementById('upload-answer-status-text');
    const uploadBtn = document.getElementById('upload-answer-btn');
    const textarea = document.getElementById('answer-input');

    if (statusEl) statusEl.classList.remove('hidden');
    if (statusText) statusText.textContent = `Extracting text from ${file.name}...`;
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.classList.add('opacity-50');
    }

    const formData = new FormData();
    formData.append('file', file);

    api.postForm('/api/study/extract-answer', formData)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                if (statusText) statusText.textContent = data.error;
                if (statusEl) statusEl.classList.replace('text-indigo-600', 'text-red-600');
                setTimeout(() => {
                    if (statusEl) {
                        statusEl.classList.add('hidden');
                        statusEl.classList.replace('text-red-600', 'text-indigo-600');
                    }
                }, 3000);
            } else {
                if (textarea) {
                    const existing = textarea.value.trim();
                    textarea.value = existing ? existing + '\n\n' + data.text : data.text;
                    textarea.focus();
                }
                if (statusEl) statusEl.classList.add('hidden');
            }
        })
        .catch(err => {
            if (statusText) statusText.textContent = 'Upload failed: ' + err.message;
            if (statusEl) statusEl.classList.replace('text-indigo-600', 'text-red-600');
            setTimeout(() => {
                if (statusEl) {
                    statusEl.classList.add('hidden');
                    statusEl.classList.replace('text-red-600', 'text-indigo-600');
                }
            }, 3000);
        })
        .finally(() => {
            if (uploadBtn) {
                uploadBtn.disabled = false;
                uploadBtn.classList.remove('opacity-50');
            }
            input.value = '';
        });
}

// ── AI Hints (Socratic Questioning) ──────────────────────────────

let currentHintLevel = 0;

export function requestHint() {
    const q = studyState.questions[studyState.index];
    if (!q) return;

    currentHintLevel++;
    const hintBtn = document.getElementById('hint-btn');
    const hintPanel = document.getElementById('hint-panel');
    const hintContent = document.getElementById('hint-content');
    const hintCount = document.getElementById('hint-count');

    if (hintBtn) {
        hintBtn.disabled = true;
        hintBtn.textContent = 'Thinking...';
    }

    sessionHintsUsed++;

    api.post('/api/study/hint', {
        question: q.question_text,
        command_term: q.command_term,
        marks: q.marks,
        subject: studyState.subject,
        topic: studyState.topic,
        level: studyState.level,
        hint_level: currentHintLevel,
        current_answer: document.getElementById('answer-input')?.value || '',
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            if (hintContent) hintContent.textContent = data.error;
        } else {
            if (hintContent) hintContent.innerHTML = escapeHtml(data.hint).replace(/\n/g, '<br>');
            if (hintCount) hintCount.textContent = `Hint ${currentHintLevel}/3`;
        }
        if (hintPanel) hintPanel.classList.remove('hidden');
        if (hintBtn) {
            hintBtn.disabled = currentHintLevel >= 3;
            hintBtn.textContent = currentHintLevel >= 3 ? 'No more hints' : 'Another hint?';
        }
    })
    .catch(err => {
        if (hintContent) hintContent.textContent = 'Failed to get hint: ' + err.message;
        if (hintPanel) hintPanel.classList.remove('hidden');
        if (hintBtn) {
            hintBtn.disabled = false;
            hintBtn.textContent = 'Need a hint?';
        }
    });
}

// ── Submit for Peer Review ────────────────────────────────────────

export function submitForReview() {
    const q = studyState.questions[studyState.index];
    if (!q) return;

    const btn = document.getElementById('review-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Submitting...';
    }

    api.post('/api/reviews/submit', {
        doc_type: 'exam_answer',
        subject: studyState.subject,
        title: `${q.command_term}: ${studyState.topic}`,
        text: document.getElementById('answer-input')?.value || '',
    })
    .then(res => res.json())
    .then(data => {
        if (btn) {
            if (data.error) {
                btn.textContent = 'Failed';
                setTimeout(() => { btn.textContent = 'Peer Review'; btn.disabled = false; }, 2000);
            } else {
                btn.textContent = 'Submitted!';
                btn.classList.remove('text-amber-600', 'border-amber-200', 'bg-amber-50');
                btn.classList.add('text-green-600', 'border-green-200', 'bg-green-50');
            }
        }
    })
    .catch(() => {
        if (btn) {
            btn.textContent = 'Failed';
            setTimeout(() => { btn.textContent = 'Peer Review'; btn.disabled = false; }, 2000);
        }
    });
}

// ── Review Calendar ──────────────────────────────────────────────

window.toggleReviewCalendar = async function() {
    const section = document.getElementById('review-calendar-section');
    if (!section.classList.contains('hidden')) {
        section.classList.add('hidden');
        return;
    }
    section.classList.remove('hidden');
    const grid = document.getElementById('review-calendar-grid');
    grid.innerHTML = '<p class="col-span-7 text-sm text-slate-400">Loading...</p>';

    try {
        const res = await api('/api/study/review-calendar');
        const calendar = res.calendar || {};
        renderCalendar(grid, calendar);
    } catch {
        grid.innerHTML = '<p class="col-span-7 text-sm text-red-500">Failed to load calendar.</p>';
    }
};

function renderCalendar(grid, calendar) {
    const today = new Date();
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    let html = dayNames.map(d => `<div class="font-medium text-slate-500 py-1">${d}</div>`).join('');

    // Pad to start of week
    const startDate = new Date(today);
    const dayOfWeek = startDate.getDay();
    html += '<div></div>'.repeat(dayOfWeek);

    for (let i = 0; i < 30; i++) {
        const d = new Date(today);
        d.setDate(d.getDate() + i);
        const key = d.toISOString().split('T')[0];
        const items = calendar[key] || [];
        const count = items.length;
        const bgClass = count === 0 ? 'bg-slate-100 dark:bg-slate-700'
            : count <= 2 ? 'bg-indigo-100 dark:bg-indigo-900/40'
            : count <= 5 ? 'bg-indigo-200 dark:bg-indigo-800/60'
            : 'bg-indigo-400 dark:bg-indigo-700';

        html += `<div class="p-1 rounded cursor-pointer hover:ring-2 hover:ring-indigo-400 ${bgClass}" onclick="showCalendarDay('${key}', ${JSON.stringify(items).replace(/"/g, '&quot;')})">
            <div class="text-xs font-medium">${d.getDate()}</div>
            ${count > 0 ? `<div class="text-[10px] text-indigo-700 dark:text-indigo-300">${count}</div>` : ''}
        </div>`;
    }
    grid.innerHTML = html;
}

window.showCalendarDay = function(dateStr, items) {
    const detail = document.getElementById('review-calendar-detail');
    const dateEl = document.getElementById('calendar-detail-date');
    const itemsEl = document.getElementById('calendar-detail-items');

    if (!items || items.length === 0) {
        detail.classList.add('hidden');
        return;
    }
    detail.classList.remove('hidden');
    dateEl.textContent = `Due: ${dateStr}`;
    itemsEl.innerHTML = items.map(item => {
        const icon = item.type === 'flashcard' ? '📇' : '📝';
        const label = item.type === 'flashcard'
            ? `${item.subject} — ${item.front}`
            : `${item.subject}: ${item.topic} (${item.command_term})`;
        return `<p class="text-xs text-slate-600 dark:text-slate-400">${icon} ${label}</p>`;
    }).join('');
};

// ── Weak Topics ─────────────────────────────────────────────────

async function loadWeakTopics() {
    try {
        const res = await api('/api/study/weak-topics');
        const topics = res.weak_topics || [];
        const sos = res.sos_alerts || [];
        if (topics.length === 0 && sos.length === 0) return;

        const card = document.getElementById('weak-topics-card');
        const list = document.getElementById('weak-topics-list');
        if (!card || !list) return;

        let html = '';
        for (const t of sos.slice(0, 3)) {
            html += `<button onclick="quickDrill('${t.subject}', '${t.topic}')"
                class="px-3 py-1.5 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-xs rounded-full border border-red-200 dark:border-red-800 hover:bg-red-200 cursor-pointer">
                🚨 ${t.subject}: ${t.topic} (${Math.round(t.avg_percentage)}%)
            </button>`;
        }
        for (const t of topics.slice(0, 5)) {
            html += `<button onclick="quickDrill('${t.subject}', '${t.subtopic}')"
                class="px-3 py-1.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-xs rounded-full border border-amber-200 dark:border-amber-800 hover:bg-amber-200 cursor-pointer">
                ${t.subject}: ${t.subtopic} (${Math.round(t.avg_percentage)}%)
            </button>`;
        }
        list.innerHTML = html;
        card.classList.remove('hidden');
    } catch {
        // Non-critical — ignore
    }
}

window.quickDrill = function(subject, topic) {
    // Pre-fill subject/topic and start a focused practice session
    const subjectSelect = document.getElementById('subject-select');
    const topicSelect = document.getElementById('topic-select');
    if (subjectSelect) subjectSelect.value = subject;
    if (topicSelect) {
        // Add as option if not present
        const opt = document.createElement('option');
        opt.value = topic;
        opt.textContent = topic;
        topicSelect.appendChild(opt);
        topicSelect.value = topic;
    }
    selectMode('smart');
};

// ── Exam History ────────────────────────────────────────────────

window.toggleExamHistory = async function() {
    const section = document.getElementById('exam-history-section');
    if (!section.classList.contains('hidden')) {
        section.classList.add('hidden');
        return;
    }
    section.classList.remove('hidden');
    const list = document.getElementById('exam-history-list');
    list.innerHTML = '<p class="text-sm text-slate-400">Loading...</p>';

    try {
        const res = await api('/api/study/exam-history');
        const sessions = res.sessions || [];
        if (sessions.length === 0) {
            list.innerHTML = '<p class="text-sm text-slate-500">No exam simulations completed yet.</p>';
            return;
        }

        list.innerHTML = sessions.map(s => `
            <div class="p-3 bg-slate-50 dark:bg-slate-700 rounded-lg">
                <div class="flex items-center justify-between">
                    <h4 class="text-sm font-medium">${s.subject} ${s.level} — Paper ${s.paper_number}</h4>
                    <span class="text-xs px-2 py-0.5 rounded-full ${s.percentage >= 70 ? 'bg-green-100 text-green-700' : s.percentage >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}">
                        ${s.percentage}% (Grade ${s.grade})
                    </span>
                </div>
                <p class="text-xs text-slate-500 mt-1">${s.earned_marks}/${s.total_marks} marks &middot; ${s.duration_minutes} min &middot; ${s.started_at || ''}</p>
                ${Object.keys(s.command_term_breakdown).length > 0 ? `
                    <div class="mt-2 flex flex-wrap gap-1">
                        ${Object.entries(s.command_term_breakdown).map(([ct, stats]) => {
                            const pct = stats.total > 0 ? Math.round(stats.earned / stats.total * 100) : 0;
                            return `<span class="text-[10px] px-1.5 py-0.5 rounded ${pct >= 70 ? 'bg-green-100 text-green-700' : pct >= 50 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'}">${ct}: ${pct}%</span>`;
                        }).join('')}
                    </div>
                ` : ''}
            </div>
        `).join('');

        // Render Chart.js chart for latest session if it has command term data
        const latest = sessions[0];
        if (latest && Object.keys(latest.command_term_breakdown).length > 0) {
            renderExamChart(latest.command_term_breakdown);
        }
    } catch {
        list.innerHTML = '<p class="text-sm text-red-500">Failed to load exam history.</p>';
    }
};

function renderExamChart(breakdown) {
    const canvas = document.getElementById('exam-ct-chart');
    if (!canvas || typeof Chart === 'undefined') return;

    canvas.classList.remove('hidden');
    const labels = Object.keys(breakdown);
    const data = labels.map(ct => {
        const s = breakdown[ct];
        return s.total > 0 ? Math.round(s.earned / s.total * 100) : 0;
    });

    // Destroy previous chart if exists
    if (canvas._chart) canvas._chart.destroy();

    canvas._chart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Score %',
                data,
                backgroundColor: data.map(v => v >= 70 ? '#86efac' : v >= 50 ? '#fde68a' : '#fca5a5'),
                borderRadius: 4,
            }],
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true, max: 100 } },
            plugins: { legend: { display: false }, title: { display: true, text: 'Latest Exam — Command Term Performance' } },
        },
    });
}

// ── Auto-init on import ──────────────────────────────────────────

initSubjectTopicSync();
checkSpeechSupport();
loadWeakTopics();
