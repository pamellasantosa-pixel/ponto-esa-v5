"""
Sistema de Push Notifications usando ntfy.sh (gratuito).

Envia lembretes de ponto, avisos, aniversários e alertas.
Todas as operações de banco usam o pool centralizado de ``database.py``.
"""

import os
import hashlib
import re
import requests
import threading
from datetime import date
from contextlib import contextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app_logger import get_logger, log_db_error

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Importação centralizada do banco — USA O POOL de database.py
# ---------------------------------------------------------------------------
try:
    from database import get_connection, return_connection, SQL_PLACEHOLDER
except ImportError:
    from ponto_esa_v5.database import get_connection, return_connection, SQL_PLACEHOLDER

# URL base do ntfy.sh (gratuito e público)
NTFY_URL = "https://ntfy.sh"

# Horários de lembrete PADRÃO (hora, minuto, mensagem, emoji)
HORARIOS_LEMBRETE_PADRAO = [
    (7, 50, "Bom dia! Não esqueça de registrar a entrada.", "🌅"),
    (12, 0, "Hora do almoço! Registre a saída.", "🍽️"),
    (13, 0, "Voltando do almoço? Registre a entrada.", "☕"),
    (16, 50, "Quase na hora! Registre a saída.", "🏠"),
]


# ---------------------------------------------------------------------------
# Helpers de conexão (usa pool e devolve corretamente)
# ---------------------------------------------------------------------------

@contextmanager
def _db():
    """Context manager que obtém conexão do pool e a devolve ao final."""
    conn = get_connection()
    try:
        yield conn
    finally:
        return_connection(conn)


def _ph(count: int = 1) -> str:
    """Retorna placeholders SQL separados por vírgula."""
    return ", ".join([SQL_PLACEHOLDER] * count)


# ---------------------------------------------------------------------------
# Funções de tópico
# ---------------------------------------------------------------------------

def get_topic_for_user(usuario: str) -> str:
    """Gera um tópico ntfy único e determinístico para o usuário.

    Args:
        usuario: login do usuário.

    Returns:
        String no formato ``ponto-exsa-<hash8>``.
    """
    hash_user = hashlib.md5(f"ponto_exsa_{usuario}".encode()).hexdigest()[:8]
    return f"ponto-exsa-{hash_user}"


# ---------------------------------------------------------------------------
# Envio de notificação via ntfy
# ---------------------------------------------------------------------------

def enviar_notificacao(usuario: str, titulo: str, mensagem: str, emoji: str = "📋") -> bool:
    """Envia uma notificação push para o usuário via ntfy.sh.

    Args:
        usuario: login do usuário.
        titulo: título da notificação.
        mensagem: corpo da notificação.
        emoji: emoji decorativo para o título.

    Returns:
        True se enviada com sucesso, False caso contrário.
    """
    if not usuario or not titulo:
        logger.warning("[Push] Tentativa de envio com parâmetros vazios")
        return False

    topic = get_topic_for_user(usuario)
    url = f"{NTFY_URL}/{topic}"

    try:
        response = requests.post(
            url,
            data=mensagem.encode("utf-8"),
            headers={
                "Title": f"{emoji} {titulo}",
                "Priority": "high",
                "Tags": "clock,calendar",
                "Click": os.getenv("APP_URL", "https://ponto-exsa.onrender.com"),
            },
            timeout=10,
        )
        if response.status_code == 200:
            logger.info("[Push] Notificação enviada para %s: %s", usuario, mensagem[:80])
            return True

        logger.error("[Push] Erro ao enviar para %s: HTTP %s", usuario, response.status_code)
        return False

    except requests.RequestException as e:
        logger.error("[Push] Exceção ao enviar para %s: %s", usuario, e)
        return False


# ---------------------------------------------------------------------------
# Lembrete de ponto (executado pelo scheduler)
# ---------------------------------------------------------------------------

