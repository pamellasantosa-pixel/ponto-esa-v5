#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para corrigir indentação após remoção do if True:
"""

# Ler arquivo
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total de linhas: {len(lines)}")

# Encontrar linha com st.markdown("**🔑 Alterar Senha:")
senha_line_idx = None
for i, line in enumerate(lines):
    if 'st.markdown("**🔑 Alterar Senha:' in line:
        senha_line_idx = i
        print(f"Encontrada linha Alterar Senha: {i+1}")
        print(f"Indentação: {len(line) - len(line.lstrip())} espaços")
        break

if senha_line_idx:
    # Pegar a indentação base (da linha st.markdown)
    base_indent = len(lines[senha_line_idx]) - len(lines[senha_line_idx].lstrip())
    print(f"Indentação base: {base_indent} espaços")
    
    # Procurar linhas após st.markdown que têm indentação MAIOR que base_indent + 4
    # e dedent elas em 12 espaços (diferença entre indentação dentro e fora do if)
    
    fixed_lines = []
    in_senha_block = False
    for i, line in enumerate(lines):
        if i == senha_line_idx:
            in_senha_block = True
            fixed_lines.append(line)
        elif in_senha_block:
            current_indent = len(line) - len(line.lstrip())
            # Se tem mais de base_indent + 4, provavelmente é do if True removido
            if current_indent > base_indent + 4 and line.strip():
                # Dedent 12 espaços
                dedent = min(12, current_indent - (base_indent + 4))
                new_line = ' ' * (current_indent - dedent) + line.lstrip()
                print(f"Linha {i+1}: {current_indent} -> {current_indent - dedent} espaços")
                fixed_lines.append(new_line)
            else:
                fixed_lines.append(line)
                # Se chegou em uma linha com indentação menor ou igual a base, saiu do bloco
                if current_indent <= base_indent and line.strip():
                    in_senha_block = False
        else:
            fixed_lines.append(line)
    
    print(f"\nLinhas fixadas: {len(fixed_lines)}")
    
    # Salvar
    with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(fixed_lines)
    
    print("✅ Arquivo salvo!")
    
    # Testar sintaxe
    import subprocess
    import sys
    
    result = subprocess.run([sys.executable, '-m', 'py_compile', 'ponto_esa_v5/app_v5_final.py'], 
                           capture_output=True, text=True)
    
    if result.returncode == 0:
        print("\n✅✅✅ SINTAXE OK! ✅✅✅")
    else:
        print("\n❌ ERRO DE SINTAXE:")
        print(result.stderr)
else:
    print("❌ Não encontrou a linha de Alterar Senha!")
