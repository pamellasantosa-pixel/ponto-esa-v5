"""
Push Notifications System para Ponto ExSA
==========================================
Sistema completo de notificações push via Web Push API.
Compatível com Neon PostgreSQL.

Funcionalidades:
- Enviar notificações push para usuários
- Gerenciar subscriptions (registrar, remover)
- Sistema de lembretes automáticos
- Log de notificações enviadas
- Tratamento de erros e retry

Dependências:
- pywebpush: pip install pywebpush
- cryptography: pip install cryptography

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import os
import json
import logging
from datetime import datetime, timedelta, time
from typing import Optional, Dict, List, Any, Tuple
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logger
logger = logging.getLogger(__name__)

# Tentar importar pywebpush
try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    logger.warning("pywebpush não instalado. Notificações push desabilitadas.")
    logger.warning("Para habilitar, execute: pip install pywebpush")

# Importar conexão com banco
try:
    from database import get_connection, SQL_PLACEHOLDER
except ImportError:
    # Fallback se importar de outro local
    from ponto_esa_v5.database import get_connection, SQL_PLACEHOLDER


# ============================================
# CONFIGURAÇÃO VAPID
# ============================================

# Chaves VAPID - DEVEM ser configuradas via variáveis de ambiente
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_CLAIM_EMAIL = os.getenv('VAPID_CLAIM_EMAIL', 'mailto:contato@expressaosa.com.br')

# Validar configuração
def is_push_configured() -> bool:
    """Verifica se as notificações push estão configuradas corretamente."""
    return bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY and WEBPUSH_AVAILABLE)


def get_vapid_public_key() -> str:
    """Retorna a chave pública VAPID para uso no frontend."""
    return VAPID_PUBLIC_KEY


# ============================================
# GERENCIAMENTO DE SUBSCRIPTIONS
# ============================================

def salvar_subscription(
    usuario: str,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: Optional[str] = None,
    device_info: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Salva ou atualiza uma subscription de push no banco de dados.
    
    Args:
        usuario: Username do usuário
        endpoint: URL do endpoint de push
        p256dh: Chave pública do cliente
        auth: Chave de autenticação
        user_agent: User-Agent do navegador (opcional)
        device_info: Informações do dispositivo (opcional)
    
    Returns:
        Tuple[bool, str]: (sucesso, mensagem)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar se já existe subscription para este endpoint
        cursor.execute(
            f"SELECT id FROM push_subscriptions WHERE endpoint = {SQL_PLACEHOLDER}",
            (endpoint,)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Atualizar subscription existente
            cursor.execute(f"""
                UPDATE push_subscriptions
                SET usuario = {SQL_PLACEHOLDER},
                    p256dh = {SQL_PLACEHOLDER},
                    auth = {SQL_PLACEHOLDER},
                    user_agent = {SQL_PLACEHOLDER},
                    device_info = {SQL_PLACEHOLDER},
                    ativo = 1,
                    falhas_consecutivas = 0
                WHERE endpoint = {SQL_PLACEHOLDER}
            """, (usuario, p256dh, auth, user_agent, device_info, endpoint))
            conn.commit()
            logger.info(f"Subscription atualizada para usuário: {usuario}")
            return True, "Subscription atualizada com sucesso"
        else:
            # Criar nova subscription
            cursor.execute(f"""
                INSERT INTO push_subscriptions 
                (usuario, endpoint, p256dh, auth, user_agent, device_info)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 
                        {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
            """, (usuario, endpoint, p256dh, auth, user_agent, device_info))
            conn.commit()
            logger.info(f"Nova subscription criada para usuário: {usuario}")
            return True, "Subscription registrada com sucesso"
            
    except Exception as e:
        logger.error(f"Erro ao salvar subscription: {e}")
        return False, f"Erro ao salvar subscription: {str(e)}"
    finally:
        if conn:
            conn.close()


def remover_subscription(endpoint: str) -> Tuple[bool, str]:
    """
    Remove uma subscription do banco de dados.
    
    Args:
        endpoint: URL do endpoint de push
    
    Returns:
        Tuple[bool, str]: (sucesso, mensagem)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"DELETE FROM push_subscriptions WHERE endpoint = {SQL_PLACEHOLDER}",
            (endpoint,)
        )
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Subscription removida: {endpoint[:50]}...")
            return True, "Subscription removida com sucesso"
        else:
            return False, "Subscription não encontrada"
            
    except Exception as e:
        logger.error(f"Erro ao remover subscription: {e}")
        return False, f"Erro ao remover: {str(e)}"
    finally:
        if conn:
            conn.close()


