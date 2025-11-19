"""
Testes Unitários para JornadaSemanalCalculoSystem
Valida cálculos de jornada semanal e detecção de hora extra
"""

import os
import pytest
import sqlite3
import tempfile
from datetime import datetime, date, timedelta, time
from pathlib import Path

# Setup: Usar banco de dados temporário para testes
@pytest.fixture
def temp_db():
    """Cria um banco de dados temporário para testes"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Criar tabelas necessárias
    cursor.execute('''
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            nome_completo TEXT,
            tipo TEXT,
            ativo INTEGER DEFAULT 1,
            jornada_inicio_previsto TEXT DEFAULT '08:00',
            jornada_fim_previsto TEXT DEFAULT '17:00',
            trabalha_seg INTEGER DEFAULT 1,
            jornada_seg_inicio TEXT DEFAULT '08:00',
            jornada_seg_fim TEXT DEFAULT '18:00',
            intervalo_seg INTEGER DEFAULT 60,
            trabalha_ter INTEGER DEFAULT 1,
            jornada_ter_inicio TEXT DEFAULT '08:00',
            jornada_ter_fim TEXT DEFAULT '18:00',
            intervalo_ter INTEGER DEFAULT 60,
            trabalha_qua INTEGER DEFAULT 1,
            jornada_qua_inicio TEXT DEFAULT '08:00',
            jornada_qua_fim TEXT DEFAULT '18:00',
            intervalo_qua INTEGER DEFAULT 60,
            trabalha_qui INTEGER DEFAULT 1,
            jornada_qui_inicio TEXT DEFAULT '08:00',
            jornada_qui_fim TEXT DEFAULT '18:00',
            intervalo_qui INTEGER DEFAULT 60,
            trabalha_sex INTEGER DEFAULT 1,
            jornada_sex_inicio TEXT DEFAULT '08:00',
            jornada_sex_fim TEXT DEFAULT '17:00',
            intervalo_sex INTEGER DEFAULT 60,
            trabalha_sab INTEGER DEFAULT 0,
            jornada_sab_inicio TEXT DEFAULT '08:00',
            jornada_sab_fim TEXT DEFAULT '17:00',
            intervalo_sab INTEGER DEFAULT 60,
            trabalha_dom INTEGER DEFAULT 0,
            jornada_dom_inicio TEXT DEFAULT '08:00',
            jornada_dom_fim TEXT DEFAULT '17:00',
            intervalo_dom INTEGER DEFAULT 60
        )
    ''')
    
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
            data_registro TEXT
        )
    ''')
    
    conn.commit()
    
    yield path
    
    # Limpeza
    conn.close()
    os.unlink(path)


def setup_test_usuario(conn, usuario='teste_user', nome='Usuário Teste'):
    """Insere um usuário de teste no banco"""
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO usuarios 
        (usuario, nome_completo, tipo, ativo, 
         trabalha_seg, jornada_seg_inicio, jornada_seg_fim, intervalo_seg,
         trabalha_ter, jornada_ter_inicio, jornada_ter_fim, intervalo_ter,
         trabalha_qua, jornada_qua_inicio, jornada_qua_fim, intervalo_qua,
         trabalha_qui, jornada_qui_inicio, jornada_qui_fim, intervalo_qui,
         trabalha_sex, jornada_sex_inicio, jornada_sex_fim, intervalo_sex,
         trabalha_sab, jornada_sab_inicio, jornada_sab_fim, intervalo_sab,
         trabalha_dom, jornada_dom_inicio, jornada_dom_fim, intervalo_dom)
        VALUES (?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?)
    ''', (usuario, nome, 'funcionario', 1,
          1, '08:00', '18:00', 60,
          1, '08:00', '18:00', 60,
          1, '08:00', '18:00', 60,
          1, '08:00', '18:00', 60,
          1, '08:00', '17:00', 60,
          0, '08:00', '17:00', 60,
          0, '08:00', '17:00', 60))
    conn.commit()
    return usuario


def setup_test_pontos(conn, usuario, data, pontos_info):
    """
    Insere registros de ponto para teste
    pontos_info: lista de tuples (tipo, hora) ex: [('Início', '08:00'), ('Fim', '18:30')]
    """
    cursor = conn.cursor()
    for tipo, hora in pontos_info:
        data_hora = f"{data} {hora}:00"
        cursor.execute('''
            INSERT INTO registros_ponto
            (usuario, data_hora, tipo, modalidade, projeto, atividade, data_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (usuario, data_hora, tipo, 'Presencial', 'Teste', 'Teste', data))
    conn.commit()


class TestJornadaSemanalCalculoSystem:
    """Testes para o sistema de cálculo de jornada"""
    
    def test_calcular_horas_esperadas_dia_normal(self, temp_db):
        """Testa cálculo de horas esperadas em um dia normal (segunda)"""
        # Patch do banco de dados temporário
        import sys
        from unittest.mock import patch
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        # Importar após adicionar ao path
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        from jornada_semanal_system import obter_jornada_usuario
        
        conn = sqlite3.connect(temp_db)
        setup_test_usuario(conn, 'teste_user')
        conn.close()
        
        # Mock das funções de conexão
        with patch('jornada_semanal_calculo_system.get_connection') as mock_conn:
            mock_db = sqlite3.connect(temp_db)
            mock_conn.return_value = mock_db
            
            with patch('jornada_semanal_calculo_system.SQL_PLACEHOLDER', '?'):
                # Test: Segunda-feira (dia 0)
                test_date = date(2024, 11, 18)  # Segunda-feira
                
                resultado = JornadaSemanalCalculoSystem.calcular_horas_esperadas_dia(
                    'teste_user',
                    test_date
                )
                
                # Segunda: 08:00-18:00 (10h) - 60min intervalo = 9h
                assert resultado['trabalha'] == True
                assert resultado['horas_esperadas'] == 9.0
                assert resultado['horas_esperadas_minutos'] == 540  # 9 * 60
                assert resultado['intervalo_minutos'] == 60
    
    def test_calcular_horas_registradas_dia_com_pontos(self, temp_db):
        """Testa cálculo de horas registradas quando há pontos"""
        import sys
        from unittest.mock import patch
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        
        conn = sqlite3.connect(temp_db)
        usuario = setup_test_usuario(conn, 'teste_user')
        
        # Adicionar pontos: Início às 08:00, Fim às 18:30
        test_date = '2024-11-18'
        setup_test_pontos(conn, usuario, test_date, [
            ('Início', '08:00'),
            ('Fim', '18:30')
        ])
        conn.close()
        
        with patch('jornada_semanal_calculo_system.get_connection') as mock_conn:
            mock_db = sqlite3.connect(temp_db)
            mock_conn.return_value = mock_db
            
            with patch('jornada_semanal_calculo_system.SQL_PLACEHOLDER', '?'):
                teste_date_obj = date(2024, 11, 18)
                
                resultado = JornadaSemanalCalculoSystem.calcular_horas_registradas_dia(
                    usuario,
                    teste_date_obj
                )
                
                # 08:00 a 18:30 = 10h 30min = 630 min
                # 630 - 60 (intervalo) = 570 min = 9.5h
                assert resultado['trabalha'] == True
                assert resultado['horas_registradas'] == 9.5
                assert resultado['horas_registradas_minutos'] == 570
    
    def test_detectar_hora_extra_positiva(self, temp_db):
        """Testa detecção de hora extra quando há excesso de horas"""
        import sys
        from unittest.mock import patch
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        
        conn = sqlite3.connect(temp_db)
        usuario = setup_test_usuario(conn, 'teste_user')
        
        # Adicionar pontos: Início 08:00, Fim 20:00 (12h)
        # Esperado: 9h (08:00-18:00 menos 60min intervalo)
        # Registrado: 11h (08:00-20:00 menos 60min intervalo)
        # Hora Extra: 2h
        test_date = '2024-11-18'
        setup_test_pontos(conn, usuario, test_date, [
            ('Início', '08:00'),
            ('Fim', '20:00')
        ])
        conn.close()
        
        with patch('jornada_semanal_calculo_system.get_connection') as mock_conn:
            mock_db = sqlite3.connect(temp_db)
            mock_conn.return_value = mock_db
            
            with patch('jornada_semanal_calculo_system.SQL_PLACEHOLDER', '?'):
                teste_date_obj = date(2024, 11, 18)
                
                resultado = JornadaSemanalCalculoSystem.detectar_hora_extra_dia(
                    usuario,
                    teste_date_obj,
                    tolerancia_minutos=5
                )
                
                assert resultado['tem_hora_extra'] == True
                assert resultado['horas_extra'] == 2.0
                assert resultado['minutos_extra'] == 120
                assert resultado['categoria'] == 'hora_extra'
    
    def test_detectar_hora_extra_nenhuma(self, temp_db):
        """Testa quando não há hora extra"""
        import sys
        from unittest.mock import patch
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        
        conn = sqlite3.connect(temp_db)
        usuario = setup_test_usuario(conn, 'teste_user')
        
        # Adicionar pontos: Início 08:00, Fim 17:00 (exatamente como esperado, mais 60min intervalo = 8h)
        test_date = '2024-11-18'
        setup_test_pontos(conn, usuario, test_date, [
            ('Início', '08:00'),
            ('Fim', '18:00')
        ])
        conn.close()
        
        with patch('jornada_semanal_calculo_system.get_connection') as mock_conn:
            mock_db = sqlite3.connect(temp_db)
            mock_conn.return_value = mock_db
            
            with patch('jornada_semanal_calculo_system.SQL_PLACEHOLDER', '?'):
                teste_date_obj = date(2024, 11, 18)
                
                resultado = JornadaSemanalCalculoSystem.detectar_hora_extra_dia(
                    usuario,
                    teste_date_obj
                )
                
                assert resultado['tem_hora_extra'] == False
                assert resultado['horas_extra'] == 0.0
                assert resultado['categoria'] == 'dentro_jornada'
    
    def test_validar_ponto_dia_nao_trabalha(self, temp_db):
        """Testa validação de ponto em dia que não trabalha (domingo)"""
        import sys
        from unittest.mock import patch
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        
        conn = sqlite3.connect(temp_db)
        usuario = setup_test_usuario(conn, 'teste_user')
        conn.close()
        
        with patch('jornada_semanal_calculo_system.get_connection') as mock_conn:
            mock_db = sqlite3.connect(temp_db)
            mock_conn.return_value = mock_db
            
            with patch('jornada_semanal_calculo_system.SQL_PLACEHOLDER', '?'):
                # Domingo (19/11/2024)
                teste_date = date(2024, 11, 19)
                
                resultado = JornadaSemanalCalculoSystem.validar_ponto_contra_jornada(
                    usuario,
                    teste_date,
                    'Início'
                )
                
                assert resultado['valido'] == False
                assert 'não trabalha' in resultado['mensagem'].lower()
                assert resultado['categoria'] == 'nao_trabalha_dia'
    
    def test_obter_tempo_ate_fim_jornada(self, temp_db):
        """Testa cálculo de tempo até fim da jornada"""
        import sys
        from unittest.mock import patch
        
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        
        conn = sqlite3.connect(temp_db)
        usuario = setup_test_usuario(conn, 'teste_user')
        conn.close()
        
        with patch('jornada_semanal_calculo_system.get_connection') as mock_conn:
            mock_db = sqlite3.connect(temp_db)
            mock_conn.return_value = mock_db
            
            with patch('jornada_semanal_calculo_system.SQL_PLACEHOLDER', '?'):
                # Mock do datetime para controlar "agora"
                with patch('jornada_semanal_calculo_system.datetime') as mock_datetime:
                    # Simular: Segunda-feira às 17:00 (1h antes do fim que é 18:00)
                    mock_now = datetime(2024, 11, 18, 17, 0, 0)
                    mock_datetime.now.return_value = mock_now
                    mock_datetime.combine = datetime.combine
                    
                    resultado = JornadaSemanalCalculoSystem.obter_tempo_ate_fim_jornada(
                        usuario,
                        date(2024, 11, 18),
                        margem_minutos=5
                    )
                    
                    assert resultado['minutos_restantes'] == 60  # 1h = 60 min
                    assert resultado['horario_fim'] == '18:00'
                    assert resultado['dentro_margem'] == False  # 60 > 5
                    assert resultado['status'] == 'longe'


if __name__ == '__main__':
    # Executar testes
    pytest.main([__file__, '-v'])
