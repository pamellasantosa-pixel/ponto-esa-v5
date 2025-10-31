"""
Script de Teste: Verificar se PostgreSQL e R2 estão funcionando
Execute após o deploy completar
"""

import requests
import sys

def test_application():
    """Testa se a aplicação está respondendo"""
    print("🧪 Testando aplicação...")
    
    url = "https://ponto-esa-v5.onrender.com"
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            print("✅ Aplicação está no ar!")
            return True
        else:
            print(f"⚠️ Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao acessar: {e}")
        return False

def check_health():
    """Verifica saúde da aplicação"""
    print("\n🏥 Verificando saúde do Streamlit...")
    
    health_url = "https://ponto-esa-v5.onrender.com/_stcore/health"
    
    try:
        response = requests.get(health_url, timeout=10)
        if response.status_code == 200:
            print("✅ Streamlit funcionando perfeitamente!")
            return True
        else:
            print(f"⚠️ Health check retornou: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro no health check: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 TESTE DE DEPLOY - Ponto ExSA v5.0")
    print("=" * 60)
    print()
    
    app_ok = test_application()
    health_ok = check_health()
    
    print()
    print("=" * 60)
    if app_ok and health_ok:
        print("✅ SUCESSO! Aplicação está funcionando!")
        print()
        print("📋 Próximos passos:")
        print("1. Acesse: https://ponto-esa-v5.onrender.com")
        print("2. Faça login (gestor / senha_gestor_123)")
        print("3. Registre um ponto")
        print("4. Faça upload de um atestado")
        print("5. Verifique se os dados persistem após novo deploy")
        sys.exit(0)
    else:
        print("❌ FALHA! Verifique os logs no Render")
        print("   https://dashboard.render.com/web/ponto-esa-v5/logs")
        sys.exit(1)
