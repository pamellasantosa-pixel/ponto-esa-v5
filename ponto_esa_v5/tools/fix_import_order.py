"""
Script para corrigir ordem de imports e SQL_PLACEHOLDER
Move a definição de SQL_PLACEHOLDER para DEPOIS dos imports
"""

import os
import re

SOURCE_DIR = os.path.join(os.path.dirname(__file__), '..', 'ponto_esa_v5', 'ponto_esa_v5')

FILES_TO_FIX = [
    'banco_horas_system.py',
    'horas_extras_system.py',
    'atestado_horas_system.py',
    'upload_system.py'
]

def fix_import_order(filepath):
    """Move SQL_PLACEHOLDER para depois dos imports"""
    filename = os.path.basename(filepath)
    print(f"📝 Corrigindo: {filename}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remover SQL_PLACEHOLDER de antes dos imports
    pattern = r'\n# SQL Placeholder.*?\nSQL_PLACEHOLDER = .*?\n'
    sql_placeholder_def = re.search(pattern, content, re.DOTALL)
    
    if sql_placeholder_def:
        # Remover da posição atual
        content = content.replace(sql_placeholder_def.group(0), '\n')
        
        # Encontrar última linha de import
        lines = content.split('\n')
        last_import_idx = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                last_import_idx = i

        # Inserir SQL_PLACEHOLDER após último import
        lines.insert(last_import_idx + 1, '')
        lines.insert(last_import_idx + 2, '# SQL Placeholder para compatibilidade SQLite/PostgreSQL')
        lines.insert(last_import_idx + 3, 'SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"')

        content = '\n'.join(lines)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"  ✅ {filename} corrigido")
        return True
    else:
        print(f"  ℹ️  {filename} não precisa de correção")
        return False

def main():
    print("="*80)
    print(" "*25 + "CORREÇÃO DE ORDEM DE IMPORTS")
    print("="*80 + "\n")
    
    fixed = 0
    for filename in FILES_TO_FIX:
        filepath = os.path.join(SOURCE_DIR, filename)
        if os.path.exists(filepath):
            if fix_import_order(filepath):
                fixed += 1
        else:
            print(f"⚠️  Não encontrado: {filename}")
    
    print(f"\n✅ {fixed} arquivos corrigidos\n")

if __name__ == '__main__':
    main()
