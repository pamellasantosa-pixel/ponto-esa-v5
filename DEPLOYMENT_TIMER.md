# 🚀 GUIA DE DEPLOYMENT - TIMER HORA EXTRA

**Versão:** 1.0.0  
**Data:** 2024  
**Status:** ✅ PRONTO PARA DEPLOY  

---

## 📋 PRÉ-REQUISITOS

Antes de fazer deploy, confirme:

### ✅ Ambiente
- [x] Python 3.13+ instalado
- [x] Virtual environment criado (`venv`)
- [x] Dependências instaladas (`requirements.txt`)
- [x] Banco de dados inicializado

### ✅ Código
- [x] Todos os 9 testes passando
- [x] Sem erros de sintaxe
- [x] Documentação atualizada
- [x] Imports corretos

### ✅ Configuração
- [x] `.env` configurado (USE_POSTGRESQL, DB_HOST, etc.)
- [x] Logs configurados
- [x] Backup do banco de dados feito

---

## 📁 ARQUIVOS PARA FAZER DEPLOY

### Arquivo Principal
```
ponto_esa_v5/ponto_esa_v5/app_v5_final.py
```

### Novos Arquivos
```
ponto_esa_v5/ponto_esa_v5/timer_integration_functions.py
ponto_esa_v5/ponto_esa_v5/db_utils.py
ponto_esa_v5/ponto_esa_v5/hora_extra_timer_system.py  (já existe)
```

### Modificados
```
ponto_esa_v5/horas_extras_system.py  (refatorado)
ponto_esa_v5/database.py  (se necessário)
```

---

## 🔧 PASSOS DE DEPLOYMENT

### Passo 1: Backup
```bash
# Fazer backup do banco de dados
cp ponto_esa.db ponto_esa.db.backup.$(date +%Y%m%d_%H%M%S)

# Fazer backup dos arquivos Python
cp -r ponto_esa_v5/ ponto_esa_v5.backup/
```

### Passo 2: Validar Código
```bash
# Verificar sintaxe
python -m py_compile ponto_esa_v5/ponto_esa_v5/app_v5_final.py
python -m py_compile ponto_esa_v5/ponto_esa_v5/timer_integration_functions.py

# Rodar testes
pytest ponto_esa_v5/tests -v

# Deve ver: 9 passed ✅
```

### Passo 3: Deploy no Local
```bash
# Se desenvolvendo localmente
cd ponto_esa_v5
streamlit run ponto_esa_v5/app_v5_final.py

# Deve rodar sem erros
```

### Passo 4: Deploy em Produção
```bash
# Se deployando em servidor (ex: Render, Heroku)

# 1. Push code para GitHub
git add -A
git commit -m "feat: integrate timer hora extra system"
git push origin main

# 2. Trigger deployment
# (automático ou manual conforme seu pipeline)

# 3. Validar
# - Acessar URL da aplicação
# - Fazer login
# - Testar fluxo de timer
```

### Passo 5: Verificar Deployment
```bash
# Após deploy, verificar logs
tail -f ponto_esa_v5/logs/app.log

# Deve ver:
# - Conexão com banco bem-sucedida
# - Sem erros no startup
# - Timer system inicializado
```

---

## 🧪 TESTES PÓS-DEPLOYMENT

### Teste Manual 1: Fluxo Funcionário
```
1. Login como funcionário
2. Registrar ponto "Fim" após 17:00
3. Deve ver botão "🕐 Solicitar Horas Extras"
4. Clicar no botão
5. Deve ver timer começar a contar
6. Esperar 1 minuto (ou forçar em 1 hora para teste)
7. Deve aparecer popup "Continuar?"
8. Clicar "Não"
9. Deve aparecer diálogo de justificativa
10. Preencher e enviar
✅ SUCESSO: Solicitação criada
```

### Teste Manual 2: Fluxo Gestor
```
1. Login como gestor
2. Ir para "🔔 Notificações"
3. Deve ver solicitação de hora extra pendente
4. Clicar em "✅ Aceitar"
5. Deve confirmar aprovação
✅ SUCESSO: Solicitação aprovada
```

### Teste Manual 3: Fluxo Completo
```
1. Funcionário: Registra ponto Fim
2. Funcionário: Inicia hora extra
3. Funcionário: Timer conta até 1h
4. Funcionário: Popup pergunta "Continuar?"
5. Funcionário: Clica "Não"
6. Funcionário: Preenche justificativa
7. Funcionário: Seleciona aprovador
8. Funcionário: Envia solicitação
9. Gestor: Recebe notificação
10. Gestor: Aprova solicitação
11. Funcionário: Vê resposta
✅ SUCESSO: Fluxo completo funcionando
```

---

## 🔍 VERIFICAÇÕES PÓS-DEPLOYMENT

### ✅ Frontend
- [ ] Button "Solicitar Horas Extras" aparece após 17:00
- [ ] Timer atualiza a cada 1 segundo
- [ ] Popup aparece a cada 1 hora
- [ ] Diálogo de justificativa abre corretamente
- [ ] Notificações aparecem para aprovador

### ✅ Backend
- [ ] Dados salvos no banco corretamente
- [ ] Notificações persistem
- [ ] Session state funciona
- [ ] Autorefresh não causa overhead

### ✅ Database
- [ ] Tabelas existem
- [ ] Dados inserindo normalmente
- [ ] Sem SQL errors nos logs
- [ ] Backup automático rodando

### ✅ Segurança
- [ ] Apenas funcionários podem solicitar
- [ ] Apenas gestores podem aprovar
- [ ] Dados de outros usuários não aparecem
- [ ] Logs de auditoria funcionando

