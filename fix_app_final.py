#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para aplicar correções no app_v5_final.py
Corrige: timezone, SQL_PLACEHOLDER, expander aninhado
"""

import re

# Ler arquivo
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("Tamanho original:", len(content))
print("Linhas originais:", content.count('\n'))

# 1. Adicionar SQL_PLACEHOLDER após imports
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
else:
    print("✗ SQL_PLACEHOLDER já existe ou padrão não encontrado")

# 2. Adicionar get_datetime_br após sys.path
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
else:
    print("✗ get_datetime_br() já existe ou padrão não encontrado")

# 3. Verificar se import pytz existe
if "import pytz" not in content:
    # Adicionar após import dotenv
    content = content.replace(
        "from dotenv import load_dotenv",
        "from dotenv import load_dotenv\nimport pytz  # Para gerenciar fusos horários"
    )
    print("✓ import pytz adicionado")
else:
    print("✗ import pytz já existe")

print("\nTamanho após mudanças:", len(content))
print("Linhas após mudanças:", content.count('\n'))

# Salvar com LF (Unix line endings)
with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("\n✅ Arquivo salvo com line endings LF!")

# Verificar se salvou corretamente
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    verification = f.read()
    
print("\n=== VERIFICAÇÃO ===")
print("SQL_PLACEHOLDER presente:", "SQL_PLACEHOLDER" in verification)
print("get_datetime_br presente:", "get_datetime_br" in verification)
print("import pytz presente:", "import pytz" in verification)