def obter_subscriptions_usuario(usuario: str) -> List[Dict]:
    """
    Obtém todas as subscriptions ativas de um usuário.
    
    Args:
        usuario: Username do usuário
    
    Returns:
        Lista de subscriptions
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT id, endpoint, p256dh, auth, user_agent, device_info, data_criacao
            FROM push_subscriptions
            WHERE usuario = {SQL_PLACEHOLDER} AND ativo = 1
            ORDER BY data_criacao DESC
        """, (usuario,))
        
        rows = cursor.fetchall()
        subscriptions = []
        
        for row in rows:
            subscriptions.append({
                'id': row[0],
                'endpoint': row[1],
                'keys': {
                    'p256dh': row[2],
                    'auth': row[3]
                },
                'user_agent': row[4],
                'device_info': row[5],
                'data_criacao': row[6]
            })
        
        return subscriptions
        
    except Exception as e:
        logger.error(f"Erro ao obter subscriptions: {e}")
        return []
    finally:
        if conn:
            conn.close()


def marcar_subscription_invalida(endpoint: str) -> None:
    """
    Marca uma subscription como inválida após falhas consecutivas.
    Após 3 falhas, a subscription é desativada.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Incrementar contador de falhas
        cursor.execute(f"""
            UPDATE push_subscriptions
            SET falhas_consecutivas = falhas_consecutivas + 1,
                ativo = CASE WHEN falhas_consecutivas >= 2 THEN 0 ELSE ativo END
            WHERE endpoint = {SQL_PLACEHOLDER}
        """, (endpoint,))
        conn.commit()
        
    except Exception as e:
        logger.error(f"Erro ao marcar subscription inválida: {e}")
    finally:
        if conn:
            conn.close()


def resetar_falhas_subscription(endpoint: str) -> None:
    """Reseta o contador de falhas após envio bem-sucedido."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            UPDATE push_subscriptions
            SET falhas_consecutivas = 0,
                ultima_notificacao = NOW()
            WHERE endpoint = {SQL_PLACEHOLDER}
        """, (endpoint,))
        conn.commit()
        
    except Exception as e:
        logger.error(f"Erro ao resetar falhas: {e}")
    finally:
        if conn:
            conn.close()


# ============================================
# ENVIO DE NOTIFICAÇÕES
# ============================================

def enviar_push_para_subscription(
    subscription: Dict,
    titulo: str,
    mensagem: str,
    url: str = '/',
    tag: Optional[str] = None,
    dados_extras: Optional[Dict] = None,
    require_interaction: bool = False
) -> Tuple[bool, str]:
    """
    Envia uma notificação push para uma subscription específica.
    
    Args:
        subscription: Dict com endpoint e keys
        titulo: Título da notificação
        mensagem: Corpo da mensagem
        url: URL para abrir ao clicar
        tag: Tag para agrupar notificações
        dados_extras: Dados adicionais em JSON
        require_interaction: Se True, exige interação do usuário
    
    Returns:
        Tuple[bool, str]: (sucesso, mensagem)
    """
    if not WEBPUSH_AVAILABLE:
        return False, "pywebpush não instalado"
    
    if not is_push_configured():
        return False, "VAPID keys não configuradas"
    
    try:
        # Montar payload da notificação
        payload = {
            'title': titulo,
            'body': mensagem,
            'icon': '/static/icon-192.png',
            'badge': '/static/icon-192.png',
            'url': url,
            'tag': tag or 'ponto-exsa',
            'requireInteraction': require_interaction,
            'data': dados_extras or {}
        }
        
        # Construir subscription info
        subscription_info = {
            'endpoint': subscription['endpoint'],
            'keys': subscription.get('keys', {
                'p256dh': subscription.get('p256dh'),
                'auth': subscription.get('auth')
            })
        }
        
        # Enviar via webpush
        response = webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={'sub': VAPID_CLAIM_EMAIL}
        )
        
        # Resetar contador de falhas
        resetar_falhas_subscription(subscription['endpoint'])
        
        logger.info(f"Push enviado com sucesso: {titulo}")
        return True, "Notificação enviada com sucesso"
        
    except WebPushException as e:
        error_msg = str(e)
        logger.error(f"Erro WebPush: {error_msg}")
        
        # Verificar se subscription expirou ou é inválida
        if e.response and e.response.status_code in [404, 410]:
            marcar_subscription_invalida(subscription['endpoint'])
            return False, "Subscription expirada ou inválida"
        
        marcar_subscription_invalida(subscription['endpoint'])
        return False, f"Erro ao enviar: {error_msg}"
        
    except Exception as e:
        logger.error(f"Erro ao enviar push: {e}")
        return False, f"Erro: {str(e)}"


def enviar_notificacao_para_usuario(
    usuario: str,
    titulo: str,
    mensagem: str,
    tipo: str = 'info',
    url: str = '/',
    dados_extras: Optional[Dict] = None
) -> Tuple[int, int]:
    """
    Envia notificação push para todos os dispositivos de um usuário.
    
    Args:
        usuario: Username do usuário
        titulo: Título da notificação
        mensagem: Corpo da mensagem
        tipo: Tipo da notificação (info, warning, error, success)
        url: URL para abrir ao clicar
        dados_extras: Dados adicionais
    
    Returns:
        Tuple[int, int]: (enviados_com_sucesso, total_tentativas)
    """
    subscriptions = obter_subscriptions_usuario(usuario)
    
    if not subscriptions:
        logger.warning(f"Nenhuma subscription encontrada para: {usuario}")
        return 0, 0
    
    enviados = 0
    total = len(subscriptions)
    
    for sub in subscriptions:
        sucesso, msg = enviar_push_para_subscription(
            subscription=sub,
            titulo=titulo,
            mensagem=mensagem,
            url=url,
            dados_extras=dados_extras
        )
        if sucesso:
            enviados += 1
    
    # Registrar no log
    registrar_notificacao_log(usuario, titulo, mensagem, tipo, dados_extras, 
                              'enviado' if enviados > 0 else 'falhou')
    
    return enviados, total


def enviar_notificacao_para_todos(
    titulo: str,
    mensagem: str,
    tipo: str = 'info',
    url: str = '/',
    filtro_usuarios: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Envia notificação push para todos os usuários (ou lista filtrada).
    
    Args:
        titulo: Título da notificação
        mensagem: Corpo da mensagem
        tipo: Tipo da notificação
        url: URL para abrir
        filtro_usuarios: Lista de usuários específicos (opcional)
    
    Returns:
        Dict com estatísticas de envio
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if filtro_usuarios:
            placeholders = ', '.join([SQL_PLACEHOLDER] * len(filtro_usuarios))
            cursor.execute(f"""
                SELECT DISTINCT usuario FROM push_subscriptions
                WHERE ativo = 1 AND usuario IN ({placeholders})
            """, tuple(filtro_usuarios))
        else:
            cursor.execute("SELECT DISTINCT usuario FROM push_subscriptions WHERE ativo = 1")
        
        usuarios = [row[0] for row in cursor.fetchall()]
        
        resultados = {
            'total_usuarios': len(usuarios),
            'enviados': 0,
            'falhas': 0,
            'usuarios_notificados': []
        }
        
        for usuario in usuarios:
            enviados, total = enviar_notificacao_para_usuario(
                usuario=usuario,
                titulo=titulo,
                mensagem=mensagem,
                tipo=tipo,
                url=url
            )
            
            if enviados > 0:
                resultados['enviados'] += 1
                resultados['usuarios_notificados'].append(usuario)
            else:
                resultados['falhas'] += 1
        
        return resultados
        
    except Exception as e:
        logger.error(f"Erro ao enviar para todos: {e}")
        return {'error': str(e)}
    finally:
        if conn:
            conn.close()


# ============================================
# LOG DE NOTIFICAÇÕES
# ============================================

def registrar_notificacao_log(
    usuario: str,
    titulo: str,
    mensagem: str,
    tipo: str = 'info',
    dados_extras: Optional[Dict] = None,
    status: str = 'enviado',
    erro: Optional[str] = None
) -> None:
    """Registra uma notificação no log para auditoria."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        dados_json = json.dumps(dados_extras) if dados_extras else None
        
        cursor.execute(f"""
            INSERT INTO push_notifications_log 
            (usuario, titulo, mensagem, tipo, dados_extras, status, erro)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 
                    {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        """, (usuario, titulo, mensagem, tipo, dados_json, status, erro))
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Erro ao registrar log de notificação: {e}")
    finally:
        if conn:
            conn.close()


