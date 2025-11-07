import os
import sqlite3
from ponto_esa_v5.horas_extras_system import HorasExtrasSystem
from ponto_esa_v5.database import init_db


def test_solicitar_e_aprovar_horas_extras_flow():
    # Preparar DB limpo
    db_path = 'database/ponto_esa.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs('database', exist_ok=True)
    init_db()

    hes = HorasExtrasSystem(db_path=db_path)

    # Criar uma solicitação
    resultado = hes.solicitar_horas_extras(
        usuario='funcionario',
        data='2025-10-13',
        hora_inicio='18:00',
        hora_fim='20:00',
        justificativa='Trabalho extra',
        aprovador_solicitado='gestor'
    )

    assert resultado['success'] is True
    solicitacao_id = resultado['id']

    # Aprovar a solicitação
    resultado_aprovar = hes.aprovar_solicitacao(
        solicitacao_id, 'gestor', observacoes='Ok')
    assert resultado_aprovar['success'] is True
