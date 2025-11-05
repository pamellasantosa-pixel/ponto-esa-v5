# Este arquivo conterá a lógica de negócios e as funções de banco de dados
# que foram extraídas de app_v5_final.py para evitar a importação do Streamlit nos testes.

import sqlite3
import hashlib
from datetime import datetime, date, time, timedelta

# Placeholder para a conexão, será gerenciado pelas fixtures de teste ou pela aplicação principal
_db_connection = None

def set_db_connection(conn):
    """Define a conexão de banco de dados a ser usada pelo módulo."""
    global _db_connection
    _db_connection = conn

def get_db_connection():
    """Retorna a conexão de banco de dados ativa."""
    if _db_connection is None:
        # Em um cenário real, isso pode se conectar a um banco de dados padrão.
        # Para testes, esperamos que set_db_connection seja chamado.
        raise Exception("A conexão com o banco de dados não foi configurada.")
    return _db_connection

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def criar_usuario(nome, email, senha, cargo, nivel_acesso, conn=None):
    conn = conn or get_db_connection()
    senha_hash = hash_password(senha)
    try:
        conn.execute(
            "INSERT INTO usuarios (nome, email, senha, cargo, nivel_acesso) VALUES (?, ?, ?, ?, ?)",
            (nome, email, senha_hash, cargo, nivel_acesso),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# ... (todas as outras funções db_* de app_v5_final.py seriam movidas para cá)
# Por brevidade, apenas algumas funções de exemplo são incluídas.

def db_get_user(email, conn=None):
    conn = conn or get_db_connection()
    cursor = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    return cursor.fetchone()

def db_get_registros_ponto(user_id, data, conn=None):
    conn = conn or get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM registros_ponto WHERE usuario_id = ? AND data = ? ORDER BY hora",
        (user_id, data),
    )
    return cursor.fetchall()

def db_get_last_registro(user_id, data, conn=None):
    conn = conn or get_db_connection()
    cursor = conn.execute(
        "SELECT tipo FROM registros_ponto WHERE usuario_id = ? AND data = ? ORDER BY id DESC LIMIT 1",
        (user_id, data),
    )
    return cursor.fetchone()

def db_get_all_users(conn=None):
    conn = conn or get_db_connection()
    cursor = conn.execute("SELECT id, nome, email, cargo, nivel_acesso FROM usuarios")
    return cursor.fetchall()

def db_get_user_by_id(user_id, conn=None):
    conn = conn or get_db_connection()
    cursor = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    return cursor.fetchone()

def db_update_user(user_id, nome, email, cargo, nivel_acesso, conn=None):
    conn = conn or get_db_connection()
    conn.execute(
        "UPDATE usuarios SET nome = ?, email = ?, cargo = ?, nivel_acesso = ? WHERE id = ?",
        (nome, email, cargo, nivel_acesso, user_id),
    )
    conn.commit()

def db_delete_user(user_id, conn=None):
    conn = conn or get_db_connection()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
