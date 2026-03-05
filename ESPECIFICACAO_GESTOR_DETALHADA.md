# Especificação Detalhada — Área do Gestor (Ponto ExSA)

Este documento descreve, por tela, todos os campos, validações e fluxos disponíveis para o perfil de Gestor no sistema Ponto ExSA. Também descreve ações que o gestor pode executar e os efeitos no sistema (notificações, atualizações no banco e integrações).

Observação: siga os nomes de telas/menus conforme aparecem no `app_v5_final.py`.

-------------------------------------------------------------------------------

1) Painel do Gestor (Dashboard)

- Objetivo: oferecer visão consolidada de pendências (correções, atestados, horas extras), lista de colaboradores, e métricas rápidas.

- Componentes / Campos:
  - Filtro `Período` (data início, data fim): tipo `date`; validação: `data_inicio <= data_fim`, limite de intervalo (ex.: 1 ano) opcional.
  - Filtro `Equipe` / `Setor`: `select` com as equipes vinculadas ao gestor; valor obrigatório apenas quando necessário.
  - Campo de busca `Colaborador`: `text` (nome, matrícula); busca por substring, case-insensitive.
  - Cards resumidos: `Pendências Correções`, `Atestados Pendentes`, `Horas Extras Pendentes`, `Saldo Banco Horas` — cada card exibe número e link para a lista correspondente.
  - Tabela `Últimas ações` (log rápido): colunas `Data`, `Usuário`, `Ação`, `Detalhes`, `Ação rápida` (botão para abrir item).

- Ações disponíveis:
  - `Abrir item` — abre painel lateral com detalhes (ver telas específicas abaixo).
  - `Exportar relatório` — CSV/PDF do período filtrado.

- Fluxos importantes:
  - Ao abrir o painel, o sistema carrega contadores via endpoint `/gestor/dashboard` — se houver erro, exibe banner de erro e botão `Tentar novamente`.
  - Cliques nos cards redirecionam para as listas filtradas.

-------------------------------------------------------------------------------

2) Correções / Ajustes de Registro (Lista)

- Objetivo: listar solicitações de ajuste de ponto enviadas por funcionários para aprovação/rejeição.

- Componentes / Colunas da lista:
  - `ID solicitação` (string/int)
  - `Colaborador` (nome + matrícula)
  - `Tipo` (Correção / Criação / Exclusão)
  - `Data alvo` (date/time)
  - `Status` (Pendente / Aprovado / Rejeitado)
  - `Enviado em` (timestamp)
  - `Aprovador atual` (quem está definido para aprovar)
  - `Ações` (botões: `Visualizar`, `Aprovar`, `Rejeitar`)

- Tela de detalhe da solicitação (ao clicar `Visualizar`):
  - Campos apresentados (somente leitura): todos os campos acima + `Justificativa do funcionário`, `Anexos` (lista de uploads), `Histórico de alterações` (se houver).
  - Área `Aprovação`: `Decisão` (`Aprovar` / `Rejeitar`), `Comentário do gestor` (textarea, opcional), `Enviar` (botão).

- Validações / Regras:
  - Somente gestores com permissão podem aprovar; o backend valida permissão e retorna HTTP 403 se não autorizado.
  - Ao aprovar: cria ou altera registros de ponto na tabela principal (`registros`) com campos `data_hora`, `tipo`, `projeto`, `origem='ajuste'`, `aprovado_por=gestor_id`, `aprovado_em=timestamp`.
  - Ao rejeitar: atualiza o status da solicitação e envia notificação ao usuário solicitante.
  - Se houver anexos, o gestor pode baixar (botão) — sistema valida extensão e tamanho conforme regras de upload.

- Fluxos:
  - `Aprovar`: valida conflitos (duplicidade de Início/Fim) via `calculo_horas_system` antes de persistir; se conflito, exibir modal com detalhes e opção `Forçar Aprovação` (requisição adicional com justificativa).
  - `Rejeitar`: exige comentário de rejeição quando marcado `Exigir motivo` na configuração do gestor (opcional globalmente configurável).

-------------------------------------------------------------------------------

3) Atestados (Lista e Análise)

- Objetivo: permitir análise de atestados enviados pelos colaboradores.

