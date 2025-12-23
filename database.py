import os
import hashlib
import logging
from dotenv import load_dotenv
import sqlite3
from contextlib import contextmanager
import threading

# Carregar variáveis de ambiente
load_dotenv()

# Logger para este módulo
logger = logging.getLogger(__name__)

# Lista de tabelas obrigatórias que devem existir no banco
REQUIRED_TABLES = [
    'usuarios', 'registros_ponto', 'ausencias', 'projetos',
    'solicitacoes_horas_extras', 'atestado_horas', 'atestados_horas',
    'uploads', 'banco_horas', 'feriados', 'jornada_semanal',
    'Notificacoes', 'solicitacoes_ajuste_ponto', 'solicitacoes_correcao_registro',
    'auditoria_correcoes'
]

# Configuração do banco de dados - usar PostgreSQL
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'true').lower() == 'true'
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"

# Importar psycopg2 se necessário
if USE_POSTGRESQL:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool as pg_pool

# =============================================
# CONNECTION POOL SINGLETON - OTIMIZAÇÃO DE PERFORMANCE
# =============================================
# Evita abrir nova conexão TCP para cada operação (latência ~100-300ms por conexão)

_connection_pool = None
_pool_lock = threading.Lock()
_pool_connections = set()  # Rastreia conexões que vieram do pool


def _get_pool():
    """Retorna o pool de conexões singleton (thread-safe)"""
    global _connection_pool
    
    if _connection_pool is not None:
        return _connection_pool
    
    with _pool_lock:
        # Double-check após adquirir lock
        if _connection_pool is not None:
            return _connection_pool
        
        if USE_POSTGRESQL:
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                try:
                    # Pool com min 2, max 15 conexões para melhor throughput
                    # Nota: statement_timeout removido pois não é suportado pelo Neon Pooler
                    _connection_pool = pg_pool.ThreadedConnectionPool(
                        minconn=2,
                        maxconn=15,
                        dsn=database_url,
                        # Configurações para conexões mais rápidas
                        connect_timeout=10
                    )
                    logger.info("✅ Connection pool PostgreSQL criado (2-15 conexões)")
                except Exception as e:
                    logger.error(f"❌ Erro ao criar pool: {e}")
                    _connection_pool = None
    
    return _connection_pool


def get_connection(db_path: str | None = None):
    """Retorna uma conexão com o banco de dados configurado.
    
    OTIMIZADO: Usa connection pool para PostgreSQL (evita overhead de TCP handshake).
    """
    if USE_POSTGRESQL:
        # Tentar usar pool primeiro
        pool = _get_pool()
        if pool:
            try:
                conn = pool.getconn()
                # Rastrear conexão usando seu id
                _pool_connections.add(id(conn))
                return conn
            except Exception as e:
                logger.warning(f"Pool falhou, criando conexão direta: {e}")
        
        # Fallback: conexão direta (caso pool falhe)
        database_url = os.getenv('DATABASE_URL')
        try:
            if database_url:
                conn = psycopg2.connect(database_url, connect_timeout=10)
                return conn
            else:
                db_config_local = {
                    'host': os.getenv('DB_HOST', 'localhost'),
                    'database': os.getenv('DB_NAME', 'ponto_esa'),
                    'user': os.getenv('DB_USER', 'postgres'),
                    'password': os.getenv('DB_PASSWORD', 'postgres'),
                    'port': os.getenv('DB_PORT', '5432')
                }
                conn = psycopg2.connect(**db_config_local, connect_timeout=10)
                return conn
        except psycopg2.OperationalError as e:
            print(f"❌ Erro ao conectar no PostgreSQL: {e}")
            raise
    else:
        os.makedirs('database', exist_ok=True)
        return sqlite3.connect(db_path or 'database/ponto_esa.db')


def return_connection(conn):
    """Devolve conexão ao pool (ou fecha se não for do pool)"""
    if conn is None:
        return
    
    if USE_POSTGRESQL:
        pool = _get_pool()
        conn_id = id(conn)
        if pool and conn_id in _pool_connections:
            try:
                _pool_connections.discard(conn_id)
                pool.putconn(conn)
                return
            except Exception as e:
                logger.warning(f"Erro ao devolver conexão ao pool: {e}")
    
    # Fallback: fechar conexão
    try:
        conn.close()
    except:
        pass


@contextmanager
def get_db_context():
    """Context manager para conexão com banco - gerencia abertura e fechamento automaticamente.
    
    Uso:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
            conn.commit()
    """
    conn = None
    try:
        conn = get_connection()
        yield conn
    finally:
        return_connection(conn)


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


