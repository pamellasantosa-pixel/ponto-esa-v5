"""
Sistema de Notificações Avançado para Ponto ESA
Implementa notificações em tempo real para lembrar os funcionários
de registrar ponto e controlar horas extras.
"""

import threading
import time
from datetime import datetime, timedelta
import sqlite3
import json
import os

class NotificationManager:
    def __init__(self):
        self.active_notifications = {}
        self.notification_threads = {}
        self.running = True
        
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
    
    def _notification_worker(self, user_id, meio_expediente, fim_expediente):
        """
        Worker thread que gerencia as notificações para um usuário
        """
        agora = datetime.now()
        
        # Calcular quando enviar notificação do meio do expediente
        meio_hoje = agora.replace(
            hour=meio_expediente.hour,
            minute=meio_expediente.minute,
            second=meio_expediente.second,
            microsecond=0
        )
        
        # Calcular quando enviar notificação do fim do expediente
        fim_hoje = agora.replace(
            hour=fim_expediente.hour,
            minute=fim_expediente.minute,
            second=fim_expediente.second,
            microsecond=0
        )
        
        # Se já passou do meio do expediente, não notificar
        if agora < meio_hoje:
            tempo_ate_meio = (meio_hoje - agora).total_seconds()
            if tempo_ate_meio > 0:
                time.sleep(tempo_ate_meio)
                if self.running and user_id in self.notification_threads:
                    self._send_notification(
                        user_id,
                        "⏰ Lembrete de Ponto Intermediário",
                        "Não se esqueça de registrar sua atividade atual!",
                        "intermediate"
                    )
        
        # Notificação do fim do expediente
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
        notification = {
            "id": f"{user_id}_{int(time.time())}",
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.now().isoformat(),
            "read": False,
            "extra_data": extra_data or {}
        }
        
        # Salvar notificação no banco de dados
        self._save_notification_to_db(notification)
        
        # Adicionar à lista de notificações ativas
        if user_id not in self.active_notifications:
            self.active_notifications[user_id] = []
        
        self.active_notifications[user_id].append(notification)
        
        # Manter apenas as últimas 10 notificações por usuário
        if len(self.active_notifications[user_id]) > 10:
            self.active_notifications[user_id] = self.active_notifications[user_id][-10:]
    
    def _save_notification_to_db(self, notification):
        """
        Salva a notificação no banco de dados
        """
        try:
            conn = sqlite3.connect("database/ponto_esa.db")
            c = conn.cursor()
            
            # Criar tabela de notificações se não existir
            c.execute("""
                CREATE TABLE IF NOT EXISTS Notificacoes (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    title TEXT,
                    message TEXT,
                    type TEXT,
                    timestamp TEXT,
                    read BOOLEAN DEFAULT FALSE,
                    extra_data TEXT,
                    FOREIGN KEY (user_id) REFERENCES Funcionarios (id)
                )
            """)
            
            c.execute("""
                INSERT INTO Notificacoes 
                (id, user_id, title, message, type, timestamp, read, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification["id"],
                notification["user_id"],
                notification["title"],
                notification["message"],
                notification["type"],
                notification["timestamp"],
                notification["read"],
                json.dumps(notification["extra_data"])
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Erro ao salvar notificação: {e}")
    
    def _check_shift_ended(self, user_id):
        """
        Verifica se o usuário já finalizou o expediente do dia
        """
        try:
            conn = sqlite3.connect("database/ponto_esa.db")
            c = conn.cursor()
            
            hoje = datetime.now().strftime("%Y-%m-%d")
            c.execute("""
                SELECT COUNT(*) FROM RegistrosPonto 
                WHERE id_funcionario = ? AND data_registro = ? AND tipo = 'FIM'
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
            conn = sqlite3.connect("database/ponto_esa.db")
            c = conn.cursor()
            
            c.execute("""
                UPDATE Notificacoes SET read = TRUE WHERE id = ?
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

