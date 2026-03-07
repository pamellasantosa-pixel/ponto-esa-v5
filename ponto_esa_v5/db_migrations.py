"""
Sistema de Migração de Banco de Dados — Ponto ExSA v5.

Fornece versionamento incremental do schema com:
- Controle de versão por tabela `db_migrations`
- Aplicação sequencial de migrações
- Rollback seguro (quando possível) sem perda de dados
- Registro de cada migração aplicada com timestamp

Uso:
    from db_migrations import run_pending_migrations
    run_pending_migrations()  # aplica todas as migrações pendentes
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================
# REGISTRO DE MIGRAÇÕES
# =============================================
# Cada migração é uma tupla: (version, description, up_sql_list, down_sql_list)
# up_sql_list: lista de comandos SQL para aplicar
# down_sql_list: lista de comandos SQL para reverter (pode ser vazia se irreversível)

MIGRATIONS: list[tuple[int, str, list[str], list[str]]] = [
    (
        1,
        "Criar tabela db_migrations para controle de versão",
        [
            """
            CREATE TABLE IF NOT EXISTS db_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT NOW(),
                rolled_back_at TIMESTAMP
            )
            """,
        ],
        [],  # Irreversível — a tabela de migração é o próprio sistema
    ),
    (
        2,
        "Adicionar campos CPF e data_nascimento em usuarios",
        [
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS cpf TEXT",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS data_nascimento DATE",
        ],
        [
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS data_nascimento",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS cpf",
        ],
    ),
    (
        3,
        "Adicionar campos GPS em registros_ponto",
        [
            "ALTER TABLE registros_ponto ADD COLUMN IF NOT EXISTS latitude REAL",
            "ALTER TABLE registros_ponto ADD COLUMN IF NOT EXISTS longitude REAL",
        ],
        [
            "ALTER TABLE registros_ponto DROP COLUMN IF EXISTS longitude",
            "ALTER TABLE registros_ponto DROP COLUMN IF EXISTS latitude",
        ],
    ),
    (
        4,
        "Adicionar coluna nao_possui_comprovante em ausencias",
        [
            "ALTER TABLE ausencias ADD COLUMN IF NOT EXISTS nao_possui_comprovante INTEGER DEFAULT 0",
        ],
        [
            "ALTER TABLE ausencias DROP COLUMN IF EXISTS nao_possui_comprovante",
        ],
    ),
    (
        5,
        "Adicionar colunas de jornada prevista em usuarios",
        [
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_inicio_previsto TIME DEFAULT '08:00'",
            "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_fim_previsto TIME DEFAULT '17:00'",
        ],
        [
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS jornada_fim_previsto",
            "ALTER TABLE usuarios DROP COLUMN IF EXISTS jornada_inicio_previsto",
        ],
    ),
    (
        6,
        "Adicionar colunas de upload: hash_arquivo, status, conteudo BYTEA",
        [
            "ALTER TABLE uploads ADD COLUMN IF NOT EXISTS hash_arquivo TEXT",
            "ALTER TABLE uploads ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ativo'",
            "ALTER TABLE uploads ADD COLUMN IF NOT EXISTS conteudo BYTEA",
        ],
        [
            "ALTER TABLE uploads DROP COLUMN IF EXISTS conteudo",
            "ALTER TABLE uploads DROP COLUMN IF EXISTS status",
            "ALTER TABLE uploads DROP COLUMN IF EXISTS hash_arquivo",
        ],
    ),
    (
        7,
        "Adicionar total_horas em solicitacoes_horas_extras",
        [
            "ALTER TABLE solicitacoes_horas_extras ADD COLUMN IF NOT EXISTS total_horas REAL",
        ],
        [
            "ALTER TABLE solicitacoes_horas_extras DROP COLUMN IF EXISTS total_horas",
        ],
    ),
    (
        8,
        "Adicionar colunas em solicitacoes_ajuste_ponto",
        [
            "ALTER TABLE solicitacoes_ajuste_ponto ADD COLUMN IF NOT EXISTS aprovador_solicitado TEXT",
            "ALTER TABLE solicitacoes_ajuste_ponto ADD COLUMN IF NOT EXISTS data_resposta TIMESTAMP",
        ],
        [
            "ALTER TABLE solicitacoes_ajuste_ponto DROP COLUMN IF EXISTS data_resposta",
            "ALTER TABLE solicitacoes_ajuste_ponto DROP COLUMN IF EXISTS aprovador_solicitado",
        ],
    ),
    (
        9,
        "Adicionar data_hora_nova em solicitacoes_correcao_registro",
        [
            "ALTER TABLE solicitacoes_correcao_registro ADD COLUMN IF NOT EXISTS data_hora_nova TIMESTAMP",
        ],
        [
            "ALTER TABLE solicitacoes_correcao_registro DROP COLUMN IF EXISTS data_hora_nova",
        ],
    ),
    (
        10,
        "Adicionar nao_possui_comprovante em atestado_horas",
        [
            "ALTER TABLE atestado_horas ADD COLUMN IF NOT EXISTS nao_possui_comprovante INTEGER DEFAULT 0",
        ],
        [
            "ALTER TABLE atestado_horas DROP COLUMN IF EXISTS nao_possui_comprovante",
        ],
    ),
    (
        11,
        "Criar índices de performance para consultas frequentes",
        [
            "CREATE INDEX IF NOT EXISTS idx_registros_usuario ON registros_ponto(usuario)",
            "CREATE INDEX IF NOT EXISTS idx_registros_data_hora ON registros_ponto(data_hora)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_tipo_ativo ON usuarios(tipo, ativo)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_usuario ON usuarios(usuario)",
            "CREATE INDEX IF NOT EXISTS idx_ausencias_usuario ON ausencias(usuario)",
            "CREATE INDEX IF NOT EXISTS idx_ausencias_status ON ausencias(status)",
            "CREATE INDEX IF NOT EXISTS idx_he_usuario_status ON solicitacoes_horas_extras(usuario, status)",
            "CREATE INDEX IF NOT EXISTS idx_he_aprovador ON solicitacoes_horas_extras(aprovador_solicitado, status)",
            "CREATE INDEX IF NOT EXISTS idx_banco_horas_usuario ON banco_horas(usuario)",
            "CREATE INDEX IF NOT EXISTS idx_push_subscriptions_usuario ON push_subscriptions(usuario)",
        ],
        [
            "DROP INDEX IF EXISTS idx_registros_usuario",
            "DROP INDEX IF EXISTS idx_registros_data_hora",
            "DROP INDEX IF EXISTS idx_usuarios_tipo_ativo",
            "DROP INDEX IF EXISTS idx_usuarios_usuario",
            "DROP INDEX IF EXISTS idx_ausencias_usuario",
            "DROP INDEX IF EXISTS idx_ausencias_status",
            "DROP INDEX IF EXISTS idx_he_usuario_status",
            "DROP INDEX IF EXISTS idx_he_aprovador",
            "DROP INDEX IF EXISTS idx_banco_horas_usuario",
            "DROP INDEX IF EXISTS idx_push_subscriptions_usuario",
        ],
    ),
]


def _ensure_migrations_table(conn) -> None:
    """Cria a tabela de migrações se não existir."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT NOW(),
            rolled_back_at TIMESTAMP
        )
    """)
    conn.commit()


def get_applied_versions(conn) -> set[int]:
    """Retorna o conjunto de versões já aplicadas (excluindo revertidas)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT version FROM db_migrations WHERE rolled_back_at IS NULL"
    )
    return {row[0] for row in cursor.fetchall()}


