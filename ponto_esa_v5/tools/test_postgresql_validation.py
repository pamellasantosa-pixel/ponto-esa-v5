"""
Teste de Validação PostgreSQL
Verifica persistência de notificações e compatibilidade do sistema
"""

import pytest
import time
from datetime import datetime, timedelta
import os
import sys

# Adiciona os caminhos necessários para encontrar os módulos da aplicação
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PACKAGE_DIR = os.path.join(ROOT_DIR, 'ponto_esa_v5', 'ponto_esa_v5')
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

# Agora as importações devem funcionar
try:
    from notifications import notification_manager  # type: ignore[import-not-found]
except ImportError:
    from ponto_esa_v5.notifications import notification_manager  # type: ignore[import-not-found]

try:
    from database_postgresql import get_connection, USE_POSTGRESQL  # type: ignore[import-not-found]
except ImportError:
    from ponto_esa_v5.database_postgresql import get_connection, USE_POSTGRESQL  # type: ignore[import-not-found]

try:
    from database import SQL_PLACEHOLDER  # type: ignore[import-not-found]
except ImportError:
    from ponto_esa_v5.database import SQL_PLACEHOLDER  # type: ignore[import-not-found]

def print_section(title):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

    conn = None
    cursor = None

    try:
        print(f"Modo de banco: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")

        conn = get_connection()
        assert conn is not None, "A conexão com o banco de dados falhou"
        cursor = conn.cursor()

        if USE_POSTGRESQL:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print("✅ Conectado ao PostgreSQL")
            print(f"   └─ Versão: {version[:50]}...")
        else:
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            print("✅ Conectado ao SQLite")
            print(f"   └─ Versão: {version}")

    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        assert False, f"Erro na conexão: {e}"
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

def test_notification_persistence():
    """Testa persistência de notificações no banco"""
    conn = None
    cursor = None

    try:
        test_user = "user_postgres_test"
        test_payload = {
            "title": "🧪 Teste PostgreSQL",
            "message": "Testando persistência de notificações no banco de dados",
            "type": "test",
            "priority": "high",
            "timestamp_test": time.time()
        }

        print(f"Criando notificação de teste para usuário: {test_user}")
        notification_manager.add_notification(test_user, test_payload)

        # Aguardar um pouco para garantir persistência
        time.sleep(1)

        # Verificar no banco de dados
        conn = get_connection()
        cursor = conn.cursor()

        if USE_POSTGRESQL:
            cursor.execute(
                """
                    SELECT id, user_id, title, message, type, read, extra_data
                    FROM notificacoes 
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 1
                """,
                (test_user,),
            )
        else:
            cursor.execute(
                """
                    SELECT id, user_id, title, message, type, read, extra_data
                    FROM Notificacoes 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """,
                (test_user,),
            )

        row = cursor.fetchone()

        assert row is not None, "A notificação não foi encontrada no banco de dados"

        print("✅ Notificação persistida com sucesso!")
        print(f"   └─ ID: {row[0]}")
        print(f"   └─ User: {row[1]}")
        print(f"   └─ Title: {row[2]}")
        print(f"   └─ Message: {row[3][:50]}...")
        print(f"   └─ Type: {row[4]}")
        print(f"   └─ Read: {row[5]}")

    except Exception as e:
        print(f"❌ Erro no teste de persistência: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Erro no teste de persistência: {e}"
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

def test_repeating_notifications():
    """Testa notificações repetitivas"""
    print_section("🔁 TESTE 3: Notificações Repetitivas")

    conn = None
    cursor = None

    try:
        test_user = "user_repeating_test"
        job_id = "test_repeating_postgres"

        payload = {
            "title": "🔔 Lembrete Repetitivo",
            "message": "Esta é uma notificação repetitiva de teste",
            "type": "reminder",
        }

        print(f"Iniciando job de notificações repetitivas: {job_id}")
        print("Intervalo: 3 segundos (para teste rápido)")

        count = [0]
        max_repeats = 2

        def stop_after_max():
            count[0] += 1
            return count[0] >= max_repeats

        notification_manager.start_repeating_notification(
            job_id=job_id,
            user_id=test_user,
            payload=payload,
            interval_seconds=3,
            stop_condition=stop_after_max,
        )

        print(f"Job iniciado. Aguardando {max_repeats} notificações...")

        time.sleep(30)

        conn = get_connection()
        cursor = conn.cursor()

        if USE_POSTGRESQL:
            cursor.execute(
                """
                    SELECT COUNT(*) FROM notificacoes 
                    WHERE user_id = %s AND title = %s
                """,
                (test_user, payload["title"]),
            )
        else:
            cursor.execute(
                """
                    SELECT COUNT(*) FROM Notificacoes 
                    WHERE user_id = ? AND title = ?
                """,
                (test_user, payload["title"]),
            )

        notifications_created = cursor.fetchone()[0]
        assert notifications_created >= max_repeats, (
            f"Esperado pelo menos {max_repeats} notificações, mas {notifications_created} foram criadas"
        )

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
        notification_manager.stop_all_jobs()
        time.sleep(1)
        print("Todos os jobs de notificação foram parados.")

def test_table_schemas():
    """Verifica se todas as tabelas necessárias existem"""
    print_section("📊 TESTE 4: Schemas de Tabelas")
    conn = None
    cursor = None

    try:
        from database_postgresql import get_connection, USE_POSTGRESQL  # type: ignore[import-not-found]
        
        conn = get_connection()
        cursor = conn.cursor()

        required_tables_pg = [
            'usuarios', 'registros_ponto', 'solicitacoes_ajuste_ponto',
            'solicitacoes_horas_extras', 'notificacoes', 'atestados_horas'
        ]
        required_tables_sqlite = [
            'usuarios', 'registros_ponto', 'solicitacoes_ajuste_ponto',
            'solicitacoes_horas_extras', 'Notificacoes', 'atestados_horas'
        ]
        required_tables = required_tables_pg if USE_POSTGRESQL else required_tables_sqlite

        print(f"Verificando {len(required_tables)} tabelas essenciais...\n")

        all_exist = True

        for table in required_tables:
            if USE_POSTGRESQL:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """,
                    (table,),
                )
            else:
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """,
                    (table,),
                )

            exists = cursor.fetchone()

            if (USE_POSTGRESQL and exists[0]) or (not USE_POSTGRESQL and exists):
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - AUSENTE!")
                all_exist = False

        assert all_exist, "Algumas tabelas essenciais estão faltando no banco de dados"
        print("\n✅ Todas as tabelas necessárias existem")

    except Exception as e:
        print(f"❌ Erro ao verificar schemas: {e}")
        assert False, f"Erro ao verificar schemas: {e}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