# ============================================
# NOTIFICAÇÕES PRÉ-DEFINIDAS
# ============================================

def notificar_esqueceu_entrada(usuario: str) -> Tuple[int, int]:
    """Notifica usuário que esqueceu de bater ponto de entrada."""
    return enviar_notificacao_para_usuario(
        usuario=usuario,
        titulo="⏰ Lembrete de Ponto",
        mensagem="Você ainda não registrou sua entrada hoje. Não esqueça de bater o ponto!",
        tipo="warning",
        url="/",
        dados_extras={'tipo': 'lembrete_entrada'}
    )


def notificar_esqueceu_saida(usuario: str) -> Tuple[int, int]:
    """Notifica usuário que esqueceu de bater ponto de saída."""
    return enviar_notificacao_para_usuario(
        usuario=usuario,
        titulo="🏠 Hora de Ir!",
        mensagem="Seu horário de saída passou. Não esqueça de registrar sua saída!",
        tipo="warning",
        url="/",
        dados_extras={'tipo': 'lembrete_saida'}
    )


def notificar_hora_extra_aprovada(usuario: str, horas: float) -> Tuple[int, int]:
    """Notifica usuário que hora extra foi aprovada."""
    return enviar_notificacao_para_usuario(
        usuario=usuario,
        titulo="✅ Hora Extra Aprovada",
        mensagem=f"Sua solicitação de {horas:.1f}h extra foi aprovada!",
        tipo="success",
        url="/",
        dados_extras={'tipo': 'hora_extra_aprovada', 'horas': horas}
    )


