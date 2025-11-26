
import os
import hashlib
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do banco de dados
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'

# Placeholder para queries SQL (PostgreSQL usa %s, SQLite usa ?)
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"

if USE_POSTGRESQL:
    # Tenta usar psycopg (v3) primeiro; se indisponível, cai para psycopg2
    _PG_DRIVER = None
    try:
        import psycopg as _psycopg
        _PG_DRIVER = 'psycopg'
    except Exception:
        try:
            import psycopg2 as _psycopg2
            import psycopg2.extras  # noqa: F401
            _PG_DRIVER = 'psycopg2'
        except Exception as _e:
            raise RuntimeError("Nenhum driver PostgreSQL disponível (psycopg ou psycopg2)") from _e

    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'ponto_esa'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres'),
        'port': os.getenv('DB_PORT', '5432'),
        'sslmode': os.getenv('DB_SSLMODE', 'require')
    }
else:
    import sqlite3
    from datetime import date, datetime

    # Registrar adaptadores explícitos para evitar DeprecationWarning no Python 3.12+
    # Armazena date/datetime como texto ISO8601 (compatível com consultas por data)
    def _adapt_date_iso(d: date) -> str:  # type: ignore[override]
        return d.isoformat()

    def _adapt_datetime_iso(dt: datetime) -> str:  # type: ignore[override]
        return dt.isoformat(sep=" ")

    sqlite3.register_adapter(date, _adapt_date_iso)
    sqlite3.register_adapter(datetime, _adapt_datetime_iso)


def get_connection(db_path: str | None = None):
    """Retorna uma conexão com o banco de dados configurado"""
    if USE_POSTGRESQL:
        try:
            # Tentar estabelecer conexão e atribuir a `conn` para garantir
            # que qualquer exceção seja capturada pelo bloco abaixo.
            conn = None
            if _PG_DRIVER == 'psycopg':
                cfg = dict(DB_CONFIG)
                # psycopg3 aceita 'dbname' e também 'database', mas normalizar evita inconsistências
                cfg['dbname'] = cfg.pop('database', cfg.get('database'))
                conn = _psycopg.connect(**cfg)
            else:
                conn = _psycopg2.connect(**DB_CONFIG)

            # Se chegamos até aqui, a conexão PostgreSQL foi estabelecida
            return conn
        except Exception as e:
            # Registrar exceção completa e cair para o fallback SQLite
            logging.exception("Falha ao conectar no PostgreSQL, usando fallback para SQLite: %s", e)
            # Fallback: criar conexão SQLite local
            try:
                import sqlite3
                from datetime import date, datetime

                def _adapt_date_iso(d: date) -> str:  # type: ignore[override]
                    return d.isoformat()

                def _adapt_datetime_iso(dt: datetime) -> str:  # type: ignore[override]
                    return dt.isoformat(sep=" ")

                sqlite3.register_adapter(date, _adapt_date_iso)
                sqlite3.register_adapter(datetime, _adapt_datetime_iso)

                os.makedirs('database', exist_ok=True)
                if db_path:
                    conn = sqlite3.connect(db_path)
                else:
                    conn = sqlite3.connect('database/ponto_esa.db')

                class AdaptCursor:
                    def __init__(self, cursor):
                        self._cursor = cursor

                    def execute(self, sql, params=None):
                        if isinstance(sql, str):
                            sql = sql.replace('%s', SQL_PLACEHOLDER)
                        if params is None:
                            return self._cursor.execute(sql)
                        return self._cursor.execute(sql, params)

                    def executemany(self, sql, seq_of_params):
                        if isinstance(sql, str):
                            sql = sql.replace('%s', SQL_PLACEHOLDER)
                        return self._cursor.executemany(sql, seq_of_params)

                    def __getattr__(self, name):
                        return getattr(self._cursor, name)

                class ConnectionWrapper:
                    def __init__(self, conn):
                        self._conn = conn

                    def cursor(self):
                        return AdaptCursor(self._conn.cursor())

                    def commit(self):
                        return self._conn.commit()

                    def close(self):
                        return self._conn.close()

                    def __getattr__(self, name):
                        return getattr(self._conn, name)

                # Atualizar variáveis globais para refletir o fallback
                globals()['USE_POSTGRESQL'] = False
                globals()['SQL_PLACEHOLDER'] = "?"

                return ConnectionWrapper(conn)
            except Exception:
                # Se o fallback também falhar, relançar a exceção original
                raise
    else:
        os.makedirs('database', exist_ok=True)
        if db_path:
            conn = sqlite3.connect(db_path)
        else:
            conn = sqlite3.connect('database/ponto_esa.db')

        class AdaptCursor:
            def __init__(self, cursor):
                self._cursor = cursor

            def execute(self, sql, params=None):
                if isinstance(sql, str):
                    sql = sql.replace('%s', SQL_PLACEHOLDER)
                if params is None:
                    return self._cursor.execute(sql)
                return self._cursor.execute(sql, params)

            def executemany(self, sql, seq_of_params):
                if isinstance(sql, str):
                    sql = sql.replace('%s', SQL_PLACEHOLDER)
                return self._cursor.executemany(sql, seq_of_params)

            def __getattr__(self, name):
                return getattr(self._cursor, name)

        class ConnectionWrapper:
            def __init__(self, conn):
                self._conn = conn

            def cursor(self):
                return AdaptCursor(self._conn.cursor())

            def commit(self):
                return self._conn.commit()

            def close(self):
                return self._conn.close()

            def __getattr__(self, name):
                return getattr(self._conn, name)

        return ConnectionWrapper(conn)


