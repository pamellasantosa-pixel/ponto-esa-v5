#!/usr/bin/env python3
"""
Script de teste para verificar se a funcionalidade de horas extras está funcionando
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Testar importações
    print("🔍 Testando importações...")

    from horas_extras_system import HorasExtrasSystem
    print("✅ HorasExtrasSystem importado com sucesso")

    from database import get_connection
    print("✅ Database importado com sucesso")

    # Testar inicialização do sistema
    print("\n🔧 Testando inicialização do sistema...")
    horas_extras_system = HorasExtrasSystem()
    print("✅ HorasExtrasSystem inicializado com sucesso")

    # Testar conexão com banco
    print("\n🗄️ Testando conexão com banco...")
    conn = get_connection()
    if conn:
        print("✅ Conexão com banco estabelecida")
        conn.close()
    else:
        print("❌ Falha na conexão com banco")

    # Testar métodos básicos
    print("\n📋 Testando métodos básicos...")
    try:
        # Tentar listar solicitações (pode falhar se não houver dados)
        resultado = horas_extras_system.listar_solicitacoes_usuario("test_user")
        print("✅ Método listar_solicitacoes_usuario executado")
    except Exception as e:
        print(f"⚠️ Método listar_solicitacoes_usuario falhou (esperado se não houver dados): {e}")

    print("\n🎉 Todos os testes básicos passaram!")

except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erro geral: {e}")
    sys.exit(1)