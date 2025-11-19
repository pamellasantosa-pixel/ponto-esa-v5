#!/usr/bin/env python3
"""
Script de refatoracao para funcoes com multiplas queries - usar safe_cursor
"""

import re

filepath = r"c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\app_v5_final.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# PADRÃO PARA FUNÇÕES COM try/except E MÚLTIPLAS QUERIES
# Transformar: 
#   try:
#       conn = get_connection()
#       cursor = conn.cursor()
#       ... múltiplas queries ...
#   except:
#       ...
#   finally:
#       if conn: conn.close()
# EM:
#   try:
#       with safe_cursor() as cursor:
#           ... múltiplas queries ...
#   except:
#       ...

# Isto é mais seguro pois:
# 1. safe_cursor garante fechamento de cursor
# 2. safe_cursor garante fechamento de conexão
# 3. Preserva try/except existente
# 4. Menos mudanças = menos chances de bugs

print("Analisando arquivo para padrões try/except com get_connection...")

# Contar ocorrências de try/finally com conn.close()
try_finally_pattern = r'try:\s+conn = get_connection\(\)'
matches = list(re.finditer(try_finally_pattern, content))
print(f"\nEncontrado: {len(matches)} blocos try com get_connection")

# Estratégia: refatorar em partes menores
# Para cada try/except/finally, substituir apenas a parte de get_connection/cursor/close

# PADRÃO 1: try com get_connection simples
simple_try_pattern = r'''try:
        conn = get_connection\(\)
        cursor = conn\.cursor\(\)'''

simple_try_replacement = '''try:
        with safe_cursor() as cursor:'''

print("\nAplicando transformacoes...")
count1 = content.count(simple_try_pattern)
content = content.replace(simple_try_pattern, simple_try_replacement)
print(f"[1] Blocos try/get_connection → try/safe_cursor: {count1}")

# PADRÃO 2: Remover finally que apenas fecha conn
finally_close_pattern = r'''    finally:
        if conn:
            conn\.close\(\)'''

finally_close_replacement = ''

content = re.sub(finally_close_pattern, finally_close_replacement, content)
count2 = content.count('finally:')
print(f"[2] Finally conn.close() removido: ~{count2} casos")

# Remover linhas com 'if conn:' que agora estão vazias
content = re.sub(r'        if conn:\s+\n', '', content)

print("\n[OK] Transformacoes aplicadas!")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"Arquivo: {filepath}")
print(f"Total de mudancas: {count1}")
print(f"\nProximo passo: Revisar e testar arquivo")