def adapt_sql_for_postgresql(sql):
    """Adapta queries SQL para PostgreSQL se necessário"""
    if USE_POSTGRESQL:
        # Adaptar tipos de dados se necessário - FAZER PRIMEIRO as substituições específicas
        sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        # Substituir AUTOINCREMENT por SERIAL (para casos que não foram cobertos acima)
        sql = sql.replace('AUTOINCREMENT', 'SERIAL')
        # Substituir CURRENT_TIMESTAMP por NOW()
        sql = sql.replace('CURRENT_TIMESTAMP', 'NOW()')
    return sql


def q(sql_text: str) -> str:
    """Return query adapted for the configured SQL placeholder."""
    if not isinstance(sql_text, str):
        return sql_text
    return sql_text.replace('%s', SQL_PLACEHOLDER)


def hash_password(password: str) -> str:
    """Hash a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Tabela usuarios com novos campos para jornada prevista
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            nome_completo TEXT,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            jornada_inicio_previsto TIME DEFAULT '08:00',
            jornada_fim_previsto TIME DEFAULT '17:00'
        )
    '''))

    # Tabela registros_ponto com campos de GPS
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS registros_ponto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            data_hora TIMESTAMP NOT NULL,
            tipo TEXT NOT NULL,
            modalidade TEXT,
            projeto TEXT,
            atividade TEXT,
            localizacao TEXT,
            latitude REAL,
            longitude REAL,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''))

    # Tabela de ausências com campo para "não possui comprovante"
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS ausencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            data_inicio DATE NOT NULL,
            data_fim DATE NOT NULL,
            tipo TEXT NOT NULL,
            motivo TEXT,
            arquivo_comprovante TEXT,
            status TEXT DEFAULT 'pendente',
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            nao_possui_comprovante INTEGER DEFAULT 0
        )
    '''))

    # Tabela de projetos
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    '''))

    # Nova tabela para solicitações de horas extras
    c.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes_horas_extras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            justificativa TEXT NOT NULL,
            aprovador_solicitado TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    ''')

    # Tabela para atestado de horas (schema antigo - manter para compatibilidade)
    c.execute('''
        CREATE TABLE IF NOT EXISTS atestado_horas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            total_horas REAL NOT NULL,
            motivo TEXT,
            arquivo_comprovante TEXT,
            status TEXT DEFAULT 'pendente',
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    ''')

    # Tabela para aprovação de atestados de horas (novo schema para interface de aprovação)
    c.execute('''
        CREATE TABLE IF NOT EXISTS atestados_horas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            horas_trabalhadas REAL NOT NULL,
            justificativa TEXT NOT NULL,
            arquivo_id INTEGER,
            status TEXT DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            rejeitado_por TEXT,
            data_rejeicao TIMESTAMP,
            motivo_rejeicao TEXT,
            observacoes TEXT,
            FOREIGN KEY (arquivo_id) REFERENCES uploads(id)
        )
    ''')

    # Tabela para uploads de arquivos
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

    # Tabela para banco de horas
    c.execute('''
        CREATE TABLE IF NOT EXISTS banco_horas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            credito REAL DEFAULT 0,
            debito REAL DEFAULT 0,
            saldo_anterior REAL DEFAULT 0,
            saldo_atual REAL DEFAULT 0,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            relacionado_id INTEGER,
            relacionado_tabela TEXT
        )
    ''')

    # Tabela para feriados
    c.execute('''
        CREATE TABLE IF NOT EXISTS feriados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT DEFAULT 'nacional',
            ativo INTEGER DEFAULT 1
        )
    ''')

    # Tabela que armazena jornadas semanais personalizadas por usuário
    c.execute('''
        CREATE TABLE IF NOT EXISTS jornada_semanal (
            usuario TEXT NOT NULL,
            dia TEXT NOT NULL,
            trabalha INTEGER DEFAULT 1,
            inicio TIME DEFAULT '08:00',
            fim TIME DEFAULT '17:00',
            intervalo INTEGER DEFAULT 60,
            PRIMARY KEY (usuario, dia)
        )
    ''')

    # Tabela de Notificacoes (SQLite)
    c.execute('''
        CREATE TABLE IF NOT EXISTS Notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT,
            message TEXT,
            type TEXT,
            read INTEGER DEFAULT 0,
            extra_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de Solicitações de Ajuste de Ponto (inclui campos usados pelos testes)
    c.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes_ajuste_ponto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            aprovador_solicitado TEXT,
            registro_id INTEGER,
            data_hora_original TIMESTAMP,
            data_hora_nova TIMESTAMP,
            tipo_original TEXT,
            tipo_novo TEXT,
            modalidade_original TEXT,
            modalidade_nova TEXT,
            projeto_original TEXT,
            projeto_novo TEXT,
            justificativa TEXT,
            dados_solicitados TEXT,
            status TEXT DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_resposta TIMESTAMP,
            aprovado_por TEXT,
            respondido_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
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
        c.executemany(
            "INSERT INTO usuarios (usuario, senha, tipo, nome_completo) VALUES (?, ?, ?, ?)", usuarios_padrao)

    # Inserir projetos padrão se não existirem
    c.execute("SELECT COUNT(*) FROM projetos")
    if c.fetchone()[0] == 0:
        projetos_padrao = [
            ("ADMINISTRATIVO", "Atividades administrativas gerais"),
            ("EXPRESSAO-INTERNO", "Projetos internos da Expressão"),
            ("FR - 3770-PBAQ", "Projeto FR - 3770-PBAQ"),
            ("SAM - 3406-DIALOGO-GERMANO", "Projeto SAM - 3406-DIALOGO-GERMANO"),
            ("SAM - 3406-DIALOGO - UBU", "Projeto SAM - 3406-DIALOGO - UBU"),
            ("SAM - 3450-GESTÃO NEGOCIOS (PESCA)",
             "Projeto SAM - 3450-GESTÃO NEGOCIOS (PESCA)"),
            ("SAM - 3614-PAEBM - MATIPO", "Projeto SAM - 3614-PAEBM - MATIPO"),
            ("SAM - 3615-PAEBM - GERMANO", "Projeto SAM - 3615-PAEBM - GERMANO"),
            ("MVV - 4096-SERROTE", "Projeto MVV - 4096-SERROTE"),
            ("Trabalho em Campo", "Atividades de campo e visitas técnicas")
        ]
        c.executemany(
            "INSERT INTO projetos (nome, descricao) VALUES (?, ?)", projetos_padrao)

    # Inserir feriados de Belo Horizonte para 2025
    c.execute("SELECT COUNT(*) FROM feriados")
    if c.fetchone()[0] == 0:
        feriados_2025 = [
            ("2025-01-01", "Confraternização Universal", "nacional"),
            ("2025-02-28", "Carnaval", "nacional"),
            ("2025-03-01", "Carnaval", "nacional"),
            ("2025-04-18", "Sexta-feira Santa", "nacional"),
            ("2025-04-21", "Tiradentes", "nacional"),
            ("2025-05-01", "Dia do Trabalhador", "nacional"),
            ("2025-06-19", "Corpus Christi", "nacional"),
            ("2025-09-07", "Independência do Brasil", "nacional"),
            ("2025-10-12", "Nossa Senhora Aparecida", "nacional"),
            ("2025-11-02", "Finados", "nacional"),
            ("2025-11-15", "Proclamação da República", "nacional"),
            ("2025-12-25", "Natal", "nacional"),
            ("2025-08-15", "Assunção de Nossa Senhora", "bh"),
            ("2025-12-08", "Imaculada Conceição", "bh")
        ]
        c.executemany(
            "INSERT INTO feriados (data, nome, tipo) VALUES (?, ?, ?)", feriados_2025)

    # Adicionar colunas se não existirem (para compatibilidade com versões anteriores)
    try:
        c.execute(
            "ALTER TABLE usuarios ADD COLUMN jornada_inicio_previsto TIME DEFAULT '08:00'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute(
            "ALTER TABLE usuarios ADD COLUMN jornada_fim_previsto TIME DEFAULT '17:00'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE registros_ponto ADD COLUMN latitude REAL")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE registros_ponto ADD COLUMN longitude REAL")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute(
            "ALTER TABLE ausencias ADD COLUMN nao_possui_comprovante INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Compatibilidade: adicionar coluna hash_arquivo em uploads se ausente
    try:
        c.execute("ALTER TABLE uploads ADD COLUMN hash_arquivo TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE uploads ADD COLUMN status TEXT DEFAULT 'ativo'")
    except sqlite3.OperationalError:
        pass

    # Compatibilidade: adicionar coluna nao_possui_comprovante em atestado_horas se ausente
    try:
        c.execute("ALTER TABLE atestado_horas ADD COLUMN nao_possui_comprovante INTEGER DEFAULT 0")
    except Exception:
        pass

    # Compatibilidade: adicionar colunas ausentes em solicitacoes_ajuste_ponto
    try:
        c.execute("ALTER TABLE solicitacoes_ajuste_ponto ADD COLUMN aprovador_solicitado TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE solicitacoes_ajuste_ponto ADD COLUMN data_resposta TIMESTAMP")
    except Exception:
        pass

    # Tabela para auditoria de correções de registros
    c.execute('''
        CREATE TABLE IF NOT EXISTS auditoria_correcoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_id INTEGER NOT NULL,
            gestor TEXT NOT NULL,
            justificativa TEXT NOT NULL,
            data_correcao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (registro_id) REFERENCES registros_ponto (id)
        )
    ''')

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
