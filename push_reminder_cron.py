"""
Sistema de Lembretes Automáticos - Ponto ExSA
==============================================
Verifica periodicamente e envia lembretes para:
- Funcionários que esqueceram de bater ponto de entrada
- Funcionários que esqueceram de bater ponto de saída
- Funcionários em hora extra por muito tempo

Pode ser executado:
- Como cron job externo (Render, Railway, etc)
- Via APScheduler (integrado ao app)
- Manualmente para testes

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import os
import sys
import logging
from datetime import datetime, timedelta, time, date
from typing import List, Dict, Tuple, Optional

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Tentar importar pytz para timezone
try:
    import pytz
    TIMEZONE_BR = pytz.timezone('America/Sao_Paulo')
except ImportError:
    TIMEZONE_BR = None

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar módulos do sistema
try:
    from database import get_connection, SQL_PLACEHOLDER
    from push_notifications import (
        push_system,
        notificar_esqueceu_entrada,
        notificar_esqueceu_saida,
        notificar_fim_hora_extra,
        enviar_notificacao_para_usuario
    )
except ImportError as e:
    logger.error(f"Erro ao importar módulos: {e}")
    sys.exit(1)


def get_datetime_br() -> datetime:
    """Retorna datetime atual no fuso de Brasília."""
    if TIMEZONE_BR:
        return datetime.now(TIMEZONE_BR)
    return datetime.now()


def get_date_br() -> date:
    """Retorna data atual no fuso de Brasília."""
    return get_datetime_br().date()


def get_time_br() -> time:
    """Retorna hora atual no fuso de Brasília."""
    return get_datetime_br().time()


# ============================================
# VERIFICAÇÃO DE PONTO
# ============================================

def obter_usuarios_ativos_com_jornada() -> List[Dict]:
    """
    Obtém lista de usuários ativos com suas configurações de jornada.
    
    Returns:
        Lista de dicts com usuario, jornada_inicio, jornada_fim
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usuario, nome_completo, jornada_inicio_previsto, jornada_fim_previsto
            FROM usuarios
            WHERE ativo = 1
        """)
        
        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                'usuario': row[0],
                'nome': row[1] or row[0],
                'jornada_inicio': row[2] or time(8, 0),
                'jornada_fim': row[3] or time(17, 0)
            })
        
        return usuarios
        
    except Exception as e:
        logger.error(f"Erro ao obter usuários: {e}")
        return []
    finally:
        if conn:
            conn.close()


def verificar_registro_entrada_hoje(usuario: str) -> bool:
    """
    Verifica se o usuário já registrou entrada hoje.
    
    Args:
        usuario: Username do usuário
    
    Returns:
        True se já registrou entrada, False caso contrário
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoje = get_date_br()
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM registros_ponto
            WHERE usuario = {SQL_PLACEHOLDER}
            AND DATE(data_hora) = {SQL_PLACEHOLDER}
            AND LOWER(tipo) = 'início'
        """, (usuario, hoje))
        
        count = cursor.fetchone()[0]
        return count > 0
        
    except Exception as e:
        logger.error(f"Erro ao verificar entrada: {e}")
        return True  # Em caso de erro, não enviar lembrete
    finally:
        if conn:
            conn.close()


def verificar_registro_saida_hoje(usuario: str) -> bool:
    """
    Verifica se o usuário já registrou saída hoje.
    
    Args:
        usuario: Username do usuário
    
    Returns:
        True se já registrou saída, False caso contrário
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoje = get_date_br()
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM registros_ponto
            WHERE usuario = {SQL_PLACEHOLDER}
            AND DATE(data_hora) = {SQL_PLACEHOLDER}
            AND LOWER(tipo) = 'fim'
        """, (usuario, hoje))
        
        count = cursor.fetchone()[0]
        return count > 0
        
    except Exception as e:
        logger.error(f"Erro ao verificar saída: {e}")
        return True  # Em caso de erro, não enviar lembrete
    finally:
        if conn:
            conn.close()


def obter_horas_extras_ativas() -> List[Dict]:
    """
    Obtém lista de horas extras em andamento.
    
    Returns:
        Lista de dicts com usuario, data_inicio, minutos_decorridos
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usuario, data_inicio, hora_inicio
            FROM horas_extras_ativas
            WHERE status = 'em_execucao'
        """)
        
        agora = get_datetime_br().replace(tzinfo=None)
        horas_extras = []
        
        for row in cursor.fetchall():
            usuario = row[0]
            data_inicio = row[1]
            hora_inicio = row[2]
            
            # Calcular tempo decorrido
            if isinstance(data_inicio, datetime):
                inicio = data_inicio
            else:
                inicio = datetime.combine(data_inicio, hora_inicio)
            
            delta = agora - inicio
            minutos = int(delta.total_seconds() / 60)
            
            horas_extras.append({
                'usuario': usuario,
                'data_inicio': data_inicio,
                'minutos_decorridos': minutos
            })
        
        return horas_extras
        
    except Exception as e:
        logger.error(f"Erro ao obter horas extras ativas: {e}")
        return []
    finally:
        if conn:
            conn.close()


def verificar_config_lembretes(usuario: str) -> Dict:
    """
    Obtém configuração de lembretes do usuário.
    
    Args:
        usuario: Username
    
    Returns:
        Dict com configurações ou defaults
    """
    conn = None
    defaults = {
        'lembrete_entrada': True,
        'lembrete_saida': True,
        'lembrete_hora_extra': True,
        'horario_lembrete_entrada': time(8, 15),
        'horario_lembrete_saida': time(17, 15),
        'dias_semana': [1, 2, 3, 4, 5]  # Seg a Sex
    }
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT lembrete_entrada, lembrete_saida, lembrete_hora_extra,
                   horario_lembrete_entrada, horario_lembrete_saida, dias_semana
            FROM config_lembretes_push
            WHERE usuario = {SQL_PLACEHOLDER}
        """, (usuario,))
        
        row = cursor.fetchone()
        
        if row:
            dias = [int(d) for d in (row[5] or '1,2,3,4,5').split(',')]
            return {
                'lembrete_entrada': bool(row[0]),
                'lembrete_saida': bool(row[1]),
                'lembrete_hora_extra': bool(row[2]),
                'horario_lembrete_entrada': row[3] or defaults['horario_lembrete_entrada'],
                'horario_lembrete_saida': row[4] or defaults['horario_lembrete_saida'],
                'dias_semana': dias
            }
        
        return defaults
        
    except Exception as e:
        logger.error(f"Erro ao obter config de lembretes: {e}")
        return defaults
    finally:
        if conn:
            conn.close()


