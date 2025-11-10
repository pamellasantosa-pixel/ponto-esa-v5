# 🔧 Guia de Correção - Executar Migration no Render

## 🐛 Problemas Corrigidos

### 1. ✅ Checkbox "Não tenho atestado" não aparecia
**Status:** CORRIGIDO no código

- Checkbox agora aparece **ANTES** do botão submit
- Upload só aparece se **NÃO** marcar o checkbox
- Aviso visual quando marcar
- Aplicado em:
  - `atestado_horas_interface()`
  - `registrar_ausencia_interface()`

### 2. ⚠️ Tabela `horas_extras_ativas` não existe
**Status:** REQUER AÇÃO MANUAL NO RENDER

---

## 🚀 Executar Migration no Render

### Opção 1: Via Console do Render (Recomendado)

1. **Acessar Console do Render:**
   - Abra https://dashboard.render.com
   - Selecione seu serviço `ponto-esa-v5`
   - Clique em **"Shell"** no menu lateral

2. **Executar Migration:**
   ```bash
   cd /opt/render/project/src/ponto_esa_v5
   python apply_jornada_semanal_migration.py
   ```

3. **Verificar Saída:**
   ```
   ============================================================
   🔧 APLICAR MIGRATIONS - JORNADA SEMANAL E HORAS EXTRAS
   ============================================================
   🔄 Iniciando migration de jornada semanal...
     ✅ Coluna 'jornada_seg_inicio' adicionada
     ...
   ✅ Migration de jornada semanal concluída!
   
   🔄 Criando tabela de horas extras ativas...
     ✅ Tabela 'horas_extras_ativas' criada
   ✅ Migration de horas extras ativas concluída!
   
   ============================================================
   ✅ TODAS AS MIGRATIONS FORAM APLICADAS COM SUCESSO!
   ============================================================
   ```

4. **Reiniciar Serviço:**
   - Clique em **"Manual Deploy"** → **"Clear build cache & deploy"**
   - Aguarde conclusão

---

### Opção 2: Via SQL Direto no Banco PostgreSQL

1. **Acessar PostgreSQL:**
   - Vá em **"Dashboard"** → Selecione o banco de dados PostgreSQL
   - Clique em **"Connect"** → **"External Connection"**
   - Use as credenciais fornecidas

2. **Executar SQL:**

```sql
-- Criar tabela horas_extras_ativas
CREATE TABLE IF NOT EXISTS horas_extras_ativas (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(255) NOT NULL,
    aprovador VARCHAR(255) NOT NULL,
    justificativa TEXT NOT NULL,
    data_inicio TIMESTAMP NOT NULL,
    hora_inicio TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'em_execucao',
    data_fim TIMESTAMP,
    hora_fim TIME,
    tempo_decorrido_minutos INTEGER,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario) REFERENCES usuarios(usuario),
    FOREIGN KEY (aprovador) REFERENCES usuarios(usuario)
);

-- Verificar se tabela foi criada
SELECT COUNT(*) FROM horas_extras_ativas;
```

3. **Adicionar Colunas de Jornada Semanal (se ainda não existirem):**

```sql
-- Segunda-feira
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_seg_inicio TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_seg_fim TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trabalha_seg INTEGER DEFAULT 1;

-- Terça-feira
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_ter_inicio TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_ter_fim TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trabalha_ter INTEGER DEFAULT 1;

-- Quarta-feira
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_qua_inicio TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_qua_fim TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trabalha_qua INTEGER DEFAULT 1;

-- Quinta-feira
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_qui_inicio TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_qui_fim TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trabalha_qui INTEGER DEFAULT 1;

-- Sexta-feira
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_sex_inicio TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_sex_fim TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trabalha_sex INTEGER DEFAULT 1;

-- Sábado
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_sab_inicio TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_sab_fim TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trabalha_sab INTEGER DEFAULT 0;

-- Domingo
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_dom_inicio TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS jornada_dom_fim TIME;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS trabalha_dom INTEGER DEFAULT 0;

-- Copiar jornada padrão para seg-sex
UPDATE usuarios 
SET 
    jornada_seg_inicio = jornada_inicio_previsto,
    jornada_seg_fim = jornada_fim_previsto,
    jornada_ter_inicio = jornada_inicio_previsto,
    jornada_ter_fim = jornada_fim_previsto,
    jornada_qua_inicio = jornada_inicio_previsto,
    jornada_qua_fim = jornada_fim_previsto,
    jornada_qui_inicio = jornada_inicio_previsto,
    jornada_qui_fim = jornada_fim_previsto,
    jornada_sex_inicio = jornada_inicio_previsto,
    jornada_sex_fim = jornada_fim_previsto
WHERE jornada_seg_inicio IS NULL;
```

