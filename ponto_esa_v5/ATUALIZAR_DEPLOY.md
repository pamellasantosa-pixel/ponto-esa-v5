# 🚀 Atualização Deploy Render - Ponto ESA v5

**URL Produção:** https://ponto-esa-v5.onrender.com/

## ✅ Checklist de Atualização

### 1. Commit e Push das Alterações

```bash
cd C:\Users\lf\OneDrive\ponto_esa_v5_implemented

# Verificar arquivos modificados
git status

# Adicionar todas as alterações
git add .

# Commit com mensagem descritiva
git commit -m "feat: Sistema de ajuste de registros completo + notificações + validações"

# Push para o repositório
git push origin main
```

**✨ Novo nesta versão:**
- ✅ Sistema completo de ajuste de registros (funcionário solicita → gestor aprova/rejeita)
- ✅ Notificações repetitivas com persistência em banco
- ✅ Funções helper de parsing seguro (safe_datetime_parse, safe_date_parse, safe_time_parse)
- ✅ Compatibilidade PostgreSQL/SQLite
- ✅ Validação e testes automatizados
- ✅ Imports e constantes corrigidos (0 erros Pylance)

---

### 2. Deploy Automático no Render

Após o push, o Render fará deploy automático:

1. Acesse: https://dashboard.render.com
2. Vá para seu serviço: **ponto-esa-v5**
3. Acompanhe o deploy em tempo real na aba **"Events"** ou **"Logs"**
4. Aguarde mensagem: `✅ Deploy live`

⏱️ **Tempo estimado:** 3-5 minutos

---

### 3. Verificar Variáveis de Ambiente

No dashboard do Render, vá para **Environment** e confirme:

| Variável | Valor Esperado | Status |
|----------|----------------|--------|
| `USE_POSTGRESQL` | `true` | ✅ Obrigatório |
| `DATABASE_URL` | `postgresql://...` | ✅ Obrigatório |
| `NOTIFICATION_REMINDER_INTERVAL` | `3600` (ou outro) | ⚙️ Opcional |

**⚠️ Se faltar alguma variável, adicione agora!**

---

### 4. Executar Migração do Banco (Se necessário)

#### 4.1 Via Render Shell

1. No dashboard do serviço, clique em **"Shell"** (canto superior direito)
2. Execute:

```bash
# Navegar para diretório correto
cd ponto_esa_v5

# Verificar estrutura atual
python -c "from database_postgresql import get_connection; c=get_connection(); r=c.cursor(); r.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public'\"); print([t[0] for t in r.fetchall()]); c.close()"

# Criar/Atualizar tabelas (seguro, não apaga dados existentes)
python database_postgresql.py

# Verificar nova tabela de ajustes
python -c "from database_postgresql import get_connection; c=get_connection(); r=c.cursor(); r.execute('SELECT COUNT(*) FROM solicitacoes_ajuste_ponto'); print(f'✅ Tabela ajustes: {r.fetchone()[0]} registros'); c.close()"
```

#### 4.2 Verificar Tabelas Essenciais

Execute este comando para garantir que todas as tabelas foram criadas:

```bash
python -c "
from database_postgresql import get_connection
tables = ['usuarios', 'registros_ponto', 'solicitacoes_ajuste_ponto', 'solicitacoes_horas_extras', 'atestados_horas']
conn = get_connection()
cursor = conn.cursor()
for t in tables:
    cursor.execute(f\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{t}')\")
    exists = cursor.fetchone()[0]
    print(f\"{'✅' if exists else '❌'} {t}\")
conn.close()
"
```

**Resultado esperado:**
```
✅ usuarios
✅ registros_ponto
✅ solicitacoes_ajuste_ponto
✅ solicitacoes_horas_extras
✅ atestados_horas
```

---

### 5. Testar Nova Funcionalidade

#### 5.1 Acesse a Aplicação

🔗 https://ponto-esa-v5.onrender.com/

#### 5.2 Teste como Funcionário

1. **Login** com usuário funcionário existente
2. Vá para aba **"Ajuste de Registros"**
3. Se aparecer a aba → ✅ **Deploy bem-sucedido!**
4. Teste criar uma solicitação:
   - Clique em **"📥 Nova Solicitação"**
   - Escolha "Corrigir registro existente" ou "Adicionar registro ausente"
   - Preencha e envie

#### 5.3 Teste como Gestor

