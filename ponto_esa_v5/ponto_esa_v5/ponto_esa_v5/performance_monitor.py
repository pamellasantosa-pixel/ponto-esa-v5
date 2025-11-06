"""
Sistema de Monitoramento de Performance para Ponto ESA
Monitora performance do aplicativo e otimiza consultas ao banco
"""

import sqlite3
import time
import psutil
import threading
from datetime import datetime, timedelta
from functools import wraps
import json
import os

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "database_queries": [],
            "page_loads": [],
            "system_resources": [],
            "errors": []
        }
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """
        Inicia o monitoramento de performance
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_worker,
            daemon=True
        )
        self.monitor_thread.start()
    
    def _monitor_worker(self):
        """
        Worker thread para monitoramento contínuo
        """
        while self.monitoring:
            try:
                # Coletar métricas do sistema
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                system_metric = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "disk_percent": disk.percent,
                    "disk_free": disk.free
                }
                
                self.metrics["system_resources"].append(system_metric)
                
                # Manter apenas as últimas 1000 métricas
                if len(self.metrics["system_resources"]) > 1000:
                    self.metrics["system_resources"] = self.metrics["system_resources"][-1000:]
                
                time.sleep(60)  # Coletar a cada minuto
            
            except Exception as e:
                self.log_error("monitor_worker", str(e))
                time.sleep(60)
    
    def stop_monitoring(self):
        """
        Para o monitoramento
        """
        self.monitoring = False
    
    def log_database_query(self, query, execution_time, rows_affected=0):
        """
        Registra uma consulta ao banco de dados
        """
        query_metric = {
            "timestamp": datetime.now().isoformat(),
            "query": query[:200],  # Primeiros 200 caracteres
            "execution_time": execution_time,
            "rows_affected": rows_affected
        }
        
        self.metrics["database_queries"].append(query_metric)
        
        # Manter apenas as últimas 1000 consultas
        if len(self.metrics["database_queries"]) > 1000:
            self.metrics["database_queries"] = self.metrics["database_queries"][-1000:]
    
    def log_page_load(self, page_name, load_time):
        """
        Registra o tempo de carregamento de uma página
        """
        page_metric = {
            "timestamp": datetime.now().isoformat(),
            "page_name": page_name,
            "load_time": load_time
        }
        
        self.metrics["page_loads"].append(page_metric)
        
        # Manter apenas os últimos 1000 carregamentos
        if len(self.metrics["page_loads"]) > 1000:
            self.metrics["page_loads"] = self.metrics["page_loads"][-1000:]
    
    def log_error(self, component, error_message):
        """
        Registra um erro
        """
        error_metric = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "error_message": error_message
        }
        
        self.metrics["errors"].append(error_metric)
        
        # Manter apenas os últimos 1000 erros
        if len(self.metrics["errors"]) > 1000:
            self.metrics["errors"] = self.metrics["errors"][-1000:]
    
    def get_performance_report(self):
        """
        Gera um relatório de performance
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_queries": len(self.metrics["database_queries"]),
                "total_page_loads": len(self.metrics["page_loads"]),
                "total_errors": len(self.metrics["errors"]),
                "avg_query_time": 0,
                "avg_page_load_time": 0,
                "current_system_status": {}
            },
            "slow_queries": [],
            "slow_pages": [],
            "recent_errors": []
        }
        
        # Calcular tempo médio de consultas
        if self.metrics["database_queries"]:
            total_time = sum(q["execution_time"] for q in self.metrics["database_queries"])
            report["summary"]["avg_query_time"] = total_time / len(self.metrics["database_queries"])
            
            # Consultas lentas (> 1 segundo)
            report["slow_queries"] = [
                q for q in self.metrics["database_queries"] 
                if q["execution_time"] > 1.0
            ][-10:]  # Últimas 10
        
        # Calcular tempo médio de carregamento de páginas
        if self.metrics["page_loads"]:
            total_time = sum(p["load_time"] for p in self.metrics["page_loads"])
            report["summary"]["avg_page_load_time"] = total_time / len(self.metrics["page_loads"])
            
            # Páginas lentas (> 3 segundos)
            report["slow_pages"] = [
                p for p in self.metrics["page_loads"] 
                if p["load_time"] > 3.0
            ][-10:]  # Últimas 10
        
        # Erros recentes
        report["recent_errors"] = self.metrics["errors"][-10:]
        
        # Status atual do sistema
        if self.metrics["system_resources"]:
            latest = self.metrics["system_resources"][-1]
            report["summary"]["current_system_status"] = {
                "cpu_percent": latest["cpu_percent"],
                "memory_percent": latest["memory_percent"],
                "disk_percent": latest["disk_percent"]
            }
        
        return report
    
    def save_metrics_to_file(self, filename="performance_metrics.json"):
        """
        Salva métricas em arquivo
        """
        try:
            os.makedirs("logs", exist_ok=True)
            filepath = os.path.join("logs", filename)
            
            with open(filepath, 'w') as f:
                json.dump(self.metrics, f, indent=2)
            
            return filepath
        except Exception as e:
            self.log_error("save_metrics", str(e))
            return None

