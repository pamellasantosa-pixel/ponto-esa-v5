"""
Sistema de Push Notifications usando ntfy.sh (gratuito)
Envia lembretes de ponto nos horários configurados
"""
import os
import requests
import threading
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL base do ntfy.sh (gratuito e público)
NTFY_URL = "https://ntfy.sh"

# Horários de lembrete (hora, minuto, mensagem, emoji)
HORARIOS_LEMBRETE = [
    (7, 50, "Bom dia! Não esqueça de registrar a entrada.", "🌅"),
    (12, 0, "Hora do almoço! Registre a saída.", "🍽️"),
    (13, 0, "Voltando do almoço? Registre a entrada.", "☕"),
    (16, 50, "Quase na hora! Registre a saída.", "🏠"),
]

def get_topic_for_user(usuario: str) -> str:
    """Gera um tópico único para cada usuário"""
    # Usar prefixo único para evitar colisões
    import hashlib
    hash_user = hashlib.md5(f"ponto_exsa_{usuario}".encode()).hexdigest()[:8]
    return f"ponto-exsa-{hash_user}"

def enviar_notificacao(usuario: str, titulo: str, mensagem: str, emoji: str = "📋"):
    """Envia uma notificação push para o usuário via ntfy.sh"""
    topic = get_topic_for_user(usuario)
    url = f"{NTFY_URL}/{topic}"
    
    try:
        response = requests.post(
            url,
            data=mensagem.encode('utf-8'),
            headers={
                "Title": f"{emoji} {titulo}",
                "Priority": "high",
                "Tags": "clock,calendar",
                "Click": os.getenv("APP_URL", "https://ponto-exsa.onrender.com"),
            },
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"[Push] Notificação enviada para {usuario}: {mensagem}")
            return True
        else:
            logger.error(f"[Push] Erro ao enviar para {usuario}: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"[Push] Exceção ao enviar para {usuario}: {e}")
        return False

def enviar_lembrete_ponto(hora: int, minuto: int, mensagem: str, emoji: str):
    """Envia lembrete para todos os usuários inscritos"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar usuários com push ativado
        cursor.execute("""
            SELECT DISTINCT usuario FROM push_subscriptions 
            WHERE ativo = TRUE
        """)
        
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Enviando lembrete das {hora:02d}:{minuto:02d} para {len(usuarios)} usuários")
        
        for (usuario,) in usuarios:
            enviar_notificacao(
                usuario=usuario,
                titulo="Lembrete de Ponto",
                mensagem=mensagem,
                emoji=emoji
            )
            
    except Exception as e:
        logger.error(f"[Push] Erro ao enviar lembretes: {e}")

def criar_tabela_subscriptions():
    """Cria tabela de subscriptions se não existir"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(100) NOT NULL,
                topic VARCHAR(100) NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(usuario)
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("[Push] Tabela push_subscriptions criada/verificada")
        
    except Exception as e:
        logger.error(f"[Push] Erro ao criar tabela: {e}")

def registrar_subscription(usuario: str) -> str:
    """Registra um usuário para receber push notifications"""
    from database_postgresql import get_connection
    
    # Garantir que tabela existe
    criar_tabela_subscriptions()
    
    topic = get_topic_for_user(usuario)
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO push_subscriptions (usuario, topic, ativo)
            VALUES (%s, %s, TRUE)
            ON CONFLICT (usuario) 
            DO UPDATE SET ativo = TRUE, topic = %s
        """, (usuario, topic, topic))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Usuário {usuario} registrado com topic: {topic}")
        return topic
        
    except Exception as e:
        logger.error(f"[Push] Erro ao registrar subscription: {e}")
        return topic

def desativar_subscription(usuario: str):
    """Desativa push notifications para um usuário"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE push_subscriptions SET ativo = FALSE WHERE usuario = %s
        """, (usuario,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Push desativado para {usuario}")
        
    except Exception as e:
        logger.error(f"[Push] Erro ao desativar subscription: {e}")

def verificar_subscription(usuario: str) -> tuple:
    """Verifica se usuário tem push ativo e retorna o topic"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT topic, ativo FROM push_subscriptions WHERE usuario = %s
        """, (usuario,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result[0], result[1]
        return None, False
        
    except Exception as e:
        logger.error(f"[Push] Erro ao verificar subscription: {e}")
        return None, False

# Scheduler global
_scheduler = None

def iniciar_scheduler():
    """Inicia o scheduler de lembretes"""
    global _scheduler
    
    if _scheduler is not None:
        logger.info("[Push] Scheduler já está rodando")
        return
    
    # Criar tabela se não existir
    criar_tabela_subscriptions()
    
    _scheduler = BackgroundScheduler(timezone='America/Sao_Paulo')
    
    # Adicionar jobs para cada horário
    for hora, minuto, mensagem, emoji in HORARIOS_LEMBRETE:
        _scheduler.add_job(
            func=enviar_lembrete_ponto,
            trigger=CronTrigger(hour=hora, minute=minuto, timezone='America/Sao_Paulo'),
            args=[hora, minuto, mensagem, emoji],
            id=f"lembrete_{hora:02d}{minuto:02d}",
            replace_existing=True
        )
        logger.info(f"[Push] Job agendado: {hora:02d}:{minuto:02d} - {mensagem}")
    
    _scheduler.start()
    logger.info("[Push] Scheduler de lembretes iniciado!")

def parar_scheduler():
    """Para o scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("[Push] Scheduler parado")

# Iniciar automaticamente quando o módulo for importado
def init_push_system():
    """Inicializa o sistema de push em uma thread separada"""
    try:
        iniciar_scheduler()
    except Exception as e:
        logger.error(f"[Push] Erro ao iniciar sistema: {e}")
