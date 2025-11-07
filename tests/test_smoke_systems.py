import os
import sqlite3
from ponto_esa_v5.horas_extras_system import HorasExtrasSystem
from ponto_esa_v5.upload_system import UploadSystem
from ponto_esa_v5.banco_horas_system import BancoHorasSystem
from ponto_esa_v5.database import init_db

# Garantir que o DB e diretório existem para os testes smoke
os.makedirs('database', exist_ok=True)
db_path = 'database/ponto_esa.db'
# Remover DB existente para garantir esquema limpo durante testes
if os.path.exists(db_path):
    try:
        os.remove(db_path)
    except Exception:
        pass

init_db()


def test_horas_extras_import_and_check():
    hes = HorasExtrasSystem(db_path='database/ponto_esa.db')
    # Apenas chamar método de verificação sem exigir usuário existente
    resp = hes.verificar_fim_jornada('usuario_inexistente')
    assert isinstance(resp, dict)
    assert 'deve_notificar' in resp


def test_uploadsystem_init_and_save_temp():
    # Usar um DB temporário
    os.makedirs('uploads/temp', exist_ok=True)
    us = UploadSystem(db_path='database/ponto_esa.db', upload_dir='uploads')
    # Testar geração de nome seguro
    safe = us.generate_safe_filename('teste.pdf')
    assert safe.endswith('.pdf')


def test_banco_horas_init_and_calc():
    # Se não existir DB principal, criar um mínimo
    if not os.path.exists('database/ponto_esa.db'):
        os.makedirs('database', exist_ok=True)
        conn = sqlite3.connect('database/ponto_esa.db')
        cursor = conn.cursor()
        # criar tabelas mínimas
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT, nome_completo TEXT, jornada_inicio_previsto TIME, jornada_fim_previsto TIME, ativo INTEGER)''')
        cursor.execute(
            '''CREATE TABLE IF NOT EXISTS registros_ponto (usuario TEXT, data_hora TEXT)''')
        conn.commit()
        conn.close()

    bs = BancoHorasSystem(db_path='database/ponto_esa.db')
    # chamada básica que não deve estourar
    resultado = bs.calcular_banco_horas(
        'usuario_inexistente', '2025-10-01', '2025-10-31')
    assert isinstance(resultado, dict)
    assert 'success' in resultado
