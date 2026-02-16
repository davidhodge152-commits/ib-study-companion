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

    return res;
}

export const api = {
    get: (url) => apiFetch(url),
    post: (url, data) => apiFetch(url, { method: 'POST', body: JSON.stringify(data) }),
    postForm: (url, formData) => apiFetch(url, { method: 'POST', body: formData }),
    delete: (url) => apiFetch(url, { method: 'DELETE' }),
};
