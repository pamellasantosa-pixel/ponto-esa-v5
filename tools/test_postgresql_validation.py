"""
Teste de Validação PostgreSQL
Verifica persistência de notificações e compatibilidade do sistema
"""

import sys
import os
import time

# Adicionar path do módulo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ponto_esa_v5', 'ponto_esa_v5'))

def print_section(title):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_database_connection():
    """Testa conexão com o banco de dados"""
    print_section("🔌 TESTE 1: Conexão com Banco de Dados")
    
    try:
        from database_postgresql import get_connection, USE_POSTGRESQL  # type: ignore[import-not-found]
        
        print(f"Modo de banco: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Testar query básica
        if USE_POSTGRESQL:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print(f"✅ Conectado ao PostgreSQL")
            print(f"   └─ Versão: {version[:50]}...")
        else:
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            print(f"✅ Conectado ao SQLite")
            print(f"   └─ Versão: {version}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def test_notification_persistence():
    """Testa persistência de notificações no banco"""
    print_section("💾 TESTE 2: Persistência de Notificações")
    
    try:
        from notifications import notification_manager  # type: ignore[import-not-found]
        from database_postgresql import get_connection, USE_POSTGRESQL  # type: ignore[import-not-found]
        
        # Criar notificação de teste
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
            cursor.execute("""
                SELECT id, user_id, title, message, type, read, extra_data
                FROM notificacoes 
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (test_user,))
        else:
            cursor.execute("""
                SELECT id, user_id, title, message, type, read, extra_data
                FROM Notificacoes 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (test_user,))
        
        row = cursor.fetchone()
        
        if row:
            print(f"✅ Notificação persistida com sucesso!")
            print(f"   └─ ID: {row[0]}")
            print(f"   └─ User: {row[1]}")
            print(f"   └─ Title: {row[2]}")
            print(f"   └─ Message: {row[3][:50]}...")
            print(f"   └─ Type: {row[4]}")
            print(f"   └─ Read: {row[5]}")
            
            conn.close()
            return True
        else:
            print(f"❌ Notificação não encontrada no banco")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de persistência: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_repeating_notifications():
    """Testa notificações repetitivas"""
    print_section("🔁 TESTE 3: Notificações Repetitivas")
    
    try:
        from notifications import notification_manager  # type: ignore[import-not-found]
        
        test_user = "user_repeating_test"
        job_id = "test_repeating_postgres"
        
        payload = {
            "title": "🔔 Lembrete Repetitivo",
            "message": "Esta é uma notificação repetitiva de teste",
            "type": "reminder"
        }
        
        print(f"Iniciando job de notificações repetitivas: {job_id}")
        print(f"Intervalo: 3 segundos (para teste rápido)")
        
        # Contador para stop_condition
        count = [0]
        max_repeats = 3
        
        def stop_after_3():
            count[0] += 1
            return count[0] >= max_repeats
        
        notification_manager.start_repeating_notification(
            job_id=job_id,
            user_id=test_user,
            payload=payload,
            interval_seconds=3,
            stop_condition=stop_after_3
        )
        
        print(f"Job iniciado. Aguardando {max_repeats} notificações...")
        
        # Aguardar execuções
        time.sleep(12)
        
        # Verificar quantas notificações foram criadas
        from database_postgresql import get_connection, USE_POSTGRESQL  # type: ignore[import-not-found]
        
        conn = get_connection()
        cursor = conn.cursor()
        
        if USE_POSTGRESQL:
            cursor.execute("""
                SELECT COUNT(*) FROM notificacoes 
                WHERE user_id = %s AND title = %s
            """, (test_user, payload['title']))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM Notificacoes 
                WHERE user_id = ? AND title = ?
            """, (test_user, payload['title']))
        
        count_notifs = cursor.fetchone()[0]
        conn.close()
        
        print(f"✅ Notificações repetitivas criadas: {count_notifs}")
        
        if count_notifs >= max_repeats:
            print(f"   └─ Job funcionou corretamente!")
            return True
        else:
            print(f"   └─ ⚠️ Esperado {max_repeats}, obtido {count_notifs}")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de notificações repetitivas: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_table_schemas():
    """Verifica se todas as tabelas necessárias existem"""
    print_section("📊 TESTE 4: Schemas de Tabelas")
    
    try:
        from database_postgresql import get_connection, USE_POSTGRESQL  # type: ignore[import-not-found]
        
        conn = get_connection()
        cursor = conn.cursor()
        
        required_tables = [
            'usuarios',
            'registros_ponto',
            'solicitacoes_ajuste_ponto',
            'solicitacoes_horas_extras',
            'notificacoes',
            'atestados_horas'
        ]
        
        print(f"Verificando {len(required_tables)} tabelas essenciais...\n")
        
        all_exist = True
        
        for table in required_tables:
            if USE_POSTGRESQL:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    )
                """, (table,))
            else:
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, (table,))
            
            exists = cursor.fetchone()
            
            if (USE_POSTGRESQL and exists[0]) or (not USE_POSTGRESQL and exists):
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} - AUSENTE!")
                all_exist = False
        
        conn.close()
        
        if all_exist:
            print(f"\n✅ Todas as tabelas necessárias existem")
            return True
        else:
            print(f"\n❌ Algumas tabelas estão faltando")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar schemas: {e}")
        return False

