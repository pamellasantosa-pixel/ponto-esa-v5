"""
Sistema de Push Notifications usando ntfy.sh (gratuito)
Envia lembretes de ponto, avisos, aniversários e alertas
"""
import os
import requests
import threading
from datetime import datetime, time, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL base do ntfy.sh (gratuito e público)
NTFY_URL = "https://ntfy.sh"

# Horários de lembrete PADRÃO (hora, minuto, mensagem, emoji)
HORARIOS_LEMBRETE_PADRAO = [
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
    """Envia lembrete para todos os usuários inscritos (respeitando horários personalizados)"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar usuários com push ativado e seus horários personalizados
        cursor.execute("""
            SELECT DISTINCT p.usuario, p.horario_entrada, p.horario_almoco_saida,
                   p.horario_almoco_retorno, p.horario_saida
            FROM push_subscriptions p
            WHERE p.ativo = TRUE
        """)
        
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        
        hora_atual = f"{hora:02d}:{minuto:02d}"
        logger.info(f"[Push] Verificando lembrete das {hora_atual} para {len(usuarios)} usuários")
        
        for row in usuarios:
            usuario = row[0]
            horarios = {
                'entrada': row[1] or "07:50",
                'almoco_saida': row[2] or "12:00",
                'almoco_retorno': row[3] or "13:00",
                'saida': row[4] or "16:50"
            }
            
            # Verificar se este horário corresponde a um dos horários do usuário
            deve_enviar = False
            msg_personalizada = mensagem
            
            if hora_atual == horarios['entrada']:
                deve_enviar = True
                msg_personalizada = "Bom dia! Não esqueça de registrar a entrada."
            elif hora_atual == horarios['almoco_saida']:
                deve_enviar = True
                msg_personalizada = "Hora do almoço! Registre a saída."
            elif hora_atual == horarios['almoco_retorno']:
                deve_enviar = True
                msg_personalizada = "Voltando do almoço? Registre a entrada."
            elif hora_atual == horarios['saida']:
                deve_enviar = True
                msg_personalizada = "Quase na hora! Registre a saída."
            
            if deve_enviar:
                enviar_notificacao(
                    usuario=usuario,
                    titulo="Lembrete de Ponto",
                    mensagem=msg_personalizada,
                    emoji=emoji
                )
            
    except Exception as e:
        logger.error(f"[Push] Erro ao enviar lembretes: {e}")

def criar_tabela_subscriptions():
    """Cria tabela de subscriptions se não existir (com horários personalizados)"""
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
                horario_entrada VARCHAR(5) DEFAULT '07:50',
                horario_almoco_saida VARCHAR(5) DEFAULT '12:00',
                horario_almoco_retorno VARCHAR(5) DEFAULT '13:00',
                horario_saida VARCHAR(5) DEFAULT '16:50',
                UNIQUE(usuario)
            )
        """)
        
        # Adicionar colunas se não existirem (para bancos existentes)
        try:
            cursor.execute("ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS horario_entrada VARCHAR(5) DEFAULT '07:50'")
            cursor.execute("ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS horario_almoco_saida VARCHAR(5) DEFAULT '12:00'")
            cursor.execute("ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS horario_almoco_retorno VARCHAR(5) DEFAULT '13:00'")
            cursor.execute("ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS horario_saida VARCHAR(5) DEFAULT '16:50'")
        except:
            pass
        
        # Criar tabela de avisos do gestor
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS avisos_gestor (
                id SERIAL PRIMARY KEY,
                gestor VARCHAR(100) NOT NULL,
                titulo VARCHAR(200) NOT NULL,
                mensagem TEXT NOT NULL,
                destinatarios TEXT DEFAULT 'todos',
                data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                lido_por TEXT DEFAULT ''
            )
        """)
        
        # Criar tabela de mensagens diretas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensagens_diretas (
                id SERIAL PRIMARY KEY,
                remetente VARCHAR(100) NOT NULL,
                destinatario VARCHAR(100) NOT NULL,
                mensagem TEXT NOT NULL,
                lida BOOLEAN DEFAULT FALSE,
                data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Criar tabela de férias
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ferias_funcionarios (
                id SERIAL PRIMARY KEY,
                usuario VARCHAR(100) NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE NOT NULL,
                dias_aviso INTEGER DEFAULT 7,
                notificado BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("[Push] Tabelas de push criadas/verificadas")
        
    except Exception as e:
        logger.error(f"[Push] Erro ao criar tabelas: {e}")

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
    
    # Jobs de lembrete de ponto (a cada minuto verifica se alguém tem horário configurado)
    # Na prática, só envia para quem tem aquele horário configurado
    for hora, minuto, mensagem, emoji in HORARIOS_LEMBRETE_PADRAO:
        _scheduler.add_job(
            func=enviar_lembrete_ponto,
            trigger=CronTrigger(hour=hora, minute=minuto, timezone='America/Sao_Paulo'),
            args=[hora, minuto, mensagem, emoji],
            id=f"lembrete_{hora:02d}{minuto:02d}",
            replace_existing=True
        )
        logger.info(f"[Push] Job agendado: {hora:02d}:{minuto:02d} - {mensagem}")
    
    # Adicionar mais horários comuns para horários personalizados
    horarios_extras = [
        (8, 0), (8, 30), (9, 0),  # Manhã
        (11, 30), (12, 30),       # Almoço
        (13, 30), (14, 0),        # Retorno
        (17, 0), (17, 30), (18, 0)  # Saída
    ]
    
    for hora, minuto in horarios_extras:
        _scheduler.add_job(
            func=enviar_lembrete_ponto,
            trigger=CronTrigger(hour=hora, minute=minuto, timezone='America/Sao_Paulo'),
            args=[hora, minuto, "", "⏰"],
            id=f"lembrete_{hora:02d}{minuto:02d}",
            replace_existing=True
        )
    
    # Job diário: verificar aniversários (8h)
    _scheduler.add_job(
        func=verificar_aniversarios,
        trigger=CronTrigger(hour=8, minute=0, timezone='America/Sao_Paulo'),
        id="aniversarios_diario",
        replace_existing=True
    )
    logger.info("[Push] Job agendado: 08:00 - Verificar aniversários")
    
    # Job diário: verificar férias (8h)
    _scheduler.add_job(
        func=verificar_lembretes_ferias,
        trigger=CronTrigger(hour=8, minute=5, timezone='America/Sao_Paulo'),
        id="ferias_diario",
        replace_existing=True
    )
    logger.info("[Push] Job agendado: 08:05 - Verificar férias")
    
    # Job diário: resumo de pendências para gestores (8h)
    _scheduler.add_job(
        func=enviar_resumo_pendencias_gestor,
        trigger=CronTrigger(hour=8, minute=10, timezone='America/Sao_Paulo'),
        id="resumo_gestor_diario",
        replace_existing=True
    )
    logger.info("[Push] Job agendado: 08:10 - Resumo pendências gestor")
    
    # Job diário: verificar inconsistências (18h)
    _scheduler.add_job(
        func=verificar_inconsistencias_ponto,
        trigger=CronTrigger(hour=18, minute=0, timezone='America/Sao_Paulo'),
        id="inconsistencias_diario",
        replace_existing=True
    )
    logger.info("[Push] Job agendado: 18:00 - Verificar inconsistências")
    
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


# ============================================
# NOVAS FUNCIONALIDADES DE NOTIFICAÇÃO
# ============================================

def atualizar_horarios_usuario(usuario: str, entrada: str, almoco_saida: str, almoco_retorno: str, saida: str):
    """Atualiza os horários de lembrete personalizados de um usuário"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE push_subscriptions 
            SET horario_entrada = %s, 
                horario_almoco_saida = %s,
                horario_almoco_retorno = %s,
                horario_saida = %s
            WHERE usuario = %s
        """, (entrada, almoco_saida, almoco_retorno, saida, usuario))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Horários atualizados para {usuario}")
        return True
        
    except Exception as e:
        logger.error(f"[Push] Erro ao atualizar horários: {e}")
        return False


def obter_horarios_usuario(usuario: str) -> dict:
    """Obtém os horários de lembrete personalizados de um usuário"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT horario_entrada, horario_almoco_saida, horario_almoco_retorno, horario_saida
            FROM push_subscriptions WHERE usuario = %s
        """, (usuario,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return {
                'entrada': result[0] or "07:50",
                'almoco_saida': result[1] or "12:00",
                'almoco_retorno': result[2] or "13:00",
                'saida': result[3] or "16:50"
            }
        
        return {
            'entrada': "07:50",
            'almoco_saida': "12:00",
            'almoco_retorno': "13:00",
            'saida': "16:50"
        }
        
    except Exception as e:
        logger.error(f"[Push] Erro ao obter horários: {e}")
        return {
            'entrada': "07:50",
            'almoco_saida': "12:00",
            'almoco_retorno': "13:00",
            'saida': "16:50"
        }


def enviar_aviso_geral(gestor: str, titulo: str, mensagem: str, destinatarios: str = 'todos'):
    """Gestor envia aviso para todos os funcionários ou grupo específico"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Salvar aviso no banco
        cursor.execute("""
            INSERT INTO avisos_gestor (gestor, titulo, mensagem, destinatarios)
            VALUES (%s, %s, %s, %s)
        """, (gestor, titulo, mensagem, destinatarios))
        
        # Buscar usuários para enviar push
        if destinatarios == 'todos':
            cursor.execute("""
                SELECT DISTINCT usuario FROM push_subscriptions WHERE ativo = TRUE
            """)
        else:
            # destinatarios = lista separada por vírgula
            lista = [d.strip() for d in destinatarios.split(',')]
            placeholders = ','.join(['%s'] * len(lista))
            cursor.execute(f"""
                SELECT DISTINCT usuario FROM push_subscriptions 
                WHERE ativo = TRUE AND usuario IN ({placeholders})
            """, lista)
        
        usuarios = cursor.fetchall()
        conn.commit()
        cursor.close()
        conn.close()
        
        # Enviar push para cada usuário
        enviados = 0
        for (usuario,) in usuarios:
            if enviar_notificacao(usuario, f"📢 {titulo}", mensagem, "📢"):
                enviados += 1
        
        logger.info(f"[Push] Aviso enviado para {enviados} usuários")
        return enviados
        
    except Exception as e:
        logger.error(f"[Push] Erro ao enviar aviso: {e}")
        return 0


