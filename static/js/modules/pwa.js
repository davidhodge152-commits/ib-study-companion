/**
 * PWA install prompt (with visit-count gating), offline/online detection,
 * and pull-to-refresh on dashboard.
 */

// ── PWA Install Prompt (show after 3+ visits) ──────────────

let deferredPrompt = null;

// Track visit count
const visitCount = parseInt(localStorage.getItem('pwa-visit-count') || '0', 10) + 1;
localStorage.setItem('pwa-visit-count', String(visitCount));

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;

    // Only show after 3+ visits, not previously dismissed, with 5s delay
    if (visitCount >= 3 && !localStorage.getItem('pwa-install-dismissed')) {
        setTimeout(() => showInstallBanner(), 5000);
    }
});

function showInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner && deferredPrompt) {
        banner.classList.remove('hidden');
    }
}

export function installApp() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(() => {
        deferredPrompt = null;
        dismissInstallBanner();
    });
}

export function dismissInstallBanner() {
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

// ── Pull-to-Refresh on Dashboard ────────────────────────────

function initPullToRefresh() {
    const main = document.getElementById('main-content');
    if (!main) return;

    let startY = 0;
    let pulling = false;
    let indicator = null;

    main.addEventListener('touchstart', (e) => {
        if (main.scrollTop === 0) {
            startY = e.touches[0].clientY;
            pulling = true;
        }
    }, { passive: true });

    main.addEventListener('touchmove', (e) => {
        if (!pulling) return;
        const dy = e.touches[0].clientY - startY;
        if (dy > 0 && main.scrollTop === 0) {
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.className = 'fixed top-0 left-0 right-0 z-[70] text-center py-2 text-sm font-medium text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-950 transition-transform';
                indicator.textContent = 'Pull to refresh...';
                document.body.appendChild(indicator);
            }
            const progress = Math.min(dy / 80, 1);
            indicator.style.transform = `translateY(${Math.min(dy * 0.4, 60)}px)`;
            indicator.style.opacity = progress;
            if (dy > 80) {
                indicator.textContent = 'Release to refresh';
            } else {
                indicator.textContent = 'Pull to refresh...';
            }
        }
    }, { passive: true });

    main.addEventListener('touchend', (e) => {
        if (!pulling) return;
        pulling = false;
        const dy = e.changedTouches[0].clientY - startY;

        if (indicator) {
            indicator.remove();
            indicator = null;
        }

        if (dy > 80 && main.scrollTop === 0) {
            window.location.reload();
        }
    }, { passive: true });
}

document.addEventListener('DOMContentLoaded', initPullToRefresh);
