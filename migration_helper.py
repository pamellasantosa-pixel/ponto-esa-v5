"""
Utilitários para migração de código para usar context managers.
Fornece padrões e exemplos de refatoração.
"""

from typing import Tuple

# Padrões de migração


PATTERN_OLD_CONN = """
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    conn.commit()
except Exception as e:
    logger.error(f"Erro: {e}")
    if conn:
        conn.rollback()
finally:
    if conn:
        conn.close()
"""

PATTERN_NEW_CONN = """
from connection_manager import execute_query

result = execute_query(query)
"""

PATTERN_OLD_UPDATE = """
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(update_query, params)
    conn.commit()
except Exception as e:
    logger.error(f"Erro: {e}")
    if conn:
        conn.rollback()
finally:
    if conn:
        conn.close()
"""

PATTERN_NEW_UPDATE = """
from connection_manager import execute_update

success = execute_update(update_query, params)
"""

PATTERN_OLD_SAFE_CURSOR = """
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
except Exception as e:
    logger.error(f"Erro: {e}")
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
"""

PATTERN_NEW_SAFE_CURSOR = """
from connection_manager import safe_cursor

with safe_cursor() as cursor:
    cursor.execute(query)
    result = cursor.fetchall()
"""

PATTERN_OLD_TRANSACTION = """
try:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Múltiplas operações
    cursor.execute(query1)
    cursor.execute(query2)
    
    conn.commit()
except Exception as e:
    logger.error(f"Erro: {e}")
    conn.rollback()
finally:
    if conn:
        conn.close()
"""

PATTERN_NEW_TRANSACTION = """
from connection_manager import safe_database_connection

with safe_database_connection() as conn:
    cursor = conn.cursor()
    cursor.execute(query1)
    cursor.execute(query2)
    # commit e rollback são automáticos
"""


def get_migration_guide() -> str:
    """Retorna guia completo de migração."""
    return """
╔════════════════════════════════════════════════════════════════════════════╗
║                    GUIA DE MIGRAÇÃO PARA CONTEXT MANAGERS                 ║
╚════════════════════════════════════════════════════════════════════════════╝

1. PADRÃO BÁSICO DE QUERY (SELECT)
──────────────────────────────────────────────────────────────────────────────

❌ ANTES:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios")
        result = cursor.fetchall()
        conn.commit()
    except Exception as e:
        logger.error(f"Erro: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

✅ DEPOIS:
    from connection_manager import execute_query
    
    result = execute_query("SELECT * FROM usuarios")


2. PADRÃO UPDATE/INSERT/DELETE
──────────────────────────────────────────────────────────────────────────────

❌ ANTES:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET nome = %s WHERE id = %s", (novo_nome, user_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Erro: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

✅ DEPOIS:
    from connection_manager import execute_update
    
    success = execute_update(
        "UPDATE usuarios SET nome = %s WHERE id = %s",
        (novo_nome, user_id)
    )
    if success:
        print("Atualizado com sucesso")


3. PADRÃO TRANSAÇÃO (múltiplas operações)
──────────────────────────────────────────────────────────────────────────────

❌ ANTES:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO usuarios (nome) VALUES (%s)", ("João",))
        cursor.execute("UPDATE contadores SET total = total + 1")
        conn.commit()
    except Exception as e:
        logger.error(f"Erro: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

✅ DEPOIS:
    from connection_manager import safe_database_connection
    
    try:
        with safe_database_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO usuarios (nome) VALUES (%s)", ("João",))
            cursor.execute("UPDATE contadores SET total = total + 1")
    except Exception as e:
        print(f"Erro na transação: {e}")


4. PADRÃO CURSOR PERSONALIZADO (com processamento)
──────────────────────────────────────────────────────────────────────────────

❌ ANTES:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE ativo = true")
        usuarios = cursor.fetchall()
        
        resultado = {}
        for usuario in usuarios:
            resultado[usuario[0]] = usuario[1]
        
        return resultado
    except Exception as e:
        logger.error(f"Erro: {e}")
        return {}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

✅ DEPOIS:
    from connection_manager import safe_cursor
    
    try:
        resultado = {}
        with safe_cursor() as cursor:
            cursor.execute("SELECT * FROM usuarios WHERE ativo = true")
            usuarios = cursor.fetchall()
            for usuario in usuarios:
                resultado[usuario[0]] = usuario[1]
        return resultado
    except Exception as e:
        print(f"Erro: {e}")
        return {}


5. PADRÃO COM ERROS ESPECÍFICOS
──────────────────────────────────────────────────────────────────────────────

❌ ANTES:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
        usuario = cursor.fetchone()
    except psycopg2.IntegrityError as e:
        logger.error(f"Erro de integridade: {e}")
    except psycopg2.DatabaseError as e:
        logger.error(f"Erro no banco: {e}")
    except Exception as e:
        logger.error(f"Erro desconhecido: {e}")
    finally:
        if conn:
            conn.close()

✅ DEPOIS:
    from connection_manager import safe_cursor
    import psycopg2
    from error_handler import log_error
    
    try:
        with safe_cursor() as cursor:
            cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
            usuario = cursor.fetchone()
    except psycopg2.IntegrityError as e:
        log_error("Violação de integridade", e, {"user_id": user_id}, "ERROR")
    except psycopg2.DatabaseError as e:
        log_error("Erro no banco de dados", e, {"user_id": user_id}, "ERROR")
    except Exception as e:
        log_error("Erro desconhecido", e, {"user_id": user_id}, "CRITICAL")


CHECKLIST DE MIGRAÇÃO:
──────────────────────────────────────────────────────────────────────────────

Para cada função que usa banco de dados:

□ Remover importação de `get_connection`
□ Adicionar importação de `connection_manager` (execute_query/execute_update/safe_cursor)
□ Remover try/finally/conn.close()
□ Usar context manager apropriado
□ Remover try/except genéricos, deixar apenas específicos
□ Adicionar logging com error_handler quando apropriado
□ Testar função localmente
□ Verificar se resultado é tratado corretamente
□ Fazer commit com mensagem clara


IMPORTAÇÕES NECESSÁRIAS:
──────────────────────────────────────────────────────────────────────────────

from connection_manager import (
    execute_query,      # Para SELECT simples
    execute_update,     # Para INSERT/UPDATE/DELETE
    safe_cursor,        # Para queries complexas
    safe_database_connection,  # Para transações
)

from error_handler import (
    log_error,          # Para logar erros
    log_database_operation,  # Para auditoria
)
"""


