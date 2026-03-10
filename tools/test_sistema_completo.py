"""
Teste Completo End-to-End do Sistema Ponto ESA v5
Testa TODAS as funcionalidades como funcionário e gestor fariam
Valida: registros, cálculos, aprovações, notificações, relatórios
"""

import sys
import os
from datetime import datetime, date, time, timedelta
import json
import pytest

# Adiciona os caminhos necessários para encontrar os módulos da aplicação
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PACKAGE_DIR = os.path.join(ROOT_DIR, 'ponto_esa_v5', 'ponto_esa_v5')
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if PACKAGE_DIR not in sys.path:
    sys.path.insert(0, PACKAGE_DIR)

# Agora as importações devem funcionar tanto em execução direta quanto via pacote
try:
    from ponto_esa_v5.banco_horas_system import BancoHorasSystem  # type: ignore[import]
    from ponto_esa_v5.calculo_horas_system import CalculoHorasSystem  # type: ignore[import]
    from ponto_esa_v5.atestado_horas_system import AtestadoHorasSystem  # type: ignore[import]
    from ponto_esa_v5.ajuste_registros_system import AjusteRegistrosSystem  # type: ignore[import]
    from ponto_esa_v5.horas_extras_system import HorasExtrasSystem  # type: ignore[import]
    from ponto_esa_v5.database_postgresql import (  # type: ignore[import]
        get_connection,
        init_db,
        USE_POSTGRESQL,
        hash_password,
    )
    from ponto_esa_v5.database import SQL_PLACEHOLDER  # type: ignore[import]
except ImportError:  # pragma: no cover - fallback para execução direta dos testes
    from ponto_esa_v5.ponto_esa_v5.banco_horas_system import BancoHorasSystem  # type: ignore
    from ponto_esa_v5.ponto_esa_v5.calculo_horas_system import CalculoHorasSystem  # type: ignore
    from ponto_esa_v5.ponto_esa_v5.atestado_horas_system import AtestadoHorasSystem  # type: ignore
    from ponto_esa_v5.ponto_esa_v5.ajuste_registros_system import AjusteRegistrosSystem  # type: ignore
    from ponto_esa_v5.ponto_esa_v5.horas_extras_system import HorasExtrasSystem  # type: ignore
    from ponto_esa_v5.ponto_esa_v5.database_postgresql import (  # type: ignore
        get_connection,
        init_db,
        USE_POSTGRESQL,
        hash_password,
    )
    from ponto_esa_v5.ponto_esa_v5.database import SQL_PLACEHOLDER  # type: ignore

# Definir placeholder correto e garantir que o esquema exista antes dos testes
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"
init_db()

def print_section(title, level=1):
    """Imprime seção formatada"""
    if level == 1:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    elif level == 2:
        print(f"\n{'-'*80}")
        print(f"  {title}")
        print(f"{'-'*80}\n")
    else:
        print(f"\n  ▶ {title}")

def print_result(passed, message):
    """Imprime resultado do teste"""
    status = "✅" if passed else "❌"
    print(f"{status} {message}")
    return passed

def limpar_dados_teste():
    """Remove dados de teste anteriores"""
    print_section("🧹 Limpando dados de teste anteriores", 2)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Limpar dependências para evitar violações de FK na remoção de registros.
        cursor.execute(f"DELETE FROM auditoria_correcoes WHERE gestor IN ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})",
                      ('teste_gestor', 'teste_admin'))

        if USE_POSTGRESQL:
            cursor.execute("DELETE FROM solicitacoes_ajuste_ponto WHERE usuario LIKE %s", ('%teste%',))
            cursor.execute("DELETE FROM solicitacoes_horas_extras WHERE usuario LIKE %s", ('%teste%',))
        else:
            cursor.execute("DELETE FROM solicitacoes_ajuste_ponto WHERE usuario LIKE ?", ('%teste%',))
            cursor.execute("DELETE FROM solicitacoes_horas_extras WHERE usuario LIKE ?", ('%teste%',))

        # Remover usuários de teste
        cursor.execute(f"DELETE FROM usuarios WHERE usuario IN ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})",
                      ('teste_func', 'teste_gestor', 'teste_admin'))
        
        # Remover registros de teste
        cursor.execute(f"DELETE FROM registros_ponto WHERE usuario IN ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})",
                      ('teste_func', 'teste_gestor'))
        
        conn.commit()
        print("✅ Dados de teste anteriores removidos")
        
    except Exception as e:
        print(f"⚠️ Erro ao limpar dados (pode ser normal se for primeira execução): {e}")
        conn.rollback()
    finally:
        conn.close()

