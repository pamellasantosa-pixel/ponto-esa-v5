"""
Background Scheduler - Ponto ExSA
==================================
Scheduler de notificações que roda em background thread.
Integrado ao app principal (sem custo adicional no Render).

Esta solução usa APScheduler com BackgroundScheduler que roda
em uma thread separada, sem bloquear o app principal.

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import os
import sys
import logging
import threading
import atexit
from typing import Optional

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


def iniciar_scheduler_background() -> bool:
    """
    Inicia o scheduler de notificações em background.
    Usa BackgroundScheduler do APScheduler que roda em thread separada.
    
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
            # JOB 1: Lembrete de Entrada
            # Horários: 8:15, 8:30, 9:00 (dias úteis)
            # Notifica funcionários que esqueceram de bater entrada
            # ============================================
            _scheduler.add_job(
                job_lembrete_entrada,
                CronTrigger(hour=8, minute=15, day_of_week='mon-fri'),
                id='entrada_8h15',
                name='Lembrete Entrada 8:15',
                replace_existing=True
            )
            _scheduler.add_job(
                job_lembrete_entrada,
                CronTrigger(hour=8, minute=30, day_of_week='mon-fri'),
                id='entrada_8h30',
                name='Lembrete Entrada 8:30',
                replace_existing=True
            )
            _scheduler.add_job(
                job_lembrete_entrada,
                CronTrigger(hour=9, minute=0, day_of_week='mon-fri'),
                id='entrada_9h00',
                name='Lembrete Entrada 9:00',
                replace_existing=True
            )
            logger.info("  ✅ Lembrete de Entrada: 8:15, 8:30, 9:00 (Seg-Sex)")
            
            # ============================================
            # JOB 2: Lembrete de Saída
            # Horários: 17:15, 17:30, 18:00 (dias úteis)
            # Notifica funcionários que esqueceram de bater saída
            # ============================================
            _scheduler.add_job(
                job_lembrete_saida,
                CronTrigger(hour=17, minute=15, day_of_week='mon-fri'),
                id='saida_17h15',
                name='Lembrete Saída 17:15',
                replace_existing=True
            )
            _scheduler.add_job(
                job_lembrete_saida,
                CronTrigger(hour=17, minute=30, day_of_week='mon-fri'),
                id='saida_17h30',
                name='Lembrete Saída 17:30',
                replace_existing=True
            )
            _scheduler.add_job(
                job_lembrete_saida,
                CronTrigger(hour=18, minute=0, day_of_week='mon-fri'),
                id='saida_18h00',
                name='Lembrete Saída 18:00',
                replace_existing=True
            )
            logger.info("  ✅ Lembrete de Saída: 17:15, 17:30, 18:00 (Seg-Sex)")
            
            # ============================================
            # JOB 3: Alerta de Hora Extra
            # Horários: cada 30min entre 18h e 22h (dias úteis)
            # Notifica funcionários em hora extra prolongada
            # ============================================
            _scheduler.add_job(
                job_alerta_hora_extra,
                CronTrigger(hour='18-22', minute='0,30', day_of_week='mon-fri'),
                id='hora_extra',
                name='Alerta Hora Extra',
                replace_existing=True
            )
            logger.info("  ✅ Alerta Hora Extra: cada 30min das 18h às 22h (Seg-Sex)")
            
            # ============================================
            # JOB 4: Lembrete para Aprovadores
            # Horários: 9:00, 14:00 (dias úteis)
            # Notifica gestores sobre solicitações pendentes
            # ============================================
            _scheduler.add_job(
                job_lembrete_aprovadores,
                CronTrigger(hour=9, minute=0, day_of_week='mon-fri'),
                id='aprovadores_9h',
                name='Lembrete Aprovadores 9:00',
                replace_existing=True
            )
            _scheduler.add_job(
                job_lembrete_aprovadores,
                CronTrigger(hour=14, minute=0, day_of_week='mon-fri'),
                id='aprovadores_14h',
                name='Lembrete Aprovadores 14:00',
                replace_existing=True
            )
            logger.info("  ✅ Lembrete Aprovadores: 9:00, 14:00 (Seg-Sex)")
            
            # ============================================
            # JOB 5: Lembrete Urgente Aprovadores
            # Horário: 17:00 (dias úteis)
            # Notifica gestores sobre solicitações urgentes
            # ============================================
            _scheduler.add_job(
                job_lembrete_fim_dia_aprovadores,
                CronTrigger(hour=17, minute=0, day_of_week='mon-fri'),
                id='aprovadores_urgente',
                name='Lembrete Urgente Aprovadores 17:00',
                replace_existing=True
            )
            logger.info("  ✅ Lembrete Urgente Aprovadores: 17:00 (Seg-Sex)")
            
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
