# 🔧 EXEMPLOS DE REFATORAÇÃO - Copy/Paste Ready

**Data:** 19 de novembro de 2025  
**Propósito:** Exemplos práticos e testados para refatoração automática

---

## 📌 PADRÃO 1: Simple SELECT fetchone()

### Exemplo #1.1 - verificar_login()

**ANTES (Linhas 435-447)**
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

**DEPOIS**
```python
from connection_manager import execute_query

def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    return execute_query(
        "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s",
        (usuario, senha_hash),
        fetch_one=True
    )
```

**Checklist:**
- ✅ Imports adicionados
- ✅ Query preservada exatamente igual
- ✅ Parâmetros preservados
- ✅ 11 linhas → 5 linhas

---

## 📌 PADRÃO 2: Simple SELECT fetchall()

### Exemplo #2.1 - obter_projetos_ativos()

**ANTES (Linhas 449-455)**
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

**DEPOIS**
```python
from connection_manager import execute_query

def obter_projetos_ativos():
    """Obtém lista de projetos ativos"""
    rows = execute_query(
        "SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome"
    )
    return [row[0] for row in (rows or [])]
```

**Checklist:**
- ✅ Query preservada
- ✅ List comprehension preservado
- ✅ Fallback para list vazia se None
- ✅ 8 linhas → 5 linhas

---

### Exemplo #2.2 - obter_usuarios_para_aprovacao()

**ANTES (Linhas 520-526)**
```python
def obter_usuarios_para_aprovacao():
    """Obtém lista de usuários que podem aprovar horas extras"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo")
    usuarios = cursor.fetchall()
    conn.close()
    return [{"usuario": u[0], "nome": u[1] or u[0]} for u in usuarios]
```

**DEPOIS**
```python
from connection_manager import execute_query

def obter_usuarios_para_aprovacao():
    """Obtém lista de usuários que podem aprovar horas extras"""
    usuarios = execute_query(
        "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo"
    )
    return [
        {"usuario": u[0], "nome": u[1] or u[0]}
        for u in (usuarios or [])
    ]
```

**Checklist:**
- ✅ Dict comprehension preservado
- ✅ Fallback com `or []`
- ✅ 10 linhas → 6 linhas

---

## 📌 PADRÃO 3: Simple SELECT com Parâmetros Dinâmicos

### Exemplo #3.1 - obter_registros_usuario()

**ANTES (Linhas 497-517)**
```python
def obter_registros_usuario(usuario, data_inicio=None, data_fim=None):
    """Obtém registros de ponto do usuário"""
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
```

**DEPOIS**
```python
from connection_manager import execute_query

def obter_registros_usuario(usuario, data_inicio=None, data_fim=None):
    """Obtém registros de ponto do usuário"""
    query = f"SELECT * FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER}"
    params = [usuario]

    if data_inicio and data_fim:
        query += f" AND DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}"
        params.extend([data_inicio, data_fim])

    query += " ORDER BY data_hora DESC"

    return execute_query(query, tuple(params))
```

**Checklist:**
- ✅ Query construction preservada
- ✅ Params list handling correto
- ✅ Conversão para tuple() para execute_query
- ✅ 19 linhas → 12 linhas

---

## 📌 PADRÃO 4: INSERT com Commit

### Exemplo #4.1 - registrar_ponto()

**ANTES (Linhas 457-493, parcial)**
```python
def registrar_ponto(usuario, tipo, modalidade, projeto, atividade, 
                   data_registro=None, hora_registro=None, latitude=None, longitude=None):
    """Registra ponto do usuário com GPS real"""
    conn = get_connection()
    cursor = conn.cursor()

    # ... [processamento de data/hora omitido] ...
    
    placeholders = ', '.join([SQL_PLACEHOLDER] * 9)
    cursor.execute(f'''
        INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
        VALUES ({placeholders})
    ''', (usuario, data_hora_registro, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude))

    conn.commit()
    conn.close()

    return data_hora_registro
```

