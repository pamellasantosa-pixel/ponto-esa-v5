"""Sistema de gerenciamento de solicitações de ajustes de registros de ponto."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from notifications import notification_manager
from database_postgresql import get_connection, USE_POSTGRESQL

SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"


class AjusteRegistrosSystem:
    """Controla o fluxo de solicitações de ajuste de registro."""

    def __init__(self, connection_factory: Optional[Callable[[], Any]] = None) -> None:
        self._get_connection = connection_factory or get_connection

    # ===== Métodos auxiliares internos =====
    def _dump_json(self, payload: Dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False)

    def _load_json(self, payload: Optional[str]) -> Dict[str, Any]:
        if not payload:
            return {}
        # PostgreSQL pode retornar dict diretamente (tipo JSON/JSONB)
        if isinstance(payload, dict):
            return payload
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return {}

    def _now(self) -> datetime:
        return datetime.now()

    def _stop_job(self, solicitacao_id: int) -> None:
        notification_manager.stop_repeating_notification(
            f"ajuste_registro_{solicitacao_id}"
        )

    # Adicionar verificação de conexão ao banco de dados
    def _check_database_connection(self) -> bool:
        try:
            conn = self._get_connection()
            conn.close()
            return True
        except Exception as exc:
            print(f"Erro ao conectar ao banco de dados: {exc}")
            return False

    # ===== Consultas =====
    def is_solicitacao_resolvida(self, solicitacao_id: int) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT status FROM solicitacoes_ajuste_ponto WHERE id = {SQL_PLACEHOLDER}",
                (solicitacao_id,),
            )
            row = cursor.fetchone()
            return not row or (row[0] and row[0].lower() != "pendente")
        finally:
            conn.close()

    def listar_solicitacoes_usuario(self, usuario: str) -> list[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT id, aprovador_solicitado, justificativa, status, data_solicitacao,
                       data_resposta, observacoes, dados_solicitados, respondido_por
                FROM solicitacoes_ajuste_ponto
                WHERE usuario = {SQL_PLACEHOLDER}
                ORDER BY data_solicitacao DESC
                """,
                (usuario,),
            )
            rows = cursor.fetchall()
            resultado = []
            for row in rows:
                resultado.append(
                    {
                        "id": row[0],
                        "aprovador": row[1],
                        "justificativa": row[2],
                        "status": row[3],
                        "data_solicitacao": row[4],
                        "data_resposta": row[5],
                        "observacoes": row[6],
                        "dados": self._load_json(row[7]),
                        "respondido_por": row[8],
                    }
                )
            return resultado
        finally:
            conn.close()

    def listar_solicitacoes_para_gestor(self, gestor: str) -> list[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT id, usuario, justificativa, status, data_solicitacao,
                       dados_solicitados
                FROM solicitacoes_ajuste_ponto
                WHERE aprovador_solicitado = {SQL_PLACEHOLDER}
                  AND status = 'pendente'
                ORDER BY data_solicitacao ASC
                """,
                (gestor,),
            )
            rows = cursor.fetchall()
            resultado = []
            for row in rows:
                resultado.append(
                    {
                        "id": row[0],
                        "usuario": row[1],
                        "justificativa": row[2],
                        "status": row[3],
                        "data_solicitacao": row[4],
                        "dados": self._load_json(row[5]),
                    }
                )
            return resultado
        finally:
            conn.close()

    def obter_registro(self, registro_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT id, usuario, data_hora, tipo, modalidade, projeto, atividade
                FROM registros_ponto
                WHERE id = {SQL_PLACEHOLDER}
                """,
                (registro_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "usuario": row[1],
                "data_hora": row[2],
                "tipo": row[3],
                "modalidade": row[4],
                "projeto": row[5],
                "atividade": row[6],
            }
        finally:
            conn.close()

    # ===== Operações principais =====
    def solicitar_ajuste(
        self,
        usuario: str,
        aprovador_solicitado: str,
        dados_solicitados: Dict[str, Any],
        justificativa: str,
    ) -> Dict[str, Any]:
        if not self._check_database_connection():
            return {"success": False, "message": "Erro de conexão com o banco de dados."}

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            dados_json = self._dump_json(dados_solicitados)
            if USE_POSTGRESQL:
                cursor.execute(
                    """
                    INSERT INTO solicitacoes_ajuste_ponto
                        (usuario, aprovador_solicitado, dados_solicitados, justificativa, data_solicitacao)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (usuario, aprovador_solicitado, dados_json, justificativa, self._now()),
                )
                solicitacao_id = cursor.fetchone()[0]
            else:
                cursor.execute(
                    """
                    INSERT INTO solicitacoes_ajuste_ponto
                        (usuario, aprovador_solicitado, dados_solicitados, justificativa, data_solicitacao)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (usuario, aprovador_solicitado, dados_json, justificativa, self._now()),
                )
                solicitacao_id = cursor.lastrowid
            conn.commit()
        except Exception as exc:
            conn.rollback()
            return {"success": False, "message": f"Erro ao registrar solicitação: {exc}"}
        finally:
            conn.close()

        # Notificar gestor responsável
        titulo = "Solicitação de ajuste de ponto"
        mensagem = "Existe um pedido de ajuste aguardando sua análise."
        payload = {
            "type": "ajuste_registro_solicitacao",
            "title": titulo,
            "message": mensagem,
            "solicitacao_id": solicitacao_id,
            "usuario": usuario,
            "requires_response": True,
        }
        notification_manager.add_notification(aprovador_solicitado, payload)

        lembrete_payload = {
            "type": "ajuste_registro_lembrete",
            "title": "Lembrete: ajuste pendente",
            "message": f"A solicitação #{solicitacao_id} de {usuario} ainda aguarda decisão.",
            "solicitacao_id": solicitacao_id,
            "usuario": usuario,
            "requires_response": True,
        }

        def stop_condition() -> bool:
            return self.is_solicitacao_resolvida(solicitacao_id)

        notification_manager.start_repeating_notification(
            f"ajuste_registro_{solicitacao_id}",
            aprovador_solicitado,
            lembrete_payload,
            stop_condition=stop_condition,
        )

        return {"success": True, "message": "Solicitação enviada com sucesso", "solicitacao_id": solicitacao_id}

    def aplicar_ajuste(
        self,
        solicitacao_id: int,
        gestor: str,
        dados_confirmados: Dict[str, Any],
        observacoes: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._check_database_connection():
            return {"success": False, "message": "Erro de conexão com o banco de dados."}

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT usuario, dados_solicitados
                FROM solicitacoes_ajuste_ponto
                WHERE id = {SQL_PLACEHOLDER} AND status = 'pendente'
                """,
                (solicitacao_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "Solicitação não encontrada ou já tratada."}

            usuario = row[0]
            dados_originais = self._load_json(row[1])
            dados_para_aplicar = {**dados_originais, **(dados_confirmados or {})}

            acao = dados_para_aplicar.get("acao")
            if acao not in {"corrigir", "criar"}:
                return {"success": False, "message": "Tipo de ajuste inválido."}

            if acao == "corrigir":
                registro_id = dados_para_aplicar.get("registro_id")
                if not registro_id:
                    return {"success": False, "message": "Registro alvo não informado."}

                nova_data = dados_para_aplicar.get("nova_data")
                nova_hora = dados_para_aplicar.get("nova_hora")
                if not nova_data or not nova_hora:
                    return {"success": False, "message": "Nova data e hora são obrigatórias."}

                # Suportar tanto HH:MM quanto HH:MM:SS
                try:
                    nova_data_hora = datetime.strptime(
                        f"{nova_data} {nova_hora}", "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    nova_data_hora = datetime.strptime(
                        f"{nova_data} {nova_hora}", "%Y-%m-%d %H:%M"
                    )
                novo_tipo = dados_para_aplicar.get("novo_tipo")
                nova_modalidade = dados_para_aplicar.get("modalidade")
                novo_projeto = dados_para_aplicar.get("projeto")
                nova_atividade = dados_para_aplicar.get("atividade")

                cursor.execute(
                    f"""
                    UPDATE registros_ponto
                    SET data_hora = {SQL_PLACEHOLDER}, tipo = {SQL_PLACEHOLDER},
                        modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}, atividade = {SQL_PLACEHOLDER}
                    WHERE id = {SQL_PLACEHOLDER}
                    """,
                    (
                        nova_data_hora,
                        novo_tipo,
                        nova_modalidade,
                        novo_projeto,
                        nova_atividade,
                        registro_id,
                    ),
                )

                cursor.execute(
                    f"""
                    INSERT INTO auditoria_correcoes
                        (registro_id, gestor, justificativa, data_correcao)
                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                    """,
                    (
                        registro_id,
                        gestor,
                        observacoes or "Ajuste aplicado via solicitação",
                        self._now(),
                    ),
                )

            elif acao == "criar":
                data_nova = dados_para_aplicar.get("data")
                hora_nova = dados_para_aplicar.get("hora")
                if not data_nova or not hora_nova:
                    return {"success": False, "message": "Data e hora são obrigatórias."}

                # Suportar tanto HH:MM quanto HH:MM:SS
                try:
                    data_hora_nova = datetime.strptime(
                        f"{data_nova} {hora_nova}", "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    data_hora_nova = datetime.strptime(
                        f"{data_nova} {hora_nova}", "%Y-%m-%d %H:%M"
                    )
                tipo = dados_para_aplicar.get("tipo")
                modalidade = dados_para_aplicar.get("modalidade")
                projeto = dados_para_aplicar.get("projeto")
                atividade = dados_para_aplicar.get("atividade")

                if USE_POSTGRESQL:
                    cursor.execute(
                        """
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            usuario,
                            data_hora_nova,
                            tipo,
                            modalidade,
                            projeto,
                            atividade,
                            "Registro inserido via ajuste aprovado",
                        ),
                    )
                    registro_id = cursor.fetchone()[0]
                else:
                    cursor.execute(
                        """
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            usuario,
                            data_hora_nova,
                            tipo,
                            modalidade,
                            projeto,
                            atividade,
                            "Registro inserido via ajuste aprovado",
                        ),
                    )
                    registro_id = cursor.lastrowid

                cursor.execute(
                    f"""
                    INSERT INTO auditoria_correcoes
                        (registro_id, gestor, justificativa, data_correcao)
                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                    """,
                    (
                        registro_id,
                        gestor,
                        observacoes or "Registro criado via ajuste aprovado",
                        self._now(),
                    ),
                )

            # Atualizar status da solicitação
            cursor.execute(
                f"""
                UPDATE solicitacoes_ajuste_ponto
                SET status = 'aplicado', respondido_por = {SQL_PLACEHOLDER},
                    data_resposta = {SQL_PLACEHOLDER}, observacoes = {SQL_PLACEHOLDER},
                    dados_solicitados = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
                """,
                (
                    gestor,
                    self._now(),
                    observacoes,
                    self._dump_json(dados_para_aplicar),
                    solicitacao_id,
                ),
            )

            conn.commit()
        except Exception as exc:
            conn.rollback()
            return {"success": False, "message": f"Erro ao aplicar ajuste: {exc}"}
        finally:
            conn.close()

        self._stop_job(solicitacao_id)

        notification_manager.add_notification(
            usuario,
            {
                "type": "ajuste_registro_resposta",
                "title": "Ajuste aplicado",
                "message": "Seu pedido de ajuste foi aprovado e aplicado com sucesso.",
                "solicitacao_id": solicitacao_id,
                "status": "aplicado",
            },
        )

        return {"success": True, "message": "Ajuste aplicado com sucesso"}

    def rejeitar_ajuste(
        self,
        solicitacao_id: int,
        gestor: str,
        observacoes: str,
    ) -> Dict[str, Any]:
        if not self._check_database_connection():
            return {"success": False, "message": "Erro de conexão com o banco de dados."}

        if not observacoes.strip():
            return {"success": False, "message": "Observações são obrigatórias para rejeição."}

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"""
                SELECT usuario FROM solicitacoes_ajuste_ponto
                WHERE id = {SQL_PLACEHOLDER} AND status = 'pendente'
                """,
                (solicitacao_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "Solicitação não encontrada ou já tratada."}

            usuario = row[0]

            cursor.execute(
                f"""
                UPDATE solicitacoes_ajuste_ponto
                SET status = 'rejeitado', respondido_por = {SQL_PLACEHOLDER},
                    data_resposta = {SQL_PLACEHOLDER}, observacoes = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
                """,
                (
                    gestor,
                    self._now(),
                    observacoes,
                    solicitacao_id,
                ),
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            return {"success": False, "message": f"Erro ao rejeitar solicitação: {exc}"}
        finally:
            conn.close()

        self._stop_job(solicitacao_id)

        notification_manager.add_notification(
            usuario,
            {
                "type": "ajuste_registro_resposta",
                "title": "Ajuste rejeitado",
                "message": "Seu pedido de ajuste foi rejeitado.",
                "solicitacao_id": solicitacao_id,
                "status": "rejeitado",
                "observacoes": observacoes,
            },
        )

        return {"success": True, "message": "Solicitação rejeitada"}


__all__ = ["AjusteRegistrosSystem"]
