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

def instalar_supervisor():
    """Instala Supervisor se não estiver instalado"""
    print_info("Verificando instalação do Supervisor...")
    try:
        subprocess.check_output(["supervisord", "--version"])
        print_success("Supervisor já está instalado.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("Supervisor não encontrado. Tentando instalar...")
        try:
            if sys.platform.startswith("linux"):
                subprocess.check_call(["sudo", "apt-get", "update"])
                subprocess.check_call(["sudo", "apt-get", "install", "-y", "supervisor"])
                print_success("Supervisor instalado com sucesso no Linux!")
                return True
            elif sys.platform.startswith("darwin"):
                subprocess.check_call(["brew", "install", "supervisor"])
                print_success("Supervisor instalado com sucesso no macOS!")
                return True
            else:
                print_error("Sistema operacional não suportado para instalação automática do Supervisor. Por favor, instale manualmente.")
                return False
        except subprocess.CalledProcessError:
            print_error("Falha ao instalar Supervisor. Verifique sua conexão com a internet e permissões.")
            return False

def criar_config_supervisor(app_file, porta=8501):
    """Cria o arquivo de configuração do Supervisor"""
    print_info("Criando arquivo de configuração do Supervisor...")
    
    config_dir = "/etc/supervisor/conf.d" if sys.platform.startswith("linux") else os.path.join(os.getcwd(), "supervisor_conf")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "ponto-exsa.conf")

    # Caminho completo para o interpretador Python
    python_executable = sys.executable
    
    # Caminho completo para o script do Streamlit
    streamlit_script = os.path.abspath(app_file)

    config_content = f"""
[program:ponto-exsa]
command={python_executable} -m streamlit run {streamlit_script} --server.port {porta} --server.address 0.0.0.0 --server.headless true --browser.gatherUsageStats false
directory={os.getcwd()}
autostart=true
autorestart=true
stderr_logfile={os.getcwd()}/logs/ponto-exsa_stderr.log
stdout_logfile={os.getcwd()}/logs/ponto-exsa_stdout.log
user={os.getenv('USER', 'ubuntu')}
numprocs=1
process_name=%(program_name)s_%(process_num)02d
"""

    try:
        with open(config_path, "w") as f:
            f.write(config_content)
        print_success(f"Arquivo de configuração do Supervisor criado em: {config_path}")
        return True
    except Exception as e:
        print_error(f"Falha ao criar arquivo de configuração do Supervisor: {e}")
        return False

def configurar_supervisor():
    print("\n" + "=" * 80)
    print("⚙️ CONFIGURAÇÃO SUPERVISOR PARA PRODUÇÃO")
    print("=" * 80)

    print_info("Este script irá instalar e configurar o Supervisor para manter o Ponto ExSA sempre rodando em segundo plano.")
    print_warning("Recomendado para ambientes de produção em servidores Linux/macOS.")

    if not instalar_supervisor():
        print_error("Não foi possível continuar sem o Supervisor instalado. Por favor, instale-o manualmente e tente novamente.")
        input("Pressione Enter para sair...")
        return

    app_file = "app_v4_final.py" # Nome do arquivo principal do aplicativo
    if not os.path.exists(app_file):
        print_error(f"Arquivo do aplicativo '{app_file}' não encontrado. Certifique-se de estar na pasta correta.")
        input("Pressione Enter para sair...")
        return

    porta = 8501 # Porta padrão do Streamlit

    if not criar_config_supervisor(app_file, porta):
        return

    print_info("Recarregando e atualizando Supervisor...")
    try:
        if sys.platform.startswith("linux"):
            subprocess.check_call(["sudo", "supervisorctl", "reread"])
            subprocess.check_call(["sudo", "supervisorctl", "update"])
            subprocess.check_call(["sudo", "supervisorctl", "start", "ponto-exsa"])
        elif sys.platform.startswith("darwin"):
            # Para macOS, pode ser necessário iniciar o supervisord primeiro
            # ou usar 'brew services start supervisor'
            print_warning("Para macOS, pode ser necessário iniciar o supervisord manualmente ou via 'brew services start supervisor'.")
            subprocess.check_call(["supervisorctl", "reread"])
            subprocess.check_call(["supervisorctl", "update"])
            subprocess.check_call(["supervisorctl", "start", "ponto-exsa"])
        else:
            print_warning("Supervisor configurado, mas a inicialização automática pode requerer passos manuais no seu SO.")

        print_success("Ponto ExSA configurado e iniciado com Supervisor!")
        print_info(f"Você pode verificar o status com: supervisorctl status ponto-exsa")
        print_info(f"Logs de saída: {os.getcwd()}/logs/ponto-exsa_stdout.log")
        print_info(f"Logs de erro: {os.getcwd()}/logs/ponto-exsa_stderr.log")
        print_info(f"O aplicativo estará acessível em http://localhost:{porta} ou http://[SEU_IP_LOCAL]:{porta}")
    except subprocess.CalledProcessError as e:
        print_error(f"Falha ao iniciar/atualizar Supervisor: {e}")
        print_warning("Verifique se o Supervisor está rodando e se você tem permissões de sudo (se em Linux).")
    except Exception as e:
        print_error(f"Ocorreu um erro inesperado: {e}")

    input("Pressione Enter para finalizar...")

if __name__ == "__main__":
    configurar_supervisor()


