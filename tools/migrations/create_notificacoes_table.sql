-- Cria a tabela de notificações em PostgreSQL caso ainda não exista
CREATE TABLE IF NOT EXISTS notificacoes (
    id TEXT PRIMARY KEY,
    user_id VARCHAR(255),
    title TEXT,
    message TEXT,
    type TEXT,
    timestamp TEXT,
    read BOOLEAN DEFAULT FALSE,
    extra_data JSON
);