class DatabaseOptimizer:
    def __init__(self, db_path="database/ponto_esa.db"):
        self.db_path = db_path
    
    def optimize_database(self):
        """
        Otimiza o banco de dados
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Criar índices para melhorar performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_registros_funcionario_data ON RegistrosPonto(id_funcionario, data_registro)",
                "CREATE INDEX IF NOT EXISTS idx_registros_tipo ON RegistrosPonto(tipo)",
                "CREATE INDEX IF NOT EXISTS idx_registros_data ON RegistrosPonto(data_registro)",
                "CREATE INDEX IF NOT EXISTS idx_funcionarios_usuario ON Funcionarios(usuario)",
                "CREATE INDEX IF NOT EXISTS idx_notificacoes_user ON Notificacoes(user_id, timestamp)"
            ]
            
            for index_sql in indexes:
                c.execute(index_sql)
            
            # Analisar tabelas para otimizar planos de consulta
            c.execute("ANALYZE")
            
            # Vacuum para compactar banco
            c.execute("VACUUM")
            
            conn.commit()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"Erro ao otimizar banco: {e}")
            return False
    
    def get_database_stats(self):
        """
        Retorna estatísticas do banco de dados
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            stats = {}
            
            # Tamanho das tabelas
            tables = ["Funcionarios", "RegistrosPonto", "Notificacoes"]
            for table in tables:
                try:
                    c.execute(f"SELECT COUNT(*) FROM {table}")
                    count = c.fetchone()[0]
                    stats[f"{table}_count"] = count
                except:
                    stats[f"{table}_count"] = 0
            
            # Tamanho do arquivo
            stats["file_size"] = os.path.getsize(self.db_path)
            
            # Índices existentes
            c.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in c.fetchall()]
            stats["indexes"] = indexes
            
            conn.close()
            return stats
        
        except Exception as e:
            print(f"Erro ao obter estatísticas: {e}")
            return {}

def monitor_database_query(func):
    """
    Decorator para monitorar consultas ao banco
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log da consulta (se disponível)
            if hasattr(performance_monitor, 'log_database_query'):
                query = kwargs.get('query', 'Unknown query')
                performance_monitor.log_database_query(query, execution_time)
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            if hasattr(performance_monitor, 'log_error'):
                performance_monitor.log_error('database_query', str(e))
            raise
    
    return wrapper

def monitor_page_load(page_name):
    """
    Decorator para monitorar carregamento de páginas
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                load_time = time.time() - start_time
                
                if hasattr(performance_monitor, 'log_page_load'):
                    performance_monitor.log_page_load(page_name, load_time)
                
                return result
            except Exception as e:
                load_time = time.time() - start_time
                if hasattr(performance_monitor, 'log_error'):
                    performance_monitor.log_error(page_name, str(e))
                raise
        
        return wrapper
    return decorator

# Instâncias globais
performance_monitor = PerformanceMonitor()
database_optimizer = DatabaseOptimizer()

def start_performance_monitoring():
    """
    Inicia o monitoramento de performance
    """
    performance_monitor.start_monitoring()

def optimize_system():
    """
    Otimiza o sistema
    """
    return database_optimizer.optimize_database()

def get_system_report():
    """
    Gera relatório do sistema
    """
    return performance_monitor.get_performance_report()

