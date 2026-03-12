"""
Módulo de Banco de Dados Otimizado para Ponto ExSA v5.0
Usa o Connection Pool CENTRALIZADO de database.py + Cache Streamlit para queries frequentes.

NOTA: NÃO cria pool próprio — reutiliza o pool de database.py via get_connection/return_connection.
"""

import os
import streamlit as st
from datetime import datetime, date, timedelta
from typing import Any, Optional, List, Dict, Tuple
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Reutilizar o pool centralizado
try:
    from database import get_connection, return_connection, SQL_PLACEHOLDER
except ImportError:
    from ponto_esa_v5.database import get_connection, return_connection, SQL_PLACEHOLDER


@contextmanager
def get_pooled_connection():
    """Context manager para conexão do pool centralizado (devolve ao pool ao final)."""
    conn = get_connection()
    try:
        yield conn
    finally:
        return_connection(conn)


def execute_query_optimized(query: str, params: tuple = None, 
                            fetch_one: bool = False, 
                            fetch_all: bool = True) -> Any:
    """Executa query usando conexão do pool"""
    with get_pooled_connection() as conn:
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Erro na query: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()


def execute_update_optimized(query: str, params: tuple = None) -> bool:
    """Executa UPDATE/INSERT/DELETE usando conexão do pool"""
    with get_pooled_connection() as conn:
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro no update: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()


# ============== FUNÇÕES COM CACHE ==============

@st.cache_data(ttl=300)  # Cache de 5 minutos
def get_total_usuarios_ativos() -> int:
    """Retorna total de usuários ativos (com cache)"""
    try:
        result = execute_query_optimized(
            "SELECT COUNT(*) FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario'",
            fetch_one=True
        )
        return result[0] if result else 0
    except Exception as e:
        logger.debug(f"Falha ao obter total de usuários ativos: {e}")
        return 0


@st.cache_data(ttl=60)  # Cache de 1 minuto
def get_registros_hoje(data_hoje: str) -> int:
    """Retorna total de registros do dia (com cache)"""
    try:
        result = execute_query_optimized(
            f"SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = {SQL_PLACEHOLDER}",
            (data_hoje,),
            fetch_one=True
        )
        return result[0] if result else 0
    except Exception as e:
        logger.debug(f"Falha ao obter registros de hoje: {e}")
        return 0


@st.cache_data(ttl=60)  # Cache de 1 minuto
def get_presentes_hoje(data_hoje: str) -> int:
    """Retorna usuários distintos que registraram ponto hoje (com cache)"""
    try:
        result = execute_query_optimized(
            f"SELECT COUNT(DISTINCT usuario) FROM registros_ponto WHERE DATE(data_hora) = {SQL_PLACEHOLDER}",
            (data_hoje,),
            fetch_one=True
        )
        return result[0] if result else 0
    except Exception as e:
        logger.debug(f"Falha ao obter presentes hoje: {e}")
        return 0


@st.cache_data(ttl=120)  # Cache de 2 minutos
def get_pendencias() -> Dict[str, int]:
    """Retorna contagem de pendências (com cache)"""
    pendencias = {"ausencias": 0, "horas_extras": 0}
    try:
        result = execute_query_optimized(
            "SELECT COUNT(*) FROM ausencias WHERE status = 'pendente'",
            fetch_one=True
        )
        if result:
            pendencias["ausencias"] = result[0]
        
        result = execute_query_optimized(
            "SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente'",
            fetch_one=True
        )
        if result:
            pendencias["horas_extras"] = result[0]
    except Exception as e:
        logger.debug(f"Falha ao obter pendências: {e}")
    return pendencias


@st.cache_data(ttl=300)  # Cache de 5 minutos
def get_lista_usuarios_ativos() -> List[Dict]:
    """Retorna lista de usuários ativos (com cache)"""
    try:
        result = execute_query_optimized(
            "SELECT id, usuario, nome_completo, tipo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo"
        )
        if result:
            return [
                {"id": r[0], "usuario": r[1], "nome": r[2], "tipo": r[3]}
                for r in result
            ]
    except Exception as e:
        logger.debug(f"Falha ao obter lista de usuários ativos: {e}")
    return []


@st.cache_data(ttl=600)  # Cache de 10 minutos
def get_configuracoes_sistema() -> Dict[str, str]:
    """Retorna configurações do sistema (com cache)"""
    try:
        result = execute_query_optimized(
            "SELECT chave, valor FROM configuracoes"
        )
        if result:
            return {r[0]: r[1] for r in result}
    except Exception as e:
        logger.debug(f"Falha ao obter configurações do sistema: {e}")
    return {}


