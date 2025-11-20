#!/usr/bin/env python3
"""
Script para DEBUG de login - verifica estado do banco de dados
"""

import sys
import os
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def hash_password(password):
    """Hash de senha usando SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def debug_database():
    """Debug do banco de dados"""
    print("=" * 70)
    print("DEBUG - BANCO DE DADOS")
    print("=" * 70)
    print()
    
    # Verificar qual banco está sendo usado
    use_postgresql = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'
    print(f"Tipo de banco: {'PostgreSQL' if use_postgresql else 'SQLite'}")
    print()
    
    if use_postgresql:
        print("Tentando conectar ao PostgreSQL...")
        try:
            from database_postgresql import get_connection, hash_password as db_hash
            conn = get_connection()
            cursor = conn.cursor()
            
            # Verificar se tabela usuarios existe
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'usuarios'
                )
            """)
            
            table_exists = cursor.fetchone()[0]
            print(f"  ✓ Tabela 'usuarios' existe: {table_exists}")
            
            if table_exists:
                # Contar usuários
                cursor.execute("SELECT COUNT(*) FROM usuarios")
                count = cursor.fetchone()[0]
                print(f"  ✓ Total de usuários: {count}")
                
                # Listar usuários
                cursor.execute("SELECT usuario, tipo FROM usuarios LIMIT 5")
                usuarios = cursor.fetchall()
                if usuarios:
                    print(f"\n  Usuários no banco:")
                    for user, tipo in usuarios:
                        print(f"    - {user} ({tipo})")
                else:
                    print(f"\n  ⚠️  Nenhum usuário encontrado!")
                
                # Tentar inserir usuários padrão
                print(f"\n  Inserindo usuários padrão...")
                usuarios_padrao = [
                    ("funcionario", db_hash("senha_func_123"), "funcionario", "Funcionário Padrão"),
                    ("gestor", db_hash("senha_gestor_123"), "gestor", "Gestor Principal"),
                ]
                
                for usuario, senha_hash, tipo, nome in usuarios_padrao:
                    try:
                        # Remover se existir
                        cursor.execute("DELETE FROM usuarios WHERE usuario = %s", (usuario,))
                        # Inserir
                        cursor.execute(
                            "INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) VALUES (%s, %s, %s, %s, 1)",
                            (usuario, senha_hash, tipo, nome)
                        )
                        print(f"    ✓ {usuario} - OK")
                    except Exception as e:
                        print(f"    ✗ {usuario} - ERROR: {e}")
                
                conn.commit()
                conn.close()
                
                print(f"\n✅ Banco de dados atualizado!")
                
        except Exception as e:
            print(f"❌ Erro ao conectar ao PostgreSQL: {e}")
            print()
            print("Verifique as variáveis de ambiente:")
            print(f"  - DATABASE_URL: {os.getenv('DATABASE_URL', 'não definida')}")
            print(f"  - DB_HOST: {os.getenv('DB_HOST', 'não definida')}")
            print(f"  - DB_NAME: {os.getenv('DB_NAME', 'não definida')}")
    else:
        print("Usando SQLite...")
        try:
            from database import get_connection, hash_password as db_hash, init_db
            
            # Inicializar banco se não existir
            print("  Inicializando banco de dados...")
            init_db()
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Contar usuários
            cursor.execute("SELECT COUNT(*) FROM usuarios")
            count = cursor.fetchone()[0]
            print(f"  ✓ Total de usuários: {count}")
            
            # Listar usuários
            cursor.execute("SELECT usuario, tipo FROM usuarios LIMIT 5")
            usuarios = cursor.fetchall()
            if usuarios:
                print(f"\n  Usuários no banco:")
                for user, tipo in usuarios:
                    print(f"    - {user} ({tipo})")
            else:
                print(f"\n  ⚠️  Nenhum usuário encontrado!")
                print(f"  Criando usuários padrão...")
                
                usuarios_padrao = [
                    ("funcionario", db_hash("senha_func_123"), "funcionario", "Funcionário Padrão"),
                    ("gestor", db_hash("senha_gestor_123"), "gestor", "Gestor Principal"),
                ]
                
                for usuario, senha_hash, tipo, nome in usuarios_padrao:
                    cursor.execute(
                        "INSERT INTO usuarios (usuario, senha, tipo, nome_completo) VALUES (?, ?, ?, ?)",
                        (usuario, senha_hash, tipo, nome)
                    )
                    print(f"    ✓ {usuario} - OK")
                
                conn.commit()
            
            conn.close()
            print(f"\n✅ Banco de dados OK!")
            
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    print()
    print("=" * 70)
    print("TESTE DE LOGIN")
    print("=" * 70)
    print()
    print("Credenciais padrão:")
    print("  Funcionário: funcionario / senha_func_123")
    print("  Gestor: gestor / senha_gestor_123")
    print()
    print("Tente fazer login na aplicação!")

if __name__ == '__main__':
    debug_database()
