"""
Background Scheduler - Ponto ExSA
==================================
Scheduler de notificações que roda em background thread.
Integrado ao app principal (sem custo adicional no Render).

Esta solução usa APScheduler com BackgroundScheduler que roda
em uma thread separada, sem bloquear o app principal.

Configurações são lidas do banco de dados (tabela configuracoes).

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.1.0
"""

import os
import sys
import logging
import threading
import atexit
from typing import Optional, Dict, List

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Instância global do scheduler
_scheduler = None
_scheduler_lock = threading.Lock()
_scheduler_started = False


def get_scheduler():
    """Retorna a instância do scheduler (singleton)."""
    global _scheduler
    return _scheduler


def is_scheduler_running() -> bool:
    """Verifica se o scheduler está rodando."""
    global _scheduler, _scheduler_started
    return _scheduler is not None and _scheduler_started


def carregar_configuracoes_notificacao() -> Dict:
    """
    Carrega configurações de notificação do banco de dados.
    
    Returns:
        Dict com as configurações
    """
    # Valores padrão
    config = {
        'notif_entrada_ativo': True,
        'notif_entrada_horarios': ['08:15', '08:30', '09:00'],
        'notif_saida_ativo': True,
        'notif_saida_horarios': ['17:15', '17:30', '18:00'],
        'notif_hora_extra_ativo': True,
        'notif_hora_extra_inicio': '18:00',
        'notif_hora_extra_fim': '22:00',
        'notif_aprovadores_ativo': True,
        'notif_aprovadores_horarios': ['09:00', '14:00', '17:00']
    }
    
    try:
        from database import get_connection, SQL_PLACEHOLDER
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar configurações do banco
        cursor.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'notif_%'")
        rows = cursor.fetchall()
        conn.close()
        
        for chave, valor in rows:
            if chave == 'notif_entrada_ativo':
                config['notif_entrada_ativo'] = valor == '1'
            elif chave == 'notif_entrada_horarios':
                config['notif_entrada_horarios'] = [h.strip() for h in valor.split(',') if h.strip()]
            elif chave == 'notif_saida_ativo':
                config['notif_saida_ativo'] = valor == '1'
            elif chave == 'notif_saida_horarios':
                config['notif_saida_horarios'] = [h.strip() for h in valor.split(',') if h.strip()]
            elif chave == 'notif_hora_extra_ativo':
                config['notif_hora_extra_ativo'] = valor == '1'
            elif chave == 'notif_hora_extra_inicio':
                config['notif_hora_extra_inicio'] = valor
            elif chave == 'notif_hora_extra_fim':
                config['notif_hora_extra_fim'] = valor
            elif chave == 'notif_aprovadores_ativo':
                config['notif_aprovadores_ativo'] = valor == '1'
            elif chave == 'notif_aprovadores_horarios':
                config['notif_aprovadores_horarios'] = [h.strip() for h in valor.split(',') if h.strip()]
        
        logger.info("Configurações de notificação carregadas do banco")
        
    except Exception as e:
        logger.warning(f"Usando configurações padrão (erro ao carregar do banco: {e})")
    
    return config


def parse_horario(horario_str: str) -> tuple:
    """Converte string HH:MM para tupla (hora, minuto)."""
    try:
        parts = horario_str.strip().split(':')
        return int(parts[0]), int(parts[1])
    except:
        return None, None


