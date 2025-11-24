"""Shim de compatibilidade para imports não qualificados de notificações."""
try:
    from ponto_esa_v5.notifications import *  # type: ignore
    try:
        from ponto_esa_v5.notifications import __all__ as __ponto_all__  # type: ignore
        __all__ = __ponto_all__
    except Exception:
        __all__ = [name for name in globals() if not name.startswith('_')]
except Exception:
    class NotificationManager:
        def __init__(self):
            self.active_notifications = {}

        # stubs para evitar erros de import
        def get_notifications(self, user_id):
            return self.active_notifications.get(user_id, [])

        def add_notification(self, user_id, payload):
            self.active_notifications.setdefault(user_id, []).append(payload)

        def start_notification_system(self, *args, **kwargs):
            return True

        def stop_notifications(self, *args, **kwargs):
            return True

        def mark_notification_read(self, *args, **kwargs):
            return True

    notification_manager = NotificationManager()

    def start_notifications_for_user(*args, **kwargs):
        return notification_manager.start_notification_system(*args, **kwargs)

    def get_user_notifications(user_id):
        return notification_manager.get_notifications(user_id)

    def mark_notification_as_read(*args, **kwargs):
        return notification_manager.mark_notification_read(*args, **kwargs)

    def stop_user_notifications(*args, **kwargs):
        return notification_manager.stop_notifications(*args, **kwargs)

    __all__ = [
        "NotificationManager",
        "notification_manager",
        "start_notifications_for_user",
        "get_user_notifications",
        "mark_notification_as_read",
        "stop_user_notifications",
    ]