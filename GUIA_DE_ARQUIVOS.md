# 📁 GUIA DE ARQUIVOS - JORNADA SEMANAL COM HORA EXTRA

**Mapeamento completo de todos os arquivos criados e modificados**

---

## 📝 ARQUIVOS CRIADOS (4 arquivos)

### 1. `ponto_esa_v5/jornada_semanal_calculo_system.py` ⭐
**Tipo:** Sistema Principal  
**Linhas:** 650  
**Prioridade:** CRÍTICA  

**Conteúdo:**
- Classe `JornadaSemanalCalculoSystem`
- 6 métodos públicos
- 1 função helper
- Documentação completa

**Métodos:**
```python
# Cálculos
- calcular_horas_esperadas_dia()
- calcular_horas_registradas_dia()
- detectar_hora_extra_dia()
- validar_ponto_contra_jornada()
- obter_tempo_ate_fim_jornada()
- obter_pontos_dia() [helper]
```

**Dependências:**
- database.py (ou database_postgresql.py)
- jornada_semanal_system.py
- datetime, logging

**Como usar:**
```python
from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem

resultado = JornadaSemanalCalculoSystem.detectar_hora_extra_dia(
    usuario='joao',
    data=date(2024, 11, 18)
)
if resultado['tem_hora_extra']:
    print(f"Hora extra: {resultado['horas_extra']}h")
```

---

### 2. `tests/test_jornada_semanal_calculo.py` ⭐
**Tipo:** Testes Unitários  
**Linhas:** 300+  
**Prioridade:** ALTA  

**Conteúdo:**
- Fixture `temp_db()` para banco temporário
- Helpers para setup de dados
- Classe `TestJornadaSemanalCalculoSystem`
- 6 casos de teste

**Testes:**
```
✓ test_calcular_horas_esperadas_dia_normal
✓ test_calcular_horas_registradas_dia_com_pontos
✓ test_detectar_hora_extra_positiva
✓ test_detectar_hora_extra_nenhuma
✓ test_validar_ponto_dia_nao_trabalha
✓ test_obter_tempo_ate_fim_jornada
```

**Como rodar:**
```bash
cd ponto_esa_v5
python -m pytest tests/test_jornada_semanal_calculo.py -v
```

---

### 3. `PLANO_JORNADA_HORA_EXTRA.md` 📋
**Tipo:** Documentação (Planejamento)  
**Linhas:** 400+  
**Prioridade:** MÉDIA  

**Seções:**
- 🔍 Descoberta do sistema existente
- 🎯 Estratégia de integração
- 📊 Diagrama de fluxos
- 🔧 Detalhes de implementação
- 🔄 Resumo da integração
- ✨ Abordagem "sem quebrar nada"
- 🚀 Plano em 5 fases

**Público:** Técnico + Gestão  
**Uso:** Referência durante desenvolvimento

---

### 4. `CONCLUSAO_JORNADA_HORA_EXTRA.md` 📋
**Tipo:** Documentação (Técnica)  
**Linhas:** 600+  
**Prioridade:** ALTA  

**Seções:**
- 📊 Resumo de mudanças por fase
- 🔗 Integração com sistema existente
- 📈 Arquitetura final
- 🚀 Como usar
- 📝 Arquivos modificados/criados
- ✨ Próximas melhorias
- ✅ Validações finais

**Público:** Técnico + RH  
**Uso:** Referência pós-implementação

---

## 🔄 ARQUIVOS MODIFICADOS (3 arquivos)

### 1. `ponto_esa_v5/apply_jornada_semanal_migration.py` 🔧
**Tipo:** Banco de Dados  
**Mudanças:** +20 linhas  
**Prioridade:** CRÍTICA  

