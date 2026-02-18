const CACHE_NAME = 'ib-study-v7';
const FLASHCARD_CACHE = 'ib-flashcards-v1';

const STATIC_ASSETS = [
  '/static/app.js',
  '/static/js/app.js',
  '/static/js/modules/api.js',
  '/static/js/modules/study.js',
  '/static/js/modules/a11y.js',
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

const CACHEABLE_PAGES = [
  '/dashboard',
  '/study',
  '/flashcards',
  '/insights',
  '/planner',
];

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  const keepCaches = [CACHE_NAME, FLASHCARD_CACHE];
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => !keepCaches.includes(key)).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: route-based strategy selection
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // API calls that require server: network only
  if (url.pathname.startsWith('/api/study/generate') ||
      url.pathname.startsWith('/api/study/grade') ||
      url.pathname.startsWith('/api/upload') ||
      url.pathname.startsWith('/api/analytics') ||
      url.pathname.startsWith('/api/lifecycle')) {
    return;
  }

  // Flashcard API: stale-while-revalidate
  if (url.pathname.startsWith('/api/flashcards')) {
    event.respondWith(staleWhileRevalidate(event.request));
    return;
  }

  // Static assets: cache first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // CDN assets (Tailwind, Chart.js, Google Fonts): cache first with opaque fallback
  if (url.origin !== self.location.origin) {
    event.respondWith(cacheFirstCDN(event.request));
    return;
  }

  // Page routes: network first with cache fallback
  if (CACHEABLE_PAGES.includes(url.pathname) || url.pathname === '/') {
    event.respondWith(networkFirst(event.request));
    return;
  }
});

// Cache First strategy (for static assets)
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('Offline', { status: 503 });
  }
}

// Cache First for CDN (opaque responses OK)
async function cacheFirstCDN(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    // Cache even opaque responses (type === 'opaque')
    if (response.status === 0 || response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 503 });
  }
}

// Network First strategy (for pages)
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(
      '<html><body style="font-family:Inter,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#f8fafc;color:#64748b;"><div style="text-align:center"><h1>You\'re Offline</h1><p>Check your connection and try again.</p></div></body></html>',
      { headers: { 'Content-Type': 'text/html' }, status: 503 }
    );
  }
}

// Stale-While-Revalidate (for flashcard data)
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cached);

  return cached || fetchPromise;
}

// Push notification handler
self.addEventListener('push', (event) => {
  let data = { title: 'IB Study Companion', body: 'You have a new notification' };
  try {
    data = event.data.json();
  } catch (e) {
    data.body = event.data ? event.data.text() : data.body;
  }

  const options = {
    body: data.body,
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    data: { url: data.url || '/' },
    actions: [{ action: 'open', title: 'Open' }],
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/';
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

// Background sync: flush queued flashcard reviews when back online
self.addEventListener('sync', (event) => {
  if (event.tag === 'flashcard-review-sync') {
    event.waitUntil(syncFlashcardReviews());
  }
});

async function syncFlashcardReviews() {
  const cache = await caches.open(FLASHCARD_CACHE);
  const queueReq = new Request('/_offline_queue/flashcard-reviews');
  const queueRes = await cache.match(queueReq);
  if (!queueRes) return;

  const reviews = await queueRes.json();
  const remaining = [];

  for (const review of reviews) {
    try {
      const res = await fetch('/api/flashcards/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(review),
      });
      if (!res.ok) remaining.push(review);
    } catch {
      remaining.push(review);
    }
  }

  if (remaining.length > 0) {
    await cache.put(queueReq, new Response(JSON.stringify(remaining)));
  } else {
    await cache.delete(queueReq);
  }
}
