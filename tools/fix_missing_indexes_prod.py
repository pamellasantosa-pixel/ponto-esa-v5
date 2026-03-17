import os, sys
import psycopg2

url = os.getenv('DATABASE_URL')
if not url:
    print('ERRO: DATABASE_URL ausente')
    sys.exit(2)

sql_commands = [
    # Coluna e índices de auditoria
    "ALTER TABLE auditoria_alteracoes_ponto ADD COLUMN IF NOT EXISTS registro_id INTEGER",
    "CREATE INDEX IF NOT EXISTS idx_auditoria_registro_id ON auditoria_alteracoes_ponto(registro_id)",
    "CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_data ON auditoria_alteracoes_ponto(usuario_afetado, data_registro)",
    "CREATE INDEX IF NOT EXISTS idx_auditoria_data_alteracao ON auditoria_alteracoes_ponto(data_alteracao)",

    # Índices ausências
    "CREATE INDEX IF NOT EXISTS idx_ausencias_data ON ausencias(data_inicio, data_fim)",

    # Índices de pendências e correções
    "CREATE INDEX IF NOT EXISTS idx_pendencias_ign_data ON pendencias_ponto_ignoradas(data_referencia)",
    "CREATE INDEX IF NOT EXISTS idx_corr_usuario_status_data ON solicitacoes_correcao_registro(usuario, status, data_solicitacao)",

    # Corrige índice de notificações para colunas reais
    "DROP INDEX IF EXISTS idx_notif_usuario_lida",
    "CREATE INDEX IF NOT EXISTS idx_notif_usuario_lida ON Notificacoes(user_id, read)",

    # Corrige índice de jornada para colunas reais
    "DROP INDEX IF EXISTS idx_jornada_usuario_data",
    "CREATE INDEX IF NOT EXISTS idx_jornada_usuario_data ON jornada_semanal(usuario, dia)",
]

conn = psycopg2.connect(url)
conn.autocommit = False
try:
    cur = conn.cursor()
    for sql in sql_commands:
        cur.execute(sql)
    conn.commit()
    print('OK: migracao aplicada com sucesso')
finally:
    conn.close()
