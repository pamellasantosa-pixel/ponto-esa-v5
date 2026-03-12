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
import time as time_module
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
    Executa o scheduler de notificações com configuração dinâmica do banco.
    Reutiliza o background_scheduler para respeitar horários salvos na UI.
    """
    global shutdown_requested

    try:
        from background_scheduler import (
            iniciar_scheduler_background,
            parar_scheduler,
            obter_status_scheduler,
        )
    except Exception as e:
        logger.error(f"Erro ao importar background_scheduler: {e}")
        return

    logger.info("=" * 60)
    logger.info("🔔 NOTIFICATION WORKER - Ponto ExSA")
    logger.info("=" * 60)
    logger.info("Iniciando scheduler com configurações salvas no banco...")

    if not iniciar_scheduler_background():
        logger.error("Falha ao iniciar scheduler de notificações")
        return

    status = obter_status_scheduler()
    logger.info("Scheduler ativo=%s | jobs=%s", status.get("ativo"), status.get("total_jobs"))

    try:
        while not shutdown_requested:
            time_module.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler interrompido.")
    finally:
        parar_scheduler()
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
        from database import get_connection, return_connection
        
        # Testar conexão com banco
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return_connection(conn)
        
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
