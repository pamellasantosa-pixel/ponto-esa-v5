# 📋 PLANO DE INTEGRAÇÃO - JORNADA SEMANAL COM HORA EXTRA

**Data:** 18/11/2025  
**Status:** Planejamento  

---

## 🔍 DESCOBERTA DO SISTEMA EXISTENTE

### ✅ O QUE JÁ EXISTE

**Arquivo:** `ponto_esa_v5/jornada_semanal_system.py` (373 linhas)

Já tem:
- ✅ Tabela: colunas adicionadas à `usuarios` 
  - `trabalha_seg, jornada_seg_inicio, jornada_seg_fim` (e para todos os dias)
  - `trabalha_ter, jornada_ter_inicio, jornada_ter_fim`
  - ... (seg, ter, qua, qui, sex, sab, dom)

- ✅ Funções principais:
  - `obter_jornada_usuario(usuario)` → Dict com config de cada dia
  - `obter_jornada_do_dia(usuario, data)` → Config de um dia específico
  - `usuario_trabalha_hoje(usuario, data)` → Bool se trabalha
  - `salvar_jornada_semanal(usuario_id, jornada_config)` → Salva config

- ✅ Dados por dia:
  ```python
  {
    'seg': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00'},
    'ter': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00'},
    ...
  }
  ```

---

## 🎯 ESTRATÉGIA: "CONVERSAR COM O EXISTENTE"

### **PASSO 1: ESTENDER A TABELA USUARIOS** ✨

**Adicionar 2 colunas por dia:**

```sql
-- Adicionar intervalo (almoço em minutos) por dia
ALTER TABLE usuarios ADD COLUMN intervalo_seg INTEGER DEFAULT 60;
ALTER TABLE usuarios ADD COLUMN intervalo_ter INTEGER DEFAULT 60;
ALTER TABLE usuarios ADD COLUMN intervalo_qua INTEGER DEFAULT 60;
-- ... para todos os dias

-- EXEMPLO:
-- intervalo_seg = 60  (1h de almoço)
-- intervalo_ter = 0   (sem almoço, trabalha corrido)
```

**Estrutura final para cada dia:**
```
trabalha_seg: 1 (bool)
jornada_seg_inicio: "08:00"
jornada_seg_fim: "18:00"
intervalo_seg: 60 (minutos de intervalo/almoço)

Cálculo:
- Tempo bruto: 18:00 - 08:00 = 10h
- Tempo efetivo: 10h - (60/60)h = 9h efetivas
```

---

## 🔧 ESTRATÉGIA: "ESTENDER, NÃO REESCREVER"

### **PASSO 2: CRIAR NOVO ARQUIVO - `jornada_semanal_calculo_system.py`**

Vou criar um arquivo NOVO que:
- ✅ NÃO modifica o existente
- ✅ Importa e usa `jornada_semanal_system.py`
- ✅ Adiciona funcionalidades de CÁLCULO
- ✅ Não quebra nada que já existe

**Funções novas a implementar:**

```python
class JornadaSemanalCalculoSystem:
    
    def calcular_horas_esperadas_dia(usuario, data):
        """Retorna quantas horas o funcionário DEVERIA trabalhar"""
        # 1. Busca jornada do dia (usa jornada_semanal_system.obter_jornada_do_dia)
        # 2. Se não trabalha → return 0
        # 3. Se trabalha → calcula (fim - inicio - intervalo)
        # 4. Return: 9 (exemplo: 10h - 1h intervalo)
    
    def calcular_horas_registradas_dia(usuario, data):
        """Retorna quantas horas o funcionário REGISTROU"""
        # 1. Busca pontos do dia (Início + Fim)
        # 2. Calcula diferença (fim - inicio)
        # 3. Desconta intervalo da jornada
        # 4. Return: 11 (exemplo: registrou 8-20h = 12h - 1h intervalo = 11h)
    
    def detectar_hora_extra_dia(usuario, data):
        """Detecta se há hora extra"""
        # 1. horas_esperadas = calcular_horas_esperadas_dia(usuario, data)
        # 2. horas_registradas = calcular_horas_registradas_dia(usuario, data)
        # 3. diferenca = horas_registradas - horas_esperadas
        # 4. If diferenca > 5 minutos → return {'hora_extra': True, 'horas': 2.5}
        # 5. Else → return {'hora_extra': False, 'horas': 0}
    
    def validar_ponto_contra_jornada(usuario, data, tipo_ponto, hora):
        """Valida se ponto pode ser registrado"""
        # 1. Busca jornada_do_dia
        # 2. If não trabalha neste dia → aviso "Você não trabalha hoje"
        # 3. If tipo = "Início" e está fora de jornada → aviso "Fora do horário"
        # 4. Return: {'valido': True/False, 'mensagem': '...'}
```