@st.cache_data(ttl=60)  # Cache de 1 minuto
def get_registros_semana(data_fim: str) -> Dict[str, List]:
    """Retorna registros dos últimos 7 dias para gráfico (com cache)"""
    datas = []
    valores = []
    
    try:
        data_fim_obj = datetime.strptime(data_fim, "%Y-%m-%d").date()
        
        for i in range(6, -1, -1):
            data_check = (data_fim_obj - timedelta(days=i)).strftime("%Y-%m-%d")
            result = execute_query_optimized(
                f"SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = {SQL_PLACEHOLDER}",
                (data_check,),
                fetch_one=True
            )
            datas.append((data_fim_obj - timedelta(days=i)).strftime("%d/%m"))
            valores.append(result[0] if result else 0)
    except Exception as e:
        logger.error(f"Erro em get_registros_semana: {e}")
    
    return {"datas": datas, "valores": valores}


@st.cache_data(ttl=120)  # Cache de 2 minutos
def get_ausencias_por_tipo(data_inicio_mes: str) -> Dict[str, int]:
    """Retorna ausências agrupadas por tipo (com cache)"""
    ausencias = {}
    try:
        result = execute_query_optimized(
            f"""SELECT tipo, COUNT(*) as total FROM ausencias 
               WHERE data_inicio >= {SQL_PLACEHOLDER} 
               GROUP BY tipo""",
            (data_inicio_mes,)
        )
        if result:
            for row in result:
                ausencias[row[0][:25]] = row[1]
    except Exception as e:
        logger.debug(f"Falha ao obter ausências por tipo: {e}")
    return ausencias


def invalidar_caches():
    """Invalida todos os caches (chamar após alterações importantes)"""
    get_total_usuarios_ativos.clear()
    get_registros_hoje.clear()
    get_presentes_hoje.clear()
    get_pendencias.clear()
    get_lista_usuarios_ativos.clear()
    get_configuracoes_sistema.clear()
    get_registros_semana.clear()
    get_ausencias_por_tipo.clear()
    logger.info("Todos os caches foram invalidados")


# ============== MÉTRICAS DO DASHBOARD (OTIMIZADO) ==============

def get_metricas_dashboard_otimizado() -> Dict[str, Any]:
    """Retorna todas as métricas do dashboard de uma vez (otimizado)"""
    hoje = date.today().strftime("%Y-%m-%d")
    primeiro_dia_mes = date.today().replace(day=1).strftime("%Y-%m-%d")
    
    # Usar funções com cache
    total_usuarios = get_total_usuarios_ativos()
    registros_hoje = get_registros_hoje(hoje)
    presentes_hoje = get_presentes_hoje(hoje)
    pendencias = get_pendencias()
    
    # Atestados do mês
    atestados_mes = 0
    try:
        result = execute_query_optimized(
            f"SELECT COUNT(*) FROM ausencias WHERE data_inicio >= {SQL_PLACEHOLDER} AND tipo LIKE '%%Atestado%%'",
            (primeiro_dia_mes,),
            fetch_one=True
        )
        if result:
            atestados_mes = result[0]
    except Exception as e:
        logger.debug(f"Falha ao obter atestados do mês: {e}")
    
    return {
        "total_usuarios": total_usuarios,
        "registros_hoje": registros_hoje,
        "presentes_hoje": presentes_hoje,
        "ausencias_pendentes": pendencias["ausencias"],
        "horas_extras_pendentes": pendencias["horas_extras"],
        "pendencias_total": pendencias["ausencias"] + pendencias["horas_extras"],
        "atestados_mes": atestados_mes,
        "taxa_presenca": (presentes_hoje / total_usuarios * 100) if total_usuarios > 0 else 0
    }


# ============== CRIAR ÍNDICES PARA OTIMIZAÇÃO ==============

def criar_indices_performance():
    """Cria índices no banco para melhorar performance das queries"""
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_registros_data ON registros_ponto(DATE(data_hora))",
        "CREATE INDEX IF NOT EXISTS idx_registros_usuario ON registros_ponto(usuario)",
        "CREATE INDEX IF NOT EXISTS idx_registros_usuario_data ON registros_ponto(usuario, DATE(data_hora))",
        "CREATE INDEX IF NOT EXISTS idx_ausencias_status ON ausencias(status)",
        "CREATE INDEX IF NOT EXISTS idx_ausencias_usuario ON ausencias(usuario)",
        "CREATE INDEX IF NOT EXISTS idx_he_status ON solicitacoes_horas_extras(status)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo)",
    ]
    
    sucesso = 0
    for idx_sql in indices:
        try:
            execute_update_optimized(idx_sql)
            sucesso += 1
        except Exception as e:
            logger.warning(f"Índice já existe ou erro: {e}")
    
    logger.info(f"Índices criados/verificados: {sucesso}/{len(indices)}")
    return sucesso


# ============== TESTE DE PERFORMANCE ==============