def enviar_lembrete_ponto(hora: int, minuto: int, mensagem: str, emoji: str) -> None:
    """Envia lembrete para todos os usuários inscritos, respeitando horários personalizados."""
    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT usuario, horario_entrada, horario_almoco_saida,
                       horario_almoco_retorno, horario_saida
                FROM push_subscriptions
                WHERE ativo = TRUE
            """)
            usuarios = cursor.fetchall()
            cursor.close()

        hora_atual = f"{hora:02d}:{minuto:02d}"
        logger.info("[Push] Verificando lembrete das %s para %d usuários", hora_atual, len(usuarios))

        for row in usuarios:
            usuario = row[0]
            horarios = {
                "entrada": row[1] or "07:50",
                "almoco_saida": row[2] or "12:00",
                "almoco_retorno": row[3] or "13:00",
                "saida": row[4] or "16:50",
            }

            msg_personalizada = _mensagem_para_horario(hora_atual, horarios)
            if msg_personalizada:
                enviar_notificacao(usuario, "Lembrete de Ponto", msg_personalizada, emoji)

    except Exception as e:
        log_db_error(__name__, "enviar_lembrete_ponto", e)


def _mensagem_para_horario(hora_atual: str, horarios: dict):
    """Retorna a mensagem de lembrete apropriada para o horário, ou None."""
    mapa = {
        horarios["entrada"]: "Bom dia! Não esqueça de registrar a entrada.",
        horarios["almoco_saida"]: "Hora do almoço! Registre a saída.",
        horarios["almoco_retorno"]: "Voltando do almoço? Registre a entrada.",
        horarios["saida"]: "Quase na hora! Registre a saída.",
    }
    return mapa.get(hora_atual)


# ---------------------------------------------------------------------------
# Tabelas de push (criação idempotente)
# ---------------------------------------------------------------------------

def criar_tabela_subscriptions() -> None:
    """Cria tabelas de push (subscriptions, avisos, mensagens, férias) se não existirem."""
    try:
        with _db() as conn:
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

            for col, default in [
                ("horario_entrada", "'07:50'"),
                ("horario_almoco_saida", "'12:00'"),
                ("horario_almoco_retorno", "'13:00'"),
                ("horario_saida", "'16:50'"),
            ]:
                try:
                    cursor.execute(
                        f"ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS {col} VARCHAR(5) DEFAULT {default}"
                    )
                except Exception as e:
                    logger.debug("Erro silenciado: %s", e)

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
        logger.info("[Push] Tabelas de push criadas/verificadas")

    except Exception as e:
        log_db_error(__name__, "criar_tabela_subscriptions", e)


# ---------------------------------------------------------------------------
# CRUD de subscriptions
# ---------------------------------------------------------------------------

def registrar_subscription(usuario: str) -> str:
    """Registra (ou reativa) um usuário para receber push notifications.

    Returns:
        Tópico ntfy atribuído ao usuário.
    """
    criar_tabela_subscriptions()
    topic = get_topic_for_user(usuario)

    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO push_subscriptions (usuario, topic, ativo)
                VALUES ({_ph(3)})
                ON CONFLICT (usuario)
                DO UPDATE SET ativo = TRUE, topic = {SQL_PLACEHOLDER}
            """, (usuario, topic, True, topic))
            conn.commit()
            cursor.close()
        logger.info("[Push] Usuário %s registrado com topic: %s", usuario, topic)
    except Exception as e:
        log_db_error(__name__, "registrar_subscription", e)

    return topic


def desativar_subscription(usuario: str) -> None:
    """Desativa push notifications para um usuário."""
    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE push_subscriptions SET ativo = FALSE WHERE usuario = {SQL_PLACEHOLDER}",
                (usuario,),
            )
            conn.commit()
            cursor.close()
        logger.info("[Push] Push desativado para %s", usuario)
    except Exception as e:
        log_db_error(__name__, "desativar_subscription", e)


def verificar_subscription(usuario: str) -> tuple:
    """Verifica se usuário tem push ativo e retorna o tópico.

    Returns:
        Tupla ``(topic, ativo)`` — ``(None, False)`` se não encontrado.
    """
    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT topic, ativo FROM push_subscriptions WHERE usuario = {SQL_PLACEHOLDER}",
                (usuario,),
            )
            result = cursor.fetchone()
            cursor.close()
            if result:
                return result[0], result[1]
    except Exception as e:
        log_db_error(__name__, "verificar_subscription", e)

    return None, False


