import os
import sys
import subprocess

def print_header():
    print("\n" + "=" * 80)
    print("🚀 PONTO ExSA - FERRAMENTA DE CONFIGURAÇÃO DE SERVIDOR")
    print("=" * 80)

def print_info(message):
    print(f"ℹ️  {message}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_warning(message):
    print(f"⚠️  {message}")

def run_script(script_name):
    """Executa um script Python"""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    if not os.path.exists(script_path):
        print_error(f"Script [1m{script_name}[0m não encontrado em {script_path}")
        return
    
    print_info(f"Executando [1m{script_name}[0m...")
    try:
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError:
        print_error(f"Falha ao executar [1m{script_name}[0m.")
    except Exception as e:
        print_error(f"Erro inesperado ao executar [1m{script_name}[0m: {e}")

def main():
    print_header()
    
    while True:
        print("\nEscolha uma opção de configuração:")
        print("1. 🌐 Configurar Acesso em Rede Local (para outros PCs na mesma rede)")
        print("2. 🌍 Configurar Acesso Externo Temporário (ngrok - para acessar de qualquer lugar, temporariamente)")
        print("3. ⚙️ Configurar para Produção com PM2 (manter o app sempre rodando - requer Node.js)")
        print("4. 🛠️ Configurar para Produção com Supervisor (manter o app sempre rodando - para Linux/macOS)")
        print("0. Sair")
        
        escolha = input("Digite o número da sua escolha: ")
        
        if escolha == "1":
            run_script("configurar_rede_local.py")
        elif escolha == "2":
            run_script("configurar_ngrok.py")
        elif escolha == "3":
            run_script("configurar_pm2.py")
        elif escolha == "4":
            run_script("configurar_supervisor.py")
        elif escolha == "0":
            print_info("Saindo da ferramenta de configuração. Até mais!")
            break
        else:
            print_warning("Opção inválida. Por favor, digite um número de 0 a 4.")
            
        input("Pressione Enter para continuar...")

if __name__ == "__main__":
    main()


