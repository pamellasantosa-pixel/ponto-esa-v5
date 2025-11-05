# 🚀 Guia de Instalação SUPER FÁCIL do Ponto ExSA v3.0

Olá! Este guia foi feito para você que quer usar o sistema Ponto ExSA, mas não entende muito de computadores. Não se preocupe, vamos juntos, passo a passo, como se estivéssemos conversando!

## 🌟 O que você vai precisar (É como ter os ingredientes para uma receita!)

Para o sistema funcionar, você só precisa de duas coisas principais no seu computador:

1.  **Um programa chamado Python**: Pense nele como o "motor" que faz o Ponto ExSA funcionar. Ele precisa estar instalado no seu computador.
2.  **Um navegador de internet**: Você já usa um! Pode ser o Google Chrome, Mozilla Firefox, Microsoft Edge ou Safari. É por ele que você vai acessar o Ponto ExSA.

### 💻 Seu Computador (Onde tudo vai acontecer)

O Ponto ExSA funciona em computadores com:

*   **Windows** (versões 10 ou 11)
*   **macOS** (computadores da Apple)
*   **Linux** (sistemas como Ubuntu)

## 🛠️ Passo 1: Instalando o Python (O "motor" do sistema)

Se você já tem o Python instalado, pode pular para o **Passo 2**. Se não tem certeza, siga estas instruções:

### Para Computadores Windows:

1.  **Abra seu navegador de internet** (Chrome, Edge, etc.).
2.  **Digite este endereço** na barra de pesquisa e aperte Enter: `https://www.python.org/downloads/`
3.  Você verá uma página com um botão grande escrito **"Download Python 3.X.X"** (o X.X.X são números que indicam a versão mais recente). Clique nesse botão para baixar o instalador.
4.  Depois que o download terminar, **clique no arquivo que você baixou** (geralmente ele aparece na parte de baixo da tela do navegador ou na pasta "Downloads"). O nome do arquivo deve ser algo como `python-3.x.x-amd64.exe`.
5.  Uma janela de instalação vai aparecer. **MUITO IMPORTANTE**: Na primeira tela, marque a caixinha que diz **"Add Python 3.x to PATH"** (adicione Python 3.x ao PATH). Isso é essencial para o sistema funcionar corretamente!
6.  Depois de marcar a caixinha, clique em **"Install Now"** (Instalar Agora).
7.  Siga as instruções na tela. Pode ser que ele peça permissão para fazer alterações no seu computador, clique em **"Sim"** ou **"Allow"**.
8.  Quando a instalação terminar, você verá uma mensagem como "Setup was successful" (Instalação concluída com sucesso). Clique em **"Close"** (Fechar).

### Para Computadores macOS (Apple):

1.  **Abra seu navegador de internet**.
2.  **Digite este endereço**: `https://www.python.org/downloads/`
3.  Baixe o instalador clicando no botão **"Download Python 3.X.X"**.
4.  Abra o arquivo `.pkg` que você baixou.
5.  Siga as instruções na tela, clicando em **"Continuar"** e **"Instalar"**. Pode ser que ele peça sua senha de usuário do Mac.
6.  Ao final, clique em **"Fechar"**.

### Para Computadores Linux (Ubuntu, por exemplo):

Seu Linux provavelmente já vem com Python. Para ter certeza, abra o **Terminal** (você pode pesquisar por "Terminal" no menu de aplicativos) e digite:

```bash
python3 --version
```

Se aparecer algo como `Python 3.x.x`, está tudo certo! Se não, ou se a versão for muito antiga, digite no Terminal:

```bash
sudo apt update
sudo apt install python3 python3-pip
```

Ele vai pedir sua senha de usuário. Digite e aperte Enter.

## 📦 Passo 2: Preparando os Arquivos do Ponto ExSA (É como arrumar os ingredientes na bancada!)

1.  Você recebeu um arquivo compactado (ZIP) chamado `PontoESA_Completo_V3_Final.zip`. **Encontre este arquivo** no seu computador (geralmente na pasta "Downloads").
2.  **Clique com o botão direito do mouse** sobre o arquivo `PontoESA_Completo_V3_Final.zip`.
3.  No menu que aparecer, escolha a opção **"Extrair tudo..."** (no Windows) ou **"Abrir"** (no macOS/Linux, que geralmente já extrai).
4.  Ele vai perguntar onde você quer extrair. Sugiro criar uma pasta na sua área de trabalho ou em "Documentos" e extrair lá. Por exemplo, uma pasta chamada `Ponto_ExSA`.
5.  Depois de extrair, você terá uma pasta com vários arquivos dentro. **Entre nesta pasta** (ela deve se chamar `ponto_esa`).