# ---------------------------------------------------------------------------
# Horários personalizados
# ---------------------------------------------------------------------------

def atualizar_horarios_usuario(
    usuario: str, entrada: str, almoco_saida: str, almoco_retorno: str, saida: str
) -> bool:
    """Atualiza os horários de lembrete personalizados de um usuário."""
    pattern = re.compile(r"^\d{2}:\d{2}$")
    for h in (entrada, almoco_saida, almoco_retorno, saida):
        if not pattern.match(str(h)):
            logger.warning("[Push] Horário inválido: %s", h)
            return False

    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE push_subscriptions
                SET horario_entrada = {SQL_PLACEHOLDER},
                    horario_almoco_saida = {SQL_PLACEHOLDER},
                    horario_almoco_retorno = {SQL_PLACEHOLDER},
                    horario_saida = {SQL_PLACEHOLDER}
                WHERE usuario = {SQL_PLACEHOLDER}
            """, (entrada, almoco_saida, almoco_retorno, saida, usuario))
            conn.commit()
            cursor.close()
        logger.info("[Push] Horários atualizados para %s", usuario)
        return True
    except Exception as e:
        log_db_error(__name__, "atualizar_horarios_usuario", e)
        return False


def obter_horarios_usuario(usuario: str) -> dict:
    """Obtém os horários de lembrete personalizados de um usuário."""
    defaults = {
        "entrada": "07:50",
        "almoco_saida": "12:00",
        "almoco_retorno": "13:00",
        "saida": "16:50",
    }
    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT horario_entrada, horario_almoco_saida,
                       horario_almoco_retorno, horario_saida
                FROM push_subscriptions WHERE usuario = {SQL_PLACEHOLDER}
            """, (usuario,))
            result = cursor.fetchone()
            cursor.close()

        if result:
            return {
                "entrada": result[0] or defaults["entrada"],
                "almoco_saida": result[1] or defaults["almoco_saida"],
                "almoco_retorno": result[2] or defaults["almoco_retorno"],
                "saida": result[3] or defaults["saida"],
            }
    except Exception as e:
        log_db_error(__name__, "obter_horarios_usuario", e)

    return defaults


# ---------------------------------------------------------------------------
# Avisos gerais (gestor → funcionários)
# ---------------------------------------------------------------------------

def listar_subscriptions_ativas() -> list:
    """Retorna lista de dicts com info de push de todos os usuários.

    Returns:
        Lista de {"usuario": str, "topic": str, "ativo": bool}.
    """
    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT usuario, topic, ativo FROM push_subscriptions ORDER BY usuario"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [{"usuario": r[0], "topic": r[1], "ativo": bool(r[2])} for r in rows]
    except Exception as e:
        log_db_error(__name__, "listar_subscriptions_ativas", e)
        return []


def enviar_aviso_geral(gestor: str, titulo: str, mensagem: str, destinatarios: str = "todos") -> int:
    """Gestor envia aviso para todos os funcionários ou grupo específico.

    Quando o destinatário não tem subscription na tabela, envia diretamente
    para o tópico ntfy gerado a partir do username (fallback).

    Returns:
        Quantidade de notificações enviadas com sucesso.
    """
    if not titulo or not mensagem:
        return 0

    try:
        # Salvar aviso no banco
        with _db() as conn:
            cursor = conn.cursor()

            cursor.execute(f"""
                INSERT INTO avisos_gestor (gestor, titulo, mensagem, destinatarios)
                VALUES ({_ph(4)})
            """, (gestor, titulo, mensagem, destinatarios))

            conn.commit()
            cursor.close()

        # Determinar lista de destinatários
        if destinatarios == "todos":
            # Buscar todos os usuários ativos do sistema
            with _db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT usuario FROM usuarios WHERE ativo = 1"
                )
                todos_usuarios = [r[0] for r in cursor.fetchall()]
                cursor.close()
            lista_destino = todos_usuarios
        else:
            lista_destino = [d.strip() for d in destinatarios.split(",") if d.strip()]

        logger.info("[Push] Enviando aviso para %d destinatário(s): %s", len(lista_destino), lista_destino)

        # Enviar para cada destinatário (usa tópico ntfy direto, sem depender de subscription)
        enviados = 0
        for usuario in lista_destino:
            try:
                ok = enviar_notificacao(usuario, f"📢 {titulo}", mensagem, "📢")
                if ok:
                    enviados += 1
                else:
                    logger.warning("[Push] Falha ao enviar para %s", usuario)
            except Exception as e:
                logger.error("[Push] Erro ao enviar para %s: %s", usuario, e)

        logger.info("[Push] Aviso enviado para %d de %d usuários", enviados, len(lista_destino))
        return enviados

    except Exception as e:
        log_db_error(__name__, "enviar_aviso_geral", e)
        return 0


