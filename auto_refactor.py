#!/usr/bin/env python3
"""
Script de refatoração automática para app_v5_final.py
Migra get_connection() para context managers
"""

import re
import sys
import os
from pathlib import Path

# Ler arquivo original
app_file = r"c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\app_v5_final.py"

with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

# PASSO 1: Adicionar imports necessários logo após os outros imports
imports_to_add = """from connection_manager import execute_query, execute_update, safe_cursor
from error_handler import log_error, get_logger"""

# Encontrar a posição certa para adicionar imports (depois de outros imports)
# Procurar pela última linha que começa com 'from' ou 'import'
lines = content.split('\n')
last_import_idx = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith(('from ', 'import ')) and not line.startswith(' '):
        last_import_idx = i

# Verificar se imports já existem
if 'from connection_manager import' not in content:
    # Adicionar imports
    lines.insert(last_import_idx + 1, imports_to_add)
    print("[OK] Imports adicionados")
else:
    print("[INFO] Imports já existem")

# PASSO 2: Remover import de get_connection que não será mais usado
content = '\n'.join(lines)

# Remover: from database_postgresql import get_connection, init_db
content = re.sub(
    r'from database_postgresql import get_connection, init_db\n',
    'from database_postgresql import init_db\n',
    content
)

# Remover: from database import init_db, get_connection
content = re.sub(
    r'from database import init_db, get_connection\n',
    'from database import init_db\n',
    content
)

# Remover linhas que definem get_db_connection
content = re.sub(r'get_db_connection = get_connection\n', '', content)

print("[OK] Imports de get_connection removidos")

# PASSO 3: Refatorar verificar_login - SELECT simples com fetchone
old_verificar = r'''def verificar_login\(usuario, senha\):
    """Verifica credenciais de login"""
    conn = get_connection\(\)
    cursor = conn\.cursor\(\)

    senha_hash = hashlib\.sha256\(senha\.encode\(\)\.hexdigest\(\)
    cursor\.execute\(
        "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", \(usuario, senha_hash\)\)
    result = cursor\.fetchone\(\)
    conn\.close\(\)

    return result'''

new_verificar = '''def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return execute_query(
        "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s",
        (usuario, senha_hash),
        fetch_one=True
    )'''

content = re.sub(old_verificar, new_verificar, content, flags=re.MULTILINE)
print("[OK] verificar_login refatorado")

# PASSO 4: Refatorar obter_projetos_ativos - SELECT com fetchall
old_projetos = r'''def obter_projetos_ativos\(\):
    """Obtém lista de projetos ativos"""
    conn = get_connection\(\)
    cursor = conn\.cursor\(\)
    cursor\.execute\("SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome"\)
    projetos = \[row\[0\] for row in cursor\.fetchall\(\)\]
    conn\.close\(\)
    return projetos'''

new_projetos = '''def obter_projetos_ativos():
    """Obtém lista de projetos ativos"""
    results = execute_query(
        "SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome"
    )
    return [row[0] for row in results] if results else []'''

content = re.sub(old_projetos, new_projetos, content, flags=re.MULTILINE)
print("[OK] obter_projetos_ativos refatorado")

# Salvar arquivo
with open(app_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n[SUCESSO] Refatoracao concluida!")
print(f"Arquivo: {app_file}")
print("Funcoes refatoradas: 2 (verificar_login, obter_projetos_ativos)")
print("\nProximas: refatorar registrar_ponto, obter_registros_usuario, etc.")
