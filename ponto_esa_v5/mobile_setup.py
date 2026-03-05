"""
Configuração Progressive Web App (PWA) para Ponto ESA
Permite que o aplicativo funcione como um app nativo no celular
"""

import streamlit as st
import json
import os

def setup_pwa():
    """
    Configura o aplicativo como Progressive Web App
    """
    
    # Manifest.json para PWA
    manifest = {
        "name": "Ponto ExSA - Sistema de Controle de Ponto",
        "short_name": "Ponto ExSA",
        "description": "Sistema de controle de ponto centralizado da Expressão Socioambiental",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#87CEEB",
        "theme_color": "#2C3E50",
        "orientation": "portrait",
        "scope": "/",
        "icons": [
            {
                "src": "static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ],
        "categories": ["business", "productivity"],
        "lang": "pt-BR",
        "dir": "ltr"
    }
    
    # Salvar manifest
    os.makedirs("static", exist_ok=True)
    with open("static/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    # Service Worker para funcionalidade offline
    service_worker = """
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
"""
    
    with open("static/sw.js", "w", encoding="utf-8") as f:
        f.write(service_worker)
    
    return True

def get_pwa_html():
    """
    Retorna HTML adicional para PWA
    """
    return """
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#2C3E50">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Ponto ExSA">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <meta name="msapplication-TileImage" content="/static/icon-192.png">
    <meta name="msapplication-TileColor" content="#2C3E50">
    
    <script>
    // Registrar Service Worker
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js')
          .then(function(registration) {
            console.log('SW registered: ', registration);
          }, function(registrationError) {
            console.log('SW registration failed: ', registrationError);
          });
      });
    }
    
    // Prompt de instalação PWA
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      
      // Mostrar botão de instalação personalizado
      const installButton = document.createElement('button');
      installButton.textContent = '📱 Instalar App';
      installButton.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(45deg, #2C3E50, #34495E);
        color: white;
        border: none;
        padding: 12px 20px;
        border-radius: 25px;
        font-weight: bold;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        cursor: pointer;
        z-index: 1000;
        font-size: 14px;
      `;
      
      installButton.addEventListener('click', () => {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then((choiceResult) => {
          if (choiceResult.outcome === 'accepted') {
            console.log('User accepted the install prompt');
          }
          deferredPrompt = null;
          installButton.remove();
        });
      });
      
      document.body.appendChild(installButton);
    });
    </script>
    """

def create_mobile_icons():
    """
    Cria ícones para o aplicativo mobile usando CSS/SVG
    """
    
    # Ícone 192x192
    icon_192_svg = """
    <svg width="192" height="192" viewBox="0 0 192 192" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#3498DB;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#2980B9;stop-opacity:1" />
        </linearGradient>
      </defs>
      <circle cx="96" cy="96" r="96" fill="url(#grad1)"/>
      <text x="96" y="110" font-family="Arial, sans-serif" font-size="48" font-weight="bold" 
            text-anchor="middle" fill="white">ESA</text>
    </svg>
    """
    
    # Ícone 512x512
    icon_512_svg = """
    <svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#3498DB;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#2980B9;stop-opacity:1" />
        </linearGradient>
      </defs>
      <circle cx="256" cy="256" r="256" fill="url(#grad2)"/>
      <text x="256" y="290" font-family="Arial, sans-serif" font-size="128" font-weight="bold" 
            text-anchor="middle" fill="white">ESA</text>
    </svg>
    """
    
    os.makedirs("static", exist_ok=True)
    
    with open("static/icon-192.svg", "w", encoding="utf-8") as f:
        f.write(icon_192_svg)
    
    with open("static/icon-512.svg", "w", encoding="utf-8") as f:
        f.write(icon_512_svg)
    
    return True

# Instruções de instalação mobile
MOBILE_INSTRUCTIONS = """
# 📱 Como Instalar o Ponto ExSA no Celular

## 📋 Opções de Instalação

### 1. 🌐 Acesso via Navegador (Recomendado)
- Abra o navegador do seu celular (Chrome, Safari, Firefox)
- Acesse o link do aplicativo
- O aplicativo é totalmente responsivo e funciona perfeitamente no mobile

### 2. 📱 Instalar como PWA (Progressive Web App)
**No Android (Chrome):**
1. Abra o aplicativo no Chrome
2. Toque no menu (3 pontos) → "Adicionar à tela inicial"
3. Confirme a instalação
4. O app aparecerá como ícone na tela inicial

**No iPhone (Safari):**
1. Abra o aplicativo no Safari
2. Toque no botão de compartilhar (quadrado com seta)
3. Selecione "Adicionar à Tela de Início"
4. Confirme a instalação

### 3. 🔗 Criar Atalho Manual
1. Abra o navegador e acesse o aplicativo
2. Adicione aos favoritos/marcadores
3. Crie um atalho na tela inicial (varia por dispositivo)

## ✨ Vantagens da Versão Mobile

### 📱 Interface Otimizada
- Design responsivo que se adapta ao tamanho da tela
- Botões e campos otimizados para toque
- Navegação intuitiva em dispositivos móveis

### 🔔 Notificações (PWA)
- Notificações push para lembrar de bater ponto
- Alertas de fim de expediente
- Avisos de horas extras

### 📍 Localização GPS
- Captura automática da localização ao registrar ponto
- Funciona mesmo offline (dados salvos localmente)

### ⚡ Performance
- Carregamento rápido
- Funcionalidade offline básica
- Cache inteligente para melhor experiência

## 🔧 Requisitos Técnicos

### 📱 Dispositivos Suportados
- **Android:** Versão 5.0+ com Chrome 45+
- **iOS:** Versão 11.3+ com Safari
- **Outros:** Qualquer navegador moderno

### 🌐 Conectividade
- Conexão com internet para sincronização
- Funcionalidade básica offline (PWA)
- Dados salvos localmente quando offline

### 💾 Armazenamento
- Aproximadamente 5MB de espaço
- Cache automático para melhor performance

## 🆘 Suporte e Troubleshooting

### ❓ Problemas Comuns
1. **App não carrega:** Verifique conexão com internet
2. **Notificações não funcionam:** Ative permissões no navegador
3. **GPS não funciona:** Ative localização nas configurações
4. **Tela pequena:** Use modo paisagem ou zoom

### 📞 Contato para Suporte
- **Desenvolvido por:** Pâmela SAR
- **Empresa:** Expressão Socioambiental
- **Versão:** 2.0 (Mobile Ready)

## 🔄 Atualizações
- Atualizações automáticas via web
- Não precisa baixar nova versão
- Sempre a versão mais recente disponível
"""

def save_mobile_instructions():
    """
    Salva as instruções de instalação mobile
    """
    with open("INSTALACAO_MOBILE.md", "w", encoding="utf-8") as f:
        f.write(MOBILE_INSTRUCTIONS)
    
    return "INSTALACAO_MOBILE.md"

if __name__ == "__main__":
    setup_pwa()
    create_mobile_icons()
    save_mobile_instructions()
    print("✅ Configuração PWA criada com sucesso!")

