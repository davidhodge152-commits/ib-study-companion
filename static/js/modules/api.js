/**
 * Centralized API client with auth redirect on 401.
 */

async function apiFetch(url, options = {}) {
    const defaults = {
        headers: { 'Content-Type': 'application/json' },
    };

    // Don't set Content-Type for FormData (browser sets boundary automatically)
    if (options.body instanceof FormData) {
        delete defaults.headers['Content-Type'];
    }

    const merged = { ...defaults, ...options };
    if (options.headers && defaults.headers) {
        merged.headers = { ...defaults.headers, ...options.headers };
    }

    const res = await fetch(url, merged);

    if (res.status === 401) {
        window.location.href = '/login';
        throw new Error('Authentication required');
    }

    if (res.status === 402) {
        showUpgradeModal('credits');
        throw new Error('Insufficient credits');
    }

    if (res.status === 403) {
        try {
            const body = await res.clone().json();
            if (body.required_plan) {
                showUpgradeModal('plan', body.required_plan);
                throw new Error(`Upgrade to ${body.required_plan} required`);
            }
        } catch (e) {
            if (e.message.startsWith('Upgrade to')) throw e;
        }
    }

    return res;
}

function showUpgradeModal(type, planName) {
    // Remove any existing modal
    const existing = document.getElementById('upgrade-modal');
    if (existing) existing.remove();

    const isCredits = type === 'credits';
    const title = isCredits ? 'Insufficient Credits' : 'Upgrade Required';
    const message = isCredits
        ? 'You don\'t have enough credits for this action. Purchase more credits or upgrade your plan for higher limits.'
        : `This feature requires the <strong>${planName}</strong> plan or higher.`;
    const btnText = isCredits ? 'Buy Credits' : 'View Plans';

    const modal = document.createElement('div');
    modal.id = 'upgrade-modal';
    modal.className = 'fixed inset-0 z-[100] flex items-center justify-center bg-black/50';
    modal.innerHTML = `
        <div class="bg-white dark:bg-slate-800 rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
            <h3 class="text-lg font-bold text-slate-800 dark:text-slate-200 mb-2">${title}</h3>
            <p class="text-sm text-slate-600 dark:text-slate-400 mb-4">${message}</p>
            <div class="flex gap-3">
                <a href="/pricing" class="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg text-center transition-colors">${btnText}</a>
                <button onclick="this.closest('#upgrade-modal').remove()" class="px-4 py-2.5 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-300 text-sm rounded-lg hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors">Dismiss</button>
            </div>
        </div>`;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

/**
 * The api export is both callable as a function — api(url, options) — and has
 * convenience methods: api.get(), api.post(), api.postForm(), api.delete().
 */
export async function api(url, options = {}) {
    return apiFetch(url, options);
}
api.get = (url) => apiFetch(url);
api.post = (url, data) => apiFetch(url, { method: 'POST', body: JSON.stringify(data) });
api.postForm = (url, formData) => apiFetch(url, { method: 'POST', body: formData });
api.delete = (url) => apiFetch(url, { method: 'DELETE' });
