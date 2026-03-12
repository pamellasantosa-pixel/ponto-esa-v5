import sqlite3
from datetime import datetime

import ponto_esa_v5.ajuste_registros_system as ajuste_mod
from ponto_esa_v5.ajuste_registros_system import AjusteRegistrosSystem


def test_registra_auditoria_com_registro_id_e_justificativa_padrao():
    ajuste_mod.SQL_PLACEHOLDER = "?"

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE auditoria_alteracoes_ponto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registro_id INTEGER,
            usuario_afetado TEXT NOT NULL,
            data_registro TEXT NOT NULL,
            entrada_original TEXT,
            saida_original TEXT,
            entrada_corrigida TEXT,
            saida_corrigida TEXT,
            tipo_alteracao TEXT NOT NULL,
            realizado_por TEXT NOT NULL,
            data_alteracao TEXT,
            justificativa TEXT,
            detalhes TEXT
        )
        """
    )

    # Evita executar __init__ (que valida conexao global).
    sistema = AjusteRegistrosSystem.__new__(AjusteRegistrosSystem)
    sistema._now = lambda: datetime(2026, 3, 11, 12, 0, 0)

    sistema._registrar_auditoria_alteracao_cursor(
        cursor=cursor,
        registro_id=123,
        usuario_afetado="funcionario1",
        data_registro="2026-03-10",
        entrada_original="08:00",
        saida_original="17:00",
        entrada_corrigida="08:15",
        saida_corrigida="17:10",
        tipo_alteracao="correcao_registro_manual",
        realizado_por="gestor1",
        justificativa=None,
        detalhes="ajuste de teste",
    )
    conn.commit()

    cursor.execute(
        """
        SELECT registro_id, usuario_afetado, data_registro, justificativa, tipo_alteracao
        FROM auditoria_alteracoes_ponto
        """
    )
    row = cursor.fetchone()

    assert row is not None
    assert row[0] == 123
    assert row[1] == "funcionario1"
    assert row[2] == "2026-03-10"
    assert row[3] == "Sem justificativa informada"
    assert row[4] == "correcao_registro_manual"
