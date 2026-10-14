// bump CACHE_VERSION to throw away every cached asset/page on next activate
// (e.g. if a bad response ever gets stuck in the cache)
const CACHE_VERSION = "v2";
const CACHE = `steep-seeker-assets-${CACHE_VERSION}`;
const PAGES_CACHE = `steep-seeker-pages-${CACHE_VERSION}`;
const offlineFallbackPage = "/offline.html";

// offline.html plus everything it needs to render, so the fallback is styled
// even if the user never loaded these assets while online
const PRECACHE_URLS = [
  offlineFallbackPage,
  "/base.css",
  "/page.css",
  "/index.css",
  "/logo.svg",
  "/hamburger-menu.svg",
];

importScripts("https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js");

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  // activate immediately rather than waiting for every open tab to close
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // drop caches from older versions of this worker
      const keep = [CACHE, PAGES_CACHE];
      for (const name of await caches.keys()) {
        if (!keep.includes(name)) await caches.delete(name);
      }
      // take control of already-open pages, so the first visit's requests
      // get cached instead of only the ones after the next navigation
      await self.clients.claim();
    })()
  );
});

if (workbox.navigationPreload.isSupported()) {
  workbox.navigationPreload.enable();
}

// Use Workbox only for static assets (not navigation)
workbox.routing.registerRoute(
  ({ request }) => request.destination !== "document",
  new workbox.strategies.StaleWhileRevalidate({
    cacheName: CACHE,
  })
);

// Custom navigation fetch handler: network first, saving each successful page
// so it can be served later when offline
self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          // 1 Try navigation preload, then the network
          const response =
            (await event.preloadResponse) || (await fetch(event.request));

          // 2 Save a copy for offline use
          if (response.ok) {
            const copy = response.clone();
            event.waitUntil(
              caches.open(PAGES_CACHE).then((cache) => cache.put(event.request, copy))
            );
          }
          return response;
        } catch (error) {
          // 3 If offline: try cached page first
          const cachedPage = await caches.match(event.request, {
            cacheName: PAGES_CACHE,
          });
          if (cachedPage) return cachedPage;

          // 4 If no cached page: fall back to offline.html
          return caches.match(offlineFallbackPage, { cacheName: CACHE });
        }
      })()
    );
  }
});
