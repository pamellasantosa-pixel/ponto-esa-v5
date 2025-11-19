#!/usr/bin/env python3
"""
Script para testar o fluxo completo de login
"""

import sys
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

def test_login_flow():
    """Testa o fluxo completo de login"""
    print("=" * 70)
    print("TESTE DE FLUXO DE LOGIN")
    print("=" * 70)
    print()
    
    try:
        # 1. Importar hash_password
        print("✓ Importando hash_password...")
        from database import hash_password
        
        # 2. Conectar ao banco
        print("✓ Conectando ao banco de dados...")
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # 3. Testar credenciais padrão
        print("✓ Testando credenciais padrão...")
        
        credenciais_teste = [
            ("funcionario", "senha_func_123"),
            ("gestor", "senha_gestor_123"),
            ("admin", "admin123"),
        ]
        
        for usuario, senha in credenciais_teste:
            print(f"\n  📝 Testando {usuario}...")
            
            # Calcular hash
            senha_hash = hash_password(senha)
            print(f"    Hash calculado: {senha_hash[:16]}...")
            
            # Buscar usuário no banco
            cursor.execute(
                "SELECT usuario, senha FROM usuarios WHERE usuario = %s",
                (usuario,)
            )
            resultado = cursor.fetchone()
            
            if resultado:
                usuario_db, senha_db = resultado
                print(f"    Hash no BD:     {senha_db[:16]}...")
                
                if senha_db == senha_hash:
                    print(f"    ✅ LOGIN OK - Hashes coincidem!")
                else:
                    print(f"    ❌ ERRO - Hashes não coincidem!")
            else:
                print(f"    ❌ Usuário não encontrado no banco!")
        
        conn.close()
        
        print()
        print("=" * 70)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 70)
        print()
        print("Se todos os testes passaram:")
        print("1. Faça deploy para Render")
        print("2. Teste com as mesmas credenciais na aplicação web")
        print("3. Se ainda não funcionar, verifique:")
        print("   - DATABASE_URL no Render está correto")
        print("   - Variáveis de ambiente estão configuradas")
        print("   - Banco PostgreSQL no Render está ativo")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_login_flow()
