# 📋 Plano de Implementação de Logging Completo

**Data Agendada:** 1º de dezembro de 2025  
**Tempo Estimado:** 2-3 horas  
**Status:** ⏳ Agendado

---

## 📊 Escopo Completo

### 1. **Conexão com Banco de Dados** ⚠️ Deprecado em Python 3.12+
- [ ] Log ao abrir conexão (debug level)
- [ ] Log ao fechar conexão (debug level)
- [ ] Capturar e logar falhas de conexão
- [ ] Registrar tempo de conexão
- **Arquivo:** `database.py`, `database_postgresql.py`

### 2. **Validação de Arquivos** ✅ Essencial
- [ ] Log de erros de validação
- [ ] Log de tipos de arquivo recusados
- [ ] Log de tamanhos inválidos
- **Arquivo:** `upload_system.py`

### 3. **Operações de Upload** ✅ Essencial
- [ ] Log de upload bem-sucedido com metadados
- [ ] Log de falhas durante processo
- [ ] Log de exceções com stack trace
- [ ] Log de tempo de upload
- **Arquivo:** `upload_system.py`

### 4. **Consultas ao Banco de Dados** ⚠️ Risco de Segurança
- [ ] Log de queries (com sanitização de dados sensíveis)
- [ ] Log de parâmetros (mascarados)
- [ ] Log de tempo de execução
- [ ] Log de erros SQL
- **Arquivo:** `database.py`, todos os `*_system.py`
- **⚠️ CUIDADO:** Não logar senhas, CPF, dados pessoais

### 5. **Remoção de Arquivos** ✅ Essencial
- [ ] Log ao marcar arquivo como removido
- [ ] Log de exclusão física
- [ ] Log com ID do arquivo e usuário
- [ ] Timestamp da ação
- **Arquivo:** `upload_system.py`

---

## 🏗️ Arquitetura Sugerida

```python
# logging_config.py (NOVO)
import logging
import logging.handlers
import os
from datetime import datetime

class SecureFormatter(logging.Formatter):
    """Formata logs removendo dados sensíveis"""
    SENSITIVE_FIELDS = ['senha', 'password', 'token', 'cpf', 'email']
    
    def format(self, record):
        # Sanitizar registro antes de logar
        return sanitized_message

# Criar handlers:
# 1. File handler - rotativo (diário)
# 2. Console handler - apenas produção (INFO+)
# 3. Error handler - arquivo separado para erros
```

---

## 📁 Estrutura de Logs

```
logs/
├── app.log              # Logs gerais (rotativo)
├── errors.log           # Apenas erros
├── uploads.log          # Operações de upload
├── database.log         # Queries (sem dados sensíveis)
├── 2025-12-01.log      # Arquivo diário
└── archive/             # Logs antigos
    └── 2025-11-*.log
```

---

## 🔐 Pontos de Segurança

### ❌ NUNCA logar:
- Senhas (hash ou plaintext)
- CPF, RG, documentos
- Tokens de autenticação
- Dados bancários
- Emails de usuários

### ✅ SEGURO logar:
- ID de usuário (username, não email)
- Timestamp de ações
- Tipo de operação
- Status (sucesso/falha)
- Arquivo: nome apenas
- Tamanho de arquivo
- Duração de operação

---

## 📍 Pontos de Injeção

### upload_system.py
```python
def save_file(...):
    logger.info(f"Upload iniciado: {original_filename}")
    try:
        # operação
        logger.info(f"Upload bem-sucedido: {filename}")
    except Exception as e:
        logger.error(f"Falha no upload: {e}", exc_info=True)

def remove_file(...):
    logger.info(f"Remoção de arquivo: {file_id}")
    logger.info(f"Exclusão física: {path}")
```

### database.py
```python
def execute(self, sql, params):
    logger.debug(f"Query: {sql}")
    logger.debug(f"Params: {self._sanitize_params(params)}")
    try:
        return self._cursor.execute(sql, params)
    except Exception as e:
        logger.error(f"Erro SQL: {e}", exc_info=True)
```

### *_system.py files
```python
def method(...):
    logger.info(f"Operação iniciada: {operation_name}")
    try:
        # lógica
        logger.info(f"Operação concluída com sucesso")
    except Exception as e:
        logger.error(f"Falha em {operation_name}: {e}")
```

---

## ⚡ Performance Considerations

- **Debug Logs:** Disabled em produção por padrão
- **Query Logs:** Apenas quando `DEBUG=true`
- **Batch Writes:** Logs são buffered (não synchronous)
- **File Rotation:** Diário ou 10MB (menor)
- **Estimado I/O:** < 2% overhead em produção

---

## 🚀 Checklist de Implementação

### Dia 1º de Dezembro:

**Fase 1 (30 min): Setup**
- [ ] Criar `logging_config.py`
- [ ] Configurar handlers e formatters
- [ ] Criar diretório `logs/`
- [ ] Adicionar env var `LOG_LEVEL` (default: INFO)

**Fase 2 (45 min): Upload System**
- [ ] Adicionar logs em `save_file()`
- [ ] Adicionar logs em `remove_file()`
- [ ] Adicionar logs em validações
- [ ] Testar com mock files

**Fase 3 (45 min): Database Layer**
- [ ] Adicionar logs em execute queries (query logging)
- [ ] Implementar sanitização de params
- [ ] Log de erros SQL
- [ ] Log de tempo de execução

**Fase 4 (30 min): Testes & Docs**
- [ ] Rodar suite de testes
- [ ] Verificar overhead de performance
- [ ] Documentar formato de logs
- [ ] Update README com LOG_LEVEL

---

## 📝 Variáveis de Ambiente

```bash
# .env
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_MAX_BYTES=10485760      # 10MB
LOG_BACKUP_COUNT=30         # Manter 30 dias de backup
LOG_SANITIZE=true           # Ativar sanitização de dados sensíveis
DEBUG=false                 # Se true, habilita query logging detalhado
```

---

## ✅ Critério de Sucesso

- [x] 51 testes continuam passando
- [ ] Logs gerados sem erros
- [ ] Performance degradação < 5%
- [ ] Dados sensíveis não aparecem em logs
- [ ] Arquivos rotativos funcionando
- [ ] Documentação atualizada

---

## 📞 Referências

- Python logging: https://docs.python.org/3/library/logging.html
- Best practices: https://docs.python-guide.org/writing/logging/
- Security: https://owasp.org/www-community/attacks/Log_Injection

---

**Próximo passo:** Executar em 1º de dezembro conforme planejado ✅
