#!/usr/bin/env python3
"""
Refatorador automático em massa para app_v5_final.py
Substitui padrões comuns de get_connection() de forma segura
"""

import re
import sys

filepath = r"c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\app_v5_final.py"

# Ler arquivo
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

original_content = content
count = 0

print("Iniciando refatoracao em massa...\n")

# PADRÃO 1: Simples SELECT com fetchall (sem processamento)
pattern1 = r'''    conn = get_connection\(\)
    cursor = conn\.cursor\(\)
    cursor\.execute\((.+?)\)
    (.+?) = cursor\.fetchall\(\)
    conn\.close\(\)
    return \2'''

def replace1(match):
    global count
    query_part = match.group(1)
    var_name = match.group(2)
    count += 1
    return f'''    results = execute_query({query_part})
    return [row[0] for row in results] if results else []''' if "row[0]" in content[match.start():match.end()+200] else f'''    return execute_query({query_part})'''

# PADRÃO 2: Simples SELECT com fetchone (sem processamento)
pattern2 = r'''    conn = get_connection\(\)
    cursor = conn\.cursor\(\)
    cursor\.execute\((.+?)\)
    (.+?) = cursor\.fetchone\(\)
    conn\.close\(\)
    return \2'''

def replace2(match):
    global count
    query_part = match.group(1)
    var_name = match.group(2)
    count += 1
    return f'''    return execute_query({query_part}, fetch_one=True)'''

# PADRÃO 3: UPDATE/INSERT com commit
pattern3 = r'''    conn = get_connection\(\)
    cursor = conn\.cursor\(\)
    cursor\.execute\((.+?)\)
    conn\.commit\(\)
    conn\.close\(\)'''

def replace3(match):
    global count
    query_part = match.group(1)
    count += 1
    return f'''    execute_update({query_part})'''

# Aplicar padrões
print("Processando padrões...")

# Padrão 3 é mais seguro (não toca em código com processamento)
content = re.sub(pattern3, replace3, content, flags=re.MULTILINE)
print(f"[PADRÃO 3] UPDATE/INSERT simples: {count} substituicoes")

# Contar quantas ainda faltam
remaining = content.count('conn = get_connection()')
print(f"\nAinda faltam: {remaining} conexoes\n")

# Salvar
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

if content != original_content:
    print(f"[SUCESSO] Arquivo atualizado!")
    print(f"Total de substituicoes: {count}")
else:
    print("[INFO] Nenhuma mudanca foi feita (padroes nao encontrados ou nao seguem regex esperado)")

print(f"\nProximos passos:")
print(f"1. Revisar arquivo em editor")
print(f"2. Testar funcionalidade")
print(f"3. Fazer commit se OK")
