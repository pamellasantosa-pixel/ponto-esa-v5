"""
Sistema de Horas Extras - Ponto ExSA v5.0
Gerencia solicitações e aprovações de horas extras
"""

import sqlite3
from database_postgresql import get_connection
from datetime import datetime, timedelta, time
import json
from notifications import notification_manager


class HorasExtrasSystem:
    def __init__(self):
        
    def verificar_fim_jornada(self, usuario):
        """Verifica se o usuário chegou no horário de fim da jornada prevista"""
        conn = get_connection()
        cursor = conn.cursor()

        # Buscar jornada prevista do usuário
        cursor.execute("""
            SELECT jornada_fim_previsto FROM usuarios 
            WHERE usuario = ? AND ativo = 1
        """, (usuario,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return {"deve_notificar": False, "message": "Usuário não encontrado"}

        jornada_fim = result[0] or "17:00"

        # Verificar se é hora de notificar
        agora = datetime.now().time()
        jornada_fim_time = datetime.strptime(jornada_fim, "%H:%M").time()

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
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT usuario, nome_completo, tipo FROM usuarios 
            WHERE ativo = 1 
            ORDER BY tipo DESC, nome_completo ASC
        """)

        aprovadores = cursor.fetchall()
        conn.close()

        return [{"usuario": a[0], "nome": a[1] or a[0], "tipo": a[2]} for a in aprovadores]

    def solicitar_horas_extras(self, usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado):
        """Registra uma nova solicitação de horas extras"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Verificar se já existe solicitação para o mesmo período
            cursor.execute("""
                SELECT id FROM solicitacoes_horas_extras 
                WHERE usuario = ? AND data = ? AND status = 'pendente'
            """, (usuario, data))

            if cursor.fetchone():
                return {"success": False, "message": "Já existe uma solicitação pendente para esta data"}

            # Calcular total de horas
            inicio = datetime.strptime(hora_inicio, "%H:%M")
            fim = datetime.strptime(hora_fim, "%H:%M")

            if fim <= inicio:
                # Assumir que passou para o próximo dia
                fim += timedelta(days=1)

            total_horas = (fim - inicio).total_seconds() / 3600

            # Inserir solicitação
            cursor.execute("""
                INSERT INTO solicitacoes_horas_extras 
                (usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado))

            solicitacao_id = cursor.lastrowid
            conn.commit()

            # Enviar notificação para o aprovador
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
                    "timestamp": datetime.now().isoformat(),
                    "requires_response": True
                }
            )

            return {
                "success": True,
                "message": "Solicitação de horas extras enviada com sucesso",
                "id": solicitacao_id,
                "total_horas": total_horas
            }

        except Exception as e:
            conn.rollback()
            return {"success": False, "message": f"Erro ao solicitar horas extras: {str(e)}"}
        finally:
            conn.close()

    def listar_solicitacoes_usuario(self, usuario, status=None):
        """Lista solicitações de horas extras de um usuário"""
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM solicitacoes_horas_extras WHERE usuario = ?"
        params = [usuario]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY data_solicitacao DESC"

        cursor.execute(query, params)
        solicitacoes = cursor.fetchall()
        conn.close()

        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'justificativa',
                   'aprovador_solicitado', 'status', 'data_solicitacao', 'aprovado_por',
                   'data_aprovacao', 'observacoes']

        return [dict(zip(colunas, s)) for s in solicitacoes]

    def listar_solicitacoes_para_aprovacao(self, aprovador):
        """Lista solicitações pendentes para um aprovador específico"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = ? AND status = 'pendente'
            ORDER BY data_solicitacao ASC
        """, (aprovador,))

        solicitacoes = cursor.fetchall()
        conn.close()

        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'justificativa',
                   'aprovador_solicitado', 'status', 'data_solicitacao', 'aprovado_por',
                   'data_aprovacao', 'observacoes']

        return [dict(zip(colunas, s)) for s in solicitacoes]

    def aprovar_solicitacao(self, solicitacao_id, aprovador, observacoes=None):
        """Aprova uma solicitação de horas extras"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Verificar se a solicitação existe e está pendente
            cursor.execute("""
                SELECT usuario, data, hora_inicio, hora_fim, aprovador_solicitado 
                FROM solicitacoes_horas_extras 
                WHERE id = ? AND status = 'pendente'
            """, (solicitacao_id,))

            solicitacao = cursor.fetchone()
            if not solicitacao:
                return {"success": False, "message": "Solicitação não encontrada ou já processada"}

            # Verificar se o aprovador é o correto
            if solicitacao[4] != aprovador:
                return {"success": False, "message": "Você não tem permissão para aprovar esta solicitação"}

            # Aprovar solicitação
            cursor.execute("""
                UPDATE solicitacoes_horas_extras 
                SET status = 'aprovado', aprovado_por = ?, data_aprovacao = ?, observacoes = ?
                WHERE id = ?
            """, (aprovador, datetime.now().isoformat(), observacoes, solicitacao_id))

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

            conn.commit()
            return {"success": True, "message": "Solicitação aprovada com sucesso"}

        except Exception as e:
            conn.rollback()
            return {"success": False, "message": f"Erro ao aprovar solicitação: {str(e)}"}
        finally:
            conn.close()

    def rejeitar_solicitacao(self, solicitacao_id, aprovador, observacoes):
        """Rejeita uma solicitação de horas extras"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Verificar se a solicitação existe e está pendente
            cursor.execute("""
                SELECT aprovador_solicitado FROM solicitacoes_horas_extras 
                WHERE id = ? AND status = 'pendente'
            """, (solicitacao_id,))

            result = cursor.fetchone()
            if not result:
                return {"success": False, "message": "Solicitação não encontrada ou já processada"}

            # Verificar se o aprovador é o correto
            if result[0] != aprovador:
                return {"success": False, "message": "Você não tem permissão para rejeitar esta solicitação"}

            # Rejeitar solicitação
            cursor.execute("""
                UPDATE solicitacoes_horas_extras 
                SET status = 'rejeitado', aprovado_por = ?, data_aprovacao = ?, observacoes = ?
                WHERE id = ?
            """, (aprovador, datetime.now().isoformat(), observacoes, solicitacao_id))

            conn.commit()
            return {"success": True, "message": "Solicitação rejeitada"}

        except Exception as e:
            conn.rollback()
            return {"success": False, "message": f"Erro ao rejeitar solicitação: {str(e)}"}
        finally:
            conn.close()

    def _calcular_horas_extras(self, hora_inicio, hora_fim):
        """Calcula o total de horas extras"""
        inicio = datetime.strptime(hora_inicio, "%H:%M")
        fim = datetime.strptime(hora_fim, "%H:%M")

        if fim <= inicio:
            fim += timedelta(days=1)

        return (fim - inicio).total_seconds() / 3600

    def _registrar_banco_horas(self, cursor, usuario, data, tipo, descricao, credito, debito, relacionado_id, relacionado_tabela):
        """Registra movimentação no banco de horas"""
        # Buscar saldo anterior
        cursor.execute("""
            SELECT saldo_atual FROM banco_horas 
            WHERE usuario = ? 
            ORDER BY data_registro DESC 
            LIMIT 1
        """, (usuario,))

        result = cursor.fetchone()
        saldo_anterior = result[0] if result else 0
        saldo_atual = saldo_anterior + credito - debito

        # Inserir registro
        cursor.execute("""
            INSERT INTO banco_horas 
            (usuario, data, tipo, descricao, credito, debito, saldo_anterior, saldo_atual, relacionado_id, relacionado_tabela)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (usuario, data, tipo, descricao, credito, debito, saldo_anterior, saldo_atual, relacionado_id, relacionado_tabela))

    def contar_notificacoes_pendentes(self, aprovador):
        """Conta quantas solicitações estão pendentes para um aprovador"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = ? AND status = 'pendente'
        """, (aprovador,))

        count = cursor.fetchone()[0]
        conn.close()

        return count

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