**DEPOIS**
```python
from connection_manager import execute_update

def registrar_ponto(usuario, tipo, modalidade, projeto, atividade, 
                   data_registro=None, hora_registro=None, latitude=None, longitude=None):
    """Registra ponto do usuário com GPS real"""
    
    # ... [processamento de data/hora omitido - IDÊNTICO] ...
    
    placeholders = ', '.join([SQL_PLACEHOLDER] * 9)
    success = execute_update(
        f'''INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
            VALUES ({placeholders})''',
        (usuario, data_hora_registro, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
    )

    return data_hora_registro if success else None
```

**Checklist:**
- ✅ SQL preservado exatamente igual
- ✅ Parâmetros preservados
- ✅ Execute_update retorna bool
- ✅ Verifica success antes de retornar
- ✅ 18 linhas → 13 linhas

---

## 📌 PADRÃO 5: UPDATE/DELETE com Try/Except

### Exemplo #5.1 - Atualizar usuário (adaptado de padrão comum)

**ANTES (Padrão genérico)**
```python
def atualizar_usuario(usuario_id, nome, email):
    """Atualiza dados do usuário"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE usuarios SET nome_completo = %s, email = %s WHERE id = %s",
            (nome, email, usuario_id)
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
```

**DEPOIS**
```python
from connection_manager import execute_update
from error_handler import log_error

def atualizar_usuario(usuario_id, nome, email):
    """Atualiza dados do usuário"""
    try:
        return execute_update(
            "UPDATE usuarios SET nome_completo = %s, email = %s WHERE id = %s",
            (nome, email, usuario_id)
        )
    except Exception as e:
        log_error("Erro ao atualizar usuário", e, {"usuario_id": usuario_id})
        return False
```

**Checklist:**
- ✅ Try/except preservado
- ✅ Error logging com contexto
- ✅ 17 linhas → 8 linhas

---

## 📌 PADRÃO 6: Multiple Queries em Transação

### Exemplo #6.1 - Contagem de notificações (Linhas 1181-1210)

**ANTES**
```python
def exibir_widget_notificacoes(horas_extras_system):
    """Exibe widget fixo de notificações pendentes"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Solicitações de horas extras pendentes
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        he_pendentes = cursor.fetchone()[0]
        
        # Solicitações de correção de registro pendentes
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_correcao_registro 
            WHERE usuario = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        correcoes_pendentes = cursor.fetchone()[0]
        
        # Atestados de horas pendentes
        cursor.execute("""
            SELECT COUNT(*) FROM atestado_horas 
            WHERE usuario = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        atestados_pendentes = cursor.fetchone()[0]
        
        conn.close()
        
        total_notificacoes = he_pendentes + correcoes_pendentes + atestados_pendentes
        
        if total_notificacoes > 0:
            # ... UI code ...
        
    except Exception as e:
        logger.error(f"Erro ao buscar notificações: {e}")
```

**DEPOIS**
```python
from connection_manager import safe_cursor
from error_handler import log_error

def exibir_widget_notificacoes(horas_extras_system):
    """Exibe widget fixo de notificações pendentes"""
    try:
        with safe_cursor() as cursor:
            # Solicitações de horas extras pendentes
            cursor.execute("""
                SELECT COUNT(*) FROM solicitacoes_horas_extras 
                WHERE aprovador_solicitado = %s AND status = 'pendente'
            """, (st.session_state.usuario,))
            he_pendentes = cursor.fetchone()[0]
            
            # Solicitações de correção de registro pendentes
            cursor.execute("""
                SELECT COUNT(*) FROM solicitacoes_correcao_registro 
                WHERE usuario = %s AND status = 'pendente'
            """, (st.session_state.usuario,))
            correcoes_pendentes = cursor.fetchone()[0]
            
            # Atestados de horas pendentes
            cursor.execute("""
                SELECT COUNT(*) FROM atestado_horas 
                WHERE usuario = %s AND status = 'pendente'
            """, (st.session_state.usuario,))
            atestados_pendentes = cursor.fetchone()[0]
            
            total_notificacoes = he_pendentes + correcoes_pendentes + atestados_pendentes
            
            if total_notificacoes > 0:
                # ... UI code ...
        
    except Exception as e:
        log_error("Erro ao buscar notificações", e)
```

