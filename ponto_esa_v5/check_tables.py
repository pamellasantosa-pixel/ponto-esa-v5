#!/usr/bin/env python3
"""Script para verificar estrutura das tabelas no banco"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

# Verificar colunas da tabela horas_extras_ativas
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'horas_extras_ativas'
    ORDER BY ordinal_position
""")
print('Colunas de horas_extras_ativas:')
for row in cursor.fetchall():
    print(f'  - {row[0]}')

# Verificar colunas de solicitacoes_correcao_registro
cursor.execute("""
    SELECT column_name FROM information_schema.columns 
    WHERE table_name = 'solicitacoes_correcao_registro'
    ORDER BY ordinal_position
""")
print('\nColunas de solicitacoes_correcao_registro:')
for row in cursor.fetchall():
    print(f'  - {row[0]}')

conn.close()
