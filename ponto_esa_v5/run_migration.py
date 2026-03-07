#!/usr/bin/env python3
"""
Script para migrar a tabela solicitacoes_correcao_registro
Adiciona as colunas que faltam para compatibilidade com app_v5_final.py
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def get_database_url():
    """Obter URL do banco de dados"""
    return os.environ.get('DATABASE_URL')

def run_migration():
    """Executar migração da tabela"""
    print("🔄 Iniciando migração da tabela solicitacoes_correcao_registro...")
    
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor()
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'solicitacoes_correcao_registro'
            );
        """)
        
        if not cursor.fetchone()[0]:
            print("⚠️ Tabela solicitacoes_correcao_registro não existe. Criando...")
            cursor.execute("""
                CREATE TABLE solicitacoes_correcao_registro (
                    id SERIAL PRIMARY KEY,
                    usuario TEXT NOT NULL,
                    registro_id INTEGER NOT NULL,
                    data_hora_original TIMESTAMP NOT NULL,
                    data_hora_nova TIMESTAMP NOT NULL,
                    tipo_original TEXT,
                    tipo_novo TEXT,
                    modalidade_original TEXT,
                    modalidade_nova TEXT,
                    projeto_original TEXT,
                    projeto_novo TEXT,
                    justificativa TEXT NOT NULL,
                    status TEXT DEFAULT 'pendente',
                    data_solicitacao TIMESTAMP DEFAULT NOW(),
                    aprovado_por TEXT,
                    data_aprovacao TIMESTAMP,
                    observacoes TEXT
                )
            """)
            conn.commit()
            print("✅ Tabela criada com sucesso!")
            return True
        
        # Listar colunas atuais
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'solicitacoes_correcao_registro'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"📋 Colunas existentes: {existing_columns}")
        
        # Colunas a adicionar/renomear
        migrations = []
        
        # 1. Renomear data_hora_corrigida para data_hora_nova se necessário
        if 'data_hora_corrigida' in existing_columns and 'data_hora_nova' not in existing_columns:
            migrations.append(("RENAME", "data_hora_corrigida", "data_hora_nova"))
        
        # 2. Adicionar colunas que faltam
        required_columns = [
            ('tipo_original', 'TEXT'),
            ('tipo_novo', 'TEXT'),
            ('modalidade_original', 'TEXT'),
            ('modalidade_nova', 'TEXT'),
            ('projeto_original', 'TEXT'),
            ('projeto_novo', 'TEXT'),
            ('data_hora_nova', 'TIMESTAMP')  # Se não existir data_hora_corrigida
        ]
        
        for col_name, col_type in required_columns:
            if col_name not in existing_columns:
                # Caso especial: data_hora_nova deve ser NOT NULL se for nova
                if col_name == 'data_hora_nova' and 'data_hora_corrigida' not in existing_columns:
                    migrations.append(("ADD", col_name, f"{col_type} NOT NULL DEFAULT NOW()"))
                else:
                    migrations.append(("ADD", col_name, col_type))
        
        # Executar migrações
        if not migrations:
            print("✅ Nenhuma migração necessária. Tabela já está atualizada!")
            return True
        
        for migration in migrations:
            try:
                if migration[0] == "RENAME":
                    sql = f"ALTER TABLE solicitacoes_correcao_registro RENAME COLUMN {migration[1]} TO {migration[2]}"
                    print(f"🔄 Renomeando coluna {migration[1]} para {migration[2]}...")
                elif migration[0] == "ADD":
                    sql = f"ALTER TABLE solicitacoes_correcao_registro ADD COLUMN IF NOT EXISTS {migration[1]} {migration[2]}"
                    print(f"➕ Adicionando coluna {migration[1]}...")
                
                cursor.execute(sql)
                conn.commit()
                print(f"   ✅ Concluído!")
            except psycopg2.Error as e:
                print(f"   ⚠️ Erro (ignorado): {e}")
                conn.rollback()
        
        # Verificar estrutura final
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'solicitacoes_correcao_registro'
            ORDER BY ordinal_position
        """)
        final_columns = cursor.fetchall()
        
        print("\n📋 Estrutura final da tabela:")
        for col in final_columns:
            print(f"   - {col[0]}: {col[1]}")
        
        conn.close()
        print("\n✅ Migração concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro durante migração: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
