"""
API Server para Push Notifications - Ponto ExSA
================================================
Servidor Flask leve para gerenciar endpoints de push notifications.
Roda separadamente ou pode ser integrado ao Streamlit.

Endpoints:
- POST /api/push/subscribe - Registrar subscription
- POST /api/push/unsubscribe - Remover subscription
- GET /api/push/vapid-key - Obter chave pública VAPID
- POST /api/push/test - Enviar notificação de teste

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from functools import wraps

# Tentar importar Flask
try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

from push_notifications import (
    push_system,
    salvar_subscription,
    remover_subscription,
    get_vapid_public_key,
    is_push_configured,
    notificar_teste
)

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar app Flask (se disponível)
if FLASK_AVAILABLE:
    app = Flask(__name__)
    app.config['JSON_AS_ASCII'] = False  # Suporte a UTF-8
else:
    app = None
    logger.warning("Flask não instalado. API de push não disponível standalone.")


def json_response(data: Dict, status: int = 200):
    """Helper para criar respostas JSON."""
    response = jsonify(data)
    response.status_code = status
    return response


def require_json(f):
    """Decorator para validar Content-Type JSON."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.content_type != 'application/json':
            return json_response({
                'success': False,
                'error': 'Content-Type deve ser application/json'
            }, 400)
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# ENDPOINTS DA API
# ============================================

if FLASK_AVAILABLE:
    
    @app.route('/api/push/vapid-key', methods=['GET'])
    def get_vapid_key():
        """
        Retorna a chave pública VAPID para o frontend.
        
        Response:
            {
                "success": true,
                "vapidKey": "BLx...",
                "configured": true
            }
        """
        try:
            return json_response({
                'success': True,
                'vapidKey': get_vapid_public_key(),
                'configured': is_push_configured()
            })
        except Exception as e:
            logger.error(f"Erro ao obter VAPID key: {e}")
            return json_response({
                'success': False,
                'error': str(e)
            }, 500)
    
    
    @app.route('/api/push/subscribe', methods=['POST'])
    @require_json
    def subscribe():
        """
        Registra uma nova subscription de push.
        
        Request Body:
            {
                "usuario": "username",
                "subscription": {
                    "endpoint": "https://...",
                    "keys": {
                        "p256dh": "...",
                        "auth": "..."
                    }
                },
                "userAgent": "Mozilla/5.0...",
                "deviceInfo": "Chrome/Windows"
            }
        
        Response:
            {
                "success": true,
                "message": "Subscription registrada com sucesso"
            }
        """
        try:
            data = request.get_json()
            
            # Validar dados obrigatórios
            if not data.get('usuario'):
                return json_response({
                    'success': False,
                    'error': 'Campo "usuario" é obrigatório'
                }, 400)
            
            subscription = data.get('subscription', {})
            if not subscription.get('endpoint'):
                return json_response({
                    'success': False,
                    'error': 'Subscription inválida: endpoint ausente'
                }, 400)
            
            keys = subscription.get('keys', {})
            if not keys.get('p256dh') or not keys.get('auth'):
                return json_response({
                    'success': False,
                    'error': 'Subscription inválida: keys ausentes'
                }, 400)
            
            # Salvar subscription
            success, message = salvar_subscription(
                usuario=data['usuario'],
                endpoint=subscription['endpoint'],
                p256dh=keys['p256dh'],
                auth=keys['auth'],
                user_agent=data.get('userAgent'),
                device_info=data.get('deviceInfo')
            )
            
            if success:
                return json_response({
                    'success': True,
                    'message': message
                })
            else:
                return json_response({
                    'success': False,
                    'error': message
                }, 500)
                
        except Exception as e:
            logger.error(f"Erro ao registrar subscription: {e}")
            return json_response({
                'success': False,
                'error': str(e)
            }, 500)
    
    
    @app.route('/api/push/unsubscribe', methods=['POST'])
    @require_json
    def unsubscribe():
        """
        Remove uma subscription de push.
        
        Request Body:
            {
                "endpoint": "https://..."
            }
        
        Response:
            {
                "success": true,
                "message": "Subscription removida com sucesso"
            }
        """
        try:
            data = request.get_json()
            
            if not data.get('endpoint'):
                return json_response({
                    'success': False,
                    'error': 'Campo "endpoint" é obrigatório'
                }, 400)
            
            success, message = remover_subscription(data['endpoint'])
            
            return json_response({
                'success': success,
                'message': message
            }, 200 if success else 404)
            
        except Exception as e:
            logger.error(f"Erro ao remover subscription: {e}")
            return json_response({
                'success': False,
                'error': str(e)
            }, 500)
    
    
    @app.route('/api/push/test', methods=['POST'])
    @require_json
    def test_notification():
        """
        Envia uma notificação de teste para o usuário.
        
        Request Body:
            {
                "usuario": "username"
            }
        
        Response:
            {
                "success": true,
                "enviados": 1,
                "total": 1
            }
        """
        try:
            data = request.get_json()
            
            if not data.get('usuario'):
                return json_response({
                    'success': False,
                    'error': 'Campo "usuario" é obrigatório'
                }, 400)
            
            enviados, total = notificar_teste(data['usuario'])
            
            return json_response({
                'success': enviados > 0,
                'enviados': enviados,
                'total': total,
                'message': f'{enviados} de {total} notificações enviadas'
            })
            
        except Exception as e:
            logger.error(f"Erro ao enviar teste: {e}")
            return json_response({
                'success': False,
                'error': str(e)
            }, 500)
    
    
    @app.route('/api/push/status', methods=['GET'])
    def push_status():
        """
        Retorna o status do sistema de push.
        
        Response:
            {
                "configured": true,
                "ready": true,
                "vapidKeySet": true
            }
        """
        return json_response({
            'configured': is_push_configured(),
            'ready': push_system.is_ready(),
            'vapidKeySet': bool(get_vapid_public_key())
        })
    
    
    # CORS headers para requisições cross-origin
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return response


