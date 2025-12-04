/**
 * Sistema de Push Notifications - Frontend
 * Ponto ExSA v5.0
 * 
 * Gerencia registro do Service Worker, permissões e subscriptions
 * para notificações push no PWA.
 * 
 * @author Pâmella SAR - Expressão Socioambiental
 * @version 1.0.0
 */

(function() {
    'use strict';

    // Configuração da API
    const API_BASE_URL = window.location.origin;
    const SW_PATH = '/static/sw.js';
    const SW_SCOPE = '/';
    
    // Estado do sistema
    const PushManager = {
        registration: null,
        subscription: null,
        publicKey: null,
        isSupported: false,
        isSubscribed: false,
        currentUser: null
    };

    /**
     * Verifica se Push Notifications são suportadas
     */
    function checkSupport() {
        PushManager.isSupported = (
            'serviceWorker' in navigator &&
            'PushManager' in window &&
            'Notification' in window
        );
        
        if (!PushManager.isSupported) {
            console.warn('[Push] Notificações Push não são suportadas neste navegador');
        }
        
        return PushManager.isSupported;
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
                scope: SW_SCOPE
            });
            
            // Aguardar SW estar pronto
            await navigator.serviceWorker.ready;
            
            PushManager.registration = registration;
            console.log('[Push] Service Worker registrado:', registration.scope);
            
            // Verificar se já existe subscription
            const existingSubscription = await registration.pushManager.getSubscription();
            if (existingSubscription) {
                PushManager.subscription = existingSubscription;
                PushManager.isSubscribed = true;
                console.log('[Push] Subscription existente encontrada');
            }
            
            return registration;
            
        } catch (error) {
            console.error('[Push] Erro ao registrar Service Worker:', error);
            return null;
        }
    }

    /**
     * Obtém a chave pública VAPID do servidor
     */
    async function getVapidPublicKey() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/push/vapid-key`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            PushManager.publicKey = data.publicKey;
            
            console.log('[Push] Chave VAPID obtida');
            return data.publicKey;
            
        } catch (error) {
            console.error('[Push] Erro ao obter chave VAPID:', error);
            return null;
        }
    }

    /**
     * Converte base64 URL para Uint8Array (necessário para applicationServerKey)
     */
    function urlBase64ToUint8Array(base64String) {
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
     * Solicita permissão de notificações ao usuário
     */
    async function requestPermission() {
        if (!checkSupport()) {
            return 'unsupported';
        }

        try {
            const permission = await Notification.requestPermission();
            console.log('[Push] Permissão de notificações:', permission);
            return permission;
            
        } catch (error) {
            console.error('[Push] Erro ao solicitar permissão:', error);
            return 'denied';
        }
    }

    /**
     * Cria uma nova subscription de push
     */
    async function subscribeToPush(usuario) {
        if (!PushManager.registration) {
            console.error('[Push] Service Worker não registrado');
            return null;
        }

        if (!PushManager.publicKey) {
            await getVapidPublicKey();
            if (!PushManager.publicKey) {
                console.error('[Push] Chave VAPID não disponível');
                return null;
            }
        }

        try {
            console.log('[Push] Criando subscription...');
            
            const subscription = await PushManager.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(PushManager.publicKey)
            });

            PushManager.subscription = subscription;
            PushManager.isSubscribed = true;
            PushManager.currentUser = usuario;
            
            console.log('[Push] Subscription criada:', subscription.endpoint);
            
            // Enviar subscription para o servidor
            await sendSubscriptionToServer(usuario, subscription);
            
            return subscription;
            
        } catch (error) {
            console.error('[Push] Erro ao criar subscription:', error);
            return null;
        }
    }

    /**
     * Envia a subscription para o servidor
     */
    async function sendSubscriptionToServer(usuario, subscription) {
        try {
            const subscriptionJson = subscription.toJSON();
            
            const response = await fetch(`${API_BASE_URL}/api/push/subscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    usuario: usuario,
                    endpoint: subscription.endpoint,
                    p256dh: subscriptionJson.keys.p256dh,
                    auth: subscriptionJson.keys.auth
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erro ao salvar subscription');
            }

            const result = await response.json();
            console.log('[Push] Subscription salva no servidor:', result);
            return result;
            
        } catch (error) {
            console.error('[Push] Erro ao enviar subscription ao servidor:', error);
            throw error;
        }
    }

    /**
     * Remove a subscription atual
     */
    async function unsubscribeFromPush() {
        if (!PushManager.subscription) {
            console.warn('[Push] Nenhuma subscription ativa');
            return true;
        }

        try {
            // Remover do servidor primeiro
            await fetch(`${API_BASE_URL}/api/push/unsubscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    endpoint: PushManager.subscription.endpoint
                })
            });

            // Depois remover localmente
            await PushManager.subscription.unsubscribe();
            
            PushManager.subscription = null;
            PushManager.isSubscribed = false;
            
            console.log('[Push] Subscription removida');
            return true;
            
        } catch (error) {
            console.error('[Push] Erro ao remover subscription:', error);
            return false;
        }
    }

    /**
     * Envia uma notificação de teste
     */
    async function sendTestNotification(usuario) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/push/test`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ usuario: usuario })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erro ao enviar teste');
            }

            const result = await response.json();
            console.log('[Push] Notificação de teste enviada:', result);
            return result;
            
        } catch (error) {
            console.error('[Push] Erro ao enviar teste:', error);
            throw error;
        }
    }

    /**
     * Obtém o status do sistema de push para um usuário
     */
    async function getPushStatus(usuario) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/push/status?usuario=${encodeURIComponent(usuario)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error('[Push] Erro ao obter status:', error);
            return null;
        }
    }

    /**
     * Inicializa o sistema de Push completo para um usuário
     * Uso: PontoESA.Push.init('usuario123')
     */
    async function initializePush(usuario) {
        console.log('[Push] Inicializando sistema de push para:', usuario);
        
        // Verificar suporte
        if (!checkSupport()) {
            return {
                success: false,
                error: 'Push notifications não suportadas neste navegador'
            };
        }

        // Registrar Service Worker
        const registration = await registerServiceWorker();
        if (!registration) {
            return {
                success: false,
                error: 'Falha ao registrar Service Worker'
            };
        }

        // Verificar permissão atual
        const currentPermission = Notification.permission;
        
        if (currentPermission === 'denied') {
            return {
                success: false,
                error: 'Permissão de notificações negada. Habilite nas configurações do navegador.'
            };
        }

        // Se já está inscrito, retornar sucesso
        if (PushManager.isSubscribed) {
            console.log('[Push] Usuário já inscrito');
            return {
                success: true,
                status: 'already_subscribed'
            };
        }

        // Solicitar permissão se necessário
        if (currentPermission === 'default') {
            const permission = await requestPermission();
            if (permission !== 'granted') {
                return {
                    success: false,
                    error: 'Permissão de notificações não concedida'
                };
            }
        }

        // Criar subscription
        try {
            await subscribeToPush(usuario);
            return {
                success: true,
                status: 'subscribed'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Mostra modal/dialog para ativar notificações
     * Integra com Streamlit via st.components
     */
    function showEnableNotificationsUI(usuario) {
        // Criar overlay
        const overlay = document.createElement('div');
        overlay.id = 'push-notification-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;

        // Criar modal
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 24px;
            max-width: 400px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        `;

        modal.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 16px;">🔔</div>
            <h2 style="margin: 0 0 12px 0; color: #1a1a2e;">Ativar Notificações</h2>
            <p style="color: #666; margin-bottom: 20px; line-height: 1.5;">
                Receba lembretes quando esquecer de bater o ponto ou quando estiver em hora extra.
            </p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button id="push-enable-btn" style="
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 16px;
                    cursor: pointer;
                    transition: background 0.3s;
                ">Ativar</button>
                <button id="push-cancel-btn" style="
                    background: #f0f0f0;
                    color: #666;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 16px;
                    cursor: pointer;
                ">Agora não</button>
            </div>
            <div id="push-status-msg" style="margin-top: 16px; font-size: 14px;"></div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Event listeners
        document.getElementById('push-enable-btn').addEventListener('click', async () => {
            const statusMsg = document.getElementById('push-status-msg');
            statusMsg.textContent = 'Ativando...';
            statusMsg.style.color = '#666';

            const result = await initializePush(usuario);
            
            if (result.success) {
                statusMsg.textContent = '✅ Notificações ativadas!';
                statusMsg.style.color = '#4CAF50';
                
                setTimeout(() => {
                    overlay.remove();
                }, 1500);
            } else {
                statusMsg.textContent = '❌ ' + result.error;
                statusMsg.style.color = '#f44336';
            }
        });

        document.getElementById('push-cancel-btn').addEventListener('click', () => {
            overlay.remove();
        });

        // Fechar ao clicar fora
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.remove();
            }
        });
    }

    /**
     * Verifica e atualiza UI baseado no status do push
     */
    async function updatePushUI(usuario) {
        const status = await getPushStatus(usuario);
        
        // Emitir evento customizado para Streamlit ou outros listeners
        window.dispatchEvent(new CustomEvent('pushStatusUpdate', {
            detail: {
                usuario: usuario,
                status: status,
                isSupported: PushManager.isSupported,
                isSubscribed: PushManager.isSubscribed
            }
        }));
        
        return status;
    }

    // ==========================================
    // API Pública
    // ==========================================
    
    window.PontoESA = window.PontoESA || {};
    window.PontoESA.Push = {
        // Estado
        isSupported: () => PushManager.isSupported,
        isSubscribed: () => PushManager.isSubscribed,
        
        // Funções principais
        init: initializePush,
        checkSupport: checkSupport,
        registerSW: registerServiceWorker,
        requestPermission: requestPermission,
        subscribe: subscribeToPush,
        unsubscribe: unsubscribeFromPush,
        
        // Utilitários
        getStatus: getPushStatus,
        sendTest: sendTestNotification,
        showEnableUI: showEnableNotificationsUI,
        updateUI: updatePushUI,
        
        // Acesso direto ao estado (somente leitura)
        getState: () => ({ ...PushManager })
    };

    // ==========================================
    // Auto-inicialização
    // ==========================================
    
    // Verificar suporte ao carregar
    checkSupport();
    
    // Registrar SW automaticamente se suportado
    if (PushManager.isSupported) {
        registerServiceWorker().then(() => {
            console.log('[Push] Sistema inicializado');
            
            // Disparar evento de pronto
            window.dispatchEvent(new CustomEvent('pushReady', {
                detail: { supported: true }
            }));
        });
    } else {
        window.dispatchEvent(new CustomEvent('pushReady', {
            detail: { supported: false }
        }));
    }

    console.log('[Push] Módulo de notificações carregado');

})();
