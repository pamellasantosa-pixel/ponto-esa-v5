/**
 * Service Worker para Ponto ExSA PWA
 * Versão com suporte completo a Push Notifications
 * 
 * @version 2.0.0
 * @author Pâmella SAR - Expressão Socioambiental
 */

const CACHE_NAME = 'ponto-exsa-v2';
const CACHE_VERSION = '2.0.0';

// Lista de recursos para cache offline
const STATIC_CACHE = [
    '/',
    '/app/static/manifest.json',
    '/app/static/icon-192.svg',
    '/app/static/icon-512.svg',
    '/app/static/offline.html'
];

// ============================================
// EVENTOS DE INSTALAÇÃO E ATIVAÇÃO
// ============================================

/**
 * Evento de instalação do Service Worker
 * Cacheia recursos estáticos essenciais
 */
self.addEventListener('install', function(event) {
    console.log('[SW] Instalando Service Worker v' + CACHE_VERSION);
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('[SW] Cacheando recursos estáticos');
                return cache.addAll(STATIC_CACHE);
            })
            .then(function() {
                // Força ativação imediata (pula waiting)
                return self.skipWaiting();
            })
            .catch(function(error) {
                console.error('[SW] Erro ao cachear:', error);
            })
    );
});

/**
 * Evento de ativação do Service Worker
 * Limpa caches antigos
 */
self.addEventListener('activate', function(event) {
    console.log('[SW] Ativando Service Worker v' + CACHE_VERSION);
    
    event.waitUntil(
        caches.keys()
            .then(function(cacheNames) {
                return Promise.all(
                    cacheNames
                        .filter(function(cacheName) {
                            return cacheName !== CACHE_NAME;
                        })
                        .map(function(cacheName) {
                            console.log('[SW] Removendo cache antigo:', cacheName);
                            return caches.delete(cacheName);
                        })
                );
            })
            .then(function() {
                // Toma controle de todas as páginas imediatamente
                return self.clients.claim();
            })
    );
});

// ============================================
// ESTRATÉGIA DE CACHE (Network First)
// ============================================

/**
 * Intercepta requisições de rede
 * Estratégia: Network First com fallback para cache
 */
self.addEventListener('fetch', function(event) {
    // Ignorar requisições não-GET
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Ignorar requisições para APIs de streaming do Streamlit
    if (event.request.url.includes('_stcore') || 
        event.request.url.includes('stream') ||
        event.request.url.includes('healthz')) {
        return;
    }
    
    event.respondWith(
        fetch(event.request)
            .then(function(response) {
                // Clonar resposta para cache
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME)
                        .then(function(cache) {
                            cache.put(event.request, responseClone);
                        });
                }
                return response;
            })
            .catch(function() {
                // Fallback para cache se offline
                return caches.match(event.request)
                    .then(function(response) {
                        if (response) {
                            return response;
                        }
                        // Página offline para navegação
                        if (event.request.mode === 'navigate') {
                            return caches.match('/static/offline.html');
                        }
                        return new Response('Offline', { status: 503 });
                    });
            })
    );
});

// ============================================
// PUSH NOTIFICATIONS
// ============================================

/**
 * Evento de recebimento de notificação push
 * Processa dados e exibe a notificação
 */
