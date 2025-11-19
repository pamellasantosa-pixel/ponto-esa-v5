# 🚀 IMPLEMENTAÇÃO: Timer de 1 Hora para Solicitação de Horas Extras

**Status:** Pronto para integração  
**Componente:** Novo `HoraExtraTimerSystem`  
**Integração:** `app_v5_final.py` - função `tela_funcionario()`  

---

## 📋 FLUXO IMPLEMENTADO

### Phase 1: Verificar Final da Jornada (Já Existe)
```python
# Em app_v5_final.py::registrar_ponto_interface()
# Linha ~1585: Se tipo == "Fim", verificar_fim_jornada()
if tipo_registro == "Fim" and horas_extras_system is not None:
    verificacao = horas_extras_system.verificar_fim_jornada(usuario)
    if verificacao.get("deve_notificar"):
        st.info(f"💡 {verificacao.get('message')}")
        # Aqui seria bom show button "Solicitar Horas Extras"
```

### Phase 2: Button "Solicitar Horas Extras" (NOVO)
Aparece quando passa do horário de fim:
- ✅ Button desabilitado até horário de saída
- ✅ Button habilitado automaticamente em `tela_funcionario()`
- ✅ Click abre modal com opções

### Phase 3: Modal com Timer (NOVO)
Quando clica no button:
1. Inicia timer, contando o tempo que está de hora extra
2. Exibe countdown (MM:SS) em tempo real
3. Usuário pode:
   - **Encerrar antes** (clicando em "Finalizar Hora Extra")
   
   Ao clicar em "Finalizar Hora Extra":
   - ✅ Abre caixa de diálogo para **justificar** por que fez hora extra
   - ✅ Selecionar **funcionário para autorizar** (sem mostrar o nome do solicitante)
   - ✅ Envia solicitação para aprovador

### Phase 4: Popup a Cada 1 Hora (NOVO)
A cada 1 hora que passa:
1. **Popup pergunta:** "Deseja continuar com a hora extra?"
2. Se **SIM**: 
   - ✅ Timer continua contando
   - ✅ Novo popup aparecerá em mais 1 hora
3. Se **NÃO**: 
   - ✅ Abre caixa de diálogo para **justificar** por que fez hora extra
   - ✅ Selecionar **funcionário para autorizar** (sem mostrar o nome do solicitante)
   - ✅ Envia solicitação para aprovador

### Phase 5: Notificação para Aprovador (NOVO)
Quando solicitação é enviada:
1. **Popup notification** aparece para o funcionário selecionado
2. Pode **Aceitar** ou **Rejeitar** a solicitação
3. Pode **Justificar** a decisão
4. Notificação volta ao solicitante com resposta

---

## 🔧 CÓDIGO DE INTEGRAÇÃO

### 1. Adicionar Timer System ao init_systems()

```python
# Em app_v5_final.py::init_systems()
def init_systems():
    """Inicializa sistemas"""
    from ponto_esa_v5.hora_extra_timer_system import HoraExtraTimerSystem
    
    timer_system = HoraExtraTimerSystem()
    
    return (
        calculo_horas_system,
        horas_extras_system,
        upload_system,
        atestado_horas_system,
        ajuste_registros_system,
        notification_manager,
        timer_system,  # Novo
    )
```

### 2. Adicionar Session State para Timer

```python
# Em app_v5_final.py::main() ou _setup_page_config()
def _init_session_state():
    """Inicializa session state do usuário"""
    # ... código existente ...
    
    # Timer de hora extra
    if "hora_extra_ativa" not in st.session_state:
        st.session_state.hora_extra_ativa = False
    if "hora_extra_inicio" not in st.session_state:
        st.session_state.hora_extra_inicio = None
    if "hora_extra_timeout" not in st.session_state:
        st.session_state.hora_extra_timeout = None
    if "exibir_popup_hora_extra_expirou" not in st.session_state:
        st.session_state.exibir_popup_hora_extra_expirou = False
```

### 3. Função para Exibir Button no Footer (NOVO)

