"""
Sistema de Cálculo de Jornada Semanal com Hora Extra
Estende o sistema jornada_semanal_system.py com funcionalidades de cálculo
"""

import os
import logging
from datetime import datetime, timedelta, time

# Verificar se usa PostgreSQL e importar o módulo correto
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'

if USE_POSTGRESQL:
    from database_postgresql import get_connection, SQL_PLACEHOLDER
else:
    from database import get_connection, SQL_PLACEHOLDER

from jornada_semanal_system import obter_jornada_do_dia, obter_jornada_usuario

logger = logging.getLogger(__name__)


class JornadaSemanalCalculoSystem:
    """Sistema para cálculos de hora extra baseado em jornada semanal variável"""
    
    @staticmethod
    def obter_pontos_dia(usuario, data):
        """
        Obtém pontos registrados em um dia específico
        
        Args:
            usuario: Nome de usuário
            data: datetime.date ou datetime.datetime
        
        Returns:
            list: Lista com pontos do dia: [
                {'id': int, 'tipo': str, 'data_hora': str, 'timestamp': datetime},
                ...
            ]
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Converter para date se for datetime
        if isinstance(data, datetime):
            data_str = data.strftime('%Y-%m-%d')
        else:
            data_str = data.strftime('%Y-%m-%d')
        
        # Buscar pontos do dia (tipo: Início, Intermediário, Fim)
        query = f"""
            SELECT id, tipo, data_hora
            FROM registros_ponto
            WHERE usuario = {SQL_PLACEHOLDER}
            AND DATE(data_hora) = {SQL_PLACEHOLDER}
            ORDER BY data_hora ASC
        """
        
        try:
            cursor.execute(query, (usuario, data_str))
            resultados = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Erro ao obter pontos do dia: {e}")
            resultados = []
        finally:
            conn.close()
        
        # Processar resultados
        pontos = []
        for row in resultados:
            ponto_id, tipo, data_hora_str = row
            
            # Parsear data_hora
            try:
                # Tentar diferentes formatos
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        dt = datetime.strptime(data_hora_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    # Se nenhum formato funcionou, usar parsing ISO
                    dt = datetime.fromisoformat(data_hora_str.replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Erro ao parsear data_hora {data_hora_str}: {e}")
                continue
            
            pontos.append({
                'id': ponto_id,
                'tipo': tipo,
                'data_hora': data_hora_str,
                'timestamp': dt
            })
        
        return pontos
    
    @staticmethod
    def calcular_horas_esperadas_dia(usuario, data):
        """
        Calcula quantas horas o funcionário DEVERIA trabalhar em um dia
        
        Cálculo: (hora_fim - hora_inicio) - intervalo_minutos
        Exemplo: 18:00 - 08:00 = 10h, intervalo 60min = 9h efetivas
        
        Args:
            usuario: Nome de usuário
            data: datetime.date ou datetime.datetime
        
        Returns:
            dict: {
                'trabalha': bool,
                'horas_esperadas': float,  # em horas
                'horas_esperadas_minutos': int,  # total em minutos
                'horario_inicio': str,
                'horario_fim': str,
                'intervalo_minutos': int
            }
        """
        jornada_dia = obter_jornada_do_dia(usuario, data)
        
        if not jornada_dia:
            return {
                'trabalha': False,
                'horas_esperadas': 0.0,
                'horas_esperadas_minutos': 0,
                'horario_inicio': None,
                'horario_fim': None,
                'intervalo_minutos': 0
            }
        
        if not jornada_dia.get('trabalha', False):
            return {
                'trabalha': False,
                'horas_esperadas': 0.0,
                'horas_esperadas_minutos': 0,
                'horario_inicio': None,
                'horario_fim': None,
                'intervalo_minutos': 0
            }
        
        # Parsear horários
        try:
            hora_inicio = datetime.strptime(jornada_dia['inicio'], '%H:%M').time()
            hora_fim = datetime.strptime(jornada_dia['fim'], '%H:%M').time()
        except (ValueError, TypeError) as e:
            logger.warning(f"Erro ao parsear horários de jornada: {e}")
            return {
                'trabalha': False,
                'horas_esperadas': 0.0,
                'horas_esperadas_minutos': 0,
                'horario_inicio': str(jornada_dia['inicio']),
                'horario_fim': str(jornada_dia['fim']),
                'intervalo_minutos': 0
            }
        
        # Calcular diferença em minutos
        dt_inicio = datetime.combine(datetime.today(), hora_inicio)
        dt_fim = datetime.combine(datetime.today(), hora_fim)
        
        # Se fim é antes do início, considerar próximo dia (trabalho noturno)
        if dt_fim < dt_inicio:
            dt_fim += timedelta(days=1)
        
        minutos_brutos = int((dt_fim - dt_inicio).total_seconds() / 60)
        intervalo_minutos = int(jornada_dia.get('intervalo', 60))
        
        # Calcular horas efetivas
        minutos_efetivos = max(0, minutos_brutos - intervalo_minutos)
        horas_efetivas = minutos_efetivos / 60.0
        
        return {
            'trabalha': True,
            'horas_esperadas': horas_efetivas,
            'horas_esperadas_minutos': minutos_efetivos,
            'horario_inicio': jornada_dia['inicio'],
            'horario_fim': jornada_dia['fim'],
            'intervalo_minutos': intervalo_minutos
        }
    
    @staticmethod
    def calcular_horas_registradas_dia(usuario, data, excluir_tipo_intermediario=True):
        """
        Calcula quantas horas o funcionário REGISTROU em um dia
        
        Usa pontos de tipo 'Início' e 'Fim' para calcular tempo trabalhado.
        Se houver ponto 'Intermediário', considera o último 'Inicio' antes dele.
        
        Args:
            usuario: Nome de usuário
            data: datetime.date ou datetime.datetime
            excluir_tipo_intermediario: Se True, ignora pontos intermediários no cálculo
        
        Returns:
            dict: {
                'trabalha': bool,  # Se tem registros de ponto
                'horas_registradas': float,  # em horas
                'horas_registradas_minutos': int,  # total em minutos
                'pontos': list,  # Pontos utilizados no cálculo
                'intervalo_minutos': int,  # intervalo debitado do cálculo
                'primeira_marca': str,  # Primeira marca (Início)
                'ultima_marca': str  # Última marca (Fim)
            }
        """
        pontos = JornadaSemanalCalculoSystem.obter_pontos_dia(usuario, data)
        
        if not pontos:
            return {
                'trabalha': False,
                'horas_registradas': 0.0,
                'horas_registradas_minutos': 0,
                'pontos': [],
                'intervalo_minutos': 0,
                'primeira_marca': None,
                'ultima_marca': None
            }
        
        # Filtrar pontos por tipo
        pontos_inicio = [p for p in pontos if p['tipo'] in ['Início', 'inicio']]
        pontos_fim = [p for p in pontos if p['tipo'] in ['Fim', 'fim']]
        
        # Precisa ter pelo menos 1 Início e 1 Fim
        if not pontos_inicio or not pontos_fim:
            return {
                'trabalha': False if not pontos else True,
                'horas_registradas': 0.0,
                'horas_registradas_minutos': 0,
                'pontos': pontos,
                'intervalo_minutos': 0,
                'primeira_marca': pontos_inicio[0]['data_hora'] if pontos_inicio else None,
                'ultima_marca': pontos_fim[-1]['data_hora'] if pontos_fim else None
            }
        
        # Usar primeiro Início e último Fim
        primeira_marca = pontos_inicio[0]['timestamp']
        ultima_marca = pontos_fim[-1]['timestamp']
        
        # Se fim é antes do início, considerar trabalho que cruzou madrugada
        if ultima_marca < primeira_marca:
            logger.warning(f"Marca de fim {ultima_marca} antes de início {primeira_marca} para {usuario}")
            return {
                'trabalha': True,
                'horas_registradas': 0.0,
                'horas_registradas_minutos': 0,
                'pontos': pontos,
                'intervalo_minutos': 0,
                'primeira_marca': primeira_marca.strftime('%Y-%m-%d %H:%M:%S'),
                'ultima_marca': ultima_marca.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        # Calcular minutos brutos
        minutos_brutos = int((ultima_marca - primeira_marca).total_seconds() / 60)
        
        # Obter intervalo da jornada esperada
        resultado_esperado = JornadaSemanalCalculoSystem.calcular_horas_esperadas_dia(usuario, data)
        intervalo_minutos = resultado_esperado.get('intervalo_minutos', 0)
        
        # Calcular minutos efetivos
        minutos_efetivos = max(0, minutos_brutos - intervalo_minutos)
        horas_registradas = minutos_efetivos / 60.0
        
        return {
            'trabalha': True,
            'horas_registradas': horas_registradas,
            'horas_registradas_minutos': minutos_efetivos,
            'pontos': pontos,
            'intervalo_minutos': intervalo_minutos,
            'primeira_marca': primeira_marca.strftime('%Y-%m-%d %H:%M:%S'),
            'ultima_marca': ultima_marca.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    @staticmethod
    def detectar_hora_extra_dia(usuario, data, tolerancia_minutos=5):
        """
        Detecta se há hora extra em um dia
        
        Compara:
        - Horas esperadas (jornada)
        - Horas registradas (pontos)
        
        Se registradas > esperadas + tolerância → hora extra
        
        Args:
            usuario: Nome de usuário
            data: datetime.date ou datetime.datetime
            tolerancia_minutos: Tolerância antes de considerar hora extra (padrão: 5 min)
        
        Returns:
            dict: {
                'tem_hora_extra': bool,
                'horas_extra': float,  # em horas (ex: 2.5)
                'minutos_extra': int,  # em minutos (ex: 150)
                'esperado_minutos': int,
                'registrado_minutos': int,
                'categoria': str  # 'sem_ponto', 'dentro_jornada', 'hora_extra'
            }
        """
        # Calcular esperado
        esperado = JornadaSemanalCalculoSystem.calcular_horas_esperadas_dia(usuario, data)
        
        if not esperado['trabalha']:
            return {
                'tem_hora_extra': False,
                'horas_extra': 0.0,
                'minutos_extra': 0,
                'esperado_minutos': 0,
                'registrado_minutos': 0,
                'categoria': 'sem_jornada'
            }
        
        # Calcular registrado
        registrado = JornadaSemanalCalculoSystem.calcular_horas_registradas_dia(usuario, data)
        
        if not registrado['trabalha']:
            return {
                'tem_hora_extra': False,
                'horas_extra': 0.0,
                'minutos_extra': 0,
                'esperado_minutos': esperado['horas_esperadas_minutos'],
                'registrado_minutos': 0,
                'categoria': 'sem_ponto'
            }
        
        # Comparar
        esperado_min = esperado['horas_esperadas_minutos']
        registrado_min = registrado['horas_registradas_minutos']
        diferenca_min = registrado_min - esperado_min
        
        # Aplicar tolerância
        if diferenca_min > tolerancia_minutos:
            horas_extra = diferenca_min / 60.0
            return {
                'tem_hora_extra': True,
                'horas_extra': horas_extra,
                'minutos_extra': diferenca_min,
                'esperado_minutos': esperado_min,
                'registrado_minutos': registrado_min,
                'categoria': 'hora_extra'
            }
        elif diferenca_min < -tolerancia_minutos:
            # Trabalhou menos que esperado
            return {
                'tem_hora_extra': False,
                'horas_extra': 0.0,
                'minutos_extra': diferenca_min,  # será negativo
                'esperado_minutos': esperado_min,
                'registrado_minutos': registrado_min,
                'categoria': 'abaixo_jornada'
            }
        else:
            # Dentro da tolerância
            return {
                'tem_hora_extra': False,
                'horas_extra': 0.0,
                'minutos_extra': 0,
                'esperado_minutos': esperado_min,
                'registrado_minutos': registrado_min,
                'categoria': 'dentro_jornada'
            }
    
    @staticmethod
    def validar_ponto_contra_jornada(usuario, data, tipo_ponto, hora_ponto=None):
        """
        Valida se um ponto pode ser registrado contra a jornada
        
        Args:
            usuario: Nome de usuário
            data: datetime.date ou datetime.datetime
            tipo_ponto: 'Início', 'Intermediário', 'Fim'
            hora_ponto: datetime ou None (usar hora atual se None)
        
        Returns:
            dict: {
                'valido': bool,
                'mensagem': str,
                'alerta': bool,  # True se aviso (mas ainda permite)
                'categoria': str  # 'ok', 'fora_jornada', 'nao_trabalha_dia', 'aviso'
            }
        """
        jornada_dia = obter_jornada_do_dia(usuario, data)
        
        if not jornada_dia:
            return {
                'valido': True,  # Permite, mas com aviso
                'mensagem': f'⚠️ Sem jornada configurada para este dia',
                'alerta': True,
                'categoria': 'sem_jornada'
            }
        
        if not jornada_dia.get('trabalha', False):
            return {
                'valido': False,
                'mensagem': f'❌ Você não trabalha neste dia ({data.strftime("%d/%m/%Y")})',
                'alerta': False,
                'categoria': 'nao_trabalha_dia'
            }
        
        # Parsear horários
        try:
            hora_inicio = datetime.strptime(jornada_dia['inicio'], '%H:%M').time()
            hora_fim = datetime.strptime(jornada_dia['fim'], '%H:%M').time()
        except (ValueError, TypeError):
            return {
                'valido': True,
                'mensagem': f'⚠️ Horários de jornada inválidos',
                'alerta': True,
                'categoria': 'horario_invalido'
            }
        
        # Usar hora atual se não fornecida
        if hora_ponto is None:
            hora_ponto = datetime.now().time()
        elif isinstance(hora_ponto, datetime):
            hora_ponto = hora_ponto.time()
        
        # Verificar se está dentro da jornada
        # Se fim < inicio, consideramos trabalho noturno
        trabalho_noturno = hora_fim < hora_inicio
        
        if trabalho_noturno:
            # Ex: trabalha de 22:00 a 06:00
            dentro_jornada = hora_ponto >= hora_inicio or hora_ponto <= hora_fim
        else:
            # Ex: trabalha de 08:00 a 18:00
            dentro_jornada = hora_inicio <= hora_ponto <= hora_fim
        
        if tipo_ponto in ['Início', 'inicio']:
            if not dentro_jornada and hora_ponto < hora_inicio:
                return {
                    'valido': True,
                    'mensagem': f'⏰ Você está iniciando antes do horário ({jornada_dia["inicio"]})',
                    'alerta': True,
                    'categoria': 'aviso'
                }
            elif not dentro_jornada and hora_ponto > hora_fim:
                return {
                    'valido': True,
                    'mensagem': f'⚠️ Você está iniciando após o fim da jornada ({jornada_dia["fim"]})',
                    'alerta': True,
                    'categoria': 'aviso'
                }
        
        elif tipo_ponto in ['Fim', 'fim']:
            if not dentro_jornada:
                return {
                    'valido': True,
                    'mensagem': f'⚠️ Você está finalizando fora do horário de jornada',
                    'alerta': True,
                    'categoria': 'aviso'
                }
        
        return {
            'valido': True,
            'mensagem': f'✅ Ponto registrado com sucesso',
            'alerta': False,
            'categoria': 'ok'
        }
    
    @staticmethod
    def obter_tempo_ate_fim_jornada(usuario, data=None, margem_minutos=5):
        """
        Retorna tempo até o fim da jornada
        
        Útil para mostrar popup de alerta 5 min antes de finalizar
        
        Args:
            usuario: Nome de usuário
            data: datetime.date ou datetime.datetime (padrão: hoje)
            margem_minutos: Considerar "próximo" se falta menos que X minutos
        
        Returns:
            dict: {
                'dentro_margem': bool,  # True se falta <= margem_minutos
                'minutos_restantes': int,  # Minutos até fim (None se não trabalha)
                'horario_fim': str,
                'status': str  # 'ja_passou', 'dentro_margem', 'longe'
            }
        """
        if data is None:
            data = datetime.now()
        
        jornada_dia = obter_jornada_do_dia(usuario, data)
        
        if not jornada_dia or not jornada_dia.get('trabalha', False):
            return {
                'dentro_margem': False,
                'minutos_restantes': None,
                'horario_fim': None,
                'status': 'nao_trabalha'
            }
        
        # Parsear horário de fim
        try:
            hora_fim = datetime.strptime(jornada_dia['fim'], '%H:%M').time()
        except (ValueError, TypeError):
            return {
                'dentro_margem': False,
                'minutos_restantes': None,
                'horario_fim': jornada_dia['fim'],
                'status': 'horario_invalido'
            }
        
        # Calcular tempo até fim
        agora = datetime.now()
        dt_fim = agora.replace(hour=hora_fim.hour, minute=hora_fim.minute, second=0, microsecond=0)
        
        # Se já passou, considerar próximo dia
        if agora > dt_fim:
            return {
                'dentro_margem': False,
                'minutos_restantes': 0,
                'horario_fim': jornada_dia['fim'],
                'status': 'ja_passou'
            }
        
        minutos_restantes = int((dt_fim - agora).total_seconds() / 60)
        
        if minutos_restantes <= margem_minutos:
            status = 'dentro_margem'
            dentro_margem = True
        else:
            status = 'longe'
            dentro_margem = False
        
        return {
            'dentro_margem': dentro_margem,
            'minutos_restantes': minutos_restantes,
            'horario_fim': jornada_dia['fim'],
            'status': status
        }


# Função helper para teste rápido
def testar_sistema():
    """Função para teste rápido do sistema"""
    print("✅ Sistema de Cálculo de Jornada Semanal carregado com sucesso!")
    print("\nFunções disponíveis:")
    print("  - calcular_horas_esperadas_dia(usuario, data)")
    print("  - calcular_horas_registradas_dia(usuario, data)")
    print("  - detectar_hora_extra_dia(usuario, data)")
    print("  - validar_ponto_contra_jornada(usuario, data, tipo_ponto)")
    print("  - obter_tempo_ate_fim_jornada(usuario, data)")


if __name__ == "__main__":
    testar_sistema()
