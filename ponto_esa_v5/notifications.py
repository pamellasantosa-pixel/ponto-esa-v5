"""
Compat shim para o módulo de notificações.
Esse arquivo preserva compatibilidade para importações não qualificadas
(`from notifications import notification_manager`), reexportando a
implementação principal que fica em `ponto_esa_v5.notifications`.
"""

try:
    # Prefer the package implementation inside the nested package
    from ponto_esa_v5.ponto_esa_v5.notifications import (
        NotificationManager,
        notification_manager,
        start_notifications_for_user,
        get_user_notifications,
        mark_notification_as_read,
        stop_user_notifications,
    )
except Exception:
    # Fallback minimal implementation if package import fails
    class NotificationManager:
        def __init__(self):
            self.active_notifications = {}
        def get_notifications(self, user_id):
            return self.active_notifications.get(user_id, [])
        def add_notification(self, user_id, payload):
            if user_id not in self.active_notifications:
                self.active_notifications[user_id] = []
            self.active_notifications[user_id].append(payload)
        def start_repeating_notification(self, *args, **kwargs):
            pass
        def stop_repeating_notification(self, *args, **kwargs):
            pass

    notification_manager = NotificationManager()

__all__ = [
    "NotificationManager",
    "notification_manager",
    "start_notifications_for_user",
    "get_user_notifications",
    "mark_notification_as_read",
    "stop_user_notifications",
]

# Instância global do gerenciador de notificações
notification_manager = NotificationManager()

def start_notifications_for_user(user_id, horario_inicio, horario_fim):
    """
    Função helper para iniciar notificações para um usuário
    """
    notification_manager.start_notification_system(user_id, horario_inicio, horario_fim)

def get_user_notifications(user_id):
    """
    Função helper para obter notificações de um usuário
    """
    return notification_manager.get_notifications(user_id)

def mark_notification_as_read(notification_id):
    """
    Função helper para marcar notificação como lida
    """
    notification_manager.mark_notification_read(notification_id)

def stop_user_notifications(user_id):
    """
    Função helper para parar notificações de um usuário
    """
    notification_manager.stop_notifications(user_id)

