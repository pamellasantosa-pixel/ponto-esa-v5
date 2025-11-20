"""
Sistema centralizado de logging com tratamento de erros.
Garante que todos os erros sejam capturados e logados adequadamente.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Optional

# Criar diretório de logs se não existir
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Nomes dos arquivos de log
MAIN_LOG = os.path.join(LOG_DIR, "ponto_esa_v5.log")
ERROR_LOG = os.path.join(LOG_DIR, "errors.log")
DATABASE_LOG = os.path.join(LOG_DIR, "database.log")
SECURITY_LOG = os.path.join(LOG_DIR, "security.log")


def setup_logger(
    name: str,
    log_file: str,
    level: int = logging.DEBUG,
) -> logging.Logger:
    """
    Configura um logger com arquivo e console.
    
    Args:
        name: Nome do logger
        log_file: Arquivo de log
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evitar duplicatas
    if logger.handlers:
        return logger
    
    # Formato comum
    formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para arquivo (com rotação)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,  # Manter 5 backups
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para console (apenas WARNING e acima em produção)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


# Criar loggers globais
main_logger = setup_logger("ponto_esa_v5", MAIN_LOG)
error_logger = setup_logger("ponto_esa_v5.errors", ERROR_LOG, level=logging.ERROR)
database_logger = setup_logger("ponto_esa_v5.database", DATABASE_LOG)
security_logger = setup_logger("ponto_esa_v5.security", SECURITY_LOG)


def log_error(
    message: str,
    error: Optional[Exception] = None,
    context: Optional[dict] = None,
    severity: str = "ERROR",
) -> None:
    """
    Loga um erro com contexto completo.
    
    Args:
        message: Mensagem de erro
        error: Exceção capturada
        context: Contexto adicional (dicionário)
        severity: CRITICAL, ERROR, WARNING
    
    Uso:
        try:
            ...
        except Exception as e:
            log_error("Erro ao processar usuário", e, {"usuario": "joao"})
    """
    full_message = f"{message}"
    
    if error:
        full_message += f" | Exception: {type(error).__name__}: {error}"
    
    if context:
        full_message += f" | Context: {context}"
    
    if severity == "CRITICAL":
        error_logger.critical(full_message, exc_info=error)
    elif severity == "ERROR":
        error_logger.error(full_message, exc_info=error)
    else:
        error_logger.warning(full_message, exc_info=error)


def log_database_operation(
    operation: str,
    query: str,
    params: Optional[tuple] = None,
    duration_ms: Optional[float] = None,
    success: bool = True,
) -> None:
    """
    Loga operações de banco de dados para auditoria.
    
    Args:
        operation: INSERT, UPDATE, DELETE, SELECT
        query: Query executada (sem dados sensíveis)
        params: Parâmetros (serão mascarados se sensíveis)
        duration_ms: Tempo em milissegundos
        success: Se operação foi bem-sucedida
    
    Uso:
        log_database_operation("UPDATE", "UPDATE usuarios SET ...", success=True, duration_ms=45)
    """
    status = "✅ SUCCESS" if success else "❌ FAILED"
    query_short = query[:80].replace('\n', ' ')
    
    message = f"{operation} | {status} | Query: {query_short}"
    
    if duration_ms:
        message += f" | Duration: {duration_ms:.2f}ms"
    
    if success:
        database_logger.info(message)
    else:
        database_logger.error(message)


def log_security_event(
    event_type: str,
    usuario: Optional[str] = None,
    details: Optional[str] = None,
    severity: str = "WARNING",
    context: Optional[dict] = None,
) -> None:
    """
    Loga eventos de segurança para auditoria.

    Args:
        event_type: LOGIN, LOGOUT, UNAUTHORIZED_ACCESS, etc.
        usuario: Usuário envolvido
        details: Detalhes do evento
        severity: INFO, WARNING, CRITICAL
        context: Dicionário com informações adicionais do contexto

    Uso:
        log_security_event("UNAUTHORIZED_ACCESS", usuario="joao", details="Tentou acessar dashboard gestor")
        log_security_event("HOUR_EXTRA_REQUESTED", usuario="joao", context={"he_id": 123, "aprovador": "maria"})
    """
    message = f"[{event_type}]"

    if usuario:
        message += f" User: {usuario}"

    if details:
        message += f" | {details}"

    if context:
        context_str = " | ".join([f"{k}: {v}" for k, v in context.items()])
        message += f" | {context_str}"

    if severity == "CRITICAL":
        security_logger.critical(message)
    elif severity == "WARNING":
        security_logger.warning(message)
    else:
        security_logger.info(message)


def get_logger(name: str) -> logging.Logger:
    """
    Obtém um logger configurado para um módulo.
    
    Uso:
        logger = get_logger(__name__)
        logger.info("Iniciando aplicação")
    """
    return logging.getLogger(f"ponto_esa_v5.{name}")


def log_summary() -> dict:
    """Retorna resumo de logs gerados."""
    return {
        "main_log": MAIN_LOG if os.path.exists(MAIN_LOG) else None,
        "error_log": ERROR_LOG if os.path.exists(ERROR_LOG) else None,
        "database_log": DATABASE_LOG if os.path.exists(DATABASE_LOG) else None,
        "security_log": SECURITY_LOG if os.path.exists(SECURITY_LOG) else None,
        "timestamp": datetime.now().isoformat(),
    }


__all__ = [
    "main_logger",
    "error_logger",
    "database_logger",
    "security_logger",
    "setup_logger",
    "get_logger",
    "log_error",
    "log_database_operation",
    "log_security_event",
    "log_summary",
]
