"""
Script para corrigir f{SQL_PLACEHOLDER} → {SQL_PLACEHOLDER}
Remove o 'f' duplicado dentro de f-strings
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
    """Corrige f{SQL_PLACEHOLDER} para {SQL_PLACEHOLDER}"""
    filename = os.path.basename(filepath)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Contar ocorrências antes
    count_before = content.count('f{SQL_PLACEHOLDER}')
    
    if count_before == 0:
        return False
    
    print(f"📝 {filename}: {count_before} ocorrências de f{{SQL_PLACEHOLDER}}")
    
    # Substituir f{SQL_PLACEHOLDER} por {SQL_PLACEHOLDER}
    content = content.replace('f{SQL_PLACEHOLDER}', '{SQL_PLACEHOLDER}')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✅ Corrigido!")
    return True

def main():
    print("="*80)
    print(" "*25 + "CORREÇÃO DE F-STRINGS")
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
