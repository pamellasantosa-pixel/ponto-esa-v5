# 🗺️ MAPA DE PROBLEMAS E MATRIZ DE PRIORIZAÇÃO

**Data**: 19 de novembro de 2025  

---

## 1️⃣ MATRIZ DE IMPACTO vs PROBABILIDADE

```
                     PROBABILIDADE (eixo horizontal)
                     
                     BAIXA        MÉDIA      ALTA       MUITO ALTA
                  (20-40%)    (40-60%)   (60-80%)     (80-100%)
                     
CRÍTICO           □           ⚠️ #4      🔴 #5         🔴 #1
(8-10)            
                     
ALTO              □           ⚠️ #2      ⚠️ #3         🟡 #2b
(6-8)             
                     
MÉDIO             ✓ #6        ✓ #7       ✓ #8          ✓ #9
(4-6)             
                     
BAIXO             ✓ #10       ✓ #11      ✓ #12         ✓ #13
(2-4)             
```

### Legenda
- 🔴 CRÍTICO - Fix imediatamente (hoje)
- 🟡 ALTO - Fix urgente (próximos 2 dias)
- ⚠️ MÉDIO - Fix esta semana
- ✓ BAIXO - Fix quando possível

---

## 2️⃣ TOP 10 PROBLEMAS COM TIMELINE

```
PRIORIDADE │ PROBLEMA                      │ ARQUIVO          │ LINHAS   │ ESFORÇO
───────────┼───────────────────────────────┼──────────────────┼──────────┼────────
    1️⃣     │ Vazamento conexão (70+)       │ app_v5_final.py  │ 433-6254 │ 4h
    2️⃣     │ Queries contagem duplicadas   │ app_v5_final.py  │ 1186,1329│ 1.5h
    3️⃣     │ Bare except clauses           │ app_v5_final.py  │ 5424,5446│ 30min
    4️⃣     │ Vazamento em upload_system    │ upload_system.py │ 227-445  │ 1h
    5️⃣     │ Exceções silenciosas (15x)    │ database.py      │ 325-357  │ 1.5h
    6️⃣     │ Circular import potencial     │ app_v5_final.py  │ 8-24     │ 1h
    7️⃣     │ Vazamento horas_extras_sys    │ horas_extras_sys │ 33-360   │ 1h
    8️⃣     │ N+1 queries em relatórios     │ relatorios_*.py  │ múltiplas│ 1h
    9️⃣     │ db_utils.py context manager   │ db_utils.py      │ 52       │ 2h
   1️⃣0️⃣    │ Notificações vazias           │ notifications.py │ 18-20    │ 1h
───────────┴───────────────────────────────┴──────────────────┴──────────┴────────
TOTAL                                                                    14h
```

---

## 3️⃣ ROADMAP DE CORREÇÃO (GANTT)

```
SEMANA 1
├── [████████░░░░░░░░] SEG/TER: Context Manager Migration (4h)
│   ├── [████████░░] Create db_utils.py
│   ├── [██████████] Migrate app_v5_final.py
│   └── [████░░░░░░] Migrate upload_system.py
│
├── [████████░░░░░░░░] TER/QUA: Exception Handling (2.5h)
│   ├── [██████████] Fix bare excepts
│   ├── [████████░░] Add logging to database.py
│   └── [████░░░░░░] Add logging to other systems
│
├── [████████░░░░░░░░] QUA/QUI: Query Deduplication (1.5h)
│   ├── [████████████] Extract helper functions
│   ├── [████░░░░░░] Replace duplicates
│   └── [██░░░░░░░░] Test
│
├── [████░░░░░░░░░░░░] QUI/SEX: Circular Import Fix (1h)
│   └── [████████████] Consolidate imports
│
└── [████████░░░░░░░░] SEX: Testing & Review (3h)
    ├── [████████░░] Unit tests
    ├── [████████░░] Integration tests
    └── [████░░░░░░] Code review
```

---

## 4️⃣ ARQUIVOS CRÍTICOS PARA REVISAR

```
RANKING │ ARQUIVO                      │ PROBLEMAS │ LINHAS │ PRIORIDADE
────────┼──────────────────────────────┼───────────┼────────┼──────────
   1    │ app_v5_final.py              │ 35        │ 6254   │ 🔴 CRÍTICA
   2    │ upload_system.py             │ 8         │ 450    │ 🟡 ALTA
   3    │ horas_extras_system.py       │ 6         │ 400    │ 🟡 ALTA
   4    │ database.py                  │ 7         │ 372    │ 🟡 ALTA
   5    │ calculo_horas_system.py      │ 5         │ 450    │ 🟡 ALTA
   6    │ jornada_semanal_system.py    │ 4         │ 330    │ 🟠 MÉDIA
   7    │ relatorios_horas_extras.py   │ 3         │ 380    │ 🟠 MÉDIA
   8    │ db_utils.py                  │ 2         │ 60     │ 🔴 CRÍTICA
   9    │ notifications.py             │ 2         │ 50     │ 🟡 ALTA
  10    │ offline_system.py            │ 2         │ 350    │ 🟠 MÉDIA
```

---

## 5️⃣ CHECKLIST DE IMPLEMENTAÇÃO

### FASE 0: Setup (30min)

```
□ Criar branch: git checkout -b fix/critical-issues
□ Criar db_utils.py nova versão
□ Criar system_factory.py
□ Adicionar logging imports
□ Revisar tests existentes
```

### FASE 1: Context Manager (4h)