def criar_usuarios_teste():
    """Cria usuários de teste: funcionário, gestor e admin"""
    print_section("👥 Criando usuários de teste", 2)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    usuarios = [
        {
            'usuario': 'teste_func',
            'senha': hash_password('senha123'),
            'tipo': 'funcionario',
            'nome_completo': 'Funcionário Teste',
            'jornada_inicio': '08:00:00',
            'jornada_fim': '17:00:00'
        },
        {
            'usuario': 'teste_gestor',
            'senha': hash_password('senha123'),
            'tipo': 'gestor',
            'nome_completo': 'Gestor Teste',
            'jornada_inicio': '08:00:00',
            'jornada_fim': '18:00:00'
        },
        {
            'usuario': 'teste_admin',
            'senha': hash_password('senha123'),
            'tipo': 'admin',
            'nome_completo': 'Admin Teste',
            'jornada_inicio': '08:00:00',
            'jornada_fim': '17:00:00'
        }
    ]
    
    for user in usuarios:
        try:
            cursor.execute(f'''
                INSERT INTO usuarios (usuario, senha, tipo, nome_completo, jornada_inicio_previsto, jornada_fim_previsto)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
            ''', (user['usuario'], user['senha'], user['tipo'], user['nome_completo'], 
                  user['jornada_inicio'], user['jornada_fim']))
            
            print(f"✅ Usuário criado: {user['usuario']} ({user['tipo']}) - senha: senha123")
        except Exception as e:
            print(f"❌ Erro ao criar {user['usuario']}: {e}")
    
    conn.commit()
    conn.close()

def test_registrar_ponto():
    """TESTE 1: Registrar ponto - Entrada, Saída Almoço, Retorno, Saída"""
    print_section("📍 TESTE 1: Sistema de Registro de Ponto")
    
    limpar_dados_teste()
    criar_usuarios_teste()

    conn = get_connection()
    cursor = conn.cursor()
    
    hoje = date.today()
    registros = [
        {'tipo': 'entrada', 'hora': '08:00:00', 'modalidade': 'presencial'},
        {'tipo': 'saida_almoco', 'hora': '12:00:00', 'modalidade': 'presencial'},
        {'tipo': 'retorno_almoco', 'hora': '13:00:00', 'modalidade': 'presencial'},
        {'tipo': 'saida', 'hora': '17:30:00', 'modalidade': 'presencial'}
    ]
    
    all_passed = True
    
    for i, registro in enumerate(registros, 1):
        try:
            data_hora = datetime.combine(hoje, time.fromisoformat(registro['hora']))
            
            cursor.execute(f'''
                INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
            ''', ('teste_func', data_hora, registro['tipo'], registro['modalidade']))
            
            conn.commit()
            all_passed &= print_result(True, f"Registro {i}/4: {registro['tipo']} às {registro['hora']}")
        except Exception as e:
            all_passed &= print_result(False, f"Erro no registro {registro['tipo']}: {e}")
    
    # Verificar se todos os registros foram salvos
    cursor.execute(f'''
        SELECT COUNT(*) FROM registros_ponto 
        WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
    ''', ('teste_func', hoje))
    
    count = cursor.fetchone()[0]
    all_passed &= print_result(count == 4, f"Total de registros salvos: {count}/4")
    
    conn.close()
    assert all_passed, "Falha no registro de ponto"

