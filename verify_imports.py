#!/usr/bin/env python3
"""
Script para verificar e validar todos os imports do projeto.
Detecta imports circulares e módulos faltantes.
"""

import sys
import os
import ast
from pathlib import Path

def extract_imports(file_path):
    """Extrai todos os imports de um arquivo Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append({
                        'type': 'from',
                        'module': node.module,
                        'names': [alias.name for alias in node.names],
                        'line': node.lineno
                    })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        'type': 'import',
                        'module': alias.name,
                        'line': node.lineno
                    })
        return imports
    except Exception as e:
        print(f"❌ Erro ao ler {file_path}: {e}")
        return []

def check_circular_imports():
    """Verifica imports circulares"""
    print("🔍 Verificando imports circulares...")
    
    project_dir = Path(__file__).parent
    py_files = list(project_dir.glob('*.py'))
    
    issues = []
    
    for py_file in py_files:
        imports = extract_imports(py_file)
        for imp in imports:
            # Verificar se está importando de si mesmo
            file_module = py_file.stem
            
            if imp['type'] == 'from':
                if f".{file_module}" in imp['module'] or imp['module'] == file_module:
                    issues.append({
                        'file': py_file.name,
                        'line': imp['line'],
                        'issue': f"Possível import circular: importa de {imp['module']}"
                    })
    
    if issues:
        print(f"⚠️  {len(issues)} possível(is) import(s) circular(es) encontrado(s):")
        for issue in issues:
            print(f"   📄 {issue['file']}:{issue['line']} - {issue['issue']}")
        return False
    else:
        print("✅ Nenhum import circular detectado!")
        return True

def check_required_modules():
    """Verifica se módulos requeridos estão presentes"""
    print("\n📦 Verificando módulos requeridos...")
    
    project_dir = Path(__file__).parent
    required_modules = [
        'app_v5_final.py',
        'banco_horas_system.py',
        'atestado_horas_system.py',
        'horas_extras_system.py',
        'upload_system.py',
        'notifications.py',
        'database.py',
        'database_postgresql.py',
        'error_handler.py',
        'connection_manager.py',
    ]
    
    missing = []
    for module in required_modules:
        if not (project_dir / module).exists():
            missing.append(module)
    
    if missing:
        print(f"❌ {len(missing)} módulo(s) faltando:")
        for module in missing:
            print(f"   📄 {module}")
        return False
    else:
        print(f"✅ Todos os {len(required_modules)} módulos requeridos presentes!")
        return True

def check_function_exports():
    """Verifica se funções esperadas estão sendo exportadas"""
    print("\n📤 Verificando exports de funções...")
    
    project_dir = Path(__file__).parent
    
    required_exports = {
        'banco_horas_system.py': ['BancoHorasSystem', 'format_saldo_display'],
        'atestado_horas_system.py': ['AtestadoHorasSystem', 'format_time_duration', 'get_status_color', 'get_status_emoji'],
        'hora_extra_timer_system.py': ['HoraExtraTimerSystem'],
        'upload_system.py': ['UploadSystem', 'format_file_size', 'get_file_icon'],
        'notifications.py': ['NotificationManager'],  # notification_manager é uma instância
    }
    
    issues = []
    
    for file_name, expected_exports in required_exports.items():
        file_path = project_dir / file_name
        if not file_path.exists():
            issues.append(f"❌ {file_name} não encontrado")
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for export in expected_exports:
                if f"def {export}" not in content and f"class {export}" not in content and f"{export} =" not in content:
                    issues.append(f"⚠️  {file_name} - Faltando: {export}")
        except Exception as e:
            issues.append(f"❌ Erro ao ler {file_name}: {e}")
    
    if issues:
        print(f"⚠️  {len(issues)} problema(s) encontrado(s):")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ Todos os exports estão presentes!")
        return True

def main():
    print("=" * 70)
    print("🔧 VERIFICAÇÃO DE IMPORTS - PONTO-ESA-V5")
    print("=" * 70)
    
    results = {
        'circular': check_circular_imports(),
        'required': check_required_modules(),
        'exports': check_function_exports(),
    }
    
    print("\n" + "=" * 70)
    print("📊 RESUMO:")
    print("=" * 70)
    
    total = sum(1 for v in results.values() if v)
    print(f"✅ Verificações passando: {total}/{len(results)}")
    
    if all(results.values()):
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema pronto para deploy.")
        return 0
    else:
        print("\n❌ Há problemas a corrigir antes do deploy.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