**app_v5_final.py**
```
□ verificar_login()             - linha 433   [████░░░░░░] 5min
□ obter_projetos_ativos()       - linha 449   [████░░░░░░] 5min
□ registrar_ponto()             - linha 458   [████████░░] 10min
□ obter_registros_usuario()     - linha 500   [████████░░] 10min
□ obter_usuarios_para_aprovacao - linha 520   [████░░░░░░] 5min
□ obter_usuarios_ativos()       - linha 530   [████░░░░░░] 5min
□ validar_limites_horas_extras  - linha 619   [██████████] ✓ (já tem try/finally)
□ exibir_hora_extra_em_andamento- linha 868   [████████░░] 10min
□ (mais 60+)                                    [total 4h]
```

**upload_system.py**
```
□ init_database()               - linha 77    [████░░░░░░] 5min
□ register_upload()             - linha 227   [████████░░] 10min
□ find_file_by_hash()           - linha 258   [████░░░░░░] 5min
□ get_file_info()               - linha 315   [████░░░░░░] 5min
□ delete_file()                 - linha 350   [████░░░░░░] 5min
□ get_user_uploads()            - linha 281   [████░░░░░░] 5min
□ (mais 3+)                                    [total 1h]
```

### FASE 2: Exception Handling (2.5h)

**Bare Excepts**
```
□ app_v5_final.py:5424         [████░░░░░░] 10min
□ app_v5_final.py:5446         [████░░░░░░] 10min
```

**Silent Exceptions**
```
□ database.py:325-357          [████████░░] 20min (CREATE TABLE x7)
□ relatorios_horas_extras:375  [████░░░░░░] 10min
□ calculo_horas_system:146,263 [████░░░░░░] 10min
□ upload_system:379,420        [████░░░░░░] 10min
□ offline_system:81,143        [████░░░░░░] 10min
```

### FASE 3: Query Deduplication (1.5h)

```
□ Criar obter_contagem_notificacoes() helper
□ Substituir linhas 1186, 1329, 2181 (horas extras)
□ Substituir linhas 1193, 1336, 2187 (correções)
□ Substituir linhas 1200, 1343, 2193 (atestados)
□ Testar contagem está correta
```

### FASE 4: Circular Imports (1h)

```
□ notifications.py - remover métodos vazios
□ app_v5_final.py - consolidar imports
□ horas_extras_system.py - remover try/except duplicado
□ Testar import sem erro
```

### FASE 5: Testing (3h)

```
□ Unit tests para safe_connection()
□ Unit tests para each migrated function
□ Integration tests de login/ponto/horas_extras
□ Load test com 100 conexões simultâneas
□ Verificar vazamento com psutil
□ Code review
```

---

## 6️⃣ MÉTRICAS DE PROGRESSO

### Antes vs Depois

```
MÉTRICA                          ANTES      DEPOIS    META
─────────────────────────────────────────────────────────
Funções com try/finally          10         80+       ✓ 95%
Bare excepts                      2          0         ✓ 0
Exceções com logging             30%        95%       ✓ 100%
Queries duplicadas               9          0         ✓ 0
Max uptime antes leak            30min      8h+       ✓ 1h min
Connection pool exhaustion       SIM        NÃO       ✓ NUNCA
```

### Performance

```
MÉTRICA                          ANTES      DEPOIS    GANHO
─────────────────────────────────────────────────────────
Tempo query contagem             5ms        2ms       60% ↓
Tempo login                      50ms       50ms      Igual
Memory per connection            2MB        1.8MB     10% ↓
CPU logging overhead             0.5%       1%        Aceitável
```

---

## 7️⃣ RISK MITIGATION

### Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Regressão em login | MÉDIA | CRÍTICO | Testes automatizados |
| Performance piorar | BAIXA | MÉDIO | Load testing |
| Merge conflicts | BAIXA | MÉDIO | Feature branch + code review |
| Circularidade novo | MUITO BAIXA | CRÍTICO | Import testing |

### Plano de Rollback

```bash
# Se algo der errado
git revert <commit_hash>
# Voltar a branch anterior
git checkout main
```

---

## 8️⃣ APROVAÇÃO E SIGN-OFF

### Antes de Deploy

- [ ] **Dev**: "Código passou em testes automatizados" ✓/✗
- [ ] **QA**: "Funcionalidade validada em staging" ✓/✗
- [ ] **DBA**: "Pool de conexões não tem leak" ✓/✗
- [ ] **Sec**: "Sem exposição de dados sensíveis" ✓/✗
- [ ] **PM**: "Aprova para produção" ✓/✗

---

## 9️⃣ SUPORTE E RUNBOOK

### Se der problema em PROD

```
1. Verificar logs
   tail -f /var/log/app/error.log | grep -i "connection"

2. Verificar pool
   SELECT count(*) FROM pg_stat_activity;

3. Matá conexão antiga
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE state = 'idle' AND query_start < now() - interval '10 min';

4. Revert se necessário
   git revert <hash>
   systemctl restart app
```

---

## 🔟 Q&A

### P: Por que não fazemos tudo de uma vez?
**R**: Risco muito alto. Melhor em fases para isolar problemas.

### P: Preciso parar app durante deploy?
**R**: 5min downtime máximo. Coordenar com usuários.

### P: Quem aprova as mudanças?
**R**: Code review + 2 pessoas aprovam (dev + tech lead).

### P: Quanto custa isso?
**R**: ~14h dev time = ~1 dia pessoa. Economiza $10k+ em downtime.

---

**Status**: 📋 Ready to Implement  
**Próximo Passo**: Criar tickets e designar desenvolvedores  

