"""
Módulo de Relatórios de Horas Extras - Ponto ExSA
================================================
Gera relatórios detalhados de horas extras trabalhadas.

@author: Pâmella SAR - Expressão Socioambiental
@version: 2.0.0
"""

import os
import sys
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import logging

# Configurar logging
logger = logging.getLogger(__name__)

# Importar conexão com banco
try:
    from database import get_connection, SQL_PLACEHOLDER
except ImportError:
    from ponto_esa_v5.database import get_connection, SQL_PLACEHOLDER


def gerar_relatorio_horas_extras(
    usuario: Optional[str] = None,
    inicio: Optional[str] = None,
    fim: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gera relatório de horas extras com filtros.
    
    Args:
        usuario: Filtrar por usuário específico (None = todos)
        inicio: Data inicial (formato YYYY-MM-DD)
        fim: Data final (formato YYYY-MM-DD)
        status: Filtrar por status (pendente, aprovado, rejeitado, None = todos)
    
    Returns:
        Dict com dados do relatório
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construir query dinamicamente
        query = """
            SELECT h.id, h.usuario, h.data, h.hora_inicio, h.hora_fim,
                   h.total_horas, h.justificativa, h.status,
                   h.data_solicitacao, h.aprovado_por, h.data_aprovacao,
                   u.nome_completo
            FROM solicitacoes_horas_extras h
            LEFT JOIN usuarios u ON h.usuario = u.usuario
            WHERE 1=1
        """
        params = []
        
        if usuario:
            query += f" AND h.usuario = {SQL_PLACEHOLDER}"
            params.append(usuario)
        
        if inicio:
            query += f" AND h.data >= {SQL_PLACEHOLDER}"
            params.append(inicio)
        
        if fim:
            query += f" AND h.data <= {SQL_PLACEHOLDER}"
            params.append(fim)
        
        if status:
            query += f" AND h.status = {SQL_PLACEHOLDER}"
            params.append(status)
        
        query += " ORDER BY h.data DESC, h.hora_inicio"
        
        cursor.execute(query, tuple(params))
        registros = cursor.fetchall()
        
        # Processar resultados
        horas_extras = []
        total_horas = 0
        total_pendentes = 0
        total_aprovadas = 0
        total_rejeitadas = 0
        
        for reg in registros:
            id_, usr, dt, hi, hf, tot_h, just, st, dt_sol, aprov, dt_aprov, nome = reg
            
            # Calcular horas se não tiver total_horas
            if tot_h:
                horas = float(tot_h)
            else:
                try:
                    if isinstance(hi, str):
                        hi = datetime.strptime(hi, '%H:%M:%S' if ':' in hi and hi.count(':') == 2 else '%H:%M').time()
                    if isinstance(hf, str):
                        hf = datetime.strptime(hf, '%H:%M:%S' if ':' in hf and hf.count(':') == 2 else '%H:%M').time()
                    
                    dt_hi = datetime.combine(date.today(), hi)
                    dt_hf = datetime.combine(date.today(), hf)
                    delta = (dt_hf - dt_hi).total_seconds()
                    if delta < 0:
                        delta += 24 * 3600
                    horas = delta / 3600
                except:
                    horas = 0
            
            total_horas += horas
            
            if st == 'pendente':
                total_pendentes += 1
            elif st == 'aprovado':
                total_aprovadas += 1
            elif st == 'rejeitado':
                total_rejeitadas += 1
            
            horas_extras.append({
                'id': id_,
                'usuario': usr,
                'nome_completo': nome or usr,
                'data': dt.strftime('%Y-%m-%d') if isinstance(dt, date) else str(dt),
                'hora_inicio': str(hi)[:5] if hi else '',
                'hora_fim': str(hf)[:5] if hf else '',
                'horas': round(horas, 2),
                'justificativa': just,
                'status': st,
                'data_solicitacao': dt_sol.isoformat() if dt_sol else None,
                'aprovado_por': aprov,
                'data_aprovacao': dt_aprov.isoformat() if dt_aprov else None
            })
        
        conn.close()
        
        return {
            'success': True,
            'horas_extras': horas_extras,
            'horas_extras_detectadas': horas_extras,  # Compatibilidade
            'total_registros': len(horas_extras),
            'total_horas': round(total_horas, 2),
            'total_horas_extras': round(total_horas, 2),  # Compatibilidade
            'total_pendentes': total_pendentes,
            'total_aprovadas': total_aprovadas,
            'total_rejeitadas': total_rejeitadas,
            'periodo': {
                'inicio': inicio,
                'fim': fim
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório de horas extras: {e}")
        if conn:
            conn.close()
        return {
            'success': False,
            'message': str(e),
            'horas_extras': [],
            'horas_extras_detectadas': [],
            'total_horas': 0,
            'total_horas_extras': 0
        }


def gerar_relatorio_por_usuario(
    inicio: Optional[str] = None,
    fim: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gera relatório agregado por usuário.
    
    Args:
        inicio: Data inicial
        fim: Data final
    
    Returns:
        Dict com totais por usuário
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT h.usuario, u.nome_completo,
                   COUNT(*) as total_solicitacoes,
                   SUM(CASE WHEN h.status = 'aprovado' THEN COALESCE(h.total_horas, 0) ELSE 0 END) as horas_aprovadas,
                   SUM(CASE WHEN h.status = 'pendente' THEN 1 ELSE 0 END) as pendentes,
                   SUM(CASE WHEN h.status = 'aprovado' THEN 1 ELSE 0 END) as aprovadas,
                   SUM(CASE WHEN h.status = 'rejeitado' THEN 1 ELSE 0 END) as rejeitadas
            FROM solicitacoes_horas_extras h
            LEFT JOIN usuarios u ON h.usuario = u.usuario
            WHERE 1=1
        """
        params = []
        
        if inicio:
            query += f" AND h.data >= {SQL_PLACEHOLDER}"
            params.append(inicio)
        
        if fim:
            query += f" AND h.data <= {SQL_PLACEHOLDER}"
            params.append(fim)
        
        query += " GROUP BY h.usuario, u.nome_completo ORDER BY horas_aprovadas DESC"
        
        cursor.execute(query, tuple(params))
        resultados = cursor.fetchall()
        
        usuarios = []
        for row in resultados:
            usuarios.append({
                'usuario': row[0],
                'nome_completo': row[1] or row[0],
                'total_solicitacoes': row[2],
                'horas_aprovadas': round(float(row[3] or 0), 2),
                'pendentes': row[4],
                'aprovadas': row[5],
                'rejeitadas': row[6]
            })
        
        conn.close()
        
        return {
            'success': True,
            'usuarios': usuarios,
            'total_usuarios': len(usuarios)
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório por usuário: {e}")
        if conn:
            conn.close()
        return {
            'success': False,
            'message': str(e),
            'usuarios': []
        }


def gerar_relatorio_mensal(
    ano: int = None,
    mes: int = None
) -> Dict[str, Any]:
    """
    Gera relatório mensal de horas extras.
    
    Args:
        ano: Ano do relatório (default: ano atual)
        mes: Mês do relatório (default: mês atual)
    
    Returns:
        Dict com dados mensais
    """
    if not ano:
        ano = date.today().year
    if not mes:
        mes = date.today().month
    
    # Calcular primeiro e último dia do mês
    primeiro_dia = date(ano, mes, 1)
    if mes == 12:
        ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)
    
    return gerar_relatorio_horas_extras(
        inicio=primeiro_dia.strftime('%Y-%m-%d'),
        fim=ultimo_dia.strftime('%Y-%m-%d')
    )


def obter_estatisticas_gerais() -> Dict[str, Any]:
    """
    Obtém estatísticas gerais de horas extras.
    
    Returns:
        Dict com estatísticas
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Total geral
        cursor.execute("SELECT COUNT(*) FROM solicitacoes_horas_extras")
        total = cursor.fetchone()[0]
        
        # Por status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM solicitacoes_horas_extras 
            GROUP BY status
        """)
        por_status = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Média de horas por solicitação aprovada
        cursor.execute("""
            SELECT AVG(total_horas) 
            FROM solicitacoes_horas_extras 
            WHERE status = 'aprovado' AND total_horas IS NOT NULL
        """)
        media = cursor.fetchone()[0]
        
        # Total de horas aprovadas
        cursor.execute("""
            SELECT SUM(total_horas) 
            FROM solicitacoes_horas_extras 
            WHERE status = 'aprovado'
        """)
        total_horas = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'success': True,
            'total_solicitacoes': total,
            'por_status': por_status,
            'media_horas_aprovadas': round(float(media or 0), 2),
            'total_horas_aprovadas': round(float(total_horas or 0), 2)
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        if conn:
            conn.close()
        return {
            'success': False,
            'message': str(e)
        }


__all__ = [
    "gerar_relatorio_horas_extras",
    "gerar_relatorio_por_usuario",
    "gerar_relatorio_mensal",
    "obter_estatisticas_gerais"
]
