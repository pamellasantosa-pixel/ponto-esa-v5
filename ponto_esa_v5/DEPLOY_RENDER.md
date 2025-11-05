# 🚀 Guia de Deploy - Render.com com PostgreSQL

## 📋 Pré-requisitos

- Conta no [Render.com](https://render.com)
- Repositório Git (GitHub, GitLab ou Bitbucket)
- Código do projeto commitado

---

## 🗄️ PASSO 1: Criar Banco de Dados PostgreSQL

### 1.1 No Dashboard do Render

1. Acesse https://dashboard.render.com
2. Clique em **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name:** `ponto-esa-db` (ou nome de sua escolha)
   - **Database:** `ponto_esa`
   - **User:** `ponto_esa_user` (gerado automaticamente)
   - **Region:** Escolha mais próximo (ex: Ohio, Oregon)
   - **PostgreSQL Version:** 15 ou superior
   - **Plan:** Free (para testes) ou Starter ($7/mês)

4. Clique em **"Create Database"**

### 1.2 Anotar Credenciais

Após criação, na página do banco você verá:

```
Internal Database URL: postgresql://user:senha@host/database
External Database URL: postgresql://user:senha@host:port/database
```

⚠️ **IMPORTANTE:** Copie a **Internal Database URL** - será usada no próximo passo.

---

## 🌐 PASSO 2: Criar Web Service

### 2.1 No Dashboard do Render

1. Clique em **"New +"** → **"Web Service"**
2. Conecte seu repositório Git
3. Configure:
   - **Name:** `ponto-esa-v5`
   - **Region:** Mesma do banco de dados
   - **Branch:** `main` (ou sua branch principal)
   - **Root Directory:** `ponto_esa_v5` (ajuste conforme estrutura)
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install -r requirements-pinned.txt
     ```
   - **Start Command:**
     ```bash
     streamlit run ponto_esa_v5/app_v5_final.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true
     ```

### 2.2 Configurar Variáveis de Ambiente

Na seção **"Environment Variables"**, adicione:

| Key | Value | Descrição |
|-----|-------|-----------|
| `USE_POSTGRESQL` | `true` | Ativa PostgreSQL |
| `DATABASE_URL` | `[URL copiada no passo 1.2]` | Conexão com banco |
| `NOTIFICATION_REMINDER_INTERVAL` | `3600` | Intervalo de notificações (1h) |
| `PYTHON_VERSION` | `3.11.9` | Versão do Python |

⚠️ **Cole a DATABASE_URL completa que você copiou!**

Exemplo:
```
postgresql://ponto_esa_user:abc123xyz@dpg-xxxxx.oregon-postgres.render.com/ponto_esa
```

### 2.3 Configurar Health Check

Em **"Advanced"** → **"Health Check Path"**:
- Deixe em branco ou use: `/_stcore/health`

### 2.4 Deploy

1. Clique em **"Create Web Service"**
2. Aguarde o build (3-5 minutos)
3. Acompanhe os logs em tempo real

---

## 🔧 PASSO 3: Inicializar Banco de Dados

### 3.1 Via Render Shell

1. Na página do seu web service, clique em **"Shell"** (canto superior direito)
2. Execute os comandos:

```bash
# Navegar para o diretório correto
cd ponto_esa_v5

# Inicializar banco
python database_postgresql.py

# Verificar conexão
python -c "from database_postgresql import get_connection; conn = get_connection(); print('✅ Conexão OK'); conn.close()"
```

### 3.2 Via Script de Inicialização (Alternativa)

Adicione ao **Build Command** no Render:

```bash
pip install --upgrade pip && pip install -r requirements-pinned.txt && python ponto_esa_v5/database_postgresql.py
```

---

## 👤 PASSO 4: Criar Primeiro Usuário

### 4.1 Via Render Shell

```bash
python -c "
from database_postgresql import get_connection
import hashlib

conn = get_connection()
cursor = conn.cursor()

# Criar usuário admin
senha_hash = hashlib.sha256('admin123'.encode()).hexdigest()
cursor.execute('''
    INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo)
    VALUES (%s, %s, %s, %s, %s)
''', ('admin', senha_hash, 'gestor', 'Administrador', 1))

conn.commit()
conn.close()
print('✅ Usuário admin criado: admin / admin123')
"
```

### 4.2 Via Psql (Avançado)

Na página do banco PostgreSQL no Render:
1. Clique em **"Connect"** → **"External Connection"**
2. Use o comando PSQL fornecido
3. Execute:

```sql
INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo)
VALUES (
    'admin',
    '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', -- admin123
    'gestor',
    'Administrador',
    1
);
```

---

## ✅ PASSO 5: Verificar Deploy

### 5.1 Acessar Aplicação

1. URL será algo como: `https://ponto-esa-v5.onrender.com`
2. Aguarde carregar (primeira vez pode demorar ~1 min)
3. Faça login com: `admin` / `admin123`

