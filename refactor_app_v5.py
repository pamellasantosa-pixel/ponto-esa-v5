#!/usr/bin/env python3
"""
Automatizador de refatoração para app_v5_final.py
Transforma get_connection() em context managers
"""

import re
import sys
import os

# Adicionar ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ponto_esa_v5'))


def analyze_connection_patterns(content: str) -> dict:
    """Analisa padrões de conexão no arquivo."""
    patterns = {
        'simple_select': re.finditer(
            r'conn = get_connection\(\)\s+cursor = conn\.cursor\(\)\s+cursor\.execute\([^)]+\)\s+result = cursor\.(fetchone|fetchall)\(\)\s+conn\.close\(\)',
            content, re.MULTILINE
        ),
        'update_with_commit': re.finditer(
            r'conn = get_connection\(\)\s+cursor = conn\.cursor\(\)\s+cursor\.execute\([^)]+\)\s+conn\.commit\(\)\s+conn\.close\(\)',
            content, re.MULTILINE
        ),
        'try_except_pattern': re.finditer(
            r'try:\s+conn = get_connection\(\).*?finally:\s+(if conn:\s+)?conn\.close\(\)',
            content, re.DOTALL
        ),
    }
    
    return {
        name: list(matches)
        for name, matches in patterns.items()
    }


def extract_function_contexts(content: str) -> dict:
    """Extrai contexto de cada função com get_connection()."""
    functions = {}
    
    # Encontrar funções que usam get_connection()
    func_pattern = re.compile(
        r'^def\s+(\w+)\s*\([^)]*\)[^:]*:\s*(?:""".*?"""|\'\'\'.*?\'\'\')?(.+?)(?=\ndef\s|\Z)',
        re.MULTILINE | re.DOTALL
    )
    
    for match in func_pattern.finditer(content):
        func_name = match.group(1)
        func_body = match.group(2)
        
        if 'get_connection()' in func_body:
            functions[func_name] = {
                'start': match.start(),
                'end': match.end(),
                'has_conn': 'get_connection()' in func_body,
                'has_try': 'try:' in func_body,
                'has_commit': 'conn.commit()' in func_body,
                'has_rollback': 'conn.rollback()' in func_body,
                'has_fetchone': 'fetchone()' in func_body,
                'has_fetchall': 'fetchall()' in func_body,
            }
    
    return functions


def generate_refactoring_report(filepath: str) -> str:
    """Gera relatório de refatoração necessária."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"
    
    functions = extract_function_contexts(content)
    
    report = """
╔════════════════════════════════════════════════════════════════════════════╗
║         RELATÓRIO DE REFATORAÇÃO - app_v5_final.py                       ║
╚════════════════════════════════════════════════════════════════════════════╝

RESUMO:
"""
    
    report += f"\n  Total de funções com get_connection(): {len(functions)}\n"
    
    select_only = sum(1 for f in functions.values() 
                     if (f['has_fetchone'] or f['has_fetchall']) 
                     and not f['has_commit'])
    update_funcs = sum(1 for f in functions.values() if f['has_commit'])
    try_except_funcs = sum(1 for f in functions.values() if f['has_try'])
    
    report += f"  - Funções SELECT: {select_only}"
    report += f"\n  - Funções UPDATE/INSERT: {update_funcs}"
    report += f"\n  - Com try/except: {try_except_funcs}"
    
    report += "\n\nFUNÇÕES PARA REFATORAR:\n"
    report += "-" * 80 + "\n"
    
    for i, (func_name, info) in enumerate(sorted(functions.items())[:15], 1):
        type_label = "SELECT" if (info['has_fetchone'] or info['has_fetchall']) else "UPDATE"
        if info['has_try']:
            type_label += " [try/except]"
        
        report += f"{i:2d}. {func_name:30s} | {type_label}\n"
    
    if len(functions) > 15:
        report += f"    ... e {len(functions) - 15} mais\n"
    
    report += "\n" + "="*80 + "\n"
    report += "BENEFÍCIOS DA REFATORAÇÃO:\n"
    report += "  ✓ Remover ~400-500 linhas de boilerplate\n"
    report += "  ✓ Eliminar vazamento de recursos (conexões não fechadas)\n"
    report += "  ✓ Adicionar logging automático de operações\n"
    report += "  ✓ Melhorar tratamento de erros\n"
    report += "  ✓ Aumentar segurança\n"
    
    report += "\n" + "="*80 + "\n"
    report += "ESTRATÉGIA RECOMENDADA:\n"
    report += f"  1. Refatorar {select_only} funções SELECT (mais simples)\n"
    report += f"  2. Refatorar {update_funcs} funções UPDATE/INSERT\n"
    report += f"  3. Revisar {try_except_funcs} funções com try/except\n"
    report += "  4. Testar cada grupo de funcionalidade\n"
    report += "  5. Fazer commit final\n"
    
    return report


def create_refactoring_plan() -> str:
    """Cria plano de refatoração com exemplos."""
    plan = """