1. **Login** com usuário gestor
2. Vá para aba **"Ajustes Solicitados"**
3. Veja se aparece a solicitação criada
4. Teste aprovar/rejeitar

---

### 6. Solução de Problemas

#### Erro: "Application failed to respond"

**Solução:**
```bash
# No Render Dashboard → seu serviço → Logs
# Procure por erros tipo ImportError ou ModuleNotFoundError
# Se encontrar, force redeploy:
# Manual Deploy → Deploy latest commit
```

#### Erro: "ImportError: cannot import name 'safe_datetime_parse'"

**Causa:** Cache antigo ou imports não atualizados

**Solução:**
```bash
# No Render Shell:
pip install --upgrade --force-reinstall -r requirements-pinned.txt
```

#### Tabela 'solicitacoes_ajuste_ponto' não existe

**Solução:**
```bash
# No Render Shell:
cd ponto_esa_v5
python database_postgresql.py
```

#### App muito lento ou não carrega

**Causa comum:** Plano free "hiberna"

**Solução temporária:**
- Aguarde ~1 minuto no primeiro acesso
- App "acorda" após inatividade

**Solução definitiva:**
- Upgrade para plano Starter ($7/mês) - sempre ativo

---

### 7. Monitoramento Pós-Deploy

#### Verificar Logs

```bash
# No dashboard do Render
# Clique em "Logs" → veja em tempo real
# Procure por:
✅ "You can now view your Streamlit app"
✅ "External URL: https://ponto-esa-v5.onrender.com"
❌ Qualquer linha com "Error" ou "Exception"
```

#### Testar Endpoints

```bash
# Health check
curl https://ponto-esa-v5.onrender.com/_stcore/health

# Deve retornar: {"status": "ok"}
```

---

### 8. Rollback (Se necessário)

Se algo der errado:

1. No Render dashboard → **Events**
2. Encontre o deploy anterior funcionando
3. Clique em **"Rollback"**
4. Confirme

---

## 📊 Validação Completa

Execute esta checklist:

- [ ] Push foi feito com sucesso
- [ ] Deploy no Render completou (veja "Events")
- [ ] Aplicação carrega em https://ponto-esa-v5.onrender.com/
- [ ] Login funciona normalmente
- [ ] Nova aba "Ajuste de Registros" aparece para funcionários
- [ ] Nova aba "Ajustes Solicitados" aparece para gestores
- [ ] Consegue criar uma solicitação de ajuste
- [ ] Gestor consegue aprovar/rejeitar
- [ ] Histórico de ajustes aparece corretamente
- [ ] Logs no Render não mostram erros críticos

---

## 🎯 Comandos Rápidos (Render Shell)

```bash
# Ver versão em produção
python -c "import sys; print(f'Python: {sys.version}')"

# Testar conexão banco
python -c "from database_postgresql import get_connection; conn=get_connection(); print('✅ Conectado'); conn.close()"

# Contar solicitações de ajuste
python -c "from database_postgresql import get_connection; c=get_connection(); r=c.cursor(); r.execute('SELECT COUNT(*) FROM solicitacoes_ajuste_ponto'); print(f'Ajustes: {r.fetchone()[0]}'); c.close()"

# Listar últimas 5 solicitações
python -c "from database_postgresql import get_connection; c=get_connection(); r=c.cursor(); r.execute('SELECT id, usuario, status FROM solicitacoes_ajuste_ponto ORDER BY data_solicitacao DESC LIMIT 5'); print(r.fetchall()); c.close()"

# Reiniciar aplicação (força reload)
# No dashboard → Settings → Delete Service (NÃO FAÇA!)
# Melhor: Manual Deploy → Deploy latest commit
```

---

## 📞 Suporte

- **Dashboard:** https://dashboard.render.com
- **Logs em tempo real:** Dashboard → seu serviço → Logs
- **Banco de dados:** Dashboard → ponto-esa-db → Info
- **Status geral:** https://status.render.com

---

## ✅ Deploy Concluído

Se todos os checks passaram, seu sistema está atualizado com:

✨ **Novas Features:**
- Sistema de ajuste de registros completo
- Notificações persistentes em PostgreSQL
- Validações robustas
- Compatibilidade total SQLite/PostgreSQL

🎉 **Sistema pronto para uso em produção!**

---

**Última atualização:** 03/11/2025
**Versão:** 5.0.0 - Sistema de Ajustes Implementado
