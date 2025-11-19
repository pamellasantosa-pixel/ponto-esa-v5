#!/usr/bin/env python3
"""
Script para gerenciar usuários e credenciais do sistema
"""

import hashlib
import sys
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

def hash_password(password):
    """Hash de senha usando SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def test_login_credentials():
    """Testa credenciais de login"""
    print("=" * 70)
    print("TESTE DE CREDENCIAIS DE LOGIN")
    print("=" * 70)
    print()
    
    credenciais = {
        'funcionario': 'senha_func_123',
        'gestor': 'senha_gestor_123',
    }
    
    print("Credenciais padrão do sistema:")
    print()
    
    for usuario, senha in credenciais.items():
        senha_hash = hash_password(senha)
        print(f"Usuário: {usuario}")
        print(f"Senha: {senha}")
        print(f"Hash (SHA256): {senha_hash}")
        print(f"Comando SQL para criar/atualizar:")
        print(f"  INSERT INTO usuarios (usuario, senha, tipo) VALUES ('{usuario}', '{senha_hash}', '{usuario}');")
        print()

def reset_passwords():
    """Reset de senhas no banco de dados"""
    print("=" * 70)
    print("SCRIPT DE RESET DE SENHAS")
    print("=" * 70)
    print()
    
    try:
        from database_postgresql import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Criar usuários com senhas padrão
        usuarios_padrao = [
            ("funcionario", hash_password("senha_func_123"), "funcionario", "Funcionário Demo"),
            ("gestor", hash_password("senha_gestor_123"), "gestor", "Gestor Demo"),
            ("admin", hash_password("admin123"), "admin", "Administrador"),
        ]
        
        for usuario, senha_hash, tipo, nome in usuarios_padrao:
            try:
                cursor.execute(
                    "DELETE FROM usuarios WHERE usuario = %s",
                    (usuario,)
                )
                cursor.execute(
                    "INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) VALUES (%s, %s, %s, %s, 1)",
                    (usuario, senha_hash, tipo, nome)
                )
                print(f"✓ {usuario} - Criado/Atualizado com sucesso")
            except Exception as e:
                print(f"✗ {usuario} - Erro: {e}")
        
        conn.commit()
        conn.close()
        print()
        print("Credenciais resetadas com sucesso!")
        
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        print()
        print("SQL alternativo (executar manualmente):")
        for usuario, senha_hash, tipo, nome in usuarios_padrao:
            print(f"DELETE FROM usuarios WHERE usuario = '{usuario}';")
            print(f"INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo) VALUES ('{usuario}', '{senha_hash}', '{tipo}', '{nome}', 1);")
            print()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'reset':
        reset_passwords()
    else:
        test_login_credentials()
        print()
        print("INSTRUÇÕES DE USO:")
        print()
        print("1. Se estiver em desenvolvimento local:")
        print("   python manage_users.py reset")
        print()
        print("2. Se estiver em Render (sem acesso direto ao BD):")
        print("   - Use as credenciais mostradas acima")
        print("   - Funcionário: funcionario / senha_func_123")
        print("   - Gestor: gestor / senha_gestor_123")
        print()
        print("3. Se as credenciais não funcionarem:")
        print("   - Verifique se a tabela 'usuarios' existe")
        print("   - Execute o SQL acima manualmente no admin BD")
        print("   - Reinicie a aplicação")

if __name__ == '__main__':
    main()
