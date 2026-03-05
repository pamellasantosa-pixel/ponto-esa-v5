"""
Módulo centralizado de Logging para Ponto ExSA v5.

Configura um logger global que:
- Grava erros num ficheiro rotativo (logs/app.log, máx 5 MB × 3 backups)
- Exibe mensagens >= WARNING no console (stdout)
- Fornece funções helper para registar eventos relevantes

Uso em qualquer módulo:
    from app_logger import get_logger
    logger = get_logger(__name__)
    logger.info("Mensagem informativa")
    logger.error("Algo deu errado", exc_info=True)
"""

import os
import logging
from logging.handlers import RotatingFileHandler

# ---------- configuração ----------

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

_configured = False


def _configure_root_logger() -> None:
    """Configura o root logger uma única vez por processo."""
    global _configured
    if _configured:
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # Handler de arquivo rotativo
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Handler de console (apenas WARNING+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    # Evitar duplicar handlers se chamado mais de uma vez
    if not root.handlers:
        root.setLevel(logging.DEBUG)
        root.addHandler(file_handler)
        root.addHandler(console_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger nomeado já configurado.

    Args:
        name: geralmente ``__name__`` do módulo chamador.

    Returns:
        logging.Logger configurado com file + console handlers.
    """
    _configure_root_logger()
    return logging.getLogger(name)


def log_user_action(usuario: str, acao: str, detalhes: str = "") -> None:
    """Registra uma ação do usuário para auditoria.

    Args:
        usuario: login do usuário que executou a ação.
        acao: descrição curta da ação (ex: "login", "registro_ponto").
        detalhes: informações adicionais opcionais.
    """
    logger = get_logger("audit")
    logger.info("user=%s | action=%s | %s", usuario, acao, detalhes)


def log_db_error(modulo: str, operacao: str, erro: Exception) -> None:
    """Registra um erro de banco de dados com contexto.

    Args:
        modulo: nome do módulo onde ocorreu o erro.
        operacao: descrição da operação que falhou.
        erro: exceção capturada.
    """
    logger = get_logger("db_error")
    logger.error(
        "module=%s | op=%s | error=%s",
        modulo,
        operacao,
        str(erro),
        exc_info=True,
    )