# ---------------------------------------------------------------------------
# Mensagens diretas
# ---------------------------------------------------------------------------

def enviar_mensagem_direta(remetente: str, destinatario: str, mensagem: str) -> bool:
    """Envia mensagem direta de um usuário para outro."""
    if not remetente or not destinatario or not mensagem:
        return False

    try:
        with _db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}",
                (remetente,),
            )
            result = cursor.fetchone()
            nome_remetente = result[0] if result else remetente

            cursor.execute(f"""
                INSERT INTO mensagens_diretas (remetente, destinatario, mensagem)
                VALUES ({_ph(3)})
            """, (remetente, destinatario, mensagem))

            conn.commit()
            cursor.close()

        enviar_notificacao(destinatario, f"💬 Mensagem de {nome_remetente}", mensagem, "💬")
        logger.info("[Push] Mensagem enviada de %s para %s", remetente, destinatario)
        return True

    except Exception as e:
        log_db_error(__name__, "enviar_mensagem_direta", e)
        return False


def obter_mensagens_usuario(usuario: str, apenas_nao_lidas: bool = False) -> list:
    """Obtém mensagens diretas de um usuário."""
    try:
        with _db() as conn:
            cursor = conn.cursor()
            query = f"""
                SELECT m.id, m.remetente, m.mensagem, m.data_envio, m.lida, u.nome_completo
                FROM mensagens_diretas m
                LEFT JOIN usuarios u ON m.remetente = u.usuario
                WHERE m.destinatario = {SQL_PLACEHOLDER}
            """
            if apenas_nao_lidas:
                query += " AND m.lida = FALSE"
            query += " ORDER BY m.data_envio DESC"

            cursor.execute(query, (usuario,))
            mensagens = cursor.fetchall()
            cursor.close()
            return mensagens

    except Exception as e:
        log_db_error(__name__, "obter_mensagens_usuario", e)
        return []


def marcar_mensagem_lida(mensagem_id: int) -> bool:
    """Marca uma mensagem como lida."""
    if not isinstance(mensagem_id, int) or mensagem_id <= 0:
        return False

    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE mensagens_diretas SET lida = TRUE WHERE id = {SQL_PLACEHOLDER}",
                (mensagem_id,),
            )
            conn.commit()
            cursor.close()
        return True
    except Exception as e:
        log_db_error(__name__, "marcar_mensagem_lida", e)
        return False


# ---------------------------------------------------------------------------
# Férias
# ---------------------------------------------------------------------------

