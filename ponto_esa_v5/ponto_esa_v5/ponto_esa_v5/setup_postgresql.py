"""
Script completo de configuração do PostgreSQL para Ponto ExSA v5.0
Executa todos os passos necessários automaticamente
"""

import subprocess
import time
import os
import sys

def print_header(mensagem):
    print("\n" + "="*60)
    print(f"  {mensagem}")
    print("="*60 + "\n")

def executar_comando(comando, descricao):
    print(f"🔧 {descricao}...")
    try:
        result = subprocess.run(comando, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {descricao} - Concluído")
            return True
        else:
            print(f"❌ {descricao} - Erro: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {descricao} - Erro: {e}")
        return False

def main():
    print_header("Instalação e Configuração do PostgreSQL")
    
    # 1. Verificar se PostgreSQL já está instalado
    print("🔍 Verificando se PostgreSQL está instalado...")
    result = subprocess.run("psql --version", shell=True, capture_output=True)
    if result.returncode == 0:
        print("✅ PostgreSQL já está instalado!")
        versao = result.stdout.decode().strip()
        print(f"   Versão: {versao}")
    else:
        print("⚠️  PostgreSQL não encontrado. Instalando...")
        
        # 2. Instalar PostgreSQL
        if not executar_comando(
            "winget install -e --id PostgreSQL.PostgreSQL.16 --accept-source-agreements --accept-package-agreements",
            "Instalando PostgreSQL 16"
        ):
            print("\n❌ Falha na instalação do PostgreSQL")
            print("💡 Instale manualmente de: https://www.postgresql.org/download/windows/")
            return False
        
        print("\n⏳ Aguardando instalação do PostgreSQL (30 segundos)...")
        time.sleep(30)
        
        # Adicionar PostgreSQL ao PATH
        print("\n📝 Adicionando PostgreSQL ao PATH do sistema...")
        pg_path = "C:\\Program Files\\PostgreSQL\\16\\bin"
        if os.path.exists(pg_path):
            os.environ["PATH"] += f";{pg_path}"
            print(f"✅ PATH atualizado: {pg_path}")
        else:
            print(f"⚠️  Diretório não encontrado: {pg_path}")
            print("   Reinicie o terminal para que o PATH seja atualizado")
    
    # 3. Configurar arquivo .env
    print_header("Configurando arquivo .env")
    
    senha_postgres = input("Digite a senha do usuário 'postgres' (padrão: postgres): ").strip()
    if not senha_postgres:
        senha_postgres = "postgres"
    
    env_content = f"""# Configuração do Banco de Dados - Ponto ExSA v5.0
USE_POSTGRESQL=true
DB_HOST=localhost
DB_NAME=ponto_esa
DB_USER=postgres
DB_PASSWORD={senha_postgres}
DB_PORT=5432
"""
    
    with open('.env', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ Arquivo .env criado com sucesso!")
    
    # 4. Criar banco de dados
    print_header("Criando banco de dados PostgreSQL")
    
    print("📝 Executando: CREATE DATABASE ponto_esa;")
    comando_create_db = f'psql -U postgres -c "CREATE DATABASE ponto_esa;" 2>nul || echo Banco pode já existir'
    
    os.environ['PGPASSWORD'] = senha_postgres
    result = subprocess.run(comando_create_db, shell=True, capture_output=True, text=True)
    
    if "CREATE DATABASE" in result.stdout or "Banco pode já existir" in result.stdout:
        print("✅ Banco de dados 'ponto_esa' criado (ou já existe)")
    else:
        print(f"⚠️  Resultado: {result.stdout}")
        print(f"⚠️  Erro: {result.stderr}")
    
    # 5. Inicializar estrutura do banco
    print_header("Inicializando estrutura do banco de dados")
    
    if executar_comando(
        "python database_postgresql.py",
        "Criando tabelas e dados iniciais"
    ):
        print("✅ Banco de dados inicializado com sucesso!")
    else:
        print("❌ Erro ao inicializar banco. Execute manualmente:")
        print("   python database_postgresql.py")
    
    # 6. Verificar conexão
    print_header("Verificando conexão")
    
    if executar_comando(
        'python -c "from database import get_connection; conn = get_connection(); print(\'Conexão OK\'); conn.close()"',
        "Testando conexão com PostgreSQL"
    ):
        print("✅ Sistema conectado ao PostgreSQL com sucesso!")
    else:
        print("❌ Erro na conexão. Verifique as configurações no arquivo .env")
    
    # 7. Instruções finais
    print_header("Configuração Concluída!")
    
    print("""
🎉 PostgreSQL configurado com sucesso!

📋 Próximos passos:

1️⃣  Para executar a aplicação:
   streamlit run app_v5_final.py

2️⃣  Para migrar dados do SQLite (opcional):
   python tools/migrate_sqlite_to_postgresql.py

3️⃣  Para voltar ao SQLite, edite .env:
   USE_POSTGRESQL=false

💡 Credenciais de acesso ao sistema:
   Funcionário: funcionario / senha_func_123
   Gestor: gestor / senha_gestor_123

📖 Consulte MIGRAÇÃO_POSTGRESQL.md para mais informações
""")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Configuração cancelada pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
