from ponto_esa_v5.database_postgresql import get_connection

# Encapsular referências a `get_connection` dentro de funções
def initialize_postgresql():
    conn = get_connection()
    cursor = conn.cursor()

    # Criar tabelas obrigatórias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS horas_extras_ativas (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            justificativa TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT NOW(),
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    ''')

    cursor.execute('''
        ALTER TABLE solicitacoes_correcao_registro
        ADD COLUMN IF NOT EXISTS data_hora_nova TIMESTAMP
    ''')

    conn.commit()
    conn.close()

initialize_postgresql()