self.addEventListener('push', function(event) {
    console.log('[SW] Push recebido:', event);
    
    let notificationData = {
        title: 'Ponto ExSA',
        body: 'Nova notificação',
        icon: '/static/icon-192.svg',
        badge: '/static/icon-192.svg',
        tag: 'ponto-exsa-notification',
        requireInteraction: false,
        data: {}
    };
    
    // Tentar parsear dados JSON do push
    if (event.data) {
        try {
            const payload = event.data.json();
            console.log('[SW] Payload recebido:', payload);
            
            notificationData = {
                title: payload.title || notificationData.title,
                body: payload.body || payload.message || notificationData.body,
                icon: payload.icon || notificationData.icon,
                badge: payload.badge || notificationData.badge,
                tag: payload.tag || notificationData.tag,
                requireInteraction: payload.requireInteraction || false,
                data: payload.data || {},
                actions: payload.actions || []
            };
            
            // Adicionar timestamp aos dados
            notificationData.data.timestamp = Date.now();
            notificationData.data.url = payload.url || '/';
            
        } catch (e) {
            // Se não for JSON, usar texto simples
            notificationData.body = event.data.text();
            console.log('[SW] Payload como texto:', notificationData.body);
        }
    }
    
    // Configurar opções da notificação
    const options = {
        body: notificationData.body,
        icon: notificationData.icon,
        badge: notificationData.badge,
        tag: notificationData.tag,
        requireInteraction: notificationData.requireInteraction,
        vibrate: [200, 100, 200, 100, 200],
        data: notificationData.data,
        actions: notificationData.actions.length > 0 ? notificationData.actions : [
            {
                action: 'open',
                title: '📱 Abrir App',
                icon: '/static/icon-192.svg'
            },
            {
                action: 'dismiss',
                title: '❌ Dispensar',
                icon: '/static/icon-192.svg'
            }
        ]
    };
    
    // Exibir notificação
    event.waitUntil(
        self.registration.showNotification(notificationData.title, options)
            .then(function() {
                console.log('[SW] Notificação exibida com sucesso');
            })
            .catch(function(error) {
                console.error('[SW] Erro ao exibir notificação:', error);
            })
    );
});

/**
 * Evento de clique na notificação
 * Abre ou foca o app quando o usuário clica
 */
self.addEventListener('notificationclick', function(event) {
    console.log('[SW] Clique na notificação:', event.action);
    
    // Fechar a notificação
    event.notification.close();
    
    // Tratar ações específicas
    if (event.action === 'dismiss') {
        console.log('[SW] Notificação dispensada pelo usuário');
        return;
    }
    
    // URL para abrir (padrão: raiz do app)
    const urlToOpen = event.notification.data?.url || '/';
    
    // Tentar focar uma janela existente ou abrir nova
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(function(clientList) {
                // Procurar janela já aberta
                for (let i = 0; i < clientList.length; i++) {
                    const client = clientList[i];
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        console.log('[SW] Focando janela existente');
                        return client.focus();
                    }
                }
                // Se não encontrar, abrir nova janela
                if (clients.openWindow) {
                    console.log('[SW] Abrindo nova janela:', urlToOpen);
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

/**
 * Evento de fechamento da notificação (sem clique)
 */
self.addEventListener('notificationclose', function(event) {
    console.log('[SW] Notificação fechada sem interação');
});

// ============================================
// SUBSCRIPTION CHANGE (Renovação automática)
// ============================================

/**
 * Evento disparado quando a subscription muda
 * Útil para re-registrar quando a subscription expira
 */
self.addEventListener('pushsubscriptionchange', function(event) {
    console.log('[SW] Subscription mudou, re-registrando...');
    
    event.waitUntil(
        // Re-inscrever automaticamente
        self.registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(self.VAPID_PUBLIC_KEY)
        })
        .then(function(subscription) {
            console.log('[SW] Nova subscription:', subscription);
            
            // Enviar nova subscription para o servidor
            return fetch('/api/push/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    subscription: subscription.toJSON(),
                    oldEndpoint: event.oldSubscription?.endpoint
                })
            });
        })
        .catch(function(error) {
            console.error('[SW] Erro ao re-registrar subscription:', error);
        })
    );
});

// ============================================
// UTILITÁRIOS
// ============================================

/**
 * Converte chave VAPID de base64url para Uint8Array
 * Necessário para a API de Push
 */
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
    
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// ============================================
// MENSAGENS DO CLIENTE
// ============================================

/**
 * Recebe mensagens da página principal
 * Permite comunicação bidirecional com o app
 */
self.addEventListener('message', function(event) {
    console.log('[SW] Mensagem recebida:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'SET_VAPID_KEY') {
        self.VAPID_PUBLIC_KEY = event.data.key;
        console.log('[SW] VAPID key configurada');
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_VERSION });
    }
});

console.log('[SW] Service Worker carregado - v' + CACHE_VERSION);
