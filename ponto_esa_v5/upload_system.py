"""
Sistema de Upload de Arquivos - Ponto ExSA v3.0
Permite upload seguro de documentos e comprovantes
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
import mimetypes
import hashlib

from database import get_connection, return_connection, adapt_sql_for_postgresql, SQL_PLACEHOLDER as DB_SQL_PLACEHOLDER
import database as database_module
import logging
from constants import agora_br

logger = logging.getLogger(__name__)

# SQL Placeholder para compatibilidade SQLite/PostgreSQL
SQL_PLACEHOLDER = DB_SQL_PLACEHOLDER


class UploadSystem:
    def __init__(self, upload_dir="uploads", db_path: str | None = None):
        global SQL_PLACEHOLDER
        self.upload_dir = upload_dir
        self._test_db_path = db_path
        if self._test_db_path:
            SQL_PLACEHOLDER = "?"
        else:
            SQL_PLACEHOLDER = DB_SQL_PLACEHOLDER
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {
            'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'txt', 'rtf'
        }
        self.allowed_mimes = {
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'image/gif',
            'text/plain',
            'application/rtf'
        }
        self.init_directories()
        self.init_database()

    def _get_connection(self):
        """Retorna conexão ao banco, usando db_path de teste se configurado."""
        if getattr(self, '_test_db_path', None):
            return get_connection(self._test_db_path)
        return get_connection()

    def init_directories(self):
        """Cria estrutura de diretórios para uploads"""
        base_dirs = [
            f"{self.upload_dir}/ausencias",
            f"{self.upload_dir}/atestados",
            f"{self.upload_dir}/documentos",
            f"{self.upload_dir}/temp"
        ]

        for dir_path in base_dirs:
            os.makedirs(dir_path, exist_ok=True)

        # Criar subdiretórios por ano/mês
        current_year = agora_br().year
        current_month = agora_br().month

        for base_dir in base_dirs[:-1]:  # Excluir temp
            year_dir = f"{base_dir}/{current_year}"
            month_dir = f"{year_dir}/{current_month:02d}"
            os.makedirs(month_dir, exist_ok=True)

    def init_database(self):
        """Inicializa tabela de uploads"""
        conn = self._get_connection()
        cursor = conn.cursor()

        sql = '''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                nome_original TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT NOT NULL,
                tamanho INTEGER NOT NULL,
                caminho TEXT NOT NULL,
                hash_arquivo TEXT NOT NULL,
                relacionado_a TEXT,
                relacionado_id INTEGER,
                conteudo BLOB,
                data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ativo'
            )
        '''
        # Em banco de teste SQLite local não converter SQL para dialeto PostgreSQL.
        if not getattr(self, '_test_db_path', None):
            sql = adapt_sql_for_postgresql(sql)
        cursor.execute(sql)
        conn.commit()
        return_connection(conn)

    def validate_file(self, file_content, filename, file_size):
        """Valida arquivo antes do upload"""
        errors = []

        # Verificar tamanho
        if file_size > self.max_file_size:
            errors.append(
                f"Arquivo muito grande. Máximo permitido: {self.max_file_size // (1024*1024)}MB")

        # Verificar extensão
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        if extension not in self.allowed_extensions:
            errors.append(
                f"Tipo de arquivo não permitido. Permitidos: {', '.join(self.allowed_extensions)}")

        # Verificar MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type not in self.allowed_mimes:
            errors.append("Tipo MIME não permitido")

        # Verificar nome do arquivo
        if not filename or len(filename) > 255:
            errors.append("Nome do arquivo inválido")

        # Verificar caracteres perigosos
        dangerous_chars = ['<', '>', ':', '"', '|', f'{SQL_PLACEHOLDER}', '*', '\\', '/']
        if any(char in filename for char in dangerous_chars):
            errors.append("Nome do arquivo contém caracteres não permitidos")

        return errors

    def generate_safe_filename(self, original_filename):
        """Gera nome de arquivo seguro e único"""
        extension = original_filename.lower().split(
            '.')[-1] if '.' in original_filename else 'bin'
        unique_id = str(uuid.uuid4())
        timestamp = agora_br().strftime("%Y%m%d_%H%M%S")

        return f"{timestamp}_{unique_id}.{extension}"

    def calculate_file_hash(self, file_content):
        """Calcula hash SHA-256 do arquivo"""
        return hashlib.sha256(file_content).hexdigest()

    def get_upload_path(self, categoria, filename):
        """Determina caminho de upload baseado na categoria"""
        now = agora_br()
        year = now.year
        month = now.month

        categoria_map = {
            'ausencia': 'ausencias',
            'atestado_horas': 'atestados',
            'documento': 'documentos'
        }

        base_dir = categoria_map.get(categoria, 'documentos')
        return f"{self.upload_dir}/{base_dir}/{year}/{month:02d}/{filename}"

    def save_file(self, file_content, usuario, original_filename, categoria='documento', relacionado_a=None, relacionado_id=None):
        """Salva arquivo no sistema (banco de dados para persistência em nuvem)"""
        try:
            file_size = len(file_content)

            # Validar arquivo
            validation_errors = self.validate_file(
                file_content, original_filename, file_size)
            if validation_errors:
                return {
                    "success": False,
                    "message": "Arquivo inválido",
                    "errors": validation_errors
                }

            # Gerar nome seguro
            safe_filename = self.generate_safe_filename(original_filename)
            file_path = self.get_upload_path(categoria, safe_filename)

            # Calcular hash
            file_hash = self.calculate_file_hash(file_content)

            # Verificar se arquivo já existe (por hash)
            existing_file = self.find_file_by_hash(file_hash, usuario)
            if existing_file:
                return {
                    "success": False,
                    "message": "Arquivo já existe no sistema",
                    "existing_file": existing_file
                }

            # Conteúdo crítico fica persistido no banco (BYTEA/BLOB).
            # O caminho físico é mantido apenas como metadado de compatibilidade.

            # Registrar no banco COM conteúdo
            mime_type, _ = mimetypes.guess_type(original_filename)
            upload_id = self.register_upload(
                usuario=usuario,
                nome_original=original_filename,
                nome_arquivo=safe_filename,
                tipo_arquivo=mime_type or 'application/octet-stream',
                tamanho=file_size,
                caminho=file_path,
                hash_arquivo=file_hash,
                relacionado_a=relacionado_a,
                relacionado_id=relacionado_id,
                conteudo=file_content  # 🔧 NOVO: Salvar conteúdo no banco
            )

            return {
                "success": True,
                "message": "Arquivo enviado com sucesso",
                "upload_id": upload_id,
                "filename": safe_filename,
                "path": file_path,
                "size": file_size
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Erro ao salvar arquivo: {str(e)}"
            }

    def register_upload(self, usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a=None, relacionado_id=None, conteudo=None):
        """Registra upload no banco de dados (incluindo conteúdo binário)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 🔧 CORREÇÃO: Incluir coluna conteudo na inserção
            if conteudo is not None:
                params = (usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a, relacionado_id, conteudo)
                query = f"INSERT INTO uploads (usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a, relacionado_id, conteudo) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})"
            else:
                params = (usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a, relacionado_id)
                query = f"INSERT INTO uploads (usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a, relacionado_id) VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})"

            if database_module.USE_POSTGRESQL and not self._test_db_path:
                # Em PostgreSQL, usar RETURNING id para obter o id inserido
                query = query + " RETURNING id"
                cursor.execute(query, params)
                result = cursor.fetchone()
                upload_id = result[0] if result else None
                conn.commit()
                return upload_id
            else:
                # SQLite: executar e usar lastrowid
                cursor.execute(query, params)
                upload_id = cursor.lastrowid
                conn.commit()
                return upload_id

        except Exception as e:
            raise e
        finally:
            return_connection(conn)

    def find_file_by_hash(self, file_hash, usuario):
        """Busca arquivo por hash para evitar duplicatas"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f'''
            SELECT id, nome_original, caminho FROM uploads 
            WHERE hash_arquivo = {SQL_PLACEHOLDER} AND usuario = {SQL_PLACEHOLDER} AND status = 'ativo'
        ''', (file_hash, usuario))

        result = cursor.fetchone()
        return_connection(conn)

        if result:
            return {
                "id": result[0],
                "nome_original": result[1],
                "caminho": result[2]
            }
        return None

    def get_user_uploads(self, usuario, categoria=None, relacionado_a=None, relacionado_id=None):
        """Lista uploads de um usuário"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = f"SELECT * FROM uploads WHERE usuario = {SQL_PLACEHOLDER} AND status = 'ativo'"
        params = [usuario]
        if categoria:
            # Mapear categoria para relacionado_a
            if categoria in ['ausencia', 'atestado_horas', 'documento']:
                query += f" AND relacionado_a = {SQL_PLACEHOLDER}"
                params.append(categoria)

        if relacionado_a:
            query += f" AND relacionado_a = {SQL_PLACEHOLDER}"
            params.append(relacionado_a)

        if relacionado_id:
            query += f" AND relacionado_id = {SQL_PLACEHOLDER}"
            params.append(relacionado_id)

        query += " ORDER BY data_upload DESC"
        cursor.execute(query, params)
        uploads = cursor.fetchall()
        return_connection(conn)

        # Converter para dicionários
        colunas = ['id', 'usuario', 'nome_original', 'nome_arquivo', 'tipo_arquivo',
                   'tamanho', 'caminho', 'hash_arquivo', 'relacionado_a', 'relacionado_id',
                   'data_upload', 'status']

        return [dict(zip(colunas, upload)) for upload in uploads]

    def get_file_info(self, upload_id, usuario=None):
        """Obtém informações de um arquivo específico"""
        conn = self._get_connection()
        cursor = conn.cursor()
        # upload_id pode ser um inteiro (id) ou uma string (caminho)
        params = []

        # Detectar se foi passado o caminho do arquivo em vez do id
        use_caminho = False
        try:
            # Se for convertível para int, tratar como id
            int(upload_id)
        except Exception:
            # Não é inteiro: provavelmente é um caminho
            use_caminho = True

        if use_caminho:
            query = f"SELECT * FROM uploads WHERE caminho = {SQL_PLACEHOLDER}"
            params = [upload_id]
            if usuario:
                query += f" AND usuario = {SQL_PLACEHOLDER}"
                params.append(usuario)
        else:
            query = f"SELECT * FROM uploads WHERE id = {SQL_PLACEHOLDER}"
            params = [int(upload_id)]
            if usuario:
                query += f" AND usuario = {SQL_PLACEHOLDER}"
                params.append(usuario)

        cursor.execute(query, params)
        upload = cursor.fetchone()
        return_connection(conn)

        if upload:
            colunas = ['id', 'usuario', 'nome_original', 'nome_arquivo', 'tipo_arquivo',
                       'tamanho', 'caminho', 'hash_arquivo', 'relacionado_a', 'relacionado_id',
                       'data_upload', 'status']
            return dict(zip(colunas, upload))

        return None

    def delete_file(self, upload_id, usuario):
        """Remove arquivo (marca como inativo)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Verificar se arquivo pertence ao usuário
            # Suporta upload_id como id ou caminho
            try:
                cursor.execute(
                    f"SELECT caminho FROM uploads WHERE id = {SQL_PLACEHOLDER} AND usuario = {SQL_PLACEHOLDER}", (int(upload_id), usuario))
            except Exception:
                cursor.execute(
                    f"SELECT caminho FROM uploads WHERE caminho = {SQL_PLACEHOLDER} AND usuario = {SQL_PLACEHOLDER}", (upload_id, usuario))
            result = cursor.fetchone()

            if not result:
                return {"success": False, "message": "Arquivo não encontrado"}

            # Marcar como inativo no banco
            cursor.execute(
                f"UPDATE uploads SET status = 'removido' WHERE id = {SQL_PLACEHOLDER}", (upload_id,))

            conn.commit()
            return {"success": True, "message": "Arquivo removido com sucesso"}

        except Exception as e:
            return {"success": False, "message": f"Erro ao remover arquivo: {str(e)}"}
        finally:
            return_connection(conn)

    def get_file_content(self, upload_id, usuario=None):
        """Obtém conteúdo de um arquivo para download (prioriza banco de dados)"""
        # Suporta upload_id como id (int) ou caminho (str)
        file_info = self.get_file_info(upload_id, usuario)

        if not file_info:
            return None, None

        # 🔧 CORREÇÃO: Primeiro tentar obter do banco de dados (para funcionar no Render)
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Obter conteúdo do banco de dados
            cursor.execute(
                f"SELECT conteudo FROM uploads WHERE id = {SQL_PLACEHOLDER}",
                (file_info['id'],)
            )
            result = cursor.fetchone()
            return_connection(conn)
            
            if result and result[0]:
                # Conteúdo encontrado no banco de dados
                content = result[0]
                # Em PostgreSQL, BYTEA pode vir como memoryview, converter para bytes
                if isinstance(content, memoryview):
                    content = bytes(content)
                return content, file_info
        except Exception:
            pass  # Se falhar, tenta arquivo local
        
        # Sem fallback para disco local: evita dependência de filesystem efêmero.
        return None, None

    def cleanup_temp_files(self, max_age_hours=24):
        """Remove arquivos temporários antigos"""
        temp_dir = f"{self.upload_dir}/temp"
        if not os.path.exists(temp_dir):
            return

        cutoff_time = agora_br().timestamp() - (max_age_hours * 3600)

        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < cutoff_time:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.warning("Não foi possível remover arquivo temporário %s: %s", file_path, e)

    def get_storage_stats(self):
        """Obtém estatísticas de armazenamento"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                COUNT(*) as total_files,
                SUM(tamanho) as total_size,
                relacionado_a,
                COUNT(*) as files_by_category
            FROM uploads 
            WHERE status = 'ativo'
            GROUP BY relacionado_a
        ''')

        stats_by_category = cursor.fetchall()

        cursor.execute('''
            SELECT COUNT(*), SUM(tamanho) FROM uploads WHERE status = 'ativo'
        ''')

        total_stats = cursor.fetchone()
        return_connection(conn)

        return {
            "total_files": total_stats[0] or 0,
            "total_size": total_stats[1] or 0,
            "by_category": [
                {
                    "category": row[2] or "outros",
                    "files": row[3],
                    "size": row[1]
                }
                for row in stats_by_category
            ]
        }

# Funções utilitárias para integração com Streamlit


def format_file_size(size_bytes):
    """Formata tamanho do arquivo para exibição"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_file_icon(mime_type):
    """Retorna emoji/ícone baseado no tipo de arquivo"""
    icons = {
        'application/pdf': '📄',
        'application/msword': '📝',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '📝',
        'image/jpeg': '🖼️',
        'image/png': '🖼️',
        'image/gif': '🖼️',
        'text/plain': '📃',
        'application/rtf': '📝'
    }
    return icons.get(mime_type, '📎')


def is_image_file(mime_type):
    """Verifica se arquivo é uma imagem"""
    return mime_type.startswith('image/')


def get_category_name(categoria):
    """Retorna nome amigável da categoria"""
    names = {
        'ausencia': 'Ausências',
        'atestado_horas': 'Atestados de Horas',
        'documento': 'Documentos'
    }
    return names.get(categoria, 'Outros')

try:
    from notifications import NotificationManager
except ImportError:
    from notifications import NotificationManager

__all__ = [
    "UploadSystem",
    "format_file_size",
    "get_file_icon",
    "is_image_file",
    "get_category_name",
]
