"""
Sistema de Backup Automático para PostgreSQL - Ponto ExSA
=========================================================
Implementa backup automático do banco de dados PostgreSQL (Neon)
com exportação para JSON/CSV e restauração.

@author: Pâmella SAR - Expressão Socioambiental
@version: 2.0.0 - PostgreSQL/Neon
"""

import os
import json
import gzip
import csv
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from io import StringIO, BytesIO
import threading
import time

# Configurar logging
logger = logging.getLogger(__name__)

# Importar conexão
try:
    from database import get_connection, SQL_PLACEHOLDER, USE_POSTGRESQL
except ImportError:
    USE_POSTGRESQL = True
    from ponto_esa_v5.database import get_connection, SQL_PLACEHOLDER


class PostgreSQLBackupManager:
    """
    Gerenciador de backups para PostgreSQL/Neon.
    
    Como o Neon é um serviço gerenciado, não podemos fazer pg_dump tradicional.
    Este sistema exporta os dados para JSON/CSV que pode ser usado para restauração.
    """
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = backup_dir
        self.running = False
        self.backup_thread = None
        
        # Criar diretório de backup se não existir
        os.makedirs(backup_dir, exist_ok=True)
        
        # Tabelas a serem incluídas no backup
        self.tables_to_backup = [
            'usuarios',
            'registros_ponto',
            'ausencias',
            'projetos',
            'solicitacoes_horas_extras',
            'horas_extras_ativas',
            'banco_horas',
            'atestados',
            'configuracoes',
            'jornada_semanal',
            'feriados',
            'solicitacoes_correcao_registro',
            'uploads'
        ]
    
    def get_table_data(self, table_name: str) -> Tuple[List[str], List[tuple]]:
        """
        Obtém dados de uma tabela.
        
        Returns:
            Tuple com (colunas, dados)
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Obter colunas
            cursor.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            columns = [row[0] for row in cursor.fetchall()]
            
            if not columns:
                return [], []
            
            # Obter dados
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            return columns, rows
            
        except Exception as e:
            logger.error(f"Erro ao obter dados da tabela {table_name}: {e}")
            return [], []
        finally:
            if conn:
                conn.close()
    
    def export_to_json(self, compress: bool = True) -> Optional[str]:
        """
        Exporta todas as tabelas para um arquivo JSON.
        
        Args:
            compress: Se True, comprime o arquivo com gzip
            
        Returns:
            Caminho do arquivo de backup ou None em caso de erro
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_data = {
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'version': '2.0.0',
                    'type': 'postgresql_export',
                    'tables': []
                },
                'data': {}
            }
            
            for table in self.tables_to_backup:
                try:
                    columns, rows = self.get_table_data(table)
                    
                    if columns:
                        # Converter rows para lista de dicts
                        table_data = []
                        for row in rows:
                            row_dict = {}
                            for i, col in enumerate(columns):
                                value = row[i]
                                # Converter tipos não serializáveis
                                if isinstance(value, (datetime, )):
                                    value = value.isoformat()
                                elif isinstance(value, bytes):
                                    value = value.decode('utf-8', errors='ignore')
                                elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, type(None), list, dict)):
                                    value = str(value)
                                row_dict[col] = value
                            table_data.append(row_dict)
                        
                        backup_data['data'][table] = table_data
                        backup_data['metadata']['tables'].append({
                            'name': table,
                            'columns': columns,
                            'rows': len(rows)
                        })
                        
                        logger.info(f"Tabela {table}: {len(rows)} registros exportados")
                        
                except Exception as e:
                    logger.warning(f"Erro ao exportar tabela {table}: {e}")
                    continue
            
            # Salvar arquivo
            json_content = json.dumps(backup_data, ensure_ascii=False, indent=2, default=str)
            
            if compress:
                filename = f"ponto_esa_backup_{timestamp}.json.gz"
                filepath = os.path.join(self.backup_dir, filename)
                
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(json_content)
            else:
                filename = f"ponto_esa_backup_{timestamp}.json"
                filepath = os.path.join(self.backup_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(json_content)
            
            # Registrar no log
            self._log_backup(filepath, os.path.getsize(filepath), 'json')
            
            logger.info(f"Backup JSON criado: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Erro ao criar backup JSON: {e}")
            return None
    
    def export_to_csv(self) -> Optional[str]:
        """
        Exporta todas as tabelas para arquivos CSV (um por tabela).
        
        Returns:
            Caminho do diretório com os CSVs ou None em caso de erro
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_dir = os.path.join(self.backup_dir, f"csv_backup_{timestamp}")
            os.makedirs(csv_dir, exist_ok=True)
            
            for table in self.tables_to_backup:
                try:
                    columns, rows = self.get_table_data(table)
                    
                    if columns and rows:
                        filepath = os.path.join(csv_dir, f"{table}.csv")
                        
                        with open(filepath, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerow(columns)
                            
                            for row in rows:
                                # Converter valores para string
                                csv_row = []
                                for value in row:
                                    if value is None:
                                        csv_row.append('')
                                    elif isinstance(value, datetime):
                                        csv_row.append(value.isoformat())
                                    else:
                                        csv_row.append(str(value))
                                writer.writerow(csv_row)
                        
                        logger.info(f"CSV exportado: {table}.csv ({len(rows)} registros)")
                        
                except Exception as e:
                    logger.warning(f"Erro ao exportar CSV {table}: {e}")
                    continue
            
            # Criar arquivo de metadados
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'tables': self.tables_to_backup
            }
            with open(os.path.join(csv_dir, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Backup CSV criado: {csv_dir}")
            return csv_dir
            
        except Exception as e:
            logger.error(f"Erro ao criar backup CSV: {e}")
            return None
    
    def restore_from_json(self, filepath: str, clear_existing: bool = False) -> Tuple[bool, str]:
        """
        Restaura dados de um backup JSON.
        
        Args:
            filepath: Caminho do arquivo de backup
            clear_existing: Se True, limpa os dados existentes antes de restaurar
            
        Returns:
            Tuple (sucesso, mensagem)
        """
        try:
            # Ler arquivo
            if filepath.endswith('.gz'):
                with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                    backup_data = json.load(f)
            else:
                with open(filepath, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
            
            if 'data' not in backup_data:
                return False, "Formato de backup inválido"
            
            conn = get_connection()
            cursor = conn.cursor()
            
            restored_tables = []
            errors = []
            
            for table_name, table_data in backup_data['data'].items():
                if not table_data:
                    continue
                    
                try:
                    # Limpar tabela se solicitado
                    if clear_existing:
                        cursor.execute(f"DELETE FROM {table_name}")
                    
                    # Obter colunas do primeiro registro
                    columns = list(table_data[0].keys())
                    
                    # Inserir dados
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_str = ', '.join(columns)
                    
                    for row in table_data:
                        values = [row.get(col) for col in columns]
                        
                        try:
                            cursor.execute(f"""
                                INSERT INTO {table_name} ({columns_str})
                                VALUES ({placeholders})
                                ON CONFLICT DO NOTHING
                            """, values)
                        except Exception as insert_error:
                            # Log mas continua
                            logger.warning(f"Erro ao inserir em {table_name}: {insert_error}")
                    
                    restored_tables.append(table_name)
                    logger.info(f"Tabela {table_name} restaurada: {len(table_data)} registros")
                    
                except Exception as e:
                    errors.append(f"{table_name}: {str(e)}")
                    logger.error(f"Erro ao restaurar tabela {table_name}: {e}")
            
            conn.commit()
            conn.close()
            
            if errors:
                return True, f"Restauração parcial. Tabelas OK: {restored_tables}. Erros: {errors}"
            
            return True, f"Restauração completa. Tabelas: {restored_tables}"
            
        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            return False, f"Erro: {str(e)}"
    
    def _log_backup(self, filepath: str, file_size: int, backup_type: str):
        """Registra o backup no log."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "backup_created",
            "file_path": filepath,
            "file_size": file_size,
            "type": backup_type,
            "status": "success"
        }
        
        log_file = os.path.join(self.backup_dir, "backup_log.json")
        
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(log_entry)
        
        # Manter apenas os últimos 100 logs
        if len(logs) > 100:
            logs = logs[-100:]
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Remove backups antigos."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            removed = 0
            
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("ponto_esa_backup_"):
                    file_path = os.path.join(self.backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    
                    if file_time < cutoff_date:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            removed += 1
                            logger.info(f"Backup antigo removido: {filename}")
            
            # Remover diretórios CSV antigos
            for dirname in os.listdir(self.backup_dir):
                if dirname.startswith("csv_backup_"):
                    dir_path = os.path.join(self.backup_dir, dirname)
                    if os.path.isdir(dir_path):
                        dir_time = datetime.fromtimestamp(os.path.getctime(dir_path))
                        if dir_time < cutoff_date:
                            import shutil
                            shutil.rmtree(dir_path)
                            removed += 1
            
            logger.info(f"Limpeza concluída: {removed} backups removidos")
            
        except Exception as e:
            logger.error(f"Erro ao limpar backups antigos: {e}")
    
    def start_automatic_backup(self, interval_hours: int = 24):
        """Inicia backup automático em intervalos regulares."""
        if self.running:
            return
        
        self.running = True
        self.backup_thread = threading.Thread(
            target=self._backup_worker,
            args=(interval_hours,),
            daemon=True
        )
        self.backup_thread.start()
        logger.info(f"Backup automático iniciado (intervalo: {interval_hours}h)")
    
    def _backup_worker(self, interval_hours: int):
        """Worker thread para backup automático."""
        while self.running:
            try:
                # Criar backup
                backup_path = self.export_to_json(compress=True)
                if backup_path:
                    logger.info(f"Backup automático criado: {backup_path}")
                
                # Limpar backups antigos
                self.cleanup_old_backups()
                
                # Aguardar próximo backup
                time.sleep(interval_hours * 3600)
            
            except Exception as e:
                logger.error(f"Erro no backup automático: {e}")
                time.sleep(3600)  # Aguardar 1 hora em caso de erro
    
    def stop_automatic_backup(self):
        """Para o backup automático."""
        self.running = False
        logger.info("Backup automático parado")
    
    def get_backup_list(self) -> List[Dict]:
        """Retorna lista de backups disponíveis."""
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.startswith("ponto_esa_backup_"):
                    file_path = os.path.join(self.backup_dir, filename)
                    
                    if os.path.isfile(file_path):
                        file_stats = os.stat(file_path)
                        
                        # Determinar tipo
                        if filename.endswith('.json.gz'):
                            backup_type = 'JSON (comprimido)'
                        elif filename.endswith('.json'):
                            backup_type = 'JSON'
                        else:
                            backup_type = 'Desconhecido'
                        
                        backups.append({
                            "filename": filename,
                            "path": file_path,
                            "size": file_stats.st_size,
                            "size_formatted": self._format_size(file_stats.st_size),
                            "created": datetime.fromtimestamp(file_stats.st_ctime),
                            "type": backup_type
                        })
            
            # Adicionar diretórios CSV
            for dirname in os.listdir(self.backup_dir):
                if dirname.startswith("csv_backup_"):
                    dir_path = os.path.join(self.backup_dir, dirname)
                    if os.path.isdir(dir_path):
                        # Calcular tamanho total
                        total_size = sum(
                            os.path.getsize(os.path.join(dir_path, f))
                            for f in os.listdir(dir_path)
                        )
                        
                        backups.append({
                            "filename": dirname,
                            "path": dir_path,
                            "size": total_size,
                            "size_formatted": self._format_size(total_size),
                            "created": datetime.fromtimestamp(os.path.getctime(dir_path)),
                            "type": 'CSV (múltiplos arquivos)'
                        })
            
            # Ordenar por data de criação (mais recente primeiro)
            backups.sort(key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            logger.error(f"Erro ao listar backups: {e}")
        
        return backups
    
    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para exibição."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def get_backup_as_bytes(self, filepath: str) -> Optional[bytes]:
        """
        Retorna o conteúdo de um backup como bytes para download.
        
        Args:
            filepath: Caminho do arquivo de backup
            
        Returns:
            Bytes do arquivo ou None
        """
        try:
            with open(filepath, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Erro ao ler backup: {e}")
            return None


# ============================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================

# Instância global
backup_manager = PostgreSQLBackupManager()


def start_backup_system():
    """Inicia o sistema de backup automático."""
    backup_manager.start_automatic_backup(interval_hours=24)


def stop_backup_system():
    """Para o sistema de backup automático."""
    backup_manager.stop_automatic_backup()


def create_manual_backup(backup_type: str = 'json') -> Optional[str]:
    """
    Cria um backup manual.
    
    Args:
        backup_type: 'json' ou 'csv'
        
    Returns:
        Caminho do backup ou None
    """
    if backup_type == 'csv':
        return backup_manager.export_to_csv()
    return backup_manager.export_to_json(compress=True)


def get_available_backups() -> List[Dict]:
    """Retorna lista de backups disponíveis."""
    return backup_manager.get_backup_list()


def restore_backup(filepath: str, clear_existing: bool = False) -> Tuple[bool, str]:
    """Restaura um backup."""
    return backup_manager.restore_from_json(filepath, clear_existing)


def enviar_backup_por_email(
    email_destino: str,
    backup_type: str = 'json',
    assunto_personalizado: str = None
) -> Tuple[bool, str]:
    """
    Cria um backup e envia por email.
    
    Args:
        email_destino: Email para enviar o backup
        backup_type: 'json' ou 'csv'
        assunto_personalizado: Assunto personalizado (opcional)
        
    Returns:
        Tuple (sucesso, mensagem)
    """
    try:
        from email_notifications import enviar_email, is_email_configured, get_template_base
        
        if not is_email_configured():
            return False, "Sistema de email não configurado. Configure SMTP_USER e SMTP_PASSWORD."
        
        # Criar backup
        logger.info(f"Criando backup {backup_type} para envio por email...")
        
        if backup_type == 'csv':
            # Para CSV, criar um ZIP com todos os arquivos
            import zipfile
            import tempfile
            
            csv_dir = backup_manager.export_to_csv()
            if not csv_dir:
                return False, "Erro ao criar backup CSV"
            
            # Criar ZIP
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"backup_ponto_esa_{timestamp}.zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(csv_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, csv_dir)
                        zipf.write(file_path, arcname)
            
            with open(zip_path, 'rb') as f:
                backup_bytes = f.read()
            
            anexo_nome = zip_filename
            os.remove(zip_path)  # Limpar arquivo temporário
            
        else:
            # JSON comprimido
            backup_path = backup_manager.export_to_json(compress=True)
            if not backup_path:
                return False, "Erro ao criar backup JSON"
            
            with open(backup_path, 'rb') as f:
                backup_bytes = f.read()
            
            anexo_nome = os.path.basename(backup_path)
        
        # Obter estatísticas do backup
        conn = None
        stats = {}
        try:
            from database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM registros_ponto")
            stats['registros'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE ativo = 1")
            stats['usuarios'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(data), MAX(data) FROM registros_ponto")
            result = cursor.fetchone()
            stats['periodo_inicio'] = result[0] if result[0] else 'N/A'
            stats['periodo_fim'] = result[1] if result[1] else 'N/A'
            
        except Exception as e:
            logger.warning(f"Erro ao obter estatísticas: {e}")
            stats = {'registros': 'N/A', 'usuarios': 'N/A', 'periodo_inicio': 'N/A', 'periodo_fim': 'N/A'}
        finally:
            if conn:
                conn.close()
        
        # Montar email
        data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")
        tamanho_backup = len(backup_bytes) / 1024  # KB
        
        if tamanho_backup > 1024:
            tamanho_str = f"{tamanho_backup/1024:.2f} MB"
        else:
            tamanho_str = f"{tamanho_backup:.2f} KB"
        
        assunto = assunto_personalizado or f"🔒 Backup Ponto ExSA - {datetime.now().strftime('%d/%m/%Y')}"
        
        conteudo = f"""
        <h2 style="color: #1a1a2e; margin-bottom: 20px;">📦 Backup Automático</h2>
        
        <p style="color: #333; font-size: 16px;">
            O backup do sistema <strong>Ponto ExSA</strong> foi gerado com sucesso.
        </p>
        
        <div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h3 style="color: #2e7d32; margin-top: 0;">✅ Informações do Backup</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #555;"><strong>📅 Data/Hora:</strong></td>
                    <td style="padding: 8px 0; color: #333;">{data_atual}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #555;"><strong>📁 Arquivo:</strong></td>
                    <td style="padding: 8px 0; color: #333;">{anexo_nome}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #555;"><strong>💾 Tamanho:</strong></td>
                    <td style="padding: 8px 0; color: #333;">{tamanho_str}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #555;"><strong>📊 Total de Registros:</strong></td>
                    <td style="padding: 8px 0; color: #333;">{stats['registros']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #555;"><strong>👥 Usuários Ativos:</strong></td>
                    <td style="padding: 8px 0; color: #333;">{stats['usuarios']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #555;"><strong>📆 Período:</strong></td>
                    <td style="padding: 8px 0; color: #333;">{stats['periodo_inicio']} a {stats['periodo_fim']}</td>
                </tr>
            </table>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-radius: 10px; margin: 20px 0;">
            <h4 style="color: #e65100; margin-top: 0;">⚠️ Importante</h4>
            <p style="color: #555; margin-bottom: 0;">
                Por lei (Portaria 671/2021), os registros de ponto devem ser mantidos por <strong>5 anos</strong>.
                Guarde este backup em local seguro (Google Drive, OneDrive, HD externo).
            </p>
        </div>
        
        <p style="color: #666; font-size: 14px;">
            Para restaurar o backup, acesse o sistema e vá em <strong>Sistema → Backup → Restaurar</strong>.
        </p>
        """
        
        corpo_html = get_template_base(conteudo, "Backup Ponto ExSA")
        
        corpo_texto = f"""
BACKUP PONTO ExSA - {data_atual}

Informações:
- Arquivo: {anexo_nome}
- Tamanho: {tamanho_str}
- Registros: {stats['registros']}
- Período: {stats['periodo_inicio']} a {stats['periodo_fim']}

IMPORTANTE: Por lei (Portaria 671/2021), os registros de ponto 
devem ser mantidos por 5 anos. Guarde este backup em local seguro.
        """
        
        # Enviar email com anexo
        anexo = {
            'nome': anexo_nome,
            'dados': backup_bytes
        }
        
        sucesso, msg = enviar_email(
            destinatario=email_destino,
            assunto=assunto,
            corpo_html=corpo_html,
            corpo_texto=corpo_texto,
            anexos=[anexo]
        )
        
        if sucesso:
            logger.info(f"Backup enviado por email para {email_destino}")
            return True, f"Backup enviado com sucesso para {email_destino}"
        else:
            logger.error(f"Erro ao enviar backup por email: {msg}")
            return False, f"Erro ao enviar email: {msg}"
            
    except Exception as e:
        logger.error(f"Erro ao enviar backup por email: {e}")
        return False, f"Erro: {str(e)}"


def agendar_backup_email_semanal(email_destino: str, dia_semana: int = 0) -> bool:
    """
    Agenda backup semanal por email.
    
    Args:
        email_destino: Email para enviar o backup
        dia_semana: 0=Segunda, 1=Terça, ..., 6=Domingo
        
    Returns:
        True se agendado com sucesso
    """
    try:
        from background_scheduler import scheduler, is_scheduler_running
        from apscheduler.triggers.cron import CronTrigger
        
        if not is_scheduler_running():
            logger.warning("Scheduler não está rodando")
            return False
        
        # Remover job anterior se existir
        job_id = 'backup_email_semanal'
        try:
            scheduler.remove_job(job_id)
        except:
            pass
        
        # Agendar novo job - Segunda às 06:00
        scheduler.add_job(
            func=lambda: enviar_backup_por_email(email_destino, 'json'),
            trigger=CronTrigger(day_of_week=dia_semana, hour=6, minute=0),
            id=job_id,
            name='Backup Semanal por Email',
            replace_existing=True
        )
        
        logger.info(f"Backup semanal agendado para {email_destino}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao agendar backup semanal: {e}")
        return False


__all__ = [
    'PostgreSQLBackupManager',
    'backup_manager',
    'start_backup_system',
    'stop_backup_system',
    'create_manual_backup',
    'get_available_backups',
    'restore_backup',
    'enviar_backup_por_email',
    'agendar_backup_email_semanal'
]
