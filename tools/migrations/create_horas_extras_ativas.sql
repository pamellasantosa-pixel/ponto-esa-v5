-- Migration: Criar tabela para controlar horas extras em andamento
-- Data: 07/11/2024
-- Descrição: Registra horas extras que estão sendo executadas em tempo real

CREATE TABLE IF NOT EXISTS horas_extras_ativas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL,
    aprovador TEXT NOT NULL,
    justificativa TEXT NOT NULL,
    data_inicio TIMESTAMP NOT NULL,
    hora_inicio TIME NOT NULL,
    status TEXT DEFAULT 'em_execucao',
    data_fim TIMESTAMP,
    hora_fim TIME,
    tempo_decorrido_minutos INTEGER,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