**Modificações:**
```python
# ANTES: 21 colunas (3 por dia)
colunas_a_adicionar = [
    ("trabalha_seg", "INTEGER DEFAULT 1"),
    ("jornada_seg_inicio", "TIME"),
    ("jornada_seg_fim", "TIME"),
    # ... para todos os 7 dias
]

# DEPOIS: 28 colunas (4 por dia)
colunas_a_adicionar = [
    ("trabalha_seg", "INTEGER DEFAULT 1"),
    ("jornada_seg_inicio", "TIME"),
    ("jornada_seg_fim", "TIME"),
    ("intervalo_seg", "INTEGER DEFAULT 60"),  # ← NOVO
    # ... para todos os 7 dias
]
```

**Colunas Adicionadas:**
- intervalo_seg, intervalo_ter, intervalo_qua, intervalo_qui, intervalo_sex, intervalo_sab, intervalo_dom

**Type:** INTEGER DEFAULT 60 (em minutos)

**Como executar:**
```bash
cd ponto_esa_v5
python apply_jornada_semanal_migration.py
```

---

### 2. `ponto_esa_v5/jornada_semanal_system.py` 🔧
**Tipo:** Sistema Existente (Estendido)  
**Mudanças:** ~50 linhas  
**Prioridade:** ALTA  

**Modificações:**

1. **JORNADA_COLUMNS** (linhas 22-60)
   ```python
   # Adicionadas 7 colunas de intervalo
   ("intervalo_seg", "INTEGER DEFAULT 60"),
   ("intervalo_ter", "INTEGER DEFAULT 60"),
   # ... etc
   ```

2. **obter_jornada_usuario()** (linhas ~110-155)
   ```python
   # ANTES:
   jornada[dia] = {
       'trabalha': trabalha,
       'inicio': str(inicio),
       'fim': str(fim)
   }
   
   # DEPOIS:
   jornada[dia] = {
       'trabalha': trabalha,
       'inicio': str(inicio),
       'fim': str(fim),
       'intervalo': int(intervalo)  # ← NOVO
   }
   ```

3. **salvar_jornada_semanal()** (linhas ~190-230)
   ```python
   # Agora salva também o intervalo
   intervalo_novo = int(config.get('intervalo', 60))
   updates.append(f"intervalo_{dia} = {SQL_PLACEHOLDER}")
   params.append(intervalo_novo)
   ```

**Compatibilidade:** 100% backward compatible  
**Teste:** Funções antigas continuam funcionando

---

### 3. `ponto_esa_v5/app_v5_final.py` 🔧
**Tipo:** Interface Principal  
**Mudanças:** ~400 linhas  
**Prioridade:** CRÍTICA  

**Modificações:**

1. **Função configurar_jornada_interface()** (+200 linhas)
   - Local: linha ~5900 (antes de buscar_registros_dia)
   - Interface visual com 7 dias
   - Modal para editar
   - Atalhos para copiar/resetar

2. **Função exibir_alerta_fim_jornada_avancado()** (+80 linhas)
   - Local: linha ~5840 (após configurar_jornada_interface)
   - Alerta quando ≤ 5 min para fim
   - Integra com novo sistema de cálculo
   - Fallback para sistema antigo

3. **tela_funcionario()** (modificações ~20 linhas)
   - Chama `exibir_alerta_fim_jornada_avancado()` logo no início
   - Substitui código anterior de alerta

4. **registrar_ponto_interface()** (modificações ~80 linhas)
   - Adicionado bloco após sucesso do registro (tipo "Fim")
   - Tenta novo sistema primeiro
   - Detecta hora extra
   - Mostra resultado ao usuário
   - Fallback para sistema antigo

5. **Menu tela_gestor()** (modificações ~5 linhas)
   - Adicionada opção: "📅 Configurar Jornada"
   - Adicionado elif correspondente

**Seções Modificadas:**
- Linha ~3335: opcoes_menu += "📅 Configurar Jornada"
- Linha ~3360: elif opcao.startswith("📅 Configurar Jornada"):
- Linha ~1289: tela_funcionario() - adiciona chamada a exibir_alerta
- Linha ~1550: registrar_ponto_interface() - adiciona detecção HE

