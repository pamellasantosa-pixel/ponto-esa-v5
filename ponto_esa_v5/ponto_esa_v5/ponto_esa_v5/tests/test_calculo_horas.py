import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from ponto_esa_v5.calculo_horas_system import CalculoHorasSystem


def setup_temp_db():
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # criar tabelas mínimas necessárias
    cursor.execute('''
        CREATE TABLE registros_ponto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            data_hora TEXT,
            tipo TEXT,
            modalidade TEXT,
            projeto TEXT,
            atividade TEXT,
            localizacao TEXT,
            latitude REAL,
            longitude REAL,
            registro TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE atestado_horas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT,
            data TEXT,
            hora_inicio TEXT,
            hora_fim TEXT,
            total_horas REAL,
            status TEXT
        )
    ''')

    conn.commit()
    conn.close()
    return path


def test_calcular_horas_dia_sem_registros():
    db_path = setup_temp_db()
    try:
        ch = CalculoHorasSystem(db_path)
        resultado = ch.calcular_horas_dia('user1', '2025-10-13')
        assert isinstance(resultado, dict)
        assert resultado['horas_finais'] == 0
        assert 'primeiro_registro' in resultado and 'ultimo_registro' in resultado
        assert resultado['total_registros'] == 0
    finally:
        os.remove(db_path)


def test_calcular_horas_dia_com_registros():
    db_path = setup_temp_db()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # inserir dois registros (início e fim)
        dt_inicio = datetime(2025, 10, 13, 8, 0, 0)
        dt_fim = datetime(2025, 10, 13, 17, 0, 0)
        cursor.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
                       ('user1', dt_inicio.strftime('%Y-%m-%d %H:%M:%S'), 'Início'))
        cursor.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
                       ('user1', dt_fim.strftime('%Y-%m-%d %H:%M:%S'), 'Fim'))
        conn.commit()
        conn.close()

        ch = CalculoHorasSystem(db_path)
        resultado = ch.calcular_horas_dia('user1', '2025-10-13')
        assert resultado['total_registros'] == 2
        assert round(resultado['horas_trabalhadas']) == 9  # 9 horas brutas
        assert resultado['desconto_almoco'] == 1
        assert round(resultado['horas_liquidas']) == 8
        assert 'horas_finais' in resultado
        assert resultado['horas_finais'] >= 0
    finally:
        os.remove(db_path)


def test_calcular_horas_periodo():
    db_path = setup_temp_db()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # inserir registros em 2 dias
        dt1_inicio = datetime(2025, 10, 13, 8, 0, 0)
        dt1_fim = datetime(2025, 10, 13, 17, 0, 0)
        dt2_inicio = datetime(2025, 10, 14, 8, 0, 0)
        dt2_fim = datetime(2025, 10, 14, 17, 0, 0)
        cursor.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
                       ('user1', dt1_inicio.strftime('%Y-%m-%d %H:%M:%S'), 'Início'))
        cursor.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
                       ('user1', dt1_fim.strftime('%Y-%m-%d %H:%M:%S'), 'Fim'))
        cursor.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
                       ('user1', dt2_inicio.strftime('%Y-%m-%d %H:%M:%S'), 'Início'))
        cursor.execute("INSERT INTO registros_ponto (usuario, data_hora, tipo) VALUES (?, ?, ?)",
                       ('user1', dt2_fim.strftime('%Y-%m-%d %H:%M:%S'), 'Fim'))
        conn.commit()
        conn.close()

        ch = CalculoHorasSystem(db_path)
        resultado = ch.calcular_horas_periodo(
            'user1', '2025-10-13', '2025-10-14')
        assert 'total_horas' in resultado
        assert resultado['dias_trabalhados'] == 2
        assert len(resultado['detalhes_por_dia']) == 2
    finally:
        os.remove(db_path)
