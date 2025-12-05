"""
Sistema de Distribuição de Horas por Projeto - Ponto ExSA
=========================================================
Calcula e exibe a distribuição de horas trabalhadas por projeto.
Mostra percentuais do tempo total dedicado a cada projeto.

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from database import get_connection, SQL_PLACEHOLDER

logger = logging.getLogger(__name__)


class HorasProjetoSystem:
    """
    Sistema de distribuição e análise de horas por projeto.
    Permite visualizar quanto tempo (em horas e percentual) foi dedicado a cada projeto.
    """
    
    def __init__(self):
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Garante que as tabelas necessárias existem."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Tabela de alocação de horas por projeto (opcional, para ajustes manuais)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS horas_projeto (
                    id SERIAL PRIMARY KEY,
                    usuario TEXT NOT NULL,
                    projeto_id INTEGER,
                    projeto_nome TEXT,
                    data DATE NOT NULL,
                    horas REAL NOT NULL DEFAULT 0,
                    percentual REAL,
                    fonte TEXT DEFAULT 'registro',
                    observacao TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Índices para performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_horas_projeto_usuario_data 
                ON horas_projeto(usuario, data)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_horas_projeto_projeto 
                ON horas_projeto(projeto_id)
            """)
            
            conn.commit()
            logger.info("Tabelas de horas por projeto verificadas/criadas")
            
        except Exception as e:
            logger.error(f"Erro ao criar tabelas de horas por projeto: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def calcular_horas_por_projeto_periodo(
        self, 
        usuario: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None
    ) -> Dict:
        """
        Calcula a distribuição de horas por projeto em um período.
        
        Args:
            usuario: Username do funcionário (None para todos)
            data_inicio: Data início no formato YYYY-MM-DD
            data_fim: Data fim no formato YYYY-MM-DD
            
        Returns:
            Dict com:
            - total_horas: Total de horas no período
            - projetos: Lista de dicts com nome, horas, percentual
            - por_dia: Detalhamento diário (opcional)
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Query para somar horas por projeto baseado nos registros de ponto
            query = """
                WITH intervalos AS (
                    SELECT 
                        r1.usuario,
                        r1.projeto,
                        DATE(r1.data_hora) as data,
                        r1.data_hora as inicio,
                        (
                            SELECT MIN(r2.data_hora) 
                            FROM registros_ponto r2 
                            WHERE r2.usuario = r1.usuario 
                            AND r2.data_hora > r1.data_hora
                            AND DATE(r2.data_hora) = DATE(r1.data_hora)
                            AND LOWER(r2.tipo) IN ('fim', 'saída', 'saida', 'saída almoço', 'saida almoco')
                        ) as fim
                    FROM registros_ponto r1
                    WHERE LOWER(r1.tipo) IN ('início', 'inicio', 'retorno almoço', 'retorno almoco')
            """
            
            params = []
            
            if usuario:
                query += f" AND r1.usuario = {SQL_PLACEHOLDER}"
                params.append(usuario)
            
            if data_inicio:
                query += f" AND DATE(r1.data_hora) >= {SQL_PLACEHOLDER}"
                params.append(data_inicio)
            
            if data_fim:
                query += f" AND DATE(r1.data_hora) <= {SQL_PLACEHOLDER}"
                params.append(data_fim)
            
            query += """
                )
                SELECT 
                    COALESCE(projeto, 'Sem Projeto') as projeto,
                    SUM(
                        EXTRACT(EPOCH FROM (fim - inicio)) / 3600.0
                    ) as horas
                FROM intervalos
                WHERE fim IS NOT NULL
                GROUP BY projeto
                ORDER BY horas DESC
            """
            
            cursor.execute(query, params)
            resultados = cursor.fetchall()
            
            # Calcular totais e percentuais
            projetos = []
            total_horas = 0
            
            for row in resultados:
                projeto_nome = row[0] or 'Sem Projeto'
                horas = float(row[1]) if row[1] else 0
                total_horas += horas
                projetos.append({
                    'projeto': projeto_nome,
                    'horas': round(horas, 2),
                    'percentual': 0  # Será calculado depois
                })
            
            # Calcular percentuais
            for p in projetos:
                if total_horas > 0:
                    p['percentual'] = round((p['horas'] / total_horas) * 100, 1)
            
            return {
                'success': True,
                'total_horas': round(total_horas, 2),
                'projetos': projetos,
                'periodo': {
                    'inicio': data_inicio,
                    'fim': data_fim
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular horas por projeto: {e}")
            return {
                'success': False,
                'message': str(e),
                'total_horas': 0,
                'projetos': []
            }
        finally:
            conn.close()
    
    def calcular_horas_por_projeto_mes(
        self,
        usuario: Optional[str] = None,
        ano: int = None,
        mes: int = None
    ) -> Dict:
        """
        Calcula distribuição de horas por projeto para um mês específico.
        
        Args:
            usuario: Username do funcionário (None para todos)
            ano: Ano (default: ano atual)
            mes: Mês (default: mês atual)
            
        Returns:
            Dict com total_horas, projetos com percentuais
        """
        if ano is None:
            ano = date.today().year
        if mes is None:
            mes = date.today().month
        
        # Calcular primeiro e último dia do mês
        primeiro_dia = date(ano, mes, 1)
        if mes == 12:
            ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)
        
        resultado = self.calcular_horas_por_projeto_periodo(
            usuario=usuario,
            data_inicio=primeiro_dia.strftime('%Y-%m-%d'),
            data_fim=ultimo_dia.strftime('%Y-%m-%d')
        )
        
        resultado['mes'] = mes
        resultado['ano'] = ano
        resultado['mes_nome'] = primeiro_dia.strftime('%B/%Y')
        
        return resultado
    
    def calcular_distribuicao_diaria(
        self,
        usuario: str,
        data: str
    ) -> Dict:
        """
        Calcula distribuição de horas por projeto para um dia específico.
        
        Args:
            usuario: Username do funcionário
            data: Data no formato YYYY-MM-DD
            
        Returns:
            Dict com horas por projeto naquele dia
        """
        return self.calcular_horas_por_projeto_periodo(
            usuario=usuario,
            data_inicio=data,
            data_fim=data
        )
    
    def obter_relatorio_mensal_todos_funcionarios(
        self,
        ano: int = None,
        mes: int = None
    ) -> Dict:
        """
        Gera relatório de horas por projeto para todos os funcionários.
        
        Returns:
            Dict com dados de todos os funcionários
        """
        if ano is None:
            ano = date.today().year
        if mes is None:
            mes = date.today().month
        
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Buscar todos os funcionários ativos
            cursor.execute("""
                SELECT usuario, nome_completo 
                FROM usuarios 
                WHERE tipo = 'funcionario' AND ativo = 1
                ORDER BY nome_completo
            """)
            funcionarios = cursor.fetchall()
            
            relatorio = {
                'success': True,
                'ano': ano,
                'mes': mes,
                'funcionarios': [],
                'totais_por_projeto': {},
                'total_geral': 0
            }
            
            for func in funcionarios:
                usuario = func[0]
                nome = func[1] or usuario
                
                dados_func = self.calcular_horas_por_projeto_mes(
                    usuario=usuario,
                    ano=ano,
                    mes=mes
                )
                
                relatorio['funcionarios'].append({
                    'usuario': usuario,
                    'nome': nome,
                    'total_horas': dados_func.get('total_horas', 0),
                    'projetos': dados_func.get('projetos', [])
                })
                
                # Acumular totais por projeto
                for proj in dados_func.get('projetos', []):
                    nome_proj = proj['projeto']
                    if nome_proj not in relatorio['totais_por_projeto']:
                        relatorio['totais_por_projeto'][nome_proj] = 0
                    relatorio['totais_por_projeto'][nome_proj] += proj['horas']
                
                relatorio['total_geral'] += dados_func.get('total_horas', 0)
            
            # Calcular percentuais dos totais
            relatorio['projetos_consolidados'] = []
            for nome_proj, horas in sorted(
                relatorio['totais_por_projeto'].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentual = 0
                if relatorio['total_geral'] > 0:
                    percentual = round((horas / relatorio['total_geral']) * 100, 1)
                
                relatorio['projetos_consolidados'].append({
                    'projeto': nome_proj,
                    'horas': round(horas, 2),
                    'percentual': percentual
                })
            
            return relatorio
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório mensal: {e}")
            return {
                'success': False,
                'message': str(e),
                'funcionarios': []
            }
        finally:
            conn.close()
    
    def obter_evolucao_projeto(
        self,
        projeto_nome: str,
        meses: int = 6
    ) -> Dict:
        """
        Obtém evolução de horas de um projeto nos últimos meses.
        
        Args:
            projeto_nome: Nome do projeto
            meses: Quantidade de meses para analisar
            
        Returns:
            Dict com evolução mensal
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            data_inicio = date.today() - timedelta(days=meses * 30)
            
            query = f"""
                WITH intervalos AS (
                    SELECT 
                        r1.projeto,
                        DATE_TRUNC('month', r1.data_hora) as mes,
                        r1.data_hora as inicio,
                        (
                            SELECT MIN(r2.data_hora) 
                            FROM registros_ponto r2 
                            WHERE r2.usuario = r1.usuario 
                            AND r2.data_hora > r1.data_hora
                            AND DATE(r2.data_hora) = DATE(r1.data_hora)
                            AND LOWER(r2.tipo) IN ('fim', 'saída', 'saida')
                        ) as fim
                    FROM registros_ponto r1
                    WHERE LOWER(r1.tipo) IN ('início', 'inicio', 'retorno almoço', 'retorno almoco')
                    AND r1.projeto = {SQL_PLACEHOLDER}
                    AND r1.data_hora >= {SQL_PLACEHOLDER}
                )
                SELECT 
                    TO_CHAR(mes, 'YYYY-MM') as mes_ano,
                    SUM(EXTRACT(EPOCH FROM (fim - inicio)) / 3600.0) as horas
                FROM intervalos
                WHERE fim IS NOT NULL
                GROUP BY mes
                ORDER BY mes
            """
            
            cursor.execute(query, (projeto_nome, data_inicio))
            resultados = cursor.fetchall()
            
            evolucao = []
            for row in resultados:
                evolucao.append({
                    'mes': row[0],
                    'horas': round(float(row[1]) if row[1] else 0, 2)
                })
            
            return {
                'success': True,
                'projeto': projeto_nome,
                'evolucao': evolucao
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter evolução do projeto: {e}")
            return {
                'success': False,
                'message': str(e),
                'evolucao': []
            }
        finally:
            conn.close()


def format_horas_projeto(horas: float) -> str:
    """Formata horas para exibição."""
    if horas == 0:
        return "0h"
    
    h = int(horas)
    m = int((horas - h) * 60)
    
    if m > 0:
        return f"{h}h {m}min"
    return f"{h}h"


def format_percentual(percentual: float) -> str:
    """Formata percentual para exibição."""
    return f"{percentual:.1f}%"


# Cores para gráficos de projetos - paleta harmoniosa com tons azuis
CORES_PROJETOS = [
    '#667eea',  # Roxo-azul (cor principal do sistema)
    '#28a745',  # Verde
    '#17a2b8',  # Ciano/Teal
    '#6f42c1',  # Roxo
    '#fd7e14',  # Laranja
    '#20c997',  # Verde-água
    '#007bff',  # Azul
    '#6c757d',  # Cinza
    '#5a67d8',  # Indigo
    '#38b2ac',  # Teal escuro
]


def get_cor_projeto(index: int) -> str:
    """Retorna uma cor para o projeto baseado no índice."""
    return CORES_PROJETOS[index % len(CORES_PROJETOS)]


__all__ = [
    'HorasProjetoSystem',
    'format_horas_projeto',
    'format_percentual',
    'get_cor_projeto',
    'CORES_PROJETOS'
]
