#!/usr/bin/env python3
"""Debug completo de login"""

import hashlib
from database import get_connection

def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    conn = get_connection()
    cursor = conn.cursor()
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    print(f'Testando login:')
    print(f'  Usuario: {usuario}')
    print(f'  Senha hash: {senha_hash[:16]}...')
    
    cursor.execute(
        'SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s', 
        (usuario, senha_hash)
    )
    result = cursor.fetchone()
    conn.close()
    return result

# Testar
print("="*70)
print("TESTE DE LOGIN COMPLETO")
print("="*70)
print()

resultado = verificar_login('funcionario', 'senha_func_123')
if resultado:
    print(f'✅ LOGIN OK! Tipo: {resultado[0]}, Nome: {resultado[1]}')
else:
    print(f'❌ Login falhou')
    
    # Debug: Verificar o hash no banco
    print()
    print("Debugando...")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT usuario, senha FROM usuarios WHERE usuario = %s', ('funcionario',))
    user_db = cursor.fetchone()
    conn.close()
    
    if user_db:
        hash_esperado = hashlib.sha256(b"senha_func_123").hexdigest()
        print(f'  Usuario no BD: {user_db[0]}')
        print(f'  Hash no BD: {user_db[1]}')
        print(f'  Hash esperado: {hash_esperado}')
        print(f'  Coincidem? {user_db[1] == hash_esperado}')
    else:
        print('  Usuário não encontrado no banco!')
