# 🔧 PRÉ-SESSÃO: PREPARAÇÃO PARA 1º DE DEZEMBRO

## ✅ CHECKLIST DE PREPARAÇÃO

Execute **ANTES** de 1º de dezembro para evitar atrasos no dia.

---

## 1️⃣  VERIFICAR AMBIENTE PYTHON

```bash
# Terminal
python --version
# Resultado esperado: Python 3.11+ (você tem 3.13, perfeito!)

# Verificar packages necessárias
pip list | grep -E "pyotp|qrcode|cryptography"
```

### Se faltar packages:
```bash
pip install pyotp qrcode cryptography python-dotenv
```

---

## 2️⃣  VERIFICAR BANCO DE DADOS

```bash
# PostgreSQL rodando?
# Teste:
python -c "
import psycopg2
import os
url = os.getenv('DATABASE_URL')
if url:
    conn = psycopg2.connect(url)
    print('✅ PostgreSQL OK')
    conn.close()
else:
    print('⚠️  DATABASE_URL não encontrada')
"
```

---

## 3️⃣  CRIAR BRANCH GIT

```bash
# Navegar ao projeto
cd c:\Users\lf\OneDrive\ponto_esa_v5_implemented

# Ver status
git status

# Se houver mudanças não commitadas:
git stash

# Criar branch para trabalho
git checkout -b feature/lgpd-wcag-2fa-monitoring

# Verificar
git branch
```

---

## 4️⃣  BACKUP DO CÓDIGO ATUAL

```bash
# Criar backup completo
Copy-Item -Path "c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5" `
         -Destination "c:\Users\lf\OneDrive\ponto_esa_v5_implemented\backup_pre_01dez_2025" `
         -Recurse

# Verificar
Get-ChildItem "c:\Users\lf\OneDrive\ponto_esa_v5_implemented\backup_pre_01dez_2025" | Measure-Object
```

---

## 5️⃣  CRIAR ESTRUTURA BÁSICA (Opcional - faz hoje)

Se quiser, posso criar os arquivos vazios hoje:

```bash
# Criar estrutura
New-Item -Type File "c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\lgpd_system.py"
New-Item -Type File "c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\two_factor_auth_system.py"
New-Item -Type File "c:\Users\lf\OneDrive\ponto_esa_v5_implemented\ponto_esa_v5\performance_alerts.py"
```

---

## 6️⃣  VERIFICAR RENDER.COM

```
1. Abra: https://dashboard.render.com
2. Clique em: ponto-esa-v5 (seu service)
3. Verifique: Environment variables
   - USE_POSTGRESQL=true
   - DATABASE_URL está configurada
4. Confirme: Deploy está online (verde)
```

---

## 7️⃣  LISTAR TABELAS EXISTENTES

```bash
# Ver quais tabelas já existem
python -c "
import psycopg2
import os

DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute('''
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
''')

print('Tabelas existentes:')
for table in cur.fetchall():
    print(f'  ✅ {table[0]}')

conn.close()
"
```

---

## 📋 CHECKLIST PRÉ-1º DE DEZEMBRO

```
PRÉ-REQUISITOS:

□ Python 3.11+ instalado
  └─ Verificar: python --version

□ Packages instaladas
  ├─ pyotp (TOTP)
  ├─ qrcode (QR codes)
  ├─ cryptography (criptografia)
  └─ Verificar: pip install pyotp qrcode cryptography

□ PostgreSQL funcionando
  ├─ Conexão testada
  ├─ DATABASE_URL configurada
  └─ Render.com online

□ Git branch criado
  ├─ Comando: git checkout -b feature/lgpd-wcag-2fa-monitoring
  └─ Verificar: git branch

□ Backup feito
  ├─ Pasta: backup_pre_01dez_2025/
  └─ Tamanho > 100MB

□ Estrutura básica (opcional)
  ├─ lgpd_system.py (vazio)
  ├─ two_factor_auth_system.py (vazio)
  └─ performance_alerts.py (vazio)

□ Documentação revisada
  ├─ AGENDAMENTO_01_DEZEMBRO_2025.md
  ├─ FEATURES_OPCIONAIS_DETALHADAS.md
  └─ Conhecer os 4 sistemas
```

---

## ⚠️  COISAS IMPORTANTES A SABER

### 1. Não terá interrupção no app.py
- Vamos trabalhar em módulos separados primeiro
- Integração apenas no final (última hora)
- Render.com continuará rodando normal

### 2. Migrations automáticas
- Tabelas novas serão criadas automaticamente
- Sem perder dados existentes
- Backup ativado previamente

### 3. Testes são importantes
- 30 min de teste final (16:00-16:30)
- Checklist completo
- Sem deploy sem passar em testes

### 4. Se algo der errado
- Revert fácil: `git reset --hard HEAD~1`
- Backup pronto: `backup_pre_01dez_2025/`
- PostgreSQL pode ser restaurado

---

## 🎯 DIA 1º DE DEZEMBRO

### ✅ Ao acordar (dia agendado):
1. Abra este arquivo: `AGENDAMENTO_01_DEZEMBRO_2025.md`
2. Leia a agenda detalhada (5 min)
3. Confirme que está pronto
4. Comece às 09:00 em ponto

### ✅ Durante o dia:
1. Siga a agenda hora por hora
2. Faça os testes conforme indicado
3. Pause para almoço às 13:00-14:00
4. Finalize às 17:00 com commit

### ✅ Resultado esperado:
- ✅ 4 sistemas implementados
- ✅ Tudo testado
- ✅ Documentação criada
- ✅ Commit no GitHub
- ✅ v5.1 pronto para produção

---

## 📞 RESUMO RÁPIDO

| O que fazer | Quando | Status |
|-----------|--------|--------|
| Setup Python/packages | Antes 1º dez | ⏳ Pendente |
| Criar branch Git | Antes 1º dez | ⏳ Pendente |
| Backup código | Antes 1º dez | ⏳ Pendente |
| Verificar Render.com | Antes 1º dez | ⏳ Pendente |
| **IMPLEMENTAR TUDO** | **1º dez 09:00-17:00** | ⏳ **Agendado** |
| Deploy | 1º dez 17:00 | ⏳ Depois |

---

## 🚀 CONFIRME COMIGO AGORA

Responda (ou indique que leu):

```
□ Confirmado: 1º de dezembro de 2025
□ Hora: 09:00 - 17:00
□ Local: Seu computador (ambiente desenvolvimento)
□ Deixar tudo rodando: app, PostgreSQL, Git
□ Lido: AGENDAMENTO_01_DEZEMBRO_2025.md
```

Se tudo está OK, você está pronto! 🎉

---

**Arquivo**: PRE_SESSAO_PREPARACAO.md  
**Data**: 19 de novembro de 2025  
**Para execução**: 1º de dezembro de 2025  
**Status**: ✅ Pronto para agendar
