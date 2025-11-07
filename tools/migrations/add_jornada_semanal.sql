-- Migration: Adicionar jornada semanal variável aos usuários
-- Data: 07/11/2024
-- Descrição: Permite configurar horários de entrada/saída diferentes para cada dia da semana

-- Adicionar colunas para Segunda-feira
ALTER TABLE usuarios ADD COLUMN jornada_seg_inicio TIME;
ALTER TABLE usuarios ADD COLUMN jornada_seg_fim TIME;

-- Adicionar colunas para Terça-feira
ALTER TABLE usuarios ADD COLUMN jornada_ter_inicio TIME;
ALTER TABLE usuarios ADD COLUMN jornada_ter_fim TIME;

-- Adicionar colunas para Quarta-feira
ALTER TABLE usuarios ADD COLUMN jornada_qua_inicio TIME;
ALTER TABLE usuarios ADD COLUMN jornada_qua_fim TIME;

-- Adicionar colunas para Quinta-feira
ALTER TABLE usuarios ADD COLUMN jornada_qui_inicio TIME;
ALTER TABLE usuarios ADD COLUMN jornada_qui_fim TIME;

-- Adicionar colunas para Sexta-feira
ALTER TABLE usuarios ADD COLUMN jornada_sex_inicio TIME;
ALTER TABLE usuarios ADD COLUMN jornada_sex_fim TIME;

-- Adicionar colunas para Sábado
ALTER TABLE usuarios ADD COLUMN jornada_sab_inicio TIME;
ALTER TABLE usuarios ADD COLUMN jornada_sab_fim TIME;

-- Adicionar colunas para Domingo
ALTER TABLE usuarios ADD COLUMN jornada_dom_inicio TIME;
ALTER TABLE usuarios ADD COLUMN jornada_dom_fim TIME;

-- Adicionar campo para indicar se trabalha no dia
ALTER TABLE usuarios ADD COLUMN trabalha_seg INTEGER DEFAULT 1;
ALTER TABLE usuarios ADD COLUMN trabalha_ter INTEGER DEFAULT 1;
ALTER TABLE usuarios ADD COLUMN trabalha_qua INTEGER DEFAULT 1;
ALTER TABLE usuarios ADD COLUMN trabalha_qui INTEGER DEFAULT 1;
ALTER TABLE usuarios ADD COLUMN trabalha_sex INTEGER DEFAULT 1;
ALTER TABLE usuarios ADD COLUMN trabalha_sab INTEGER DEFAULT 0;
ALTER TABLE usuarios ADD COLUMN trabalha_dom INTEGER DEFAULT 0;