## 🚀 Passo 3: Iniciando o Ponto ExSA (É como ligar o fogão e começar a cozinhar!)

Agora que o Python está instalado e os arquivos estão prontos, vamos ligar o sistema!

1.  Dentro da pasta `ponto_esa` que você extraiu, procure por um arquivo chamado **`iniciar_ponto_esa_v3_final.py`**.
2.  **Clique DUAS VEZES** neste arquivo. Uma janela preta (chamada "Prompt de Comando" no Windows ou "Terminal" no Linux/macOS) vai aparecer.
3.  **Não feche essa janela preta!** Ela é o "motor" do sistema funcionando. Ela vai mostrar algumas mensagens de "Verificando...", "Instalando..." e "Iniciando...". Isso é normal e pode levar alguns minutos na primeira vez.
4.  Quando o sistema estiver pronto, a janela preta vai mostrar algumas linhas importantes, como estas:

    ```
    🌐 Acesso local: http://localhost:8501
    🌐 Acesso rede: http://[SEU_IP]:8501
    ```

    E também as credenciais de acesso:

    ```
    🔐 CREDENCIAIS DE ACESSO:
       👤 Funcionário: funcionario / senha_func_123
       👨‍💼 Gestor: gestor / senha_gestor_123
    ```

5.  **NOVIDADE!** O sistema agora abre o navegador automaticamente! Você verá a mensagem "🌐 Abrindo navegador automaticamente..." e o seu navegador padrão vai abrir com a tela de login do Ponto ExSA.

## 🌐 Passo 4: Acessando o Ponto ExSA (É como provar a receita!)

Se por algum motivo o navegador não abrir automaticamente, ou se você quiser acessar de outro computador:

1.  **Abra seu navegador de internet** (Chrome, Firefox, Edge, etc.).
2.  Na barra de endereço (onde você digita `google.com`), digite exatamente este endereço:

    `http://localhost:8501`

    **⚠️ IMPORTANTE**: Se o navegador mostrar uma mensagem como "Não consigo chegar à página" ou tentar acessar `http://0.0.0.0:8501/`, isso é normal! Simplesmente **apague o endereço da barra** e digite novamente `http://localhost:8501`.

3.  Aperte Enter.
4.  Pronto! A tela de login do Ponto ExSA deve aparecer. Use as credenciais que apareceram na janela preta para entrar no sistema.

## 📱 Dica Extra: Como ter o Ponto ExSA no seu Celular (Como um aplicativo!)

O Ponto ExSA pode ser usado como um aplicativo no seu celular, mesmo sem precisar instalar nada da loja de aplicativos!

1.  No seu celular, **abra o navegador de internet** (Chrome no Android, Safari no iPhone).
2.  **Digite o endereço do sistema** (o mesmo que você usou no computador, mas se for acessar de outro celular, use o `http://[SEU_IP]:8501` que apareceu na janela preta do computador onde o sistema está rodando).
3.  Depois que a página carregar:
    *   **No Android (Chrome)**: Toque nos três pontinhos (menu) no canto superior direito e procure por **"Adicionar à tela inicial"**.
    *   **No iPhone (Safari)**: Toque no ícone de compartilhamento (um quadrado com uma seta para cima) na parte de baixo da tela e procure por **"Adicionar à Tela de Início"**.
4.  Confirme a adição. Um ícone do Ponto ExSA aparecerá na tela inicial do seu celular, como se fosse um aplicativo normal!

## 🛑 Como Desligar o Ponto ExSA

Para desligar o sistema, basta ir na janela preta (Prompt de Comando/Terminal) que está aberta e **apertar as teclas `Ctrl` e `C` ao mesmo tempo**.

## ❓ Perguntas Frequentes

### "Preciso ter Python instalado em todos os computadores e celulares?"

**NÃO!** Apenas o computador onde o sistema Ponto ExSA está "ligado" (o servidor) precisa ter o Python. Todos os outros computadores e celulares acessam o sistema pelo navegador de internet, como se fosse um site normal.

### "O que é esse 'IP' que aparece na janela preta?"

O IP é como o "endereço" do seu computador na rede. Se você quiser que outras pessoas na mesma rede (por exemplo, na mesma sala ou escritório) acessem o Ponto ExSA, elas podem usar o endereço `http://[SEU_IP]:8501` no navegador delas. O `[SEU_IP]` será um número que aparecerá na sua janela preta, como `192.168.1.100`.