def iniciar_scheduler_background() -> bool:
    """
    Inicia o scheduler de notificações em background.
    Usa BackgroundScheduler do APScheduler que roda em thread separada.
    Carrega configurações do banco de dados.
    
    Returns:
        True se iniciou com sucesso, False caso contrário
    """
    global _scheduler, _scheduler_started
    
    with _scheduler_lock:
        # Verificar se já está rodando
        if _scheduler_started:
            logger.info("Scheduler já está rodando")
            return True
        
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.warning("APScheduler não instalado. Notificações automáticas desabilitadas.")
            logger.info("Para habilitar, execute: pip install apscheduler")
            return False
        
        # Importar funções de job
        try:
            from push_reminder_cron import (
                job_lembrete_entrada,
                job_lembrete_saida,
                job_alerta_hora_extra,
                job_lembrete_aprovadores,
                job_lembrete_fim_dia_aprovadores,
                get_datetime_br
            )
        except ImportError as e:
            logger.error(f"Erro ao importar push_reminder_cron: {e}")
            return False
        
        try:
            # Carregar configurações do banco
            config = carregar_configuracoes_notificacao()
            
            # Criar scheduler com timezone de Brasília
            _scheduler = BackgroundScheduler(
                timezone='America/Sao_Paulo',
                job_defaults={
                    'coalesce': True,  # Combinar execuções perdidas
                    'max_instances': 1,  # Apenas uma instância por job
                    'misfire_grace_time': 600  # 10 minutos de tolerância
                }
            )
            
            logger.info("=" * 60)
            logger.info("🔔 BACKGROUND SCHEDULER - Ponto ExSA")
            logger.info("=" * 60)
            logger.info(f"Iniciando em: {get_datetime_br()}")
            logger.info("Configurando jobs de notificação automática...")
            
            # ============================================
            # JOB 1: Lembrete de Entrada (configurável)
            # ============================================
            if config['notif_entrada_ativo']:
                for i, horario in enumerate(config['notif_entrada_horarios']):
                    hora, minuto = parse_horario(horario)
                    if hora is not None:
                        _scheduler.add_job(
                            job_lembrete_entrada,
                            CronTrigger(hour=hora, minute=minuto, day_of_week='mon-fri'),
                            id=f'entrada_{hora}h{minuto:02d}',
                            name=f'Lembrete Entrada {hora}:{minuto:02d}',
                            replace_existing=True
                        )
                horarios_str = ', '.join(config['notif_entrada_horarios'])
                logger.info(f"  ✅ Lembrete de Entrada: {horarios_str} (Seg-Sex)")
            else:
                logger.info("  ⏸️ Lembrete de Entrada: DESATIVADO")
            
            # ============================================
            # JOB 2: Lembrete de Saída (configurável)
            # ============================================
            if config['notif_saida_ativo']:
                for i, horario in enumerate(config['notif_saida_horarios']):
                    hora, minuto = parse_horario(horario)
                    if hora is not None:
                        _scheduler.add_job(
                            job_lembrete_saida,
                            CronTrigger(hour=hora, minute=minuto, day_of_week='mon-fri'),
                            id=f'saida_{hora}h{minuto:02d}',
                            name=f'Lembrete Saída {hora}:{minuto:02d}',
                            replace_existing=True
                        )
                horarios_str = ', '.join(config['notif_saida_horarios'])
                logger.info(f"  ✅ Lembrete de Saída: {horarios_str} (Seg-Sex)")
            else:
                logger.info("  ⏸️ Lembrete de Saída: DESATIVADO")
            
            # ============================================
            # JOB 3: Alerta de Hora Extra (configurável)
            # ============================================
            if config['notif_hora_extra_ativo']:
                hora_inicio, _ = parse_horario(config['notif_hora_extra_inicio'])
                hora_fim, _ = parse_horario(config['notif_hora_extra_fim'])
                if hora_inicio and hora_fim:
                    _scheduler.add_job(
                        job_alerta_hora_extra,
                        CronTrigger(hour=f'{hora_inicio}-{hora_fim}', minute='0,30', day_of_week='mon-fri'),
                        id='hora_extra',
                        name='Alerta Hora Extra',
                        replace_existing=True
                    )
                    logger.info(f"  ✅ Alerta Hora Extra: cada 30min das {hora_inicio}h às {hora_fim}h (Seg-Sex)")
            else:
                logger.info("  ⏸️ Alerta Hora Extra: DESATIVADO")
            
            # ============================================
            # JOB 4: Lembrete para Aprovadores (configurável)
            # ============================================
            if config['notif_aprovadores_ativo']:
                for i, horario in enumerate(config['notif_aprovadores_horarios']):
                    hora, minuto = parse_horario(horario)
                    if hora is not None:
                        # Último horário é urgente
                        if i == len(config['notif_aprovadores_horarios']) - 1:
                            _scheduler.add_job(
                                job_lembrete_fim_dia_aprovadores,
                                CronTrigger(hour=hora, minute=minuto, day_of_week='mon-fri'),
                                id=f'aprovadores_urgente_{hora}h{minuto:02d}',
                                name=f'Lembrete Urgente Aprovadores {hora}:{minuto:02d}',
                                replace_existing=True
                            )
                        else:
                            _scheduler.add_job(
                                job_lembrete_aprovadores,
                                CronTrigger(hour=hora, minute=minuto, day_of_week='mon-fri'),
                                id=f'aprovadores_{hora}h{minuto:02d}',
                                name=f'Lembrete Aprovadores {hora}:{minuto:02d}',
                                replace_existing=True
                            )
                horarios_str = ', '.join(config['notif_aprovadores_horarios'])
                logger.info(f"  ✅ Lembrete Aprovadores: {horarios_str} (Seg-Sex)")
            else:
                logger.info("  ⏸️ Lembrete Aprovadores: DESATIVADO")
            
            # Iniciar scheduler
            _scheduler.start()
            _scheduler_started = True
            
            # Registrar shutdown no exit
            atexit.register(parar_scheduler)
            
            logger.info("=" * 60)
            logger.info("🚀 Scheduler iniciado com sucesso!")
            logger.info("   Notificações automáticas ativadas")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar scheduler: {e}")
            _scheduler = None
            _scheduler_started = False
            return False


