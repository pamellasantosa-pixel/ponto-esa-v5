import os
import subprocess
import time
import sys

def print_info(message):
    print(f"ℹ️  {message}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def verificar_streamlit_rodando(porta=8501):
    """Verifica se o Streamlit está rodando na porta especificada"""
    import socket
    print_info(f"Verificando se o Ponto ExSA está rodando na porta {porta}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(1) # Timeout de 1 segundo
        result = sock.connect_ex(("127.0.0.1", porta))
        if result == 0:
            print_success(f"Ponto ExSA detectado e rodando na porta {porta}!")
            return True
        else:
            print_warning(f"Ponto ExSA NÃO detectado na porta {porta}. Certifique-se de que o aplicativo está iniciado.")
            return False
    except Exception:
        print_warning(f"Não foi possível verificar a porta {porta}.")
        return False
    finally:
        sock.close()

def instalar_ngrok():
    """Instala o ngrok se não estiver instalado"""
    print_info("Verificando instalação do ngrok...")
    try:
        subprocess.check_output(["ngrok", "version"])
        print_success("ngrok já está instalado.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_warning("ngrok não encontrado. Tentando instalar...")
        
        if sys.platform.startswith('win'):
            print_info("Para Windows, por favor, baixe o ngrok de https://ngrok.com/download e adicione-o ao PATH do sistema.")
            print_info("Ou instale via Chocolatey (se tiver): choco install ngrok")
            return False
        elif sys.platform.startswith('linux'):
            try:
                subprocess.check_call(["sudo", "snap", "install", "ngrok"])
                print_success("ngrok instalado via Snap.")
                return True
            except subprocess.CalledProcessError:
                print_warning("Falha ao instalar ngrok via Snap. Tentando via apt...")
                try:
                    subprocess.check_call(["sudo", "apt", "update"])
                    subprocess.check_call(["sudo", "apt", "install", "-y", "ngrok"])
                    print_success("ngrok instalado via apt.")
                    return True
                except subprocess.CalledProcessError:
                    print_error("Falha ao instalar ngrok no Linux. Por favor, instale manualmente.")
                    return False
        elif sys.platform == 'darwin': # macOS
            try:
                subprocess.check_call(["brew", "install", "ngrok"])
                print_success("ngrok instalado via Homebrew.")
                return True
            except subprocess.CalledProcessError:
                print_error("Falha ao instalar ngrok no macOS. Por favor, instale manualmente.")
                return False
        else:
            print_error("Sistema operacional não suportado para instalação automática do ngrok. Por favor, instale manualmente.")
            return False

def configurar_ngrok():
    print("\n" + "=" * 80)
    print("🌍 CONFIGURAÇÃO NGROK PARA ACESSO EXTERNO TEMPORÁRIO")
    print("=" * 80)

    print_info("Este script irá configurar um túnel ngrok para que seu Ponto ExSA possa ser acessado de qualquer lugar na internet.")
    print_warning("Este acesso é TEMPORÁRIO e a URL muda a cada vez que o ngrok é iniciado (a menos que você tenha uma conta paga).")
    print_info("Certifique-se de que o Ponto ExSA já está rodando no seu computador (servidor).")

    if not instalar_ngrok():
        print_error("Não foi possível continuar sem o ngrok instalado. Por favor, instale-o manualmente e tente novamente.")
        input("Pressione Enter para sair...")
        return

    porta = 8501 # Porta padrão do Streamlit

    if not verificar_streamlit_rodando(porta):
        print_warning("O Ponto ExSA não parece estar rodando. Por favor, inicie-o primeiro usando 'iniciar_ponto_esa_v4_final.py'.")
        input("Pressione Enter para continuar (ou Ctrl+C para sair)...")
        if not verificar_streamlit_rodando(porta):
            print_error("O Ponto ExSA ainda não está rodando. Não é possível configurar o ngrok sem ele.")
            return

    print_info(f"Iniciando túnel ngrok para a porta {porta}...")
    print_warning("O ngrok pode pedir para você autenticar sua conta. Siga as instruções no terminal do ngrok.")
    print_info("Para parar o ngrok, pressione Ctrl+C no terminal onde ele está rodando.")

    try:
        # Iniciar ngrok em um novo processo para não bloquear este script
        # O ngrok imprime a URL no stderr ou stdout, dependendo da versão/config
        process = subprocess.Popen(["ngrok", "http", str(porta)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print_info("Aguardando o ngrok gerar a URL pública... Isso pode levar alguns segundos.")
        url_publica = None
        start_time = time.time()
        
        while time.time() - start_time < 30: # Espera até 30 segundos
            output = process.stderr.readline() # ngrok geralmente imprime no stderr
            if "Forwarding" in output:
                # Exemplo: Forwarding                    https://xxxx-xx-xx-xx.ngrok-free.app -> http://localhost:8501
                parts = output.split(" ")
                for part in parts:
                    if part.startswith("https://"):
                        url_publica = part
                        break
                if url_publica:
                    break
            output = process.stdout.readline() # Caso imprima no stdout
            if "Forwarding" in output:
                parts = output.split(" ")
                for part in parts:
                    if part.startswith("https://"):
                        url_publica = part
                        break
                if url_publica:
                    break
            time.sleep(1)

        if url_publica:
            print("\n" + "🌐" * 40)
            print_success(f"Túnel ngrok criado com sucesso!")
            print_success(f"Sua URL pública para acesso externo é: {url_publica}")
            print("🌐" * 40)
            print_warning("Compartilhe esta URL com quem precisa acessar o Ponto ExSA de fora da sua rede.")
            print_warning("Lembre-se: esta URL é temporária e só funciona enquanto o ngrok estiver rodando.")
        else:
            print_error("Não foi possível obter a URL pública do ngrok. Verifique o terminal do ngrok para erros.")
            print_info("Pode ser necessário autenticar o ngrok com um token. Veja em https://dashboard.ngrok.com/get-started/your-authtoken")
            
        print_info("O ngrok continuará rodando em segundo plano. Para pará-lo, pressione Ctrl+C no terminal onde ele foi iniciado.")
        input("Pressione Enter para finalizar este script (o ngrok continuará rodando)...")

    except FileNotFoundError:
        print_error("Comando 'ngrok' não encontrado. Certifique-se de que o ngrok está instalado e no PATH.")
    except Exception as e:
        print_error(f"Ocorreu um erro ao iniciar o ngrok: {e}")
    finally:
        # Não matar o processo ngrok aqui, pois ele deve continuar rodando
        pass

if __name__ == "__main__":
    configurar_ngrok()


