import sys
import os
import pytest
import sqlite3
import tempfile
import shutil

# --- Configuração do Caminho do Projeto ---
# Adiciona o diretório raiz do projeto e o diretório do pacote ao sys.path
# para garantir que os módulos sejam encontrados durante a execução dos testes.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PACKAGE_DIR = os.path.join(ROOT_DIR, 'ponto_esa_v5', 'ponto_esa_v5')

if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

# --- Fixtures ---

@pytest.fixture(scope="function")
def db_connection():
    """
    Fixture para criar um banco de dados SQLite temporário em memória para cada função de teste.
    Garante que os testes sejam executados em um ambiente isolado.
    """
    # Importa as funções do banco de dados aqui para garantir que o sys.path já foi configurado
    import database as db_module

    # Importa depois para manter referência consistente ao módulo
    from database import init_db

    # Cria um arquivo de banco de dados temporário
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Conecta ao banco de dados temporário
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Inicializa o esquema do banco de dados usando a conexão temporária
    original_get_connection = db_module.get_connection

    def _temp_get_connection():
        return conn

    db_module.get_connection = _temp_get_connection

    try:
        init_db()
    finally:
        db_module.get_connection = original_get_connection
    
    yield conn
    
    # Fecha a conexão e remove o arquivo temporário
    conn.close()
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def temp_db_path():
    """Cria um caminho para um arquivo de banco de dados temporário."""
    # Cria um diretório temporário
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    
    yield db_path
    
    # Limpa o diretório temporário
    shutil.rmtree(temp_dir)
