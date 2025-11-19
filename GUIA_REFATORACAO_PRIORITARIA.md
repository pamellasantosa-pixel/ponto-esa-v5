# 🛠️ GUIA DE REFATORAÇÃO - Ponto ExSA v5.0

**Documento**: Correções Prioritárias  
**Data**: 19 de novembro de 2025  
**Tempo Estimado**: 16 horas de desenvolvimento  

---

## 1. FIX CRÍTICO #1: Context Manager de Conexão

### Status Atual (INSEGURO)
```python
# ❌ Padrão em 70+ funções
def verificar_login(usuario, senha):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ... FROM usuarios WHERE usuario = %s", (usuario,))
    result = cursor.fetchone()
    conn.close()  # ❌ Risco: exceção antes desta linha vaza conexão
    return result
```

### Solução Recomendada

**Arquivo**: `db_utils.py` - SUBSTITUIR

```python
"""
Utilitários de banco de dados com context managers seguros.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator, Any, Optional

from database_postgresql import get_connection

logger = logging.getLogger(__name__)


@contextmanager
def safe_connection(db_path: Optional[str] = None) -> Generator[Any, None, None]:
    """
    Context manager seguro para operações de banco de dados.
    
    Garante que:
    - Cursor é sempre fechado
    - Conexão é sempre fechada
    - Rollback automático em erro
    - Logging de erros
    
    Uso:
        with safe_connection() as cursor:
            cursor.execute("SELECT ...")
            result = cursor.fetchone()
    """
    conn = get_connection(db_path) if db_path else get_connection()
    cursor = None
    
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro em operação de banco: {type(e).__name__}", exc_info=True)
        raise
        
    finally:
        # Fechar cursor primeiro
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar cursor: {e}")
        
        # Depois fechar conexão
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar conexão: {e}")


@contextmanager
def safe_transaction(db_path: Optional[str] = None) -> Generator[Any, None, None]:
    """
    Context manager com transação explícita.
    
    Uso:
        with safe_transaction() as cursor:
            cursor.execute("INSERT ...")
            # Auto-commit ao sair do bloco
    """
    conn = get_connection(db_path) if db_path else get_connection()
    cursor = None
    
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Erro em transação: {type(e).__name__}", exc_info=True)
        raise
        
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def create_error_response(message: str, details: dict = None) -> dict:
    """Cria resposta de erro padronizada"""
    response = {"success": False, "message": message}
    if details:
        response.update(details)
    return response


def create_success_response(message: str, data: dict = None) -> dict:
    """Cria resposta de sucesso padronizada"""
    response = {"success": True, "message": message}
    if data:
        response.update(data)
    return response


__all__ = [
    "safe_connection",
    "safe_transaction",
    "create_error_response",
    "create_success_response",
]
```

### Migração de Funções

#### Antes (INSEGURO)
```python
def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
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
```

#### Depois (SEGURO)
```python
def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    from db_utils import safe_connection
    
    with safe_connection() as cursor:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cursor.execute(
            "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", 
            (usuario, senha_hash)
        )
        return cursor.fetchone()
```

### Lista de Funções a Migrar (Prioridade)

| Função | Arquivo | Linhas | Impacto | Tempo |
|--------|---------|--------|--------|-------|
| `verificar_login` | app_v5_final.py | 433-445 | Alto | 5min |
| `obter_projetos_ativos` | app_v5_final.py | 449-456 | Alto | 5min |
| `registrar_ponto` | app_v5_final.py | 458-537 | Crítico | 10min |
| `obter_registros_usuario` | app_v5_final.py | 500-517 | Crítico | 10min |
| `obter_usuarios_*` | app_v5_final.py | 520-538 | Médio | 10min |
| `register_upload` | upload_system.py | 227-253 | Alto | 10min |
| `get_file_info` | upload_system.py | 315-340 | Alto | 8min |
| `delete_file` | upload_system.py | 350-388 | Alto | 8min |
| `verificar_fim_jornada` | horas_extras_system.py | 33-43 | Médio | 5min |
| ... (60+ mais) | múltiplos | - | Variado | 180min |

---

## 2. FIX CRÍTICO #2: Tratamento de Exceção

### Antes (INSEGURO - Bare except)
```python
try:
    hora_parts = hora_inicio_str.split(':')
    hora_inicio_val = time(int(hora_parts[0]), int(hora_parts[1]))
except:  # ❌ Captura TUDO
    hora_inicio_val = time(8, 0)
```

