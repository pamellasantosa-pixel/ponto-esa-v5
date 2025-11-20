"""
Gerenciador centralizado de conexões com banco de dados.
Implementa context managers para garantir limpeza segura de recursos.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional
import time
import os

# Importar de database.py que detecta automaticamente se é PostgreSQL ou SQLite
# e adapta os placeholders SQL conforme necessário
if os.getenv('USE_POSTGRESQL', 'false').lower() == 'true':
    from database_postgresql import get_connection, USE_POSTGRESQL
else:
    from database import get_connection
    USE_POSTGRESQL = False

try:
    from error_handler import (
        log_error,
        log_database_operation,
        database_logger,
        get_logger,
    )
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """Gerenciador singleton de pool de conexões."""
    
    _instance = None
    _active_connections = 0
    _max_connections = 20
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._active_connections = 0
            cls._instance._max_connections = 20
        return cls._instance
    
    @classmethod
    def get_active_count(cls) -> int:
        """Retorna número de conexões ativas."""
        pool = cls()
        return pool._active_connections
    
    @classmethod
    def set_max_connections(cls, max_conn: int) -> None:
        """Define limite máximo de conexões."""
        pool = cls()
        pool._max_connections = max_conn


# Inicializar o pool uma vez
_pool = DatabaseConnectionPool()


@contextmanager
def safe_database_connection(
    db_path: Optional[str] = None,
) -> Generator[Any, None, None]:
    """
    Context manager para conexão segura com banco de dados.
    
    Garante:
    - Conexão sempre será fechada
    - Exceções são loggadas
    - Transações são commitadas ou rollback
    
    Uso:
        with safe_database_connection() as cursor:
            cursor.execute("SELECT * FROM usuarios")
            rows = cursor.fetchall()
    """
    conn = None
    try:
        conn = get_connection(db_path)
        _pool._active_connections += 1
        
        if _pool._active_connections > _pool._max_connections:
            logger.warning(
                f"⚠️ Conexões ativas: {_pool._active_connections}/"
                f"{_pool._max_connections}"
            )
        
        yield conn
        
        if conn:
            conn.commit()
            
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception as rollback_err:
                logger.error(f"❌ Erro ao fazer rollback: {rollback_err}")
        
        logger.error(f"❌ Erro em transação de banco de dados: {e}", exc_info=True)
        raise
        
    finally:
        if conn:
            try:
                conn.close()
            except Exception as close_err:
                logger.error(f"❌ Erro ao fechar conexão: {close_err}")
            finally:
                _pool._active_connections -= 1


@contextmanager
def safe_cursor(
    db_path: Optional[str] = None,
) -> Generator[Any, None, None]:
    """
    Context manager para cursor seguro com banco de dados.
    
    Garante:
    - Cursor sempre será fechado
    - Conexão sempre será fechada
    - Erros são tratados corretamente
    
    Uso:
        with safe_cursor() as cursor:
            cursor.execute("SELECT * FROM usuarios")
            return cursor.fetchall()
    """
    with safe_database_connection(db_path) as conn:
        cursor = conn.cursor()
        try:
            yield cursor
        except Exception as e:
            logger.error(f"❌ Erro ao executar query: {e}", exc_info=True)
            raise
        finally:
            try:
                cursor.close()
            except Exception as close_err:
                logger.error(f"❌ Erro ao fechar cursor: {close_err}")


def execute_query(
    query: str,
    params: tuple = (),
    fetch_one: bool = False,
    db_path: Optional[str] = None,
) -> Optional[Any]:
    """
    Executa query de forma segura com tratamento de erro automático.
    
    Args:
        query: Query SQL a executar
        params: Parâmetros para bind
        fetch_one: Se True, retorna um registro; se False, retorna todos
        db_path: Caminho do banco SQLite (None para PostgreSQL)
    
    Returns:
        Resultado da query ou None se erro
    
    Uso:
        result = execute_query("SELECT * FROM usuarios WHERE usuario = %s", ("joao",))
    """
    start_time = time.time()
    try:
        with safe_cursor(db_path) as cursor:
            cursor.execute(query, params)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if fetch_one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()
            
            # Log da operação bem-sucedida
            try:
                log_database_operation(
                    operation="SELECT",
                    query=query,
                    duration_ms=duration_ms,
                    success=True,
                )
            except:
                pass  # Falha ao logar não deve afetar aplicação
            
            return result
                
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"❌ Erro ao executar query: {query[:100]}... - {e}", exc_info=True)
        
        # Log da operação falhada
        try:
            log_database_operation(
                operation="SELECT",
                query=query,
                duration_ms=duration_ms,
                success=False,
            )
        except:
            pass  # Falha ao logar não deve afetar aplicação
        
        return None


def execute_update(
    query: str,
    params: tuple = (),
    db_path: Optional[str] = None,
) -> bool:
    """
    Executa INSERT/UPDATE/DELETE de forma segura.
    
    Args:
        query: Query SQL a executar
        params: Parâmetros para bind
        db_path: Caminho do banco SQLite (None para PostgreSQL)
    
    Returns:
        True se sucesso, False se erro
    
    Uso:
        success = execute_update(
            "UPDATE usuarios SET nome_completo = %s WHERE usuario = %s",
            ("João", "joao")
        )
    """
    start_time = time.time()
    try:
        with safe_cursor(db_path) as cursor:
            cursor.execute(query, params)
            
            # Determinar tipo de operação
            query_upper = query.strip().upper()
            if query_upper.startswith("INSERT"):
                operation = "INSERT"
            elif query_upper.startswith("UPDATE"):
                operation = "UPDATE"
            elif query_upper.startswith("DELETE"):
                operation = "DELETE"
            else:
                operation = "EXECUTE"
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Log da operação bem-sucedida
            try:
                log_database_operation(
                    operation=operation,
                    query=query,
                    duration_ms=duration_ms,
                    success=True,
                )
            except:
                pass  # Falha ao logar não deve afetar aplicação
            
            return True
            
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(f"❌ Erro ao executar update: {query[:100]}... - {e}", exc_info=True)
        
        # Log da operação falhada
        try:
            log_database_operation(
                operation="UPDATE",
                query=query,
                duration_ms=duration_ms,
                success=False,
            )
        except:
            pass  # Falha ao logar não deve afetar aplicação
        
        return False


__all__ = [
    "safe_database_connection",
    "safe_cursor",
    "execute_query",
    "execute_update",
    "DatabaseConnectionPool",
]