def enviar_mensagem_direta(remetente: str, destinatario: str, mensagem: str):
    """Envia mensagem direta de um usuário para outro"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar nome do remetente
        cursor.execute("SELECT nome_completo FROM usuarios WHERE usuario = %s", (remetente,))
        result = cursor.fetchone()
        nome_remetente = result[0] if result else remetente
        
        # Salvar mensagem
        cursor.execute("""
            INSERT INTO mensagens_diretas (remetente, destinatario, mensagem)
            VALUES (%s, %s, %s)
        """, (remetente, destinatario, mensagem))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Enviar push
        enviar_notificacao(
            destinatario, 
            f"💬 Mensagem de {nome_remetente}",
            mensagem,
            "💬"
        )
        
        logger.info(f"[Push] Mensagem enviada de {remetente} para {destinatario}")
        return True
        
    except Exception as e:
        logger.error(f"[Push] Erro ao enviar mensagem: {e}")
        return False


def obter_mensagens_usuario(usuario: str, apenas_nao_lidas: bool = False):
    """Obtém mensagens diretas de um usuário"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT m.id, m.remetente, m.mensagem, m.data_envio, m.lida, u.nome_completo
            FROM mensagens_diretas m
            LEFT JOIN usuarios u ON m.remetente = u.usuario
            WHERE m.destinatario = %s
        """
        
        if apenas_nao_lidas:
            query += " AND m.lida = FALSE"
        
        query += " ORDER BY m.data_envio DESC"
        
        cursor.execute(query, (usuario,))
        mensagens = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return mensagens
        
    except Exception as e:
        logger.error(f"[Push] Erro ao obter mensagens: {e}")
        return []


def marcar_mensagem_lida(mensagem_id: int):
    """Marca uma mensagem como lida"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE mensagens_diretas SET lida = TRUE WHERE id = %s", (mensagem_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"[Push] Erro ao marcar mensagem lida: {e}")
        return False


