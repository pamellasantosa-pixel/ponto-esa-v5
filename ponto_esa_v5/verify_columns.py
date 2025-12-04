"""Verificar colunas do banco de dados"""
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_4dpyuhtMZJL7@ep-spring-tree-ac2y3okx-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

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
