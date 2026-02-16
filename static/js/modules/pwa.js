/**
 * PWA install prompt and offline/online detection.
 */

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