╔════════════════════════════════════════════════════════════════════════════╗
║           PLANO DE REFATORAÇÃO - PADRÕES DE SUBSTITUIÇÃO                  ║
╚════════════════════════════════════════════════════════════════════════════╝

PADRÃO 1: SELECT simples (fetchone)
──────────────────────────────────────────────────────────────────────────────

ANTES:
    def verificar_login(usuario, senha):
        conn = get_connection()
        cursor = conn.cursor()
        
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cursor.execute(
            "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", 
            (usuario, senha_hash)
        )
        result = cursor.fetchone()
        conn.close()
        
        return result

DEPOIS:
    from connection_manager import execute_query
    
    def verificar_login(usuario, senha):
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        return execute_query(
            "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", 
            (usuario, senha_hash),
            fetch_one=True
        )


PADRÃO 2: SELECT com fetchall
──────────────────────────────────────────────────────────────────────────────

ANTES:
    def obter_projetos_ativos():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome")
        projetos = [row[0] for row in cursor.fetchall()]
        conn.close()
        return projetos

DEPOIS:
    from connection_manager import execute_query
    
    def obter_projetos_ativos():
        results = execute_query(
            "SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome",
            fetch_one=False
        )
        return [row[0] for row in results] if results else []


PADRÃO 3: INSERT/UPDATE com commit
──────────────────────────────────────────────────────────────────────────────

ANTES:
    def registrar_ponto(usuario, tipo, ...):
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            INSERT INTO registros_ponto (...)
            VALUES ({placeholders})
        ''', (usuario, ...))
        
        conn.commit()
        conn.close()
        
        return data_hora_registro

DEPOIS:
    from connection_manager import execute_update
    
    def registrar_ponto(usuario, tipo, ...):
        success = execute_update(
            f'''
                INSERT INTO registros_ponto (...)
                VALUES ({placeholders})
            ''',
            (usuario, ...)
        )
        
        if success:
            return data_hora_registro
        else:
            return None


PADRÃO 4: Com processamento após query
──────────────────────────────────────────────────────────────────────────────

ANTES:
    def obter_registros_usuario(usuario, data_inicio=None, data_fim=None):
        conn = get_connection()
        cursor = conn.cursor()
        
        query = f"SELECT * FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER}"
        params = [usuario]
        
        if data_inicio and data_fim:
            query += f" AND DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}"
            params.extend([data_inicio, data_fim])
        
        query += " ORDER BY data_hora DESC"
        
        cursor.execute(query, params)
        registros = cursor.fetchall()
        conn.close()
        
        return registros

DEPOIS:
    from connection_manager import execute_query
    
    def obter_registros_usuario(usuario, data_inicio=None, data_fim=None):
        query = f"SELECT * FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER}"
        params = [usuario]
        
        if data_inicio and data_fim:
            query += f" AND DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}"
            params.extend([data_inicio, data_fim])
        
        query += " ORDER BY data_hora DESC"
        
        return execute_query(query, tuple(params))


PADRÃO 5: Com try/except
──────────────────────────────────────────────────────────────────────────────

ANTES:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
    except Exception as e:
        logger.error(f"Erro ao executar query: {e}")
        result = []
    finally:
        if conn:
            conn.close()
    
    return result

DEPOIS:
    from connection_manager import execute_query
    from error_handler import log_error
    
    result = execute_query(query)
    if result is None:
        # log_error já foi chamado automaticamente pelo execute_query
        return []
    
    return result


IMPORTS A ADICIONAR NO TOPO:
──────────────────────────────────────────────────────────────────────────────

from connection_manager import (
    execute_query,
    execute_update,
    safe_cursor,
    safe_database_connection,
)

from error_handler import (
    log_error,
    log_database_operation,
    get_logger,
)

# Se necessário manter logger existente, usar get_logger:
# logger = get_logger(__name__)


REMOÇÃO DE IMPORTS:
──────────────────────────────────────────────────────────────────────────────

Remover ou comentar:
    from database_postgresql import get_connection, ...
    from database import init_db, get_connection
    get_db_connection = get_connection  # Não mais necessário


VALIDAÇÃO APÓS REFATORAÇÃO:
──────────────────────────────────────────────────────────────────────────────

□ Executar syntax check: python -m py_compile app_v5_final.py
□ Verificar imports: python -c "import app_v5_final"
□ Executar testes: pytest tests/
□ Verificar no Streamlit: streamlit run app_v5_final.py


PRÓXIMOS PASSOS:
──────────────────────────────────────────────────────────────────────────────

1. Gerar relatório de refatoração: python refactor_app_v5.py --report
2. Revisar padrões acima
3. Escolher estratégia (manual com regex, ou script automático)
4. Executar refatoração
5. Testar e validar
6. Fazer commit
"""
    
    return plan


if __name__ == "__main__":
    filepath = "ponto_esa_v5/app_v5_final.py"
    
    print(analyze_connection_patterns.__doc__)
    print("\nGerando análise do arquivo...")
    
    if os.path.exists(filepath):
        report = generate_refactoring_report(filepath)
        print(report)
        
        print("\n" + create_refactoring_plan())
    else:
        print(f"Arquivo não encontrado: {filepath}")
