"""
Sistema de Notificações Avançado para Ponto ESA
Implementa notificações em tempo real para lembrar os funcionários
de registrar ponto e controlar horas extras.
"""

import threading
import time
from datetime import datetime, timedelta
import json
import os
import sqlite3
from database_postgresql import get_connection

def _load_default_interval():
    raw_value = os.getenv("NOTIFICATION_REMINDER_INTERVAL", "60")
    try:
        parsed = int(raw_value)
        return parsed if parsed > 0 else 60
    except ValueError:
        return 60


DEFAULT_REMINDER_INTERVAL = _load_default_interval()

class NotificationManager:
    def __init__(self):
        self.active_notifications = {}
        self.notification_threads = {}
        self.running = True
        self.repeating_jobs = {}
        self.default_reminder_interval = DEFAULT_REMINDER_INTERVAL
        
    def start_notification_system(self, user_id, horario_inicio, horario_fim):
        """
        Inicia o sistema de notificações para um usuário específico
        """
        if user_id in self.notification_threads:
            self.stop_notifications(user_id)
        
        # Calcular horários de notificação
        inicio = datetime.strptime(horario_inicio, "%H:%M:%S")
        fim = datetime.strptime(horario_fim, "%H:%M:%S")
        
        # Notificação no meio do expediente
        meio_expediente = inicio + (fim - inicio) / 2
        
        # Criar thread para notificações
        thread = threading.Thread(
            target=self._notification_worker,
            args=(user_id, meio_expediente, fim),
            daemon=True
        )
        
        self.notification_threads[user_id] = thread
        thread.start()
    
    def _notification_worker(self, user_id, meio_expediente, fim):
        """
        Worker thread que gerencia as notificações ao longo do dia
        """
        hoje = datetime.now().date()
        meio_hoje = datetime.combine(hoje, meio_expediente.time())
        fim_hoje = datetime.combine(hoje, fim.time())
        
        # Notificação no meio do expediente
        agora = datetime.now()
        if agora < meio_hoje:
            tempo_ate_meio = (meio_hoje - agora).total_seconds()
            if tempo_ate_meio > 0:
                time.sleep(tempo_ate_meio)
                if self.running and user_id in self.notification_threads:
                    self._send_notification(
                        user_id,
                        "⏰ Lembrete de Registro",
                        "Não esqueça de registrar seu ponto intermediário!",
                        "midshift"
                    )
        
        # Notificação no fim do expediente
        agora = datetime.now()
        if agora < fim_hoje:
            tempo_ate_fim = (fim_hoje - agora).total_seconds()
            if tempo_ate_fim > 0:
                time.sleep(tempo_ate_fim)
                if self.running and user_id in self.notification_threads:
                    self._send_notification(
                        user_id,
                        "🌆 Fim do Expediente",
                        "Seu horário de trabalho terminou. Deseja finalizar o expediente?",
                        "end_shift"
                    )
        
        # Notificações de hora extra (a cada hora após o fim)
        hora_extra_count = 1
        while self.running and user_id in self.notification_threads:
            proxima_notificacao = fim_hoje + timedelta(hours=hora_extra_count)
            agora = datetime.now()
            
            if agora < proxima_notificacao:
                tempo_ate_proxima = (proxima_notificacao - agora).total_seconds()
                if tempo_ate_proxima > 0:
                    time.sleep(tempo_ate_proxima)
            
            if self.running and user_id in self.notification_threads:
                # Verificar se o usuário ainda não finalizou o expediente
                if not self._check_shift_ended(user_id):
                    self._send_notification(
                        user_id,
                        "⚠️ Hora Extra Detectada",
                        f"Você está fazendo {hora_extra_count}h extra(s). Deseja finalizar o expediente?",
                        "overtime",
                        {"hours": hora_extra_count}
                    )
                    hora_extra_count += 1
                else:
                    break
            else:
                break
    
    def _send_notification(self, user_id, title, message, notification_type, extra_data=None):
        """
        Envia uma notificação para o usuário
        """
        base_extra = extra_data or {}

        notification = {
            "id": f"{user_id}_{int(time.time())}",
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.now().isoformat(),
            "read": False,
            "extra_data": base_extra,
            "requires_response": base_extra.get("requires_response", False)
        }

        for key, value in base_extra.items():
            if key not in notification:
                notification[key] = value
        
        # Salvar notificação no banco de dados
        self._save_notification_to_db(notification)
        
        # Adicionar à lista de notificações ativas
        if user_id not in self.active_notifications:
            self.active_notifications[user_id] = []
        
        self.active_notifications[user_id].append(notification)
        
        # Manter apenas as últimas 10 notificações por usuário
        if len(self.active_notifications[user_id]) > 10:
            self.active_notifications[user_id] = self.active_notifications[user_id][-10:]

    def add_notification(self, user_id, payload):
        """Adiciona uma notificação a partir de um payload flexível."""
        if not isinstance(payload, dict):
            raise ValueError("payload deve ser um dicionário")

        title = payload.get("title", "Notificação")
        message = payload.get("message", "")
        notification_type = payload.get("type", "general")

        extra_data = payload.copy()
        extra_data.pop("title", None)
        extra_data.pop("message", None)
        extra_data.pop("type", None)

        self._send_notification(user_id, title, message, notification_type, extra_data)

    def start_repeating_notification(self, job_id, user_id, payload, interval_seconds=None, stop_condition=None):
        """Inicia uma notificação repetitiva até que a condição de parada seja atendida."""
        if job_id in self.repeating_jobs:
            # Já existe um job ativo para este identificador
            return

        job_control = {"active": True}
        self.repeating_jobs[job_id] = job_control

        interval = interval_seconds if interval_seconds is not None else self.default_reminder_interval

        def worker():
            try:
                while self.running and job_control.get("active", False):
                    time.sleep(interval)

                    if stop_condition and stop_condition():
                        break

                    self.add_notification(user_id, payload)
            finally:
                # Remover job ao finalizar
                self.repeating_jobs.pop(job_id, None)

        thread = threading.Thread(target=worker, daemon=True)
        job_control["thread"] = thread
        thread.start()

    def stop_repeating_notification(self, job_id):
        """Solicita a parada de um job de notificações repetitivas."""
        job = self.repeating_jobs.get(job_id)
        if job:
            job["active"] = False

    def _save_notification_to_db(self, notification):
        """Persiste notificações em PostgreSQL ou SQLite, conforme disponível."""
        conn = None
        driver = 'unknown'

        try:
            # Tentar conexão via camada compartilhada
            try:
                conn = get_connection()
            except Exception:
                conn = None

            if conn is None:
                # Fallback explícito para SQLite local
                os.makedirs('database', exist_ok=True)
                conn = sqlite3.connect('database/ponto_esa.db')

            driver = type(conn).__module__
            cursor = conn.cursor()

            if 'psycopg2' in driver:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notificacoes (
                        id TEXT PRIMARY KEY,
                        user_id VARCHAR(255),
                        title TEXT,
                        message TEXT,
                        type TEXT,
                        timestamp TEXT,
                        read BOOLEAN DEFAULT FALSE,
                        extra_data JSON
                    )
                ''')

                cursor.execute(
                    '''INSERT INTO notificacoes
                       (id, user_id, title, message, type, timestamp, read, extra_data)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                    (
                        notification['id'],
                        notification['user_id'],
                        notification['title'],
                        notification['message'],
                        notification['type'],
                        notification['timestamp'],
                        int(bool(notification['read'])),
                        json.dumps(notification.get('extra_data', {}))
                    )
                )
            else:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS Notificacoes (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        title TEXT,
                        message TEXT,
                        type TEXT,
                        timestamp TEXT,
                        read INTEGER DEFAULT 0,
                        extra_data TEXT
                    )
                ''')

                cursor.execute(
                    '''INSERT INTO Notificacoes
                       (id, user_id, title, message, type, timestamp, read, extra_data)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (
                        notification['id'],
                        notification['user_id'],
                        notification['title'],
                        notification['message'],
                        notification['type'],
                        notification['timestamp'],
                        int(bool(notification['read'])),
                        json.dumps(notification.get('extra_data', {}))
                    )
                )

            conn.commit()
        except Exception as exc:
            print(f"Erro ao salvar notificação (driver={driver}): {exc}")
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
    
    def _check_shift_ended(self, user_id):
        """
        Verifica se o usuário já finalizou o expediente do dia
        """
        try:
            conn = get_connection()
            c = conn.cursor()
            
            hoje = datetime.now().strftime("%Y-%m-%d")
            c.execute("""
                SELECT COUNT(*) FROM registros_ponto 
                WHERE usuario = %s AND DATE(data_hora) = %s AND tipo = 'Fim'
            """, (user_id, hoje))
            
            result = c.fetchone()[0]
            conn.close()
            
            return result > 0
        except:
            return False
    
    def get_notifications(self, user_id):
        """
        Retorna as notificações ativas para um usuário
        """
        return self.active_notifications.get(user_id, [])
    
    def mark_notification_read(self, notification_id):
        """
        Marca uma notificação como lida
        """
        try:
            conn = get_connection()
            c = conn.cursor()
            
            c.execute("""
                UPDATE notificacoes SET read = TRUE WHERE id = %s
            """, (notification_id,))
            
            conn.commit()
            conn.close()
            
            # Atualizar também na memória
            for user_notifications in self.active_notifications.values():
                for notification in user_notifications:
                    if notification["id"] == notification_id:
                        notification["read"] = True
                        break
        except Exception as e:
            print(f"Erro ao marcar notificação como lida: {e}")
    
    def stop_notifications(self, user_id):
        """
        Para as notificações para um usuário específico
        """
        if user_id in self.notification_threads:
            del self.notification_threads[user_id]
        
        if user_id in self.active_notifications:
            del self.active_notifications[user_id]
    
    def stop_all_notifications(self):
        """
        Para todas as notificações
        """
        self.running = False
        self.notification_threads.clear()
        self.active_notifications.clear()
        for job in self.repeating_jobs.values():
            job["active"] = False
        self.repeating_jobs.clear()

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

