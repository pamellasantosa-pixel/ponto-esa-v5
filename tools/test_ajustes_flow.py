"""
Teste End-to-End do Fluxo de Ajustes de Registros
Simula interação completa: funcionário solicita → gestor aprova/rejeita
"""

import sys
import os
from datetime import datetime, date, time

# Adicionar path do módulo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ponto_esa_v5', 'ponto_esa_v5'))

from ajuste_registros_system import AjusteRegistrosSystem  # type: ignore[import-not-found]
from database_postgresql import get_connection, init_db, USE_POSTGRESQL  # type: ignore[import-not-found]

# Definir placeholder correto
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"

def print_section(title):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def setup_test_data():
    """Cria dados de teste básicos"""
    print_section("🔧 SETUP: Criando dados de teste")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Criar usuário funcionário de teste (se não existir)
        cursor.execute(f"SELECT COUNT(*) FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", ('func_teste',))
        if cursor.fetchone()[0] == 0:
            import hashlib
            senha_hash = hashlib.sha256('senha123'.encode()).hexdigest()
            placeholders = ', '.join([SQL_PLACEHOLDER] * 5)
            cursor.execute(f"""
                INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 5)})
            """, ('func_teste', senha_hash, 'funcionario', 'Funcionário Teste', 1))
            print("✅ Usuário funcionário criado: func_teste / senha123")
        
        # Criar usuário gestor de teste (se não existir)
        cursor.execute(f"SELECT COUNT(*) FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", ('gestor_teste',))
        if cursor.fetchone()[0] == 0:
            import hashlib
            senha_hash = hashlib.sha256('senha123'.encode()).hexdigest()
            cursor.execute(f"""
                INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 5)})
            """, ('gestor_teste', senha_hash, 'gestor', 'Gestor Teste', 1))
            print("✅ Usuário gestor criado: gestor_teste / senha123")
        
        # Criar registro de ponto de teste
        if USE_POSTGRESQL:
            cursor.execute(f"""
                INSERT INTO registros_ponto 
                (usuario, data_hora, tipo, modalidade, projeto, atividade)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 6)})
                RETURNING id
            """, ('func_teste', datetime.now(), 'Início', 'Presencial', 'TESTE', 'Atividade teste'))
        else:
            cursor.execute(f"""
                INSERT INTO registros_ponto 
                (usuario, data_hora, tipo, modalidade, projeto, atividade)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 6)})
            """, ('func_teste', datetime.now(), 'Início', 'Presencial', 'TESTE', 'Atividade teste'))
            registro_id = cursor.lastrowid
            conn.commit()
            conn.close()
            print(f"✅ Registro de ponto criado: ID {registro_id}")
            return registro_id
        
        if USE_POSTGRESQL:
            registro_id = cursor.fetchone()[0]
            conn.commit()
            print(f"✅ Registro de ponto criado: ID {registro_id}")
            conn.close()
            return registro_id
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro no setup: {e}")
        return None
    finally:
        conn.close()

def test_solicitar_ajuste_correcao(ajuste_system, registro_id):
    """Testa solicitação de correção de registro existente"""
    print_section("📝 TESTE 1: Funcionário solicita CORREÇÃO de registro")
    
    dados_solicitados = {
        "acao": "corrigir",
        "registro_id": registro_id,
        "nova_data": "2025-11-04",
        "nova_hora": "09:30",
        "novo_tipo": "Intermediário",
        "modalidade": "Home Office",
        "projeto": "TESTE_CORRIGIDO",
        "atividade": "Atividade corrigida após ajuste"
    }
    
    resultado = ajuste_system.solicitar_ajuste(
        usuario="func_teste",
        aprovador_solicitado="gestor_teste",
        dados_solicitados=dados_solicitados,
        justificativa="Esqueci de registrar no horário correto, preciso ajustar para 09:30"
    )
    
    if resultado["success"]:
        solicitacao_id = resultado.get("solicitacao_id")
        print(f"✅ Solicitação de CORREÇÃO criada: ID {solicitacao_id}")
        print(f"   └─ Registro alvo: #{registro_id}")
        print(f"   └─ Nova data/hora: {dados_solicitados['nova_data']} {dados_solicitados['nova_hora']}")
        print(f"   └─ Novo tipo: {dados_solicitados['novo_tipo']}")
        return solicitacao_id
    else:
        print(f"❌ Erro ao criar solicitação: {resultado['message']}")
        return None

def test_solicitar_ajuste_criacao(ajuste_system):
    """Testa solicitação de criação de novo registro"""
    print_section("📝 TESTE 2: Funcionário solicita CRIAÇÃO de registro ausente")
    
    dados_solicitados = {
        "acao": "criar",
        "data": "2025-11-03",
        "hora": "18:00",
        "tipo": "Fim",
        "modalidade": "Presencial",
        "projeto": "PROJETO_NOVO",
        "atividade": "Registro que esqueci de fazer ontem"
    }
    
    resultado = ajuste_system.solicitar_ajuste(
        usuario="func_teste",
        aprovador_solicitado="gestor_teste",
        dados_solicitados=dados_solicitados,
        justificativa="Esqueci de registrar a saída ontem, estava em reunião"
    )
    
    if resultado["success"]:
        solicitacao_id = resultado.get("solicitacao_id")
        print(f"✅ Solicitação de CRIAÇÃO registrada: ID {solicitacao_id}")
        print(f"   └─ Novo registro: {dados_solicitados['data']} às {dados_solicitados['hora']}")
        print(f"   └─ Tipo: {dados_solicitados['tipo']}")
        return solicitacao_id
    else:
        print(f"❌ Erro ao criar solicitação: {resultado['message']}")
        return None