### "O sistema funciona sem internet?"

**SIM!** Depois de carregar a primeira vez, o Ponto ExSA pode ser usado offline. Ele guarda os registros no seu computador e, quando a internet volta, ele envia tudo automaticamente para o sistema principal. Você será avisado quando isso acontecer.

### "Posso usar o sistema em qualquer lugar, fora da minha rede?"

**SIM!** Para isso, o computador onde o Ponto ExSA está rodando precisa estar configurado para ser acessível pela internet. Isso geralmente envolve configurações de rede mais avançadas (como abrir portas no roteador ou usar um serviço de nuvem), mas o sistema já está preparado para isso. No guia de instalação mais técnico (`INSTALACAO_V3_FINAL.md`), há mais detalhes sobre como fazer isso.

---

**Ponto ExSA v3.0** - Sistema de ponto exclusivo da empresa Expressão Socioambiental Pesquisa e Projetos
*feito por Pâmella SAR*




## 🚀 **PARTE 3: ACESSANDO O PONTO ExSA DE OUTROS LUGARES (CONFIGURAÇÕES AVANÇADAS)**

Agora que você já sabe como instalar e iniciar o Ponto ExSA no seu computador, vamos ver como fazer para que outras pessoas (ou você mesmo, de outro lugar) possam usar o sistema.

Para facilitar, criei um script especial que faz a maior parte do trabalho para você! Ele se chama `configurar_servidor_completo.py`.

### **Passo a Passo para Usar o `configurar_servidor_completo.py`:**

1.  **Certifique-se de que o Ponto ExSA NÃO está rodando.** Se ele estiver aberto no seu navegador ou se a "janela preta" do `iniciar_ponto_esa_v4_final.py` estiver aberta, feche-a primeiro (pressione `Ctrl+C` na janela preta e depois `Enter`).
2.  **Abra a pasta `ponto_esa`** onde você extraiu os arquivos.
3.  **Clique DUAS VEZES** no arquivo **`configurar_servidor_completo.py`**.
4.  Uma nova "janela preta" vai aparecer com um menu de opções. Escolha a que melhor se encaixa na sua necessidade:

#### **Opção 1: 🌐 Configurar Acesso em Rede Local (para outros PCs na mesma rede)**

*   **Quando usar**: Se você quer que outras pessoas na mesma rede Wi-Fi ou cabo (por exemplo, no mesmo escritório ou casa) possam acessar o Ponto ExSA que está rodando no seu computador.
*   **Como funciona**: Este script vai te mostrar o "endereço" (IP) do seu computador na rede local. Outras pessoas usarão esse endereço para acessar o sistema.
*   **Passos**:
    1.  Na janela do `configurar_servidor_completo.py`, digite `1` e pressione `Enter`.
    2.  O script vai te guiar e mostrar o IP do seu computador. Anote-o.
    3.  Ele vai te pedir para iniciar o Ponto ExSA (usando o `iniciar_ponto_esa_v4_final.py`). Faça isso em outra janela.
    4.  Depois que o Ponto ExSA estiver rodando, as outras pessoas podem digitar `http://[SEU_IP_AQUI]:8501` no navegador delas para acessar.
    5.  **Importante**: O seu computador precisa estar ligado e com o Ponto ExSA rodando para que os outros acessem.

#### **Opção 2: 🌍 Configurar Acesso Externo Temporário (ngrok - para acessar de qualquer lugar, temporariamente)**

*   **Quando usar**: Se você precisa que alguém de fora da sua rede (por exemplo, um colega em outra cidade, ou para uma demonstração rápida) acesse o Ponto ExSA no seu computador. Este acesso é temporário.
*   **Como funciona**: Este script instala e configura uma ferramenta chamada `ngrok`. O `ngrok` cria um "túnel" seguro do seu computador para a internet, gerando um link que qualquer pessoa pode usar.
*   **Passos**:
    1.  Na janela do `configurar_servidor_completo.py`, digite `2` e pressione `Enter`.
    2.  O script tentará instalar o `ngrok` (pode pedir sua senha se for Linux/macOS). Se não conseguir, ele te dará instruções para instalar manualmente.
    3.  Ele vai te pedir para iniciar o Ponto ExSA (usando o `iniciar_ponto_esa_v4_final.py`). Faça isso em outra janela.
    4.  Depois que o Ponto ExSA estiver rodando, o script do `ngrok` vai gerar um link (URL) que começa com `https://...`. Este é o link que você pode compartilhar.
    5.  **Importante**: Este link muda toda vez que você inicia o `ngrok` (a menos que você tenha uma conta paga). O seu computador precisa estar ligado e com o Ponto ExSA E o `ngrok` rodando para que o acesso funcione.