def cadastrar_ferias(usuario: str, data_inicio, data_fim, dias_aviso: int = 7) -> bool:
    """Cadastra período de férias de um funcionário."""
    if not usuario or not data_inicio or not data_fim:
        return False

    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO ferias_funcionarios (usuario, data_inicio, data_fim, dias_aviso)
                VALUES ({_ph(4)})
            """, (usuario, data_inicio, data_fim, dias_aviso))
            conn.commit()
            cursor.close()
        logger.info("[Push] Férias cadastradas para %s: %s a %s", usuario, data_inicio, data_fim)
        return True
    except Exception as e:
        log_db_error(__name__, "cadastrar_ferias", e)
        return False


def verificar_lembretes_ferias() -> None:
    """Verifica e envia lembretes de férias (executado diariamente pelo scheduler)."""
    try:
        hoje = date.today()
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT f.id, f.usuario, f.data_inicio, f.dias_aviso, u.nome_completo
                FROM ferias_funcionarios f
                LEFT JOIN usuarios u ON f.usuario = u.usuario
                WHERE f.notificado = FALSE
                  AND f.data_inicio - {SQL_PLACEHOLDER} <= f.dias_aviso
                  AND f.data_inicio >= {SQL_PLACEHOLDER}
            """, (hoje, hoje))

            ferias = cursor.fetchall()

            for ferias_id, usuario, data_inicio, dias_aviso, nome in ferias:
                dias_restantes = (data_inicio - hoje).days
                enviar_notificacao(
                    usuario,
                    "🏖️ Lembrete de Férias",
                    f"Suas férias começam em {dias_restantes} dia(s) ({data_inicio.strftime('%d/%m/%Y')}). Aproveite!",
                    "🏖️",
                )
                cursor.execute(
                    f"UPDATE ferias_funcionarios SET notificado = TRUE WHERE id = {SQL_PLACEHOLDER}",
                    (ferias_id,),
                )

            conn.commit()
            cursor.close()
        logger.info("[Push] Verificados %d lembretes de férias", len(ferias))

    except Exception as e:
        log_db_error(__name__, "verificar_lembretes_ferias", e)


def verificar_aniversarios() -> None:
    """Verifica e envia notificações de aniversário (executado diariamente às 8h)."""
    try:
        hoje = date.today()
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT usuario, nome_completo, data_nascimento
                FROM usuarios
                WHERE EXTRACT(MONTH FROM data_nascimento) = {SQL_PLACEHOLDER}
                  AND EXTRACT(DAY FROM data_nascimento) = {SQL_PLACEHOLDER}
                  AND ativo = 1
            """, (hoje.month, hoje.day))
            aniversariantes = cursor.fetchall()

            if aniversariantes:
                cursor.execute("SELECT DISTINCT usuario FROM push_subscriptions WHERE ativo = TRUE")
                usuarios_ativos = cursor.fetchall()

                for aniv_usuario, nome, _data_nasc in aniversariantes:
                    enviar_notificacao(
                        aniv_usuario,
                        "🎂 Feliz Aniversário!",
                        f"Parabéns {nome}! Desejamos tudo de bom!",
                        "🎂",
                    )
                    for (u,) in usuarios_ativos:
                        if u != aniv_usuario:
                            enviar_notificacao(u, "🎉 Aniversário", f"Hoje é aniversário de {nome}!", "🎉")

            cursor.close()
        logger.info("[Push] Verificados %d aniversários", len(aniversariantes))

    except Exception as e:
        log_db_error(__name__, "verificar_aniversarios", e)


def verificar_inconsistencias_ponto() -> None:
    """Verifica registros de ponto inconsistentes (executado às 18h)."""
    try:
        hoje = date.today()
        with _db() as conn:
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT u.usuario, u.nome_completo
                FROM usuarios u
                LEFT JOIN registros_ponto r ON u.usuario = r.usuario
                    AND DATE(r.data_hora) = {SQL_PLACEHOLDER}
                WHERE u.ativo = 1
                  AND u.tipo = 'funcionario'
                  AND r.id IS NULL
            """, (hoje,))
            sem_registro = cursor.fetchall()

            for usuario, _nome in sem_registro:
                cursor.execute(
                    f"SELECT ativo FROM push_subscriptions WHERE usuario = {SQL_PLACEHOLDER}",
                    (usuario,),
                )
                result = cursor.fetchone()
                if result and result[0]:
                    enviar_notificacao(
                        usuario,
                        "⚠️ Registro Pendente",
                        f"Você ainda não registrou o ponto hoje ({hoje.strftime('%d/%m/%Y')}).",
                        "⚠️",
                    )

            cursor.execute(f"""
                SELECT r.usuario, COUNT(*) as qtd, u.nome_completo
                FROM registros_ponto r
                JOIN usuarios u ON r.usuario = u.usuario
                WHERE DATE(r.data_hora) = {SQL_PLACEHOLDER}
                GROUP BY r.usuario, u.nome_completo
                HAVING MOD(COUNT(*), 2) = 1
            """, (hoje,))
            registros_impares = cursor.fetchall()

            for usuario, qtd, _nome in registros_impares:
                cursor.execute(
                    f"SELECT ativo FROM push_subscriptions WHERE usuario = {SQL_PLACEHOLDER}",
                    (usuario,),
                )
                result = cursor.fetchone()
                if result and result[0]:
                    enviar_notificacao(
                        usuario,
                        "⚠️ Registro Incompleto",
                        f"Você tem {qtd} registro(s) hoje - falta registrar saída/entrada!",
                        "⚠️",
                    )

            cursor.close()
        logger.info(
            "[Push] Inconsistências: %d sem registro, %d incompletos",
            len(sem_registro),
            len(registros_impares),
        )

    except Exception as e:
        log_db_error(__name__, "verificar_inconsistencias_ponto", e)