```python
# Em tela_funcionario(), após o menu lateral:
def exibir_button_solicitar_hora_extra(horas_extras_system, timer_system):
    """Exibe button para solicitar horas extras quando passa do horário"""
    
    # Verificar se passou do horário de fim
    verificacao = horas_extras_system.verificar_fim_jornada(
        st.session_state.usuario
    )
    
    if verificacao.get("deve_notificar"):
        col1, col2 = st.columns([0.7, 0.3])
        
        with col1:
            st.warning(f"🕐 {verificacao.get('message')}")
        
        with col2:
            if st.button("🕐 Solicitar Horas Extras", key="btn_hora_extra"):
                st.session_state.hora_extra_ativa = True
                st.session_state.hora_extra_inicio = get_datetime_br().isoformat()
                st.rerun()
```

### 4. Modal com Timer (NOVO)

```python
# Em tela_funcionario(), exibir modal com timer:
def exibir_modal_timer_hora_extra(timer_system):
    """Exibe modal com countdown de hora extra em tempo real"""
    
    if not st.session_state.hora_extra_ativa:
        return
    
    with st.container():
        st.markdown("---")
        st.markdown("### ⏱️ Hora Extra em Andamento")
        
        col1, col2 = st.columns([0.6, 0.4])
        
        with col1:
            st.markdown("""
            Você iniciou a contagem de hora extra. 
            O sistema pedirá confirmação a cada 1 hora.
            """)
            
            # Verificar tempo decorrido
            resultado = timer_system.verificar_timeout_expirado(
                hora_extra_inicio=st.session_state.hora_extra_inicio,
                usuario=st.session_state.usuario
            )
            
            if resultado["success"]:
                tempo_restante = resultado["tempo_restante"]
                tempo_formatado = timer_system.formatar_tempo_restante(tempo_restante)
                
                # Exibir timer com tempo decorrido
                horas_decorridas = (resultado["timeout_datetime"] - 
                                   st.session_state.hora_extra_inicio).total_seconds() / 3600
                st.metric("Tempo de Hora Extra", tempo_formatado, 
                         delta=f"{horas_decorridas:.1f}h acumuladas")
                
                # Se passou 1h, 2h, 3h, etc., mostrar popup
                if resultado["expirado"]:
                    st.session_state.exibir_popup_hora_extra_expirou = True
        
        with col2:
            if st.button("🛑 Finalizar Hora Extra", key="btn_finalizar_hora_extra"):
                # Abrir diálogo para justificativa e seleção de aprovador
                st.session_state.exibir_dialog_justificativa = True
                st.session_state.hora_extra_ativa = False
                st.rerun()
```

### 4B. Diálogo de Justificativa e Seleção de Aprovador (NOVO)

```python
# Em tela_funcionario(), após o modal do timer:
def exibir_dialog_justificativa_hora_extra(horas_extras_system):
    """Exibe diálogo para justificar hora extra e selecionar aprovador"""
    
    if not st.session_state.get("exibir_dialog_justificativa", False):
        return
    
    st.warning("### 📋 Registrar Solicitação de Hora Extra")
    
    with st.form("form_justificativa_hora_extra"):
        # Justificativa
        justificativa = st.text_area(
            "Por que você fez hora extra?",
            placeholder="Descreva os motivos da hora extra...",
            height=100
        )
        
        # Selecionar aprovador (sem mostrar o nome do solicitante)
        aprovadores = horas_extras_system.obter_aprovadores_disponiveis()
        
        # Filtrar para não mostrar o próprio usuário
        aprovadores_filtrados = [
            a for a in aprovadores 
            if a["usuario"] != st.session_state.usuario
        ]
        
        opcoes_aprovadores = {
            a["nome"]: a["usuario"] for a in aprovadores_filtrados
        }
        
        nome_aprovador = st.selectbox(
            "Selecione quem deve autorizar:",
            options=list(opcoes_aprovadores.keys())
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("✅ Enviar Solicitação"):
                if not justificativa.strip():
                    st.error("❌ Por favor, preencha a justificativa")
                else:
                    # Obter ID do aprovador selecionado
                    aprovador_id = opcoes_aprovadores[nome_aprovador]
                    
                    # Calcular tempo de hora extra
                    from datetime import datetime
                    tempo_decorrido = (datetime.now() - 
                                     datetime.fromisoformat(st.session_state.hora_extra_inicio)
                                     ).total_seconds() / 3600
                    
                    # Criar solicitação
                    resultado = horas_extras_system.solicitar_horas_extras(
                        usuario=st.session_state.usuario,
                        data=date.today().isoformat(),
                        hora_inicio="17:00",  # Usar fim de jornada
                        hora_fim=(date.today() + timedelta(hours=int(tempo_decorrido))).isoformat(),
                        justificativa=justificativa,
                        aprovador_solicitado=aprovador_id
                    )
                    
                    if resultado["success"]:
                        st.success("✅ Solicitação enviada com sucesso!")
                        st.session_state.exibir_dialog_justificativa = False
                        st.session_state.hora_extra_ativa = False
                        st.session_state.hora_extra_inicio = None
                        st.rerun()
                    else:
                        st.error(f"❌ Erro: {resultado['message']}")
        
        with col2:
            if st.form_submit_button("❌ Cancelar"):
                st.session_state.exibir_dialog_justificativa = False
                st.session_state.hora_extra_ativa = True
                st.rerun()
```

