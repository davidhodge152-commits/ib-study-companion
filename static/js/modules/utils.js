/**
 * Shared utilities: constants, escapeHtml, showToast, copyToClipboard,
 * dark mode toggle, mobile sidebar toggle.
 */

// ── Command Term Definitions ──────────────────────────────────────

export const COMMAND_TERM_DEFINITIONS = {
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

// ── Utility functions ─────────────────────────────────────────────

export function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function showToast(message, options = {}) {
    const { variant = 'default', duration = 2500, action = null } = typeof options === 'object' ? options : {};

    const existing = document.getElementById('app-toast');
    if (existing) existing.remove();

    const variantClasses = {
        default: 'bg-slate-800 dark:bg-slate-700 text-white',
        success: 'bg-green-600 text-white',
        warning: 'bg-amber-500 text-white',
        danger: 'bg-red-600 text-white',
    };

    const toast = document.createElement('div');
    toast.id = 'app-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.className = `fixed bottom-24 lg:bottom-6 left-1/2 -translate-x-1/2 ${variantClasses[variant] || variantClasses.default} text-sm px-4 py-2.5 rounded-lg shadow-lg z-[70] animate-slide-up flex items-center gap-3`;

    const textSpan = document.createElement('span');
    textSpan.textContent = message;
    toast.appendChild(textSpan);

    if (action && action.text && action.onclick) {
        const btn = document.createElement('button');
        btn.textContent = action.text;
        btn.className = 'font-semibold underline hover:no-underline';
        btn.onclick = action.onclick;
        toast.appendChild(btn);
    }

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 300ms';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

export function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!');
    }).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        showToast('Copied to clipboard!');
    });
}

// ── Dark Mode Toggle ──────────────────────────────────────────────

export function toggleDarkMode() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', isDark ? 'true' : 'false');

    const icon = document.getElementById('dark-mode-icon');
    if (icon) {
        if (isDark) {
            icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>';
        } else {
            icon.innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>';
        }
    }
}

// ── Mobile Sidebar Toggle ─────────────────────────────────────────

export function toggleMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const menuBtn = document.getElementById('mobile-menu-btn');
    if (!sidebar) return;

    const isOpen = sidebar.classList.contains('open');
    if (isOpen) {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
        document.body.style.overflow = '';
        if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
    } else {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
        if (menuBtn) menuBtn.setAttribute('aria-expanded', 'true');
    }
}
