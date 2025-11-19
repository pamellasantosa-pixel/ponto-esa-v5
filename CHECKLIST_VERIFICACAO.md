# ✅ CHECKLIST DE VERIFICAÇÃO - JORNADA SEMANAL COM HORA EXTRA

**Data:** 18/11/2024  
**Versão:** 1.0  
**Status:** Pronto para Verificação  

---

## 📋 VERIFICAÇÃO DE ARQUIVOS

### ✅ Arquivos Criados

- [x] `ponto_esa_v5/jornada_semanal_calculo_system.py` (650 linhas)
  - Contém: JornadaSemanalCalculoSystem com 6 métodos
  - Testes: sim (test_jornada_semanal_calculo.py)
  
- [x] `tests/test_jornada_semanal_calculo.py` (300 linhas)
  - Testes: 6 casos principais
  - Framework: pytest
  
- [x] `PLANO_JORNADA_HORA_EXTRA.md`
  - Planejamento completo
  - 5 fases documentadas
  
- [x] `CONCLUSAO_JORNADA_HORA_EXTRA.md`
  - Detalhes técnicos
  - Arquitetura final
  
- [x] `RESUMO_JORNADA_HORA_EXTRA.md`
  - Resumo executivo
  - Exemplos de uso

### ✅ Arquivos Modificados

- [x] `ponto_esa_v5/apply_jornada_semanal_migration.py`
  - [x] Adicionadas 7 colunas intervalo_XXX
  - [x] DEFAULT 60 para cada coluna
  - [x] Comentários adicionados
  
- [x] `ponto_esa_v5/jornada_semanal_system.py`
  - [x] JORNADA_COLUMNS atualizado (28 colunas)
  - [x] obter_jornada_usuario() estendido
  - [x] salvar_jornada_semanal() estendido
  - [x] Suporta intervalo_XXX
  
- [x] `ponto_esa_v5/app_v5_final.py`
  - [x] Função configurar_jornada_interface() (~200 linhas)
  - [x] Função exibir_alerta_fim_jornada_avancado() (~80 linhas)
  - [x] Integração em tela_funcionario()
  - [x] Integração em registrar_ponto_interface()
  - [x] Menu gestor adicionado "📅 Configurar Jornada"
  - [x] Elif adicionado para nova opção

---

## 🧪 VERIFICAÇÃO FUNCIONAL

### ✅ Fase 1: Banco de Dados

```python
# Verificar se colunas existem:
# SELECT * FROM usuarios LIMIT 1;
# Procurar por: intervalo_seg, intervalo_ter, ..., intervalo_dom

# Comando para adicionar (se não existir):
# python apply_jornada_semanal_migration.py
```

**Checklist:**
- [ ] 7 colunas de intervalo criadas
- [ ] DEFAULT value é 60
- [ ] Todas as linhas têm valor (não NULL)

### ✅ Fase 2: Sistema de Cálculo

```python
# Testar no Python interativo:
from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
from datetime import date

# Teste 1: Calcular horas esperadas
resultado = JornadaSemanalCalculoSystem.calcular_horas_esperadas_dia(
    usuario='seu_usuario',
    data=date.today()
)
print(resultado)
# Esperado: dict com 'horas_esperadas', 'intervalo_minutos', etc

# Teste 2: Detectar hora extra
resultado = JornadaSemanalCalculoSystem.detectar_hora_extra_dia(
    usuario='seu_usuario',
    data=date.today()
)
print(resultado)
# Esperado: dict com 'tem_hora_extra', 'horas_extra', 'categoria'
```

**Checklist:**
- [ ] Import funciona sem erros
- [ ] calcular_horas_esperadas_dia() retorna float
- [ ] detectar_hora_extra_dia() retorna dict
- [ ] detectar_hora_extra_dia() tem chave 'tem_hora_extra'
- [ ] Tolerância aplicada (5 min padrão)

### ✅ Fase 3: Interface Gestor

```
1. Logar como gestor
2. Menu esquerdo → "📅 Configurar Jornada"
3. Verificar:
   - Dropdown de funcionários aparece
   - Tabela com 7 dias aparece
   - Cada dia tem botão expansível
```

