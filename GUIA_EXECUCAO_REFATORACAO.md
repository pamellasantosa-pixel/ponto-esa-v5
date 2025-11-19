# 🚀 GUIA DE EXECUÇÃO - Refatoração Automática Step-by-Step

**Data:** 19 de novembro de 2025  
**Objetivo:** Completar refatoração em 4-5 sessões de 2 horas cada  
**Risco:** BAIXO (com backup)

---

## 📋 CHECKLIST PRÉ-EXECUÇÃO

- [ ] Leitura completa dos 3 relatórios
  - ✅ `RELATORIO_REFATORACAO_CONTEXT_MANAGERS.md` (estrutura geral)
  - ✅ `EXEMPLOS_REFATORACAO_COPY_PASTE.md` (exemplos práticos)
  - ✅ Este arquivo (execução passo-a-passo)

- [ ] Backup do arquivo original
  ```powershell
  Copy-Item "ponto_esa_v5_final.py" "ponto_esa_v5_final.py.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
  ```

- [ ] Verificação de dependências
  - [ ] `connection_manager.py` existe e está correto
  - [ ] `error_handler.py` existe e está correto
  - [ ] `migrations_helper.py` existe (se necessário)

- [ ] Ambiente Python pronto
  - [ ] Venv ativado
  - [ ] Imports disponíveis

---

## 🎯 FASE 0: PREPARAÇÃO (15 minutos)

### Passo 1: Fazer backup do arquivo original
```powershell
cd "c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5"

# Backup com timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "app_v5_final.py" "app_v5_final.py.backup.$timestamp.bak"

Write-Host "✅ Backup criado: app_v5_final.py.backup.$timestamp.bak"
```

### Passo 2: Verificar módulos de suporte
```python
# Abrir Python REPL e testar
from connection_manager import execute_query, execute_update, safe_cursor
from error_handler import log_error, log_database_operation, get_logger

print("✅ connection_manager importado com sucesso")
print("✅ error_handler importado com sucesso")
```

### Passo 3: Criar branch de trabalho (Git)
```powershell
cd "c:\Users\lf\OneDrive\ponto_esa_v5_implemented"

git status
git checkout -b refactor/context-managers
```

---

## 🔧 FASE 1: SIMPLE SELECT fetchone() (2 horas)

**Objetivo:** Refatorar 14 funções de SELECT simples que retornam um registro

### Funções a Refatorar:
1. `verificar_login()` - Linha 435
2. Outras funções que usam `fetchone()`

### Estratégia:
- Usar padrão uniforme: `execute_query(sql, params, fetch_one=True)`
- Substituir try/finally
- Adicionar imports

### Passo 1: Adicionar imports no topo

**Localizar (linha ~30):**
```python
import pytz  # Para gerenciar fusos horários
import logging
```

**Adicionar após:**
```python
# ===== CONNECTION MANAGEMENT =====
from connection_manager import execute_query, execute_update, safe_cursor
from error_handler import log_error, log_database_operation, get_logger
```

### Passo 2: Refatorar função #1 - verificar_login()

**Localizar (linha 435):**
```python
def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    conn = get_connection()
    cursor = conn.cursor()

    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    cursor.execute(
        "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha_hash))
    result = cursor.fetchone()
    conn.close()

    return result
```

**Substituir por:**
```python
def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return execute_query(
        "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s",
        (usuario, senha_hash),
        fetch_one=True
    )
```

### Passo 3: Validar
```python
# Testar em Python REPL
from app_v5_final import verificar_login

result = verificar_login("usuario_teste", "senha_teste")
print(f"✅ Function works: {result is None or isinstance(result, tuple)}")
```

### Passo 4: Commit
```powershell
git add ponto_esa_v5/app_v5_final.py
git commit -m "refactor: simplify verificar_login() with execute_query"
```

---

## 🔧 FASE 2: SIMPLE SELECT fetchall() (1.5 horas)

**Objetivo:** Refatorar 16 funções de SELECT que retornam múltiplos registros

