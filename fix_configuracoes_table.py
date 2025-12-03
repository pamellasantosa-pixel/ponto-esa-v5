"""Script para adicionar coluna descricao na tabela configuracoes"""
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_4dpyuhtMZJL7@ep-spring-tree-ac2y3okx-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("=" * 60)
print("Verificando tabela configuracoes...")
print("=" * 60)

# Verificar colunas existentes
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'configuracoes'
""")
existing_columns = [row[0] for row in cur.fetchall()]
print(f"Colunas existentes: {existing_columns}")

# Adicionar coluna descricao se não existir
if 'descricao' not in existing_columns:
    print("\n➡️ Adicionando coluna 'descricao'...")
    cur.execute("ALTER TABLE configuracoes ADD COLUMN descricao TEXT")
    conn.commit()
    print("✅ Coluna 'descricao' adicionada!")
else:
    print("✅ Coluna 'descricao' já existe")

# Verificar resultado
cur.execute("""
    SELECT column_name, is_nullable, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'configuracoes'
    ORDER BY ordinal_position
""")
print("\n" + "=" * 60)
print("COLUNAS DA TABELA configuracoes:")
print("=" * 60)
for row in cur.fetchall():
    print(f"  {row[0]}: {row[2]}, nullable={row[1]}")

conn.close()
print("\n✅ Correção concluída!")