**Checklist:**
- [ ] Opção "📅 Configurar Jornada" no menu
- [ ] Dropdown funciona
- [ ] Tabela com 7 dias visível
- [ ] Clicar em dia abre modal
- [ ] Modal tem inputs: trabalha, hora_inicio, hora_fim, intervalo
- [ ] Botão "Salvar" funciona
- [ ] Atalhos funcionam (copiar, desativar, resetar)

### ✅ Fase 4: Detecção de Hora Extra

```
1. Funcionário registra ponto tipo "Fim"
2. Sistema deve calcular automaticamente
3. Se hora extra, mostra mensagem com horas
```

**Checklist:**
- [ ] Ao registrar ponto "Fim", calcula automático
- [ ] Se tem HE, mostra: "⏱️ HORA EXTRA DETECTADA!"
- [ ] Mostra horas extra calculadas
- [ ] Mostra esperado vs registrado
- [ ] Botão "📝 Solicitar Aprovação" funciona
- [ ] Se dentro da jornada, mostra: "✅ Tempo registrado..."
- [ ] Se abaixo da jornada, mostra: "⏰ Você trabalhou X min menos..."

### ✅ Fase 5: Alerta 5 Minutos

```
1. Funcionário loga próximo do fim da jornada
2. Se ≤ 5 min: card deve aparecer no topo da tela
3. Se > 5 min: nada deve aparecer
```

**Checklist:**
- [ ] Card aparece quando ≤ 5 min
- [ ] Card mostra: "⏰ FALTA POUCO..."
- [ ] Card tem design destacado (gradiente rosa)
- [ ] Card tem animação de pulso
- [ ] Botão "✅ Vou Finalizar" funciona
- [ ] Botão "⏱️ Vou Fazer Hora Extra" funciona
- [ ] Card não aparece quando > 5 min (correto)

### ✅ Fase 6: Testes

```bash
# Rodar testes:
cd ponto_esa_v5
python -m pytest tests/test_jornada_semanal_calculo.py -v

# Esperado: 6 testes passam
```

**Checklist:**
- [ ] test_calcular_horas_esperadas_dia_normal ✅
- [ ] test_calcular_horas_registradas_dia_com_pontos ✅
- [ ] test_detectar_hora_extra_positiva ✅
- [ ] test_detectar_hora_extra_nenhuma ✅
- [ ] test_validar_ponto_dia_nao_trabalha ✅
- [ ] test_obter_tempo_ate_fim_jornada ✅

---

## 🔄 VERIFICAÇÃO DE COMPATIBILIDADE

### ✅ Não Quebra Sistema Existente

**Teste 1: Registrar Ponto Normal**
```
1. Logar como funcionário
2. Menu → "🕐 Registrar Ponto"
3. Registrar ponto tipo "Início" e "Fim"
4. Verificar: funciona como antes
```

**Checklist:**
- [ ] Ponto registra normalmente
- [ ] Mensagem de sucesso aparece
- [ ] Hora é registrada corretamente
- [ ] Nenhum erro no console

**Teste 2: Solicitação de Hora Extra**
```
1. Logar como funcionário
2. Registrar ponto com hora extra
3. Clicar "Solicitar Aprovação"
4. Verificar: abre formulário normal
5. Gestor aprova normalmente
```

**Checklist:**
- [ ] Formulário de HE abre
- [ ] Campos aparecem (justificativa, etc)
- [ ] Pode submeter normalmente
- [ ] Gestor aprova
- [ ] Hora extra é registrada

**Teste 3: Sistema Antigo (Fallback)**
```
1. Renomear jornada_semanal_calculo_system.py temporariamente
2. Registrar ponto tipo "Fim"
3. Verificar: usa sistema antigo, sem erro
4. Restaurar arquivo
```

**Checklist:**
- [ ] Sem arquivo de cálculo, funciona fallback
- [ ] Sem mensagem de hora extra, mas não quebra
- [ ] Recupera quando arquivo restaurado

---

## 📊 DADOS ESPERADOS

### Estrutura da Jornada no Banco

```sql
-- Para funcionário "joao":
SELECT usuario, 
       trabalha_seg, jornada_seg_inicio, jornada_seg_fim, intervalo_seg,
       trabalha_ter, jornada_ter_inicio, jornada_ter_fim, intervalo_ter,
       -- ... etc para todos os dias
FROM usuarios
WHERE usuario = 'joao';

-- Esperado:
-- joao, 1, 08:00, 18:00, 60, 1, 08:00, 18:00, 60, ...
```

