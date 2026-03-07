"""Verificar colunas do banco de dados"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("=" * 60)
print("COLUNAS DA TABELA solicitacoes_correcao_registro:")
print("=" * 60)

cur.execute("""
    SELECT column_name, is_nullable, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'solicitacoes_correcao_registro' 
    ORDER BY ordinal_position
""")

for row in cur.fetchall():
    print(f"  {row[0]}: {row[2]}, nullable={row[1]}")

print("\n" + "=" * 60)
print("COLUNAS DA TABELA horas_extras_ativas:")
print("=" * 60)

cur.execute("""
    SELECT column_name, is_nullable, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'horas_extras_ativas' 
    ORDER BY ordinal_position
""")

for row in cur.fetchall():
    print(f"  {row[0]}: {row[2]}, nullable={row[1]}")

conn.close()
print("\n✅ Verificação concluída!")