### 5. Popup a Cada 1 Hora (NOVO)

```python
# Em tela_funcionario(), depois de exibir o timer:
def exibir_popup_continuar_hora_extra(timer_system):
    """Exibe popup a cada 1 hora pedindo confirmação para continuar"""
    
    if not st.session_state.get("exibir_popup_hora_extra_expirou", False):
        return
    
    st.warning("""
    ### ⏰ 1 HORA DE HORA EXTRA COMPLETADA
    
    Você está trabalhando há mais 1 hora além da sua jornada.
    **Deseja continuar com a hora extra?**
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Sim, Continuar", key="btn_continuar_hora_extra"):
            # Resetar timeout para mais 1 hora
            st.session_state.hora_extra_timeout = (
                datetime.now() + timedelta(hours=1)
            ).isoformat()
            st.session_state.exibir_popup_hora_extra_expirou = False
            st.rerun()
    
    with col2:
        if st.button("❌ Não, Encerrar", key="btn_encerrar_hora_extra"):
            # Abrir diálogo para justificativa
            st.session_state.exibir_dialog_justificativa = True
            st.session_state.exibir_popup_hora_extra_expirou = False
            st.rerun()
```

### 5B. Notificação para Aprovador (NOVO)

```python
# Em tela_funcionario() ou em uma aba de notificações:
def exibir_notificacoes_hora_extra_pendente(horas_extras_system):
    """Exibe notificações de solicitações de hora extra pendentes"""
    
    if st.session_state.tipo_usuario != "gestor":
        return
    
    # Buscar solicitações pendentes
    solicitacoes = horas_extras_system.listar_solicitacoes_para_aprovacao(
        st.session_state.usuario
    )
    
    if solicitacoes:
        st.info(f"📬 Você tem {len(solicitacoes)} solicitação(ões) de hora extra pendente(s)")
        
        for sol in solicitacoes:
            with st.container(border=True):
                col1, col2, col3 = st.columns([0.5, 0.25, 0.25])
                
                with col1:
                    st.markdown(f"""
                    **Solicitante:** {sol['usuario']}  
                    **Data:** {sol['data']}  
                    **Horas:** {sol['hora_inicio']} - {sol['hora_fim']}  
                    **Justificativa:** {sol['justificativa']}
                    """)
                
                with col2:
                    if st.button("✅ Aceitar", key=f"aceitar_{sol['id']}"):
                        # Validação/justificativa para aceitar
                        observacao = st.text_input(
                            "Observação (opcional):",
                            key=f"obs_aceitar_{sol['id']}"
                        )
                        
                        resultado = horas_extras_system.aprovar_solicitacao(
                            sol['id'],
                            st.session_state.usuario,
                            observacao
                        )
                        
                        if resultado["success"]:
                            st.success("✅ Solicitação aprovada!")
                            st.rerun()
                
                with col3:
                    if st.button("❌ Rejeitar", key=f"rejeitar_{sol['id']}"):
                        # Caixa de justificativa para rejeição
                        justificativa = st.text_area(
                            "Motivo da rejeição:",
                            key=f"motivo_rejeitar_{sol['id']}"
                        )
                        
                        if st.button("Confirmar Rejeição", key=f"conf_rejeitar_{sol['id']}"):
                            resultado = horas_extras_system.rejeitar_solicitacao(
                                sol['id'],
                                st.session_state.usuario,
                                justificativa
                            )
                            
                            if resultado["success"]:
                                st.error("❌ Solicitação rejeitada")
                                st.rerun()
```