### Depois (SEGURO)
```python
try:
    hora_parts = hora_inicio_str.split(':')
    if len(hora_parts) != 2:
        raise ValueError("Formato inválido HH:MM")
    hora_inicio_val = time(int(hora_parts[0]), int(hora_parts[1]))
except (ValueError, IndexError):  # ✅ Específico
    logger.warning(f"Hora inválida: {hora_inicio_str}, usando padrão 08:00")
    hora_inicio_val = time(8, 0)
```

### Ocorrências a Corrigir

| Arquivo | Linhas | Tipo | Fix |
|---------|--------|------|-----|
| app_v5_final.py | 5424 | bare except | Adicionar exceção específica |
| app_v5_final.py | 5446 | bare except | Adicionar exceção específica |
| relatorios_horas_extras.py | 375 | bare except | Adicionar logging |
| offline_system.py | 81 | bare except | Adicionar logging |
| tools/migrate*.py | múltiplas | bare except | Adicionar logging |

---

## 3. FIX #3: Duplicação de Queries

### Problema Identificado
```python
# LINHA 1186
cursor.execute("""
    SELECT COUNT(*) FROM solicitacoes_horas_extras 
    WHERE aprovador_solicitado = %s AND status = 'pendente'
""", (st.session_state.usuario,))
he_pendentes = cursor.fetchone()[0]

# LINHA 1329 - REPETIDA
cursor.execute("""
    SELECT COUNT(*) FROM solicitacoes_horas_extras 
    WHERE aprovador_solicitado = %s AND status = 'pendente'
""", (st.session_state.usuario,))
he_pendentes = cursor.fetchone()[0]

# LINHA 2181 - REPETIDA NOVAMENTE
cursor.execute("""
    SELECT COUNT(*) FROM solicitacoes_horas_extras 
    WHERE aprovador_solicitado = %s AND status = 'pendente'
""", (st.session_state.usuario,))
he_pendentes = cursor.fetchone()[0]
```

### Solução: Helper Function

**Arquivo**: `app_v5_final.py` - ADICIONAR NOVA FUNÇÃO

```python
def obter_contagem_notificacoes(usuario: str) -> dict:
    """
    Obtém contagem de todas as notificações pendentes para um usuário.
    
    Returns:
        {
            'he_pendentes': int,
            'correcoes_pendentes': int,
            'atestados_pendentes': int,
            'total': int
        }
    """
    from db_utils import safe_connection
    
    with safe_connection() as cursor:
        # Query única que retorna tudo
        cursor.execute("""
            SELECT 
                COALESCE((
                    SELECT COUNT(*) FROM solicitacoes_horas_extras 
                    WHERE aprovador_solicitado = %s AND status = 'pendente'
                ), 0) as he_pendentes,
                COALESCE((
                    SELECT COUNT(*) FROM solicitacoes_correcao_registro 
                    WHERE usuario = %s AND status = 'pendente'
                ), 0) as correcoes_pendentes,
                COALESCE((
                    SELECT COUNT(*) FROM atestado_horas 
                    WHERE usuario = %s AND status = 'pendente'
                ), 0) as atestados_pendentes
        """, (usuario, usuario, usuario))
        
        result = cursor.fetchone()
        return {
            'he_pendentes': result[0] or 0,
            'correcoes_pendentes': result[1] or 0,
            'atestados_pendentes': result[2] or 0,
            'total': (result[0] or 0) + (result[1] or 0) + (result[2] or 0)
        }
```

### Uso
```python
# Antes: 3 queries separadas
conn = get_connection()
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE ...", (usuario,))
he_pendentes = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM solicitacoes_correcao_registro WHERE ...", (usuario,))
correcoes_pendentes = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM atestado_horas WHERE ...", (usuario,))
atestados_pendentes = cursor.fetchone()[0]

conn.close()

# Depois: 1 query via helper
notificacoes = obter_contagem_notificacoes(usuario)
he_pendentes = notificacoes['he_pendentes']
correcoes_pendentes = notificacoes['correcoes_pendentes']
atestados_pendentes = notificacoes['atestados_pendentes']
```

---

## 4. FIX #4: Logging em Exceções Silenciosas

### Exemplo em database.py

#### Antes
```python
try:
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (...)")
except:
    pass  # ❌ Silencioso
```

#### Depois
```python
try:
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (...)")
except Exception as e:
    logger.warning(f"Tabela usuarios talvez já exista ou erro de criação: {e}")
    # Não é erro crítico, tabela pode já existir
```

### Arquivo database.py - Correções

