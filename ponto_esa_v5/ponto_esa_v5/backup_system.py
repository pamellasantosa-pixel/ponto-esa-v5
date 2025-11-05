"""
Sistema de Backup Automático para Ponto ESA
Implementa backup automático do banco de dados e logs de auditoria
"""

import sqlite3
import shutil
import os
import json
import gzip
from datetime import datetime, timedelta
import threading
import time

class BackupManager:
    def __init__(self, db_path="database/ponto_esa.db", backup_dir="backups"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.running = False
        self.backup_thread = None
        
        # Criar diretório de backup se não existir
        os.makedirs(backup_dir, exist_ok=True)
    
    def create_backup(self, compress=True):
        """
        Cria um backup do banco de dados
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"ponto_esa_backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copiar banco de dados
            shutil.copy2(self.db_path, backup_path)
            
            # Comprimir se solicitado
            if compress:
                compressed_path = backup_path + ".gz"
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remover arquivo não comprimido
                os.remove(backup_path)
                backup_path = compressed_path
            
            # Registrar backup no log
            self._log_backup(backup_path, os.path.getsize(backup_path))
            
            return backup_path
        
        except Exception as e:
            print(f"Erro ao criar backup: {e}")
            return None
    
    def _log_backup(self, backup_path, file_size):
        """
        Registra o backup no log de auditoria
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "backup_created",
            "file_path": backup_path,
            "file_size": file_size,
            "status": "success"
        }
        
        log_file = os.path.join(self.backup_dir, "backup_log.json")
        
        # Ler logs existentes
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # Adicionar novo log
        logs.append(log_entry)
        
        # Manter apenas os últimos 100 logs
        if len(logs) > 100:
            logs = logs[-100:]
        
        # Salvar logs
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def cleanup_old_backups(self, days_to_keep=60):
        """
        Remove backups antigos
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("ponto_esa_backup_") and (filename.endswith(".db") or filename.endswith(".db.gz")):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_date:
                        os.remove(file_path)
                        print(f"Backup antigo removido: {filename}")
        
        except Exception as e:
            print(f"Erro ao limpar backups antigos: {e}")
    
    def start_automatic_backup(self, interval_hours=24):
        """
        Inicia backup automático em intervalos regulares
        """
        if self.running:
            return
        
        self.running = True
        self.backup_thread = threading.Thread(
            target=self._backup_worker,
            args=(interval_hours,),
            daemon=True
        )
        self.backup_thread.start()
    
    def _backup_worker(self, interval_hours):
        """
        Worker thread para backup automático
        """
        while self.running:
            try:
                # Criar backup
                backup_path = self.create_backup()
                if backup_path:
                    print(f"Backup automático criado: {backup_path}")
                
                # Limpar backups antigos
                self.cleanup_old_backups()
                
                # Aguardar próximo backup
                time.sleep(interval_hours * 3600)
            
            except Exception as e:
                print(f"Erro no backup automático: {e}")
                time.sleep(3600)  # Aguardar 1 hora em caso de erro
    
    def stop_automatic_backup(self):
        """
        Para o backup automático
        """
        self.running = False
    
    def restore_backup(self, backup_path):
        """
        Restaura um backup
        """
        try:
            # Verificar se é arquivo comprimido
            if backup_path.endswith('.gz'):
                # Descomprimir temporariamente
                temp_path = backup_path[:-3]  # Remove .gz
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Restaurar
                shutil.copy2(temp_path, self.db_path)
                os.remove(temp_path)
            else:
                shutil.copy2(backup_path, self.db_path)
            
            return True
        
        except Exception as e:
            print(f"Erro ao restaurar backup: {e}")
            return False
    
    def get_backup_list(self):
        """
        Retorna lista de backups disponíveis
        """
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("ponto_esa_backup_") and (filename.endswith(".db") or filename.endswith(".db.gz")):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_stats = os.stat(file_path)
                    
                    backups.append({
                        "filename": filename,
                        "path": file_path,
                        "size": file_stats.st_size,
                        "created": datetime.fromtimestamp(file_stats.st_ctime),
                        "modified": datetime.fromtimestamp(file_stats.st_mtime)
                    })
            
            # Ordenar por data de criação (mais recente primeiro)
            backups.sort(key=lambda x: x["created"], reverse=True)
        
        except Exception as e:
            print(f"Erro ao listar backups: {e}")
        
        return backups

class AuditLogger:
    def __init__(self, log_file="logs/audit.log"):
        self.log_file = log_file
        
        # Criar diretório de logs se não existir
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def log_action(self, user_id, action, details=None, ip_address=None):
        """
        Registra uma ação no log de auditoria
        """
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "action": action,
                "details": details or {},
                "ip_address": ip_address,
                "session_id": self._get_session_id()
            }
            
            # Ler logs existentes
            logs = []
            if os.path.exists(self.log_file):
                try:
                    with open(self.log_file, 'r') as f:
                        logs = json.load(f)
                except:
                    logs = []
            
            # Adicionar novo log
            logs.append(log_entry)
            
            # Manter apenas os últimos 10000 logs
            if len(logs) > 10000:
                logs = logs[-10000:]
            
            # Salvar logs
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        
        except Exception as e:
            print(f"Erro ao registrar log de auditoria: {e}")
    
    def _get_session_id(self):
        """
        Gera um ID de sessão simples
        """
        import hashlib
        import time
        return hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    
    def get_user_logs(self, user_id, limit=100):
        """
        Retorna logs de um usuário específico
        """
        try:
            if not os.path.exists(self.log_file):
                return []
            
            with open(self.log_file, 'r') as f:
                all_logs = json.load(f)
            
            # Filtrar por usuário
            user_logs = [log for log in all_logs if log.get("user_id") == user_id]
            
            # Retornar os mais recentes
            return user_logs[-limit:]
        
        except Exception as e:
            print(f"Erro ao obter logs do usuário: {e}")
            return []
    
    def get_all_logs(self, limit=1000):
        """
        Retorna todos os logs
        """
        try:
            if not os.path.exists(self.log_file):
                return []
            
            with open(self.log_file, 'r') as f:
                all_logs = json.load(f)
            
            return all_logs[-limit:]
        
        except Exception as e:
            print(f"Erro ao obter logs: {e}")
            return []

# Instâncias globais
backup_manager = BackupManager()
audit_logger = AuditLogger()

def start_backup_system():
    """
    Inicia o sistema de backup automático
    """
    backup_manager.start_automatic_backup(interval_hours=24)

def create_manual_backup():
    """
    Cria um backup manual
    """
    return backup_manager.create_backup()

def log_user_action(user_id, action, details=None):
    """
    Registra uma ação do usuário
    """
    audit_logger.log_action(user_id, action, details)

