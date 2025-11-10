"""
Database module with PostgreSQL support for Ponto ExSA v5.0
Supports both SQLite and PostgreSQL based on environment variables
"""

import os
import hashlib
import sqlite3
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'

# Placeholder para queries SQL (PostgreSQL usa %s, SQLite usa ?)
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"

# Importar psycopg2 se necessário
if USE_POSTGRESQL:
    import psycopg2
    import psycopg2.extras


def get_connection():
    """Retorna uma conexão com o banco de dados configurado"""
    if USE_POSTGRESQL:
        database_url = os.getenv('DATABASE_URL')
        try:
            if database_url:
                # No Render, a DATABASE_URL é fornecida e usada diretamente
                return psycopg2.connect(database_url)
            else:
                # Fallback para desenvolvimento local com variáveis separadas
                db_config_local = {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'database': os.getenv('DB_NAME', 'ponto_esa'),
                    'user': os.getenv('DB_USER', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', 'postgres'),
                    'port': os.getenv('DB_PORT', '5432')
                }
                return psycopg2.connect(**db_config_local)
        except psycopg2.OperationalError as e:
            print(f"❌ Erro ao conectar no PostgreSQL: {e}")
            print("\n📋 Certifique-se de que a variável de ambiente DATABASE_URL está configurada corretamente no Render.")
            raise
    else:
        os.makedirs('database', exist_ok=True)
        return sqlite3.connect('database/ponto_esa.db')


def hash_password(password):
    """Hash de senha usando SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_db_postgresql():
    """Inicializa banco de dados PostgreSQL"""
    conn = get_connection()
    c = conn.cursor()

    # Tabela usuarios
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) UNIQUE NOT NULL,
            senha VARCHAR(255) NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            nome_completo VARCHAR(255),
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT NOW(),
            jornada_inicio_previsto TIME DEFAULT '08:00',
            jornada_fim_previsto TIME DEFAULT '17:00'
        )
    ''')

    # Tabela registros_ponto
    c.execute('''
        CREATE TABLE IF NOT EXISTS registros_ponto (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            data_hora TIMESTAMP NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            modalidade VARCHAR(50),
            projeto VARCHAR(255),
            atividade TEXT,
            localizacao VARCHAR(255),
            latitude REAL,
            longitude REAL,
            data_registro TIMESTAMP DEFAULT NOW()
        )
    ''')

    # Tabela ausencias
    c.execute('''
        CREATE TABLE IF NOT EXISTS ausencias (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            data_inicio DATE NOT NULL,
            data_fim DATE NOT NULL,
            tipo VARCHAR(255) NOT NULL,
            motivo TEXT,
            arquivo_comprovante VARCHAR(255),
            status VARCHAR(50) DEFAULT 'pendente',
            data_registro TIMESTAMP DEFAULT NOW(),
            nao_possui_comprovante INTEGER DEFAULT 0
        )
    ''')

    # Tabela projetos
    c.execute('''
        CREATE TABLE IF NOT EXISTS projetos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) UNIQUE NOT NULL,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT NOW()
        )
    ''')

    # Tabela solicitacoes_horas_extras
    c.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes_horas_extras (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            justificativa TEXT NOT NULL,
            aprovador_solicitado VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT NOW(),
            aprovado_por VARCHAR(255),
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    ''')

    # Tabela atestado_horas
    c.execute('''
        CREATE TABLE IF NOT EXISTS atestado_horas (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            total_horas REAL NOT NULL,
            motivo TEXT,
            arquivo_comprovante VARCHAR(255),
            nao_possui_comprovante INTEGER DEFAULT 0,
            status VARCHAR(50) DEFAULT 'pendente',
            data_registro TIMESTAMP DEFAULT NOW(),
            aprovado_por VARCHAR(255),
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    ''')

    # Tabela atestados_horas (novo schema)
    c.execute('''
        CREATE TABLE IF NOT EXISTS atestados_horas (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            total_horas REAL NOT NULL,
            motivo TEXT,
            arquivo_comprovante VARCHAR(255),
            nao_possui_comprovante INTEGER DEFAULT 0,
            status VARCHAR(50) DEFAULT 'pendente',
            data_registro TIMESTAMP DEFAULT NOW(),
            aprovado_por VARCHAR(255),
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    ''')

    # Tabela uploads
    c.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            nome_original VARCHAR(255) NOT NULL,
            nome_arquivo VARCHAR(255) NOT NULL,
            tamanho INTEGER NOT NULL,
            tipo VARCHAR(100),
            categoria VARCHAR(50),
            data_upload TIMESTAMP DEFAULT NOW(),
            hash_arquivo VARCHAR(255),
            status VARCHAR(50) DEFAULT 'ativo'
        )
    ''')

    # Tabela banco_horas
    c.execute('''
        CREATE TABLE IF NOT EXISTS banco_horas (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            data DATE NOT NULL,
            horas_trabalhadas REAL DEFAULT 0,
            horas_previstas REAL DEFAULT 8,
            diferenca REAL DEFAULT 0,
            saldo_acumulado REAL DEFAULT 0,
            data_calculo TIMESTAMP DEFAULT NOW()
        )
    ''')

    # Tabela feriados
    c.execute('''
        CREATE TABLE IF NOT EXISTS feriados (
            id SERIAL PRIMARY KEY,
            data DATE NOT NULL,
            nome VARCHAR(255) NOT NULL,
            tipo VARCHAR(50),
            data_criacao TIMESTAMP DEFAULT NOW()
        )
    ''')

    # Tabela auditoria_correcoes
    c.execute('''
        CREATE TABLE IF NOT EXISTS auditoria_correcoes (
            id SERIAL PRIMARY KEY,
            registro_id INTEGER NOT NULL,
            gestor VARCHAR(255) NOT NULL,
            justificativa TEXT NOT NULL,
            data_correcao TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (registro_id) REFERENCES registros_ponto (id)
        )
    ''')

    # Inserir usuários padrão se não existirem
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_padrao = [
            ("funcionario", hash_password("senha_func_123"),
             "funcionario", "Funcionário Padrão"),
            ("gestor", hash_password("senha_gestor_123"),
             "gestor", "Gestor Principal")
        ]
        for usuario in usuarios_padrao:
            c.execute("""
                INSERT INTO usuarios (usuario, senha, tipo, nome_completo)
                VALUES (%s, %s, %s, %s)
            """, usuario)

    # Inserir projetos padrão se não existirem
    c.execute("SELECT COUNT(*) FROM projetos")
    if c.fetchone()[0] == 0:
        projetos_padrao = [
            "ADMINISTRATIVO",
            "EXPRESSAO-INTERNO",
            "FR - 3770-PBAQ",
            "SAM - 3406-DIALOGO-GERMANO",
            "SAM - 3406-DIALOGO - UBU",
            "SAM - 3450-GESTÃO NEGOCIOS (PESCA)",
            "SAM - 3614-PAEBM - MATIPO",
            "SAM - 3615-PAEBM - GERMANO",
            "MVV - 4096-SERROTE",
            "Trabalho em Campo"
        ]
        for projeto in projetos_padrao:
            c.execute("INSERT INTO projetos (nome) VALUES (%s)", (projeto,))

    conn.commit()
    conn.close()
    print("✅ Banco de dados PostgreSQL inicializado com sucesso!")


def init_db():
    """Inicializa o banco de dados (SQLite ou PostgreSQL)"""
    if USE_POSTGRESQL:
        init_db_postgresql()
    else:
        # Importar e usar a função original do database.py
        from database import init_db as init_db_sqlite
        init_db_sqlite()


if __name__ == '__main__':
    print(f"🔧 Modo: {'PostgreSQL' if USE_POSTGRESQL else 'SQLite'}")
    if USE_POSTGRESQL:
        print(
            f"📊 Conectando em: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    init_db()