### Funções Principais:
1. `obter_projetos_ativos()` - Linha 449
2. `obter_usuarios_para_aprovacao()` - Linha 520
3. `obter_usuarios_ativos()` - Linha 531
4. E mais 13 similares

### Passo 1: Refatorar obter_projetos_ativos()

**ANTES (Linha 449):**
```python
def obter_projetos_ativos():
    """Obtém lista de projetos ativos"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome")
    projetos = [row[0] for row in cursor.fetchall()]
    conn.close()
    return projetos
```

**DEPOIS:**
```python
def obter_projetos_ativos():
    """Obtém lista de projetos ativos"""
    rows = execute_query(
        "SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome"
    )
    return [row[0] for row in (rows or [])]
```

### Passo 2: Batch refactor com busca/replace

Use o VS Code Find & Replace:

**Buscar padrão:**
```regex
conn = get_connection\(\)\s+cursor = conn\.cursor\(\)\s+cursor\.execute\("SELECT ([^"]+)" FROM ([^"]+)"\)\s+(\w+) = \[row\[(\d+)\] for row in cursor\.fetchall\(\)\]\s+conn\.close\(\)\s+return (\w+)
```

**Este padrão é complexo, então fazer manualmente ou com script Python**

### Passo 3: Script Python para batch replace

```python
# refactor_phase2.py
import re

with open('ponto_esa_v5/app_v5_final.py', 'r') as f:
    content = f.read()

# Pattern 1: Simple fetchall with list comprehension
pattern1 = r'''conn = get_connection\(\)
\s+cursor = conn\.cursor\(\)
\s+cursor\.execute\("([^"]+)"\)
\s+(\w+) = \[row\[(\d+)\] for row in cursor\.fetchall\(\)\]
\s+conn\.close\(\)
\s+return \2'''

replacement1 = r'''rows = execute_query(
        "\1"
    )
    return [row[\3] for row in (rows or [])]'''

content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)

with open('ponto_esa_v5/app_v5_final.py', 'w') as f:
    f.write(content)

print("✅ Phase 2 refactoring complete")
```

---

## 🔧 FASE 3: INSERT/UPDATE/DELETE (1.5 horas)

**Objetivo:** Refatorar 18 funções de INSERT/UPDATE/DELETE

### Funções Principais:
1. `registrar_ponto()` - Linha 459
2. Atualizações inline em funções UI
3. Inserções em horas extras
4. E mais

### Passo 1: Padrão básico

**ANTES:**
```python
conn = get_connection()
cursor = conn.cursor()

try:
    cursor.execute("INSERT INTO tabela (...) VALUES (...)", params)
    conn.commit()
    # ... código ...
except Exception as e:
    logger.error(f"Erro: {e}")
    if conn:
        conn.rollback()
finally:
    if conn:
        conn.close()
```

**DEPOIS:**
```python
success = execute_update(
    "INSERT INTO tabela (...) VALUES (...)", 
    params
)
if success:
    # ... código ...
else:
    st.error("Erro ao executar operação")
```

### Passo 2: Refatorar registrar_ponto()

**Substitua:**
```python
# Linhas 459-493
def registrar_ponto(usuario, tipo, modalidade, projeto, atividade, 
                   data_registro=None, hora_registro=None, latitude=None, longitude=None):
    """Registra ponto do usuário com GPS real"""
    conn = get_connection()
    cursor = conn.cursor()

    # ... [processamento de data/hora MANTER] ...
    
    placeholders = ', '.join([SQL_PLACEHOLDER] * 9)
    cursor.execute(f'''
        INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
        VALUES ({placeholders})
    ''', (usuario, data_hora_registro, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude))

    conn.commit()
    conn.close()

    return data_hora_registro
```

**Por:**
```python
def registrar_ponto(usuario, tipo, modalidade, projeto, atividade, 
                   data_registro=None, hora_registro=None, latitude=None, longitude=None):
    """Registra ponto do usuário com GPS real"""
    
    # ... [processamento de data/hora MANTER] ...
    
    placeholders = ', '.join([SQL_PLACEHOLDER] * 9)
    success = execute_update(
        f'''INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
            VALUES ({placeholders})''',
        (usuario, data_hora_registro, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
    )

    return data_hora_registro if success else None
```

