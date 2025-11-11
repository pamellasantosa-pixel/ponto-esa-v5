"""
Script para aplicar migration na tabela uploads
Corrige a estrutura da tabela para incluir coluna 'caminho'
"""

import os
from database_postgresql import get_connection

def apply_uploads_migration():
    """Aplica migration para corrigir tabela uploads"""
    
    migration_sql = """
    -- Verificar e adicionar coluna caminho
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'uploads' AND column_name = 'caminho'
        ) THEN
            ALTER TABLE uploads ADD COLUMN caminho TEXT;
            
            -- Se houver dados existentes sem caminho, criar um caminho baseado no nome_arquivo
            UPDATE uploads 
            SET caminho = 'uploads/documentos/' || nome_arquivo 
            WHERE caminho IS NULL;
            
            -- Tornar a coluna NOT NULL após preencher
            ALTER TABLE uploads ALTER COLUMN caminho SET NOT NULL;
        END IF;
    END $$;

    -- Verificar e adicionar coluna hash_arquivo se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'uploads' AND column_name = 'hash_arquivo'
        ) THEN
            ALTER TABLE uploads ADD COLUMN hash_arquivo TEXT;
        END IF;
    END $$;

    -- Verificar e adicionar coluna status se não existir
    DO $$ 
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'uploads' AND column_name = 'status'
        ) THEN
            ALTER TABLE uploads ADD COLUMN status TEXT DEFAULT 'ativo';
            
            -- Atualizar registros existentes
            UPDATE uploads SET status = 'ativo' WHERE status IS NULL;
        END IF;
    END $$;

    -- Criar índices para melhor performance
    CREATE INDEX IF NOT EXISTS idx_uploads_usuario ON uploads(usuario);
    CREATE INDEX IF NOT EXISTS idx_uploads_hash ON uploads(hash_arquivo);
    CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);
    CREATE INDEX IF NOT EXISTS idx_uploads_relacionado ON uploads(relacionado_a, relacionado_id);
    """
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        print("🔄 Aplicando migration na tabela uploads...")
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration aplicada com sucesso!")
        
        # Verificar estrutura final
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'uploads'
            ORDER BY ordinal_position
        """)
        
        colunas = cursor.fetchall()
        print("\n📋 Estrutura final da tabela uploads:")
        for col in colunas:
            print(f"  - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar migration: {e}")
        return False

if __name__ == "__main__":
    apply_uploads_migration()