**Checklist:**
- ✅ Todas as queries preservadas
- ✅ Context manager `with safe_cursor()`
- ✅ Removido `conn.close()` (automático)
- ✅ Error handling simplificado
- ✅ 31 linhas → 26 linhas (mais legível)

---

## 📌 PADRÃO 7: Complex Operation com INSERT + SELECT

### Exemplo #7.1 - Solicitar hora extra (Linhas 805-846, simplificado)

**ANTES**
```python
conn = get_connection()
cursor = conn.cursor()

try:
    agora = get_datetime_br()
    agora_sem_tz = agora.replace(tzinfo=None)
    
    cursor.execute(f"""
        INSERT INTO horas_extras_ativas
        (usuario, aprovador, justificativa, data_inicio, hora_inicio, status)
        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 
                {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aguardando_aprovacao')
    """, (
        st.session_state.usuario,
        aprovador,
        justificativa,
        agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S'),
        agora_sem_tz.strftime('%H:%M')
    ))
    
    # Obter ID da hora extra criada
    cursor.execute("SELECT last_insert_rowid()")
    hora_extra_id = cursor.fetchone()[0]
    
    conn.commit()
    
    # Criar notificação
    try:
        notif_manager.criar_notificacao(...)
    except Exception as e:
        print(f"Erro ao criar notificação: {e}")
    
    st.success("✅ Solicitação de hora extra enviada!")
    
except Exception as e:
    st.error(f"❌ Erro ao registrar hora extra: {e}")
finally:
    conn.close()
```

**DEPOIS**
```python
from connection_manager import safe_cursor
from error_handler import log_error

try:
    with safe_cursor() as cursor:
        agora = get_datetime_br()
        agora_sem_tz = agora.replace(tzinfo=None)
        
        cursor.execute(f"""
            INSERT INTO horas_extras_ativas
            (usuario, aprovador, justificativa, data_inicio, hora_inicio, status)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 
                    {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aguardando_aprovacao')
        """, (
            st.session_state.usuario,
            aprovador,
            justificativa,
            agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S'),
            agora_sem_tz.strftime('%H:%M')
        ))
        
        # Obter ID da hora extra criada
        cursor.execute("SELECT last_insert_rowid()")
        hora_extra_id = cursor.fetchone()[0]
        
        # Criar notificação
        try:
            notif_manager.criar_notificacao(...)
        except Exception as e:
            log_error("Erro ao criar notificação", e)
        
        st.success("✅ Solicitação de hora extra enviada!")
        
except Exception as e:
    log_error("Erro ao registrar hora extra", e)
    st.error(f"❌ Erro ao registrar hora extra: {e}")
```

**Checklist:**
- ✅ SQL preservado
- ✅ Context manager automático
- ✅ Commit/Rollback automático
- ✅ Try/finally removido
- ✅ 34 linhas → 28 linhas
- ✅ Error logging melhorado

---

## 📌 PADRÃO 8: SELECT com BETWEEN e Condições Dinâmicas

### Exemplo #8.1 - Relatório de ponto (Linhas 4652-4681)

