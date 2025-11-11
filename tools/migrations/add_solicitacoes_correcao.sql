-- Migration: Tabela de solicitações de correção de registro
-- Permite que funcionários solicitem correção de registros incorretos

CREATE TABLE IF NOT EXISTS solicitacoes_correcao_registro (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(255) NOT NULL,
    registro_id INTEGER NOT NULL,
    data_hora_original TIMESTAMP NOT NULL,
    data_hora_nova TIMESTAMP NOT NULL,
    tipo_original VARCHAR(50),
    tipo_novo VARCHAR(50),
    modalidade_original VARCHAR(50),
    modalidade_nova VARCHAR(50),
    projeto_original VARCHAR(255),
    projeto_novo VARCHAR(255),
    justificativa TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pendente',
    data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aprovado_por VARCHAR(255),
    data_aprovacao TIMESTAMP,
    observacoes TEXT,
    FOREIGN KEY (usuario) REFERENCES usuarios(usuario),
    FOREIGN KEY (registro_id) REFERENCES registros_ponto(id)
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_solicitacoes_correcao_usuario ON solicitacoes_correcao_registro(usuario);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_correcao_status ON solicitacoes_correcao_registro(status);
CREATE INDEX IF NOT EXISTS idx_solicitacoes_correcao_registro ON solicitacoes_correcao_registro(registro_id);