def cadastrar_ferias(usuario: str, data_inicio: date, data_fim: date, dias_aviso: int = 7):
    """Cadastra período de férias de um funcionário"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ferias_funcionarios (usuario, data_inicio, data_fim, dias_aviso)
            VALUES (%s, %s, %s, %s)
        """, (usuario, data_inicio, data_fim, dias_aviso))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Férias cadastradas para {usuario}: {data_inicio} a {data_fim}")
        return True
        
    except Exception as e:
        logger.error(f"[Push] Erro ao cadastrar férias: {e}")
        return False


def verificar_lembretes_ferias():
    """Verifica e envia lembretes de férias (executa diariamente)"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoje = date.today()
        
        # Buscar férias próximas não notificadas
        cursor.execute("""
            SELECT f.id, f.usuario, f.data_inicio, f.dias_aviso, u.nome_completo
            FROM ferias_funcionarios f
            LEFT JOIN usuarios u ON f.usuario = u.usuario
            WHERE f.notificado = FALSE 
              AND f.data_inicio - %s <= f.dias_aviso
              AND f.data_inicio >= %s
        """, (hoje, hoje))
        
        ferias = cursor.fetchall()
        
        for ferias_id, usuario, data_inicio, dias_aviso, nome in ferias:
            dias_restantes = (data_inicio - hoje).days
            
            # Enviar notificação
            enviar_notificacao(
                usuario,
                "🏖️ Lembrete de Férias",
                f"Suas férias começam em {dias_restantes} dia(s) ({data_inicio.strftime('%d/%m/%Y')}). Aproveite!",
                "🏖️"
            )
            
            # Marcar como notificado
            cursor.execute("UPDATE ferias_funcionarios SET notificado = TRUE WHERE id = %s", (ferias_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Verificados {len(ferias)} lembretes de férias")
        
    except Exception as e:
        logger.error(f"[Push] Erro ao verificar férias: {e}")


def verificar_aniversarios():
    """Verifica e envia notificações de aniversário (executa diariamente às 8h)"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoje = date.today()
        
        # Buscar aniversariantes do dia
        cursor.execute("""
            SELECT usuario, nome_completo, data_nascimento
            FROM usuarios
            WHERE EXTRACT(MONTH FROM data_nascimento) = %s
              AND EXTRACT(DAY FROM data_nascimento) = %s
              AND ativo = 1
        """, (hoje.month, hoje.day))
        
        aniversariantes = cursor.fetchall()
        
        if aniversariantes:
            # Buscar todos os usuários com push ativo para notificar
            cursor.execute("SELECT DISTINCT usuario FROM push_subscriptions WHERE ativo = TRUE")
            usuarios_ativos = cursor.fetchall()
            
            for aniv_usuario, nome, data_nasc in aniversariantes:
                idade = hoje.year - data_nasc.year
                
                # Notificar o aniversariante
                enviar_notificacao(
                    aniv_usuario,
                    "🎂 Feliz Aniversário!",
                    f"Parabéns {nome}! Desejamos tudo de bom no seu aniversário!",
                    "🎂"
                )
                
                # Notificar os colegas (exceto o próprio aniversariante)
                for (usuario,) in usuarios_ativos:
                    if usuario != aniv_usuario:
                        enviar_notificacao(
                            usuario,
                            "🎉 Aniversário de Colega",
                            f"Hoje é aniversário de {nome}! Deseje parabéns!",
                            "🎉"
                        )
        
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Verificados {len(aniversariantes)} aniversários")
        
    except Exception as e:
        logger.error(f"[Push] Erro ao verificar aniversários: {e}")


