"""
Sistema de Cache e Otimização de Performance para Ponto ExSA v5.0
Usa st.cache_data e st.cache_resource para melhorar a velocidade
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Callable
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

# TTL padrão para cache (em segundos)
CACHE_TTL_SHORT = 60  # 1 minuto - dados que mudam frequentemente
CACHE_TTL_MEDIUM = 300  # 5 minutos - dados moderadamente estáveis
CACHE_TTL_LONG = 3600  # 1 hora - dados raramente alterados


def get_cache_key(*args, **kwargs) -> str:
    """Gera uma chave única para cache baseada nos argumentos"""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


@st.cache_data(ttl=CACHE_TTL_MEDIUM)
def cached_query_count(query: str, params: tuple = None, _execute_query: Callable = None) -> int:
    """Cache para queries de contagem (COUNT)"""
    if _execute_query is None:
        return 0
    
    try:
        result = _execute_query(query, params, fetch_one=True)
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Erro em cached_query_count: {e}")
        return 0


@st.cache_data(ttl=CACHE_TTL_SHORT)
def cached_get_usuarios_ativos(_execute_query: Callable) -> List[Dict]:
    """Cache para lista de usuários ativos"""
    try:
        query = """
            SELECT id, usuario, nome, email, tipo, cargo 
            FROM usuarios 
            WHERE ativo = 1 
            ORDER BY nome
        """
        result = _execute_query(query, fetch_all=True)
        if result:
            return [
                {
                    "id": r[0],
                    "usuario": r[1],
                    "nome": r[2],
                    "email": r[3],
                    "tipo": r[4],
                    "cargo": r[5]
                }
                for r in result
            ]
        return []
    except Exception as e:
        logger.error(f"Erro em cached_get_usuarios_ativos: {e}")
        return []


@st.cache_data(ttl=CACHE_TTL_LONG)
def cached_get_configuracoes(_execute_query: Callable) -> Dict[str, str]:
    """Cache para configurações do sistema"""
    try:
        query = "SELECT chave, valor FROM configuracoes"
        result = _execute_query(query, fetch_all=True)
        if result:
            return {r[0]: r[1] for r in result}
        return {}
    except Exception as e:
        logger.error(f"Erro em cached_get_configuracoes: {e}")
        return {}


@st.cache_data(ttl=CACHE_TTL_MEDIUM)
def cached_get_metricas_dashboard(data_ref: str, _execute_query: Callable) -> Dict[str, Any]:
    """Cache para métricas do dashboard do gestor"""
    metricas = {
        "total_usuarios": 0,
        "registros_hoje": 0,
        "ausencias_pendentes": 0,
        "horas_extras_pendentes": 0,
        "atestados_mes": 0,
        "presentes_hoje": 0
    }
    
    try:
        # Total de usuários ativos
        result = _execute_query(
            "SELECT COUNT(*) FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario'",
            fetch_one=True
        )
        if result:
            metricas["total_usuarios"] = result[0]
        
        # Registros hoje
        result = _execute_query(
            "SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = %s",
            (data_ref,), fetch_one=True
        )
        if result:
            metricas["registros_hoje"] = result[0]
        
        # Usuários presentes hoje (distintos)
        result = _execute_query(
            "SELECT COUNT(DISTINCT usuario_id) FROM registros_ponto WHERE DATE(data_hora) = %s",
            (data_ref,), fetch_one=True
        )
        if result:
            metricas["presentes_hoje"] = result[0]
        
        # Ausências pendentes
        result = _execute_query(
            "SELECT COUNT(*) FROM ausencias WHERE status = 'pendente'",
            fetch_one=True
        )
        if result:
            metricas["ausencias_pendentes"] = result[0]
        
        # Horas extras pendentes
        result = _execute_query(
            "SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente'",
            fetch_one=True
        )
        if result:
            metricas["horas_extras_pendentes"] = result[0]
        
        # Atestados do mês
        primeiro_dia_mes = date.today().replace(day=1).strftime("%Y-%m-%d")
        result = _execute_query(
            "SELECT COUNT(*) FROM ausencias WHERE data_inicio >= %s AND tipo LIKE '%%Atestado%%'",
            (primeiro_dia_mes,), fetch_one=True
        )
        if result:
            metricas["atestados_mes"] = result[0]
            
    except Exception as e:
        logger.error(f"Erro em cached_get_metricas_dashboard: {e}")
    
    return metricas


@st.cache_data(ttl=CACHE_TTL_SHORT)
def cached_get_registros_semana(data_fim: str, _execute_query: Callable) -> Dict[str, List]:
    """Cache para registros da última semana (para gráfico)"""
    datas = []
    valores = []
    
    try:
        data_fim_obj = datetime.strptime(data_fim, "%Y-%m-%d").date()
        
        for i in range(6, -1, -1):
            data_check = (data_fim_obj - timedelta(days=i)).strftime("%Y-%m-%d")
            result = _execute_query(
                "SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = %s",
                (data_check,), fetch_one=True
            )
            datas.append((data_fim_obj - timedelta(days=i)).strftime("%d/%m"))
            valores.append(result[0] if result else 0)
            
    except Exception as e:
        logger.error(f"Erro em cached_get_registros_semana: {e}")
    
    return {"datas": datas, "valores": valores}


@st.cache_data(ttl=CACHE_TTL_MEDIUM)
def cached_get_ausencias_por_tipo(data_inicio_mes: str, _execute_query: Callable) -> Dict[str, int]:
    """Cache para ausências por tipo no mês"""
    ausencias = {}
    
    try:
        result = _execute_query(
            """SELECT tipo, COUNT(*) as total FROM ausencias 
               WHERE data_inicio >= %s 
               GROUP BY tipo""",
            (data_inicio_mes,), fetch_all=True
        )
        if result:
            for row in result:
                ausencias[row[0][:25]] = row[1]  # Truncar nome longo
                
    except Exception as e:
        logger.error(f"Erro em cached_get_ausencias_por_tipo: {e}")
    
    return ausencias


@st.cache_data(ttl=CACHE_TTL_SHORT)
def cached_get_registros_usuario(usuario: str, data_inicio: str, data_fim: str, 
                                  _execute_query: Callable) -> List[tuple]:
    """Cache para registros de um usuário em um período"""
    try:
        query = """
            SELECT id, usuario, data_hora, tipo, latitude, longitude, localizacao 
            FROM registros_ponto 
            WHERE usuario = %s 
            AND DATE(data_hora) BETWEEN %s AND %s 
            ORDER BY data_hora
        """
        result = _execute_query(query, (usuario, data_inicio, data_fim), fetch_all=True)
        return result if result else []
        
    except Exception as e:
        logger.error(f"Erro em cached_get_registros_usuario: {e}")
        return []


@st.cache_data(ttl=CACHE_TTL_SHORT)
def cached_get_saldo_banco_horas(usuario: str, _execute_query: Callable) -> float:
    """Cache para saldo do banco de horas de um usuário"""
    try:
        result = _execute_query(
            "SELECT saldo_minutos FROM banco_horas WHERE usuario = %s",
            (usuario,), fetch_one=True
        )
        return result[0] if result else 0
        
    except Exception as e:
        logger.error(f"Erro em cached_get_saldo_banco_horas: {e}")
        return 0


def invalidar_cache_usuario(usuario: str):
    """Invalida caches relacionados a um usuário específico"""
    # Limpa caches que podem conter dados do usuário
    cached_get_registros_usuario.clear()
    cached_get_saldo_banco_horas.clear()
    cached_get_metricas_dashboard.clear()
    logger.info(f"Cache invalidado para usuário: {usuario}")


def invalidar_cache_geral():
    """Invalida todos os caches"""
    cached_query_count.clear()
    cached_get_usuarios_ativos.clear()
    cached_get_configuracoes.clear()
    cached_get_metricas_dashboard.clear()
    cached_get_registros_semana.clear()
    cached_get_ausencias_por_tipo.clear()
    cached_get_registros_usuario.clear()
    cached_get_saldo_banco_horas.clear()
    logger.info("Todos os caches foram invalidados")


class PerformanceMonitor:
    """Monitor de performance para identificar gargalos"""
    
    def __init__(self):
        if 'performance_log' not in st.session_state:
            st.session_state.performance_log = []
    
    def start_timer(self, operation: str) -> datetime:
        """Inicia um timer para uma operação"""
        return datetime.now()
    
    def end_timer(self, operation: str, start_time: datetime):
        """Finaliza o timer e registra o tempo"""
        elapsed = (datetime.now() - start_time).total_seconds() * 1000  # ms
        
        log_entry = {
            "operation": operation,
            "time_ms": elapsed,
            "timestamp": datetime.now().isoformat()
        }
        
        st.session_state.performance_log.append(log_entry)
        
        # Manter apenas os últimos 100 registros
        if len(st.session_state.performance_log) > 100:
            st.session_state.performance_log = st.session_state.performance_log[-100:]
        
        # Alertar se operação demorar muito
        if elapsed > 1000:  # Mais de 1 segundo
            logger.warning(f"Operação lenta: {operation} ({elapsed:.0f}ms)")
        
        return elapsed
    
    def get_slow_operations(self, threshold_ms: float = 500) -> List[Dict]:
        """Retorna operações que excederam o threshold"""
        return [
            log for log in st.session_state.performance_log 
            if log['time_ms'] > threshold_ms
        ]
    
    def get_average_time(self, operation: str) -> float:
        """Retorna tempo médio de uma operação"""
        times = [
            log['time_ms'] for log in st.session_state.performance_log 
            if log['operation'] == operation
        ]
        return sum(times) / len(times) if times else 0


# Dicas de otimização de queries
QUERY_OPTIMIZATION_TIPS = """
### 🚀 Dicas de Performance para PostgreSQL/Neon:

