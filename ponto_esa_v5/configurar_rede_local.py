import socket
import os
import subprocess
import time

def print_info(message):
    print(f"ℹ️  {message}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def obter_ip_local():
    """Obtém o IP local da máquina"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # Conecta a um endereço externo para descobrir o IP local
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1" # Fallback para localhost

def verificar_streamlit_rodando(porta=8501):
    """Verifica se o Streamlit está rodando na porta especificada"""
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

def configurar_rede_local():
    print("\n" + "=" * 80)
    print("🌐 CONFIGURAÇÃO DE REDE LOCAL PARA PONTO ExSA")
    print("=" * 80)

    print_info("Este script irá te ajudar a configurar o Ponto ExSA para ser acessível por outros computadores na mesma rede local.")
    print_info("Certifique-se de que o Ponto ExSA já está rodando no seu computador (servidor).")
    
    ip_local = obter_ip_local()
    porta = 8501 # Porta padrão do Streamlit

    print_info(f"Seu endereço IP local é: {ip_local}")
    print_info(f"O Ponto ExSA está configurado para usar a porta: {porta}")

    if not verificar_streamlit_rodando(porta):
        print_warning("O Ponto ExSA não parece estar rodando. Por favor, inicie-o primeiro usando 'iniciar_ponto_esa_v4_final.py'.")
        input("Pressione Enter para continuar (ou Ctrl+C para sair)...")
        if not verificar_streamlit_rodando(porta):
            print_error("O Ponto ExSA ainda não está rodando. Não é possível configurar o acesso pela rede local sem ele.")
            return

    print("\n" + "--- INSTRUÇÕES PARA OUTROS COMPUTADORES NA REDE ---")
    print_success(f"Para acessar o Ponto ExSA de OUTROS COMPUTADORES na mesma rede Wi-Fi ou cabo, peça para digitarem no navegador:")
    print(f"   👉  http://{ip_local}:{porta}")
    print_info("Exemplo: se o IP for 192.168.1.100, digite http://192.168.1.100:8501")
    print_warning("Certifique-se de que o firewall do seu computador (servidor) não está bloqueando a porta 8501.")
    print_info("Se tiver problemas, procure por 'como abrir porta no firewall do Windows/Linux/macOS'.")
    print("----------------------------------------------------\n")

    input("Pressione Enter para finalizar...")

if __name__ == "__main__":
    configurar_rede_local()


