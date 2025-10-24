#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para corrigir indentação e remover 'if True:' problemático
"""

# Ler arquivo
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total de linhas: {len(lines)}")

# Procurar e remover a linha com "if True:"
fixed_lines = []
skip_next = False

for i, line in enumerate(lines, 1):
    # Se encontrar "if True:  # Removido expander", pula essa linha
    if 'if True:' in line and 'Removido expander' in line:
        print(f"Removendo linha {i}: {line.strip()}")
        continue
    
    fixed_lines.append(line)

print(f"Linhas após correção: {len(fixed_lines)}")

# Salvar
with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
    f.writelines(fixed_lines)

print("\n✅ Arquivo corrigido!")

# Testar sintaxe
import subprocess
import sys

result = subprocess.run([sys.executable, '-m', 'py_compile', 'ponto_esa_v5/app_v5_final.py'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("✅ SINTAXE OK!")
else:
    print("❌ ERRO DE SINTAXE:")
    print(result.stderr)
