# Verificando e acionando deploys no Render

Este arquivo descreve 3 opções que você pediu: A) como abrir e checar o painel do Render; B) como obter logs básicos do deploy; C) como acionar um deploy automaticamente usando a API (script incluído em `tools/render_deploy.py`).

**A — Abrir painel e checar deploys (manual)**
- Abra https://dashboard.render.com e faça login com a conta que contém o serviço do projeto.
- Navegue até `Services` → clique no serviço correspondente ao repositório (o nome aparece igual ao que você configurou no Render).
- Na página do serviço, abra a aba `Deploys` e cheque o status do deploy mais recente e o log de build (há um link direto para o log de cada deploy).

**B — Obter logs básicos sem sair do terminal (instruções PowerShell / curl)**
- Se preferir o terminal, você pode copiar o trace do log da página do Render. O painel web é o lugar mais direto para logs completos.
- Opcional: Use a API do Render para listar deploys (requer API key). Exemplo PowerShell:

```powershell
# exportar variáveis (PowerShell)
$env:RENDER_API_KEY = "seu_token_aqui"
$env:RENDER_SERVICE_ID = "srv-xxxxxx"

# listar os últimos deploys
Invoke-RestMethod -Method Get -Uri "https://api.render.com/v1/services/$($env:RENDER_SERVICE_ID)/deploys" -Headers @{ Authorization = "Bearer $env:RENDER_API_KEY" } | ConvertTo-Json -Depth 5

# pegar detalhes do deploy mais recente (substitua deployId)
Invoke-RestMethod -Method Get -Uri "https://api.render.com/v1/services/$($env:RENDER_SERVICE_ID)/deploys/<DEPLOY_ID>" -Headers @{ Authorization = "Bearer $env:RENDER_API_KEY" } | ConvertTo-Json -Depth 5
```

Observação: os logs detalhados de build normalmente aparecem no painel web; a API dá metadados e estados do deploy.

**C — Acionar deploy via script (automático)**
- O repositório contém `tools/render_deploy.py`. Ele faz um POST para `https://api.render.com/v1/services/{serviceId}/deploys` e retorna o ID do deploy.
- Uso rápido (PowerShell):

```powershell
# Defina as variáveis de ambiente no PowerShell
$env:RENDER_API_KEY = "seu_token_aqui"
$env:RENDER_SERVICE_ID = "srv-xxxxxx"

# Rodar e aguardar conclusão
python tools/render_deploy.py --wait

# Ou passar explicitamente
python tools/render_deploy.py --service-id srv-xxxxxx --api-key <token> --wait
```

Recomendações de segurança:
- Nunca compartilhe seu `RENDER_API_KEY` em mensagens públicas.
- Se quiser que eu (o agente) acione o deploy automaticamente, forneça o token e o id do serviço por um canal seguro ou execute o script localmente.

Se quiser, eu posso:
- A) te guiar passo-a-passo para abrir o painel e copiar os logs; ou
- B) executar o script aqui (se você colar `RENDER_API_KEY` e `RENDER_SERVICE_ID` agora ou autorizar o acesso); ou
- C) apenas te entregar os comandos que você precisa rodar localmente (sem fornecer token).
