/**
 * Configuração VAPID para Push Notifications
 * Este arquivo é gerado/atualizado automaticamente pelo servidor
 * 
 * NOTA: A chave pública VAPID é segura para expor no frontend.
 * A chave privada NUNCA deve ser exposta.
 */

// A chave pública será injetada pelo Streamlit via JavaScript
// Este é apenas um fallback caso não seja configurada
window.VAPID_CONFIG = window.VAPID_CONFIG || {
    publicKey: null,
    configured: false
};

// Função para verificar se VAPID está configurado
window.isVapidConfigured = function() {
    return window.VAPID_CONFIG && 
           window.VAPID_CONFIG.publicKey && 
           window.VAPID_CONFIG.publicKey.length > 0;
};

console.log('[VAPID] Config carregado, chave configurada:', window.isVapidConfigured());