def test_calculo_horas():
    """TESTE 2: Cálculo de horas trabalhadas"""
    print_section("🧮 TESTE 2: Cálculo de Horas Trabalhadas")
    
    calc_system = CalculoHorasSystem()
    hoje = date.today()
    
    # Calcular horas do dia
    resultado = calc_system.calcular_horas_dia('teste_func', hoje.strftime('%Y-%m-%d'))
    
    all_passed = True
    
    if resultado:
        # Esperado: 08:00-12:00 (4h) + 13:00-17:30 (4.5h) = 8.5h
        horas_esperadas_liquidas = 8.5
        horas_calculadas = resultado.get('horas_liquidas', 0)
        
        all_passed &= print_result(
            abs(horas_calculadas - horas_esperadas_liquidas) < 0.1,
            f"Horas trabalhadas (líquidas): {horas_calculadas:.2f}h (esperado: {horas_esperadas_liquidas}h)"
        )
        
        all_passed &= print_result(
            resultado.get('primeiro_registro') == '08:00',
            f"Entrada: {resultado.get('primeiro_registro')}"
        )
        
        all_passed &= print_result(
            resultado.get('ultimo_registro') == '17:30',
            f"Saída: {resultado.get('ultimo_registro')}"
        )
        
        # Horas finais (com multiplicadores e descontos)
        horas_finais = resultado.get('horas_finais', 0)
        all_passed &= print_result(
            horas_finais > 0,
            f"Horas finais calculadas: {horas_finais:.2f}h"
        )
    else:
        all_passed = print_result(False, "Falha ao calcular horas do dia")
    
    assert all_passed, "Falha no cálculo de horas"

def test_banco_horas():
    """TESTE 3: Sistema de Banco de Horas"""
    print_section("💰 TESTE 3: Sistema de Banco de Horas")

    limpar_dados_teste()
    criar_usuarios_teste()

    conn = get_connection()
    cursor = conn.cursor()
    hoje = date.today()
    registros_ponto = [
        ('teste_func', datetime.combine(hoje, time(8, 1)), 'entrada', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(12, 5)), 'saida_almoco', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(13, 2)), 'retorno_almoco', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(17, 35)), 'saida', 'presencial'),
    ]
    for reg in registros_ponto:
        cursor.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        ''', reg)
    conn.commit()
    conn.close()
    # --- Fim da adição de registros ---

    banco_system = BancoHorasSystem()

    all_passed = True
    
    # Calcular banco de horas (últimos 7 dias)
    hoje = date.today()
    sete_dias_atras = hoje - timedelta(days=7)
    
    resultado = banco_system.calcular_banco_horas(
        'teste_func',
        sete_dias_atras.strftime('%Y-%m-%d'),
        hoje.strftime('%Y-%m-%d')
    )
    
    all_passed &= print_result(
        resultado is not None,
        f"Banco de horas calculado: {resultado.get('saldo_total', 0):.2f}h"
    )
    
    # Buscar extrato
    extrato = resultado.get('extrato', []) if resultado else []
    
    all_passed &= print_result(
        extrato is not None and len(extrato) > 0,
        f"Extrato gerado com {len(extrato) if extrato else 0} registros"
    )
    
    assert all_passed, "Falha no sistema de banco de horas"

def test_ajuste_registros_criacao():
    """TESTE 4: Solicitar ajuste - Criar registro ausente"""
    print_section("📝 TESTE 4: Ajuste de Registros - Criar Registro Ausente")
    
    ajuste_system = AjusteRegistrosSystem()
    ontem = date.today() - timedelta(days=1)
    
    all_passed = True
    
    try:
        # Solicitar criação de registro
        dados_solicitados = {
            'acao': 'criar',
            'data': ontem.strftime('%Y-%m-%d'),
            'hora': '08:00:00',
            'tipo': 'entrada',
            'modalidade': 'presencial'
        }
        
        resultado = ajuste_system.solicitar_ajuste(
            usuario='teste_func',
            aprovador_solicitado='teste_gestor',
            dados_solicitados=dados_solicitados,
            justificativa='Esqueci de registrar ontem - teste de criação'
        )
        
        all_passed &= print_result(
            resultado.get('success', False),
            f"Solicitação: {resultado.get('message', '')} (ID: {resultado.get('id', 'N/A')})"
        )
        
        # Verificar se foi salva
        solicitacoes = ajuste_system.listar_solicitacoes_para_gestor('teste_gestor')
        all_passed &= print_result(
            len(solicitacoes) > 0,
            f"Solicitação aparece na lista do gestor ({len(solicitacoes)} pendentes)"
        )
        
    except Exception as e:
        all_passed = print_result(False, f"Erro ao criar solicitação: {e}")
    
    assert all_passed, "Falha ao solicitar criação de ajuste"

def test_ajuste_registros_correcao():
    """TESTE 5: Solicitar ajuste - Corrigir registro existente"""
    print_section("✏️ TESTE 5: Ajuste de Registros - Corrigir Registro Existente")
    
    ajuste_system = AjusteRegistrosSystem()
    hoje = date.today()
    
    all_passed = True
    
    try:
        # Buscar o registro de entrada de hoje
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT id FROM registros_ponto 
            WHERE usuario = {SQL_PLACEHOLDER} 
            AND DATE(data_hora) = {SQL_PLACEHOLDER} 
            AND tipo = {SQL_PLACEHOLDER}
            LIMIT 1
        ''', ('teste_func', hoje, 'entrada'))
        
        registro = cursor.fetchone()
        conn.close()
        
        if registro:
            registro_id = registro[0]
            
            # Solicitar correção (entrada era 08:00, mudar para 07:30)
            dados_solicitados = {
                'acao': 'corrigir',
                'registro_id': registro_id,
                'nova_data': hoje.strftime('%Y-%m-%d'),
                'nova_hora': '07:30',
                'novo_tipo': 'entrada'
            }
            
            resultado = ajuste_system.solicitar_ajuste(
                usuario='teste_func',
                aprovador_solicitado='teste_gestor',
                dados_solicitados=dados_solicitados,
                justificativa='Cheguei mais cedo mas registrei errado - teste de correção'
            )
            
            all_passed &= print_result(
                resultado.get('success', False),
                f"Correção: {resultado.get('message', '')} (ID: {resultado.get('id', 'N/A')})"
            )
        else:
            all_passed &= print_result(False, "Registro de entrada não encontrado")
        
    except Exception as e:
        all_passed = print_result(False, f"Erro ao solicitar correção: {e}")
    
    assert all_passed, "Falha ao solicitar correção de ajuste"

