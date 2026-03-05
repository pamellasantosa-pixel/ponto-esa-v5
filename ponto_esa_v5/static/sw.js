/**
 * Service Worker para Push Notifications - Ponto ExSA v5.0
 */

const SW_VERSION = '3.0.0';

self.addEventListener('install', function(event) {
    console.log('[SW] Instalando v' + SW_VERSION);
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    console.log('[SW] Ativando v' + SW_VERSION);
    event.waitUntil(self.clients.claim());
});

self.addEventListener('push', function(event) {
    console.log('[SW] Push recebido');
    
    let data = {
        title: 'Ponto ExSA',
        body: 'Lembrete de ponto',
        icon: '/favicon.ico',
        tag: 'ponto-exsa'
    };
    
    if (event.data) {
        try {
            const payload = event.data.json();
            data.title = payload.title || data.title;
            data.body = payload.body || payload.message || data.body;
            data.icon = payload.icon || data.icon;
            data.tag = payload.tag || data.tag;
            data.data = payload.data || {};
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon,
            badge: data.icon,
            tag: data.tag,
            vibrate: [200, 100, 200],
            data: data.data || {}
        })
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(function(clientList) {
                for (let client of clientList) {
                    if ('focus' in client) return client.focus();
                }
                if (clients.openWindow) return clients.openWindow('/');
            })
    );
});

console.log('[SW] Carregado v' + SW_VERSION);
