"""
Database PostgreSQL para Render.com
Migração do SQLite para PostgreSQL
"""
# Import psycopg2 if available; otherwise fallback to None so code can handle missing dependency.
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None

import os
from datetime import datetime
import hashlib

class DatabasePostgres:
    def __init__(self):
        """Inicializa conexão com PostgreSQL usando variável de ambiente DATABASE_URL do Render"""
        self.database_url = os.environ.get('DATABASE_URL')
        self.conn = None
        self.use_sqlite = False
        self.sqlite_db = None

        # Se a dependência psycopg2 não estiver disponível, força fallback para SQLite local
        if psycopg2 is None:
            print("⚠️ psycopg2 não encontrado; usando SQLite local para desenvolvimento.")
            try:
                import database
                # assume database.Database existe no módulo local de fallback
                self.sqlite_db = getattr(database, 'Database')() if hasattr(database, 'Database') else None
                self.use_sqlite = True
            except Exception:
                # If even local fallback fails, keep use_sqlite False and let errors surface later
                pass

    def get_connection(self):
        """Retorna conexão com PostgreSQL"""
        # se estamos em fallback para sqlite ou psycopg2 não está presente, não cria conexão pg
        if self.use_sqlite or psycopg2 is None:
            return None

        if self.conn is None or getattr(self.conn, 'closed', True):
            # Use RealDictCursor only if it was imported successfully
            if RealDictCursor is not None:
                self.conn = psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
            else:
                self.conn = psycopg2.connect(self.database_url)
        return self.conn

    def _row_to_dict(self, row, cursor):
        """Converte uma linha retornada pelo cursor em dict, independente do cursor_factory."""
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        # cursor.description é seq de tuples, nome da coluna em [0]
        if cursor is not None and cursor.description:
            return {col[0]: val for col, val in zip(cursor.description, row)}
        # fallback: return as-is in a dict with numeric keys
        return {str(i): v for i, v in enumerate(row)}

    def _rows_to_dicts(self, rows, cursor):
        return [self._row_to_dict(r, cursor) for r in rows] if rows else []

    def _create_tables(self):
        """Cria todas as tabelas necessárias no PostgreSQL"""
        if self.use_sqlite:
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        # Tabela de usuários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                usuario VARCHAR(100) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL,
                tipo VARCHAR(50) NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de registros de ponto
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registros_ponto (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id),
                data DATE NOT NULL,
                hora TIME NOT NULL,
                tipo VARCHAR(50) NOT NULL,
                latitude DECIMAL(10, 8),
                longitude DECIMAL(11, 8),
                observacao TEXT,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de ausências
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ausencias (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id),
                tipo VARCHAR(100) NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE NOT NULL,
                motivo TEXT,
                arquivo_url VARCHAR(500),
                status VARCHAR(50) DEFAULT 'pendente',
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de atestados de horas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS atestados_horas (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id),
                data DATE NOT NULL,
                projeto VARCHAR(255),
                atividade VARCHAR(255),
                horas_trabalhadas DECIMAL(5, 2),
                descricao TEXT,
                arquivo_url VARCHAR(500),
                status VARCHAR(50) DEFAULT 'pendente',
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        cursor.close()

        # Criar usuário admin padrão se não existir
        self._create_default_users()

    def _create_default_users(self):
        """Cria usuários padrão (gestor e funcionário)"""
        if self.use_sqlite:
            return

        conn = self.get_connection()
        cursor = conn.cursor()

        # Verificar se já existe usuário
        cursor.execute("SELECT COUNT(*) as count FROM usuarios")
        result = cursor.fetchone()
        row = self._row_to_dict(result, cursor)

        if row and row.get('count', 0) == 0:
            # Criar gestor
            senha_gestor = hashlib.sha256("senha_gestor_123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO usuarios (nome, usuario, senha, tipo, ativo)
                VALUES (%s, %s, %s, %s, %s)
            """, ("Gestor Padrão", "gestor", senha_gestor, "gestor", True))

            # Criar funcionário
            senha_func = hashlib.sha256("senha_func_123".encode()).hexdigest()
            cursor.execute("""
                INSERT INTO usuarios (nome, usuario, senha, tipo, ativo)
                VALUES (%s, %s, %s, %s, %s)
            """, ("Funcionário Teste", "funcionario", senha_func, "funcionario", True))

            conn.commit()
            print("✅ Usuários padrão criados com sucesso!")

        cursor.close()

    # Métodos de autenticação
    def verificar_login(self, usuario, senha):
        """Verifica credenciais do usuário"""
        if self.use_sqlite and self.sqlite_db is not None:
            return self.sqlite_db.verificar_login(usuario, senha)

        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, nome, usuario, tipo, ativo
            FROM usuarios
            WHERE usuario = %s AND senha = %s AND ativo = TRUE
        """, (usuario, senha_hash))

        result = cursor.fetchone()
        row = self._row_to_dict(result, cursor)
        cursor.close()

        return row

    # Métodos de registro de ponto
    def registrar_ponto(self, usuario_id, tipo, latitude=None, longitude=None, observacao=None):
        """Registra ponto do funcionário"""
        if self.use_sqlite and self.sqlite_db is not None:
            return self.sqlite_db.registrar_ponto(usuario_id, tipo, latitude, longitude, observacao)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO registros_ponto (usuario_id, data, hora, tipo, latitude, longitude, observacao)
            VALUES (%s, CURRENT_DATE, CURRENT_TIME, %s, %s, %s, %s)
            RETURNING id
        """, (usuario_id, tipo, latitude, longitude, observacao))

        result = cursor.fetchone()
        conn.commit()
        row = self._row_to_dict(result, cursor)
        cursor.close()

        return row.get('id') if row else None

    def obter_registros_dia(self, usuario_id, data=None):
        """Obtém registros de ponto de um dia específico"""
        if self.use_sqlite and self.sqlite_db is not None:
            return self.sqlite_db.obter_registros_dia(usuario_id, data)

        if data is None:
            data = datetime.now().date()

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM registros_ponto
            WHERE usuario_id = %s AND data = %s
            ORDER BY hora
        """, (usuario_id, data))

        results = cursor.fetchall()
        rows = self._rows_to_dicts(results, cursor)
        cursor.close()

        return rows

    # Métodos de ausências
    def registrar_ausencia(self, usuario_id, tipo, data_inicio, data_fim, motivo, arquivo_url=None):
        """Registra ausência do funcionário"""
        if self.use_sqlite and self.sqlite_db is not None:
            return self.sqlite_db.registrar_ausencia(usuario_id, tipo, data_inicio, data_fim, motivo, arquivo_url)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ausencias (usuario_id, tipo, data_inicio, data_fim, motivo, arquivo_url, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pendente')
            RETURNING id
        """, (usuario_id, tipo, data_inicio, data_fim, motivo, arquivo_url))

        result = cursor.fetchone()
        conn.commit()
        row = self._row_to_dict(result, cursor)
        cursor.close()

        return row.get('id') if row else None

    def obter_ausencias_usuario(self, usuario_id):
        """Obtém todas as ausências de um usuário"""
        if self.use_sqlite and self.sqlite_db is not None:
            return self.sqlite_db.obter_ausencias_usuario(usuario_id)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM ausencias
            WHERE usuario_id = %s
            ORDER BY data_inicio DESC
        """, (usuario_id,))

        results = cursor.fetchall()
        rows = self._rows_to_dicts(results, cursor)
        cursor.close()

        return rows

    # Métodos de atestados de horas
    def registrar_atestado_horas(self, usuario_id, data, projeto, atividade, horas, descricao, arquivo_url=None):
        """Registra atestado de horas trabalhadas"""
        if self.use_sqlite and self.sqlite_db is not None:
            return self.sqlite_db.registrar_atestado_horas(usuario_id, data, projeto, atividade, horas, descricao, arquivo_url)

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO atestados_horas (usuario_id, data, projeto, atividade, horas_trabalhadas, descricao, arquivo_url, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pendente')
            RETURNING id
        """, (usuario_id, data, projeto, atividade, horas, descricao, arquivo_url))

        result = cursor.fetchone()
        conn.commit()
        row = self._row_to_dict(result, cursor)
        cursor.close()

        return row.get('id') if row else None

    def obter_todos_usuarios(self):
        """Obtém lista de todos os usuários"""
        if self.use_sqlite and self.sqlite_db is not None:
            return self.sqlite_db.obter_todos_usuarios()

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, nome, usuario, tipo, ativo, data_cadastro
            FROM usuarios
            ORDER BY nome
        """)

        results = cursor.fetchall()
        rows = self._rows_to_dicts(results, cursor)
        cursor.close()

        return rows

    def __del__(self):
        """Fecha conexão ao destruir objeto"""
        if hasattr(self, 'conn') and self.conn and not getattr(self.conn, 'closed', False):
            try:
                self.conn.close()
            except Exception:
                pass

# Instância global
db = DatabasePostgres()