### Passo 3: Commit Phase 3
```powershell
git add ponto_esa_v5/app_v5_final.py
git commit -m "refactor: convert INSERT/UPDATE/DELETE to execute_update"
```

---

## 🔧 FASE 4: MULTIPLE QUERIES (2 horas)

**Objetivo:** Refatorar 8 funções com múltiplas queries em transação

### Funções Principais:
1. `exibir_widget_notificacoes()` - Linha 1181
2. `validar_limites_hora_extra()` - Linha 615 (complexa)
3. Relatórios
4. E mais

### Passo 1: Padrão com safe_cursor()

**ANTES:**
```python
conn = get_connection()
cursor = conn.cursor()

try:
    cursor.execute("SELECT COUNT(*) FROM tabela1 WHERE ...")
    count1 = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tabela2 WHERE ...")
    count2 = cursor.fetchone()[0]
    
    conn.close()
    
    total = count1 + count2
    # ... processamento ...
    
except Exception as e:
    logger.error(f"Erro: {e}")
finally:
    if conn:
        conn.close()
```

**DEPOIS:**
```python
from connection_manager import safe_cursor

try:
    with safe_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM tabela1 WHERE ...")
        count1 = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tabela2 WHERE ...")
        count2 = cursor.fetchone()[0]
        
        total = count1 + count2
        # ... processamento ...
        
except Exception as e:
    log_error("Erro ao buscar dados", e)
```

### Passo 2: Refatorar exibir_widget_notificacoes()

**Localizar (linha 1181) e refatorar conforme exemplo**

### Passo 3: Commit Phase 4
```powershell
git add ponto_esa_v5/app_v5_final.py
git commit -m "refactor: use safe_cursor for multi-query operations"
```

---

## 🔧 FASE 5: COMPLEX OPERATIONS (1.5 horas)

**Objetivo:** Refatorar 18+ funções com lógica complexa

### Exemplos:
1. Solicitação de hora extra (linha 805)
2. Aprovação de horas
3. Operações com notificações
4. E mais

### Passo 1: Manter lógica customizada

Nestas operações, NÃO SUBSTITUIR:
- ✅ Lógica de validação
- ✅ Lógica de negócio
- ✅ Tratamento de UI (Streamlit)

**APENAS SUBSTITUIR:**
- 🔄 get_connection()
- 🔄 try/except/finally padrão
- 🔄 conn.commit() / conn.close()

### Passo 2: Template para complex ops

```python
from connection_manager import safe_cursor
from error_handler import log_error

def operacao_complexa():
    """Descrição"""
    
    try:
        with safe_cursor() as cursor:
            # Query 1
            cursor.execute("SELECT ...")
            resultado1 = cursor.fetchone()
            
            # Processar resultado1
            if resultado1:
                # Query 2
                cursor.execute("UPDATE ... VALUES ...")
            
            # Lógica customizada
            if condicao:
                # Query 3
                cursor.execute("INSERT ...")
            
            # Retornar resultado
            return True
            
    except Exception as e:
        log_error("Erro em operacao_complexa", e, {"contexto": "dados"})
        return False
```

### Passo 3: Refatorar exemplos principais

1. `exibir_hora_extra_em_andamento()` - Linha 868
2. Operação inline de solicitar hora extra - Linha 805
3. E mais

### Passo 4: Commit Phase 5
```powershell
git add ponto_esa_v5/app_v5_final.py
git commit -m "refactor: complex operations with safe_cursor and error handling"
```

---

## ✅ FASE 6: VALIDAÇÃO (1 hora)

### Passo 1: Syntax Check
```python
# syntax_check.py
import py_compile
import sys

try:
    py_compile.compile('ponto_esa_v5/app_v5_final.py', doraise=True)
    print("✅ Syntax is valid!")
except py_compile.PyCompileError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)
```