**ANTES**
```python
# Buscar registros
conn = get_connection()
cursor = conn.cursor()

query = """
    SELECT r.id, r.usuario, r.data_hora, r.tipo, r.modalidade, 
           r.projeto, r.atividade, r.localizacao, r.latitude, r.longitude,
           u.nome_completo
    FROM registros_ponto r
    LEFT JOIN usuarios u ON r.usuario = u.usuario
    WHERE DATE(r.data_hora) BETWEEN %s AND %s
"""
params = [data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")]

# Aplicar filtro de usuário
if usuario_filter != "Todos":
    usuario_login = usuario_filter.split("(")[1].rstrip(")")
    query += " AND r.usuario = %s"
    params.append(usuario_login)

# Aplicar filtro de tipo
if tipo_registro != "Todos":
    query += " AND r.tipo = %s"
    params.append(tipo_registro)

query += " ORDER BY r.data_hora DESC LIMIT 500"

cursor.execute(query, params)
registros = cursor.fetchall()
conn.close()
```

**DEPOIS**
```python
from connection_manager import execute_query

query = """
    SELECT r.id, r.usuario, r.data_hora, r.tipo, r.modalidade, 
           r.projeto, r.atividade, r.localizacao, r.latitude, r.longitude,
           u.nome_completo
    FROM registros_ponto r
    LEFT JOIN usuarios u ON r.usuario = u.usuario
    WHERE DATE(r.data_hora) BETWEEN %s AND %s
"""
params = [data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")]

# Aplicar filtro de usuário
if usuario_filter != "Todos":
    usuario_login = usuario_filter.split("(")[1].rstrip(")")
    query += " AND r.usuario = %s"
    params.append(usuario_login)

# Aplicar filtro de tipo
if tipo_registro != "Todos":
    query += " AND r.tipo = %s"
    params.append(tipo_registro)

query += " ORDER BY r.data_hora DESC LIMIT 500"

registros = execute_query(query, tuple(params))
```

**Checklist:**
- ✅ Query construction preservada
- ✅ Condicionais preservados
- ✅ Conversão para tuple()
- ✅ 31 linhas → 28 linhas
- ✅ Remove apenas boilerplate

---

## 📌 PADRÃO 9: Lista de usuários com filtros

### Exemplo #9.1 - Gestão de usuários (Linhas 5283-5311)

**ANTES**
```python
# Buscar usuários
conn = get_connection()
cursor = conn.cursor()

query = """
    SELECT id, usuario, nome_completo, tipo, ativo, 
           jornada_inicio_previsto, jornada_fim_previsto
    FROM usuarios WHERE 1=1
"""
params = []

if tipo_filter == "Funcionários":
    query += " AND tipo = 'funcionario'"
elif tipo_filter == "Gestores":
    query += " AND tipo = 'gestor'"

if status_filter == "Ativos":
    query += " AND ativo = 1"
elif status_filter == "Inativos":
    query += " AND ativo = 0"

if busca:
    query += " AND (usuario LIKE %s OR nome_completo LIKE %s)"
    params.extend([f"%{busca}%", f"%{busca}%"])

query += " ORDER BY nome_completo"

cursor.execute(query, params)
usuarios = cursor.fetchall()
conn.close()
```

**DEPOIS**
```python
from connection_manager import execute_query

query = """
    SELECT id, usuario, nome_completo, tipo, ativo, 
           jornada_inicio_previsto, jornada_fim_previsto
    FROM usuarios WHERE 1=1
"""
params = []

if tipo_filter == "Funcionários":
    query += " AND tipo = 'funcionario'"
elif tipo_filter == "Gestores":
    query += " AND tipo = 'gestor'"

if status_filter == "Ativos":
    query += " AND ativo = 1"
elif status_filter == "Inativos":
    query += " AND ativo = 0"

if busca:
    query += " AND (usuario LIKE %s OR nome_completo LIKE %s)"
    params.extend([f"%{busca}%", f"%{busca}%"])

query += " ORDER BY nome_completo"

usuarios = execute_query(query, tuple(params))
```

**Checklist:**
- ✅ Query building preservado
- ✅ Filtros condicionais preservados
- ✅ 28 linhas → 25 linhas
- ✅ Apenas boilerplate removido

---

## 🔧 IMPORTS A ADICIONAR NO TOPO DO ARQUIVO

**Adicionar após os imports existentes (por volta da linha 30):**

