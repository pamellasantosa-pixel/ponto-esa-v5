import os
import subprocess
import sys
import time

def print_info(message):
    print(f"ℹ️  {message}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def verificar_node_npm():
    """Verifica se Node.js e npm estão instalados"""
    print_info("Verificando instalação do Node.js e npm...")
    try:
        subprocess.check_output(["node", "-v"])
        subprocess.check_output(["npm", "-v"])
        print_success("Node.js e npm estão instalados.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Node.js ou npm não encontrados. PM2 requer Node.js.")
        print_info("Por favor, instale Node.js (que inclui npm) de https://nodejs.org/pt-br/download/")
        return False

def instalar_pm2():
    """Instala PM2 globalmente se não estiver instalado"""
    print_info("Verificando instalação do PM2...")
    try:
        subprocess.check_output(["pm2", "-v"])
        print_success("PM2 já está instalado.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("PM2 não encontrado. Tentando instalar globalmente via npm...")
        try:
            subprocess.check_call(["npm", "install", "-g", "pm2"])
            print_success("PM2 instalado com sucesso!")
            return True
        except subprocess.CalledProcessError:
            print_error("Falha ao instalar PM2. Verifique sua conexão com a internet e permissões.")
            return False

def criar_config_pm2(app_file, porta=8501):
    """Cria o arquivo ecosystem.config.js para PM2"""
    print_info("Criando arquivo de configuração ecosystem.config.js para PM2...")
    config_content = f"""
module.exports = {{
  apps : [{{
    name   : "ponto-exsa",
    script : "streamlit",
    args   : "run {app_file} --server.port {porta} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false",
    interpreter: "{sys.executable}",
    cwd    : "{os.getcwd()}",
    exec_mode: "cluster",
    instances: "max",
    autorestart: true,
    watch: false,
    max_memory_restart: "1G",
    env: {{
      NODE_ENV: "production"
    }}
  }}]
}};
"""

    try:
        with open("ecosystem.config.js", "w") as f:
            f.write(config_content)
        print_success("Arquivo ecosystem.config.js criado com sucesso!")
        return True
    except Exception as e:
        print_error(f"Falha ao criar arquivo de configuração do PM2: {e}")
        return False

def configurar_pm2():
    print("\n" + "=" * 80)
    print("⚙️ CONFIGURAÇÃO PM2 PARA PRODUÇÃO")
    print("=" * 80)

    print_info("Este script irá instalar e configurar o PM2 para manter o Ponto ExSA sempre rodando em segundo plano.")
    print_warning("Recomendado para ambientes de produção. Requer Node.js e npm.")

    if not verificar_node_npm():
        print_error("Não foi possível continuar sem Node.js e npm. Por favor, instale-os e tente novamente.")
        input("Pressione Enter para sair...")
        return

    if not instalar_pm2():
        print_error("Não foi possível continuar sem o PM2 instalado. Por favor, instale-o manualmente e tente novamente.")
        input("Pressione Enter para sair...")
        return

    app_file = "app_v4_final.py" # Nome do arquivo principal do aplicativo
    if not os.path.exists(app_file):
        print_error(f"Arquivo do aplicativo \'{app_file}\' não encontrado. Certifique-se de estar na pasta correta.")
        input("Pressione Enter para sair...")
        return

    porta = 8501 # Porta padrão do Streamlit

    if not criar_config_pm2(app_file, porta):
        return

    print_info("Iniciando Ponto ExSA com PM2...")
    try:
        subprocess.check_call(["pm2", "start", "ecosystem.config.js"])
        subprocess.check_call(["pm2", "save"])
        print_success("Ponto ExSA configurado e iniciado com PM2!")
        print_info(f"Você pode verificar o status com: pm2 status")
        print_info(f"Para parar: pm2 stop ponto-exsa")
        print_info(f"Para reiniciar: pm2 restart ponto-exsa")
        print_info(f"O aplicativo estará acessível em http://localhost:{porta} ou http://[SEU_IP_LOCAL]:{porta}")
    except subprocess.CalledProcessError as e:
        print_error(f"Falha ao iniciar/configurar PM2: {e}")
        print_warning("Verifique se o PM2 está rodando e se você tem permissões.")
    except Exception as e:
        print_error(f"Ocorreu um erro inesperado: {e}")

    input("Pressione Enter para finalizar...")

if __name__ == "__main__":
    configurar_pm2()