#### **Opção 3: ⚙️ Configurar para Produção com PM2 (manter o app sempre rodando - requer Node.js)**

*   **Quando usar**: Se você quer que o Ponto ExSA rode 24 horas por dia, 7 dias por semana, de forma confiável, em um computador que ficará sempre ligado (um "servidor"). O PM2 é um "gerenciador de processos" que garante que o aplicativo reinicie automaticamente se algo der errado.
*   **Como funciona**: Este script instala o PM2 (que precisa do Node.js, um programa que o script vai verificar) e configura o Ponto ExSA para ser gerenciado por ele.
*   **Passos**:
    1.  Na janela do `configurar_servidor_completo.py`, digite `3` e pressione `Enter`.
    2.  O script vai verificar e tentar instalar o Node.js e o PM2. Siga as instruções.
    3.  Ele vai configurar o Ponto ExSA para iniciar automaticamente com o PM2.
    4.  **Importante**: Após configurar, o Ponto ExSA estará sempre rodando em segundo plano. Você pode acessar localmente (`http://localhost:8501`) ou pela rede local (`http://[SEU_IP_AQUI]:8501`).

#### **Opção 4: 🛠️ Configurar para Produção com Supervisor (manter o app sempre rodando - para Linux/macOS)**

*   **Quando usar**: É uma alternativa ao PM2, com a mesma finalidade: manter o Ponto ExSA sempre rodando em segundo plano em um servidor, reiniciando automaticamente em caso de falha. Mais comum em sistemas Linux/macOS.
*   **Como funciona**: Este script instala o Supervisor e o configura para gerenciar o Ponto ExSA.
*   **Passos**:
    1.  Na janela do `configurar_servidor_completo.py`, digite `4` e pressione `Enter`.
    2.  O script vai verificar e tentar instalar o Supervisor. Siga as instruções (pode pedir sua senha).
    3.  Ele vai configurar o Ponto ExSA para iniciar automaticamente com o Supervisor.
    4.  **Importante**: Assim como o PM2, o Ponto ExSA estará sempre rodando em segundo plano. Você pode acessar localmente (`http://localhost:8501`) ou pela rede local (`http://[SEU_IP_AQUI]:8501`).

### **Posso usar o sistema em qualquer lugar, fora da minha rede?**

**SIM!** Para isso, o computador onde o Ponto ExSA está rodando precisa estar configurado para ser acessível pela internet. As opções 2, 3 e 4 acima te ajudam com isso:

*   **Opção 2 (ngrok)**: Ideal para acesso temporário e rápido de qualquer lugar.
*   **Opção 3 (PM2) ou 4 (Supervisor)**: Se você configurar o Ponto ExSA em um servidor na internet (um "VPS" ou "Cloud"), usando PM2 ou Supervisor, ele estará acessível de qualquer lugar do mundo, 24h por dia. Isso requer um pouco mais de conhecimento técnico para configurar o servidor na nuvem, mas é a forma mais profissional de ter o sistema online permanentemente.

### **Todos os computadores e celular têm que ter o Python instalado?**

**NÃO!** Apenas o computador onde o Ponto ExSA está **rodando** (o "servidor") precisa ter o Python instalado. Os outros computadores e celulares que vão **acessar** o sistema só precisam de um navegador de internet (Chrome, Firefox, Edge, Safari, etc.).

Para o celular, você pode "instalar" o Ponto ExSA como um aplicativo PWA (Progressive Web App), que funciona como um app normal, mas é acessado pelo navegador. As instruções para isso estão na **PARTE 2** deste guia.

### **Recomendações para usar o Ponto ExSA na Web e como PWA:**

*   **Para o "Servidor" (computador onde o Ponto ExSA roda):**
    *   Use um computador estável e que possa ficar ligado.
    *   Se for para uso contínuo, use as opções 3 (PM2) ou 4 (Supervisor) para garantir que o sistema esteja sempre ativo.
    *   Para acesso externo permanente, considere um servidor na nuvem (VPS/Cloud).

*   **Para os "Clientes" (computadores e celulares que acessam):**
    *   Use um navegador moderno e atualizado.
    *   No celular, instale como PWA para uma experiência de aplicativo nativo.
    *   Certifique-se de que o dispositivo tem acesso à rede onde o Ponto ExSA está rodando (seja local ou internet).




