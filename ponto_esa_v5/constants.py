"""
Constantes globais do sistema Ponto ExSA v5.

Centraliza todos os valores numéricos, limites e thresholds usados
pelo sistema para eliminar magic numbers e facilitar manutenção.
"""

from datetime import datetime, date, timedelta

# =============================================
# TIMEZONE
# =============================================
TIMEZONE_NAME = "America/Sao_Paulo"

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
    TIMEZONE_BR = ZoneInfo(TIMEZONE_NAME)
except ImportError:
    import pytz
    TIMEZONE_BR = pytz.timezone(TIMEZONE_NAME)


def agora_br() -> datetime:
    """Retorna datetime.now() com timezone de Brasília (America/Sao_Paulo).
    
    Substituto universal para datetime.now() em todo o projeto.
    Retorna datetime aware — para persistir no banco sem timezone,
    use agora_br_naive().
    """
    return datetime.now(TIMEZONE_BR)


def agora_br_naive() -> datetime:
    """Retorna datetime atual de Brasília SEM timezone info.
    
    Uso: quando o banco armazena timestamps sem timezone (timestamp without time zone).
    """
    return agora_br().replace(tzinfo=None)


def hoje_br() -> date:
    """Retorna date de hoje no fuso de Brasília."""
    return agora_br().date()

# =============================================
# CONNECTION POOL
# =============================================
DB_POOL_MIN_CONN = 2
DB_POOL_MAX_CONN = 15
DB_CONNECT_TIMEOUT = 5  # reduzido para 5 segundos para fail-fast e evitar reconexões prolongadas

# =============================================
# UI / UX
# =============================================
UI_FEEDBACK_DELAY_SECONDS = 2  # pausa visual após ação do usuário
DEFAULT_REPORT_DAYS = 30  # período padrão para relatórios

# =============================================
# LIMITES DE NEGÓCIO
# =============================================
MAX_RETROACTIVE_DAYS = 7  # máximo de dias para registro retroativo
MIN_EMPLOYEE_AGE_YEARS = 16  # idade mínima de funcionário
CLT_MAX_DAILY_OVERTIME_HOURS = 2  # limite CLT de HE diária
CLT_MAX_MONTHLY_OVERTIME_HOURS = 40  # limite CLT de HE mensal

# =============================================
# PERFORMANCE / CACHE
# =============================================
SLOW_QUERY_THRESHOLD_MS = 500  # alerta de query lenta
CACHE_TTL_SHORT = 60  # 1 min  — dados voláteis
CACHE_TTL_MEDIUM = 300  # 5 min  — projetos, usuários
CACHE_TTL_LONG = 3600  # 1 hora — configurações estáveis
PERF_MONITOR_MAX_ITEMS = 1000  # limite de itens no monitor
CACHE_MAX_ENTRIES = 100  # máximo de entradas no cache de sessão

# =============================================
# NOTIFICAÇÕES
# =============================================
MAX_NOTIFICATION_DESC_LEN = 100  # truncar descrição de notificação
PUSH_TIMEOUT_SECONDS = 10  # timeout para envio de push
GEOCODING_TIMEOUT_SECONDS = 5  # timeout para geocodificação

# =============================================
# SCHEDULER
# =============================================
SCHEDULER_MISFIRE_GRACE_SECONDS = 30
POLL_INTERVAL_SECONDS = 60  # intervalo de checagem do scheduler
ERROR_RETRY_DELAY_SECONDS = 30  # retry após erro

# =============================================
# ARQUIVOS / UPLOADS
# =============================================
MAX_UPLOAD_SIZE_MB = 10
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

# =============================================
# LOGS
# =============================================
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB por ficheiro de log
LOG_BACKUP_COUNT = 3

# =============================================
# SEGURANÇA
# =============================================
MAX_LOGIN_ATTEMPTS = 5  # bloqueio após N tentativas
PASSWORD_MIN_LENGTH = 8

# =============================================
# TABELAS VÁLIDAS (whitelist para operações DDL dinâmicas)
# =============================================
VALID_TABLE_NAMES = frozenset({
    "usuarios", "registros_ponto", "ausencias", "projetos",
    "solicitacoes_horas_extras", "uploads", "atestado_horas",
    "atestados_horas", "banco_horas", "feriados", "jornada_semanal",
    "Notificacoes", "solicitacoes_ajuste_ponto",
    "solicitacoes_correcao_registro", "configuracoes",
    "auditoria_correcoes", "horas_extras_ativas",
    "auditoria_alteracoes_ponto", "pendencias_ponto_ignoradas",
    "push_subscriptions", "push_notifications_log",
    "config_lembretes_push", "db_migrations",
})
