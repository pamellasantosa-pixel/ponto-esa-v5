# 🎯 IMPLEMENTAÇÃO DE JORNADA SEMANAL E HORAS EXTRAS EM TEMPO REAL

## ✅ O QUE JÁ FOI IMPLEMENTADO

### 1. Estrutura do Banco de Dados

#### Migration Aplicada com Sucesso
- ✅ Adicionadas colunas para configurar horários por dia da semana:
  - `jornada_seg_inicio`, `jornada_seg_fim`, `trabalha_seg`
  - `jornada_ter_inicio`, `jornada_ter_fim`, `trabalha_ter`
  - `jornada_qua_inicio`, `jornada_qua_fim`, `trabalha_qua`
  - `jornada_qui_inicio`, `jornada_qui_fim`, `trabalha_qui`
  - `jornada_sex_inicio`, `jornada_sex_fim`, `trabalha_sex`
  - `jornada_sab_inicio`, `jornada_sab_fim`, `trabalha_sab`
  - `jornada_dom_inicio`, `jornada_dom_fim`, `trabalha_dom`

#### Nova Tabela: `horas_extras_ativas`
```sql
CREATE TABLE horas_extras_ativas (
    id INTEGER PRIMARY KEY,
    usuario TEXT NOT NULL,
    aprovador TEXT NOT NULL,
    justificativa TEXT NOT NULL,
    data_inicio TIMESTAMP NOT NULL,
    hora_inicio TIME NOT NULL,
    status TEXT DEFAULT 'em_execucao',
    data_fim TIMESTAMP,
    hora_fim TIME,
    tempo_decorrido_minutos INTEGER,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. Módulo de Sistema de Jornada Semanal

Arquivo: `ponto_esa_v5/jornada_semanal_system.py`

#### Funções Principais:

**`obter_jornada_usuario(usuario)`**
- Retorna configuração completa de jornada semanal
- Formato: `{'seg': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00'}, ...}`

**`obter_jornada_do_dia(usuario, data=None)`**
- Retorna horários de trabalho para um dia específico
- Útil para validação de registros de ponto

**`usuario_trabalha_hoje(usuario, data=None)`**
- Verifica se usuário trabalha em determinada data
- Considera configuração do dia da semana

**`salvar_jornada_semanal(usuario_id, jornada_config)`**
- Salva configuração completa de jornada semanal
- Aceita dicionário com config de cada dia

**`verificar_horario_saida_proximo(usuario, margem_minutos=30)`**
- Verifica se está próximo do horário de saída (padrão: 30 min antes)
- Retorna: `{'proximo': bool, 'horario_saida': str, 'minutos_restantes': int}`
- **USE ESTA FUNÇÃO para exibir botão de solicitar hora extra!**

### 3. Scripts de Migration

#### `apply_jornada_semanal_migration.py`
- ✅ Executado com sucesso
- Adicionou todas as colunas necessárias
- Copiou jornada padrão existente para seg-sex

#### Arquivos SQL de Referência:
- `tools/migrations/add_jornada_semanal.sql`
- `tools/migrations/create_horas_extras_ativas.sql`

---

## 📋 O QUE FALTA IMPLEMENTAR

### PARTE 1: Interface de Jornada Semanal no Cadastro de Usuários

#### Onde modificar:
`ponto_esa_v5/app_v5_final.py` → Função `gerenciar_usuarios_interface()`

#### O que adicionar na ABA DE EDIÇÃO:

Depois da seção de "Jornada de Trabalho" atual (linhas ~3300), adicionar:

```python
# Jornada Semanal Variável
st.markdown("---")
st.markdown("**📅 Jornada Semanal Detalhada:**")
st.info("💡 Configure horários diferentes para cada dia da semana")

# Buscar jornada semanal atual
from jornada_semanal_system import obter_jornada_usuario, salvar_jornada_semanal

jornada_atual = obter_jornada_usuario(usuario) or {}

dias = {
    'seg': '🔵 Segunda', 'ter': '🔵 Terça', 'qua': '🔵 Quarta',
    'qui': '🔵 Quinta', 'sex': '🔵 Sexta', 'sab': '🟡 Sábado', 'dom': '🔴 Domingo'
}

jornada_config = {}

for dia_key, dia_nome in dias.items():
    config_dia = jornada_atual.get(dia_key, {'trabalha': dia_key in ['seg', 'ter', 'qua', 'qui', 'sex'], 
                                              'inicio': '08:00', 'fim': '17:00'})
    
    col_check, col_inicio, col_fim = st.columns([1, 2, 2])
    
    with col_check:
        trabalha = st.checkbox(
            dia_nome,
            value=config_dia['trabalha'],
            key=f"trabalha_{dia_key}_{usuario_id}"
        )
    
    with col_inicio:
        if trabalha:
            hora_inicio = st.time_input(
                "Entrada",
                value=time(*map(int, config_dia['inicio'].split(':'))),
                key=f"inicio_{dia_key}_{usuario_id}",
                label_visibility="collapsed"
            )
        else:
            hora_inicio = None
            st.markdown("<small style='color: gray;'>Não trabalha</small>", unsafe_allow_html=True)
    
    with col_fim:
        if trabalha:
            hora_fim = st.time_input(
                "Saída",
                value=time(*map(int, config_dia['fim'].split(':'))),
                key=f"fim_{dia_key}_{usuario_id}",
                label_visibility="collapsed"
            )
        else:
            hora_fim = None
            st.markdown("<small style='color: gray;'>-</small>", unsafe_allow_html=True)
    
    jornada_config[dia_key] = {
        'trabalha': trabalha,
        'inicio': hora_inicio.strftime('%H:%M') if hora_inicio else None,
        'fim': hora_fim.strftime('%H:%M') if hora_fim else None
    }

# Salvar jornada semanal ao clicar em "Salvar"
# Modificar o botão "💾 Salvar" para incluir:
if st.button("💾 Salvar", key=f"save_{usuario_id}", use_container_width=True):
    # ... código existente ...
    
    # ADICIONAR: Salvar jornada semanal
    salvar_jornada_semanal(usuario_id, jornada_config)
    
    # ... resto do código ...
```

#### O que adicionar na ABA DE CRIAÇÃO:

Depois dos campos de "Jornada de Trabalho" (linhas ~3450), adicionar:

```python
st.markdown("---")
st.markdown("**📅 Jornada Semanal Detalhada (Opcional):**")
st.info("💡 Deixe em branco para usar o padrão acima para todos os dias úteis")

with st.expander("⚙️ Configurar horários diferentes por dia"):
    # Mesmo código do exemplo acima para configurar cada dia
    # ...
    
# Ao salvar o novo usuário, após o INSERT:
if submitted:
    # ... código existente de INSERT ...
    
    # Obter ID do usuário recém-criado
    cursor.execute("SELECT last_insert_rowid()")
    novo_usuario_id = cursor.fetchone()[0]
    
    # Salvar jornada semanal se configurada
    from jornada_semanal_system import copiar_jornada_padrao_para_dias
    copiar_jornada_padrao_para_dias(novo_usuario_id, ['seg', 'ter', 'qua', 'qui', 'sex'])
```

---

### PARTE 2: Botão de Solicitar Hora Extra no Horário de Saída

#### Onde modificar:
`ponto_esa_v5/app_v5_final.py` → Função `tela_funcionario()`

#### Código a modificar (linhas ~605-616):

```python
# SUBSTITUIR O CÓDIGO EXISTENTE:
# Verificar notificação de fim de jornada
verificacao_jornada = horas_extras_system.verificar_fim_jornada(
    st.session_state.usuario)
if verificacao_jornada["deve_notificar"]:
    st.warning(f"⏰ {verificacao_jornada['message']}")
    if st.button("🕐 Solicitar Horas Extras"):
        st.session_state.solicitar_horas_extras = True

# PELO NOVO CÓDIGO:
from jornada_semanal_system import verificar_horario_saida_proximo

# Verificar se está próximo do horário de saída
verificacao_saida = verificar_horario_saida_proximo(
    st.session_state.usuario, 
    margem_minutos=30
)

if verificacao_saida['proximo']:
    minutos = verificacao_saida['minutos_restantes']
    st.warning(f"⏰ Seu horário de saída é às {verificacao_saida['horario_saida']} (faltam {minutos} minutos)")
    
    if st.button("🕐 Solicitar Hora Extra", type="primary", use_container_width=True):
        st.session_state.solicitar_horas_extras = True
        st.session_state.horario_saida_previsto = verificacao_saida['horario_saida']
```

---

### PARTE 3: Sistema de Hora Extra em Tempo Real

#### Criar nova interface: `iniciar_hora_extra_interface()`

Adicionar no arquivo `ponto_esa_v5/app_v5_final.py`:

```python
def iniciar_hora_extra_interface():
    """Interface para iniciar hora extra com contador em tempo real"""
    from datetime import datetime
    from jornada_semanal_system import obter_jornada_do_dia
    
    st.markdown("""
    <div class="feature-card">
        <h3>🕐 Iniciar Hora Extra</h3>
        <p>Solicite autorização e inicie o contador de hora extra</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Buscar gestores disponíveis
    gestores = obter_usuarios_para_aprovacao()
    
    if not gestores:
        st.error("❌ Nenhum gestor disponível para aprovar")
        return
    
    with st.form("form_iniciar_hora_extra"):
        st.markdown("### 👤 Selecione o Gestor para Aprovação")
        
        aprovador = st.selectbox(
            "Gestor Responsável:",
            options=[g['usuario'] for g in gestores],
            format_func=lambda x: next(g['nome_completo'] for g in gestores if g['usuario'] == x)
        )
        
        st.markdown("### 📝 Justificativa")
        justificativa = st.text_area(
            "Por que você precisa fazer hora extra?",
            placeholder="Ex: Finalizar relatório urgente solicitado pela diretoria...",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("✅ Iniciar Hora Extra", use_container_width=True, type="primary")
        with col2:
            cancelar = st.form_submit_button("❌ Cancelar", use_container_width=True)
        
        if cancelar:
            st.session_state.solicitar_horas_extras = False
            st.rerun()
        
        if submitted:
            if not justificativa.strip():
                st.error("❌ Justificativa é obrigatória!")
            else:
                # Registrar hora extra ativa
                conn = get_connection()
                cursor = conn.cursor()
                
                agora = datetime.now()
                
                cursor.execute(f"""
                    INSERT INTO horas_extras_ativas
                    (usuario, aprovador, justificativa, data_inicio, hora_inicio, status)
                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aguardando_aprovacao')
                """, (
                    st.session_state.usuario,
                    aprovador,
                    justificativa,
                    agora.strftime('%Y-%m-%d %H:%M:%S'),
                    agora.strftime('%H:%M')
                ))
                
                hora_extra_id = cursor.lastrowid
                
                conn.commit()
                conn.close()
                
                # Criar notificação para o gestor
                from notifications import NotificationManager
                notif_manager = NotificationManager()
                notif_manager.criar_notificacao(
                    usuario_destino=aprovador,
                    tipo='aprovacao_hora_extra',
                    titulo=f"🕐 Solicitação de Hora Extra - {st.session_state.nome_completo}",
                    mensagem=f"Justificativa: {justificativa}",
                    dados_extras={'hora_extra_id': hora_extra_id}
                )
                
                st.session_state.hora_extra_ativa_id = hora_extra_id
                st.session_state.solicitar_horas_extras = False
                st.success("✅ Solicitação enviada! Aguardando aprovação do gestor...")
                st.rerun()

def exibir_hora_extra_em_andamento():
    """Exibe contador de hora extra em andamento"""
    from datetime import datetime
    
    # Verificar se tem hora extra ativa
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT id, aprovador, justificativa, data_inicio, status
        FROM horas_extras_ativas
        WHERE usuario = {SQL_PLACEHOLDER} AND status IN ('aguardando_aprovacao', 'em_execucao')
        ORDER BY data_inicio DESC
        LIMIT 1
    """, (st.session_state.usuario,))
    
    hora_extra = cursor.fetchone()
    conn.close()
    
    if not hora_extra:
        return
    
    he_id, aprovador, justificativa, data_inicio, status = hora_extra
    
    # Calcular tempo decorrido
    inicio = datetime.strptime(data_inicio, '%Y-%m-%d %H:%M:%S')
    agora = datetime.now()
    tempo_decorrido = agora - inicio
    
    horas = int(tempo_decorrido.total_seconds() // 3600)
    minutos = int((tempo_decorrido.total_seconds() % 3600) // 60)
    
    if status == 'aguardando_aprovacao':
        st.warning(f"""
        ⏳ **AGUARDANDO APROVAÇÃO DE HORA EXTRA**
        
        - **Gestor:** {aprovador}
        - **Iniciado em:** {inicio.strftime('%H:%M')}
        - **Tempo decorrido:** {horas}h {minutos}min
        - **Justificativa:** {justificativa}
        """)
    
    elif status == 'em_execucao':
        st.success(f"""
        ⏱️ **HORA EXTRA EM ANDAMENTO**
        
        - **Aprovada por:** {aprovador}
        - **Iniciado em:** {inicio.strftime('%H:%M')}
        - **⏱️ Tempo decorrido:** {horas}h {minutos}min
        """)
        
        if st.button("🛑 Encerrar Hora Extra", type="primary", use_container_width=True):
            # Encerrar hora extra
            conn = get_connection()
            cursor = conn.cursor()
            
            agora = datetime.now()
            tempo_total_minutos = int(tempo_decorrido.total_seconds() / 60)
            
            cursor.execute(f"""
                UPDATE horas_extras_ativas
                SET status = 'encerrada',
                    data_fim = {SQL_PLACEHOLDER},
                    hora_fim = {SQL_PLACEHOLDER},
                    tempo_decorrido_minutos = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
            """, (
                agora.strftime('%Y-%m-%d %H:%M:%S'),
                agora.strftime('%H:%M'),
                tempo_total_minutos,
                he_id
            ))
            
            # Registrar na tabela de solicitações de horas extras
            cursor.execute(f"""
                INSERT INTO solicitacoes_horas_extras
                (usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado, status, aprovado_por, data_aprovacao)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aprovada', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
            """, (
                st.session_state.usuario,
                inicio.strftime('%Y-%m-%d'),
                inicio.strftime('%H:%M'),
                agora.strftime('%H:%M'),
                justificativa,
                aprovador,
                aprovador,
                agora.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Hora extra encerrada! Total: {horas}h {minutos}min")
            st.balloons()
            
            # Atualizar a cada 30 segundos
            import time
            time.sleep(2)
            st.rerun()
```

#### Integrar na tela do funcionário:

No `tela_funcionario()`, logo após o header (linha ~615):

```python
# Verificar hora extra em andamento
exibir_hora_extra_em_andamento()

# Se solicitou hora extra, mostrar formulário
if st.session_state.get('solicitar_horas_extras'):
    iniciar_hora_extra_interface()
    return  # Não exibir resto da interface
```

---

### PARTE 4: Aprovação de Hora Extra pelo Gestor

#### Modificar: `notificacoes_interface()` ou criar nova interface de aprovação rápida

Adicionar lógica para gestor aprovar/rejeitar hora extra em tempo real:

```python
def aprovar_hora_extra_rapida_interface():
    """Interface para gestor aprovar horas extras solicitadas em tempo real"""
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Buscar horas extras aguardando aprovação deste gestor
    cursor.execute(f"""
        SELECT id, usuario, justificativa, data_inicio, hora_inicio
        FROM horas_extras_ativas
        WHERE aprovador = {SQL_PLACEHOLDER} AND status = 'aguardando_aprovacao'
        ORDER BY data_inicio DESC
    """, (st.session_state.usuario,))
    
    solicitacoes = cursor.fetchall()
    conn.close()
    
    if not solicitacoes:
        return
    
    st.warning(f"⚠️ {len(solicitacoes)} solicitação(ões) de hora extra aguardando sua aprovação!")
    
    for he_id, usuario, justificativa, data_inicio, hora_inicio in solicitacoes:
        with st.expander(f"🕐 {usuario} - Solicitado em {hora_inicio}"):
            st.write(f"**Funcionário:** {usuario}")
            st.write(f"**Início:** {data_inicio}")
            st.write(f"**Justificativa:** {justificativa}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Aprovar", key=f"aprovar_he_{he_id}", use_container_width=True):
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute(f"""
                        UPDATE horas_extras_ativas
                        SET status = 'em_execucao'
                        WHERE id = {SQL_PLACEHOLDER}
                    """, (he_id,))
                    
                    conn.commit()
                    conn.close()
                    
                    st.success("✅ Hora extra aprovada!")
                    st.rerun()
            
            with col2:
                if st.button("❌ Rejeitar", key=f"rejeitar_he_{he_id}", use_container_width=True):
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute(f"""
                        UPDATE horas_extras_ativas
                        SET status = 'rejeitada'
                        WHERE id = {SQL_PLACEHOLDER}
                    """, (he_id,))
                    
                    conn.commit()
                    conn.close()
                    
                    st.warning("❌ Hora extra rejeitada!")
                    st.rerun()
```

Adicionar na `tela_gestor()`, logo após o header:

```python
# Notificações de hora extra em tempo real
aprovar_hora_extra_rapida_interface()
```

---

## 🚀 ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

1. **PRIMEIRO:** Testar funções do `jornada_semanal_system.py`
   ```python
   from jornada_semanal_system import *
   print(obter_jornada_usuario('admin'))
   print(verificar_horario_saida_proximo('admin'))
   ```

2. **SEGUNDO:** Adicionar interface de jornada semanal na aba de EDIÇÃO de usuários
   - Testar salvar/carregar configuração

3. **TERCEIRO:** Adicionar interface de jornada semanal na aba de CRIAÇÃO de usuários
   - Testar criar usuário com jornada personalizada

4. **QUARTO:** Implementar botão de hora extra com base no horário de saída
   - Usar `verificar_horario_saida_proximo()`

5. **QUINTO:** Implementar interface de iniciar hora extra
   - Formulário de solicitação
   - Salvar em `horas_extras_ativas`

6. **SEXTO:** Implementar contador em tempo real
   - Função `exibir_hora_extra_em_andamento()`
   - Auto-refresh a cada 30s

7. **SÉTIMO:** Implementar aprovação pelo gestor
   - Interface de aprovação rápida
   - Notificações push

8. **OITAVO:** Testes completos
   - Testar fluxo completo: solicitar → aprovar → executar → encerrar
   - Testar com diferentes jornadas semanais

---

## 🛡️ GARANTIR QUE ERROS ANTERIORES NÃO VOLTEM

### ⚠️ CHECKLIST DE SEGURANÇA:

- [ ] **Sempre usar `SQL_PLACEHOLDER` ao invés de `?` ou `%s`**
  ```python
  cursor.execute(f"SELECT * FROM usuarios WHERE id = {SQL_PLACEHOLDER}", (user_id,))
  ```

- [ ] **Sempre remover timezone antes de salvar datetime no PostgreSQL**
  ```python
  agora_br = get_datetime_br()
  data_hora_registro = agora_br.replace(tzinfo=None)
  ```

- [ ] **Usar `safe_datetime_parse()` ao processar datas do PostgreSQL**
  ```python
  from calculo_horas_system import safe_datetime_parse
  data_obj = safe_datetime_parse(data_string_ou_datetime)
  ```

- [ ] **Sempre usar `get_connection()` e nunca reusar conexões após erro**
  ```python
  conn = get_connection()  # Nova conexão
  try:
      cursor.execute(...)
  except Exception as e:
      conn.close()  # Fechar conexão com erro
      conn = get_connection()  # Abrir nova
  ```

- [ ] **Nunca assumir que coluna existe - verificar schema primeiro**
  ```python
  # Não fazer queries com colunas que não existem (ex: ativo em feriados)
  ```

---

## 📝 NOTAS FINAIS

- Todas as migrations foram aplicadas com sucesso
- O banco está pronto para receber as configurações de jornada semanal
- O módulo `jornada_semanal_system.py` fornece todas as funções necessárias
- Basta integrar a interface conforme documentado acima
- **Sugestão:** Implemente uma funcionalidade por vez e teste antes de prosseguir

## 🆘 EM CASO DE DÚVIDAS

- Consulte `jornada_semanal_system.py` para ver funções disponíveis
- Veja `apply_jornada_semanal_migration.py` para entender estrutura do banco
- Os exemplos de código acima estão completos e podem ser copiados/adaptados

---

**Data de criação:** 07/11/2024
**Status:** Infraestrutura pronta, aguardando integração de interface
