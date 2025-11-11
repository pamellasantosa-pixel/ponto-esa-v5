-- Migration: Fix uploads table structure
-- Adiciona coluna caminho se não existir

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
