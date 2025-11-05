import time
import json

# Ajustar caminho se necessário
from pathlib import Path
import sys

# Garantir que o pacote ponto_esa_v5 está no path
repo_root = Path(__file__).resolve().parents[1]
project_folder = repo_root / 'ponto_esa_v5'
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
if str(project_folder) not in sys.path:
    sys.path.insert(0, str(project_folder))

from ponto_esa_v5.notifications import notification_manager  # type: ignore[import-not-found]


def print_state(tag):
    print('\n---', tag, '---')
    for user_id, nots in notification_manager.active_notifications.items():
        print(f"User {user_id}: {len(nots)} active in-memory notifications")
        for n in nots:
            print(" ", json.dumps(n, ensure_ascii=False))
    print('Repeating jobs:', list(notification_manager.repeating_jobs.keys()))


if __name__ == '__main__':
    user = 'gestor_teste'

    # 1) adicionar notificação única
    notification_manager.add_notification(user, {
        'type': 'test_single',
        'title': 'Teste Único',
        'message': 'Notificação única de teste',
        'solicitacao_id': 123,
        'requires_response': False
    })

    print_state('após add_notification')

    # 2) iniciar notificação recorrente com intervalo curto (2s)
    start = time.time()

    def stop_condition():
        # parar após ~6 segundos
        return time.time() - start > 6

    payload = {
        'type': 'test_repeating',
        'title': 'Lembrete Recorrente',
        'message': 'Lembrete periódico para teste',
        'solicitacao_id': 999,
        'requires_response': True
    }

    job_id = 'test_job_999'
    notification_manager.start_repeating_notification(job_id, user, payload, interval_seconds=2, stop_condition=stop_condition)

    print('\nEsperando 8 segundos para coletar execuções do job...')
    time.sleep(8)

    print_state('após execução do job')

    # 3) solicitar parada (idempotente se já parou)
    notification_manager.stop_repeating_notification(job_id)
    time.sleep(0.5)
    print_state('após stop_repeating_notification')

    print('\nTeste concluído')