# ============================================
# FUNÇÕES PARA INTEGRAÇÃO COM STREAMLIT
# ============================================

def handle_push_request(action: str, data: Dict) -> Dict[str, Any]:
    """
    Handler para processar requisições de push via Streamlit.
    Usa esta função quando não tiver Flask separado.
    
    Args:
        action: 'subscribe', 'unsubscribe', 'test', 'vapid-key', 'status'
        data: Dados da requisição
    
    Returns:
        Dict com resultado da operação
    """
    try:
        if action == 'vapid-key':
            return {
                'success': True,
                'vapidKey': get_vapid_public_key(),
                'configured': is_push_configured()
            }
        
        elif action == 'subscribe':
            subscription = data.get('subscription', {})
            keys = subscription.get('keys', {})
            
            success, message = salvar_subscription(
                usuario=data.get('usuario', ''),
                endpoint=subscription.get('endpoint', ''),
                p256dh=keys.get('p256dh', ''),
                auth=keys.get('auth', ''),
                user_agent=data.get('userAgent'),
                device_info=data.get('deviceInfo')
            )
            
            return {'success': success, 'message': message}
        
        elif action == 'unsubscribe':
            success, message = remover_subscription(data.get('endpoint', ''))
            return {'success': success, 'message': message}
        
        elif action == 'test':
            enviados, total = notificar_teste(data.get('usuario', ''))
            return {
                'success': enviados > 0,
                'enviados': enviados,
                'total': total
            }
        
        elif action == 'status':
            return {
                'configured': is_push_configured(),
                'ready': push_system.is_ready(),
                'vapidKeySet': bool(get_vapid_public_key())
            }
        
        else:
            return {'success': False, 'error': f'Ação desconhecida: {action}'}
            
    except Exception as e:
        logger.error(f"Erro ao processar requisição push: {e}")
        return {'success': False, 'error': str(e)}


# ============================================
# MAIN - Servidor standalone
# ============================================

if __name__ == '__main__':
    if FLASK_AVAILABLE:
        print("=" * 60)
        print("Push Notification API Server - Ponto ExSA")
        print("=" * 60)
        print()
        print(f"Push configurado: {is_push_configured()}")
        print()
        print("Endpoints disponíveis:")
        print("  GET  /api/push/vapid-key  - Obter chave VAPID")
        print("  POST /api/push/subscribe  - Registrar subscription")
        print("  POST /api/push/unsubscribe - Remover subscription")
        print("  POST /api/push/test       - Enviar teste")
        print("  GET  /api/push/status     - Status do sistema")
        print()
        print("Iniciando servidor na porta 5000...")
        print("=" * 60)
        
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("❌ Flask não instalado. Execute: pip install flask")
