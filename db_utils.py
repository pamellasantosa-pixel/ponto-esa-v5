"""Utilitários de banco de dados e context managers."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional

from database_postgresql import get_connection, USE_POSTGRESQL

logger = logging.getLogger(__name__)


@contextmanager
def database_transaction() -> Generator[Any, None, None]:
    """Context manager para transações de banco de dados."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro em transação de banco de dados: {e}")
        raise
    finally:
        conn.close()


def create_error_response(message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Cria uma resposta de erro padronizada."""
    response = {"success": False, "message": message}
    if details:
        response.update(details)
    return response


def create_success_response(
    message: str, data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Cria uma resposta de sucesso padronizada."""
    response = {"success": True, "message": message}
    if data:
        response.update(data)
    return response


def execute_safe_query(
    query: str, params: tuple = (), fetch_one: bool = False
) -> Optional[Any]:
    """Executa uma query de forma segura com tratamento de erro."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
            
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Erro ao executar query: {e}")
        return None


__all__ = [
    "database_transaction",
    "create_error_response",
    "create_success_response",
    "execute_safe_query",
]