def eh_dia_util() -> bool:
    """Verifica se hoje é dia útil (seg-sex)."""
    return get_datetime_br().weekday() < 5


def eh_feriado() -> bool:
    """Verifica se hoje é feriado."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        hoje = get_date_br()
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM feriados
            WHERE data = {SQL_PLACEHOLDER} AND ativo = 1
        """, (hoje,))
        
        return cursor.fetchone()[0] > 0
        
    except Exception as e:
        logger.error(f"Erro ao verificar feriado: {e}")
        return False
    finally:
        if conn:
            conn.close()


# ============================================
# JOBS DE LEMBRETE
# ============================================

def job_lembrete_entrada() -> Dict:
    """
    Verifica e envia lembretes de entrada para usuários que esqueceram.
    Deve ser executado ~15 minutos após horário de entrada padrão.
    
    Returns:
        Dict com estatísticas do job
    """
    logger.info("Iniciando job de lembrete de entrada...")
    
    # Verificar se é dia útil
    if not eh_dia_util() or eh_feriado():
        logger.info("Hoje não é dia útil ou é feriado. Pulando lembretes de entrada.")
        return {'status': 'skipped', 'reason': 'not_workday'}
    
    resultados = {
        'verificados': 0,
        'lembretes_enviados': 0,
        'ja_registraram': 0,
        'erros': 0,
        'usuarios_notificados': []
    }
    
    usuarios = obter_usuarios_ativos_com_jornada()
    agora = get_time_br()
    
    for user in usuarios:
        resultados['verificados'] += 1
        
        try:
            # Verificar configurações do usuário
            config = verificar_config_lembretes(user['usuario'])
            
            if not config['lembrete_entrada']:
                continue
            
            # Verificar se já passou o horário de lembrete
            horario_lembrete = config['horario_lembrete_entrada']
            if agora < horario_lembrete:
                continue
            
            # Verificar se é dia de trabalho para este usuário
            dia_semana = get_datetime_br().isoweekday()
            if dia_semana not in config['dias_semana']:
                continue
            
            # Verificar se já registrou entrada
            if verificar_registro_entrada_hoje(user['usuario']):
                resultados['ja_registraram'] += 1
                continue
            
            # Enviar lembrete
            enviados, total = notificar_esqueceu_entrada(user['usuario'])
            
            if enviados > 0:
                resultados['lembretes_enviados'] += 1
                resultados['usuarios_notificados'].append(user['usuario'])
                logger.info(f"Lembrete de entrada enviado para: {user['usuario']}")
            
        except Exception as e:
            resultados['erros'] += 1
            logger.error(f"Erro ao processar usuário {user['usuario']}: {e}")
    
    logger.info(f"Job de entrada concluído: {resultados['lembretes_enviados']} lembretes enviados")
    return resultados


