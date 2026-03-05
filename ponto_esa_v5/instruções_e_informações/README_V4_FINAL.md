# Ponto ExSA v4.0 - Sistema de Controle de Ponto

**Versão Final Completa com Atestado de Horas e Upload de Arquivos**

Desenvolvido por **Pâmella SAR** para **Expressão Socioambiental Pesquisa e Projetos**

---

## 📋 Visão Geral

O Ponto ExSA v4.0 é um sistema completo de controle de ponto desenvolvido especificamente para a Expressão Socioambiental Pesquisa e Projetos. Esta versão final inclui todas as funcionalidades solicitadas, correções de bugs e melhorias de usabilidade.

## ✨ Principais Funcionalidades

### 👤 Para Funcionários
- **Registro de Ponto Flexível**: Registre início, múltiplos intermediários e fim
- **Modalidades de Trabalho**: Presencial, Home Office e Trabalho em Campo
- **Registro Retroativo**: Até 3 dias anteriores
- **Atestado de Horas**: Nova funcionalidade para ausências parciais com horários específicos
- **Upload de Arquivos**: Sistema completo para anexar comprovantes
- **Histórico Completo**: Visualize todos os seus registros
- **Sistema Offline**: Funciona sem internet e sincroniza quando conectado

### 👨‍💼 Para Gestores
- **Painel Administrativo**: Dashboard completo com métricas
- **Aprovação de Atestados**: Aprovar/rejeitar atestados de horas
- **Gerenciamento de Projetos**: Adicionar, editar e remover projetos
- **Gerenciamento de Usuários**: Adicionar, desativar e **excluir funcionários**
- **Relatórios Completos**: Exportação para Excel
- **Auditoria**: Visualização de todos os registros do sistema

## 🆕 Novas Funcionalidades v4.0

### ⏰ Sistema de Atestado de Horas
- Registro de ausências parciais com horários específicos
- Cálculo automático de horas de ausência
- Upload de comprovantes (atestados médicos, declarações)
- Fluxo de aprovação pelo gestor
- Validação de conflitos com registros de ponto

### 📁 Sistema de Upload de Arquivos
- Upload seguro de documentos (PDF, DOC, DOCX, JPG, PNG)
- Limite de 5MB por arquivo
- Categorização automática (ausência, atestado_horas, documento)
- Gerenciamento completo de arquivos
- Preview de imagens
- Download e exclusão de arquivos

### 🗑️ Exclusão de Funcionários
- Gestores podem excluir funcionários do sistema
- Exclusão completa incluindo todos os registros relacionados
- Proteção contra exclusão de gestores
- Confirmação de segurança

### 🔧 Correções de Bugs
- **Registro de Ponto**: Corrigido bug que impedia registrar em dias diferentes após finalizar
- **Login**: Melhorado sistema de autenticação
- **Interface**: Correções de responsividade e usabilidade

## 🎨 Design e Interface

### Layout de Login
- Fundo com imagem da Expressão Socioambiental
- Título em marrom com borda esfumaçada
- Botão "ENTRAR" em azul
- Textos de rodapé posicionados corretamente

### Interface Principal
- Design moderno e responsivo
- Cores da identidade visual da empresa
- Navegação intuitiva
- Feedback visual claro

## 🔐 Credenciais de Acesso

### Funcionário
- **Usuário**: `funcionario`
- **Senha**: `senha_func_123`

### Gestor
- **Usuário**: `gestor`
- **Senha**: `senha_gestor_123`

## 📊 Projetos Pré-configurados

O sistema vem com os seguintes projetos já configurados:
- ADMINISTRATIVO
- EXPRESSAO-INTERNO
- FR - 3770-PBAQ
- SAM - 3406-DIALOGO-GERMANO
- SAM - 3406-DIALOGO - UBU
- SAM - 3450-GESTÃO NEGOCIOS (PESCA)
- SAM - 3614-PAEBM - MATIPO
- SAM - 3615-PAEBM - GERMANO
- MVV - 4096-SERROTE
- Trabalho em Campo

## 🔧 Requisitos Técnicos

### Dependências Python
```
streamlit>=1.28.0
pandas>=2.0.0
sqlite3 (incluído no Python)
hashlib (incluído no Python)
datetime (incluído no Python)
os (incluído no Python)
base64 (incluído no Python)
json (incluído no Python)
uuid (incluído no Python)
openpyxl>=3.1.0
psutil>=5.9.0
```

### Requisitos do Sistema
- Python 3.8 ou superior
- 100MB de espaço em disco
- Conexão com internet (opcional - funciona offline)

## 🚀 Instalação

### Método 1: Script Automático (Recomendado)
1. Extraia o arquivo `PontoESA_Completo_V4_Final.zip`
2. Execute `iniciar_ponto_esa_v4_final.py`
3. O script instalará automaticamente as dependências
4. O navegador abrirá automaticamente no endereço correto

### Método 2: Manual
1. Instale o Python 3.8+
2. Execute: `pip install -r requirements.txt`
3. Execute: `streamlit run app_v4_final.py`
4. Acesse: `http://localhost:8501`

## 📱 Uso Mobile (PWA)

O sistema funciona como Progressive Web App:
1. Acesse pelo navegador do celular
2. Toque em "Adicionar à tela inicial"
3. Use como aplicativo nativo

## 🌐 Acesso em Rede

### Para Múltiplos Usuários
- O sistema suporta múltiplos usuários simultâneos
- Configure o servidor para aceitar conexões externas
- Outros computadores acessam via `http://[IP_DO_SERVIDOR]:8501`