def notificar_gestor_solicitacao(gestor: str, tipo: str, solicitante: str, descricao: str) -> bool:
    """Notifica o gestor sobre nova solicitação de funcionário via push."""
    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT ativo FROM push_subscriptions WHERE usuario = {SQL_PLACEHOLDER}",
                (gestor,),
            )
            result = cursor.fetchone()
            cursor.close()

        if result and result[0]:
            emojis = {"hora_extra": "🕐", "atestado": "📋", "correcao": "🔧", "ferias": "🏖️"}
            emoji = emojis.get(tipo, "📢")
            enviar_notificacao(
                gestor,
                f"{emoji} Nova Solicitação",
                f"{solicitante} enviou uma solicitação de {tipo}: {descricao}",
                emoji,
            )
            logger.info("[Push] Gestor %s notificado sobre %s de %s", gestor, tipo, solicitante)
            return True

    except Exception as e:
        log_db_error(__name__, "notificar_gestor_solicitacao", e)

    return False


def enviar_resumo_pendencias_gestor() -> None:
    """Envia resumo diário de pendências para gestores (executado às 8h)."""
    try:
        with _db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT p.usuario
                FROM push_subscriptions p
                JOIN usuarios u ON p.usuario = u.usuario
                WHERE p.ativo = TRUE AND u.tipo = 'gestor'
            """)
            gestores = cursor.fetchall()

            for (gestor,) in gestores:
                cursor.execute(
                    f"SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente' AND aprovador_solicitado = {SQL_PLACEHOLDER}",
                    (gestor,),
                )
                he = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM atestado_horas WHERE status = 'pendente'")
                at = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM solicitacoes_correcao_registro WHERE status = 'pendente'")
                co = cursor.fetchone()[0]

                total = he + at + co
                if total > 0:
                    partes = []
                    if he:
                        partes.append(f"• {he} hora(s) extra(s)")
                    if at:
                        partes.append(f"• {at} atestado(s)")
                    if co:
                        partes.append(f"• {co} correção(ões)")
                    msg = f"Você tem {total} pendência(s):\n" + "\n".join(partes)
                    enviar_notificacao(gestor, "📋 Resumo de Pendências", msg, "📋")

            cursor.close()
        logger.info("[Push] Resumo enviado para %d gestores", len(gestores))

    except Exception as e:
        log_db_error(__name__, "enviar_resumo_pendencias_gestor", e)


# ---------------------------------------------------------------------------
# Consultas de histórico
# ---------------------------------------------------------------------------

def obter_avisos_gestor(limite: int = 20) -> list:
    """Obtém últimos avisos enviados pelo gestor."""
    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT a.id, a.gestor, a.titulo, a.mensagem, a.destinatarios,
                       a.data_envio, u.nome_completo
                FROM avisos_gestor a
                LEFT JOIN usuarios u ON a.gestor = u.usuario
                ORDER BY a.data_envio DESC
                LIMIT {SQL_PLACEHOLDER}
            """, (limite,))
            avisos = cursor.fetchall()
            cursor.close()
            return avisos
    except Exception as e:
        log_db_error(__name__, "obter_avisos_gestor", e)
        return []