def job_lembrete_saida() -> Dict:
    """
    Verifica e envia lembretes de saída para usuários que esqueceram.
    Deve ser executado ~15 minutos após horário de saída padrão.
    
    Returns:
        Dict com estatísticas do job
    """
    logger.info("Iniciando job de lembrete de saída...")
    
    if not eh_dia_util() or eh_feriado():
        logger.info("Hoje não é dia útil ou é feriado. Pulando lembretes de saída.")
        return {'status': 'skipped', 'reason': 'not_workday'}
    
    resultados = {
        'verificados': 0,
        'lembretes_enviados': 0,
        'ja_registraram': 0,
        'nao_entraram': 0,
        'erros': 0,
        'usuarios_notificados': []
    }
    
    usuarios = obter_usuarios_ativos_com_jornada()
    agora = get_time_br()
    
    for user in usuarios:
        resultados['verificados'] += 1
        
        try:
            config = verificar_config_lembretes(user['usuario'])
            
            if not config['lembrete_saida']:
                continue
            
            horario_lembrete = config['horario_lembrete_saida']
            if agora < horario_lembrete:
                continue
            
            dia_semana = get_datetime_br().isoweekday()
            if dia_semana not in config['dias_semana']:
                continue
            
            # Verificar se registrou entrada (só lembrar se trabalhou)
            if not verificar_registro_entrada_hoje(user['usuario']):
                resultados['nao_entraram'] += 1
                continue
            
            # Verificar se já registrou saída
            if verificar_registro_saida_hoje(user['usuario']):
                resultados['ja_registraram'] += 1
                continue
            
            # Enviar lembrete
            enviados, total = notificar_esqueceu_saida(user['usuario'])
            
            if enviados > 0:
                resultados['lembretes_enviados'] += 1
                resultados['usuarios_notificados'].append(user['usuario'])
                logger.info(f"Lembrete de saída enviado para: {user['usuario']}")
            
        except Exception as e:
            resultados['erros'] += 1
            logger.error(f"Erro ao processar usuário {user['usuario']}: {e}")
    
    logger.info(f"Job de saída concluído: {resultados['lembretes_enviados']} lembretes enviados")
    return resultados


def job_alerta_hora_extra() -> Dict:
    """
    Verifica horas extras em andamento e alerta usuários.
    Envia alerta após 1 hora e 1h30 de hora extra.
    
    Returns:
        Dict com estatísticas do job
    """
    logger.info("Iniciando job de alerta de hora extra...")
    
    resultados = {
        'horas_extras_ativas': 0,
        'alertas_enviados': 0,
        'erros': 0,
        'usuarios_alertados': []
    }
    
    horas_extras = obter_horas_extras_ativas()
    resultados['horas_extras_ativas'] = len(horas_extras)
    
    # Limites para alerta (em minutos)
    ALERTA_60_MIN = 60
    ALERTA_90_MIN = 90
    
    for he in horas_extras:
        try:
            minutos = he['minutos_decorridos']
            usuario = he['usuario']
            
            config = verificar_config_lembretes(usuario)
            
            if not config['lembrete_hora_extra']:
                continue
            
            # Enviar alerta nos marcos de 60 e 90 minutos
            # (Na prática, verificar se está próximo desses valores)
            if ALERTA_60_MIN - 5 <= minutos <= ALERTA_60_MIN + 5:
                enviados, total = notificar_fim_hora_extra(usuario, minutos)
                if enviados > 0:
                    resultados['alertas_enviados'] += 1
                    resultados['usuarios_alertados'].append(usuario)
                    logger.info(f"Alerta de 1h de HE enviado para: {usuario}")
            
            elif ALERTA_90_MIN - 5 <= minutos <= ALERTA_90_MIN + 5:
                enviados, total = notificar_fim_hora_extra(usuario, minutos)
                if enviados > 0:
                    resultados['alertas_enviados'] += 1
                    resultados['usuarios_alertados'].append(usuario)
                    logger.info(f"Alerta de 1h30 de HE enviado para: {usuario}")
            
        except Exception as e:
            resultados['erros'] += 1
            logger.error(f"Erro ao processar HE de {he['usuario']}: {e}")
    
    logger.info(f"Job de HE concluído: {resultados['alertas_enviados']} alertas enviados")
    return resultados


