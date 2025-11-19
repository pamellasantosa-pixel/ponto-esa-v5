#!/usr/bin/env python3
"""
Teste dos novos módulos: error_handler, connection_manager, migration_helper
"""

import sys
import os

# Adicionar path para imports
sys.path.insert(0, os.path.dirname(__file__))


def test_error_handler():
    """Testa módulo error_handler."""
    print("\n" + "="*80)
    print("🧪 TESTANDO ERROR_HANDLER")
    print("="*80)
    
    try:
        from error_handler import (
            main_logger,
            error_logger,
            database_logger,
            security_logger,
            get_logger,
            log_error,
            log_database_operation,
            log_security_event,
            log_summary,
        )
        
        print("✅ Imports OK")
        
        # Testar logger básico
        logger = get_logger("test_module")
        logger.info("Teste de log básico")
        print("✅ Log básico funcionando")
        
        # Testar log_error
        try:
            raise ValueError("Erro de teste")
        except Exception as e:
            log_error("Erro de teste capturado", e, {"teste": True})
        print("✅ log_error funcionando")
        
        # Testar log_database_operation
        log_database_operation(
            operation="SELECT",
            query="SELECT * FROM usuarios",
            duration_ms=45.5,
            success=True
        )
        print("✅ log_database_operation funcionando")
        
        # Testar log_security_event
        log_security_event(
            event_type="LOGIN",
            usuario="joao",
            details="Login bem-sucedido"
        )
        print("✅ log_security_event funcionando")
        
        # Testar summary
        summary = log_summary()
        print(f"✅ log_summary: {summary}")
        
        print("\n✅ ERROR_HANDLER: TODOS OS TESTES PASSARAM")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR_HANDLER: ERRO - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_connection_manager():
    """Testa módulo connection_manager."""
    print("\n" + "="*80)
    print("🧪 TESTANDO CONNECTION_MANAGER")
    print("="*80)
    
    try:
        from connection_manager import (
            DatabaseConnectionPool,
            safe_database_connection,
            safe_cursor,
            execute_query,
            execute_update,
        )
        
        print("✅ Imports OK")
        
        # Testar DatabaseConnectionPool
        pool = DatabaseConnectionPool()
        print(f"✅ DatabaseConnectionPool criado: {pool}")
        print(f"   Conexões ativas: {pool.get_active_count()}")
        
        print("\n✅ CONNECTION_MANAGER: TESTES BÁSICOS PASSARAM")
        print("   (testes de conexão real requerem banco de dados)")
        return True
        
    except Exception as e:
        print(f"\n❌ CONNECTION_MANAGER: ERRO - {e}")
        import traceback
        traceback.print_exc()
        return False


def test_migration_helper():
    """Testa módulo migration_helper."""
    print("\n" + "="*80)
    print("🧪 TESTANDO MIGRATION_HELPER")
    print("="*80)
    
    try:
        from migration_helper import (
            get_migration_guide,
            get_functions_to_migrate,
            print_migration_examples,
            PATTERN_OLD_CONN,
            PATTERN_NEW_CONN,
        )
        
        print("✅ Imports OK")
        
        # Testar guide
        guide = get_migration_guide()
        assert "GUIA DE MIGRAÇÃO" in guide
        print("✅ get_migration_guide() funcionando")
        
        # Testar funções to migrate
        funcs = get_functions_to_migrate()
        assert len(funcs) > 0
        print(f"✅ get_functions_to_migrate(): {len(funcs)} funções identificadas")
        
        # Testar padrões
        assert "get_connection" in PATTERN_OLD_CONN
        assert "execute_query" in PATTERN_NEW_CONN
        print("✅ Padrões de migração definidos")
        
        print("\n✅ MIGRATION_HELPER: TODOS OS TESTES PASSARAM")
        return True
        
    except Exception as e:
        print(f"\n❌ MIGRATION_HELPER: ERRO - {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║              VALIDAÇÃO DOS NOVOS MÓDULOS DE REFATORAÇÃO                   ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    
    results = []
    
    # Executar testes
    results.append(("error_handler.py", test_error_handler()))
    results.append(("connection_manager.py", test_connection_manager()))
    results.append(("migration_helper.py", test_migration_helper()))
    
    # Resumo
    print("\n" + "="*80)
    print("📊 RESUMO DOS TESTES")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for _, result in results if result)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("\n✨ Próximos passos:")
        print("   1. Revisar migration_helper.py para entender os padrões")
        print("   2. Começar migração por app_v5_final.py (80 issues)")
        print("   3. Executar testes após cada migração")
        return 0
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os erros acima.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