---

## 🎨 PASSO 3: INTERFACE DO GESTOR - TABELA EDITÁVEL

### **Localização:** Nova aba em `tela_gestor()` ou em "Configurações"

```
MENU → Configuração → Jornada Semanal

[Buscar Funcionário: _______________]

┌──────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ Funcionário      │ SEG      │ TER      │ QUA      │ QUI      │ SEX      │ SAB      │ DOM      │
├──────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤
│ João Silva       │ 8-18*    │ 8-18*    │ 8-18*    │ 8-18*    │ 8-17*    │ -        │ -        │
│ Maria López      │ 8-17*    │ 8-17*    │ 8-17*    │ 8-17*    │ 8-17*    │ 9-13*    │ -        │
│ Pedro (Campo)    │ 6-14*    │ 6-14*    │ 6-14*    │ 6-14*    │ 6-14*    │ -        │ -        │
└──────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘

* = com intervalo, "-" = não trabalha

[Click na célula] → Modal para editar:

┌───────────────────────────────────────┐
│ Editar Jornada: João Silva - SEGUNDA │
├───────────────────────────────────────┤
│ Trabalha: [✓]                         │
│ Hora Início: [08:00]                  │
│ Hora Fim: [18:00]                     │
│ Intervalo (almoço): [60] minutos      │
│ Observação: [Escritório]              │
│                                       │
│ [Salvar] [Cancelar]                   │
└───────────────────────────────────────┘
```

**Código Streamlit:**
```python
def configurar_jornada_semanal_interface():
    """Interface para gestor configurar jornada dos funcionários"""
    
    # Buscar funcionários
    usuarios = obter_usuarios_ativos()
    usuario_selecionado = st.selectbox("Funcionário", usuarios)
    
    # Obter jornada atual (usa jornada_semanal_system!)
    jornada_atual = obter_jornada_usuario(usuario_selecionado['usuario'])
    
    # Criar tabela com colunas para cada dia
    cols = st.columns(7)
    dias_semana = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
    
    for idx, dia in enumerate(dias_semana):
        with cols[idx]:
            if st.button(f"{dia.upper()}\n{jornada_atual[dia]['inicio']}-{jornada_atual[dia]['fim']}"):
                # Abre modal para editar este dia
                st.session_state.dia_editando = dia
    
    # Se tem dia selecionado, mostrar modal
    if st.session_state.get('dia_editando'):
        dia = st.session_state.dia_editando
        with st.form(f"editar_jornada_{dia}"):
            trabalha = st.checkbox("Trabalha", 
                                  value=jornada_atual[dia]['trabalha'])
            
            if trabalha:
                inicio = st.time_input("Hora Início", 
                                      value=datetime.strptime(jornada_atual[dia]['inicio'], "%H:%M").time())
                fim = st.time_input("Hora Fim", 
                                   value=datetime.strptime(jornada_atual[dia]['fim'], "%H:%M").time())
                intervalo = st.number_input("Intervalo (min)", 
                                           value=jornada_atual[dia].get('intervalo', 60))
            
            if st.form_submit_button("Salvar"):
                # Atualizar jornada
                jornada_atual[dia] = {
                    'trabalha': trabalha,
                    'inicio': inicio.strftime("%H:%M"),
                    'fim': fim.strftime("%H:%M"),
                    'intervalo': int(intervalo)
                }
                salvar_jornada_semanal(usuario_id, jornada_atual)
                st.success("✅ Jornada atualizada!")
```

---

## ⏰ PASSO 4: DETECTAR HORA EXTRA NO REGISTRO

### **Integrar com `registrar_ponto_interface()`**

**Fluxo:**
```
1. Funcionário registra ponto
   ↓
2. Sistema calcula:
   - Horas esperadas (via jornada_semanal)
   - Horas registradas (via pontos)
   ↓
3. Se diferença > 5 min:
   - 5 MIN ANTES do fim de jornada:
     Popup: "Fazer horas extras?"
   - AO FINALIZAR:
     Mensagem: "✅ Você fez 2h de horas extras!"
```

**Mudança mínima no código:**