```python
# ===== IMPORTAÇÕES DE CONNECTION MANAGEMENT =====
from connection_manager import execute_query, execute_update, safe_cursor
from error_handler import log_error, log_database_operation, get_logger
```

**Exemplo de onde adicionar:**
```python
# Linhas 1-30 (existentes)
from notifications import notification_manager
from calculo_horas_system import CalculoHorasSystem
... (outros imports)

# ADICIONAR AQUI:
from connection_manager import execute_query, execute_update, safe_cursor
from error_handler import log_error, log_database_operation, get_logger

# Configurar logger
logger = logging.getLogger(__name__)
```

---

## ⚠️ GOTCHAS E EDGE CASES

### 1. **last_insert_rowid() em PostgreSQL**
```python
# ❌ NÃO VAI FUNCIONAR em PostgreSQL
cursor.execute("SELECT last_insert_rowid()")
hora_id = cursor.fetchone()[0]

# ✅ USAR RETURNIGN ID (PostgreSQL) ou lastrowid (SQLite)
# Se using connection_manager, já está tratado

# ✅ ALTERNATIVA UNIVERSAL
cursor.execute("""
    INSERT INTO tabela (col1, col2)
    VALUES (%s, %s)
    RETURNING id
""", params)
last_id = cursor.fetchone()[0]
```

### 2. **None handling em fetchall()**
```python
# ❌ VAI QUEBRAR
rows = execute_query("SELECT * FROM users")
for row in rows:  # rows é None se erro!
    print(row)

# ✅ USAR COM FALLBACK
rows = execute_query("SELECT * FROM users")
for row in (rows or []):
    print(row)
```

### 3. **Timeout em operações longas**
```python
# ❌ PODE TIMEOUT
with safe_cursor() as cursor:
    cursor.execute("SELECT * FROM huge_table")  # 1 milhão de registros
    rows = cursor.fetchall()

# ✅ USAR LIMIT ou PAGINATION
with safe_cursor() as cursor:
    cursor.execute("SELECT * FROM huge_table LIMIT 1000")
    rows = cursor.fetchall()
```

---

## ✅ LISTA DE VERIFICAÇÃO POR PADRÃO

### Padrão 1: Simple SELECT fetchone()
- [ ] Usar `execute_query(..., fetch_one=True)`
- [ ] Adicionar import
- [ ] Preservar query exatamente
- [ ] Preservar parâmetros
- [ ] Remover try/finally

### Padrão 2: Simple SELECT fetchall()
- [ ] Usar `execute_query(..., fetch_one=False)` ou simplesmente `execute_query(...)`
- [ ] Adicionar fallback com `(rows or [])`
- [ ] Preservar list comprehension
- [ ] Converter params para tuple

### Padrão 3: INSERT/UPDATE/DELETE
- [ ] Usar `execute_update(...)`
- [ ] Verificar return bool
- [ ] Remover try/except se genérico
- [ ] Manter logging customizado

### Padrão 4: Multiple Queries
- [ ] Usar `safe_cursor()` com `with`
- [ ] Manter queries em sequência
- [ ] Remover conn.close()
- [ ] Manter error handling

### Padrão 5: Complex Operations
- [ ] Usar `safe_cursor()`
- [ ] Manter try/except para lógica customizada
- [ ] Usar `log_error()` para logging
- [ ] Preservar ordem de operações

---

## 📞 TROUBLESHOOTING

**Erro: `NameError: name 'execute_query' is not defined`**
→ Adicione import no topo do arquivo

**Erro: `TypeError: tuple expected, got list`**
→ Converta params list para tuple: `tuple(params)`

**Erro: `AttributeError: 'NoneType' object is not subscriptable`**
→ Adicione fallback: `(rows or [])`

**Query não funciona após refactor**
→ Verifique que SQL_PLACEHOLDER está correto
→ Verifique parâmetros em ordem correta

---

**Pronto para usar! Copie e adapte conforme necessário.**
