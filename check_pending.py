"""Verificar estrutura de tabelas no banco"""
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_4dpyuhtMZJL7@ep-spring-tree-ac2y3okx-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

tables_to_check = [
    'atestado_horas',
    'atestados_horas', 
    'solicitacoes_correcao_registro',
    'solicitacoes_horas_extras',
    'horas_extras_ativas'
]

for table in tables_to_check:
    print(f"\n{'=' * 60}")
    print(f"TABELA: {table}")
    print('=' * 60)
    
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    
    cols = cur.fetchall()
    if cols:
        for col in cols:
            print(f"  {col[0]}: {col[1]}, nullable={col[2]}")
    else:
        print("  [TABELA NÃO EXISTE]")

# Verificar contagem de registros pendentes
print(f"\n{'=' * 60}")
print("CONTAGEM DE PENDÊNCIAS:")
print('=' * 60)

try:
    cur.execute("SELECT COUNT(*) FROM atestado_horas WHERE status = 'pendente'")
    print(f"  atestado_horas pendentes: {cur.fetchone()[0]}")
except:
    print("  atestado_horas: erro ou tabela não existe")

try:
    cur.execute("SELECT COUNT(*) FROM solicitacoes_correcao_registro WHERE status = 'pendente'")
    print(f"  solicitacoes_correcao_registro pendentes: {cur.fetchone()[0]}")
except:
    print("  solicitacoes_correcao_registro: erro ou tabela não existe")

try:
    cur.execute("SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente'")
    print(f"  solicitacoes_horas_extras pendentes: {cur.fetchone()[0]}")
except:
    print("  solicitacoes_horas_extras: erro ou tabela não existe")

try:
    cur.execute("SELECT COUNT(*) FROM horas_extras_ativas WHERE status = 'pendente'")
    print(f"  horas_extras_ativas pendentes: {cur.fetchone()[0]}")
except:
    print("  horas_extras_ativas: erro ou tabela não existe")

conn.close()
print("\n✅ Verificação concluída!")