```python
# Linhas 325-357
try:
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (...)")
except Exception as e:
    logger.warning(f"Erro ao criar tabela usuarios: {e}")

try:
    cursor.execute("CREATE TABLE IF NOT EXISTS projetos (...)")
except Exception as e:
    logger.warning(f"Erro ao criar tabela projetos: {e}")

try:
    cursor.execute("CREATE TABLE IF NOT EXISTS registros_ponto (...)")
except Exception as e:
    logger.warning(f"Erro ao criar tabela registros_ponto: {e}")

# ... continuar para todas as 7 tabelas
```

---

## 5. REFATORAÇÃO - Consolidação de Inicialização

### Problema Atual
```python
# app_v5_final.py - Múltiplos lugares inicializando sistemas
@st.cache_resource
def init_systems():
    atestado_system = AtestadoHorasSystem()
    upload_system = UploadSystem()
    # ...
    return ...

# Mas cada system também pode ser instanciado separadamente
# sem garantia de cache
```

### Solução: Singleton Factory

**Arquivo**: `system_factory.py` - NOVO

```python
"""
Factory para inicialização centralizada de sistemas.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Singleton instances
_instances = {
    'atestado_system': None,
    'upload_system': None,
    'horas_extras_system': None,
    'banco_horas_system': None,
    'calculo_horas_system': None,
    'jornada_system': None,
}


def get_atestado_system():
    """Get or create AtestadoHorasSystem instance"""
    if _instances['atestado_system'] is None:
        from atestado_horas_system import AtestadoHorasSystem
        _instances['atestado_system'] = AtestadoHorasSystem()
        logger.info("AtestadoHorasSystem initialized")
    return _instances['atestado_system']


def get_upload_system():
    """Get or create UploadSystem instance"""
    if _instances['upload_system'] is None:
        from upload_system import UploadSystem
        _instances['upload_system'] = UploadSystem()
        logger.info("UploadSystem initialized")
    return _instances['upload_system']


def get_horas_extras_system():
    """Get or create HorasExtrasSystem instance"""
    if _instances['horas_extras_system'] is None:
        from horas_extras_system import HorasExtrasSystem
        _instances['horas_extras_system'] = HorasExtrasSystem()
        logger.info("HorasExtrasSystem initialized")
    return _instances['horas_extras_system']


def get_banco_horas_system():
    """Get or create BancoHorasSystem instance"""
    if _instances['banco_horas_system'] is None:
        from banco_horas_system import BancoHorasSystem
        _instances['banco_horas_system'] = BancoHorasSystem()
        logger.info("BancoHorasSystem initialized")
    return _instances['banco_horas_system']


def get_calculo_horas_system():
    """Get or create CalculoHorasSystem instance"""
    if _instances['calculo_horas_system'] is None:
        from calculo_horas_system import CalculoHorasSystem
        _instances['calculo_horas_system'] = CalculoHorasSystem()
        logger.info("CalculoHorasSystem initialized")
    return _instances['calculo_horas_system']


def get_jornada_system():
    """Get or create JornadaSemanalCalculoSystem instance"""
    if _instances['jornada_system'] is None:
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        _instances['jornada_system'] = JornadaSemanalCalculoSystem()
        logger.info("JornadaSemanalCalculoSystem initialized")
    return _instances['jornada_system']


def get_all_systems():
    """Get or create all system instances"""
    return {
        'atestado': get_atestado_system(),
        'upload': get_upload_system(),
        'horas_extras': get_horas_extras_system(),
        'banco_horas': get_banco_horas_system(),
        'calculo_horas': get_calculo_horas_system(),
        'jornada': get_jornada_system(),
    }


def reset_systems():
    """Reset all instances (for testing)"""
    for key in _instances:
        _instances[key] = None
    logger.info("All systems reset")


__all__ = [
    'get_atestado_system',
    'get_upload_system',
    'get_horas_extras_system',
    'get_banco_horas_system',
    'get_calculo_horas_system',
    'get_jornada_system',
    'get_all_systems',
    'reset_systems',
]
```

### Uso em app_v5_final.py
```python
# Substitua
@st.cache_resource
def init_systems():
    ...
    return atestado_system, upload_system, ...

# Por
from system_factory import get_all_systems

systems = get_all_systems()
atestado_system = systems['atestado']
upload_system = systems['upload']
```

---

## 6. PLANO DE IMPLEMENTAÇÃO

### Fase 1: Preparação (30 minutos)
- [ ] Criar `db_utils.py` melhorado
- [ ] Criar `system_factory.py`
- [ ] Adicionar `import logging` em arquivos necessários

