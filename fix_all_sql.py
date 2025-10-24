#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para corrigir TODOS os placeholders SQL no app_v5_final.py
Substitui ? e %s hardcoded por SQL_PLACEHOLDER
"""

import re

# Ler arquivo
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"Tamanho original: {len(content)} bytes")

# Lista de substituições a fazer
fixes = []

# 1. Linha 380: verificar_login - já usa %s, precisa usar SQL_PLACEHOLDER
old_1 = '''    cursor.execute(
        "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha_hash))'''
new_1 = '''    cursor.execute(
        f"SELECT tipo, nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER} AND senha = {SQL_PLACEHOLDER}", (usuario, senha_hash))'''
if old_1 in content:
    content = content.replace(old_1, new_1)
    fixes.append("verificar_login() - linha 380")

# 2. Linha 1723: contador de registros
old_2 = '''        "SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = ?", (hoje,))'''
new_2 = '''        f"SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = {SQL_PLACEHOLDER}", (hoje,))'''
if old_2 in content:
    content = content.replace(old_2, new_2)
    fixes.append("contador registros - linha 1723")

# 3. Linha 1780: jornada prevista
old_3 = '''                "SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = ?", (usuario,))'''
new_3 = '''                f"SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (usuario,))'''
if old_3 in content:
    content = content.replace(old_3, new_3)
    fixes.append("jornada prevista - linha 1780")

# 4. Linha 3040: deletar projeto
old_4 = '''                                    "DELETE FROM projetos WHERE id = ?", (projeto_id,))'''
new_4 = '''                                    f"DELETE FROM projetos WHERE id = {SQL_PLACEHOLDER}", (projeto_id,))'''
if old_4 in content:
    content = content.replace(old_4, new_4)
    fixes.append("deletar projeto - linha 3040")

# 5. Linha 3288: deletar usuário
old_5 = '''                                    "DELETE FROM usuarios WHERE id = ?", (usuario_id,))'''
new_5 = '''                                    f"DELETE FROM usuarios WHERE id = {SQL_PLACEHOLDER}", (usuario_id,))'''
if old_5 in content:
    content = content.replace(old_5, new_5)
    fixes.append("deletar usuário - linha 3288")

# 6. Linha 3621: query de registros
# Precisa ler contexto maior para essa
old_6_pattern = r"WHERE usuario = \? AND DATE\(data_hora\) = \?"
new_6_replacement = f"WHERE usuario = {{SQL_PLACEHOLDER}} AND DATE(data_hora) = {{SQL_PLACEHOLDER}}"
if re.search(old_6_pattern, content):
    content = re.sub(old_6_pattern, new_6_replacement, content)
    fixes.append("query registros - linha 3621")

print(f"\n{'='*60}")
print("CORREÇÕES SQL APLICADAS:")
print(f"{'='*60}")
for i, fix in enumerate(fixes, 1):
    print(f"{i}. {fix}")

print(f"\nTamanho após mudanças: {len(content)} bytes")

# Salvar com LF
with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("\n✅ Arquivo salvo!")

# Verificação final
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    verification = f.read()

# Contar placeholders hardcoded restantes
hardcoded_question = len(re.findall(r'cursor\.execute.*\?["\']', verification))
hardcoded_percent = len(re.findall(r'cursor\.execute.*%s["\']', verification))

print(f"\n{'='*60}")
print("VERIFICAÇÃO FINAL:")
print(f"{'='*60}")
print(f"✓ Placeholders ? hardcoded restantes: {hardcoded_question}")
print(f"✓ Placeholders %s hardcoded restantes: {hardcoded_percent}")
print(f"✓ SQL_PLACEHOLDER usado: {verification.count('SQL_PLACEHOLDER')} vezes")
