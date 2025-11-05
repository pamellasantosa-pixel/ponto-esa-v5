#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script FINAL para aplicar correções CRÍTICAS (SEM mexer em expander)
"""

import re

# Ler arquivo
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Tamanho original: {len(content)} bytes")

# 1. Adicionar SQL_PLACEHOLDER
old_db_imports = """if USE_POSTGRESQL:
    import psycopg2
    from database_postgresql import get_connection, init_db
else:
    import sqlite3
    from database import init_db, get_connection"""

new_db_imports = """if USE_POSTGRESQL:
    import psycopg2
    from database_postgresql import get_connection, init_db
    # PostgreSQL usa %s como placeholder
    SQL_PLACEHOLDER = '%s'
else:
    import sqlite3
    from database import init_db, get_connection
    # SQLite usa ? como placeholder
    SQL_PLACEHOLDER = '?'"""

if old_db_imports in content and "SQL_PLACEHOLDER" not in content:
    content = content.replace(old_db_imports, new_db_imports)
    print("✓ SQL_PLACEHOLDER adicionado")

# 2. Adicionar get_datetime_br
old_path_section = """# Adicionar o diretório atual ao path para permitir importações
if os.path.dirname(__file__) not in sys.path:
    sys.path.insert(0, os.path.dirname(__file__))

# Importar sistemas desenvolvidos"""

new_path_section = """# Adicionar o diretório atual ao path para permitir importações
if os.path.dirname(__file__) not in sys.path:
    sys.path.insert(0, os.path.dirname(__file__))

# Configurar timezone do Brasil (Brasília)
TIMEZONE_BR = pytz.timezone('America/Sao_Paulo')

def get_datetime_br():
    \"\"\"Retorna datetime atual no fuso horário de Brasília\"\"\"
    return datetime.now(TIMEZONE_BR)

# Importar sistemas desenvolvidos"""

if old_path_section in content and "get_datetime_br" not in content:
    content = content.replace(old_path_section, new_path_section)
    print("✓ get_datetime_br() adicionado")

# 3. import pytz
if "import pytz" not in content:
    content = content.replace(
        "from dotenv import load_dotenv",
        "from dotenv import load_dotenv\nimport pytz  # Para gerenciar fusos horários"
    )
    print("✓ import pytz adicionado")

# 4. Substituir datetime.now() por get_datetime_br()
old_datetime_now = re.compile(r'datetime\.now\(\)(?!\s*\(TIMEZONE_BR\))')
matches = old_datetime_now.findall(content)
if matches:
    content = old_datetime_now.sub('get_datetime_br()', content)
    print(f"✓ datetime.now() -> get_datetime_br(): {len(matches)} ocorrências")

# 5. Corrigir verificar_login
old_ver = '''    cursor.execute(
        "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha_hash))'''
new_ver = '''    cursor.execute(
        f"SELECT tipo, nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER} AND senha = {SQL_PLACEHOLDER}", (usuario, senha_hash))'''
if old_ver in content:
    content = content.replace(old_ver, new_ver)
    print("✓ verificar_login() corrigida")

# 6. Atualizar docstring
old_doc = '''"""
Ponto ExSA v5.0 - Sistema de Controle de Ponto
Versão com Horas Extras, Banco de Horas, GPS Real e Melhorias
Desenvolvido por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos
"""'''

new_doc = '''"""
Ponto ExSA v5.0 - Sistema de Controle de Ponto
Versão com Horas Extras, Banco de Horas, GPS Real e Melhorias
Desenvolvido por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos
Última atualização: 24/10/2025 15:00 - Timezone Brasília, PostgreSQL/SQLite dinâmico
"""'''

if old_doc in content:
    content = content.replace(old_doc, new_doc)
    print("✓ Docstring atualizada")

print(f"\nTamanho final: {len(content)} bytes")

# Salvar
with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("✅ Arquivo salvo!")

# Verificar
import subprocess
import sys

result = subprocess.run([sys.executable, '-m', 'py_compile', 'ponto_esa_v5/app_v5_final.py'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("\n🎉 SINTAXE OK! 🎉")
else:
    print("\n❌ ERRO:")
    print(result.stderr)