def run_postgresql_validation():
    """Executa validação completa do PostgreSQL"""
    print_section("🔍 VALIDAÇÃO POSTGRESQL - Sistema Ponto ESA v5")
    
    print("Este teste valida:")
    print("  • Conexão com banco de dados (PostgreSQL ou SQLite)")
    print("  • Persistência de notificações")
    print("  • Notificações repetitivas")
    print("  • Integridade dos schemas")
    
    # Mostrar configuração atual
    try:
        from database_postgresql import USE_POSTGRESQL  # type: ignore[import-not-found]
        db_type = "PostgreSQL" if USE_POSTGRESQL else "SQLite"
        print(f"\n📌 Banco configurado: {db_type}")
        
        if USE_POSTGRESQL:
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                # Mascarar senha na URL
                masked_url = database_url.split('@')[1] if '@' in database_url else 'N/A'
                print(f"📌 DATABASE_URL: postgresql://***@{masked_url}")
            else:
                print(f"📌 DATABASE_URL: Usando variáveis separadas (DB_HOST, DB_NAME, etc.)")
    except:
        pass
    
    results = []
    
    # Executar testes
    results.append(("Conexão", test_database_connection()))
    results.append(("Persistência", test_notification_persistence()))
    results.append(("Repetitivas", test_repeating_notifications()))
    results.append(("Schemas", test_table_schemas()))
    
    # Resumo final
    print_section("📋 RESUMO DA VALIDAÇÃO")
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{'='*60}")
    print(f"Total: {passed}/{total} testes aprovados")
    print(f"{'='*60}")
    
    if passed == total:
        print("\n🎉 VALIDAÇÃO POSTGRESQL COMPLETA!")
        print("\n✅ Sistema pronto para produção com PostgreSQL")
        print("\n💡 Para usar em produção:")
        print("   1. Configure USE_POSTGRESQL=true")
        print("   2. Defina DATABASE_URL com credenciais reais")
        print("   3. Execute: python database_postgresql.py")
        print("   4. Inicie a aplicação normalmente")
    else:
        print("\n⚠️ VALIDAÇÃO INCOMPLETA")
        print(f"\n{total - passed} teste(s) falharam")
        print("\n💡 Verifique:")
        print("   • Credenciais do banco estão corretas?")
        print("   • Banco de dados está acessível?")
        print("   • Tabelas foram criadas (init_db)?")

if __name__ == "__main__":
    run_postgresql_validation()