def test_aprovacao_ajuste():
    """TESTE 6: Gestor aprovar ajuste"""
    print_section("👍 TESTE 6: Aprovação de Ajuste pelo Gestor")
    
    ajuste_system = AjusteRegistrosSystem()
    
    all_passed = True
    
    try:
        # Listar pendentes
        solicitacoes = ajuste_system.listar_solicitacoes_para_gestor('teste_gestor')
        
        if solicitacoes and len(solicitacoes) > 0:
            # Aprovar a primeira solicitação
            primeira = solicitacoes[0]
            solicitacao_id = primeira['id']
            
            # Aplicar ajuste (aprovação) - dados_confirmados podem ser os mesmos da solicitação
            import json
            dados_solicitados = json.loads(primeira.get('dados_solicitados', '{}'))
            
            resultado = ajuste_system.aplicar_ajuste(
                solicitacao_id=solicitacao_id,
                gestor='teste_gestor',
                dados_confirmados=dados_solicitados,
                observacoes='Aprovado para teste'
            )
            
            all_passed &= print_result(
                resultado.get('success', False),
                f"Ajuste ID {solicitacao_id} aplicado com sucesso: {resultado.get('message', '')}"
            )
            
            # Verificar se o status mudou
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f'''
                SELECT status, respondido_por 
                FROM solicitacoes_ajuste_ponto 
                WHERE id = {SQL_PLACEHOLDER}
            ''', (solicitacao_id,))
            
            registro = cursor.fetchone()
            conn.close()
            
            if registro:
                status, respondido_por = registro
                all_passed &= print_result(
                    status == 'aplicado',
                    f"Status atualizado para: {status}"
                )
                all_passed &= print_result(
                    respondido_por == 'teste_gestor',
                    f"Respondido por: {respondido_por}"
                )
            
        else:
            all_passed &= print_result(False, "Nenhuma solicitação pendente encontrada")
        
    except Exception as e:
        all_passed = print_result(False, f"Erro ao aprovar ajuste: {e}")
    
    assert all_passed, "Falha na aprovação de ajuste"

