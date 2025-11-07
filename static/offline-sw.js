
const CACHE_NAME = 'ponto-exsa-offline-v1';
const urlsToCache = [
    '/',
    '/static/manifest.json',
    '/static/Exsafundo.jpg',
    '/static/icon-192.png',
    '/static/icon-512.png'
];

// Instalar service worker
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                return cache.addAll(urlsToCache);
            })
    );
});

// Interceptar requisições
self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                // Retornar do cache se disponível
                if (response) {
                    return response;
                }
                
                // Tentar buscar online
                return fetch(event.request).catch(function() {
                    // Se offline, retornar página offline
                    if (event.request.destination === 'document') {
                        return caches.match('/offline.html');
                    }
                });
            })
    );
});

// Sincronização em background
self.addEventListener('sync', function(event) {
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

function doBackgroundSync() {
    return fetch('/api/sync', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: 'sync_offline_data'
        })
    });
}
