// ── IB Study Companion — Client-Side JavaScript ────────────────────

// ── Command Term Definitions ──────────────────────────────────────

const COMMAND_TERM_DEFINITIONS = {
    "Define": {
        expect: "Give the precise meaning. No explanation needed.",
        marks: "1-2 marks",
        common_mistake: "Adding unnecessary explanation or examples when only a definition is needed.",
    },
    "State": {
        expect: "Give a specific name, value, or brief answer. No explanation.",
        marks: "1-2 marks",
        common_mistake: "Writing too much — a single sentence or phrase is enough.",
    },
    "List": {
        expect: "Give a sequence of brief answers with no explanation.",
        marks: "1-3 marks",
        common_mistake: "Providing explanations when only names/terms are required.",
    },
    "Identify": {
        expect: "Provide an answer from a number of possibilities. Recognize and state briefly.",
        marks: "1-2 marks",
        common_mistake: "Confusing identify with explain — keep it brief.",
    },
    "Describe": {
        expect: "Give a detailed account or picture of a situation, event, pattern or process.",
        marks: "2-4 marks",
        common_mistake: "Not providing enough specific detail or data.",
    },
    "Outline": {
        expect: "Give a brief account or summary. Less detail than 'describe'.",
        marks: "2-4 marks",
        common_mistake: "Going into too much detail — keep it concise.",
    },
    "Distinguish": {
        expect: "Make clear the differences between two or more concepts.",
        marks: "2-4 marks",
        common_mistake: "Only describing one side without explicit comparison.",
    },
    "Explain": {
        expect: "Give a detailed account including reasons or causes. Use 'because', 'therefore', 'this leads to'.",
        marks: "3-6 marks",
        common_mistake: "Describing WHAT happens without explaining WHY or HOW.",
    },
    "Suggest": {
        expect: "Propose a solution, hypothesis or other possible answer. No single correct answer.",
        marks: "2-4 marks",
        common_mistake: "Not justifying your suggestion with reasoning.",
    },
    "Annotate": {
        expect: "Add brief notes to a diagram or graph.",
        marks: "1-3 marks",
        common_mistake: "Writing too much — annotations should be brief labels.",
    },
    "Analyse": {
        expect: "Break down to bring out the essential elements or structure. Show relationships between parts.",
        marks: "6-8 marks",
        common_mistake: "Describing without showing cause-effect relationships or interconnections.",
    },
    "Compare": {
        expect: "Give an account of similarities AND differences, referring to both throughout.",
        marks: "4-6 marks",
        common_mistake: "Only listing similarities OR differences, not both.",
    },
    "Compare and contrast": {
        expect: "Give an account of similarities AND differences between two items.",
        marks: "4-8 marks",
        common_mistake: "Treating each item separately instead of point-by-point comparison.",
    },
    "Contrast": {
        expect: "Give an account of the differences between two items, referring to both.",
        marks: "4-6 marks",
        common_mistake: "Including similarities when only differences are asked for.",
    },
    "Evaluate": {
        expect: "Weigh strengths AND limitations. Reach a supported conclusion. Must argue BOTH sides.",
        marks: "8-15 marks",
        common_mistake: "Only arguing one side. IB caps one-sided evaluations at ~50%.",
    },
    "Discuss": {
        expect: "Offer a considered and balanced review. Include a range of arguments, factors or hypotheses.",
        marks: "8-15 marks",
        common_mistake: "Not providing counter-arguments or alternative perspectives.",
    },
    "Justify": {
        expect: "Give valid reasons or evidence to support an answer or conclusion.",
        marks: "4-8 marks",
        common_mistake: "Stating a position without providing evidence or reasoning.",
    },
    "Examine": {
        expect: "Consider an argument or concept in a way that uncovers assumptions and interrelationships.",
        marks: "6-10 marks",
        common_mistake: "Surface-level treatment without digging into underlying assumptions.",
    },
    "To what extent": {
        expect: "Consider the merits of an argument. Include BOTH supporting and opposing evidence. Reach a conclusion.",
        marks: "8-15 marks",
        common_mistake: "Not quantifying or qualifying the extent — just saying 'yes' or 'no'.",
    },
};

// ── CSRF Token Helper ────────────────────────────────────────────

function csrfHeaders() {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['X-CSRFToken'] = token;
    return headers;
}

function csrfTokenHeader() {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    return token ? { 'X-CSRFToken': token } : {};
}

// ── Upload (drag-drop + file input) ──────────────────────────────

(function initUpload() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('border-indigo-500', 'bg-indigo-50');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-50');
        const files = e.dataTransfer.files;
        for (const file of files) {
            if (file.name.toLowerCase().endsWith('.pdf')) {
                uploadFile(file);
            }
        }
    });

    fileInput.addEventListener('change', () => {
        for (const file of fileInput.files) {
            uploadFile(file);
        }
        fileInput.value = '';
    });
})();

