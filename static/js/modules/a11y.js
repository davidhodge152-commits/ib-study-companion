/**
 * Accessibility module — focus trapping, modal management,
 * screen reader announcements, skip links, dyslexic font toggle.
 */

// ── Focus Trap Stack ────────────────────────────────────────────────

const focusTrapStack = [];

const FOCUSABLE_SELECTOR = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])', '[role="button"]',
].join(', ');

export function trapFocus(element) {
    const previouslyFocused = document.activeElement;
    focusTrapStack.push({ element, previouslyFocused });

    function handleKeyDown(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            const modalId = element.id;
            if (modalId) closeModal(modalId);
            return;
        }

        if (e.key !== 'Tab') return;

        const focusable = Array.from(element.querySelectorAll(FOCUSABLE_SELECTOR));
        if (focusable.length === 0) {
            e.preventDefault();
            return;
        }

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
            if (document.activeElement === first) {
                e.preventDefault();
                last.focus();
            }
        } else {
            if (document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
    }

    element._focusTrapHandler = handleKeyDown;
    element.addEventListener('keydown', handleKeyDown);

    // Focus first focusable element
    const focusable = element.querySelectorAll(FOCUSABLE_SELECTOR);
    if (focusable.length > 0) {
        focusable[0].focus();
    }
}

export function releaseFocus() {
    const entry = focusTrapStack.pop();
    if (!entry) return;

    const { element, previouslyFocused } = entry;
    if (element._focusTrapHandler) {
        element.removeEventListener('keydown', element._focusTrapHandler);
        delete element._focusTrapHandler;
    }

    if (previouslyFocused && previouslyFocused.focus) {
        previouslyFocused.focus();
    }
}

// ── Modal Management ────────────────────────────────────────────────

export function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    trapFocus(modal);
    announce(modal.querySelector('[id$="-title"]')?.textContent || 'Dialog opened');

    // Close on backdrop click
    modal._backdropHandler = (e) => {
        if (e.target === modal) closeModal(id);
    };
    modal.addEventListener('click', modal._backdropHandler);
}

export function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;

    modal.classList.add('hidden');
    document.body.style.overflow = '';
    releaseFocus();

    if (modal._backdropHandler) {
        modal.removeEventListener('click', modal._backdropHandler);
        delete modal._backdropHandler;
    }
}

// ── Screen Reader Announcements ─────────────────────────────────────

let announceEl = null;

export function announce(message, priority = 'polite') {
    if (!announceEl) {
        announceEl = document.createElement('div');
        announceEl.className = 'sr-only';
        announceEl.setAttribute('aria-live', priority);
        announceEl.setAttribute('aria-atomic', 'true');
        document.body.appendChild(announceEl);
    }
    announceEl.setAttribute('aria-live', priority);
    // Clear then set to trigger announcement
    announceEl.textContent = '';
    requestAnimationFrame(() => {
        announceEl.textContent = message;
    });
}

// ── Skip Link ───────────────────────────────────────────────────────

export function initSkipLink() {
    if (document.getElementById('skip-link')) return;

    const skip = document.createElement('a');
    skip.id = 'skip-link';
    skip.href = '#main-content';
    skip.className = 'sr-only sr-only-focusable fixed top-2 left-2 z-[100] bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium';
    skip.textContent = 'Skip to main content';
    document.body.prepend(skip);
}

// ── Dyslexic Font Toggle ────────────────────────────────────────────

export function toggleDyslexicFont() {
    const isActive = document.documentElement.classList.toggle('font-dyslexic');
    localStorage.setItem('dyslexicFont', isActive ? 'true' : 'false');
    announce(isActive ? 'Dyslexia-friendly font enabled' : 'Standard font restored');
}

function restoreDyslexicFont() {
    if (localStorage.getItem('dyslexicFont') === 'true') {
        document.documentElement.classList.add('font-dyslexic');
    }
}

// ── Init on DOM ready ───────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initSkipLink();
    restoreDyslexicFont();
});
