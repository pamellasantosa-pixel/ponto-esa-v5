"""
Worker de Notificações Automáticas - Ponto ExSA
===============================================
Este worker é um utilitário de teste e execução manual.
O scheduler real roda integrado ao app principal via background_scheduler.py

Para testes locais:
    python notification_worker.py --mode once    # Executar jobs uma vez
    python notification_worker.py --mode health  # Verificar sistema

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import os
import sys
import signal
import logging
from datetime import datetime, time
from typing import Optional

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Flag para shutdown gracioso
shutdown_requested = False

def signal_handler(signum, frame):
    """Handler para sinais de shutdown"""
    global shutdown_requested
    logger.info(f"Sinal {signum} recebido. Iniciando shutdown gracioso...")
    shutdown_requested = True

# Registrar handlers de sinal
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


def run_scheduler():
    """
    Executa o scheduler de notificações.
    Usa APScheduler para agendar jobs em horários específicos.
    """
    global shutdown_requested
    
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler não instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "apscheduler"])
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    
    # Importar funções de lembrete
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
        return
    
    # Criar scheduler com timezone de Brasília
    scheduler = BlockingScheduler(timezone='America/Sao_Paulo')
    
    logger.info("=" * 60)
    logger.info("🔔 NOTIFICATION WORKER - Ponto ExSA")
    logger.info("=" * 60)
    logger.info(f"Iniciado em: {get_datetime_br()}")
    logger.info("Jobs configurados:")
    
    # ============================================
    # JOB 1: Lembrete de Entrada (esqueceu de bater ponto)
    # Executa: 8:15, 8:30, 9:00 (dias úteis)
    # ============================================
    scheduler.add_job(
        job_lembrete_entrada,
        CronTrigger(hour='8', minute='15', day_of_week='mon-fri'),
        id='lembrete_entrada_8h15',
        name='Lembrete Entrada 8:15',
        misfire_grace_time=300
    )
    scheduler.add_job(
        job_lembrete_entrada,
        CronTrigger(hour='8', minute='30', day_of_week='mon-fri'),
        id='lembrete_entrada_8h30',
        name='Lembrete Entrada 8:30',
        misfire_grace_time=300
    )
    scheduler.add_job(
        job_lembrete_entrada,
        CronTrigger(hour='9', minute='0', day_of_week='mon-fri'),
        id='lembrete_entrada_9h00',
        name='Lembrete Entrada 9:00',
        misfire_grace_time=300
    )
    logger.info("  ✅ Lembrete de Entrada: 8:15, 8:30, 9:00 (Seg-Sex)")
    
    # ============================================
    # JOB 2: Lembrete de Saída (esqueceu de bater ponto)
    # Executa: 17:15, 17:30, 18:00 (dias úteis)
    # ============================================
    scheduler.add_job(
        job_lembrete_saida,
        CronTrigger(hour='17', minute='15', day_of_week='mon-fri'),
        id='lembrete_saida_17h15',
        name='Lembrete Saída 17:15',
        misfire_grace_time=300
    )
    scheduler.add_job(
        job_lembrete_saida,
        CronTrigger(hour='17', minute='30', day_of_week='mon-fri'),
        id='lembrete_saida_17h30',
        name='Lembrete Saída 17:30',
        misfire_grace_time=300
    )
    scheduler.add_job(
        job_lembrete_saida,
        CronTrigger(hour='18', minute='0', day_of_week='mon-fri'),
        id='lembrete_saida_18h00',
        name='Lembrete Saída 18:00',
        misfire_grace_time=300
    )
    logger.info("  ✅ Lembrete de Saída: 17:15, 17:30, 18:00 (Seg-Sex)")
    
    # ============================================
    # JOB 3: Alerta de Hora Extra (muito tempo em HE)
    # Executa: a cada 30 minutos entre 18:00 e 22:00 (dias úteis)
    # ============================================
    scheduler.add_job(
        job_alerta_hora_extra,
        CronTrigger(hour='18-22', minute='0,30', day_of_week='mon-fri'),
        id='alerta_hora_extra',
        name='Alerta Hora Extra',
        misfire_grace_time=300
    )
    logger.info("  ✅ Alerta Hora Extra: cada 30min das 18h às 22h (Seg-Sex)")
    
    # ============================================
    # JOB 4: Lembrete para Aprovadores (pendências)
    # Executa: 9:00, 14:00 (dias úteis)
    # ============================================
    scheduler.add_job(
        job_lembrete_aprovadores,
        CronTrigger(hour='9', minute='0', day_of_week='mon-fri'),
        id='aprovadores_manha',
        name='Lembrete Aprovadores Manhã',
        misfire_grace_time=300
    )
    scheduler.add_job(
        job_lembrete_aprovadores,
        CronTrigger(hour='14', minute='0', day_of_week='mon-fri'),
        id='aprovadores_tarde',
        name='Lembrete Aprovadores Tarde',
        misfire_grace_time=300
    )
    logger.info("  ✅ Lembrete Aprovadores: 9:00, 14:00 (Seg-Sex)")
    
    # ============================================
    # JOB 5: Lembrete Urgente Aprovadores (fim do dia)
    # Executa: 17:00 (dias úteis)
    # ============================================
    scheduler.add_job(
        job_lembrete_fim_dia_aprovadores,
        CronTrigger(hour='17', minute='0', day_of_week='mon-fri'),
        id='aprovadores_urgente',
        name='Lembrete Urgente Aprovadores',
        misfire_grace_time=300
    )
    logger.info("  ✅ Lembrete Urgente Aprovadores: 17:00 (Seg-Sex)")
    
    logger.info("=" * 60)
    logger.info("🚀 Scheduler iniciado. Aguardando próximo job...")
    logger.info("=" * 60)
    
    # Iniciar scheduler
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler interrompido.")
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler encerrado.")


def run_once():
    """
    Executa os jobs uma única vez (modo cron externo).
    Útil para Render Cron Jobs ou crontab tradicional.
    """
    try:
        from push_reminder_cron import executar_todos_jobs, get_datetime_br
    except ImportError as e:
        logger.error(f"Erro ao importar push_reminder_cron: {e}")
        return
    
    logger.info("=" * 60)
    logger.info("🔔 NOTIFICATION WORKER - Execução Única")
    logger.info(f"Data/Hora: {get_datetime_br()}")
    logger.info("=" * 60)
    
    resultado = executar_todos_jobs()
    
    logger.info("Resultado da execução:")
    for job_name, job_result in resultado.get('jobs', {}).items():
        status = job_result.get('status', 'executed')
        if status == 'skipped':
            logger.info(f"  ⏭️ {job_name}: pulado ({job_result.get('reason', '')})")
        else:
            enviados = job_result.get('lembretes_enviados', job_result.get('notificacoes_enviadas', 0))
            logger.info(f"  ✅ {job_name}: {enviados} notificações enviadas")
    
    logger.info("=" * 60)


def health_check():
    """Verifica se o sistema está funcionando"""
    try:
        from push_notifications import push_system
        from database import get_connection
        
        # Testar conexão com banco
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        # Verificar push
        push_ok = push_system.is_ready()
        
        logger.info("Health Check:")
        logger.info(f"  Database: ✅ OK")
        logger.info(f"  Push System: {'✅ OK' if push_ok else '⚠️ Não configurado'}")
        
        return True
    except Exception as e:
        logger.error(f"Health Check FALHOU: {e}")
        return False


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Worker de Notificações Automáticas - Ponto ExSA'
    )
    parser.add_argument(
        '--mode',
        choices=['scheduler', 'once', 'health'],
        default='scheduler',
        help='Modo de execução: scheduler (contínuo), once (única vez), health (verificação)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'health':
        success = health_check()
        sys.exit(0 if success else 1)
    elif args.mode == 'once':
        run_once()
    else:
        # Modo scheduler (padrão)
        health_check()
        run_scheduler()