def parar_scheduler():
    """Para o scheduler de forma graciosa."""
    global _scheduler, _scheduler_started
    
    with _scheduler_lock:
        if _scheduler and _scheduler_started:
            try:
                logger.info("Parando scheduler de notificações...")
                _scheduler.shutdown(wait=False)
                _scheduler_started = False
                logger.info("Scheduler parado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao parar scheduler: {e}")


def obter_proximos_jobs() -> list:
    """
    Retorna lista dos próximos jobs agendados.
    
    Returns:
        Lista de dicts com informações dos jobs
    """
    global _scheduler
    
    if not _scheduler or not _scheduler_started:
        return []
    
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'nome': job.name,
            'proximo_execucao': job.next_run_time.strftime('%d/%m/%Y %H:%M') if job.next_run_time else 'N/A'
        })
    
    return jobs


def obter_status_scheduler() -> dict:
    """
    Retorna status completo do scheduler.
    
    Returns:
        Dict com informações do scheduler
    """
    global _scheduler, _scheduler_started
    
    try:
        from push_reminder_cron import get_datetime_br
        agora = get_datetime_br().strftime('%d/%m/%Y %H:%M:%S')
    except:
        from datetime import datetime
        agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    status = {
        'ativo': _scheduler_started,
        'data_hora_atual': agora,
        'total_jobs': 0,
        'jobs': []
    }
    
    if _scheduler and _scheduler_started:
        jobs = obter_proximos_jobs()
        status['total_jobs'] = len(jobs)
        status['jobs'] = jobs
    
    return status


# Auto-iniciar se executado diretamente
if __name__ == '__main__':
    import time
    
    print("Testando Background Scheduler...")
    
    if iniciar_scheduler_background():
        print("\nScheduler iniciado! Status:")
        status = obter_status_scheduler()
        print(f"  Ativo: {status['ativo']}")
        print(f"  Total de jobs: {status['total_jobs']}")
        print("\nPróximos jobs:")
        for job in status['jobs']:
            print(f"  - {job['nome']}: {job['proximo_execucao']}")
        
        print("\nPressione Ctrl+C para parar...")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nParando...")
            parar_scheduler()
    else:
        print("Falha ao iniciar scheduler")
