"""Utilitários simples de banco de dados e helpers de resposta.

Este módulo fornece apenas o mínimo necessário para que os sistemas
de horas extras funcionem nos testes, sem adicionar complexidade
desnecessária à aplicação.
"""

from contextlib import contextmanager
from typing import Any, Dict

# Importação flexível para funcionar em diferentes contextos
try:
    from database import get_connection
except ImportError:
    from ponto_esa_v5.database import get_connection


def create_success_response(message: str, **extra: Any) -> Dict[str, Any]:
    """Cria um dicionário de resposta de sucesso padronizado."""
    data: Dict[str, Any] = {"success": True, "message": message}
    data.update(extra)
    return data


def create_error_response(message: str, error: Exception | None = None, **extra: Any) -> Dict[str, Any]:
    """Cria um dicionário de resposta de erro padronizado.

    Aceita um parâmetro opcional ``error`` apenas para compatibilidade
    com chamadas existentes; ele é convertido em string na chave
    "error_detail".
    """

    data: Dict[str, Any] = {"success": False, "message": message}
    if error is not None:
        data["error_detail"] = str(error)
    data.update(extra)
    return data


@contextmanager
def database_transaction(db_path: str | None = None):
    """Context manager simples para transações de banco.

    Usa ``get_connection`` do módulo ``database`` e garante commit/rollback
    adequado em caso de erro.
    """

    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


__all__ = [
    "create_success_response",
    "create_error_response",
    "database_transaction",
]