function uploadFile(file) {
    const progress = document.getElementById('upload-progress');
    const bar = document.getElementById('upload-bar');
    const filename = document.getElementById('upload-filename');
    const status = document.getElementById('upload-status');
    const result = document.getElementById('upload-result');

    progress.classList.remove('hidden');
    result.classList.add('hidden');
    filename.textContent = file.name;
    status.textContent = 'Uploading...';
    bar.style.width = '30%';

    const formData = new FormData();
    formData.append('file', file);
    const selectedDocType = typeof window.selectedDocType !== 'undefined'
        ? window.selectedDocType
        : (document.querySelector('.doc-type-btn.active')?.dataset?.type || 'notes');
    formData.append('doc_type', selectedDocType);

    fetch('/api/upload', { method: 'POST', headers: csrfTokenHeader(), body: formData })
        .then(res => {
            bar.style.width = '80%';
            status.textContent = 'Processing...';
            return res.json();
        })
        .then(data => {
            bar.style.width = '100%';
            if (data.error) {
                status.textContent = 'Failed';
                bar.classList.remove('bg-indigo-600');
                bar.classList.add('bg-red-500');
                result.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">${data.error}</div>`;
            } else {
                status.textContent = 'Done!';
                result.innerHTML = `
                    <div class="p-4 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm">
                        <strong>${data.filename}</strong> uploaded and indexed successfully.
                        <br><span class="text-green-600">${data.chunks} chunks | ${data.doc_type.replace(/_/g, ' ')} | ${data.subject.replace(/_/g, ' ')}</span>
                    </div>`;
                setTimeout(() => location.reload(), 1500);
            }
            result.classList.remove('hidden');
        })
        .catch(err => {
            bar.style.width = '100%';
            bar.classList.remove('bg-indigo-600');
            bar.classList.add('bg-red-500');
            status.textContent = 'Error';
            result.innerHTML = `<div class="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">Upload failed: ${err.message}</div>`;
            result.classList.remove('hidden');
        });
}

document.querySelectorAll('.doc-type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        window.selectedDocType = btn.dataset.type;
    });
});

// ── Document deletion ────────────────────────────────────────────

function deleteDocument(docId) {
    if (!confirm('Delete this document? This will remove it from the knowledge base.')) return;

    fetch(`/api/documents/${docId}`, { method: 'DELETE', headers: csrfTokenHeader() })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                const row = document.getElementById(`doc-${docId}`);
                if (row) row.remove();
            } else {
                alert(data.error || 'Failed to delete document.');
            }
        })
        .catch(err => alert('Error: ' + err.message));
}

// ── Study — Three-Mode System ────────────────────────────────────

let studyQuestions = [];
let studyIndex = 0;
let studySubject = '';
let studyTopic = '';
let studyLevel = 'HL';
let studyMode = 'smart';
let responseMode = 'full';  // 'full' | 'bullet' | 'model'
let examTimerInterval = null;
let examTimeRemaining = 0;

// Session tracking for summaries
let sessionScores = [];
let sessionXpEarned = 0;
let sessionNewBadges = [];
let sessionFlashcardsCreated = 0;
let sessionHintsUsed = 0;
let sessionGradeResults = [];  // Full grade results for mock report
let examPaperInfo = null;

const STUDY_SECTIONS = [
    'study-mode-select', 'study-setup', 'study-loading',
    'study-question', 'grading-loading', 'study-result', 'study-error',
    'study-session-summary'
];

function showSection(id) {
    STUDY_SECTIONS.forEach(s => {
        const el = document.getElementById(s);
        if (el) el.classList.toggle('hidden', s !== id);
    });
}

