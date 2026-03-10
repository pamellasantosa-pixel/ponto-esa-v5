"""
Sistema de Horas Extras - Ponto ExSA v5.0
Gerencia solicitações e aprovações de horas extras
"""

from database import get_connection, return_connection, SQL_PLACEHOLDER as DB_SQL_PLACEHOLDER

from datetime import datetime, timedelta, time
import json
from constants import agora_br
try:
    from notifications import notification_manager
except Exception:
    from notifications import notification_manager

# SQL Placeholder para compatibilidade SQLite/PostgreSQL
SQL_PLACEHOLDER = DB_SQL_PLACEHOLDER


class HorasExtrasSystem:
    def __init__(self, db_path: str | None = None):
        """Inicializa o sistema de horas extras. Se `db_path` for fornecido, será usado para conectar diretamente ao SQLite (em testes)."""
        global SQL_PLACEHOLDER
        self.db_path = db_path
        if self.db_path:
            SQL_PLACEHOLDER = "?"
            self._ensure_sqlite_schema()
        else:
            SQL_PLACEHOLDER = DB_SQL_PLACEHOLDER

    def _ensure_sqlite_schema(self):
        """Cria schema mínimo necessário quando usando SQLite local em testes."""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS solicitacoes_horas_extras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    data TEXT NOT NULL,
                    hora_inicio TEXT NOT NULL,
                    hora_fim TEXT NOT NULL,
                    justificativa TEXT NOT NULL,
                    aprovador_solicitado TEXT NOT NULL,
                    status TEXT DEFAULT 'pendente',
                    data_solicitacao TEXT DEFAULT CURRENT_TIMESTAMP,
                    aprovado_por TEXT,
                    data_aprovacao TEXT,
                    observacoes TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS banco_horas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL,
                    data TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    credito REAL DEFAULT 0,
                    debito REAL DEFAULT 0,
                    saldo_anterior REAL DEFAULT 0,
                    saldo_atual REAL DEFAULT 0,
                    data_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                    relacionado_id INTEGER,
                    relacionado_tabela TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    senha TEXT,
                    tipo TEXT,
                    nome_completo TEXT,
                    ativo INTEGER DEFAULT 1,
                    jornada_fim_previsto TEXT DEFAULT '17:00'
                )
                """
            )
            conn.commit()
        finally:
            return_connection(conn)
        
    def verificar_fim_jornada(self, usuario):
        """Verifica se o usuário chegou no horário de fim da jornada prevista"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        try:
            # Buscar jornada prevista do usuário
            cursor.execute(f"""
                SELECT jornada_fim_previsto FROM usuarios 
                WHERE usuario = {SQL_PLACEHOLDER} AND ativo = 1
            """, (usuario,))
            result = cursor.fetchone()
        except Exception:
            return {"deve_notificar": False, "message": "Usuário não encontrado"}
        finally:
            return_connection(conn)

        if not result:
            return {"deve_notificar": False, "message": "Usuário não encontrado"}

        jornada_fim = result[0] or "17:00"

        # Verificar se é hora de notificar
        agora = agora_br().time()
        
        # Converter para time se for string, senão usar diretamente
        if isinstance(jornada_fim, str):
            jornada_fim_time = datetime.strptime(jornada_fim, "%H:%M").time()
        else:
            jornada_fim_time = jornada_fim

        # Notificar se passou do horário previsto
        if agora >= jornada_fim_time:
            return {
                "deve_notificar": True,
                "message": f"Seu horário de fim da jornada ({jornada_fim}) foi atingido. Deseja solicitar horas extras?",
                "jornada_fim": jornada_fim
            }

        return {"deve_notificar": False, "message": "Ainda não é hora de notificar"}

    def obter_aprovadores_disponiveis(self):
        """Obtém lista de usuários que podem aprovar horas extras (gestores e outros funcionários)"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT usuario, nome_completo, tipo FROM usuarios 
            WHERE ativo = 1 
            ORDER BY tipo DESC, nome_completo ASC
        """)

        aprovadores = cursor.fetchall()
        return_connection(conn)

        return [{"usuario": a[0], "nome": a[1] or a[0], "tipo": a[2]} for a in aprovadores]

    def solicitar_horas_extras(self, usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado):
        """Registra uma nova solicitação de horas extras"""
        try:
            from db_utils import database_transaction, create_error_response, create_success_response
        except ImportError as err_direct:
            print(f"DEBUG: Import direto db_utils falhou em horas_extras_system.aprovar_solicitacao: {err_direct}")
            try:
                from ponto_esa_v5.db_utils import database_transaction, create_error_response, create_success_response
            except ImportError as err_pkg:
                print(f"DEBUG: Import ponto_esa_v5.db_utils falhou: {err_pkg}")
                raise
        
        try:
            # Validações básicas
            if not all([usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado]):
                return create_error_response("Todos os campos são obrigatórios")
            
            # Calcular total de horas
            try:
                inicio = datetime.strptime(hora_inicio, "%H:%M")
                fim = datetime.strptime(hora_fim, "%H:%M")
            except ValueError as e:
                return create_error_response(f"Formato de hora inválido: {e}")

            if fim <= inicio:
                fim += timedelta(days=1)

            total_horas = (fim - inicio).total_seconds() / 3600

            with database_transaction(self.db_path) as cursor:
                # Verificar se já existe solicitação para o mesmo período
                cursor.execute(f"""
                    SELECT id FROM solicitacoes_horas_extras 
                    WHERE usuario = {SQL_PLACEHOLDER} AND data = {SQL_PLACEHOLDER} AND status = 'pendente'
                """, (usuario, data))

                if cursor.fetchone():
                    return create_error_response("Já existe uma solicitação pendente para esta data")

                # Inserir solicitação
                cursor.execute(f"""
                    INSERT INTO solicitacoes_horas_extras 
                    (usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado)
                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                """, (usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado))

                solicitacao_id = cursor.lastrowid

            # Enviar notificação para o aprovador sem bloquear o fluxo principal.
            try:
                notification_manager.add_notification(
                    aprovador_solicitado,
                    {
                        "type": "horas_extras_solicitacao",
                        "title": "Nova solicitação de horas extras",
                        "message": f"{usuario} solicitou aprovação de {total_horas:.1f}h extras em {data}",
                        "solicitacao_id": solicitacao_id,
                        "usuario": usuario,
                        "data": data,
                        "total_horas": total_horas,
                        "timestamp": agora_br().isoformat(),
                        "requires_response": True
                    }
                )
            except Exception:
                pass

            # Iniciar lembrete contínuo para o aprovador selecionado
            job_id = f"horas_extras_{solicitacao_id}"

            def stop_condition():
                return self._is_solicitacao_finalizada(solicitacao_id)

            reminder_payload = {
                "type": "horas_extras_lembrete",
                "title": "Lembrete: aprovação pendente",
                "message": f"Solicitação #{solicitacao_id} de {usuario} aguarda sua decisão.",
                "solicitacao_id": solicitacao_id,
                "usuario": usuario,
                "data": data,
                "total_horas": total_horas,
                "requires_response": True
            }

            # Mantém lembretes recorrentes até aprovação ou rejeição
            try:
                notification_manager.start_repeating_notification(
                    job_id,
                    aprovador_solicitado,
                    reminder_payload,
                    stop_condition=stop_condition
                )
            except Exception:
                pass

            return {
                "success": True,
                "message": "Solicitação de horas extras enviada com sucesso",
                "id": solicitacao_id,
                "total_horas": total_horas
            }

        except Exception as e:
            return create_error_response("Erro ao solicitar horas extras", error=e)

    def listar_solicitacoes_usuario(self, usuario, status=None):
        """Lista solicitações de horas extras de um usuário"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        query = f"SELECT * FROM solicitacoes_horas_extras WHERE usuario = {SQL_PLACEHOLDER}"
        params = [usuario]

        if status:
            query += f" AND status = {SQL_PLACEHOLDER}"
            params.append(status)

        query += " ORDER BY data_solicitacao DESC"

        cursor.execute(query, params)
        solicitacoes = cursor.fetchall()
        return_connection(conn)

        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'justificativa',
                   'aprovador_solicitado', 'status', 'data_solicitacao', 'aprovado_por',
                   'data_aprovacao', 'observacoes']

        return [dict(zip(colunas, s)) for s in solicitacoes]

    def listar_solicitacoes_para_aprovacao(self, aprovador):
        """Lista solicitações pendentes para um aprovador específico"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT * FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
            ORDER BY data_solicitacao ASC
        """, (aprovador,))

        solicitacoes = cursor.fetchall()
        return_connection(conn)

        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'justificativa',
                   'aprovador_solicitado', 'status', 'data_solicitacao', 'aprovado_por',
                   'data_aprovacao', 'observacoes']

        return [dict(zip(colunas, s)) for s in solicitacoes]

    def aprovar_solicitacao(self, solicitacao_id, aprovador, observacoes=None):
        """Aprova uma solicitação de horas extras"""
        try:
            from db_utils import database_transaction, create_error_response, create_success_response
        except ImportError as err_direct:
            print(f"DEBUG: Import direto db_utils falhou em horas_extras_system.rejeitar_solicitacao: {err_direct}")
            try:
                from ponto_esa_v5.db_utils import database_transaction, create_error_response, create_success_response
            except ImportError as err_pkg:
                print(f"DEBUG: Import ponto_esa_v5.db_utils falhou: {err_pkg}")
                raise
        
        try:
            with database_transaction(self.db_path) as cursor:
                # Verificar se a solicitação existe e está pendente
                cursor.execute(f"""
                    SELECT usuario, data, hora_inicio, hora_fim, aprovador_solicitado 
                    FROM solicitacoes_horas_extras 
                    WHERE id = {SQL_PLACEHOLDER} AND status = 'pendente'
                """, (solicitacao_id,))

                solicitacao = cursor.fetchone()
                if not solicitacao:
                    return create_error_response("Solicitação não encontrada ou já processada")

                # Verificar se o aprovador é o correto
                if solicitacao[4] != aprovador:
                    return create_error_response("Você não tem permissão para aprovar esta solicitação")

                # Aprovar solicitação
                cursor.execute(f"""
                    UPDATE solicitacoes_horas_extras 
                    SET status = 'aprovado', aprovado_por = {SQL_PLACEHOLDER}, data_aprovacao = {SQL_PLACEHOLDER}, observacoes = {SQL_PLACEHOLDER}
                    WHERE id = {SQL_PLACEHOLDER}
                """, (aprovador, agora_br().isoformat(), observacoes, solicitacao_id))

                # Registrar no banco de horas
                self._registrar_banco_horas(
                    cursor,
                    solicitacao[0],  # usuario
                    solicitacao[1],  # data
                    "horas_extras_aprovadas",
                    f"Horas extras aprovadas ({solicitacao[2]} às {solicitacao[3]})",
                    self._calcular_horas_extras(solicitacao[2], solicitacao[3]),
                    0,
                    solicitacao_id,
                    "solicitacoes_horas_extras"
                )

            notification_manager.stop_repeating_notification(f"horas_extras_{solicitacao_id}")
            return {"success": True, "message": "Solicitação aprovada com sucesso"}

        except Exception as e:
            return {"success": False, "message": f"Erro ao aprovar solicitação: {str(e)}"}

    def rejeitar_solicitacao(self, solicitacao_id, aprovador, observacoes):
        """Rejeita uma solicitação de horas extras"""
        try:
            from db_utils import database_transaction, create_error_response, create_success_response
        except ImportError:
            try:
                from ponto_esa_v5.db_utils import database_transaction, create_error_response, create_success_response
            except ImportError:
                from .db_utils import database_transaction, create_error_response, create_success_response
        
        try:
            with database_transaction(self.db_path) as cursor:
                # Verificar se a solicitação existe e está pendente
                cursor.execute(f"""
                    SELECT aprovador_solicitado FROM solicitacoes_horas_extras 
                    WHERE id = {SQL_PLACEHOLDER} AND status = 'pendente'
                """, (solicitacao_id,))

                result = cursor.fetchone()
                if not result:
                    return create_error_response("Solicitação não encontrada ou já processada")

                # Verificar se o aprovador é o correto
                if result[0] != aprovador:
                    return create_error_response("Você não tem permissão para rejeitar esta solicitação")

                # Rejeitar solicitação
                cursor.execute(f"""
                    UPDATE solicitacoes_horas_extras 
                    SET status = 'rejeitado', aprovado_por = {SQL_PLACEHOLDER}, data_aprovacao = {SQL_PLACEHOLDER}, observacoes = {SQL_PLACEHOLDER}
                    WHERE id = {SQL_PLACEHOLDER}
                """, (aprovador, agora_br().isoformat(), observacoes, solicitacao_id))

            notification_manager.stop_repeating_notification(f"horas_extras_{solicitacao_id}")
            return {"success": True, "message": "Solicitação rejeitada"}

        except Exception as e:
            return {"success": False, "message": f"Erro ao rejeitar solicitação: {str(e)}"}

    def _calcular_horas_extras(self, hora_inicio, hora_fim):
        """Calcula o total de horas extras"""
        def _to_datetime(value):
            if isinstance(value, datetime):
                return value
            if isinstance(value, time):
                return datetime.combine(datetime.today().date(), value)
            if isinstance(value, str):
                for fmt in ("%H:%M", "%H:%M:%S"):
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            raise ValueError(f"Formato de hora inválido: {value!r}")

        inicio = _to_datetime(hora_inicio)
        fim = _to_datetime(hora_fim)

        if fim <= inicio:
            fim += timedelta(days=1)

        return (fim - inicio).total_seconds() / 3600

    def _registrar_banco_horas(self, cursor, usuario, data, tipo, descricao, credito, debito, relacionado_id, relacionado_tabela):
        """Registra movimentação no banco de horas"""
        # Buscar saldo anterior
        cursor.execute(f"""
            SELECT saldo_atual FROM banco_horas 
            WHERE usuario = {SQL_PLACEHOLDER} 
            ORDER BY data_registro DESC 
            LIMIT 1
        """, (usuario,))

        result = cursor.fetchone()
        saldo_anterior = result[0] if result else 0
        saldo_atual = saldo_anterior + credito - debito

        # Inserir registro
        cursor.execute(f"""
            INSERT INTO banco_horas 
            (usuario, data, tipo, descricao, credito, debito, saldo_anterior, saldo_atual, relacionado_id, relacionado_tabela)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
        """, (usuario, data, tipo, descricao, credito, debito, saldo_anterior, saldo_atual, relacionado_id, relacionado_tabela))

    def contar_notificacoes_pendentes(self, aprovador):
        """Conta quantas solicitações estão pendentes para um aprovador"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT COUNT(*) FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
        """, (aprovador,))

        count = cursor.fetchone()[0]
        return_connection(conn)

        return count

    def _is_solicitacao_finalizada(self, solicitacao_id):
        """Verifica se a solicitação de horas extras foi tratada."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT status FROM solicitacoes_horas_extras
            WHERE id = {SQL_PLACEHOLDER}
            """,
            (solicitacao_id,)
        )

        result = cursor.fetchone()
        return_connection(conn)

        if not result:
            return True

        status = result[0]
        return status and status.lower() != "pendente"

# Funções utilitárias


def format_time_duration(horas):
    """Formata duração em horas para exibição"""
    if horas < 1:
        minutos = int(horas * 60)
        return f"{minutos} min"
    else:
        h = int(horas)
        m = int((horas - h) * 60)
        return f"{h}h {m}min" if m > 0 else f"{h}h"


def get_status_emoji(status):
    """Retorna emoji para status da solicitação"""
    emojis = {
        "pendente": "⏳",
        "aprovado": "✅",
        "rejeitado": "❌"
    }
    return emojis.get(status, "📄")


__all__ = ["HorasExtrasSystem", "format_time_duration", "get_status_emoji"]
