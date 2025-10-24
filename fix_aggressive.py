#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Correção AGRESSIVA de indentação - força tudo para 24 espaços
"""

# Ler arquivo
with open('ponto_esa_v5/app_v5_final.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Encontrar linha st.markdown Alterar Senha
senha_idx = None
for i, line in enumerate(lines):
    if 'st.markdown("**🔑 Alterar Senha:' in line:
        senha_idx = i
        break

if senha_idx:
    print(f"Encontrada linha: {senha_idx + 1}")
    
    # Forçar indentação de 24 espaços para as próximas ~35 linhas
    # (todo o bloco de alteração de senha)
    fixed_lines = lines[:senha_idx + 1]  # Até st.markdown
    
    i = senha_idx + 1
    base_indent = 24  # Mesma indentação do st.markdown
    
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        
        # Se linha vazia, manter
        if not stripped:
            fixed_lines.append(line)
            i += 1
            continue
        
        current_indent = len(line) - len(stripped)
        
        # Se chegou em uma linha com indentação <= 24 E não é continuação
        # (não começa com ')' ou fechamento), saiu do bloco
        if current_indent <= 24 and not stripped.startswith(')') and i > senha_idx + 35:
            # Adicionar resto do arquivo
            fixed_lines.extend(lines[i:])
            break
        
        # Se está entre senha_idx+1 e senha_idx+35 (bloco de senha)
        if senha_idx < i <= senha_idx + 35:
            # Calcular nova indentação relativa
            if stripped.startswith(')'):
                # Fechamento de parênteses: base_indent
                new_indent = base_indent
            elif any(stripped.startswith(x) for x in ['if ', 'elif ', 'else:', 'conn ', 'cursor']):
                # Comandos de controle ou operações: base_indent + 4
                new_indent = base_indent + 4
            elif i == senha_idx + 1:  # nova_senha = ...
                new_indent = base_indent
            elif '"' in stripped and '=' not in stripped:  # String arguments
                new_indent = base_indent + 4
            else:
                # Manter relação proporcional mas ajustar base
                excess = current_indent - 28
                new_indent = base_indent + max(0, excess)
            
            new_line = ' ' * new_indent + stripped
            fixed_lines.append(new_line)
            print(f"Linha {i+1}: {current_indent} -> {new_indent}")
        else:
            fixed_lines.append(line)
        
        i += 1
    
    # Salvar
    with open('ponto_esa_v5/app_v5_final.py', 'w', encoding='utf-8', newline='\n') as f:
        f.writelines(fixed_lines)
    
    print("\n✅ Salvo!")
    
    # Testar
    import subprocess
    import sys
    
    result = subprocess.run([sys.executable, '-m', 'py_compile', 'ponto_esa_v5/app_v5_final.py'], 
                           capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ SINTAXE OK!")
    else:
        print("❌ ERRO:")
        print(result.stderr)