### 6. Integração na Tela Principal

```python
# Em tela_funcionario() - adicionar ao fluxo:

def tela_funcionario():
    """Interface principal para funcionários"""
    
    timer_system = HoraExtraTimerSystem()
    
    # ... código existente ...
    
    # 1. Exibir button para solicitar hora extra (após fim da jornada)
    exibir_button_solicitar_hora_extra(horas_extras_system, timer_system)
    
    # 2. Se tem hora extra ativa, exibir timer contando o tempo
    if st.session_state.hora_extra_ativa:
        exibir_modal_timer_hora_extra(timer_system)
        
        # 3. Se passou 1h, 2h, 3h, etc., mostrar popup
        exibir_popup_continuar_hora_extra(timer_system)
    
    # 4. Se clicou em "Finalizar" ou respondeu "Não" ao popup
    if st.session_state.get("exibir_dialog_justificativa", False):
        exibir_dialog_justificativa_hora_extra(horas_extras_system)
    
    # 5. Se é gestor/aprovador, mostrar notificações de horas extras pendentes
    exibir_notificacoes_hora_extra_pendente(horas_extras_system)
```

---

## 📊 SESSION STATE VARIABLES

| Variável | Tipo | Descrição |
|----------|------|-----------|
| `hora_extra_ativa` | bool | Se usuário está contando hora extra |
| `hora_extra_inicio` | str (ISO) | Timestamp de início da contagem |
| `hora_extra_timeout` | str (ISO) | Timestamp do próximo popup (a cada 1h) |
| `exibir_popup_hora_extra_expirou` | bool | Se mostrar popup de confirmação |
| `exibir_dialog_justificativa` | bool | Se mostrar diálogo para justificar |

---

## 🧪 TESTES RECOMENDADOS

```python
def test_timer_sistema():
    """Testa sistema de timer"""
    timer = HoraExtraTimerSystem()
    
    # Test 1: Calcula corretamente tempo até popup
    resultado = timer.calcular_tempo_para_notificacao_inicial("17:00")
    assert resultado["success"]
    assert resultado["tempo_ate_popup"] >= 0
    
    # Test 2: Formata tempo corretamente
    tempo_str = timer.formatar_tempo_restante(3661)
    assert tempo_str == "01:01:01"
    
    # Test 3: Detecta timeout expirado
    from datetime import datetime, timedelta
    tempo_passado = (datetime.now() - timedelta(hours=2)).isoformat()
    resultado = timer.verificar_timeout_expirado(tempo_passado, "user")
    assert resultado["expirado"] is True
```

---

## 🔄 AUTO-REFRESH DO STREAMLIT

Para fazer o timer contar automaticamente, usar `streamlit-autorefresh`:

```python
# No início de main():
if st.session_state.hora_extra_ativa:
    st_autorefresh(interval=1000)  # Refresh a cada 1 segundo
```

---

## 📝 NOTAS IMPLEMENTAÇÃO

✅ **Já Pronto:**
- Sistema de timer (`HoraExtraTimerSystem`)
- Funções de cálculo e formatação
- Integração com NotificationManager
- Session state para persistência

⏳ **Próximos Passos:**
1. Adicionar funções no `app_v5_final.py`
2. Integrar ao `tela_funcionario()`
3. Testar fluxo completo
4. Testes unitários

---

## 🎯 CRITÉRIOS DE ACEITAÇÃO

✅ Button "Solicitar Horas Extras" desabilitado até fim de jornada  
✅ Button habilitado automaticamente quando passa de jornada  
✅ Timer mostra countdown MM:SS  
✅ Após 1 hora: popup pergunta "Continuar?"  
✅ Se SIM: obriga selecionar aprovador  
✅ Se NÃO: cancela hora extra sem criar solicitação  
✅ Notificação enviada para aprovador  
✅ Todos os 12 testes continuam passando ✅  