def testar_performance():
    """Testa performance das conexões"""
    import time
    
    resultados = {}
    
    # Teste 1: Conexão simples (lenta)
    start = time.time()
    from database import get_connection
    conn = get_connection()
    return_connection(conn)
    resultados["conexao_simples"] = (time.time() - start) * 1000
    
    # Teste 2: Conexão do pool (rápida)
    start = time.time()
    with get_pooled_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
    resultados["conexao_pool"] = (time.time() - start) * 1000
    
    # Teste 3: Query com cache (primeira vez)
    start = time.time()
    get_total_usuarios_ativos()
    resultados["query_cache_miss"] = (time.time() - start) * 1000
    
    # Teste 4: Query com cache (segunda vez - do cache)
    start = time.time()
    get_total_usuarios_ativos()
    resultados["query_cache_hit"] = (time.time() - start) * 1000
    
    return resultados


# ============== CACHE PARA BADGES DO MENU FUNCIONÁRIO ==============

@st.cache_data(ttl=60)  # Cache de 60 segundos (aumentado para reduzir queries)
def get_notificacoes_funcionario(usuario: str) -> Dict[str, int]:
    """Retorna contagens de notificações para badges do menu (com cache).
    OTIMIZADO: Uma única query com UNION ALL ao invés de 3 queries separadas.
    """
    notif = {
        "he_aprovar": 0,
        "correcoes_pendentes": 0,
        "atestados_pendentes": 0,
        "total": 0
    }
    
    try:
        # Uma única query para todas as contagens
        query = f"""
            SELECT 'he' as tipo, COUNT(*) as cnt FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
            UNION ALL
            SELECT 'corr' as tipo, COUNT(*) as cnt FROM solicitacoes_correcao_registro 
            WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
            UNION ALL
            SELECT 'atest' as tipo, COUNT(*) as cnt FROM atestado_horas 
            WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
        """
        results = execute_query_optimized(query, (usuario, usuario, usuario))
        
        if results:
            for row in results:
                tipo, cnt = row[0], row[1]
                if tipo == 'he':
                    notif["he_aprovar"] = cnt
                elif tipo == 'corr':
                    notif["correcoes_pendentes"] = cnt
                elif tipo == 'atest':
                    notif["atestados_pendentes"] = cnt
        
        notif["total"] = notif["he_aprovar"] + notif["correcoes_pendentes"] + notif["atestados_pendentes"]
        
    except Exception as e:
        logger.error(f"Erro em get_notificacoes_funcionario: {e}")
    
    return notif


@st.cache_data(ttl=30)  # Cache de 30 segundos
def get_solicitacoes_he_pendentes(usuario: str) -> List[Dict]:
    """Retorna detalhes das solicitações de HE pendentes para aprovar (com cache)"""
    try:
        result = execute_query_optimized(
            f"""SELECT id, usuario, data, hora_inicio, hora_fim, total_horas, justificativa, data_solicitacao
               FROM solicitacoes_horas_extras 
               WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
               ORDER BY data_solicitacao DESC""",
            (usuario,)
        )
        if result:
            return [
                {
                    "id": r[0], "usuario": r[1], "data": r[2], 
                    "hora_inicio": r[3], "hora_fim": r[4], 
                    "total_horas": r[5], "justificativa": r[6],
                    "data_solicitacao": r[7]
                }
                for r in result
            ]
    except Exception as e:
        logger.error(f"Erro em get_solicitacoes_he_pendentes: {e}")
    return []


@st.cache_data(ttl=30)  # Cache de 30 segundos
def get_hora_extra_em_andamento(usuario: str) -> Optional[Dict]:
    """Verifica se há hora extra em andamento (com cache)"""
    try:
        result = execute_query_optimized(
            f"""SELECT id, data, hora_inicio, justificativa 
               FROM solicitacoes_horas_extras 
               WHERE usuario = {SQL_PLACEHOLDER} AND status = 'em_andamento'
               ORDER BY data DESC, hora_inicio DESC
               LIMIT 1""",
            (usuario,),
            fetch_one=True
        )
        if result:
            return {
                "id": result[0],
                "data": result[1],
                "hora_inicio": result[2],
                "justificativa": result[3]
            }
    except Exception as e:
        logger.error(f"Erro em get_hora_extra_em_andamento: {e}")
    return None


def invalidar_cache_funcionario(usuario: str):
    """Invalida caches específicos do funcionário"""
    get_notificacoes_funcionario.clear()
    get_hora_extra_em_andamento.clear()
    logger.info(f"Cache do funcionário {usuario} invalidado")


if __name__ == "__main__":
    # Teste
    print("🔧 Testando módulo de banco otimizado...")
    
    resultados = testar_performance()
    
    print("\n📊 Resultados de Performance:")
    print(f"  Conexão simples: {resultados['conexao_simples']:.2f}ms")
    print(f"  Conexão pool:    {resultados['conexao_pool']:.2f}ms")
    print(f"  Query (1ª vez):  {resultados['query_cache_miss']:.2f}ms")
    print(f"  Query (cache):   {resultados['query_cache_hit']:.2f}ms")
    
    print("\n✅ Criando índices de performance...")
    criar_indices_performance()