# Flag para evitar init_db() múltiplas vezes
_db_initialized = False
_db_init_lock = threading.Lock()


def init_db():
    """Inicializa o banco de dados (executa apenas uma vez por processo)"""
    global _db_initialized
    
    # Fast path: já inicializado
    if _db_initialized:
        return
    
    with _db_init_lock:
        # Double-check após lock
        if _db_initialized:
            return
        
        _init_db_internal()
        _db_initialized = True
        logger.info("✅ Banco de dados inicializado")


def _init_db_internal():
    """Implementação real do init_db (uso interno)"""
    conn = get_connection()
    c = conn.cursor()

    # Tabela usuarios com novos campos para jornada prevista, CPF e data nascimento
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL,
            nome_completo TEXT,
            cpf TEXT,
            data_nascimento DATE,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT NOW(),
            jornada_inicio_previsto TIME DEFAULT '08:00',
            jornada_fim_previsto TIME DEFAULT '17:00'
        )
    '''))
    
    # Adicionar colunas CPF e data_nascimento se não existirem (migração)
    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cpf TEXT")
        c.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS data_nascimento DATE")
    except:
        pass

    # Tabela registros_ponto com campos de GPS
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS registros_ponto (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            data_hora TIMESTAMP NOT NULL,
            tipo TEXT NOT NULL,
            modalidade TEXT,
            projeto TEXT,
            atividade TEXT,
            localizacao TEXT,
            latitude REAL,
            longitude REAL,
            data_registro TIMESTAMP DEFAULT NOW()
        )
    '''))

    # Tabela de ausências com campo para "não possui comprovante"
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS ausencias (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            data_inicio DATE NOT NULL,
            data_fim DATE NOT NULL,
            tipo TEXT NOT NULL,
            motivo TEXT,
            arquivo_comprovante TEXT,
            status TEXT DEFAULT 'pendente',
            data_registro TIMESTAMP DEFAULT NOW(),
            nao_possui_comprovante INTEGER DEFAULT 0
        )
    '''))

    # Tabela de projetos
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS projetos (
            id SERIAL PRIMARY KEY,
            nome TEXT UNIQUE NOT NULL,
            descricao TEXT,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT NOW()
        )
    '''))

    # Nova tabela para solicitações de horas extras
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS solicitacoes_horas_extras (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            total_horas REAL,
            justificativa TEXT NOT NULL,
            aprovador_solicitado TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT NOW(),
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    '''))
    
    # Migração: adicionar coluna total_horas se não existir
    try:
        c.execute("ALTER TABLE solicitacoes_horas_extras ADD COLUMN IF NOT EXISTS total_horas REAL")
    except:
        pass

    # Tabela para uploads de arquivos (DEVE vir antes de atestados_horas por causa da FK)
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS uploads (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            nome_original TEXT NOT NULL,
            nome_arquivo TEXT NOT NULL,
            tipo_arquivo TEXT NOT NULL,
            tamanho INTEGER NOT NULL,
            caminho TEXT NOT NULL,
            hash_arquivo TEXT,
            relacionado_a TEXT,
            relacionado_id INTEGER,
            data_upload TIMESTAMP DEFAULT NOW(),
            conteudo BYTEA,
            status TEXT DEFAULT 'ativo'
        )
    '''))

    # Tabela para atestado de horas (schema antigo - manter para compatibilidade)
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS atestado_horas (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            hora_inicio TIME NOT NULL,
            hora_fim TIME NOT NULL,
            total_horas REAL NOT NULL,
            motivo TEXT,
            arquivo_comprovante TEXT,
            status TEXT DEFAULT 'pendente',
            data_registro TIMESTAMP DEFAULT NOW(),
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    '''))

    # Tabela para aprovação de atestados de horas (novo schema para interface de aprovação)
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS atestados_horas (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            horas_trabalhadas REAL NOT NULL,
            justificativa TEXT NOT NULL,
            arquivo_id INTEGER,
            status TEXT DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT NOW(),
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            rejeitado_por TEXT,
            data_rejeicao TIMESTAMP,
            motivo_rejeicao TEXT,
            observacoes TEXT,
            FOREIGN KEY (arquivo_id) REFERENCES uploads(id)
        )
    '''))

    # Tabela para banco de horas
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS banco_horas (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            data DATE NOT NULL,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            credito REAL DEFAULT 0,
            debito REAL DEFAULT 0,
            saldo_anterior REAL DEFAULT 0,
            saldo_atual REAL DEFAULT 0,
            data_registro TIMESTAMP DEFAULT NOW(),
            relacionado_id INTEGER,
            relacionado_tabela TEXT
        )
    '''))

    # Tabela para feriados
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS feriados (
            id SERIAL PRIMARY KEY,
            data DATE UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT DEFAULT 'nacional',
            ativo INTEGER DEFAULT 1
        )
    '''))

    # Tabela que armazena jornadas semanais personalizadas por usuário
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS jornada_semanal (
            usuario TEXT NOT NULL,
            dia TEXT NOT NULL,
            trabalha INTEGER DEFAULT 1,
            inicio TIME DEFAULT '08:00',
            fim TIME DEFAULT '17:00',
            intervalo INTEGER DEFAULT 60,
            PRIMARY KEY (usuario, dia)
        )
    '''))

    # Tabela de Notificacoes
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS Notificacoes (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT,
            message TEXT,
            type TEXT,
            read INTEGER DEFAULT 0,
            extra_data TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        )
    '''))

    # Tabela de Solicitações de Ajuste de Ponto (inclui campos usados pelos testes)
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS solicitacoes_ajuste_ponto (
            id SERIAL PRIMARY KEY,
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
            data_solicitacao TIMESTAMP DEFAULT NOW(),
            data_resposta TIMESTAMP,
            aprovado_por TEXT,
            respondido_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    '''))

    # Tabela para solicitações de correção de registro
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS solicitacoes_correcao_registro (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            registro_id INTEGER NOT NULL,
            data_hora_original TIMESTAMP NOT NULL,
            data_hora_nova TIMESTAMP,
            tipo_original TEXT,
            tipo_novo TEXT,
            modalidade_original TEXT,
            modalidade_nova TEXT,
            projeto_original TEXT,
            projeto_novo TEXT,
            justificativa TEXT NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_solicitacao TIMESTAMP DEFAULT NOW(),
            aprovado_por TEXT,
            data_aprovacao TIMESTAMP,
            observacoes TEXT
        )
    '''))

    # Tabela configuracoes para armazenar parâmetros globais
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL,
            data_atualizacao TIMESTAMP DEFAULT NOW(),
            descricao TEXT
        )
    '''))

    # Inserir usuários padrão se não existirem
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_padrao = [
            ("funcionario", hash_password("senha_func_123"),
             "funcionario", "Funcionário Padrão"),
            ("gestor", hash_password("senha_gestor_123"),
             "gestor", "Gestor Principal")
        ]
        for u in usuarios_padrao:
            c.execute(
                f"INSERT INTO usuarios (usuario, senha, tipo, nome_completo) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})", u)

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
        for p in projetos_padrao:
            c.execute(
                f"INSERT INTO projetos (nome, descricao) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})", p)

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
        for f in feriados_2025:
            c.execute(
                f"INSERT INTO feriados (data, nome, tipo) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})", f)

    # Adicionar colunas se não existirem (para compatibilidade com versões anteriores)
    # PostgreSQL usa ADD COLUMN IF NOT EXISTS
    try:
        c.execute(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_inicio_previsto TIME DEFAULT '08:00'")
    except Exception:
        pass

    try:
        c.execute(
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_fim_previsto TIME DEFAULT '17:00'")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE registros_ponto ADD COLUMN IF NOT EXISTS latitude REAL")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE registros_ponto ADD COLUMN IF NOT EXISTS longitude REAL")
    except Exception:
        pass

    try:
        c.execute(
            "ALTER TABLE ausencias ADD COLUMN IF NOT EXISTS nao_possui_comprovante INTEGER DEFAULT 0")
    except Exception:
        pass

    # Compatibilidade: adicionar coluna hash_arquivo em uploads se ausente
    try:
        c.execute("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS hash_arquivo TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ativo'")
    except Exception:
        pass
    
    # 🔧 CORREÇÃO: Adicionar coluna conteudo para armazenar arquivos no banco de dados
    # Isso resolve o problema de arquivos perdidos em sistemas de arquivos efêmeros (Render, Heroku, etc)
    try:
        c.execute("ALTER TABLE uploads ADD COLUMN IF NOT EXISTS conteudo BYTEA")
    except Exception:
        pass

    # Compatibilidade: adicionar coluna nao_possui_comprovante em atestado_horas se ausente
    try:
        c.execute("ALTER TABLE atestado_horas ADD COLUMN IF NOT EXISTS nao_possui_comprovante INTEGER DEFAULT 0")
    except Exception:
        pass

    # Compatibilidade: adicionar colunas ausentes em solicitacoes_ajuste_ponto
    try:
        c.execute("ALTER TABLE solicitacoes_ajuste_ponto ADD COLUMN IF NOT EXISTS aprovador_solicitado TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE solicitacoes_ajuste_ponto ADD COLUMN IF NOT EXISTS data_resposta TIMESTAMP")
    except Exception:
        pass

    # Tabela para auditoria de correções de registros
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS auditoria_correcoes (
            id SERIAL PRIMARY KEY,
            registro_id INTEGER NOT NULL,
            gestor TEXT NOT NULL,
            justificativa TEXT NOT NULL,
            data_correcao TIMESTAMP DEFAULT NOW(),
            FOREIGN KEY (registro_id) REFERENCES registros_ponto (id)
        )
    '''))

    # Tabela horas_extras_ativas para gerenciar solicitações de horas extras
    c.execute(adapt_sql_for_postgresql('''
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
    '''))

    # Adicionar coluna data_hora_nova em solicitacoes_correcao_registro
    try:
        c.execute("ALTER TABLE solicitacoes_correcao_registro ADD COLUMN IF NOT EXISTS data_hora_nova TIMESTAMP")
    except Exception:
        pass

    # ============================================
    # TABELA PARA PUSH NOTIFICATIONS (Web Push)
    # ============================================
    # Armazena as subscriptions dos usuários para enviar notificações push
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT,
            device_info TEXT,
            ativo INTEGER DEFAULT 1,
            data_criacao TIMESTAMP DEFAULT NOW(),
            ultima_notificacao TIMESTAMP,
            falhas_consecutivas INTEGER DEFAULT 0
        )
    '''))
    
    # Índice para busca rápida por usuário
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_push_subscriptions_usuario ON push_subscriptions(usuario)")
    except Exception:
        pass

    # ============================================
    # TABELA PARA HISTÓRICO DE NOTIFICAÇÕES PUSH
    # ============================================
    # Registra todas as notificações enviadas para auditoria
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS push_notifications_log (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            tipo TEXT,
            dados_extras TEXT,
            status TEXT DEFAULT 'enviado',
            erro TEXT,
            data_envio TIMESTAMP DEFAULT NOW()
        )
    '''))

    # ============================================
    # TABELA PARA CONFIGURAÇÃO DE LEMBRETES
    # ============================================
    # Permite personalizar lembretes por usuário
    c.execute(adapt_sql_for_postgresql('''
        CREATE TABLE IF NOT EXISTS config_lembretes_push (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL UNIQUE,
            lembrete_entrada INTEGER DEFAULT 1,
            lembrete_saida INTEGER DEFAULT 1,
            lembrete_hora_extra INTEGER DEFAULT 1,
            horario_lembrete_entrada TIME DEFAULT '08:15',
            horario_lembrete_saida TIME DEFAULT '17:15',
            dias_semana TEXT DEFAULT '1,2,3,4,5',
            data_atualizacao TIMESTAMP DEFAULT NOW()
        )
    '''))

    # ============================================
    # ÍNDICES PARA OTIMIZAÇÃO DE PERFORMANCE
    # ============================================
    # Índices críticos para queries mais frequentes
    indices = [
        # Registros de ponto - consultas por usuário e data são muito frequentes
        ("idx_registros_usuario", "registros_ponto", "usuario"),
        ("idx_registros_data_hora", "registros_ponto", "data_hora"),
        ("idx_registros_usuario_data", "registros_ponto", "usuario, DATE(data_hora)"),
        
        # Usuários - busca por tipo e status
        ("idx_usuarios_tipo_ativo", "usuarios", "tipo, ativo"),
        ("idx_usuarios_usuario", "usuarios", "usuario"),
        
        # Ausências - consultas por usuário, status e data
        ("idx_ausencias_usuario", "ausencias", "usuario"),
        ("idx_ausencias_status", "ausencias", "status"),
        ("idx_ausencias_data", "ausencias", "data_inicio, data_fim"),
        
        # Horas extras - consultas frequentes
        ("idx_he_usuario_status", "solicitacoes_horas_extras", "usuario, status"),
        ("idx_he_aprovador", "solicitacoes_horas_extras", "aprovador_solicitado, status"),
        
        # Notificações - busca por usuário e lidas
        ("idx_notif_usuario_lida", "Notificacoes", "usuario, lida"),
        
        # Banco de horas
        ("idx_banco_horas_usuario", "banco_horas", "usuario"),
        
        # Jornada semanal
        ("idx_jornada_usuario_data", "jornada_semanal", "usuario, data_referencia"),
    ]
    
    for idx_name, table, columns in indices:
        try:
            c.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
        except Exception as e:
            # Ignorar erros de índice já existente ou tabela não existe
            logger.debug(f"Índice {idx_name}: {e}")

    conn.commit()
    return_connection(conn)


if __name__ == '__main__':
    init_db()