```python
def registrar_ponto_interface(...):
    # ... código existente ...
    
    if submitted:
        # Registrar ponto normalmente
        data_hora_registro = registrar_ponto(...)
        
        # NOVO: Verificar hora extra
        if tipo_registro == "Fim":
            resultado = JornadaSemanalCalculoSystem.detectar_hora_extra_dia(
                usuario=st.session_state.usuario,
                data=data_registro
            )
            
            if resultado['hora_extra']:
                horas = resultado['horas']
                st.success(f"✅ Você fez {horas:.1f}h de horas extras!")
                
                # Sugerir solicitar aprovação
                if st.button("📝 Solicitar Aprovação"):
                    # Abre modal de hora extra (já existe!)
                    st.session_state.exibir_dialog_justificativa = True
```

---

## 📊 PASSO 5: POPUP 5 MIN ANTES

**Integrar com `tela_funcionario()` ou usar timer existente:**

```python
def exibir_alerta_fim_jornada():
    """Mostra popup 5 min antes do fim da jornada"""
    
    jornada_hoje = obter_jornada_do_dia(st.session_state.usuario, date.today())
    
    if not jornada_hoje or not jornada_hoje['trabalha']:
        return  # Não trabalha hoje
    
    # Hora de fim - 5 min
    hora_alerta = (datetime.strptime(jornada_hoje['fim'], "%H:%M") - timedelta(minutes=5)).time()
    
    agora = datetime.now().time()
    
    if agora >= hora_alerta and agora < jornada_hoje['fim']:
        st.warning("""
        ⏰ FALTA 5 MINUTOS PARA O FIM DA JORNADA
        
        Você vai fazer horas extras hoje?
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sim, vou continuar"):
                st.session_state.vai_fazer_hora_extra = True
        with col2:
            if st.button("Não, vou finalizar"):
                st.session_state.vai_fazer_hora_extra = False
```

---

## 🔄 RESUMO DA INTEGRAÇÃO

| Componente | Já Existe? | Precisa Fazer |
|-----------|-----------|---------------|
| **Tabela usuarios** | ✅ Colunas de jornada | ✅ Adicionar colunas de intervalo |
| **jornada_semanal_system.py** | ✅ Sim (373 linhas) | ✅ Estender com histórico (data_inicio/fim) |
| **Cálculos de hora** | ❌ Não | ✅ Criar `jornada_semanal_calculo_system.py` |
| **Interface Gestor** | ❌ Não | ✅ Criar tabela editável em Streamlit |
| **Registrar ponto** | ✅ Existe | ✅ Adicionar detecção de hora extra |
| **Alerta 5 min** | ❌ Não | ✅ Integrar com tela_funcionario |
| **Popup hora extra** | ✅ Timer já existe | ✅ Reutilizar |
| **Mensagem final** | ❌ Não | ✅ Adicionar ao registrar ponto |

---

## ✨ ABORDAGEM "SEM QUEBRAR NADA"

```python
# ✅ NÃO VAI MODIFICAR
jornada_semanal_system.py  # Deixo como está
app_v5_final.py            # Só adiciono, não removo
registrar_ponto()          # Só adiciono verificação, não mudo lógica

# ✅ VAI CRIAR NOVO
jornada_semanal_calculo_system.py  # Novo arquivo com cálculos
configurar_jornada_interface()      # Nova função no app

# ✅ VAI ESTENDER (sem quebrar)
Tabela usuarios: adicionar colunas intervalo_seg, etc
```

---

## 🚀 PLANO FINAL

### Fase 1: Preparar Banco (15 min)
- [ ] Adicionar colunas `intervalo_XXX` à tabela usuarios
- [ ] Adicionar função para migração automática
- [ ] Testar

### Fase 2: Criar Sistema de Cálculo (45 min)
- [ ] Criar `jornada_semanal_calculo_system.py`
- [ ] 5 funções principais
- [ ] Testes unitários
- [ ] Integrar com jornada_semanal_system.py existente

### Fase 3: Interface do Gestor (60 min)
- [ ] Criar `configurar_jornada_interface()` em Streamlit
- [ ] Tabela dinâmica (Seg-Dom)
- [ ] Modal para editar
- [ ] Validações

### Fase 4: Detecção de Hora Extra (45 min)
- [ ] Integrar cálculos em `registrar_ponto_interface()`
- [ ] Popup 5 min antes
- [ ] Mensagem ao finalizar
- [ ] Sugerir solicitar aprovação

### Fase 5: Testes (30 min)
- [ ] Testes unitários
- [ ] Teste manual completo
- [ ] Validar que sistema existente não quebrou

---

## ✅ PRONTO PARA COMEÇAR?

Todos os pontos acima estão **100% integrados com o sistema existente** e **não quebram nada que já funciona**.

**Próximo passo:** Você quer que eu comece pela Fase 1 ou quer que mude algo no plano?