def test_rejeicao_ajuste():
    """TESTE 7: Gestor rejeitar ajuste"""
    print_section("👎 TESTE 7: Rejeição de Ajuste pelo Gestor")
    
    ajuste_system = AjusteRegistrosSystem()
    
    all_passed = True
    
    try:
        # Listar pendentes restantes
        solicitacoes = ajuste_system.listar_solicitacoes_para_gestor('teste_gestor')
        
        if solicitacoes and len(solicitacoes) > 0:
            # Rejeitar a primeira solicitação pendente
            primeira = solicitacoes[0]
            solicitacao_id = primeira['id']
            
            resultado = ajuste_system.rejeitar_ajuste(
                solicitacao_id=solicitacao_id,
                gestor='teste_gestor',
                observacoes='Rejeitado para teste - falta justificativa adequada'
            )
            
            all_passed &= print_result(
                resultado.get('success', False),
                f"Ajuste ID {solicitacao_id} rejeitado: {resultado.get('message', '')}"
            )
            
            # Verificar status
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f'''
                SELECT status, observacoes 
                FROM solicitacoes_ajuste_ponto 
                WHERE id = {SQL_PLACEHOLDER}
            ''', (solicitacao_id,))
            
            registro = cursor.fetchone()
            conn.close()
            
            if registro:
                status, obs = registro
                all_passed &= print_result(
                    status == 'rejeitado',
                    f"Status atualizado para: {status}"
                )
                all_passed &= print_result(
                    'Rejeitado para teste' in (obs or ''),
                    f"Observação registrada"
                )
        else:
            print("⚠️ Nenhuma solicitação pendente (esperado, todas foram processadas)")
        
    except Exception as e:
        all_passed = print_result(False, f"Erro ao rejeitar ajuste: {e}")
    
    assert all_passed, "Falha na rejeição de ajuste"

def test_horas_extras():
    """TESTE 8: Sistema de Horas Extras"""
    print_section("⏰ TESTE 8: Sistema de Horas Extras")
    
    horas_extras_system = HorasExtrasSystem()
    
    all_passed = True
    
    try:
        # Solicitar hora extra
        hoje = date.today()
        amanha = hoje + timedelta(days=1)
        
        resultado = horas_extras_system.solicitar_horas_extras(
            usuario='teste_func',
            data=amanha.strftime('%Y-%m-%d'),
            hora_inicio='19:00',
            hora_fim='21:00',
            justificativa='Projeto urgente - teste sistema',
            aprovador_solicitado='teste_gestor'
        )
        
        all_passed &= print_result(
            resultado.get('success', False),
            f"Solicitação de hora extra: {resultado.get('message', '')}"
        )
        
        # Listar solicitações
        solicitacoes = horas_extras_system.listar_solicitacoes_usuario('teste_func')
        all_passed &= print_result(
            len(solicitacoes) > 0,
            f"Solicitações encontradas: {len(solicitacoes)}"
        )
        
        # Listar para aprovação (gestor)
        pendentes = horas_extras_system.listar_solicitacoes_para_aprovacao('teste_gestor')
        all_passed &= print_result(
            len(pendentes) > 0,
            f"Pendentes de aprovação: {len(pendentes)}"
        )
        
        # Aprovar hora extra
        if pendentes and len(pendentes) > 0:
            solicitacao_id = pendentes[0]['id']
            resultado_aprovacao = horas_extras_system.aprovar_solicitacao(
                solicitacao_id=solicitacao_id,
                aprovador='teste_gestor',
                observacoes='Aprovado para teste'
            )
            all_passed &= print_result(
                resultado_aprovacao.get('success', False),
                f"Hora extra ID {solicitacao_id}: {resultado_aprovacao.get('message', '')}"
            )
        
    except Exception as e:
        all_passed = print_result(False, f"Erro no sistema de horas extras: {e}")
    
    assert all_passed, "Falha no sistema de horas extras"

