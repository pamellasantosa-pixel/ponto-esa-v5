"""Stubs para integração de timers usados pela UI.

Em produção, substitua por integração real com o sistema de timers
utilizado (por exemplo, APScheduler, Celery Beat, etc.).
"""


def schedule_task(name: str, when, callback, *args, **kwargs):
    """Agenda uma tarefa simples (stub)."""
    return True


def cancel_task(name: str):
    """Cancela tarefa agendada (stub)."""
    return True
