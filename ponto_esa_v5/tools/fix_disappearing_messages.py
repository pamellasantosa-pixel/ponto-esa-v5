#!/usr/bin/env python3
"""Script para adicionar time.sleep() antes de st.rerun() para evitar mensagens desaparecendo"""

import re

def fix_disappearing_messages(filepath):
    """Adiciona time.sleep(2) antes de st.rerun() que vem após st.success/st.info"""
    
    # Ler arquivo
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Criar backup
    with open(filepath + '.bak', 'w', encoding='utf-8') as f:
        f.write(content)
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    changes_count = 0
    
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Verifica se é uma linha com st.success ou st.info
        if 'st.success(' in line or 'st.info(' in line:
            # Olha para frente para encontrar st.rerun()
            j = i + 1
            # Pula linhas em branco ou continuação de string
            while j < len(lines) and (not lines[j].strip() or 
                                     lines[j].strip().startswith('f"') or
                                     lines[j].strip().startswith('"') or
                                     lines[j].strip().endswith(')') and not 'st.rerun' in lines[j]):
                new_lines.append(lines[j])
                j += 1
            
            # Se a próxima linha significativa é st.rerun()
            if j < len(lines) and 'st.rerun()' in lines[j]:
                # Verifica se não há time.sleep logo antes
                has_sleep = False
                for k in range(max(0, i-3), i):
                    if 'time.sleep' in lines[k]:
                        has_sleep = True
                        break
                
                if not has_sleep:
                    # Adiciona time.sleep com a mesma indentação
                    indent = len(lines[j]) - len(lines[j].lstrip())
                    sleep_line = ' ' * indent + 'time.sleep(2)  # Aguarda 2 segundos para usuário ver a mensagem'
                    new_lines.append(sleep_line)
                    changes_count += 1
                
                # Continua do ponto onde parou
                i = j - 1
        
        i += 1
    
    # Salvar arquivo modificado
    new_content = '\n'.join(new_lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f'✅ Correções aplicadas: {changes_count} locais')
    print(f'📁 Backup salvo em: {filepath}.bak')
    
    return changes_count

if __name__ == '__main__':
    filepath = r'c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\ponto_esa_v5\app_v5_final.py'
    changes = fix_disappearing_messages(filepath)
    print(f'\n✨ Pronto! {changes} mensagens agora serão visíveis por 2 segundos antes do rerun')