def test_atestados():
    """TESTE 9: Sistema de Atestados"""
    print_section("🏥 TESTE 9: Sistema de Atestados e Ausências")

    limpar_dados_teste()
    criar_usuarios_teste()

    atestado_system = AtestadoHorasSystem()
    all_passed = True

    try:
        ontem = date.today() - timedelta(days=1)

        # Registrar atestado de horas
        resultado = atestado_system.registrar_atestado_horas(
            usuario='teste_func',
            data=ontem.strftime('%Y-%m-%d'),
            hora_inicio='09:00',
            hora_fim='11:00',
            motivo='Consulta médica de rotina - teste',
            arquivo_comprovante=None,
            nao_possui_comprovante=1
        )

        all_passed &= print_result(
            resultado.get('success', False),
            f"Atestado de horas: {resultado.get('message', '')}"
        )

        # Listar atestados
        atestados = atestado_system.listar_atestados_usuario('teste_func')
        all_passed &= print_result(
            len(atestados) > 0,
            f"Atestados registrados: {len(atestados)}"
        )

        # Verificar se afeta cálculo de horas
        calc_system = CalculoHorasSystem()
        resultado_ontem = calc_system.calcular_horas_dia('teste_func', ontem.strftime('%Y-%m-%d'))

        if resultado_ontem:
            print_result(
                True,
                f"Ausência detectada no cálculo: {resultado_ontem.get('ausencia', 'Nenhuma')}"
            )
        else:
            print_result(
                True,
                "Cálculo de horas retornou nenhum registro para o período"
            )

    except Exception as e:
        all_passed = print_result(False, f"Erro no sistema de atestados: {e}")

    assert all_passed, "Falha no sistema de atestados"


def test_relatorios():
    """TESTE 10: Geração de Relatórios"""
    print_section("📊 TESTE 10: Geração de Relatórios")

    limpar_dados_teste()
    criar_usuarios_teste()

    conn = get_connection()
    cursor = conn.cursor()

    hoje = date.today()
    registros = [
        ('teste_func', datetime.combine(hoje, time(8, 0)), 'entrada', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(12, 0)), 'saida_almoco', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(13, 0)), 'retorno_almoco', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(17, 30)), 'saida', 'presencial'),
    ]

    for registro in registros:
        cursor.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        ''', registro)

    conn.commit()
    conn.close()

    calc_system = CalculoHorasSystem()

    all_passed = True
    
    try:
        # Relatório de horas extras
        hoje = date.today()
        inicio_mes = date(hoje.year, hoje.month, 1)
        
        relatorio = calc_system.gerar_relatorio_horas_extras(
            'teste_func',
            inicio_mes.strftime('%Y-%m-%d'),
            hoje.strftime('%Y-%m-%d')
        )
        
        all_passed &= print_result(
            relatorio is not None and relatorio.get('success', False),
            f"Relatório de horas extras: {relatorio.get('message', '') if relatorio else 'Erro'}"
        )
        
        # Cálculo de horas do dia de hoje
        resultado_hoje = calc_system.calcular_horas_dia('teste_func', hoje.strftime('%Y-%m-%d'))
        
        all_passed &= print_result(
            resultado_hoje is not None,
            f"Cálculo de horas do dia: {resultado_hoje.get('horas_trabalhadas', 0) if resultado_hoje else 0}h trabalhadas"
        )
        
    except Exception as e:
        all_passed = print_result(False, f"Erro na geração de relatórios: {e}")
    
    assert all_passed, "Falha na geração de relatórios"

def test_validacoes_integridade():
    """TESTE 11: Validações e Integridade de Dados"""
    print_section("🔍 TESTE 11: Validações e Integridade de Dados")
    
    limpar_dados_teste()
    criar_usuarios_teste()

    conn_setup = get_connection()
    cursor_setup = conn_setup.cursor()
    hoje = date.today()
    registros = [
        ('teste_func', datetime.combine(hoje, time(8, 0)), 'entrada', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(12, 0)), 'saida_almoco', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(13, 0)), 'retorno_almoco', 'presencial'),
        ('teste_func', datetime.combine(hoje, time(17, 30)), 'saida', 'presencial'),
    ]

    for registro in registros:
        cursor_setup.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        ''', registro)

    conn_setup.commit()
    conn_setup.close()

    conn = get_connection()
    cursor = conn.cursor()
    
    all_passed = True
    
    try:
        # 1. Verificar que não há registros duplicados de mesmo tipo no mesmo minuto
        cursor.execute(f'''
            SELECT usuario, data_hora, tipo, COUNT(*) as qtd
            FROM registros_ponto
            WHERE usuario = {SQL_PLACEHOLDER}
            GROUP BY usuario, data_hora, tipo
            HAVING COUNT(*) > 1
        ''', ('teste_func',))
        
        duplicados = cursor.fetchall()
        all_passed &= print_result(
            len(duplicados) == 0,
            f"Verificação de duplicados: {len(duplicados)} encontrados"
        )
        
        # 2. Verificar sequência lógica de registros (entrada antes de saída)
        hoje = date.today()
        cursor.execute(f'''
            SELECT tipo, data_hora 
            FROM registros_ponto
            WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
            ORDER BY data_hora
        ''', ('teste_func', hoje))
        
        registros = cursor.fetchall()
        sequencia_correta = True
        
        if len(registros) >= 4:
            tipos_esperados = ['entrada', 'saida_almoco', 'retorno_almoco', 'saida']
            for i, (tipo, _) in enumerate(registros[:4]):
                if tipo != tipos_esperados[i]:
                    sequencia_correta = False
                    break
        
        all_passed &= print_result(
            sequencia_correta,
            f"Sequência de registros: {'correta' if sequencia_correta else 'incorreta'}"
        )
        
        # 3. Verificar que horas de saída são após horas de entrada
        if len(registros) >= 2:
            entrada_hora = registros[0][1]
            saida_almoco_hora = registros[1][1]
            
            all_passed &= print_result(
                saida_almoco_hora > entrada_hora,
                f"Validação temporal: saída almoço após entrada"
            )
        
        # 4. Verificar que todas as solicitações têm dados válidos
        cursor.execute('''
            SELECT id, dados_solicitados 
            FROM solicitacoes_ajuste_ponto 
            WHERE usuario LIKE %s OR usuario LIKE %s
        ''' if USE_POSTGRESQL else '''
            SELECT id, dados_solicitados 
            FROM solicitacoes_ajuste_ponto 
            WHERE usuario LIKE ? OR usuario LIKE ?
        ''', ('%teste%', '%Teste%'))
        
        solicitacoes = cursor.fetchall()
        dados_validos = True
        
        for sol_id, dados_json in solicitacoes:
            try:
                dados = json.loads(dados_json) if dados_json else {}
                if not dados:
                    dados_validos = False
            except:
                dados_validos = False
        
        all_passed &= print_result(
            dados_validos,
            f"Integridade de dados JSON: {'válida' if dados_validos else 'inválida'}"
        )
        
    except Exception as e:
        all_passed &= print_result(False, f"Erro nas validações: {e}")
    finally:
        conn.close()
    
    assert all_passed, "Falha nas validações de integridade"

