"""
Script de migração leve para o Ponto ESA - garante colunas necessárias na tabela uploads.
Uso: python -m ponto_esa_v5.tools.migrate_db (a partir da raiz do projeto) ou executar diretamente.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..',
                       'database', 'ponto_esa.db')
DB_PATH = os.path.normpath(os.path.abspath(DB_PATH))


def migrate(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Garantir tabela uploads
    c.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            nome_original TEXT NOT NULL,
            nome_arquivo TEXT NOT NULL,
            tipo_arquivo TEXT NOT NULL,
            tamanho INTEGER NOT NULL,
            caminho TEXT NOT NULL,
            hash_arquivo TEXT,
            relacionado_a TEXT,
            relacionado_id INTEGER,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Adicionar colunas se ausentes
    try:
        c.execute("ALTER TABLE uploads ADD COLUMN hash_arquivo TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE uploads ADD COLUMN status TEXT DEFAULT 'ativo'")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


if __name__ == '__main__':
    migrate()
    print('Migração concluída para', DB_PATH)