---

### Opção 3: Via Variável de Ambiente (Automático)

1. **Adicionar Hook de Deploy:**
   - No Render Dashboard → Seu serviço
   - Settings → Build & Deploy
   - Em **"Build Command"**, adicionar:
   ```bash
   pip install -r requirements-pinned.txt && python ponto_esa_v5/apply_jornada_semanal_migration.py
   ```

2. **Deploy:**
   - A migration será executada automaticamente a cada deploy

---

## ✅ Verificar se Migration Foi Aplicada

### Via Aplicação Web:

1. Acesse a aplicação: https://seu-app.onrender.com
2. Faça login como funcionário
3. Tente solicitar hora extra (botão deve aparecer 5 min antes do fim da jornada)
4. Se não houver erro `relation "horas_extras_ativas" does not exist`, está OK!

### Via SQL:

```sql
-- Verificar se tabela existe
SELECT * FROM horas_extras_ativas LIMIT 1;

-- Verificar colunas de jornada semanal
SELECT jornada_seg_inicio, jornada_seg_fim 
FROM usuarios 
LIMIT 1;
```

---

## 📊 Status das Correções

| Problema | Status | Requer Ação |
|----------|--------|-------------|
| Checkbox atestado | ✅ Corrigido | Não (já no código) |
| Tabela horas_extras_ativas | ⚠️ Pendente | **SIM - Executar migration** |
| Proteção de erro | ✅ Corrigido | Não (já no código) |
| Auto-refresh contador | ✅ Implementado | Não (já no código) |

---

## 🔍 Troubleshooting

### Erro: "relation already exists"
**Solução:** Tabela já foi criada. Ignore o erro e continue.

### Erro: "column already exists"
**Solução:** Colunas já foram adicionadas. Ignore o erro e continue.

### Erro: "permission denied"
**Solução:** Use o usuário master do banco de dados.

### Erro: "could not connect to server"
**Solução:** 
1. Verifique se o banco está ativo no Render
2. Verifique as credenciais de conexão
3. Tente novamente em alguns minutos

---

## 📝 Commit Realizado

**Commit:** `e51886a`  
**Mensagem:** "fix: corrigir interface de atestados e proteção para tabela horas_extras_ativas"

**Alterações:**
- ✅ Checkbox "Não tenho atestado" agora aparece corretamente
- ✅ Proteção contra erro se tabela não existir
- ✅ Migration atualizada para PostgreSQL
- ✅ Mensagens de erro mais claras

---

## 🎯 Próximos Passos

1. **Executar migration no Render** (Opção 1, 2 ou 3 acima)
2. **Verificar se migration funcionou** (testar na aplicação)
3. **Testar interface de atestados** (checkbox deve aparecer)
4. **Testar sistema de horas extras** (não deve ter erro de tabela)

---

## ⚡ Comandos Rápidos

```bash
# No Console do Render
cd /opt/render/project/src/ponto_esa_v5
python apply_jornada_semanal_migration.py

# Ou via SQL direto
CREATE TABLE IF NOT EXISTS horas_extras_ativas (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(255) NOT NULL,
    aprovador VARCHAR(255) NOT NULL,
    justificativa TEXT NOT NULL,
    data_inicio TIMESTAMP NOT NULL,
    hora_inicio TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'em_execucao',
    data_fim TIMESTAMP,
    hora_fim TIME,
    tempo_decorrido_minutos INTEGER,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

**Data:** 07/11/2025  
**Status:** ✅ Código corrigido e enviado ao GitHub  
**Ação Pendente:** ⚠️ Executar migration no Render
