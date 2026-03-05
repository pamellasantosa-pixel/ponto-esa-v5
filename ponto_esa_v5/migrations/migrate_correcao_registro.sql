-- Migração: Adicionar colunas na tabela solicitacoes_correcao_registro
-- Data: 2025-01-14
-- Descrição: Adicionar colunas tipo_original, tipo_novo, modalidade_original, 
--            modalidade_nova, projeto_original, projeto_novo e renomear data_hora_corrigida

-- 1. Renomear data_hora_corrigida para data_hora_nova (se existir)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'solicitacoes_correcao_registro' 
        AND column_name = 'data_hora_corrigida'
    ) THEN
        ALTER TABLE solicitacoes_correcao_registro 
        RENAME COLUMN data_hora_corrigida TO data_hora_nova;
        RAISE NOTICE 'Coluna data_hora_corrigida renomeada para data_hora_nova';
    ELSE
        RAISE NOTICE 'Coluna data_hora_corrigida não existe ou já foi renomeada';
    END IF;
END $$;

-- 2. Adicionar coluna tipo_original se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'solicitacoes_correcao_registro' 
        AND column_name = 'tipo_original'
    ) THEN
        ALTER TABLE solicitacoes_correcao_registro ADD COLUMN tipo_original TEXT;
        RAISE NOTICE 'Coluna tipo_original adicionada';
    ELSE
        RAISE NOTICE 'Coluna tipo_original já existe';
    END IF;
END $$;

-- 3. Adicionar coluna tipo_novo se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'solicitacoes_correcao_registro' 
        AND column_name = 'tipo_novo'
    ) THEN
        ALTER TABLE solicitacoes_correcao_registro ADD COLUMN tipo_novo TEXT;
        RAISE NOTICE 'Coluna tipo_novo adicionada';
    ELSE
        RAISE NOTICE 'Coluna tipo_novo já existe';
    END IF;
END $$;

-- 4. Adicionar coluna modalidade_original se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'solicitacoes_correcao_registro' 
        AND column_name = 'modalidade_original'
    ) THEN
        ALTER TABLE solicitacoes_correcao_registro ADD COLUMN modalidade_original TEXT;
        RAISE NOTICE 'Coluna modalidade_original adicionada';
    ELSE
        RAISE NOTICE 'Coluna modalidade_original já existe';
    END IF;
END $$;

-- 5. Adicionar coluna modalidade_nova se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'solicitacoes_correcao_registro' 
        AND column_name = 'modalidade_nova'
    ) THEN
        ALTER TABLE solicitacoes_correcao_registro ADD COLUMN modalidade_nova TEXT;
        RAISE NOTICE 'Coluna modalidade_nova adicionada';
    ELSE
        RAISE NOTICE 'Coluna modalidade_nova já existe';
    END IF;
END $$;

-- 6. Adicionar coluna projeto_original se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'solicitacoes_correcao_registro' 
        AND column_name = 'projeto_original'
    ) THEN
        ALTER TABLE solicitacoes_correcao_registro ADD COLUMN projeto_original TEXT;
        RAISE NOTICE 'Coluna projeto_original adicionada';
    ELSE
        RAISE NOTICE 'Coluna projeto_original já existe';
    END IF;
END $$;

-- 7. Adicionar coluna projeto_novo se não existir
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'solicitacoes_correcao_registro' 
        AND column_name = 'projeto_novo'
    ) THEN
        ALTER TABLE solicitacoes_correcao_registro ADD COLUMN projeto_novo TEXT;
        RAISE NOTICE 'Coluna projeto_novo adicionada';
    ELSE
        RAISE NOTICE 'Coluna projeto_novo já existe';
    END IF;
END $$;

-- Verificar estrutura final da tabela
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'solicitacoes_correcao_registro'
ORDER BY ordinal_position;