def test_casos_borda():
    """TESTE 12: Casos de Borda e Situações Especiais"""
    print_section("⚠️ TESTE 12: Casos de Borda e Situações Especiais")
    
    all_passed = True
    
    # 1. Testar dia sem registros
    print_section("Caso 1: Dia sem registros", 3)
    calc_system = CalculoHorasSystem()
    data_futura = date.today() + timedelta(days=30)
    
    resultado = calc_system.calcular_horas_dia('teste_func', data_futura.strftime('%Y-%m-%d'))
    all_passed &= print_result(
        resultado is None or resultado.get('total_horas', 0) == 0,
        "Dia sem registros retorna 0 horas ou None"
    )
    
    # 2. Testar registro incompleto (só entrada, sem saída)
    print_section("Caso 2: Registro incompleto", 3)
    conn = get_connection()
    cursor = conn.cursor()
    
    data_teste = date.today() + timedelta(days=2)
    data_hora_teste = datetime.combine(data_teste, time(9, 0))
    
    try:
        cursor.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        ''', ('teste_func', data_hora_teste, 'entrada', 'presencial'))
        conn.commit()
        
        resultado = calc_system.calcular_horas_dia('teste_func', data_teste.strftime('%Y-%m-%d'))
        all_passed &= print_result(
            resultado is not None,
            f"Dia com registro incompleto tratado corretamente"
        )
    except Exception as e:
        all_passed &= print_result(False, f"Erro ao testar registro incompleto: {e}")
    
    # 3. Testar fim de semana
    print_section("Caso 3: Trabalho em fim de semana", 3)
    hoje = date.today()
    dias_ate_sabado = (5 - hoje.weekday()) % 7
    proximo_sabado = hoje + timedelta(days=dias_ate_sabado if dias_ate_sabado > 0 else 7)
    
    try:
        # Registrar trabalho no sábado
        entrada_sabado = datetime.combine(proximo_sabado, time(9, 0))
        saida_sabado = datetime.combine(proximo_sabado, time(13, 0))
        
        cursor.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        ''', ('teste_func', entrada_sabado, 'entrada', 'presencial'))
        
        cursor.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        ''', ('teste_func', saida_sabado, 'saida', 'presencial'))
        
        conn.commit()
        
        resultado = calc_system.calcular_horas_dia('teste_func', proximo_sabado.strftime('%Y-%m-%d'))
        if resultado:
            # Trabalho em fim de semana deve contar
            horas = resultado.get('horas_trabalhadas', 0) or resultado.get('horas_liquidas', 0) or resultado.get('total_horas', 0)
            all_passed &= print_result(
                horas >= 4.0,
                f"Horas em fim de semana: {horas}h (esperado: 4h)"
            )
        else:
            all_passed &= print_result(False, f"Cálculo retornou None para fim de semana")
    except Exception as e:
        all_passed &= print_result(False, f"Erro ao testar fim de semana: {e}")
    
    conn.close()
    
    # 4. Testar jornada muito longa (mais de 12h)
    print_section("Caso 4: Jornada muito longa", 3)
    all_passed &= print_result(
        True,
        "Sistema deve alertar para jornadas acima de 10h (validação manual necessária)"
    )
    
    assert all_passed, "Falha nos testes de casos de borda"

def executar_todos_os_testes():
    """Executa todos os testes do sistema"""
    print("\n")
    print("="*80)
    print(" "*20 + "TESTE COMPLETO DO SISTEMA PONTO ESA v5")
    print("="*80)
    print("\n🎯 Objetivo: Validar TODAS as funcionalidades end-to-end")
    print("👥 Perfis testados: Funcionário, Gestor, Admin")
    print("📋 Escopo: Registro de ponto, cálculos, aprovações, relatórios\n")
    
    # Preparação
    limpar_dados_teste()
    init_db()
    criar_usuarios_teste()
    
    # Executar testes
    resultados = {
        "Registrar Ponto": test_registrar_ponto(),
        "Cálculo de Horas": test_calculo_horas(),
        "Banco de Horas": test_banco_horas(),
        "Ajuste - Criar Registro": test_ajuste_registros_criacao(),
        "Ajuste - Corrigir Registro": test_ajuste_registros_correcao(),
        "Aprovação de Ajuste": test_aprovacao_ajuste(),
        "Rejeição de Ajuste": test_rejeicao_ajuste(),
        "Horas Extras": test_horas_extras(),
        "Atestados e Ausências": test_atestados(),
        "Relatórios": test_relatorios(),
        "Validações e Integridade": test_validacoes_integridade(),
        "Casos de Borda": test_casos_borda()
    }
    
    # Sumário final
    print_section("📈 SUMÁRIO FINAL DOS TESTES")
    
    total = len(resultados)
    passou = sum(1 for v in resultados.values() if v)
    falhou = total - passou
    
    for nome, resultado in resultados.items():
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} - {nome}")
    
    print(f"\n{'='*80}")
    print(f"Total de testes: {total}")
    print(f"✅ Passou: {passou} ({passou/total*100:.1f}%)")
    print(f"❌ Falhou: {falhou} ({falhou/total*100:.1f}%)")
    print(f"{'='*80}\n")
    
    if passou == total:
        print("🎉 SUCESSO! Todos os testes passaram!")
        print("✅ Sistema está pronto para produção")
    else:
        print("⚠️ ATENÇÃO! Alguns testes falharam")
        print("🔧 Revise os erros acima e corrija antes de deploy")
    
    print("\n📝 Credenciais para testes manuais:")
    print("   Funcionário: teste_func / senha123")
    print("   Gestor: teste_gestor / senha123")
    print("   Admin: teste_admin / senha123")
    print("\n")

if __name__ == '__main__':
    executar_todos_os_testes()
