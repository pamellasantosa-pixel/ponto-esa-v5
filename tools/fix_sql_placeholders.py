"""
Script de Correção Automática de SQL Placeholders
Converte todas as queries com %s hardcoded para usar SQL_PLACEHOLDER
Garante compatibilidade total SQLite/PostgreSQL
"""

import os
import re
import shutil
from datetime import datetime

# Diretório do código fonte
SOURCE_DIR = os.path.join(os.path.dirname(__file__), '..', 'ponto_esa_v5', 'ponto_esa_v5')

# Arquivos que precisam ser corrigidos
FILES_TO_FIX = [
    'app_v5_final.py',
    'banco_horas_system.py',
    'calculo_horas_system.py',
    'horas_extras_system.py',
    'atestado_horas_system.py',
    'upload_system.py',
    'notifications.py'
]

def create_backup(file_path):
    """Cria backup do arquivo antes de modificar"""
    backup_dir = os.path.join(os.path.dirname(__file__), '..', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.basename(file_path)
    backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")
    
    shutil.copy2(file_path, backup_path)
    print(f"✅ Backup criado: {backup_path}")
    return backup_path

def check_has_sql_placeholder_import(content):
    """Verifica se o arquivo já importa SQL_PLACEHOLDER"""
    patterns = [
        r'from database_postgresql import.*SQL_PLACEHOLDER',
        r'SQL_PLACEHOLDER\s*=\s*["\']%s["\'].*if.*USE_POSTGRESQL'
    ]
    
    for pattern in patterns:
        if re.search(pattern, content, re.MULTILINE):
            return True
    return False

def check_has_use_postgresql_import(content):
    """Verifica se o arquivo já importa USE_POSTGRESQL"""
    pattern = r'from database_postgresql import.*USE_POSTGRESQL'
    return bool(re.search(pattern, content, re.MULTILINE))

def add_sql_placeholder_import(content, filename):
    """Adiciona import de SQL_PLACEHOLDER no início do arquivo"""
    
    # Se já tem, não adiciona
    if check_has_sql_placeholder_import(content):
        print(f"  ℹ️  {filename} já tem SQL_PLACEHOLDER definido")
        return content
    
    # Encontrar a linha de import do database_postgresql
    import_pattern = r'from database_postgresql import ([^\n]+)'
    match = re.search(import_pattern, content)
    
    if match:
        current_imports = match.group(1).strip()
        
        # Adicionar USE_POSTGRESQL e SQL_PLACEHOLDER se não existirem
        imports_to_add = []
        if 'USE_POSTGRESQL' not in current_imports:
            imports_to_add.append('USE_POSTGRESQL')
        
        if imports_to_add:
            new_imports = current_imports + ', ' + ', '.join(imports_to_add)
            content = content.replace(match.group(0), f'from database_postgresql import {new_imports}')
            print(f"  ✅ Adicionado import: {', '.join(imports_to_add)}")
        
        # Adicionar definição de SQL_PLACEHOLDER após os imports
        if 'SQL_PLACEHOLDER' not in content:
            # Encontrar o final dos imports (primeira linha que não é import/comment)
            lines = content.split('\n')
            insert_pos = 0
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('import') and not stripped.startswith('from'):
                    insert_pos = i
                    break
            
            placeholder_def = '\n# SQL Placeholder para compatibilidade SQLite/PostgreSQL\nSQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"\n'
            lines.insert(insert_pos, placeholder_def)
            content = '\n'.join(lines)
            print(f"  ✅ Adicionada definição de SQL_PLACEHOLDER")
    
    return content

def replace_sql_placeholders(content, filename):
    """Substitui %s por SQL_PLACEHOLDER em queries SQL"""
    
    # Contar quantos %s existem em queries
    count_before = len(re.findall(r'WHERE.*%s|VALUES.*%s|SET.*%s|AND.*%s|OR.*%s|BETWEEN.*%s', content, re.IGNORECASE))
    
    if count_before == 0:
        print(f"  ℹ️  {filename} não precisa de correções")
        return content, 0
    
    # Padrões para encontrar queries SQL com %s
    # Importante: não substituir %s em strings de formato ou comentários
    
    # 1. Substituir em queries dentro de aspas triplas
    def replace_in_triple_quotes(match):
        query = match.group(0)
        # Substituir %s por {SQL_PLACEHOLDER}, mas preservar %%
        modified = re.sub(r'(?<!%)%s(?!%)', '{SQL_PLACEHOLDER}', query)
        return modified
    
    # 2. Substituir em queries inline (entre aspas simples ou duplas)
    def replace_in_inline_query(match):
        query = match.group(0)
        # Substituir %s por {SQL_PLACEHOLDER}, mas preservar %%
        modified = re.sub(r'(?<!%)%s(?!%)', '{SQL_PLACEHOLDER}', query)
        return modified
    
    # Substituir em queries de múltiplas linhas (aspas triplas)
    content = re.sub(
        r'"""[\s\S]*?"""',
        replace_in_triple_quotes,
        content
    )
    
    # Substituir em queries inline que contém WHERE, VALUES, SET, etc
    content = re.sub(
        r'"[^"]*(?:WHERE|VALUES|SET|AND|OR|BETWEEN|FROM|UPDATE|DELETE|INSERT)[^"]*"',
        replace_in_inline_query,
        content,
        flags=re.IGNORECASE
    )
    
    # Converter {SQL_PLACEHOLDER} para f-string
    content = content.replace('{SQL_PLACEHOLDER}', 'f{SQL_PLACEHOLDER}')
    
    # Corrigir f-strings que ficaram com aspas erradas
    # Trocar "f{SQL_PLACEHOLDER}" por f"{SQL_PLACEHOLDER}"
    content = re.sub(r'(["\'])f\{SQL_PLACEHOLDER\}', r'f\1{SQL_PLACEHOLDER}', content)
    
    # Melhor: usar f-string completa
    # SELECT ... WHERE x = %s  →  f"SELECT ... WHERE x = {SQL_PLACEHOLDER}"
    
    # Refazer de forma mais robusta
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # Se a linha tem uma query SQL (contém cursor.execute, query =, etc) com %s
        if ('cursor.execute' in line or 'query =' in line) and '%s' in line and 'SQL_PLACEHOLDER' not in line:
            # Converter para f-string
            # Encontrar a string SQL
            
            # Padrão: "...%s..." ou '...%s...'
            if '"""' in line:
                # Query multilinha, não mexer aqui
                new_lines.append(line)
                continue
            
            # Query inline
            # Trocar "...%s..." por f"...{SQL_PLACEHOLDER}..."
            modified_line = line
            
            # Encontrar todas as strings na linha
            for quote in ['"', "'"]:
                pattern = f'{quote}([^{quote}]*%s[^{quote}]*){quote}'
                matches = re.finditer(pattern, line)
                
                for match in matches:
                    original = match.group(0)
                    string_content = match.group(1)
                    
                    # Substituir %s por {SQL_PLACEHOLDER}
                    new_content = re.sub(r'(?<!%)%s(?!%)', '{SQL_PLACEHOLDER}', string_content)
                    
                    # Criar f-string
                    new_string = f'f{quote}{new_content}{quote}'
                    
                    modified_line = modified_line.replace(original, new_string)
            
            new_lines.append(modified_line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Contar quantos foram substituídos
    count_after = len(re.findall(r'SQL_PLACEHOLDER', content))
    
    return content, count_after

def fix_file(filepath):
    """Corrige um arquivo específico"""
    filename = os.path.basename(filepath)
    print(f"\n📝 Processando: {filename}")
    
    # Ler conteúdo original
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Criar backup
    create_backup(filepath)
    
    # Adicionar imports necessários
    content = add_sql_placeholder_import(original_content, filename)
    
    # Substituir placeholders
    content, replacements = replace_sql_placeholders(content, filename)
    
    # Salvar arquivo modificado
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Arquivo atualizado: {replacements} substituições")
        return True
    else:
        print(f"  ℹ️  Nenhuma alteração necessária")
        return False

def main():
    print("="*80)
    print(" "*20 + "CORREÇÃO AUTOMÁTICA DE SQL PLACEHOLDERS")
    print("="*80)
    print("\n🎯 Objetivo: Garantir compatibilidade total SQLite/PostgreSQL")
    print(f"📂 Diretório: {SOURCE_DIR}\n")
    
    fixed_count = 0
    error_count = 0
    
    for filename in FILES_TO_FIX:
        filepath = os.path.join(SOURCE_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  Arquivo não encontrado: {filename}")
            continue
        
        try:
            if fix_file(filepath):
                fixed_count += 1
        except Exception as e:
            print(f"❌ Erro ao processar {filename}: {e}")
            error_count += 1
    
    print("\n" + "="*80)
    print("📊 RESUMO")
    print("="*80)
    print(f"✅ Arquivos corrigidos: {fixed_count}")
    print(f"❌ Erros: {error_count}")
    print(f"📁 Backups salvos em: backups/")
    print("\n🎉 Correção concluída!")
    print("\n💡 Próximo passo: Execute os testes para validar as correções")
    print("   python tools/test_sistema_completo.py")

if __name__ == '__main__':
    main()