def obter_ferias_funcionarios() -> list:
    """Obtém lista de férias cadastradas."""
    try:
        with _db() as conn:
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
            return ferias
    except Exception as e:
        log_db_error(__name__, "obter_ferias_funcionarios", e)
        return []


def excluir_ferias(ferias_id: int) -> bool:
    """Exclui um registro de férias."""
    if not isinstance(ferias_id, int) or ferias_id <= 0:
        return False

    try:
        with _db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM ferias_funcionarios WHERE id = {SQL_PLACEHOLDER}",
                (ferias_id,),
            )
            conn.commit()
            cursor.close()
        return True
    except Exception as e:
        log_db_error(__name__, "excluir_ferias", e)
        return False


# ---------------------------------------------------------------------------
# Scheduler (singleton, thread-safe)
# ---------------------------------------------------------------------------

_scheduler = None
_scheduler_lock = threading.Lock()


def iniciar_scheduler() -> None:
    """Inicia o scheduler de lembretes (thread-safe, idempotente)."""
    global _scheduler

    with _scheduler_lock:
        if _scheduler is not None:
            logger.info("[Push] Scheduler já está rodando")
            return

        criar_tabela_subscriptions()

        _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

        for hora, minuto, mensagem, emoji in HORARIOS_LEMBRETE_PADRAO:
            _scheduler.add_job(
                func=enviar_lembrete_ponto,
                trigger=CronTrigger(hour=hora, minute=minuto, timezone="America/Sao_Paulo"),
                args=[hora, minuto, mensagem, emoji],
                id=f"lembrete_{hora:02d}{minuto:02d}",
                replace_existing=True,
            )

        for hora, minuto in [
            (8, 0), (8, 30), (9, 0),
            (11, 30), (12, 30),
            (13, 30), (14, 0),
            (17, 0), (17, 30), (18, 0),
        ]:
            _scheduler.add_job(
                func=enviar_lembrete_ponto,
                trigger=CronTrigger(hour=hora, minute=minuto, timezone="America/Sao_Paulo"),
                args=[hora, minuto, "", "⏰"],
                id=f"lembrete_{hora:02d}{minuto:02d}",
                replace_existing=True,
            )

        _scheduler.add_job(
            func=verificar_aniversarios,
            trigger=CronTrigger(hour=8, minute=0, timezone="America/Sao_Paulo"),
            id="aniversarios_diario",
            replace_existing=True,
        )
        _scheduler.add_job(
            func=verificar_lembretes_ferias,
            trigger=CronTrigger(hour=8, minute=5, timezone="America/Sao_Paulo"),
            id="ferias_diario",
            replace_existing=True,
        )
        _scheduler.add_job(
            func=enviar_resumo_pendencias_gestor,
            trigger=CronTrigger(hour=8, minute=10, timezone="America/Sao_Paulo"),
            id="resumo_gestor_diario",
            replace_existing=True,
        )
        _scheduler.add_job(
            func=verificar_inconsistencias_ponto,
            trigger=CronTrigger(hour=18, minute=0, timezone="America/Sao_Paulo"),
            id="inconsistencias_diario",
            replace_existing=True,
        )

        _scheduler.start()
        logger.info("[Push] Scheduler de lembretes iniciado!")


def parar_scheduler() -> None:
    """Para o scheduler de forma segura."""
    global _scheduler
    with _scheduler_lock:
        if _scheduler:
            _scheduler.shutdown(wait=False)
            _scheduler = None
            logger.info("[Push] Scheduler parado")


def init_push_system() -> None:
    """Inicializa o sistema de push (entry point chamado pelo app)."""
    try:
        iniciar_scheduler()
    except Exception as e:
        logger.error("[Push] Erro ao iniciar sistema: %s", e)
