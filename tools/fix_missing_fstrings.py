"""
Script para adicionar f-string em queries SQL que usam SQL_PLACEHOLDER
mas não têm o prefixo f
"""

import os
import re

def fix_fstrings_in_file(filepath):
    """Adiciona f-string em queries que usam SQL_PLACEHOLDER mas não têm f"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = 0
        
        # Padrão: execute(""" ou execute(''' sem f antes, que contém SQL_PLACEHOLDER
        # Procurar por blocos execute sem f-string
        pattern = r'\.execute\(\s*(["\'])(\1\1)?'
        
        lines = content.split('\n')
        new_lines = []
        in_execute = False
        execute_lines = []
        execute_indent = 0
        needs_fstring = False
        
        for i, line in enumerate(lines):
            # Detectar início de execute
            if '.execute(' in line and not line.strip().startswith('#'):
                # Verificar se já tem f-string
                execute_match = re.search(r'\.execute\(\s*f?(["\'])', line)
                if execute_match:
                    has_f = 'f' in line[execute_match.start():execute_match.end()]
                    in_execute = True
                    execute_lines = [line]
                    execute_indent = len(line) - len(line.lstrip())
                    needs_fstring = not has_f
                    continue
            
            if in_execute:
                execute_lines.append(line)
                
                # Verificar se tem SQL_PLACEHOLDER
                if 'SQL_PLACEHOLDER' in line:
                    # Precisa de f-string se ainda não detectamos necessidade
                    if needs_fstring:
                        needs_fstring = True
                
                # Detectar fim do execute (linha com parêntese de fechamento)
                if ')' in line and line.strip().endswith(')'):
                    # Processar o bloco execute
                    if needs_fstring and 'SQL_PLACEHOLDER' in '\n'.join(execute_lines):
                        # Adicionar f-string na primeira linha
                        first_line = execute_lines[0]
                        # Encontrar posição da aspas
                        quote_match = re.search(r'\.execute\(\s*(["\'])(\1\1)?', first_line)
                        if quote_match:
                            pos = quote_match.end() - 1
                            # Inserir f antes da aspas
                            execute_lines[0] = first_line[:pos] + 'f' + first_line[pos:]
                            changes += 1
                    
                    new_lines.extend(execute_lines)
                    in_execute = False
                    execute_lines = []
                    needs_fstring = False
                    continue
            
            if not in_execute:
                new_lines.append(line)
        
        if changes > 0:
            new_content = '\n'.join(new_lines)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return changes
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro ao processar {filepath}: {e}")
        return 0

def main():
    """Processa todos os arquivos Python no diretório ponto_esa_v5"""
    base_dir = r"C:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\ponto_esa_v5"
    
    print("=" * 80)
    print("       ADICIONAR F-STRING EM QUERIES COM SQL_PLACEHOLDER")
    print("=" * 80)
    print()
    
    files_to_check = [
        "horas_extras_system.py",
        "atestado_horas_system.py",
        "ajuste_registros_system.py",
        "banco_horas_system.py",
        "calculo_horas_system.py",
        "notifications.py",
        "upload_system.py"
    ]
    
    total_changes = 0
    
    for filename in files_to_check:
        filepath = os.path.join(base_dir, filename)
        if os.path.exists(filepath):
            changes = fix_fstrings_in_file(filepath)
            if changes > 0:
                print(f"✅ {filename}: {changes} correções")
                total_changes += changes
            else:
                print(f"⚪ {filename}: nenhuma correção necessária")
    
    print()
    print("=" * 80)
    print(f"Total: {total_changes} correções em queries SQL")
    print("=" * 80)

if __name__ == "__main__":
    main()
