"""
Sistema de Upload de Arquivos - Ponto ExSA v3.0
Permite upload seguro de documentos e comprovantes
"""

import os
import uuid
import sqlite3
from database_postgresql import get_connection, USE_POSTGRESQL
from datetime import datetime
import mimetypes
import hashlib

# SQL Placeholder para compatibilidade SQLite/PostgreSQL
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"
from pathlib import Path


class UploadSystem:
    def __init__(self, upload_dir="uploads", db_path=None):
        self.upload_dir = upload_dir
        self._db_path = db_path
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
        if self._db_path:
            return sqlite3.connect(self._db_path)
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
        current_year = datetime.now().year
        current_month = datetime.now().month

        for base_dir in base_dirs[:-1]:  # Excluir temp
            year_dir = f"{base_dir}/{current_year}"
            month_dir = f"{year_dir}/{current_month:02d}"
            os.makedirs(month_dir, exist_ok=True)

    def init_database(self):
        """Inicializa tabela de uploads"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id SERIAL PRIMARY KEY,
                usuario TEXT NOT NULL,
                nome_original TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT NOT NULL,
                tamanho INTEGER NOT NULL,
                caminho TEXT NOT NULL,
                hash_arquivo TEXT NOT NULL,
                relacionado_a TEXT,
                relacionado_id INTEGER,
                data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ativo'
            )
        ''')

        conn.commit()
        conn.close()

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
        print(f"DEBUG: Filename: {filename}, Guessed MIME type: {mime_type}")  # Linha de depuração
        if not mime_type:
            # Se o tipo não puder ser adivinhado, confiar na extensão
            if extension == 'txt':
                mime_type = 'text/plain'
        
        if mime_type not in self.allowed_mimes:
            errors.append(f"Tipo MIME não permitido: {mime_type}")

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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        return f"{timestamp}_{unique_id}.{extension}"

    def calculate_file_hash(self, file_content):
        """Calcula hash SHA-256 do arquivo"""
        return hashlib.sha256(file_content).hexdigest()

    def get_upload_path(self, categoria, filename):
        """Determina caminho de upload baseado na categoria"""
        now = datetime.now()
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
        """Salva arquivo no sistema"""
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

            # Criar diretório se não existir
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

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

            # Salvar arquivo
            with open(file_path, 'wb') as f:
                f.write(file_content)

            # Registrar no banco
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
                relacionado_id=relacionado_id
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

    def register_upload(self, usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a=None, relacionado_id=None):
        """Registra upload no banco de dados"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # A query foi corrigida para usar placeholders '?' diretamente,
            # que é o formato esperado pelo sqlite3, resolvendo o erro 'unrecognized token'.
            # A variável SQL_PLACEHOLDER foi mantida para consistência, mas a query agora é mais robusta.
            placeholders = ", ".join([SQL_PLACEHOLDER] * 9)
            query = f"INSERT INTO uploads (usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a, relacionado_id) VALUES ({placeholders})"
            
            cursor.execute(query, (usuario, nome_original, nome_arquivo, tipo_arquivo, tamanho, caminho, hash_arquivo, relacionado_a, relacionado_id))

            upload_id = cursor.lastrowid
            conn.commit()
            return upload_id

        except Exception as e:
            raise e
        finally:
            conn.close()

    def find_file_by_hash(self, file_hash, usuario):
        """Busca arquivo por hash para evitar duplicatas"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f'''
            SELECT id, nome_original, caminho FROM uploads 
            WHERE hash_arquivo = {SQL_PLACEHOLDER} AND usuario = {SQL_PLACEHOLDER} AND status = 'ativo'
        ''', (file_hash, usuario))

        result = cursor.fetchone()
        conn.close()

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
        conn.close()

        # Converter para dicionários
        colunas = ['id', 'usuario', 'nome_original', 'nome_arquivo', 'tipo_arquivo',
                   'tamanho', 'caminho', 'hash_arquivo', 'relacionado_a', 'relacionado_id',
                   'data_upload', 'status']

        return [dict(zip(colunas, upload)) for upload in uploads]

    def get_file_info(self, upload_id, usuario=None):
        """Obtém informações de um arquivo específico"""
        conn = self._get_connection()
        cursor = conn.cursor()

        query = f"SELECT * FROM uploads WHERE id = {SQL_PLACEHOLDER}"
        params = [upload_id]

        if usuario:
            query += f" AND usuario = {SQL_PLACEHOLDER}"
            params.append(usuario)

        cursor.execute(query, params)
        upload = cursor.fetchone()
        conn.close()

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
            cursor.execute(
                f"SELECT caminho FROM uploads WHERE id = {SQL_PLACEHOLDER} AND usuario = {SQL_PLACEHOLDER}", (upload_id, usuario))
            result = cursor.fetchone()

            if not result:
                return {"success": False, "message": "Arquivo não encontrado"}

            file_path = result[0]

            # Marcar como inativo no banco
            cursor.execute(
                f"UPDATE uploads SET status = 'removido' WHERE id = {SQL_PLACEHOLDER}", (upload_id,))

            # Remover arquivo físico
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass  # Não falhar se não conseguir remover arquivo físico

            conn.commit()
            return {"success": True, "message": "Arquivo removido com sucesso"}

        except Exception as e:
            return {"success": False, "message": f"Erro ao remover arquivo: {str(e)}"}
        finally:
            conn.close()

    def get_file_content(self, upload_id, usuario=None):
        """Obtém conteúdo de um arquivo para download"""
        file_info = self.get_file_info(upload_id, usuario)

        if not file_info:
            return None, None

        try:
            with open(file_info['caminho'], 'rb') as f:
                content = f.read()
            return content, file_info
        except:
            return None, None

    def cleanup_temp_files(self, max_age_hours=24):
        """Remove arquivos temporários antigos"""
        temp_dir = f"{self.upload_dir}/temp"
        if not os.path.exists(temp_dir):
            return

        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path):
                if os.path.getmtime(file_path) < cutoff_time:
                    try:
                        os.remove(file_path)
                    except:
                        pass

    def get_storage_stats(self):
        """Obtém estatísticas de armazenamento"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
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
        conn.close()

        return {
            "total_files": total_stats[0] or 0,
            "total_size": total_stats[1] or 0,
            "by_category": [
                {
                    "category": row[1] or "outros",
                    "files": row[2],
                    "size": row[0]
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
