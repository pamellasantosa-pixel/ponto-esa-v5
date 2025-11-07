"""Script de setup do banco de dados mínimo para desenvolvimento

Uso:
    python tools/setup_db.py [--recreate]

Se --recreate for passado, o arquivo 'database/ponto_esa.db' será removido e recriado.
"""
import os
import argparse
from ..database import init_db

parser = argparse.ArgumentParser()
parser.add_argument('--recreate', action='store_true',
                    help='Remove e recria o banco de dados')
args = parser.parse_args()

DB_PATH = 'database/ponto_esa.db'

if args.recreate:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print('Arquivo de banco removido')

os.makedirs('database', exist_ok=True)
init_db()
print('Banco inicializado com sucesso. Usuários e projetos padrão foram inseridos se estavam ausentes.')