def notificar_hora_extra_rejeitada(usuario: str, motivo: str) -> Tuple[int, int]:
    """Notifica usuário que hora extra foi rejeitada."""
    return enviar_notificacao_para_usuario(
        usuario=usuario,
        titulo="❌ Hora Extra Não Aprovada",
        mensagem=f"Sua solicitação não foi aprovada. Motivo: {motivo}",
        tipo="error",
        url="/",
        dados_extras={'tipo': 'hora_extra_rejeitada', 'motivo': motivo}
    )


def notificar_nova_solicitacao_he(gestor: str, funcionario: str) -> Tuple[int, int]:
    """Notifica gestor sobre nova solicitação de hora extra."""
    return enviar_notificacao_para_usuario(
        usuario=gestor,
        titulo="📋 Nova Solicitação",
        mensagem=f"{funcionario} solicitou autorização para hora extra. Verifique!",
        tipo="info",
        url="/",
        dados_extras={'tipo': 'nova_solicitacao_he', 'funcionario': funcionario}
    )


def notificar_fim_hora_extra(usuario: str, minutos: int) -> Tuple[int, int]:
    """Notifica usuário que está fazendo hora extra há muito tempo."""
    horas = minutos // 60
    mins = minutos % 60
    return enviar_notificacao_para_usuario(
        usuario=usuario,
        titulo="⚠️ Hora Extra em Andamento",
        mensagem=f"Você está em hora extra há {horas}h{mins}min. Lembre-se dos limites!",
        tipo="warning",
        url="/",
        dados_extras={'tipo': 'alerta_hora_extra', 'minutos': minutos}
    )


