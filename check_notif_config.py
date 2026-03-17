#!/usr/bin/env python3
"""Check notification configuration in database."""
import os

# Try PostgreSQL first
try:
    import psycopg2
    from psycopg2 import sql
    
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print("Conectando ao PostgreSQL...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check notification configs
        cursor.execute('SELECT chave, valor FROM configuracoes WHERE chave ILIKE %s ORDER BY chave', ('notif_%',))
        rows = cursor.fetchall()
        
        print('=== Configurações de Notificação ===')
        for chave, valor in rows:
            print(f'{chave}: {valor}')
        
        # Also check push_subscriptions data
        cursor.execute('SELECT usuario, horario_entrada, horario_almoco_saida, horario_almoco_retorno, horario_saida FROM push_subscriptions LIMIT 10')
        rows = cursor.fetchall()
        print('\n=== Horários cadastrados (primeiros 10) ===')
        for row in rows:
            print(f'{row[0]}: entrada={row[1]}, almoço_saída={row[2]}, almoço_retorno={row[3]}, saída={row[4]}')
        
        cursor.close()
        conn.close()
    else:
        print("DATABASE_URL não definido, tentando SQLite...")
        import sqlite3
        db_path = 'database/ponto_esa.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check notification configs
        cursor.execute('SELECT chave, valor FROM configuracoes WHERE chave LIKE "notif_%" ORDER BY chave')
        rows = cursor.fetchall()
        
        print('=== Configurações de Notificação ===')
        for chave, valor in rows:
            print(f'{chave}: {valor}')
        
        cursor.close()
        conn.close()
        
except Exception as e:
    print(f"Erro: {e}")
    import traceback
    traceback.print_exc()