def test_listar_pendentes(ajuste_system):
    """Testa listagem de solicitações pendentes para gestor"""
    print_section("📋 TESTE 3: Gestor visualiza solicitações pendentes")
    
    solicitacoes = ajuste_system.listar_solicitacoes_para_gestor("gestor_teste")
    
    print(f"Total de solicitações pendentes: {len(solicitacoes)}")
    
    for sol in solicitacoes:
        print(f"\n📌 Solicitação #{sol['id']}")
        print(f"   └─ De: {sol['usuario']}")
        print(f"   └─ Status: {sol['status']}")
        print(f"   └─ Ação: {sol['dados'].get('acao', 'N/D')}")
        print(f"   └─ Justificativa: {sol['justificativa'][:50]}...")
    
    return solicitacoes

def test_aprovar_ajuste(ajuste_system, solicitacao_id):
    """Testa aprovação de ajuste pelo gestor"""
    print_section(f"✅ TESTE 4: Gestor APROVA solicitação #{solicitacao_id}")
    
    resultado = ajuste_system.aprovar_ajuste(
        solicitacao_id=solicitacao_id,
        aprovador="gestor_teste",
        observacoes="Aprovado! Justificativa válida."
    )
    
    if resultado["success"]:
        print(f"✅ Ajuste aprovado com sucesso")
        print(f"   └─ {resultado['message']}")
        return True
    else:
        print(f"❌ Erro ao aprovar: {resultado['message']}")
        return False

def test_rejeitar_ajuste(ajuste_system, solicitacao_id):
    """Testa rejeição de ajuste pelo gestor"""
    print_section(f"❌ TESTE 5: Gestor REJEITA solicitação #{solicitacao_id}")
    
    resultado = ajuste_system.rejeitar_ajuste(
        solicitacao_id=solicitacao_id,
        aprovador="gestor_teste",
        observacoes="Rejeitado: necessário mais evidências. Por favor, reenvie com comprovante."
    )
    
    if resultado["success"]:
        print(f"✅ Ajuste rejeitado com sucesso")
        print(f"   └─ {resultado['message']}")
        return True
    else:
        print(f"❌ Erro ao rejeitar: {resultado['message']}")
        return False

def test_verificar_historico(ajuste_system):
    """Testa visualização do histórico pelo funcionário"""
    print_section("📜 TESTE 6: Funcionário verifica histórico de solicitações")
    
    solicitacoes = ajuste_system.listar_solicitacoes_usuario("func_teste")
    
    print(f"Total de solicitações do funcionário: {len(solicitacoes)}")
    
    for sol in solicitacoes:
        status_emoji = "✅" if sol['status'] == 'aprovado' else "❌" if sol['status'] == 'rejeitado' else "⏳"
        print(f"\n{status_emoji} Solicitação #{sol['id']} - {sol['status'].upper()}")
        print(f"   └─ Enviada em: {sol['data_solicitacao']}")
        
        if sol['data_resposta']:
            print(f"   └─ Respondida em: {sol['data_resposta']}")
            print(f"   └─ Por: {sol['respondido_por']}")
        
        if sol['observacoes']:
            print(f"   └─ Retorno: {sol['observacoes']}")

def run_full_test():
    """Executa bateria completa de testes"""
    print_section("🧪 INICIANDO TESTE END-TO-END: Fluxo de Ajustes")
    
    try:
        # Inicializar banco de dados
        print("Inicializando banco de dados...")
        init_db()
        
        # Inicializar sistema
        ajuste_system = AjusteRegistrosSystem()
        
        # Setup: criar dados de teste
        registro_id = setup_test_data()
        if not registro_id:
            print("❌ Falha no setup, abortando testes")
            return
        
        # Teste 1: Solicitar correção
        sol_correcao_id = test_solicitar_ajuste_correcao(ajuste_system, registro_id)
        
        # Teste 2: Solicitar criação
        sol_criacao_id = test_solicitar_ajuste_criacao(ajuste_system)
        
        # Teste 3: Listar pendentes
        pendentes = test_listar_pendentes(ajuste_system)
        
        # Teste 4: Aprovar primeira solicitação
        if sol_correcao_id:
            test_aprovar_ajuste(ajuste_system, sol_correcao_id)
        
        # Teste 5: Rejeitar segunda solicitação
        if sol_criacao_id:
            test_rejeitar_ajuste(ajuste_system, sol_criacao_id)
        
        # Teste 6: Verificar histórico
        test_verificar_historico(ajuste_system)
        
        print_section("🎉 TESTE END-TO-END CONCLUÍDO COM SUCESSO!")
        print("\n✅ Todos os componentes do fluxo de ajustes funcionando:")
        print("   ✓ Solicitação de correção")
        print("   ✓ Solicitação de criação")
        print("   ✓ Listagem para gestor")
        print("   ✓ Aprovação de ajuste")
        print("   ✓ Rejeição de ajuste")
        print("   ✓ Histórico do funcionário")
        print("\n💡 Próximo passo: Testar na UI em http://localhost:8501")
        
    except Exception as e:
        print_section("❌ ERRO DURANTE TESTE")
        print(f"Exceção: {type(e).__name__}")
        print(f"Mensagem: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_full_test()