def notificar_teste(usuario: str) -> Tuple[int, int]:
    """Envia notificação de teste para verificar se está funcionando."""
    return enviar_notificacao_para_usuario(
        usuario=usuario,
        titulo="🔔 Teste de Notificação",
        mensagem="Se você está vendo isso, as notificações push estão funcionando!",
        tipo="info",
        url="/",
        dados_extras={'tipo': 'teste', 'timestamp': datetime.now().isoformat()}
    )


# ============================================
# CLASSE PRINCIPAL DO SISTEMA
# ============================================

class PushNotificationSystem:
    """
    Classe principal para gerenciar notificações push.
    Fornece interface unificada para todas as operações.
    """
    
    def __init__(self):
        self.configured = is_push_configured()
        if not self.configured:
            logger.warning("Sistema de Push não configurado. Verifique as chaves VAPID.")
    
    def is_ready(self) -> bool:
        """Verifica se o sistema está pronto para uso."""
        return self.configured
    
    def get_public_key(self) -> str:
        """Retorna a chave pública VAPID."""
        return get_vapid_public_key()
    
    def subscribe(self, usuario: str, subscription_data: Dict) -> Tuple[bool, str]:
        """Registra uma nova subscription."""
        return salvar_subscription(
            usuario=usuario,
            endpoint=subscription_data.get('endpoint', ''),
            p256dh=subscription_data.get('keys', {}).get('p256dh', ''),
            auth=subscription_data.get('keys', {}).get('auth', ''),
            user_agent=subscription_data.get('userAgent'),
            device_info=subscription_data.get('deviceInfo')
        )
    
    def unsubscribe(self, endpoint: str) -> Tuple[bool, str]:
        """Remove uma subscription."""
        return remover_subscription(endpoint)
    
    def send(self, usuario: str, titulo: str, mensagem: str, **kwargs) -> Tuple[int, int]:
        """Envia notificação para um usuário."""
        return enviar_notificacao_para_usuario(
            usuario=usuario,
            titulo=titulo,
            mensagem=mensagem,
            **kwargs
        )
    
    def broadcast(self, titulo: str, mensagem: str, **kwargs) -> Dict[str, Any]:
        """Envia notificação para todos os usuários."""
        return enviar_notificacao_para_todos(
            titulo=titulo,
            mensagem=mensagem,
            **kwargs
        )
    
    def test(self, usuario: str) -> Tuple[int, int]:
        """Envia notificação de teste."""
        return notificar_teste(usuario)
    
    # Métodos de conveniência para notificações comuns
    def lembrete_entrada(self, usuario: str) -> Tuple[int, int]:
        return notificar_esqueceu_entrada(usuario)
    
    def lembrete_saida(self, usuario: str) -> Tuple[int, int]:
        return notificar_esqueceu_saida(usuario)
    
    def hora_extra_aprovada(self, usuario: str, horas: float) -> Tuple[int, int]:
        return notificar_hora_extra_aprovada(usuario, horas)
    
    def hora_extra_rejeitada(self, usuario: str, motivo: str) -> Tuple[int, int]:
        return notificar_hora_extra_rejeitada(usuario, motivo)
    
    def nova_solicitacao(self, gestor: str, funcionario: str) -> Tuple[int, int]:
        return notificar_nova_solicitacao_he(gestor, funcionario)


# Instância global para uso em todo o app
push_system = PushNotificationSystem()


# ============================================
# FUNÇÕES DE TESTE E DEBUG
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("Push Notification System - Ponto ExSA")
    print("=" * 60)
    print()
    
    print(f"pywebpush instalado: {WEBPUSH_AVAILABLE}")
    print(f"VAPID configurado: {is_push_configured()}")
    print(f"VAPID Public Key: {VAPID_PUBLIC_KEY[:30]}..." if VAPID_PUBLIC_KEY else "Não configurada")
    print()
    
    if not is_push_configured():
        print("⚠️ Para configurar, execute: python generate_vapid_keys.py")
        print("   E adicione as chaves ao arquivo .env")