### Passo 2: Import Check
```python
# import_check.py
import sys
sys.path.insert(0, 'ponto_esa_v5')

try:
    import app_v5_final
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
```

### Passo 3: Teste de Funções Críticas
```python
# test_refactored.py
import sys
sys.path.insert(0, 'ponto_esa_v5')

from app_v5_final import (
    verificar_login,
    obter_projetos_ativos,
    obter_usuarios_ativos,
    registrar_ponto
)

# Teste 1: verificar_login
result = verificar_login("test", "test")
assert result is None or isinstance(result, (tuple, list)), "verificar_login failed"
print("✅ verificar_login works")

# Teste 2: obter_projetos_ativos
result = obter_projetos_ativos()
assert isinstance(result, list), "obter_projetos_ativos failed"
print("✅ obter_projetos_ativos works")

# Teste 3: obter_usuarios_ativos
result = obter_usuarios_ativos()
assert isinstance(result, list), "obter_usuarios_ativos failed"
print("✅ obter_usuarios_ativos works")

print("\n✅ All critical functions working!")
```

### Passo 4: Comparar linhas

```powershell
# Verificar que nenhuma lógica foi removida
$before = (Get-Content "ponto_esa_v5/app_v5_final.py.backup.*.bak" -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
$after = (Get-Content "ponto_esa_v5/app_v5_final.py" | Measure-Object -Line).Lines

Write-Host "✅ Linhas antes: $before"
Write-Host "✅ Linhas depois: $after"
Write-Host "✅ Diferença: $($before - $after) linhas removidas (esperado 300-400)"
```

### Passo 5: Commit & Push
```powershell
git add ponto_esa_v5/app_v5_final.py
git commit -m "refactor: complete context manager refactoring - all 58 calls updated"
git push origin refactor/context-managers
```

---

## 🎯 TIMELINE RECOMENDADO

**Sessão 1 (2h):** Fase 1 + Preparação extras  
**Sessão 2 (2h):** Fase 2  
**Sessão 3 (2h):** Fase 3 + Fase 4 (parcial)  
**Sessão 4 (2h):** Fase 4 (finalizar) + Fase 5  
**Sessão 5 (1h):** Fase 6 (validação) + Deploy  

**Total:** 9 horas (com breaks)

---

## 🚨 TROUBLESHOOTING DURANTE EXECUÇÃO

### Erro: "NameError: name 'execute_query' is not defined"
**Solução:** Verificar imports no topo do arquivo
```python
from connection_manager import execute_query, execute_update, safe_cursor
```

### Erro: "TypeError: execute_query() takes X positional arguments but Y were given"
**Solução:** Verificar assinatura de função
```python
# ✅ Correto
execute_query(sql_query, params, fetch_one=True)

# ❌ Incorreto
execute_query(sql_query, fetch_one=True, params)
```

### Erro: "AttributeError: 'NoneType' object has no attribute '__getitem__'"
**Solução:** Adicionar fallback
```python
# ❌ Quebra se None
result[0]

# ✅ Seguro
(result or [None])[0]
```

### Query não funciona após refactor
**Checklist:**
1. SQL preservado exatamente?
2. Parâmetros em ordem correta?
3. SQL_PLACEHOLDER correto?
4. Params convertido para tuple?

---

## ✨ APÓS A REFATORAÇÃO

### Benefícios Alcançados:
- ✅ 300-400 linhas de boilerplate removidas
- ✅ Error handling centralizado
- ✅ Logging automático de todas operações DB
- ✅ Resource management (close/rollback) automático
- ✅ Código mais legível e manutenível
- ✅ Menos bugs potenciais

### Próximas Melhorias (Opcional):
1. Adicionar caching com `@cache_resource` para operações read-only
2. Implementar connection pooling se necessário
3. Adicionar metrics de performance
4. Migration para ORM (SQLAlchemy) em longo prazo

---

**Status:** 🟢 PRONTO PARA EXECUTAR

Todos os documentos de suporte estão preparados. Comece pela Fase 1!