def verificar_inconsistencias_ponto():
    """Verifica registros de ponto inconsistentes (falta registro, executa às 18h)"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoje = date.today()
        
        # Buscar usuários ativos que não registraram ponto hoje
        cursor.execute("""
            SELECT u.usuario, u.nome_completo
            FROM usuarios u
            LEFT JOIN registros r ON u.usuario = r.usuario 
                AND DATE(r.data_hora) = %s
            WHERE u.ativo = 1 
              AND u.tipo = 'funcionario'
              AND r.id IS NULL
        """, (hoje,))
        
        sem_registro = cursor.fetchall()
        
        # Notificar quem não registrou
        for usuario, nome in sem_registro:
            # Verificar se tem push ativo
            cursor.execute("SELECT ativo FROM push_subscriptions WHERE usuario = %s", (usuario,))
            result = cursor.fetchone()
            
            if result and result[0]:
                enviar_notificacao(
                    usuario,
                    "⚠️ Registro Pendente",
                    f"Você ainda não registrou o ponto hoje ({hoje.strftime('%d/%m/%Y')}). Não esqueça!",
                    "⚠️"
                )
        
        # Verificar registros ímpares (entrou mas não saiu)
        cursor.execute("""
            SELECT r.usuario, COUNT(*) as qtd, u.nome_completo
            FROM registros r
            JOIN usuarios u ON r.usuario = u.usuario
            WHERE DATE(r.data_hora) = %s
            GROUP BY r.usuario, u.nome_completo
            HAVING MOD(COUNT(*), 2) = 1
        """, (hoje,))
        
        registros_impares = cursor.fetchall()
        
        for usuario, qtd, nome in registros_impares:
            cursor.execute("SELECT ativo FROM push_subscriptions WHERE usuario = %s", (usuario,))
            result = cursor.fetchone()
            
            if result and result[0]:
                enviar_notificacao(
                    usuario,
                    "⚠️ Registro Incompleto",
                    f"Você tem {qtd} registro(s) hoje - falta registrar uma saída/entrada!",
                    "⚠️"
                )
        
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Verificadas inconsistências: {len(sem_registro)} sem registro, {len(registros_impares)} incompletos")
        
    except Exception as e:
        logger.error(f"[Push] Erro ao verificar inconsistências: {e}")


def notificar_gestor_solicitacao(gestor: str, tipo: str, solicitante: str, descricao: str):
    """Notifica o gestor sobre nova solicitação de funcionário"""
    from database_postgresql import get_connection
    
    try:
        # Verificar se gestor tem push ativo
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT ativo FROM push_subscriptions WHERE usuario = %s", (gestor,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0]:
            emojis = {
                'hora_extra': '🕐',
                'atestado': '📋',
                'correcao': '🔧',
                'ferias': '🏖️'
            }
            
            emoji = emojis.get(tipo, '📢')
            
            enviar_notificacao(
                gestor,
                f"{emoji} Nova Solicitação",
                f"{solicitante} enviou uma solicitação de {tipo}: {descricao}",
                emoji
            )
            
            logger.info(f"[Push] Gestor {gestor} notificado sobre {tipo} de {solicitante}")
            return True
            
    except Exception as e:
        logger.error(f"[Push] Erro ao notificar gestor: {e}")
    
    return False


def enviar_resumo_pendencias_gestor():
    """Envia resumo diário de pendências para gestores (executa às 8h)"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar gestores com push ativo
        cursor.execute("""
            SELECT p.usuario 
            FROM push_subscriptions p
            JOIN usuarios u ON p.usuario = u.usuario
            WHERE p.ativo = TRUE AND u.tipo = 'gestor'
        """)
        
        gestores = cursor.fetchall()
        
        for (gestor,) in gestores:
            # Contar pendências
            cursor.execute("""
                SELECT COUNT(*) FROM solicitacoes_horas_extras 
                WHERE status = 'pendente' AND aprovador = %s
            """, (gestor,))
            he_pendentes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM atestado_horas WHERE status = 'pendente'")
            atestados_pendentes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM solicitacoes_correcao_registro WHERE status = 'pendente'")
            correcoes_pendentes = cursor.fetchone()[0]
            
            total = he_pendentes + atestados_pendentes + correcoes_pendentes
            
            if total > 0:
                mensagem = f"Você tem {total} pendência(s):\n"
                if he_pendentes > 0:
                    mensagem += f"• {he_pendentes} hora(s) extra(s)\n"
                if atestados_pendentes > 0:
                    mensagem += f"• {atestados_pendentes} atestado(s)\n"
                if correcoes_pendentes > 0:
                    mensagem += f"• {correcoes_pendentes} correção(ões)"
                
                enviar_notificacao(
                    gestor,
                    "📋 Resumo de Pendências",
                    mensagem,
                    "📋"
                )
        
        cursor.close()
        conn.close()
        
        logger.info(f"[Push] Resumo enviado para {len(gestores)} gestores")
        
    except Exception as e:
        logger.error(f"[Push] Erro ao enviar resumo: {e}")