1. **Índices recomendados** (executar no banco):
```sql
-- Índice para buscas por data
CREATE INDEX IF NOT EXISTS idx_registros_ponto_data 
ON registros_ponto(DATE(data_hora));

-- Índice para buscas por usuário
CREATE INDEX IF NOT EXISTS idx_registros_ponto_usuario 
ON registros_ponto(usuario);

-- Índice composto para relatórios
CREATE INDEX IF NOT EXISTS idx_registros_ponto_usuario_data 
ON registros_ponto(usuario, DATE(data_hora));

-- Índice para ausências pendentes
CREATE INDEX IF NOT EXISTS idx_ausencias_status 
ON ausencias(status);

-- Índice para horas extras pendentes
CREATE INDEX IF NOT EXISTS idx_solicitacoes_he_status 
ON solicitacoes_horas_extras(status);
```

2. **Connection Pooling**: Usar pooler do Neon (-pooler no hostname)

3. **Lazy Loading**: Carregar dados sob demanda, não todos de uma vez

4. **Paginação**: Limitar resultados com LIMIT/OFFSET

5. **Cache**: Usar st.cache_data para dados que não mudam frequentemente
"""


def criar_indices_otimizacao(execute_query_func: Callable) -> bool:
    """Cria índices para otimização de performance"""
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_registros_ponto_data ON registros_ponto(DATE(data_hora))",
        "CREATE INDEX IF NOT EXISTS idx_registros_ponto_usuario ON registros_ponto(usuario)",
        "CREATE INDEX IF NOT EXISTS idx_registros_ponto_usuario_data ON registros_ponto(usuario, DATE(data_hora))",
        "CREATE INDEX IF NOT EXISTS idx_ausencias_status ON ausencias(status)",
        "CREATE INDEX IF NOT EXISTS idx_solicitacoes_he_status ON solicitacoes_horas_extras(status)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_ativo ON usuarios(ativo)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_tipo ON usuarios(tipo)"
    ]
    
    sucesso = True
    for idx in indices:
        try:
            execute_query_func(idx)
            logger.info(f"Índice criado/verificado: {idx[:50]}...")
        except Exception as e:
            logger.error(f"Erro ao criar índice: {e}")
            sucesso = False
    
    return sucesso
