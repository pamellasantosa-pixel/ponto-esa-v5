"""
Script para substituir sqlite3.connect por get_connection() em todo o código
"""

import re

# Arquivo a ser modificado
arquivo = 'app_v5_final.py'

# Ler o conteúdo
with open(arquivo, 'r', encoding='utf-8') as f:
    conteudo = f.read()

# Padrões a substituir
padroes = [
    (r'sqlite3\.connect\("database/ponto_esa\.db"\)', 'get_connection()'),
    (r'sqlite3\.connect\(\'database/ponto_esa\.db\'\)', 'get_connection()'),
    (r'sqlite3\.connect\(\s*"database/ponto_esa\.db"\s*\)', 'get_connection()'),
]

# Aplicar substituições
for padrao, substituto in padroes:
    conteudo = re.sub(padrao, substituto, conteudo)

# Salvar
with open(arquivo, 'w', encoding='utf-8') as f:
    f.write(conteudo)

print(f"✅ Arquivo {arquivo} atualizado com sucesso!")
print("Todas as conexões SQLite foram substituídas por get_connection()")