- Lista / Colunas:
  - `ID`, `Colaborador`, `Período` (data/hora), `Motivo`, `Status`, `Enviado em`, `Anexos`.

- Visualização do anexo:
  - Ao clicar no anexo, abrir viewer (se imagem/pdf) em modal com opções `Baixar` e `Marcar como verificado`.

- Ações do gestor:
  - `Aprovar` / `Rejeitar` com campo `Observação` (opcional/obrigatório conforme política).
  - `Registrar ausência` (quando aprovar, opcionalmente converte em ausência automática no calendário/folha).

- Regras de negócio:
  - Ao aprovar, o sistema atualiza o registro do funcionário para refletir ausência/ajuste de horas e cria evento no log de auditoria.
  - Ao rejeitar, gera notificação push/email ao colaborador.

-------------------------------------------------------------------------------

4) Horas Extras (Lista de Aprovação e Encerramento)

- Objetivo: revisar solicitações de HE, aprovar/rejeitar e encerrar HEs abertas.

- Lista / Colunas:
  - `ID`, `Colaborador`, `Data inicio`, `Data fim` (se aplicável), `Total solicitado`, `Justificativa`, `Status`, `Enviado em`.

- Detalhe e ações:
  - `Aprovar`, `Rejeitar`, `Ajustar horas` (campo numérico), `Encerrar em nome do colaborador` (botão para encerrar HE em aberto e registrar fim no DB).

- Regras/Validações:
  - Verificar limites legais (configurável): alerta no UI se ultrapassar limites; gestor pode aprovar com override (registro de justificativa obrigatória ao fazer override).
  - Ao aprovar, ajustar o `banco_horas` ou gerar pagamento conforme configuração da empresa.

-------------------------------------------------------------------------------

5) Banco de Horas — Gestão e Ajustes

- Objetivo: permitir consulta de saldos e aplicar ajustes manuais.

- Componentes:
  - Filtro por colaborador / período
  - Tabela de lançamentos: `Data`, `Descrição`, `Crédito/Débito`, `Saldo após`.
  - Botão `Ajustar saldo` -> abre modal com campos: `Colaborador` (select), `Tipo` (Crédito/Débito), `Quantidade` (hh:mm ou decimal), `Motivo`, `Aplicar`.

- Regras:
  - Ajustes requerem justificativa e ficam auditados; opção para notificar o colaborador via push/email.

-------------------------------------------------------------------------------

6) Relatórios (Exportação)

- Objetivo: gerar relatórios detalhados por colaborador, equipe, projeto ou período.

- Campos/Opções:
  - `Tipo de Relatório` (Espelho de ponto, Banco de horas, Horas por projeto, Atestados, Correções)
  - `Formato` (`CSV`, `PDF`)
  - `Período`, `Equipe`, `Colaborador`, `Projeto` (filtros)
  - `Agrupar por` (dia/semana/mês)

- Fluxo:
  - Usuário escolhe opções e clica `Gerar Relatório` — backend processa e disponibiliza arquivo para download (link temporário).

-------------------------------------------------------------------------------

7) Mensagens / Comunicados

- Objetivo: envio de mensagens diretas e comunicados para equipes.

- Campos:
  - `Destinatários` (checkboxes: indivíduos, equipes)
  - `Assunto` (string)
  - `Mensagem` (textarea, suporta markdown básico)
  - `Anexos` (opcional)
  - `Prioridade` (Normal / Alta)

- Regras:
  - Mensagens prioritárias podem gerar push imediato; mensagens normais ficam em fila e podem ser programadas.

-------------------------------------------------------------------------------

8) Notificações / Push (Visão de Gestão)

- Objetivo: permitir ao gestor consultar e reencaminhar instruções aos colaboradores para ativação de push, e reenviar notificações manuais.

- Componentes:
  - Lista de `Assinaturas` (usuário, tópico, ativo?), `Último recebimento`.
  - Ação `Reenviar instruções` — envia email com passo a passo ou mostra QR code/URL para assinatura no app `ntfy`.
  - `Enviar notificação manual` — campos `Tópico` (ou selecionar usuário), `Título`, `Mensagem`, `Simular para` (teste em conta do gestor)