def obter_avisos_gestor(limite: int = 20):
    """Obtém últimos avisos enviados pelo gestor"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.id, a.gestor, a.titulo, a.mensagem, a.destinatarios, 
                   a.data_envio, u.nome_completo
            FROM avisos_gestor a
            LEFT JOIN usuarios u ON a.gestor = u.usuario
            ORDER BY a.data_envio DESC
            LIMIT %s
        """, (limite,))
        
        avisos = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return avisos
        
    except Exception as e:
        logger.error(f"[Push] Erro ao obter avisos: {e}")
        return []


def obter_ferias_funcionarios():
    """Obtém lista de férias cadastradas"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT f.id, f.usuario, f.data_inicio, f.data_fim, f.dias_aviso, 
                   f.notificado, u.nome_completo
            FROM ferias_funcionarios f
            LEFT JOIN usuarios u ON f.usuario = u.usuario
            ORDER BY f.data_inicio DESC
        """)
        
        ferias = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return ferias
        
    except Exception as e:
        logger.error(f"[Push] Erro ao obter férias: {e}")
        return []


def excluir_ferias(ferias_id: int):
    """Exclui um registro de férias"""
    from database_postgresql import get_connection
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM ferias_funcionarios WHERE id = %s", (ferias_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"[Push] Erro ao excluir férias: {e}")
        return False