def executar_todos_jobs() -> Dict:
    """
    Executa todos os jobs de lembrete.
    Útil para execução via cron externo.
    
    Returns:
        Dict com resultados de todos os jobs
    """
    logger.info("=" * 60)
    logger.info("Iniciando execução de todos os jobs de lembrete")
    logger.info(f"Data/Hora: {get_datetime_br()}")
    logger.info("=" * 60)
    
    resultados = {
        'timestamp': get_datetime_br().isoformat(),
        'jobs': {}
    }
    
    # Job de entrada (executar entre 8:15 e 9:30)
    agora = get_time_br()
    if time(8, 15) <= agora <= time(9, 30):
        resultados['jobs']['entrada'] = job_lembrete_entrada()
    else:
        resultados['jobs']['entrada'] = {'status': 'skipped', 'reason': 'outside_window'}
    
    # Job de saída (executar entre 17:15 e 18:30)
    if time(17, 15) <= agora <= time(18, 30):
        resultados['jobs']['saida'] = job_lembrete_saida()
    else:
        resultados['jobs']['saida'] = {'status': 'skipped', 'reason': 'outside_window'}
    
    # Job de hora extra (executar a cada hora entre 18:00 e 22:00)
    if time(18, 0) <= agora <= time(22, 0):
        resultados['jobs']['hora_extra'] = job_alerta_hora_extra()
    else:
        resultados['jobs']['hora_extra'] = {'status': 'skipped', 'reason': 'outside_window'}
    
    logger.info("=" * 60)
    logger.info("Jobs concluídos")
    logger.info("=" * 60)
    
    return resultados


# ============================================
# SCHEDULER (APScheduler - opcional)
# ============================================

def iniciar_scheduler():
    """
    Inicia o scheduler de jobs usando APScheduler.
    Requer: pip install apscheduler
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler não instalado. Execute: pip install apscheduler")
        return None
    
    scheduler = BackgroundScheduler(timezone='America/Sao_Paulo')
    
    # Job de lembrete de entrada - 8:15, 8:30, 9:00 (dias úteis)
    scheduler.add_job(
        job_lembrete_entrada,
        CronTrigger(hour='8', minute='15,30', day_of_week='mon-fri'),
        id='lembrete_entrada_1',
        name='Lembrete de Entrada (8:15/8:30)'
    )
    scheduler.add_job(
        job_lembrete_entrada,
        CronTrigger(hour='9', minute='0', day_of_week='mon-fri'),
        id='lembrete_entrada_2',
        name='Lembrete de Entrada (9:00)'
    )
    
    # Job de lembrete de saída - 17:15, 17:30, 18:00 (dias úteis)
    scheduler.add_job(
        job_lembrete_saida,
        CronTrigger(hour='17', minute='15,30', day_of_week='mon-fri'),
        id='lembrete_saida_1',
        name='Lembrete de Saída (17:15/17:30)'
    )
    scheduler.add_job(
        job_lembrete_saida,
        CronTrigger(hour='18', minute='0', day_of_week='mon-fri'),
        id='lembrete_saida_2',
        name='Lembrete de Saída (18:00)'
    )
    
    # Job de alerta de hora extra - a cada 30 minutos entre 18:00 e 22:00
    scheduler.add_job(
        job_alerta_hora_extra,
        CronTrigger(hour='18-22', minute='0,30', day_of_week='mon-fri'),
        id='alerta_hora_extra',
        name='Alerta de Hora Extra'
    )
    
    scheduler.start()
    logger.info("Scheduler de lembretes iniciado")
    
    return scheduler


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de Lembretes Automáticos - Ponto ExSA')
    parser.add_argument('--job', choices=['entrada', 'saida', 'hora_extra', 'todos'],
                        help='Executar job específico')
    parser.add_argument('--scheduler', action='store_true',
                        help='Iniciar scheduler em background')
    parser.add_argument('--status', action='store_true',
                        help='Mostrar status do sistema')
    
    args = parser.parse_args()
    
    if args.status:
        print("=" * 60)
        print("Status do Sistema de Lembretes")
        print("=" * 60)
        print(f"Data/Hora: {get_datetime_br()}")
        print(f"Dia útil: {eh_dia_util()}")
        print(f"Feriado: {eh_feriado()}")
        print(f"Push configurado: {push_system.is_ready()}")
        print()
        
        usuarios = obter_usuarios_ativos_com_jornada()
        print(f"Usuários ativos: {len(usuarios)}")
        
        horas_extras = obter_horas_extras_ativas()
        print(f"Horas extras em andamento: {len(horas_extras)}")
        
    elif args.scheduler:
        print("Iniciando scheduler de lembretes...")
        scheduler = iniciar_scheduler()
        if scheduler:
            print("Scheduler rodando. Pressione Ctrl+C para parar.")
            try:
                while True:
                    import time as t
                    t.sleep(60)
            except KeyboardInterrupt:
                print("\nParando scheduler...")
                scheduler.shutdown()
        
    elif args.job:
        if args.job == 'entrada':
            resultado = job_lembrete_entrada()
        elif args.job == 'saida':
            resultado = job_lembrete_saida()
        elif args.job == 'hora_extra':
            resultado = job_alerta_hora_extra()
        elif args.job == 'todos':
            resultado = executar_todos_jobs()
        
        print(f"\nResultado: {resultado}")
        
    else:
        # Sem argumentos, executar todos os jobs
        resultado = executar_todos_jobs()
        print(f"\nResultado: {resultado}")