def get_functions_to_migrate() -> list:
    """Retorna lista de funções prioritárias para migração."""
    return [
        # app_v5_final.py
        ("app_v5_final.py", "get_usuario", "SELECT simples"),
        ("app_v5_final.py", "atualizar_usuario", "UPDATE com params"),
        ("app_v5_final.py", "registrar_ponto", "INSERT com transação"),
        
        # horas_extras_system.py
        ("horas_extras_system.py", "calcular_horas_extras", "SELECT com cálculo"),
        ("horas_extras_system.py", "registrar_extras", "INSERT múltiplo"),
        
        # upload_system.py
        ("upload_system.py", "processar_arquivo", "Transação complexa"),
        ("upload_system.py", "validar_dados", "SELECT de validação"),
        
        # banco_horas_system.py
        ("banco_horas_system.py", "obter_saldo", "SELECT com agregação"),
        ("banco_horas_system.py", "usar_horas", "UPDATE com validação"),
    ]


def print_migration_examples():
    """Imprime exemplos práticos."""
    print("\n" + "="*80)
    print("EXEMPLOS PRÁTICOS DE MIGRAÇÃO")
    print("="*80 + "\n")
    
    print("1️⃣  QUERY SIMPLES (SELECT)")
    print("-" * 80)
    print("ANTES:\n", PATTERN_OLD_CONN)
    print("\nDEPOIS:\n", PATTERN_NEW_CONN)
    
    print("\n\n2️⃣  UPDATE/INSERT")
    print("-" * 80)
    print("ANTES:\n", PATTERN_OLD_UPDATE)
    print("\nDEPOIS:\n", PATTERN_NEW_UPDATE)
    
    print("\n\n3️⃣  CURSOR COM PROCESSAMENTO")
    print("-" * 80)
    print("ANTES:\n", PATTERN_OLD_SAFE_CURSOR)
    print("\nDEPOIS:\n", PATTERN_NEW_SAFE_CURSOR)
    
    print("\n\n4️⃣  TRANSAÇÃO")
    print("-" * 80)
    print("ANTES:\n", PATTERN_OLD_TRANSACTION)
    print("\nDEPOIS:\n", PATTERN_NEW_TRANSACTION)


if __name__ == "__main__":
    print(get_migration_guide())
    print_migration_examples()
