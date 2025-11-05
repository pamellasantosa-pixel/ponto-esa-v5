"""
Script para adicionar 'f' em strings que têm {SQL_PLACEHOLDER} mas não são f-strings
"""

import os
import re

SOURCE_DIR = os.path.join(os.path.dirname(__file__), '..', 'ponto_esa_v5', 'ponto_esa_v5')

FILES = [
    'app_v5_final.py',
    'banco_horas_system.py',
    'calculo_horas_system.py',
    'horas_extras_system.py',
    'atestado_horas_system.py',
    'upload_system.py',
    'notifications.py'
]

def fix_file(filepath):
    """Adiciona f em strings que têm {SQL_PLACEHOLDER}"""
    filename = os.path.basename(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    
    for line in lines:
        # Se a linha tem {SQL_PLACEHOLDER} mas não é f-string
        if '{SQL_PLACEHOLDER}' in line:
            # Verificar se já é f-string
            # Padrões: """...""", "...", '...'
            
            # Triple quotes
            if '"""' in line and not 'f"""' in line:
                line = line.replace('"""', 'f"""', 1)
                modified = True
            
            # Single/double quotes inline
            elif ('"' in line or "'" in line) and '{SQL_PLACEHOLDER}' in line:
                # Procurar por padrões como cursor.execute(" ou query = "
                if 'cursor.execute(' in line and not 'f"' in line and not "f'" in line:
                    # Adicionar f antes da primeira aspas após execute(
                    line = re.sub(r'execute\(\s*"', 'execute(f"', line)
                    line = re.sub(r"execute\(\s*'", "execute(f'", line)
                    modified = True
                elif ('query =' in line or 'query +=' in line) and not 'f"' in line and not "f'" in line:
                    line = re.sub(r'=\s*"', '= f"', line)
                    line = re.sub(r"=\s*'", "= f'", line)
                    modified = True
        
        new_lines.append(line)
    
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✅ {filename} corrigido")
        return True
    
    return False

def main():
    print("="*80)
    print(" "*20 + "ADICIONAR F-STRING NAS QUERIES SQL")
    print("="*80 + "\n")
    
    fixed = 0
    for filename in FILES:
        filepath = os.path.join(SOURCE_DIR, filename)
        if os.path.exists(filepath):
            if fix_file(filepath):
                fixed += 1
    
    print(f"\n✅ {fixed} arquivos corrigidos\n")

if __name__ == '__main__':
    main()