- Regras/Integrações:
  - Uso do endpoint `push_scheduler.enviar_notificacao` no backend para disparos.

-------------------------------------------------------------------------------

9) Configurações da Equipe / Aprovação

- Objetivo: definir aprovadores, regras de substituição e políticas (ex.: exigir justificativa, limites HE).

- Campos:
  - `Aprovadores por equipe` (lista de usuários com permissão)
  - `Políticas` (checkboxes / opções): `Exigir justificativa ao rejeitar`, `Permitido override de conflitos`, `Limites HE diário/semana`

- Regras:
  - Alterar aprovadores atualiza filas de trabalho e envia notificação aos novos aprovadores.

-------------------------------------------------------------------------------

10) Auditoria e Logs

- Objetivo: visualizar histórico de aprovações, rejeições, ajustes manuais com informações de usuário e timestamp.

- Campos:
  - Filtros: `Período`, `Usuário`, `Tipo de ação` (aprovacao/rejeicao/ajuste)
  - Tabela: `Data`, `Ação`, `Alvo`, `Detalhes`, `Executado por`.

- Regras:
  - Logs são imutáveis; o sistema mantém referência a `registro_id` quando aplicável.

-------------------------------------------------------------------------------

Anexos / Uploads

- Tipos aceitos: `pdf, jpg, jpeg, png, doc, docx, txt, rtf` (máx 10MB por arquivo)
- Ao baixar, o gestor recebe o arquivo enviado pelo colaborador. O backend valida e persiste metadados na tabela `uploads`.

Mensagens e Notificações produzidas por ações do gestor

- Ao aprovar uma correção: notificação push + e-mail para o solicitante com resumo e link para visualizar.
- Ao rejeitar: notificação com motivo (se fornecido) e link para re-submissão.
- Ao ajustar banco de horas: notificação opcional se selecionado.

Fluxos de erro e mensagens de UX

- Falha ao salvar no backend: exibir toast/alert com o erro retornado; manter os dados do formulário para re-tentativa.
- Conflito de registro detectado: mostrar modal com detalhes e opções `Cancelar` / `Forçar Aprovação` (esta última grava justificativa e auditoria).

Segurança e permissões

- Apenas usuários com role `gestor` ou `admin` podem acessar essas telas. O backend valida permissões em cada endpoint.
- Ações sensíveis (`Forçar Aprovação`, `Ajuste de Banco de Horas`) exigem registro de justificativa e aparecem no log de auditoria.

Notas de implementação (técnicas)

- Endpoints esperados (exemplos):
  - `GET /gestor/dashboard`
  - `GET /gestor/correcoes`
  - `POST /gestor/correcoes/{id}/decisao` (body: `{decisao: "aprovar"|"rejeitar", comentario?: string, forcar?: bool}`)
  - `POST /gestor/atestados/{id}/decisao`
  - `GET /gestor/horas-extras`
  - `POST /reports/generate`

- Eventos gerados: `correcao_aprovada`, `correcao_rejeitada`, `atestado_aprovado`, `he_aprovada`, `banco_horas_ajustado` — usados pelo mecanismo de notificações.

-------------------------------------------------------------------------------

Instruções rápidas para uso (passo-a-passo principais)

1. Para aprovar uma correção:
   - Abra `Painel do Gestor` → `Correções / Ajustes` → clique na solicitação → reveja dados e anexos → clique `Aprovar` → (opcional) escreva comentário → `Enviar`.

2. Para rejeitar um atestado:
   - Abra `Atestados` → selecione o atestado → visualize o anexo → clique `Rejeitar` → informe motivo (se exigido) → `Enviar`.

3. Para ajustar saldo do banco de horas:
   - Abra `Banco de Horas` → clique `Ajustar saldo` → preencha colaborador, tipo, quantidade e motivo → `Aplicar`.

4. Para gerar relatório:
   - Abra `Relatórios` → selecione `Espelho de Ponto` ou outro tipo → ajuste filtros → `Gerar Relatório` → aguarde processamento → `Download`.

-------------------------------------------------------------------------------

Arquivo gerado automaticamente por pedido do time. Para criar o PDF da cartilha detalhada do gestor execute:

```bash
python cartilha_gestor.py
```
