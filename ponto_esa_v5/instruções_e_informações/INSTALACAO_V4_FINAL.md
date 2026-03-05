# Guia de Instalação - Ponto ExSA v4.0

## 🚀 Instalação Rápida (Recomendada)

### Passo 1: Baixar e Extrair
1. Baixe o arquivo `PontoESA_Completo_V4_Final.zip`
2. Extraia para uma pasta de sua escolha
3. Abra a pasta extraída

### Passo 2: Executar o Instalador
1. **Clique DUAS VEZES** no arquivo `iniciar_ponto_esa_v4_final.py`
2. Uma janela preta (terminal) abrirá
3. O sistema verificará e instalará automaticamente:
   - Python (se necessário)
   - Todas as dependências
   - Configurações iniciais
4. O navegador abrirá automaticamente quando pronto

### Passo 3: Primeiro Acesso
- **URL**: `http://localhost:8501`
- **Funcionário**: `funcionario` / `senha_func_123`
- **Gestor**: `gestor` / `senha_gestor_123`

---

## 🔧 Instalação Manual

### Requisitos
- Python 3.8 ou superior
- Conexão com internet (para instalação)

### Passo a Passo
1. **Instalar Python**:
   - Windows: Baixe de python.org
   - Linux: `sudo apt install python3 python3-pip`
   - macOS: `brew install python3`

2. **Instalar Dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Executar o Sistema**:
   ```bash
   streamlit run app_v4_final.py
   ```

4. **Acessar**:
   - Abra o navegador
   - Vá para `http://localhost:8501`

---

## 📱 Instalação Mobile (PWA)

### Android/iOS
1. Acesse o sistema pelo navegador do celular
2. Toque no menu do navegador (⋮)
3. Selecione "Adicionar à tela inicial"
4. Confirme a instalação
5. Use o ícone criado na tela inicial

---

## 🌐 Configuração para Múltiplos Usuários

### Rede Local
1. Execute o sistema normalmente
2. Descubra o IP do computador servidor:
   - Windows: `ipconfig`
   - Linux/Mac: `ifconfig`
3. Outros computadores acessam: `http://[IP]:8501`

### Exemplo
- IP do servidor: 192.168.1.100
- Outros acessam: `http://192.168.1.100:8501`

---

## 🔧 Configuração para Produção

### Usando PM2 (Recomendado)
1. Instalar PM2:
   ```bash
   npm install -g pm2
   ```

2. Criar arquivo de configuração `ecosystem.config.js`:
   ```javascript
   module.exports = {
     apps: [{
       name: 'ponto-exsa',
       script: 'streamlit',
       args: 'run app_v4_final.py --server.port 8501 --server.address 0.0.0.0',
       cwd: '/caminho/para/ponto_esa',
       instances: 1,
       autorestart: true,
       watch: false,
       max_memory_restart: '1G'
     }]
   }
   ```

3. Iniciar:
   ```bash
   pm2 start ecosystem.config.js
   pm2 save
   pm2 startup
   ```

### Usando Supervisor
1. Instalar supervisor:
   ```bash
   sudo apt install supervisor
   ```

2. Criar arquivo `/etc/supervisor/conf.d/ponto-exsa.conf`:
   ```ini
   [program:ponto-exsa]
   command=streamlit run app_v4_final.py --server.port 8501 --server.address 0.0.0.0
   directory=/caminho/para/ponto_esa
   user=ubuntu
   autostart=true
   autorestart=true
   redirect_stderr=true
   stdout_logfile=/var/log/ponto-exsa.log
   ```

3. Iniciar:
   ```bash
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start ponto-exsa
   ```

---

## 🔒 Configurações de Segurança

### Firewall
```bash
# Ubuntu/Debian
sudo ufw allow 8501

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload
```

### HTTPS (Opcional)
Para usar HTTPS, configure um proxy reverso com nginx:

```nginx
server {
    listen 443 ssl;
    server_name seu-dominio.com;
    
    ssl_certificate /caminho/para/certificado.crt;
    ssl_certificate_key /caminho/para/chave.key;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 📊 Backup e Manutenção

### Backup Automático
O sistema faz backup automático do banco de dados em:
- `database/backups/`
- Frequência: Diária
- Retenção: 30 dias

### Backup Manual
```bash
cp database/ponto_esa.db database/backup_$(date +%Y%m%d).db
```

### Limpeza de Logs
```bash
# Limpar logs antigos (mais de 30 dias)
find logs/ -name "*.log" -mtime +30 -delete
```

---

## 🆘 Solução de Problemas

### Erro: "Porta 8501 já está em uso"
```bash
# Encontrar processo usando a porta
lsof -i :8501

# Parar processo
kill -9 [PID]

# Ou usar porta diferente
streamlit run app_v4_final.py --server.port 8502
```

### Erro: "Módulo não encontrado"
```bash
# Reinstalar dependências
pip install -r requirements.txt --force-reinstall
```

### Erro: "Banco de dados corrompido"
1. Pare o sistema
2. Restaure backup: `cp database/backups/[backup_mais_recente] database/ponto_esa.db`
3. Reinicie o sistema

### Performance Lenta
1. Verifique recursos do sistema:
   ```bash
   htop
   df -h
   ```
2. Limpe arquivos temporários:
   ```bash
   rm -rf __pycache__/
   rm -rf .streamlit/
   ```

---

## 📞 Suporte Técnico

### Logs do Sistema
- Localização: `logs/`
- Arquivo principal: `ponto_esa.log`
- Rotação: Diária

### Informações Úteis
- Versão do Python: `python --version`
- Versão do Streamlit: `streamlit version`
- Status do sistema: Acesse menu "Sistema" no painel do gestor

### Contato
Para suporte técnico, forneça:
1. Versão do sistema operacional
2. Versão do Python
3. Logs de erro
4. Descrição detalhada do problema

---

**Desenvolvido por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos**