**Compatibilidade:** 100% backward compatible  
**Fallback:** Usa sistema antigo se novo falhar

---

## 📊 RESUMO DE MUDANÇAS

| Aspecto | Criados | Modificados | Total |
|---------|---------|-------------|-------|
| **Arquivos Python** | 2 | 3 | 5 |
| **Documentação** | 2 | 0 | 2 |
| **Linhas de Código** | ~950 | ~470 | ~1420 |
| **Funções Novas** | 7 | 0 | 7 |
| **Funcionalidades** | 6 | 0 | 6 |

---

## 🔍 GUIA DE NAVEGAÇÃO

### Se preciso editar a interface de gestor:
→ `app_v5_final.py` → função `configurar_jornada_interface()`

### Se preciso ajustar a lógica de cálculo:
→ `jornada_semanal_calculo_system.py` → classe `JornadaSemanalCalculoSystem`

### Se preciso adicionar coluna ao banco:
→ `apply_jornada_semanal_migration.py` → lista `colunas_a_adicionar`

### Se preciso entender o fluxo:
→ `PLANO_JORNADA_HORA_EXTRA.md` → seção "Fluxo"

### Se preciso testar:
→ `tests/test_jornada_semanal_calculo.py` → classe `TestJornadaSemanalCalculoSystem`

---

## ⚙️ DEPENDÊNCIAS E IMPORTS

### jornada_semanal_calculo_system.py precisa de:
```python
✓ database.py (SQL_PLACEHOLDER, get_connection)
✓ jornada_semanal_system.py (obter_jornada_do_dia, obter_jornada_usuario)
✓ datetime, time, logging
✓ os (para detectar PostgreSQL)
```

### app_v5_final.py novo precisa de:
```python
✓ jornada_semanal_calculo_system.py (JornadaSemanalCalculoSystem)
✓ jornada_semanal_system.py (verificar_horario_saida_proximo)
✓ streamlit (st)
✓ datetime, logging
```

### test_jornada_semanal_calculo.py precisa de:
```python
✓ pytest
✓ sqlite3, tempfile, os
✓ unittest.mock (patch)
✓ datetime
```

---

## 📦 ESTRUTURA FINAL

```
ponto_esa_v5_implemented/
├── ponto_esa_v5/
│   ├── jornada_semanal_system.py (modificado ✏️)
│   ├── jornada_semanal_calculo_system.py (NOVO ✨)
│   ├── apply_jornada_semanal_migration.py (modificado ✏️)
│   ├── app_v5_final.py (modificado ✏️)
│   ├── database.py (não modificado)
│   └── ...
├── tests/
│   ├── test_jornada_semanal_calculo.py (NOVO ✨)
│   └── ...
├── PLANO_JORNADA_HORA_EXTRA.md (NOVO ✨)
├── CONCLUSAO_JORNADA_HORA_EXTRA.md (NOVO ✨)
├── RESUMO_JORNADA_HORA_EXTRA.md (NOVO ✨)
├── CHECKLIST_VERIFICACAO.md (NOVO ✨)
└── GUIA_DE_ARQUIVOS.md (este arquivo ✨)
```

---

## ✅ CHECKLIST DE VERIFICAÇÃO

- [ ] `jornada_semanal_calculo_system.py` existe e importa sem erro
- [ ] Todos os 6 métodos existem
- [ ] `test_jornada_semanal_calculo.py` existe
- [ ] Tests passam (6/6)
- [ ] `configurar_jornada_interface()` acessível do menu gestor
- [ ] `exibir_alerta_fim_jornada_avancado()` aparece na tela funcionário
- [ ] Detecção de hora extra funciona ao registrar ponto
- [ ] Sistema antigo ainda funciona (fallback)
- [ ] Colunas de intervalo existem no banco
- [ ] Todos os 4 arquivos de documentação criados

---

**Criado:** 18/11/2024  
**Versão:** 1.0  
**Status:** ✅ Completo

