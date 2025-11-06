
// Service Worker para Ponto ExSA PWA
const CACHE_NAME = 'ponto-exsa-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

// Notificações push (futuro)
self.addEventListener('push', function(event) {
  const options = {
    body: event.data ? event.data.text() : 'Nova notificação do Ponto ExSA',
    icon: '/static/icon-192.png',
    badge: '/static/icon-192.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'Abrir App',
        icon: '/static/icon-192.png'
      },
      {
        action: 'close',
        title: 'Fechar',
        icon: '/static/icon-192.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Ponto ExSA', options)
  );
});