### 5.2 Testes Básicos

- [ ] Login funciona
- [ ] Registrar ponto
- [ ] Criar usuário novo
- [ ] Solicitar ajuste
- [ ] Gestor aprovar ajuste
- [ ] Verificar notificações

---

## 🐛 Troubleshooting

### Erro: "Application failed to respond"

**Causa:** Streamlit não iniciou corretamente

**Solução:**
1. Verifique os logs: `Deploy Logs` → procure por erros
2. Confirme que o Start Command está correto
3. Certifique-se que `$PORT` está sendo usado

### Erro: "Could not connect to database"

**Causa:** DATABASE_URL incorreta ou banco não criado

**Solução:**
1. Copie novamente a **Internal Database URL** do banco
2. Cole exatamente como está em `DATABASE_URL`
3. Verifique se `USE_POSTGRESQL=true`

### Erro: "ModuleNotFoundError"

**Causa:** Dependências não instaladas

**Solução:**
1. Verifique `requirements-pinned.txt` está na raiz correta
2. Confirme Build Command instala dependências
3. Veja logs de build para erros de instalação

### App muito lento

**Causa:** Plano free "hiberna" após inatividade

**Solução:**
- Upgrade para plano Starter ($7/mês)
- Ou use serviço de "ping" para manter ativo

---

## 🔐 Segurança - Pós-Deploy

### Alterar Senha Admin

```python
# Via Render Shell
python -c "
from database_postgresql import get_connection
import hashlib

nova_senha = 'SuaSenhaSegura@2025'
senha_hash = hashlib.sha256(nova_senha.encode()).hexdigest()

conn = get_connection()
cursor = conn.cursor()
cursor.execute('UPDATE usuarios SET senha = %s WHERE usuario = %s', (senha_hash, 'admin'))
conn.commit()
conn.close()
print('✅ Senha alterada!')
"
```

### Configurar Backup Automático

No Render, backups diários são automáticos no plano Starter+.

Para exportar manualmente:
```bash
# Na página do banco PostgreSQL
# Clique em "Backups" → "Create Backup"
```

---

## 📊 Monitoramento

### Logs em Tempo Real

```bash
# Na página do web service
# Clique em "Logs" para ver em tempo real
```

### Métricas

- **CPU/Memory:** Visível no dashboard do serviço
- **Database:** Conexões, tamanho, queries na página do banco

---

## 🔄 Atualizações

### Deploy Automático

Render faz deploy automático quando você faz push no Git:

```bash
git add .
git commit -m "Atualização do sistema"
git push origin main
```

### Deploy Manual

1. Na página do web service
2. Clique em **"Manual Deploy"** → **"Deploy latest commit"**

---

## 💰 Custos Estimados

| Recurso | Plano Free | Plano Starter |
|---------|-----------|---------------|
| Web Service | Hiberna após 15min inativo | Sempre ativo |
| PostgreSQL | 90 dias grátis, depois $7/mês | $7/mês |
| **Total** | $0 (teste) → $7/mês | $14/mês |

---

## 📞 Suporte

- **Documentação Render:** https://render.com/docs
- **Status:** https://status.render.com
- **Comunidade:** https://community.render.com

---

## ✅ Checklist Final

- [ ] Banco PostgreSQL criado no Render
- [ ] DATABASE_URL copiada e configurada
- [ ] Web Service criado e rodando
- [ ] Tabelas inicializadas (database_postgresql.py)
- [ ] Usuário admin criado
- [ ] Login funcionando na aplicação
- [ ] Teste completo do fluxo de ajustes
- [ ] Senha admin alterada para segura
- [ ] Backup configurado

**🎉 Deploy concluído com sucesso!**

---

## 📝 Comandos Úteis

```bash
# Ver versão Python
python --version

# Testar conexão banco
python -c "from database_postgresql import get_connection; get_connection().close(); print('OK')"

# Listar usuários
python -c "from database_postgresql import get_connection; c=get_connection(); r=c.cursor(); r.execute('SELECT usuario, tipo FROM usuarios'); print(r.fetchall()); c.close()"

# Contar registros
python -c "from database_postgresql import get_connection; c=get_connection(); r=c.cursor(); r.execute('SELECT COUNT(*) FROM registros_ponto'); print(f'Registros: {r.fetchone()[0]}'); c.close()"
```
