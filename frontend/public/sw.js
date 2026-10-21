const CACHE_NAME = "nomica-shell-v1";
const APP_SHELL = ["/", "/manifest.webmanifest", "/app-icon-192.png", "/app-icon-512.png", "/apple-touch-icon.png", "/favicon.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
});

self.addEventListener("fetch", (event) => {
  const requestUrl = new URL(event.request.url);

  // Auth requests must always reach the network, never an offline shell/cache.
  if (requestUrl.pathname.startsWith("/api") || requestUrl.pathname.startsWith("/line-login-")
      || requestUrl.pathname === "/auth-callback") {
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/"))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => cachedResponse || fetch(event.request))
  );
});