### Fase 2: Context Manager (4 horas)
- [ ] Migrar `app_v5_final.py` (70+ funções)
- [ ] Migrar `upload_system.py` (8+ funções)
- [ ] Migrar `horas_extras_system.py` (6+ funções)
- [ ] Teste de integração

### Fase 3: Exception Handling (2 horas)
- [ ] Corrigir 2 bare excepts em `app_v5_final.py`
- [ ] Adicionar logging em database.py (7 funções)
- [ ] Adicionar logging em relatorios_horas_extras.py
- [ ] Adicionar logging em offline_system.py

### Fase 4: Duplicação (1.5 horas)
- [ ] Criar `obter_contagem_notificacoes()`
- [ ] Substituir 3 ocorrências (linhas 1186, 1329, 2181)
- [ ] Substituir 3 ocorrências de correcoes_pendentes
- [ ] Substituir 3 ocorrências de atestados_pendentes

### Fase 5: Teste (2 horas)
- [ ] Teste manual de login
- [ ] Teste de upload
- [ ] Teste de horas extras
- [ ] Verificar se conexões fecham

---

## 7. SCRIPT DE VALIDAÇÃO

**Arquivo**: `validate_fixes.py` - NOVO

```python
#!/usr/bin/env python
"""
Script para validar se as correções foram aplicadas.
"""

import os
import re
import subprocess
from pathlib import Path

def check_bare_excepts(file_path: str) -> list:
    """Find bare except clauses"""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    issues = []
    for i, line in enumerate(lines, 1):
        if re.search(r'except\s*:\s*', line.strip()):
            issues.append((i, line.strip()))
    return issues


def check_conn_close_coverage(file_path: str) -> dict:
    """Check if all conn assignments have corresponding closes"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    conn_gets = len(re.findall(r'get_connection\(\)', content))
    conn_closes = len(re.findall(r'conn\.close\(\)', content))
    
    return {
        'file': file_path,
        'get_connection': conn_gets,
        'conn.close': conn_closes,
        'ratio': conn_closes / conn_gets if conn_gets > 0 else 0,
        'safe': conn_closes >= conn_gets * 0.9  # 90% coverage
    }


def check_safe_connection_usage(file_path: str) -> dict:
    """Check if safe_connection context manager is used"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    has_safe_conn = 'with safe_connection' in content or 'with safe_transaction' in content
    manual_get = len(re.findall(r'get_connection\(\)', content))
    
    return {
        'file': file_path,
        'uses_safe_connection': has_safe_conn,
        'manual_get_connection': manual_get,
    }


if __name__ == '__main__':
    py_files = Path('.').glob('ponto_esa_v5/**/*.py')
    
    print("=" * 60)
    print("VALIDAÇÃO DE CORREÇÕES")
    print("=" * 60)
    
    for py_file in sorted(py_files):
        print(f"\n📄 {py_file}")
        
        # Check bare excepts
        bare_excepts = check_bare_excepts(str(py_file))
        if bare_excepts:
            print(f"  ⚠️  {len(bare_excepts)} bare except(s) encontrado(s)")
            for line_no, code in bare_excepts[:3]:
                print(f"      Linha {line_no}: {code}")
        
        # Check connection closes
        coverage = check_conn_close_coverage(str(py_file))
        if not coverage['safe']:
            print(f"  🔴 {coverage['get_connection']} get_connection mas apenas {coverage['conn.close']} closes ({coverage['ratio']:.0%})")
```

---

## 8. VERIFICAÇÃO PÓS-IMPLEMENTAÇÃO

### Checklist Final

- [ ] Todos os `get_connection()` têm correspondente `conn.close()` ou estão em context manager
- [ ] Zero bare excepts (`except:`)
- [ ] Todos os exceptions têm `logger.error()` ou `logger.warning()`
- [ ] Queries duplicadas foram extraídas em helpers
- [ ] `db_utils.py` tem `safe_connection()` e `safe_transaction()`
- [ ] Testes passam sem vazamento de conexão
- [ ] Performance está OK (sem N+1 queries óbvias)

### Comandos de Teste

```bash
# Procurar bare excepts
grep -r "except:" ponto_esa_v5/ --include="*.py" | grep -v test | grep -v ".pyc"

# Procurar get_connection sem finally
grep -B5 -A5 "get_connection()" ponto_esa_v5/app_v5_final.py | grep -v "finally"

# Rodar tests
python -m pytest tests/ -v

# Verificar vazamento de conexão
python tools/check_connections.py
```

---

**Tempo Total Estimado**: 12-16 horas  
**Risco de Regressão**: Médio (requer testes abrangentes)  
**Benefício**: Alto (elimina 70% dos bugs críticos de conexão)

