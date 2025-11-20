"""
Teste End-to-End do Fluxo de Ajustes de Registros
Simula interação completa: funcionário solicita → gestor aprova/rejeita
"""

import sys
import os
from datetime import datetime, date, time
import hashlib

import pytest

# Adicionar path do módulo (apontar para diretório que contém o pacote ponto_esa_v5)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ponto_esa_v5'))

from ajuste_registros_system import AjusteRegistrosSystem  # type: ignore[import-not-found]
from database_postgresql import get_connection, init_db, USE_POSTGRESQL  # type: ignore[import-not-found]

# Definir placeholder correto
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"

TEST_USERS = {"colaborador": "func_teste", "gestor": "gestor_teste"}


def _cleanup_test_data():
    """Remove artefatos criados por estes testes."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"DELETE FROM usuarios WHERE usuario IN ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})",
            (TEST_USERS["colaborador"], TEST_USERS["gestor"]),
        )
        cursor.execute(
            f"DELETE FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER}",
            (TEST_USERS["colaborador"],),
        )
        cursor.execute(
            f"DELETE FROM solicitacoes_ajuste_ponto WHERE usuario = {SQL_PLACEHOLDER}",
            (TEST_USERS["colaborador"],),
        )
        cursor.execute(
            f"DELETE FROM solicitacoes_ajuste_ponto WHERE aprovador_solicitado = {SQL_PLACEHOLDER}",
            (TEST_USERS["gestor"],),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="module")
def ajuste_system():
    """Instancia o sistema com banco inicializado e limpo."""
    init_db()
    _cleanup_test_data()
    system = AjusteRegistrosSystem()
    yield system
    _cleanup_test_data()


@pytest.fixture
def registro_id(ajuste_system):
    """Garante um registro de ponto criado para os testes."""
    registro = setup_test_data()
    if registro is None:
        pytest.fail("Falha ao preparar registro de ponto de teste")
    return registro


@pytest.fixture
def solicitacao_id(ajuste_system):
    """Gera uma solicitação pendente e retorna seu ID."""
    registro = setup_test_data()
    assert registro is not None, "Não foi possível preparar registro para solicitação"

    dados_solicitados = {
        "acao": "corrigir",
        "registro_id": registro,
        "nova_data": datetime.now().strftime("%Y-%m-%d"),
        "nova_hora": "10:00",
        "novo_tipo": "Intermediário",
        "modalidade": "Presencial",
        "projeto": "TESTE_FIXTURE",
        "atividade": "Solicitação criada pela fixture",
    }

    resultado = ajuste_system.solicitar_ajuste(
        usuario=TEST_USERS["colaborador"],
        aprovador_solicitado=TEST_USERS["gestor"],
        dados_solicitados=dados_solicitados,
        justificativa="Fixture solicitacao",
    )

    assert resultado.get("success"), resultado.get("message")
    solicitacao = resultado.get("solicitacao_id")
    assert solicitacao is not None, "Fixture não retornou ID da solicitação"

    yield solicitacao

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"DELETE FROM solicitacoes_ajuste_ponto WHERE id = {SQL_PLACEHOLDER}",
            (solicitacao,),
        )
        conn.commit()
    finally:
        conn.close()


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
    registro_id = None
    
    try:
        # Criar usuário funcionário de teste (se não existir)
        cursor.execute(f"SELECT COUNT(*) FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (TEST_USERS["colaborador"],))
        if cursor.fetchone()[0] == 0:
            senha_hash = hashlib.sha256('senha123'.encode()).hexdigest()
            placeholders = ', '.join([SQL_PLACEHOLDER] * 5)
            cursor.execute(f"""
                INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 5)})
            """, (TEST_USERS["colaborador"], senha_hash, 'funcionario', 'Funcionário Teste', 1))
            print("✅ Usuário funcionário criado: func_teste / senha123")
        
        # Criar usuário gestor de teste (se não existir)
        cursor.execute(f"SELECT COUNT(*) FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (TEST_USERS["gestor"],))
        if cursor.fetchone()[0] == 0:
            senha_hash = hashlib.sha256('senha123'.encode()).hexdigest()
            cursor.execute(f"""
                INSERT INTO usuarios (usuario, senha, tipo, nome_completo, ativo)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 5)})
            """, (TEST_USERS["gestor"], senha_hash, 'gestor', 'Gestor Teste', 1))
            print("✅ Usuário gestor criado: gestor_teste / senha123")
        
        # Criar registro de ponto de teste
        if USE_POSTGRESQL:
            cursor.execute(f"""
                INSERT INTO registros_ponto 
                (usuario, data_hora, tipo, modalidade, projeto, atividade)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 6)})
                RETURNING id
            """, (TEST_USERS["colaborador"], datetime.now(), 'Início', 'Presencial', 'TESTE', 'Atividade teste'))
            registro_id = cursor.fetchone()[0]
        else:
            cursor.execute(f"""
                INSERT INTO registros_ponto 
                (usuario, data_hora, tipo, modalidade, projeto, atividade)
                VALUES ({', '.join([SQL_PLACEHOLDER] * 6)})
            """, (TEST_USERS["colaborador"], datetime.now(), 'Início', 'Presencial', 'TESTE', 'Atividade teste'))
            registro_id = cursor.lastrowid

        conn.commit()
        print(f"✅ Registro de ponto criado: ID {registro_id}")
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
        usuario=TEST_USERS["colaborador"],
        aprovador_solicitado=TEST_USERS["gestor"],
        dados_solicitados=dados_solicitados,
        justificativa="Esqueci de registrar no horário correto, preciso ajustar para 09:30"
    )
    
    assert resultado["success"], f"Falha ao solicitar ajuste: {resultado.get('message')}"
    solicitacao_id = resultado.get("solicitacao_id")
    assert solicitacao_id is not None, "A solicitação não retornou um ID"
    
    print(f"✅ Solicitação de CORREÇÃO criada: ID {solicitacao_id}")
    print(f"   └─ Registro alvo: #{registro_id}")
    print(f"   └─ Nova data/hora: {dados_solicitados['nova_data']} {dados_solicitados['nova_hora']}")
    print(f"   └─ Novo tipo: {dados_solicitados['novo_tipo']}")

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
        usuario=TEST_USERS["colaborador"],
        aprovador_solicitado=TEST_USERS["gestor"],
        dados_solicitados=dados_solicitados,
        justificativa="Esqueci de registrar a saída ontem, estava em reunião"
    )
    
    assert resultado["success"], f"Falha ao criar solicitação: {resultado.get('message')}"
    solicitacao_id = resultado.get("solicitacao_id")
    assert solicitacao_id is not None, "A solicitação de criação não retornou um ID"

    print(f"✅ Solicitação de CRIAÇÃO registrada: ID {solicitacao_id}")
    print(f"   └─ Novo registro: {dados_solicitados['data']} às {dados_solicitados['hora']}")
    print(f"   └─ Tipo: {dados_solicitados['tipo']}")


def test_listar_pendentes(ajuste_system):
    """Testa listagem de solicitações pendentes para gestor"""
    print_section("📋 TESTE 3: Gestor visualiza solicitações pendentes")
    
    solicitacoes = ajuste_system.listar_solicitacoes_para_gestor(TEST_USERS["gestor"])
    
    assert isinstance(solicitacoes, list)
    print(f"Total de solicitações pendentes: {len(solicitacoes)}")
    
    for sol in solicitacoes:
        print(f"\n📌 Solicitação #{sol['id']}")
        print(f"   └─ De: {sol['usuario']}")
        print(f"   └─ Status: {sol['status']}")
        print(f"   └─ Ação: {sol['dados'].get('acao', 'N/D')}")
        print(f"   └─ Justificativa: {sol['justificativa'][:50]}...")


def test_aprovar_ajuste(ajuste_system, solicitacao_id):
    """Testa aprovação de ajuste pelo gestor"""
    print_section(f"✅ TESTE 4: Gestor APROVA solicitação #{solicitacao_id}")
    
    resultado = ajuste_system.aplicar_ajuste(
        solicitacao_id=solicitacao_id,
        gestor=TEST_USERS["gestor"],
        dados_confirmados={},
        observacoes="Aprovado! Justificativa válida."
    )
    
    assert resultado["success"], f"Falha ao aprovar ajuste: {resultado.get('message')}"
    print(f"✅ Ajuste aprovado com sucesso")
    print(f"   └─ {resultado['message']}")


def test_rejeitar_ajuste(ajuste_system, solicitacao_id):
    """Testa rejeição de ajuste pelo gestor"""
    print_section(f"❌ TESTE 5: Gestor REJEITA solicitação #{solicitacao_id}")
    
    resultado = ajuste_system.rejeitar_ajuste(
        solicitacao_id=solicitacao_id,
        gestor=TEST_USERS["gestor"],
        observacoes="Rejeitado: necessário mais evidências. Por favor, reenvie com comprovante."
    )
    
    assert resultado["success"], f"Falha ao rejeitar ajuste: {resultado.get('message')}"
    print(f"✅ Ajuste rejeitado com sucesso")
    print(f"   └─ {resultado['message']}")


def test_verificar_historico(ajuste_system):
    """Testa visualização do histórico pelo funcionário"""
    print_section("📜 TESTE 6: Funcionário verifica histórico de solicitações")
    
    solicitacoes = ajuste_system.listar_solicitacoes_usuario(TEST_USERS["colaborador"])
    
    assert isinstance(solicitacoes, list)
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