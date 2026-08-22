const CACHE_VERSION = 'v2';
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const PAGES_CACHE = `pages-${CACHE_VERSION}`;

const STATIC_ASSETS = [
    '/static/css/style.css',
    '/static/images/favicon.svg',
    '/static/images/favicon-192.png',
    '/static/images/favicon-512.png',
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        }).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((key) => key !== STATIC_CACHE && key !== PAGES_CACHE)
                    .map((key) => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (e) => {
    const { request } = e;
    const url = new URL(request.url);

    // Never cache admin paths, API calls, or POST/PUT/DELETE requests
    if (
        url.pathname.startsWith('/admin') ||
        url.pathname.startsWith('/api') ||
        request.method !== 'GET'
    ) {
        e.respondWith(fetch(request).catch(() =>
            new Response('Offline — this operation requires a network connection.', {
                status: 503,
                headers: { 'Content-Type': 'text/plain' },
            })
        ));
        return;
    }

    // Cache-first for static assets (CSS, JS, images)
    if (url.pathname.startsWith('/static')) {
        e.respondWith(
            caches.match(request).then((cached) => {
                return cached || fetch(request).then((response) => {
                    if (response.ok) {
                        // Clone now, synchronously — once this response is returned the page
                        // consumes its body, and a clone taken after that throws.
                        const copy = response.clone();
                        e.waitUntil(caches.open(STATIC_CACHE).then((c) => c.put(request, copy)));
                    }
                    return response;
                });
            })
        );
        return;
    }

    // Network-first for pages (HTML, student-facing content)
    e.respondWith(
        fetch(request)
            .then((response) => {
                if (response.ok) {
                    const copy = response.clone();
                    e.waitUntil(caches.open(PAGES_CACHE).then((c) => c.put(request, copy)));
                }
                return response;
            })
            .catch(() => {
                return caches.match(request).then((cached) => {
                    return cached || new Response('Offline — page not cached.', {
                        status: 503,
                        headers: { 'Content-Type': 'text/plain' },
                    });
                });
            })
    );
});
