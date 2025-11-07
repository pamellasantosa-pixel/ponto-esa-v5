"""Gera um banco de demonstração temporário (database/ponto_esa_demo.db) com dados de exemplo.

Uso:
    python tools/demo_setup.py
"""
import hashlib
import sqlite3
import os
from datetime import datetime

DB_PATH = 'database/ponto_esa_demo.db'

# Recriar demo DB
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# Usar a função init_db mas precisaríamos adaptá-la para aceitar outro caminho;
# Como alternativa, copiamos a lógica mínima aqui para criar o DB demo.
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute('''
    CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        tipo TEXT NOT NULL,
        nome_completo TEXT,
        ativo INTEGER DEFAULT 1,
        jornada_inicio_previsto TIME DEFAULT '08:00',
        jornada_fim_previsto TIME DEFAULT '17:00'
    )
''')

c.execute('''
    CREATE TABLE registros_ponto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL,
        data_hora TIMESTAMP NOT NULL,
        tipo TEXT NOT NULL
    )
''')

# inserir usuário de exemplo e registros de um dia
pw = 'senha_func_123'
pw_hash = hashlib.sha256(pw.encode()).hexdigest()

c.execute("INSERT INTO usuarios (usuario, senha, tipo, nome_completo) VALUES (?, ?, ?, ?)",
          ('demo_user', pw_hash, 'funcionario', 'Usuário Demo'))

# inserir registros de um dia
now = datetime(2025, 10, 13, 8, 0, 0)
now2 = datetime(2025, 10, 13, 17, 0, 0)

c.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
          ('demo_user', now.strftime('%Y-%m-%d %H:%M:%S'), 'Início'))
c.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
          ('demo_user', now2.strftime('%Y-%m-%d %H:%M:%S'), 'Fim'))

conn.commit()
conn.close()

print('Banco de demonstração criado em', DB_PATH)
print('Usuário: demo_user | Senha: senha_func_123')

print('\nPara rodar a demo com esse DB, exporte a variável de ambiente ou copie o arquivo para database/ponto_esa.db')
print("Exemplo: copy database\\ponto_esa_demo.db database\\ponto_esa.db")
