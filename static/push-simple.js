/**
 * Sistema de Push Notifications - Versão Simplificada para Streamlit
 * Ponto ExSA v5.0
 * 
 * Esta versão funciona sem servidor Flask separado.
 * As subscriptions são salvas via sessionStorage/localStorage
 * e enviadas ao servidor Streamlit quando necessário.
 * 
 * @author Pâmella SAR - Expressão Socioambiental
 * @version 2.0.0
 */

(function() {
    'use strict';

    // Namespace global
    window.PontoESA = window.PontoESA || {};

    const SW_PATH = '/static/sw.js';
    const STORAGE_KEY = 'ponto_exsa_push_subscription';

    // Estado do sistema
    const State = {
        registration: null,
        subscription: null,
        publicKey: null,
        isSupported: false,
        isSubscribed: false,
        currentUser: null,
        ready: false
    };

    /**
     * Verifica suporte a Push Notifications
     */
    function checkSupport() {
        State.isSupported = (
            'serviceWorker' in navigator &&
            'PushManager' in window &&
            'Notification' in window
        );
        
        if (!State.isSupported) {
            console.warn('[Push] Notificações Push não são suportadas neste navegador');
        }
        
        return State.isSupported;
    }

    /**
     * Converte base64 URL para Uint8Array
     */
    function urlBase64ToUint8Array(base64String) {
        if (!base64String) return null;
        
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    /**
     * Registra o Service Worker
     */
    async function registerServiceWorker() {
        if (!checkSupport()) {
            return null;
        }

        try {
            console.log('[Push] Registrando Service Worker...');
            
            const registration = await navigator.serviceWorker.register(SW_PATH, {
                scope: '/'
            });
            
            // Aguardar SW estar pronto
            await navigator.serviceWorker.ready;
            
            State.registration = registration;
            console.log('[Push] Service Worker registrado:', registration.scope);
            
            // Verificar subscription existente
            const existingSubscription = await registration.pushManager.getSubscription();
            if (existingSubscription) {
                State.subscription = existingSubscription;
                State.isSubscribed = true;
                console.log('[Push] Subscription existente encontrada');
                
                // Restaurar usuário do localStorage
                const savedUser = localStorage.getItem('ponto_exsa_push_user');
                if (savedUser) {
                    State.currentUser = savedUser;
                }
            }
            
            return registration;
            
        } catch (error) {
            console.error('[Push] Erro ao registrar Service Worker:', error);
            return null;
        }
    }

    /**
     * Obtém a chave VAPID do window (injetada pelo Streamlit)
     */
    function getVapidPublicKey() {
        // Tentar pegar do window.VAPID_CONFIG (injetado pelo Streamlit)
        if (window.VAPID_CONFIG && window.VAPID_CONFIG.publicKey) {
            State.publicKey = window.VAPID_CONFIG.publicKey;
            console.log('[Push] Chave VAPID obtida do config');
            return State.publicKey;
        }
        
        // Tentar pegar do localStorage (backup)
        const savedKey = localStorage.getItem('ponto_exsa_vapid_key');
        if (savedKey) {
            State.publicKey = savedKey;
            console.log('[Push] Chave VAPID obtida do localStorage');
            return State.publicKey;
        }
        
        console.error('[Push] Chave VAPID não configurada');
        return null;
    }

    /**
     * Solicita permissão de notificações
     */
    async function requestPermission() {
        if (!checkSupport()) {
            return 'unsupported';
        }

        try {
            const permission = await Notification.requestPermission();
            console.log('[Push] Permissão:', permission);
            return permission;
            
        } catch (error) {
            console.error('[Push] Erro ao solicitar permissão:', error);
            return 'denied';
        }
    }

    /**
     * Cria subscription de push
     */
    async function subscribe(usuario) {
        if (!State.registration) {
            await registerServiceWorker();
            if (!State.registration) {
                return { success: false, error: 'Service Worker não registrado' };
            }
        }

        // Obter chave VAPID
        const publicKey = getVapidPublicKey();
        if (!publicKey) {
            return { success: false, error: 'Chave VAPID não configurada. Contate o administrador.' };
        }

        // Solicitar permissão
        const permission = await requestPermission();
        if (permission !== 'granted') {
            return { success: false, error: 'Permissão de notificações negada' };
        }

        try {
            console.log('[Push] Criando subscription...');
            
            const subscription = await State.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(publicKey)
            });

            State.subscription = subscription;
            State.isSubscribed = true;
            State.currentUser = usuario;
            
            // Salvar no localStorage
            localStorage.setItem('ponto_exsa_push_user', usuario);
            
            // Salvar subscription para enviar ao servidor
            const subscriptionJson = subscription.toJSON();
            const subscriptionData = {
                usuario: usuario,
                endpoint: subscription.endpoint,
                p256dh: subscriptionJson.keys.p256dh,
                auth: subscriptionJson.keys.auth,
                created_at: new Date().toISOString()
            };
            
            localStorage.setItem(STORAGE_KEY, JSON.stringify(subscriptionData));
            
            // Tentar enviar para API do servidor (se disponível)
            try {
                const apiUrl = window.location.origin + '/api/push/subscribe';
                const response = await fetch(apiUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        usuario: usuario,
                        subscription: {
                            endpoint: subscription.endpoint,
                            keys: {
                                p256dh: subscriptionJson.keys.p256dh,
                                auth: subscriptionJson.keys.auth
                            }
                        },
                        userAgent: navigator.userAgent,
                        deviceInfo: navigator.platform || 'Unknown'
                    })
                });
                
                if (response.ok) {
                    console.log('[Push] Subscription salva no servidor com sucesso');
                } else {
                    console.log('[Push] API não disponível, subscription salva apenas localmente');
                }
            } catch (apiError) {
                // API não disponível - subscriptions funcionarão apenas localmente
                console.log('[Push] Servidor API não disponível:', apiError.message);
            }
            
            // Disparar evento para o Streamlit capturar
            window.dispatchEvent(new CustomEvent('pushSubscribed', {
                detail: subscriptionData
            }));
            
            console.log('[Push] Subscription criada com sucesso');
            
            // Mostrar notificação de teste
            showTestNotification();
            
            return { success: true, subscription: subscriptionData };
            
        } catch (error) {
            console.error('[Push] Erro ao criar subscription:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Remove subscription
     */
    async function unsubscribe() {
        if (!State.subscription) {
            return { success: true, message: 'Nenhuma subscription ativa' };
        }

        try {
            await State.subscription.unsubscribe();
            
            State.subscription = null;
            State.isSubscribed = false;
            State.currentUser = null;
            
            localStorage.removeItem(STORAGE_KEY);
            localStorage.removeItem('ponto_exsa_push_user');
            
            console.log('[Push] Subscription removida');
            return { success: true };
            
        } catch (error) {
            console.error('[Push] Erro ao remover subscription:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Mostra notificação de teste local
     */
    function showTestNotification() {
        if (State.registration && Notification.permission === 'granted') {
            State.registration.showNotification('🎉 Notificações Ativadas!', {
                body: 'Você receberá lembretes de ponto no Ponto ExSA.',
                icon: '/static/icon-192.svg',
                badge: '/static/icon-192.svg',
                tag: 'ponto-exsa-test',
                vibrate: [200, 100, 200]
            });
        }
    }

    /**
     * Mostra UI de ativação de push
     */
    function showEnableUI(usuario) {
        // Criar modal de ativação
        const modal = document.createElement('div');
        modal.id = 'push-enable-modal';
        modal.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
            ">
                <div style="
                    background: white;
                    border-radius: 16px;
                    padding: 30px;
                    max-width: 400px;
                    text-align: center;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    animation: slideIn 0.3s ease;
                ">
                    <div style="font-size: 48px; margin-bottom: 15px;">🔔</div>
                    <h2 style="margin: 0 0 10px; color: #333;">Ativar Notificações?</h2>
                    <p style="color: #666; margin-bottom: 20px; font-size: 14px;">
                        Receba lembretes para registrar seu ponto e nunca mais esqueça!
                    </p>
                    <div style="display: flex; gap: 10px; justify-content: center;">
                        <button id="push-enable-yes" style="
                            background: linear-gradient(135deg, #4CAF50, #45a049);
                            color: white;
                            border: none;
                            padding: 12px 24px;
                            border-radius: 8px;
                            font-size: 14px;
                            cursor: pointer;
                            flex: 1;
                        ">✅ Sim, ativar!</button>
                        <button id="push-enable-no" style="
                            background: #f5f5f5;
                            color: #666;
                            border: none;
                            padding: 12px 24px;
                            border-radius: 8px;
                            font-size: 14px;
                            cursor: pointer;
                            flex: 1;
                        ">Agora não</button>
                    </div>
                </div>
            </div>
            <style>
                @keyframes slideIn {
                    from { opacity: 0; transform: scale(0.9); }
                    to { opacity: 1; transform: scale(1); }
                }
            </style>
        `;
        
        document.body.appendChild(modal);
        
        // Event listeners
        document.getElementById('push-enable-yes').onclick = async () => {
            const btn = document.getElementById('push-enable-yes');
            btn.disabled = true;
            btn.innerHTML = '⏳ Ativando...';
            
            const result = await subscribe(usuario);
            
            if (result.success) {
                modal.remove();
            } else {
                btn.innerHTML = '❌ Erro';
                setTimeout(() => modal.remove(), 2000);
            }
        };
        
        document.getElementById('push-enable-no').onclick = () => {
            modal.remove();
        };
    }

    /**
     * Obtém estado atual
     */
    function getState() {
        return {
            isSupported: State.isSupported,
            isSubscribed: State.isSubscribed,
            currentUser: State.currentUser,
            ready: State.ready,
            hasPermission: Notification.permission === 'granted'
        };
    }

    /**
     * Obtém subscription salva
     */
    function getSavedSubscription() {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : null;
    }

    /**
     * Inicializa o sistema
     */
    async function init(usuario) {
        console.log('[Push] Inicializando sistema de push...');
        
        checkSupport();
        
        if (!State.isSupported) {
            return { success: false, error: 'Push não suportado' };
        }
        
        await registerServiceWorker();
        
        if (State.isSubscribed) {
            console.log('[Push] Já inscrito');
            return { success: true, alreadySubscribed: true };
        }
        
        return await subscribe(usuario);
    }

    // Expor API pública
    window.PontoESA.Push = {
        init: init,
        subscribe: subscribe,
        unsubscribe: unsubscribe,
        getState: getState,
        getSavedSubscription: getSavedSubscription,
        showEnableUI: showEnableUI,
        requestPermission: requestPermission,
        checkSupport: checkSupport
    };

    // Auto-inicializar
    (async function() {
        checkSupport();
        
        if (State.isSupported) {
            await registerServiceWorker();
        }
        
        State.ready = true;
        
        // Disparar evento de pronto
        window.dispatchEvent(new Event('pushReady'));
        
        console.log('[Push] Sistema pronto. Suportado:', State.isSupported, 'Inscrito:', State.isSubscribed);
    })();

})();
