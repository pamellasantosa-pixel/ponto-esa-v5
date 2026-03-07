#!/usr/bin/env python3
"""Script para migrar tabela horas_extras_ativas - adicionar colunas faltantes"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

print("🔄 Migrando tabela horas_extras_ativas...")

# Adicionar coluna 'aprovador' se não existir (alias para aprovado_por ou nova coluna)
migrations = [
    ("aprovador", "TEXT"),
    ("data_inicio", "TIMESTAMP"),
    ("tempo_decorrido_minutos", "INTEGER DEFAULT 0"),
    ("data_criacao", "TIMESTAMP DEFAULT NOW()"),
]

for col_name, col_type in migrations:
    try:
        cursor.execute(f"ALTER TABLE horas_extras_ativas ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
        conn.commit()
        print(f"  ✅ Coluna {col_name} adicionada/verificada")
    except Exception as e:
        print(f"  ⚠️ Erro em {col_name}: {e}")
        conn.rollback()

# Copiar dados de aprovado_por para aprovador (se aprovador estiver vazio)
try:
    cursor.execute("""
        UPDATE horas_extras_ativas 
        SET aprovador = aprovado_por 
        WHERE aprovador IS NULL AND aprovado_por IS NOT NULL
    """)
    conn.commit()
    print("  ✅ Dados copiados de aprovado_por para aprovador")
except Exception as e:
    print(f"  ⚠️ Erro ao copiar dados: {e}")
    conn.rollback()

# Copiar dados de data_solicitacao para data_inicio (se data_inicio estiver vazio)
try:
    cursor.execute("""
        UPDATE horas_extras_ativas 
        SET data_inicio = data_solicitacao 
        WHERE data_inicio IS NULL AND data_solicitacao IS NOT NULL
    """)
    conn.commit()
    print("  ✅ Dados copiados de data_solicitacao para data_inicio")
except Exception as e:
    print(f"  ⚠️ Erro ao copiar dados: {e}")
    conn.rollback()

# Verificar estrutura final
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'horas_extras_ativas'
    ORDER BY ordinal_position
""")
print("\n📋 Estrutura final de horas_extras_ativas:")
for row in cursor.fetchall():
    print(f"  - {row[0]}: {row[1]}")

conn.close()
print("\n✅ Migração concluída!")