### Para Produção
- Use PM2 ou supervisor para manter o aplicativo sempre executando
- Configure firewall para permitir acesso à porta 8501
- Considere usar HTTPS para maior segurança

## 📋 Fluxo de Uso

### Funcionário
1. **Login** com credenciais
2. **Registrar Ponto**: Escolha tipo (Início/Intermediário/Fim)
3. **Atestado de Horas**: Para ausências parciais
4. **Upload de Arquivos**: Anexar comprovantes
5. **Visualizar Registros**: Histórico completo

### Gestor
1. **Login** com credenciais de gestor
2. **Dashboard**: Visão geral do sistema
3. **Aprovar Atestados**: Revisar e aprovar/rejeitar
4. **Gerenciar Projetos**: Adicionar/editar projetos
5. **Gerenciar Usuários**: Adicionar/excluir funcionários
6. **Relatórios**: Exportar dados para Excel

## 🔒 Segurança

- Senhas criptografadas com SHA-256
- Validação de sessão
- Controle de acesso por tipo de usuário
- Backup automático do banco de dados
- Logs de auditoria

## 📊 Banco de Dados

O sistema utiliza SQLite com as seguintes tabelas:
- `usuarios`: Informações dos usuários
- `registros_ponto`: Registros de ponto
- `ausencias`: Ausências registradas
- `projetos`: Projetos disponíveis
- `atestados_horas`: Atestados de horas (nova)
- `uploads`: Arquivos enviados (nova)

## 🛠️ Scripts de Auxílio (novo)

Existem scripts práticos na pasta `tools/` para facilitar desenvolvimento e demonstração:

## 🔄 Migração de Banco de Dados (importante)

Se você estiver atualizando de uma versão anterior, algumas colunas novas foram adicionadas às tabelas (por exemplo, `hash_arquivo` e `status` na tabela `uploads`, e `nao_possui_comprovante` em `atestado_horas`). Há um script de migração leve que garante a compatibilidade:

```powershell
python -m ponto_esa_v5.tools.migrate_db
# ou execute o init_db() diretamente
python -c "from ponto_esa_v5.database import init_db; init_db()"
```

Execute um desses comandos antes de iniciar a aplicação para atualizar o esquema do banco.

## 🔔 Mudança de comportamento de UI

Nota: a opção "❌ Não possuo comprovante" foi movida da tela de registro de ausências para o formulário de **Atestado de Horas**. Agora:

- Na tela **Registrar Ausência** não há mais upload/checkbox — o comprovante deve ser anexado via Atestado quando aplicável.
- No formulário **Atestado de Horas** há a opção **❌ Não possuo atestado físico**. Ao marcar essa opção, o atestado será registrado sem documento e o gestor será notificado; as horas podem ser lançadas como débito no banco de horas até a apresentação do comprovante.

- `tools/setup_db.py` — inicializa (ou recria com `--recreate`) o banco principal em `database/ponto_esa.db` (insere usuários e projetos padrão).
- `tools/demo_setup.py` — cria um banco de demonstração `database/ponto_esa_demo.db` com um usuário `demo_user` e registros de exemplo.

Recomenda-se usar `requirements-pinned.txt` para ambientes de desenvolvimento/CI.

## Dependências recomendadas (arquivo recomendado)

Use o arquivo `requirements-pinned.txt` na raiz do projeto para instalar dependências com versões testadas:

```powershell
python -m pip install -r requirements-pinned.txt
```

## 🐳 Executando com Docker

Há um Dockerfile e um `docker-compose.yml` para rodar a aplicação em contêineres.

1. Build e start com Docker Compose:

```powershell
docker-compose up --build -d
```

2. A aplicação ficará disponível em `http://localhost:8501`.

3. Para parar e remover contêineres:

```powershell
docker-compose down
```

## 🔁 Integração Contínua (GitHub Actions)

Um workflow de CI (`.github/workflows/ci.yml`) foi adicionado para instalar dependências e executar testes automaticamente em pushes/PRs para `main`.


## 🆘 Solução de Problemas

### Login não funciona
- Verifique se as credenciais estão corretas
- Certifique-se de que o banco de dados foi inicializado

### Não consegue registrar ponto
- Verifique se a data está dentro do limite (3 dias retroativos)
- Certifique-se de que a descrição da atividade foi preenchida

### Upload falha
- Verifique se o arquivo é menor que 5MB
- Certifique-se de que o formato é suportado

### Aplicativo não inicia
- Verifique se todas as dependências estão instaladas
- Execute `pip install -r requirements.txt`

## 📞 Suporte

Para dúvidas ou problemas:
- Consulte o arquivo `GUIA_INSTALACAO_DIDATICO.md`
- Verifique os logs do sistema
- Entre em contato com o desenvolvedor

## 📝 Histórico de Versões

### v4.0 (Atual)
- ✅ Sistema de Atestado de Horas
- ✅ Upload de Arquivos
- ✅ Exclusão de Funcionários
- ✅ Correção de bugs de registro
- ✅ Melhorias na interface

### v3.0
- Sistema de notificações
- Modo offline
- PWA para mobile
- Múltiplos usuários simultâneos

### v2.0
- Múltiplos registros intermediários
- Novo layout de login
- Sistema de backup

### v1.0
- Funcionalidades básicas de ponto
- Interface inicial
- Gestão de projetos

---

**Desenvolvido com ❤️ por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos**

*Sistema de ponto exclusivo da empresa Expressão Socioambiental Pesquisa e Projetos*