### Estrutura de Registros de Ponto

```sql
-- Para funcionário "joao" em 18/11/2024:
SELECT id, usuario, data_hora, tipo, modalidade, projeto, atividade
FROM registros_ponto
WHERE usuario = 'joao' AND DATE(data_hora) = '2024-11-18'
ORDER BY data_hora;

-- Esperado:
-- 1, joao, 2024-11-18 08:00:00, Início, ...
-- 2, joao, 2024-11-18 18:30:00, Fim, ...
```

---

## ⚠️ PROBLEMAS COMUNS E SOLUÇÕES

### Problema 1: "Módulo jornada_semanal_calculo_system não encontrado"

**Solução:**
```bash
# Verificar se arquivo existe:
ls -la ponto_esa_v5/jornada_semanal_calculo_system.py

# Se não existir, copiar do backup:
cp backups/jornada_semanal_calculo_system.py ponto_esa_v5/

# Ou recriar do zero
```

### Problema 2: "Colunas intervalo_XXX não existem"

**Solução:**
```bash
# Rodar migration:
cd ponto_esa_v5
python apply_jornada_semanal_migration.py

# Ou adicionar manualmente:
# sqlite3 database.db "ALTER TABLE usuarios ADD COLUMN intervalo_seg INTEGER DEFAULT 60;"
```

### Problema 3: "Alerta não aparece mesmo após 5 min"

**Solução:**
```python
# Verificar se jornada está configurada:
SELECT * FROM usuarios WHERE usuario = 'seu_usuario';
# Procurar por: trabalha_seg/ter/qua/etc = 1

# Se não tiver jornada configurada, alerta não aparece (normal)
# Gestor precisa configurar via interface
```

### Problema 4: "Hora extra não detecta mesmo tendo pontos"

**Solução:**
```python
# Verificar pontos do dia:
SELECT * FROM registros_ponto 
WHERE usuario = 'seu_usuario' AND DATE(data_hora) = '2024-11-18';

# Precisa ter:
# - Tipo "Início" (ou "inicio") 
# - Tipo "Fim" (ou "fim")
# Se tiver apenas intermediário, não calcula

# Verificar jornada:
SELECT trabalha_seg FROM usuarios WHERE usuario = 'seu_usuario';
# Se = 0, funcionário não trabalha segunda, sem HE possível
```

---

## 🎯 CHECKLIST FINAL

### Antes de Deploy

- [ ] Todos os 4 arquivos criados existem
- [ ] Todos os 3 arquivos modificados têm mudanças corretas
- [ ] 6 testes passam
- [ ] Interface gestor acessível
- [ ] Detecção de HE funciona
- [ ] Alertas 5 min funcionam
- [ ] Fallback para sistema antigo funciona
- [ ] Nenhum erro no console/logs
- [ ] RH validou cálculos de exemplo
- [ ] Backup dos arquivos antigos feito

### No Dia do Deploy

- [ ] Backup completo do banco de dados
- [ ] Testar em staging primeiro (se houver)
- [ ] Avisar gestores sobre novo menu
- [ ] Avisar gestores sobre configurar jornada
- [ ] Monitorar logs por 24 horas
- [ ] Plano de rollback preparado

---

## 📞 SUPORTE RÁPIDO

**Erro ao importar:**
```python
# Verify sys.path includes app directory
import sys
print(sys.path)
# Should include: /path/to/ponto_esa_v5_implemented/ponto_esa_v5
```

**Erro SQL:**
```python
# Test database connection
from database import get_connection
conn = get_connection()
print(conn)  # Should return connection object
```

**Erro ao calcular:**
```python
# Test with logging
import logging
logging.basicConfig(level=logging.DEBUG)
# Run operation and check logs
```

---

## ✨ CONCLUSÃO DA VERIFICAÇÃO

Se todos os checks passarem, o sistema está:
- ✅ Implementado corretamente
- ✅ Testado adequadamente
- ✅ Compatível com sistema existente
- ✅ Pronto para produção

**Próximo Passo:** Deploy com confiança! 🚀

---

_Checklist criado: 18/11/2024_  
_Sistema: Ponto ESA v5_  
_Feature: Jornada Semanal com Hora Extra_

