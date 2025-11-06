# Guia de Migração para PostgreSQL - Ponto ExSA v5.0

## 📋 Pré-requisitos

### 1. Instalar PostgreSQL

**Windows:**
```powershell
# Baixar do site oficial
https://www.postgresql.org/download/windows/

# Ou usar winget (se disponível)
winget install PostgreSQL.PostgreSQL

# Ou usar Chocolatey
choco install postgresql
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

### 2. Instalar dependências Python
```bash
pip install psycopg2-binary python-dotenv
```

## 🔧 Configuração

### 1. Criar o banco de dados PostgreSQL

```bash
# Conectar como usuário postgres
psql -U postgres

# Dentro do psql, executar:
CREATE DATABASE ponto_esa;
CREATE USER ponto_user WITH ENCRYPTED PASSWORD 'sua_senha_aqui';
GRANT ALL PRIVILEGES ON DATABASE ponto_esa TO ponto_user;
\q
```

### 2. Configurar variáveis de ambiente

Criar arquivo `.env` na raiz do projeto:

```bash
USE_POSTGRESQL=true
DB_HOST=localhost
DB_NAME=ponto_esa
DB_USER=ponto_user
DB_PASSWORD=sua_senha_aqui
DB_PORT=5432
```

### 3. Inicializar o banco de dados

```bash
cd ponto_esa_v5
python database_postgresql.py
```

## 🔄 Migrar dados do SQLite para PostgreSQL

### Usar o script de migração:

```bash
python tools/migrate_sqlite_to_postgresql.py
```

Este script irá:
- Ler todos os dados do SQLite
- Criar as tabelas no PostgreSQL
- Inserir os dados
- Validar a migração

## 🚀 Executar a aplicação

```bash
streamlit run app_v5_final.py
```

## 🔍 Verificar conexão

```python
python -c "from database_postgresql import get_connection; conn = get_connection(); print('✅ Conexão OK'); conn.close()"
```

## ⚠️ Troubleshooting

### Erro: "No module named 'psycopg2'"
```bash
pip install psycopg2-binary
```

### Erro: "FATAL: role does not exist"
Certifique-se de criar o usuário no PostgreSQL.

### Erro: "database does not exist"
```bash
psql -U postgres -c "CREATE DATABASE ponto_esa;"
```

### Erro de conexão
Verifique se o PostgreSQL está rodando:
```bash
# Windows
sc query postgresql-x64-15

# Linux
sudo systemctl status postgresql
```

## 📊 Diferenças SQLite vs PostgreSQL

| Recurso | SQLite | PostgreSQL |
|---------|--------|------------|
| Tipo de dados | TEXT | VARCHAR |
| Auto-increment | AUTOINCREMENT | SERIAL |
| Timestamp atual | CURRENT_TIMESTAMP | NOW() |
| Placeholders | ? | %s |
| Concorrência | Limitada | Excelente |
| Performance | Boa para <100GB | Excelente para qualquer tamanho |

## 🔙 Voltar para SQLite

Para voltar a usar SQLite, basta:

1. Remover ou renomear o arquivo `.env`
2. Ou definir `USE_POSTGRESQL=false` no `.env`
3. Reiniciar a aplicação

## 📝 Notas Importantes

1. **Backup**: Sempre faça backup antes de migrar
2. **Teste**: Teste a migração em ambiente de desenvolvimento primeiro
3. **Performance**: PostgreSQL é mais adequado para múltiplos usuários simultâneos
4. **Manutenção**: PostgreSQL requer mais manutenção que SQLite

## 🆘 Suporte

Em caso de problemas, verifique:
- Logs do PostgreSQL
- Variáveis de ambiente
- Permissões do usuário do banco
- Firewall e porta 5432