function selectMode(mode) {
    studyMode = mode;

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

    // Toggle mode-specific UI
    const ctGroup = document.getElementById('ct-select-group');
    const timeGroup = document.getElementById('time-limit-group');
    const countGroup = document.getElementById('count-group');
    const smartBanner = document.getElementById('smart-rec-banner');
    const ctDefCard = document.getElementById('ct-definition-card');

    ctGroup.classList.toggle('hidden', mode !== 'command_term');
    timeGroup.classList.toggle('hidden', mode !== 'exam_sim');
    countGroup.classList.toggle('hidden', mode === 'exam_sim');
    ctDefCard.classList.add('hidden');

    // Smart mode: show recommendation
    if (mode === 'smart' && window.RECOMMENDATION && window.RECOMMENDATION.subject) {
        smartBanner.classList.remove('hidden');
        document.getElementById('smart-rec-text').textContent =
            `Recommended: ${window.RECOMMENDATION.reason}`;
        // Pre-select recommended subject
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

function backToModes() {
    showSection('study-mode-select');
}

function onCommandTermChange() {
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

function generateStudy() {
    const subjectEl = document.getElementById('study-subject');
    const topicEl = document.getElementById('study-topic');
    const topicSelectEl = document.getElementById('study-topic-select');

    if (!subjectEl || !topicEl) return;

    studySubject = subjectEl.value;
    studyLevel = subjectEl.selectedOptions[0]?.dataset?.level || 'HL';

    // Use dropdown value if visible and selected, otherwise use text input
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
    studyTopic = topic;

    const count = studyMode === 'exam_sim' ? 5 : parseInt(document.getElementById('study-count').value);
    const style = studyMode === 'command_term'
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

    fetch('/api/study/generate', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({
            subject: studySubject,
            topic,
            count,
            level: studyLevel,
            mode: studyMode,
            style,
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            document.getElementById('error-message').textContent = data.error;
            showSection('study-error');
            return;
        }
        studyQuestions = data.questions;
        studyIndex = 0;
        examPaperInfo = data.exam_paper_info || null;

        // Start exam timer if exam sim mode
        if (studyMode === 'exam_sim') {
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

function selectResponseMode(mode) {
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
        // Show model answer
        const q = studyQuestions[studyIndex];
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

function displayQuestion() {
    if (studyIndex >= studyQuestions.length) {
        resetStudy();
        return;
    }

    const q = studyQuestions[studyIndex];
    document.getElementById('q-current').textContent = studyIndex + 1;
    document.getElementById('q-total').textContent = studyQuestions.length;
    document.getElementById('q-badge').textContent = `${q.marks} marks`;
    document.getElementById('q-command-term').textContent = q.command_term;
    document.getElementById('q-marks').textContent = `${q.marks} marks`;
    document.getElementById('q-text').textContent = q.question_text;
    document.getElementById('answer-input').value = '';

    // Show exam paper info if available
    const examBanner = document.getElementById('exam-paper-banner');
    const examText = document.getElementById('exam-paper-text');
    if (examBanner && examPaperInfo && examPaperInfo.papers && examPaperInfo.papers.length > 0) {
        const totalMarks = examPaperInfo.total_marks;
        const paperNames = examPaperInfo.papers.map(p => `${p.name} (${p.description})`).join(' | ');
        examText.textContent = `Exam Simulation: ${paperNames} — Total: ${totalMarks} marks`;
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

    // Reset response mode button styling
    const buttons = document.querySelectorAll('.response-mode-btn');
    buttons.forEach((btn, i) => {
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

function submitAnswer() {
    const answer = document.getElementById('answer-input').value.trim();
    if (!answer) {
        document.getElementById('answer-input').focus();
        return;
    }

    const q = studyQuestions[studyIndex];
    showSection('grading-loading');

    fetch('/api/study/grade', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({
            question: q.question_text,
            answer: answer,
            subject: studySubject,
            topic: studyTopic,
            marks: q.marks,
            command_term: q.command_term,
            level: studyLevel,
        })
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

function displayEnhancedResult(data) {
    // Grade badge
    const badge = document.getElementById('result-grade-badge');
    badge.textContent = data.grade;
    badge.className = 'inline-flex items-center justify-center w-12 h-12 rounded-full text-lg font-bold ';
    if (data.grade >= 6) badge.className += 'bg-green-100 text-green-700';
    else if (data.grade >= 4) badge.className += 'bg-yellow-100 text-yellow-700';
    else badge.className += 'bg-red-100 text-red-700';

    document.getElementById('result-mark').textContent = `${data.mark_earned}/${data.mark_total}`;
    document.getElementById('result-percentage').textContent = `${data.percentage}%`;

    // Score bar
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
            targetText.textContent = `Your target is Grade ${data.target_grade} (needs ~${targetPct}%). You scored ${data.percentage}% — above target!`;
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
    const strengthsList = document.getElementById('result-strengths');
    strengthsList.innerHTML = data.strengths.map(s =>
        `<li class="flex items-start gap-2"><span class="text-green-500 mt-0.5">&#10003;</span> ${escapeHtml(s)}</li>`
    ).join('');

    // Improvements
    const improvementsList = document.getElementById('result-improvements');
    improvementsList.innerHTML = data.improvements.map(s =>
        `<li class="flex items-start gap-2"><span class="text-amber-500 mt-0.5">&#9679;</span> ${escapeHtml(s)}</li>`
    ).join('');

    // Tip & Commentary
    document.getElementById('result-tip').textContent = data.examiner_tip;
    document.getElementById('result-commentary').textContent = data.full_commentary;

    // Model answer (from grader or from question generation)
    const modelPanel = document.getElementById('result-model-answer');
    const modelText = document.getElementById('result-model-text');
    const modelAnswer = data.model_answer || (studyQuestions[studyIndex] && studyQuestions[studyIndex].model_answer) || '';
    if (modelAnswer) {
        modelText.textContent = modelAnswer;
        modelPanel.classList.remove('hidden');
    } else {
        modelPanel.classList.add('hidden');
    }

    // XP & Gamification Notifications
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
        // Track full result for mock reports
        sessionGradeResults.push({
            question: studyQuestions[studyIndex]?.question_text || '',
            marks: data.mark_total,
            mark_earned: data.mark_earned,
            percentage: data.percentage,
            command_term: studyQuestions[studyIndex]?.command_term || '',
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

    // Update next button text
    const nextBtn = document.getElementById('next-btn');
    if (studyIndex >= studyQuestions.length - 1) {
        nextBtn.textContent = 'Finish Session';
    } else {
        nextBtn.textContent = 'Next Question';
    }

    showSection('study-result');
}

function nextQuestion() {
    studyIndex++;
    if (studyIndex >= studyQuestions.length) {
        resetStudy();
    } else {
        displayQuestion();
    }
}

function skipQuestion() {
    nextQuestion();
}

function resetStudy() {
    stopExamTimer();

    // Show session summary if there were graded answers
    if (sessionScores.length > 0) {
        showSessionSummary();
        return;
    }

    // No graded answers — go straight back
    studyQuestions = [];
    studyIndex = 0;
    showSection('study-mode-select');
}

function showSessionSummary() {
    const container = document.getElementById('session-summary-content');
    if (!container) {
        // Fallback if template doesn't have summary section
        studyQuestions = [];
        studyIndex = 0;
        sessionScores = [];
        sessionXpEarned = 0;
        sessionNewBadges = [];
        sessionFlashcardsCreated = 0;
        sessionHintsUsed = 0;
        showSection('study-mode-select');
        return;
    }

    const totalQuestions = studyQuestions.length;
    const answered = sessionScores.length;
    const avgScore = answered > 0
        ? Math.round(sessionScores.reduce((a, b) => a + b, 0) / sessionScores.length)
        : 0;
    const bestScore = answered > 0 ? Math.max(...sessionScores) : 0;

    // Determine performance message
    let perfMsg = '';
    let perfColor = '';
    if (avgScore >= 80) { perfMsg = 'Outstanding performance!'; perfColor = 'text-green-700'; }
    else if (avgScore >= 60) { perfMsg = 'Solid work — keep building on this.'; perfColor = 'text-blue-700'; }
    else if (avgScore >= 40) { perfMsg = 'Good effort — review weak areas and try again.'; perfColor = 'text-amber-700'; }
    else { perfMsg = 'Keep practicing — every attempt builds understanding.'; perfColor = 'text-red-700'; }

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

    // Badges earned
    if (sessionNewBadges.length > 0) {
        html += `<div class="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl">
            <h3 class="text-sm font-semibold text-amber-800 dark:text-amber-400 mb-2">&#127942; Badges Earned!</h3>
            <div class="flex flex-wrap gap-2">${sessionNewBadges.map(b =>
                `<span class="px-3 py-1 bg-amber-100 dark:bg-amber-800 text-amber-800 dark:text-amber-200 text-sm font-medium rounded-full">${escapeHtml(b)}</span>`
            ).join('')}</div>
        </div>`;
    }

    // Score breakdown
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

    // Recommendation
    const weakestScore = Math.min(...sessionScores);
    const weakestIdx = sessionScores.indexOf(weakestScore);
    if (weakestScore < 60 && studyQuestions[weakestIdx]) {
        const weakQ = studyQuestions[weakestIdx];
        html += `<div class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl">
            <h3 class="text-sm font-semibold text-blue-800 dark:text-blue-400 mb-1">Focus Next Time</h3>
            <p class="text-sm text-blue-700 dark:text-blue-300">Practice more <strong>${escapeHtml(weakQ.command_term)}</strong> questions — you scored ${weakestScore}% on Q${weakestIdx + 1}.</p>
        </div>`;
    }

    container.innerHTML = html;

    // Auto-create mock report for exam sim mode
    if (studyMode === 'exam_sim' && sessionGradeResults.length > 0) {
        fetch('/api/mock-reports/create', {
            method: 'POST',
            headers: csrfHeaders(),
            body: JSON.stringify({
                subject: studySubject,
                level: studyLevel,
                results: sessionGradeResults,
            })
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

function dismissSessionSummary() {
    studyQuestions = [];
    studyIndex = 0;
    sessionScores = [];
    sessionXpEarned = 0;
    sessionNewBadges = [];
    sessionFlashcardsCreated = 0;
    sessionHintsUsed = 0;
    sessionGradeResults = [];
    examPaperInfo = null;
    showSection('study-mode-select');
}

// ── Exam Timer ──────────────────────────────────────────────────

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

    // Urgency colors
    timerEl.classList.remove('bg-slate-100', 'text-slate-700', 'bg-amber-100', 'text-amber-700', 'bg-red-100', 'text-red-700', 'pulse-red');
    if (examTimeRemaining <= 60) {
        timerEl.classList.add('bg-red-100', 'text-red-700', 'pulse-red');
    } else if (examTimeRemaining <= 300) {
        timerEl.classList.add('bg-amber-100', 'text-amber-700');
    } else {
        timerEl.classList.add('bg-slate-100', 'text-slate-700');
    }
}

// ── Insights ────────────────────────────────────────────────────

let trendChart = null;
let distChart = null;

function loadInsights() {
    fetch('/api/insights')
        .then(res => res.json())
        .then(data => {
            if (data.error) return;

            // Text insights cards
            renderTextInsights(data.insights || []);

            // Command term breakdown
            renderCommandTermTable(data.command_term_stats || {});

            // Subject gap table
            renderGapTable(data.gaps || []);

            // Study allocation
            renderStudyAllocation(data.study_allocation || []);

            // Trend chart
            renderTrendChart(data);

            // Distribution chart
            renderDistChart(data);

            // Syllabus coverage
            renderSyllabusCoverage(data.syllabus_coverage || null);

            // Misconceptions
            loadMisconceptions();

            // Predicted grades
            loadPredictedGrades();

            // Mock exam reports
            loadMockReports();

            // Writing profile
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
        .catch(err => console.error('Insights load error:', err));
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

    // Sort by avg percentage ascending (weakest first)
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
            <td class="px-5 py-3 text-center text-slate-700 font-semibold">${g.predicted || '—'}</td>
            <td class="px-5 py-3 text-center">${g.gap > 0 ? '<span class="text-red-600 font-semibold">-' + g.gap + '</span>' : (g.status === 'no_data' ? '—' : '<span class="text-green-600">0</span>')}</td>
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
    } else {
        const chartEl = document.getElementById('dist-chart');
        if (chartEl) chartEl.style.display = 'none';
        const emptyEl = document.getElementById('dist-empty');
        if (emptyEl) emptyEl.classList.remove('hidden');
    }
}

function generateWeaknessReport() {
    const btn = document.getElementById('weakness-btn');
    const content = document.getElementById('weakness-content');

    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    content.innerHTML = '<div class="flex items-center gap-3"><div class="w-5 h-5 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div><span class="text-sm text-slate-500">Generating weakness report...</span></div>';

    fetch('/api/analytics/weakness', { method: 'POST', headers: csrfTokenHeader() })
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

// ── Subject Topic Dropdown & Tips ────────────────────────────

(function initSubjectTopicSync() {
    const subjectEl = document.getElementById('study-subject');
    if (!subjectEl) return;

    subjectEl.addEventListener('change', () => {
        const subject = subjectEl.value;
        const level = subjectEl.selectedOptions[0]?.dataset?.level || 'HL';
        loadTopicsForSubject(subject, level);
        loadSubjectTips(subject, level);
    });

    // Initial load if subject already selected
    if (subjectEl.value) {
        const level = subjectEl.selectedOptions[0]?.dataset?.level || 'HL';
        loadTopicsForSubject(subjectEl.value, level);
        loadSubjectTips(subjectEl.value, level);
    }

    // Auto-fill from URL query params (e.g. from Study Plan "Start" button)
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
        // Jump straight to setup
        selectMode('smart');
    }
})();

function loadTopicsForSubject(subject, level) {
    const selectEl = document.getElementById('study-topic-select');
    const inputEl = document.getElementById('study-topic');
    if (!selectEl || !inputEl) return;

    fetch(`/api/topics?subject=${encodeURIComponent(subject)}&level=${level}`)
        .then(res => res.json())
        .then(data => {
            const topics = data.topics || [];
            if (topics.length === 0) {
                selectEl.classList.add('hidden');
                inputEl.classList.remove('hidden');
                return;
            }

            selectEl.innerHTML = '<option value="">Select a topic...</option>';
            topics.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.name;
                opt.textContent = t.hl_only ? `${t.name} (HL)` : t.name;
                selectEl.appendChild(opt);
            });
            // Add free-text option
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
        })
        .catch(() => {
            selectEl.classList.add('hidden');
            inputEl.classList.remove('hidden');
        });
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

// ── Syllabus Coverage in Insights ────────────────────────────

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

// ── Misconception Tracker ─────────────────────────────────────

function loadMisconceptions() {
    fetch('/api/misconceptions')
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

// ── Predicted Grade Confidence ───────────────────────────────

function loadPredictedGrades() {
    fetch('/api/gamification')
        .then(res => res.json())
        .then(data => {
            // We need to get dashboard data which has predictions
            return fetch('/api/insights');
        })
        .then(res => res.json())
        .then(data => {
            const section = document.getElementById('predicted-grade-section');
            const content = document.getElementById('predicted-grade-content');
            if (!section || !content) return;

            const gaps = data.gaps || [];
            const subjectsWithData = gaps.filter(g => g.predicted && g.predicted !== '—');
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

// ── Mock Exam Reports ────────────────────────────────────────

function loadMockReports() {
    fetch('/api/mock-reports')
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

                // Command term breakdown bars
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

                // Improvements list
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

// ── Lifecycle Management ─────────────────────────────────────

function toggleMilestone(milestoneId, el) {
    fetch('/api/lifecycle/milestone', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({ milestone_id: milestoneId }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        // Toggle visual state
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

function addCASReflection() {
    const strand = document.getElementById('cas-strand')?.value;
    const title = document.getElementById('cas-title')?.value?.trim();
    const description = document.getElementById('cas-description')?.value?.trim();
    const outcome = document.getElementById('cas-outcome')?.value;
    const hours = parseFloat(document.getElementById('cas-hours')?.value) || 0;

    if (!strand || !title) {
        alert('Please select a strand and enter a title.');
        return;
    }

    fetch('/api/lifecycle/cas', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({ strand, title, description, learning_outcome: outcome, hours }),
    })
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

function updateLifecycleSection(section) {
    let payload = { section };

    if (section === 'ee') {
        payload.subject = document.getElementById('ee-subject')?.value || '';
        payload.research_question = document.getElementById('ee-rq')?.value || '';
        payload.supervisor = document.getElementById('ee-supervisor')?.value || '';
    } else if (section === 'tok') {
        payload.essay_title = document.getElementById('tok-title')?.value || '';
        payload.exhibition_theme = document.getElementById('tok-exhibition')?.value || '';
    }

    fetch('/api/lifecycle/update', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify(payload),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }
        // Brief visual feedback
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

// ── Parent Portal Settings ───────────────────────────────────

function toggleParentSharing() {
    const btn = document.getElementById('parent-toggle-btn');
    const isEnabled = btn.classList.contains('bg-indigo-600');
    const action = isEnabled ? 'disable' : 'enable';

    fetch('/api/parent/toggle', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({ action }),
    })
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

function copyParentLink() {
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

function regenerateToken() {
    if (!confirm('Regenerate the link? The old link will stop working.')) return;

    fetch('/api/parent/toggle', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({ action: 'regenerate' }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.token) {
            document.getElementById('parent-link-input').value =
                window.location.origin + '/parent/' + data.token;
        }
    })
    .catch(err => alert('Error: ' + err.message));
}

function savePrivacySettings() {
    const payload = {
        student_display_name: document.getElementById('parent-display-name')?.value || '',
        show_subject_grades: document.getElementById('priv-grades')?.checked || false,
        show_recent_activity: document.getElementById('priv-activity')?.checked || false,
        show_study_consistency: document.getElementById('priv-consistency')?.checked || false,
        show_command_term_stats: document.getElementById('priv-ct')?.checked || false,
        show_insights: document.getElementById('priv-insights')?.checked || false,
        show_exam_countdown: document.getElementById('priv-countdown')?.checked || false,
    };

    fetch('/api/parent/privacy', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify(payload),
    })
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

// ── Study Planner ────────────────────────────────────────────

function generatePlan() {
    const btn = document.getElementById('generate-plan-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Generating...';
    }

    fetch('/api/planner/generate', {
        method: 'POST',
        headers: csrfHeaders(),
    })
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

function togglePlanTask(dayDate, taskIndex, el) {
    fetch('/api/planner/complete', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({ date: dayDate, task_index: taskIndex }),
    })
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

        // Update the day's completion counter
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

// ── Speech-to-Text (Web Speech API) ─────────────────────────────

let speechRecognition = null;
let isSpeechActive = false;

function toggleSpeechToText() {
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
        // Finalize the text when recognition ends
        if (isSpeechActive) {
            const separator = existingText && !existingText.endsWith(' ') && !existingText.endsWith('\n') ? ' ' : '';
            textarea.value = existingText + separator + finalTranscript;
            stopSpeechToText();
        }
    };

    speechRecognition.start();
    isSpeechActive = true;

    // Update UI
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

    // Update UI
    const micBtn = document.getElementById('mic-btn');
    const micStatus = document.getElementById('mic-status');
    if (micBtn) {
        micBtn.classList.remove('border-red-400', 'text-red-500', 'bg-red-50');
        micBtn.classList.add('border-slate-300', 'text-slate-500');
    }
    if (micStatus) micStatus.classList.add('hidden');
}

// Disable mic button if Speech API not available
(function checkSpeechSupport() {
    const micBtn = document.getElementById('mic-btn');
    if (!micBtn) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        micBtn.disabled = true;
        micBtn.classList.add('opacity-40', 'cursor-not-allowed');
        micBtn.title = 'Speech recognition not supported in this browser';
    }
})();

// ── Answer File Upload (Image/PDF → Text Extraction) ────────────

function uploadAnswerFile(input) {
    const file = input.files[0];
    if (!file) return;

    const statusEl = document.getElementById('upload-answer-status');
    const statusText = document.getElementById('upload-answer-status-text');
    const uploadBtn = document.getElementById('upload-answer-btn');
    const textarea = document.getElementById('answer-input');

    // Show processing state
    if (statusEl) statusEl.classList.remove('hidden');
    if (statusText) statusText.textContent = `Extracting text from ${file.name}...`;
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.classList.add('opacity-50');
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/study/extract-answer', { method: 'POST', headers: csrfTokenHeader(), body: formData })
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
                // Populate textarea with extracted text
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

// ── Dark Mode Toggle ────────────────────────────────────────────

function toggleDarkMode() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', isDark ? 'true' : 'false');

    // Update icon
    const icon = document.getElementById('dark-mode-icon');
    if (icon) {
        if (isDark) {
            icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>';
        } else {
            icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>';
        }
    }
}

// ── Mobile Sidebar Toggle ───────────────────────────────────────

function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (!sidebar) return;

    const isOpen = sidebar.classList.contains('open');
    if (isOpen) {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
        document.body.style.overflow = '';
    } else {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

// ── AI Hints (Socratic Questioning) ─────────────────────────────

let currentHintLevel = 0;

function requestHint() {
    const q = studyQuestions[studyIndex];
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

    fetch('/api/study/hint', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({
            question: q.question_text,
            command_term: q.command_term,
            subject: studySubject,
            hint_level: currentHintLevel,
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            if (hintContent) hintContent.textContent = data.error;
        } else {
            if (hintContent) {
                const prevHints = hintContent.innerHTML;
                const newHint = `<div class="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-sm text-blue-700 dark:text-blue-300 mb-2">
                    <span class="text-xs font-bold text-blue-500 dark:text-blue-400">Hint ${currentHintLevel}</span>
                    <p class="mt-1">${escapeHtml(data.hint)}</p>
                </div>`;
                hintContent.innerHTML = prevHints + newHint;
            }
            sessionHintsUsed++;
        }
        if (hintPanel) hintPanel.classList.remove('hidden');
        if (hintCount) hintCount.textContent = `(${currentHintLevel}/3)`;

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

// ── Utility ─────────────────────────────────────────────────────

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ── PWA Install Prompt ──────────────────────────────────────

let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner();
});

function showInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner && !localStorage.getItem('pwa-install-dismissed')) {
        banner.classList.remove('hidden');
    }
}

function installApp() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(() => {
        deferredPrompt = null;
        dismissInstallBanner();
    });
}

function dismissInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) banner.classList.add('hidden');
    localStorage.setItem('pwa-install-dismissed', 'true');
}


// ── Offline/Online Detection ────────────────────────────────

function showOfflineBanner() {
    const banner = document.getElementById('offline-banner');
    if (banner) banner.classList.remove('hidden');
}

function hideOfflineBanner() {
    const banner = document.getElementById('offline-banner');
    if (banner) banner.classList.add('hidden');
}

window.addEventListener('offline', showOfflineBanner);
window.addEventListener('online', hideOfflineBanner);

if (!navigator.onLine) showOfflineBanner();


// ── Notification System ─────────────────────────────────────

function loadNotifications() {
    fetch('/api/notifications')
        .then(res => res.json())
        .then(data => {
            updateNotifBadge(data.unread_count);
            renderNotifications(data.notifications);

            // Browser notification for new unread items
            if (data.unread_count > 0 && 'Notification' in window && Notification.permission === 'granted') {
                const newest = data.notifications.find(n => !n.read);
                if (newest && !sessionStorage.getItem('notif_shown_' + newest.id)) {
                    new Notification('IB Study Companion', {
                        body: newest.title,
                        icon: '/static/icons/icon-192.png',
                    });
                    sessionStorage.setItem('notif_shown_' + newest.id, '1');
                }
            }
        })
        .catch(() => {});
}

function updateNotifBadge(count) {
    const badge = document.getElementById('notif-badge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 9 ? '9+' : count;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notif-list');
    if (!list) return;

    if (!notifications || notifications.length === 0) {
        list.innerHTML = '<p class="text-xs text-slate-500 text-center py-4">No notifications</p>';
        return;
    }

    const iconMap = {
        flashcard_due: '&#128196;',
        streak_risk: '&#128293;',
        weekly_summary: '&#128200;',
        plan_reminder: '&#128197;',
        milestone_due: '&#9200;',
        achievement: '&#127942;',
    };

    list.innerHTML = notifications.map(n => `
        <div class="px-3 py-2.5 hover:bg-slate-700/50 cursor-pointer ${n.read ? 'opacity-60' : ''}"
             onclick="${n.action_url ? `window.location='${n.action_url}'` : `markNotificationRead('${n.id}')`}">
            <div class="flex items-start gap-2">
                <span class="text-sm mt-0.5">${iconMap[n.type] || '&#128276;'}</span>
                <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-slate-200 ${n.read ? '' : 'text-white'}">${escapeHtml(n.title)}</p>
                    <p class="text-xs text-slate-400 mt-0.5 truncate">${escapeHtml(n.body)}</p>
                    <p class="text-[10px] text-slate-500 mt-0.5">${n.created_at ? n.created_at.slice(0, 10) : ''}</p>
                </div>
                ${!n.read ? '<span class="w-2 h-2 bg-indigo-500 rounded-full flex-shrink-0 mt-1"></span>' : ''}
            </div>
        </div>
    `).join('');
}

function toggleNotificationPanel() {
    const panel = document.getElementById('notif-panel');
    if (panel) {
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) {
            loadNotifications();
        }
    }
}

function markNotificationRead(id) {
    fetch('/api/notifications/read', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({ id }),
    }).then(() => loadNotifications());
}

function markAllNotificationsRead() {
    fetch('/api/notifications/read', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({ id: 'all' }),
    }).then(() => loadNotifications());
}

// Request browser notification permission (once, after first study)
function requestNotificationPermission() {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// Load notifications on page load
document.addEventListener('DOMContentLoaded', () => {
    loadNotifications();
});


// ── Question Sharing (Collaboration) ────────────────────────

function shareQuestion() {
    if (typeof studyQuestions === 'undefined' || typeof studyIndex === 'undefined') return;
    const q = studyQuestions[studyIndex];
    if (!q) return;

    const shareData = {
        ib_study_companion_version: '1.0',
        type: 'single_question',
        question_text: q.question_text,
        command_term: q.command_term,
        marks: q.marks,
        topic: q.topic,
        model_answer: q.model_answer,
        subject: typeof studySubject !== 'undefined' ? studySubject : '',
        level: typeof studyLevel !== 'undefined' ? studyLevel : 'HL',
    };

    const jsonStr = JSON.stringify(shareData, null, 2);

    // Try Web Share API first (mobile), fallback to clipboard
    if (navigator.share) {
        navigator.share({
            title: `IB ${shareData.subject} Question`,
            text: jsonStr,
        }).catch(() => copyToClipboard(jsonStr));
    } else {
        copyToClipboard(jsonStr);
    }
}

function exportSessionQuestions() {
    if (typeof studyQuestions === 'undefined' || !studyQuestions.length) {
        showToast('No questions to export');
        return;
    }

    const exportData = {
        ib_study_companion_version: '1.0',
        type: 'question_set',
        subject: typeof studySubject !== 'undefined' ? studySubject : '',
        level: typeof studyLevel !== 'undefined' ? studyLevel : 'HL',
        questions: studyQuestions.map(q => ({
            question_text: q.question_text,
            command_term: q.command_term,
            marks: q.marks,
            topic: q.topic || '',
            model_answer: q.model_answer || '',
        })),
    };

    // Export via API
    fetch('/api/questions/export', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({
            title: `${exportData.subject} Practice Session`,
            description: `${exportData.questions.length} questions`,
            questions: exportData.questions,
            subject: exportData.subject,
            level: exportData.level,
        }),
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const jsonStr = JSON.stringify(data.json_data, null, 2);
            copyToClipboard(jsonStr);
        }
    })
    .catch(() => {
        // Fallback: just copy the raw data
        copyToClipboard(JSON.stringify(exportData, null, 2));
    });
}

function importQuestions() {
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

    // Handle both single question and question set formats
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

    // Import via API
    fetch('/api/questions/import', {
        method: 'POST',
        headers: csrfHeaders(),
        body: JSON.stringify({
            title: data.title || 'Imported Questions',
            description: data.description || '',
            author: data.author || 'Unknown',
            subject: subject,
            topic: data.topic || '',
            level: level,
            questions: questions,
        }),
    })
    .then(res => res.json())
    .then(result => {
        if (result.success) {
            showToast(`Imported ${result.question_count} questions!`);
            // Load them into the study session
            if (typeof studyQuestions !== 'undefined') {
                studyQuestions = questions;
                studyIndex = 0;
                if (typeof studySubject !== 'undefined') studySubject = subject;
                if (typeof studyLevel !== 'undefined') studyLevel = level;
                showSection('study-question');
                displayQuestion();
            }
            input.value = '';
            document.getElementById('study-import-panel').classList.add('hidden');
        } else {
            showToast(result.error || 'Import failed');
        }
    })
    .catch(() => showToast('Import failed'));
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!');
    }).catch(() => {
        // Fallback
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Copied to clipboard!');
    });
}

function showToast(message) {
    // Remove existing toast
    const existing = document.getElementById('app-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.className = 'fixed bottom-24 lg:bottom-6 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-sm px-4 py-2 rounded-lg shadow-lg z-[70] transition-opacity';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}
