#!/usr/bin/env python3
"""Script para remover NOT NULL da coluna data_hora_corrigida"""
import psycopg2

DB_URL = 'postgresql://neondb_owner:npg_4dpyuhtMZJL7@ep-spring-tree-ac2y3okx-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require'

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Verificar estado atual
cur.execute("""
    SELECT column_name, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'solicitacoes_correcao_registro' 
    AND column_name IN ('data_hora_corrigida', 'data_hora_nova')
""")
print("Estado atual das colunas:")
for row in cur.fetchall():
    print(f"  {row[0]}: nullable={row[1]}")

# Remover NOT NULL
print("\nRemovendo NOT NULL de data_hora_corrigida...")
cur.execute("ALTER TABLE solicitacoes_correcao_registro ALTER COLUMN data_hora_corrigida DROP NOT NULL")
conn.commit()

# Verificar novamente
cur.execute("""
    SELECT column_name, is_nullable 
    FROM information_schema.columns 
    WHERE table_name = 'solicitacoes_correcao_registro' 
    AND column_name IN ('data_hora_corrigida', 'data_hora_nova')
""")
print("\nEstado após alteração:")
for row in cur.fetchall():
    print(f"  {row[0]}: nullable={row[1]}")

conn.close()
print("\n✅ Concluído!")
