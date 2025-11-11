"""
Script para aplicar migration na tabela uploads
Corrige a estrutura da tabela para incluir coluna 'caminho'
"""

import os
from database_postgresql import get_connection

def apply_uploads_migration():
    """Aplica migration para corrigir tabela uploads"""
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        print("🔄 Verificando estrutura da tabela uploads...")
        
        # Verificar se a tabela existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'uploads'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("⚠️ Tabela uploads não existe. Será criada pelo UploadSystem.")
            return True
        
        # Verificar e adicionar coluna caminho
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'uploads' AND column_name = 'caminho'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("  ➕ Adicionando coluna 'caminho'...")
            cursor.execute("ALTER TABLE uploads ADD COLUMN caminho TEXT")
            
            # Se houver dados existentes, preencher caminho
            cursor.execute("SELECT COUNT(*) FROM uploads")
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"  📝 Preenchendo 'caminho' para {count} registros existentes...")
                cursor.execute("""
                    UPDATE uploads 
                    SET caminho = 'uploads/documentos/' || nome_arquivo 
                    WHERE caminho IS NULL
                """)
            
            cursor.execute("ALTER TABLE uploads ALTER COLUMN caminho SET NOT NULL")
            print("  ✅ Coluna 'caminho' adicionada")
        else:
            print("  ✓ Coluna 'caminho' já existe")
        
        # Verificar e adicionar coluna hash_arquivo
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'uploads' AND column_name = 'hash_arquivo'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("  ➕ Adicionando coluna 'hash_arquivo'...")
            cursor.execute("ALTER TABLE uploads ADD COLUMN hash_arquivo TEXT")
            print("  ✅ Coluna 'hash_arquivo' adicionada")
        else:
            print("  ✓ Coluna 'hash_arquivo' já existe")
        
        # Verificar e adicionar coluna status
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'uploads' AND column_name = 'status'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("  ➕ Adicionando coluna 'status'...")
            cursor.execute("ALTER TABLE uploads ADD COLUMN status TEXT DEFAULT 'ativo'")
            cursor.execute("UPDATE uploads SET status = 'ativo' WHERE status IS NULL")
            print("  ✅ Coluna 'status' adicionada")
        else:
            print("  ✓ Coluna 'status' já existe")
        
        # Criar índices
        print("  📊 Criando índices...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_usuario ON uploads(usuario)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_hash ON uploads(hash_arquivo)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploads_relacionado ON uploads(relacionado_a, relacionado_id)")
        print("  ✅ Índices criados")
    
        print("  ✅ Índices criados")
        
        conn.commit()
        
        print("\n✅ Migration aplicada com sucesso!")
        
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
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao aplicar migration: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

if __name__ == "__main__":
    apply_uploads_migration()
