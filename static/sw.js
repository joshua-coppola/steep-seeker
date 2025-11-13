const CACHE = "pwabuilder-offline-page";
const offlineFallbackPage = "/offline.html";

importScripts("https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js");

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll([offlineFallbackPage]))
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

// Custom navigation fetch handler
self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          // 1 Try navigation preload
          const preloadResp = await event.preloadResponse;
          if (preloadResp) return preloadResp;

          // 2️ Try network
          const networkResp = await fetch(event.request);
          return networkResp;
        } catch (error) {
          // 3️ If offline: try cached page first
          const cache = await caches.open(CACHE);
          const cachedPage = await cache.match(event.request);
          if (cachedPage) return cachedPage;

          // 4️ If no cached page: fall back to offline.html
          const offlineResp = await cache.match(offlineFallbackPage);
          return offlineResp;
        }
      })()
    );
  }
});