### ✅ Performance
- [ ] App carrega em < 2s
- [ ] Timer não fica travado
- [ ] Múltiplos usuários sem problema
- [ ] Sem memory leaks

---

## 🚨 TROUBLESHOOTING

### Problema: "ModuleNotFoundError: No module named 'hora_extra_timer_system'"

**Solução:**
```bash
# Verificar se arquivo existe
ls -la ponto_esa_v5/ponto_esa_v5/hora_extra_timer_system.py

# Verificar PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/ponto_esa_v5"

# Reinstalar dependências
pip install -r requirements.txt
```

### Problema: "Timer não atualiza"

**Solução:**
```python
# Verificar se streamlit_autorefresh está instalado
pip install streamlit-autorefresh

# Verificar em app_v5_final.py:
# if st.session_state.hora_extra_ativa:
#     st_autorefresh(interval=1000)
```

### Problema: "Popup não aparece após 1 hora"

**Solução:**
```python
# Verificar se hora_extra_timeout está sendo setado
# Verificar se verificar_timeout_expirado() retorna True
# Verificar logs: tail -f ponto_esa_v5/logs/app.log
```

### Problema: "Session state perdido ao fazer refresh"

**Solução:**
```python
# Streamlit mantém session state entre refreshes
# Se tiver perdendo dados:
# 1. Verificar se hora_extra_ativa está sendo inicializado
# 2. Verificar se st.rerun() está no lugar certo
# 3. Limpar .streamlit/ e tentar novamente
rm -rf .streamlit/
streamlit run app_v5_final.py
```

### Problema: "Database locked" ou connection errors

**Solução:**
```bash
# Se usar SQLite
# 1. Fechar todas as conexões abertas
# 2. Remover .db-journal se existir
rm -f ponto_esa.db-journal

# 3. Rodar vacuum
sqlite3 ponto_esa.db "VACUUM;"

# Se usar PostgreSQL
# 1. Verificar conexão
psql -h localhost -U postgres -d ponto_esa -c "SELECT 1"

# 2. Verificar logs do server
tail -f /var/log/postgresql/postgresql.log
```

---

## 📊 MONITORAMENTO PÓS-DEPLOY

### Logs para Monitorar
```bash
# Ver logs em tempo real
tail -f ponto_esa_v5/logs/app.log

# Procurar por erros
grep ERROR ponto_esa_v5/logs/app.log

# Procurar por warnings
grep WARNING ponto_esa_v5/logs/app.log

# Contar eventos por tipo
grep INFO ponto_esa_v5/logs/app.log | wc -l
```

### Métricas para Acompanhar
```
1. Número de solicitações de hora extra criadas
2. Taxa de aprovação vs rejeição
3. Tempo médio de aprovação
4. Erros na criação de solicitações
5. Performance do timer (latência de update)
```

### Alertas a Configurar
```
- ⚠️ Se 5+ erros em 1 hora
- ⚠️ Se timer fica sem atualizar por 5+ segundos
- ⚠️ Se taxa de erro > 5%
- ⚠️ Se banco de dados lento (query > 1s)
```

---

## 🔄 ROLLBACK (Se Necessário)

Se algo der errado, fazer rollback é simples:

### Rollback Código
```bash
# Restaurar backup dos arquivos
rm -rf ponto_esa_v5/
cp -r ponto_esa_v5.backup/ ponto_esa_v5/

# Ou via Git
git revert HEAD~1
git push origin main
```

### Rollback Database
```bash
# Restaurar backup do banco
cp ponto_esa.db.backup.20240101_120000 ponto_esa.db

# Verificar integridade
sqlite3 ponto_esa.db "PRAGMA integrity_check;"
```

### Rollback Servidor
```bash
# Parar aplicação
kill $(lsof -t -i :8501)  # Streamlit usa porta 8501

# Restaurar
cp -r ponto_esa_v5.backup/ ponto_esa_v5/
streamlit run ponto_esa_v5/ponto_esa_v5/app_v5_final.py
```

---

## ✅ CHECKLIST PRÉ-DEPLOY

- [ ] Testes passando (9/9)
- [ ] Código sem erros de sintaxe
- [ ] Imports corretos
- [ ] Session state definido
- [ ] Autorefresh configurado
- [ ] Logs configurados
- [ ] Backup do banco feito
- [ ] Backup do código feito
- [ ] .env configurado
- [ ] Docs atualizadas
- [ ] Changelog atualizado
- [ ] Time notificado

---

## 📞 CONTATO PÓS-DEPLOY

Se houver problema pós-deploy:

1. **Checar logs:**
   ```bash
   tail -f ponto_esa_v5/logs/app.log
   ```

2. **Rodar testes:**
   ```bash
   pytest ponto_esa_v5/tests -v
   ```

3. **Fazer rollback se necessário:**
   ```bash
   # Ver seção "Rollback" acima
   ```

4. **Reportar issue:**
   - Descrever o problema
   - Incluir logs
   - Incluir steps para reproduzir
   - Enviar para time

---

## 🎉 CONCLUSÃO

Parabéns! Você está pronto para fazer deploy do Timer de Hora Extra!

**Próximos Passos:**
1. ✅ Executar os passos de deployment
2. ✅ Rodar testes pós-deployment
3. ✅ Comunicar ao time
4. ✅ Monitorar logs
5. ✅ Coletar feedback de usuários

**Se tiver dúvidas:**
- Veja `INTEGRACAO_TIMER_COMPLETA.md`
- Veja `IMPLEMENTACAO_TIMER_HORA_EXTRA.md`
- Veja `QUICK_REFERENCE.md`

**Boa sorte! 🚀**