def run_pending_migrations(conn=None) -> list[int]:
    """Aplica todas as migrações pendentes em ordem sequencial.

    Args:
        conn: conexão de banco de dados existente (opcional).
              Se None, obtém uma nova via database.get_connection().

    Returns:
        Lista de versões aplicadas nesta execução.
    """
    from database import get_connection, return_connection

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    applied: list[int] = []
    try:
        _ensure_migrations_table(conn)
        already_applied = get_applied_versions(conn)

        for version, description, up_sqls, _down_sqls in MIGRATIONS:
            if version in already_applied:
                continue
            try:
                cursor = conn.cursor()
                for sql in up_sqls:
                    cursor.execute(sql.strip())
                cursor.execute(
                    "INSERT INTO db_migrations (version, description) VALUES (%s, %s)",
                    (version, description),
                )
                conn.commit()
                applied.append(version)
                logger.info("Migration v%d aplicada: %s", version, description)
            except Exception as e:
                conn.rollback()
                logger.error("Migration v%d falhou: %s", version, e)
                # Parar na primeira falha para manter consistência
                break
    finally:
        if own_conn:
            return_connection(conn)

    if applied:
        logger.info("Migrações aplicadas: %s", applied)
    else:
        logger.debug("Nenhuma migração pendente.")

    return applied


def rollback_migration(version: int, conn=None) -> bool:
    """Reverte uma migração específica.

    Args:
        version: número da versão a reverter.
        conn: conexão existente (opcional).

    Returns:
        True se a reversão foi bem-sucedida, False caso contrário.
    """
    from database import get_connection, return_connection

    migration = None
    for v, desc, _up, down in MIGRATIONS:
        if v == version:
            migration = (v, desc, down)
            break

    if migration is None:
        logger.error("Migration v%d não encontrada.", version)
        return False

    v, desc, down_sqls = migration
    if not down_sqls:
        logger.error("Migration v%d não suporta rollback.", version)
        return False

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    try:
        cursor = conn.cursor()
        for sql in down_sqls:
            cursor.execute(sql.strip())
        cursor.execute(
            "UPDATE db_migrations SET rolled_back_at = NOW() WHERE version = %s",
            (version,),
        )
        conn.commit()
        logger.info("Migration v%d revertida: %s", version, desc)
        return True
    except Exception as e:
        conn.rollback()
        logger.error("Rollback v%d falhou: %s", version, e)
        return False
    finally:
        if own_conn:
            return_connection(conn)


def get_migration_status(conn=None) -> list[dict]:
    """Retorna o status de todas as migrações.

    Returns:
        Lista de dicts com version, description, status, applied_at.
    """
    from database import get_connection, return_connection

    own_conn = conn is None
    if own_conn:
        conn = get_connection()

    try:
        _ensure_migrations_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version, description, applied_at, rolled_back_at FROM db_migrations ORDER BY version"
        )
        applied = {row[0]: row for row in cursor.fetchall()}

        result = []
        for version, description, _up, _down in MIGRATIONS:
            row = applied.get(version)
            if row and row[3] is None:
                status = "applied"
                applied_at = row[2]
            elif row and row[3] is not None:
                status = "rolled_back"
                applied_at = row[2]
            else:
                status = "pending"
                applied_at = None
            result.append({
                "version": version,
                "description": description,
                "status": status,
                "applied_at": applied_at,
            })
        return result
    finally:
        if own_conn:
            return_connection(conn)
