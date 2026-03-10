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

# Configuração do banco de dados.
# Mantém compatibilidade com variável explícita e inferência por DATABASE_URL.
_use_pg_env = os.getenv('USE_POSTGRESQL')
if _use_pg_env is None:
    USE_POSTGRESQL = bool(os.getenv('DATABASE_URL'))
else:
    USE_POSTGRESQL = _use_pg_env.lower() == 'true'

# Placeholder para queries SQL (PostgreSQL usa %s, SQLite usa ?)
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"

# Importar psycopg2 se necessário
if USE_POSTGRESQL:
    import psycopg2
    import psycopg2.extras


def get_connection(db_path: str | None = None):
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
        # For SQLite, delegate to the primary database module which handles
        # the ConnectionWrapper and optional db_path.
        try:
            from ponto_esa_v5.database import get_connection as sqlite_get_connection
            return sqlite_get_connection(db_path)
        except Exception:
            os.makedirs('database', exist_ok=True)
            return sqlite3.connect(db_path or 'database/ponto_esa.db')


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
            cpf VARCHAR(11),
            email VARCHAR(255),
            data_nascimento DATE,
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

    # Tabela horas_extras_ativas
    c.execute('''
        CREATE TABLE IF NOT EXISTS horas_extras_ativas (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            aprovador VARCHAR(255) NOT NULL,
            justificativa TEXT NOT NULL,
            data_inicio TIMESTAMP NOT NULL,
            hora_inicio TIME NOT NULL,
            status VARCHAR(50) DEFAULT 'em_execucao',
            data_fim TIMESTAMP,
            hora_fim TIME,
            tempo_decorrido_minutos INTEGER,
            data_criacao TIMESTAMP DEFAULT NOW()
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

    # Tabela de auditoria completa das alterações de ponto
    c.execute('''
        CREATE TABLE IF NOT EXISTS auditoria_alteracoes_ponto (
            id SERIAL PRIMARY KEY,
            usuario_afetado VARCHAR(255) NOT NULL,
            data_registro DATE NOT NULL,
            entrada_original VARCHAR(20),
            saida_original VARCHAR(20),
            entrada_corrigida VARCHAR(20),
            saida_corrigida VARCHAR(20),
            tipo_alteracao VARCHAR(100) NOT NULL,
            realizado_por VARCHAR(255) NOT NULL,
            data_alteracao TIMESTAMP DEFAULT NOW(),
            justificativa TEXT,
            detalhes TEXT
        )
    ''')

    # Tabela para ignorar pendências de ponto
    c.execute('''
        CREATE TABLE IF NOT EXISTS pendencias_ponto_ignoradas (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            data_referencia DATE NOT NULL,
            tipo_inconsistencia VARCHAR(100) NOT NULL,
            ignorado_por VARCHAR(255) NOT NULL,
            motivo TEXT,
            data_ignoracao TIMESTAMP DEFAULT NOW()
        )
    ''')

    c.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS idx_pendencia_ignorada_unica
        ON pendencias_ponto_ignoradas(usuario, data_referencia, tipo_inconsistencia)
    ''')

    # Tabela solicitacoes_correcao_registro
    c.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes_correcao_registro (
            id SERIAL PRIMARY KEY,
            usuario VARCHAR(255) NOT NULL,
            registro_id INTEGER,
            data_hora_original TIMESTAMP NOT NULL,
            data_hora_nova TIMESTAMP NOT NULL,
            tipo_original VARCHAR(50),
            tipo_novo VARCHAR(50),
            modalidade_original VARCHAR(50),
            modalidade_nova VARCHAR(50),
            projeto_original VARCHAR(255),
            projeto_novo VARCHAR(255),
            tipo_solicitacao VARCHAR(50) DEFAULT 'ajuste_registro',
            data_referencia DATE,
            hora_inicio_solicitada VARCHAR(20),
            hora_saida_solicitada VARCHAR(20),
            justificativa TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprovado_por VARCHAR(255),
            data_aprovacao TIMESTAMP,
            observacoes TEXT,
            FOREIGN KEY (usuario) REFERENCES usuarios(usuario),
            FOREIGN KEY (registro_id) REFERENCES registros_ponto(id)
        )
    ''')

    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_solicitacoes_correcao_usuario 
        ON solicitacoes_correcao_registro(usuario)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_solicitacoes_correcao_status 
        ON solicitacoes_correcao_registro(status)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_solicitacoes_correcao_registro 
        ON solicitacoes_correcao_registro(registro_id)
    ''')

    # ============================================
    # MIGRATIONS: Adicionar colunas que podem faltar em tabelas existentes
    # ============================================
    
    # Adicionar colunas cpf, email, data_nascimento na tabela usuarios (se não existirem)
    migration_columns = [
        ('usuarios', 'cpf', 'VARCHAR(11)'),
        ('usuarios', 'email', 'VARCHAR(255)'),
        ('usuarios', 'data_nascimento', 'DATE'),
    ]
    
    for table, column, col_type in migration_columns:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}")
        except Exception as e:
            # Coluna já existe ou erro não crítico
            pass
    
    conn.commit()

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
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            print(f"📊 Conectando via DATABASE_URL")
        else:
            print(
                f"📊 Conectando em: {os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'ponto_esa')}")
    init_db()
