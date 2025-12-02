"""Stubs de manipuladores de erro e logging usados pela aplicação."""
import logging
logger = logging.getLogger("error_handler")


def log_error(message: str, exc: Exception | str = None, context: dict | None = None):
    logger.error("%s - %s - %s", message, exc, context)


def log_security_event(event_name: str, usuario: str | None = None, context: dict | None = None):
    logger.info("SECURITY_EVENT %s - %s - %s", event_name, usuario, context)


__all__ = ["log_error", "log_security_event"]
