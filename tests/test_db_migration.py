import os
import sqlite3
from ponto_esa_v5.database import init_db
from ponto_esa_v5.tools.migrate_db import migrate


def test_migration_adds_upload_columns(tmp_path, monkeypatch):
    # Criar um DB temporário que simula versão antiga (sem hash_arquivo e status)
    db_dir = tmp_path / "database"
    db_dir.mkdir()
    db_path = str(db_dir / "ponto_esa.db")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            nome_original TEXT NOT NULL,
            nome_arquivo TEXT NOT NULL,
            tipo_arquivo TEXT NOT NULL,
            tamanho INTEGER NOT NULL,
            caminho TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

    # Forçar init_db/migrate a usar esse DB
    monkeypatch.chdir(tmp_path)

    # Executar migrate (deve adicionar colunas)
    migrate(db_path=db_path)

    # Verificar colunas
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('PRAGMA table_info(uploads)')
    cols = [row[1] for row in cur.fetchall()]
    conn.close()

    assert 'hash_arquivo' in cols
    assert 'status' in cols
