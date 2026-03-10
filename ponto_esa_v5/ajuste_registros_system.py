"""Sistema de gerenciamento de solicitações de ajustes de registros de ponto."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from ponto_esa_v5.notifications import notification_manager
from database import get_connection, return_connection, SQL_PLACEHOLDER as DB_SQL_PLACEHOLDER
import database as database_module
from constants import agora_br_naive

SQL_PLACEHOLDER = DB_SQL_PLACEHOLDER

# Configurar logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class AjusteRegistrosSystem:
    """Controla o fluxo de solicitações de ajuste de registro."""

    def __init__(self, connection_factory: Optional[Callable[[], Any]] = None) -> None:
        self._get_connection = connection_factory or get_connection

        # Verificar dependências críticas
        logger.debug("Verificando dependências críticas...")
        if not self._check_database_connection():
            logger.critical("Erro crítico: Banco de dados não está acessível.")
            raise RuntimeError("Banco de dados não está acessível. Verifique a configuração.")
        logger.debug("Todas as dependências críticas estão disponíveis.")

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
        return agora_br_naive()

    def _parse_data_hora(self, data_str: str, hora_str: str) -> datetime:
        # Suporta HH:MM e HH:MM:SS para manter compatibilidade.
        try:
            return datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.strptime(f"{data_str} {hora_str}", "%Y-%m-%d %H:%M")

    def _normalizar_tipo(self, tipo: Any) -> str:
        valor = str(tipo or "").strip().lower()
        if valor in {"início", "inicio", "entrada"}:
            return "inicio"
        if valor in {"fim", "saída", "saida"}:
            return "fim"
        return valor

    def _obter_entrada_saida_dia_cursor(self, cursor: Any, usuario: str, data_ref: str) -> tuple[Optional[str], Optional[str]]:
        cursor.execute(
            f"""
            SELECT data_hora, tipo
            FROM registros_ponto
            WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
            ORDER BY data_hora ASC
            """,
            (usuario, data_ref),
        )
        rows = cursor.fetchall()
        primeiro_inicio = None
        ultimo_fim = None
        for data_hora, tipo in rows:
            dt = data_hora if isinstance(data_hora, datetime) else None
            if not dt:
                try:
                    dt = datetime.fromisoformat(str(data_hora))
                except Exception:
                    try:
                        dt = datetime.strptime(str(data_hora), "%Y-%m-%d %H:%M:%S")
                    except Exception:
                        dt = None
            if not dt:
                continue

            tipo_norm = self._normalizar_tipo(tipo)
            if tipo_norm == "inicio" and primeiro_inicio is None:
                primeiro_inicio = dt
            elif tipo_norm == "fim":
                ultimo_fim = dt

        entrada = primeiro_inicio.strftime("%H:%M") if primeiro_inicio else None
        saida = ultimo_fim.strftime("%H:%M") if ultimo_fim else None
        return entrada, saida

    def _registrar_auditoria_alteracao_cursor(
        self,
        cursor: Any,
        usuario_afetado: str,
        data_registro: str,
        entrada_original: Optional[str],
        saida_original: Optional[str],
        entrada_corrigida: Optional[str],
        saida_corrigida: Optional[str],
        tipo_alteracao: str,
        realizado_por: str,
        justificativa: Optional[str] = None,
        detalhes: Optional[str] = None,
    ) -> None:
        cursor.execute(
            f"""
            INSERT INTO auditoria_alteracoes_ponto
            (usuario_afetado, data_registro, entrada_original, saida_original,
             entrada_corrigida, saida_corrigida, tipo_alteracao, realizado_por,
             data_alteracao, justificativa, detalhes)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                    {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                    {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
            """,
            (
                usuario_afetado,
                data_registro,
                entrada_original,
                saida_original,
                entrada_corrigida,
                saida_corrigida,
                tipo_alteracao,
                realizado_por,
                self._now(),
                justificativa,
                detalhes,
            ),
        )

    def _aplicar_complemento_jornada(
        self,
        cursor: Any,
        usuario: str,
        dados_para_aplicar: Dict[str, Any],
        gestor: str,
        observacoes: Optional[str],
    ) -> Dict[str, Any]:
        data_ref = dados_para_aplicar.get("data_referencia") or dados_para_aplicar.get("data")
        hora_inicio = dados_para_aplicar.get("hora_inicio_solicitada") or dados_para_aplicar.get("hora_inicio")
        hora_saida = dados_para_aplicar.get("hora_saida_solicitada") or dados_para_aplicar.get("hora_saida")
        if not data_ref or not hora_inicio or not hora_saida:
            return {"success": False, "message": "Data, hora de início e hora de saída são obrigatórias."}

        dt_inicio = self._parse_data_hora(data_ref, hora_inicio)
        dt_saida = self._parse_data_hora(data_ref, hora_saida)
        if dt_saida <= dt_inicio:
            return {"success": False, "message": "Hora de saída deve ser maior que hora de início."}

        modalidade_base = dados_para_aplicar.get("modalidade")
        projeto_base = dados_para_aplicar.get("projeto")
        atividade_base = dados_para_aplicar.get("atividade")

        cursor.execute(
            f"""
            SELECT id, tipo, modalidade, projeto, atividade
            FROM registros_ponto
            WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
            ORDER BY data_hora ASC
            """,
            (usuario, data_ref),
        )
        registros_dia = cursor.fetchall()
        affected_ids = []

        if len(registros_dia) == 0:
            for data_hora, tipo in ((dt_inicio, "inicio"), (dt_saida, "fim")):
                if database_module.USE_POSTGRESQL:
                    cursor.execute(
                        f"""
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                        RETURNING id
                        """,
                        (
                            usuario,
                            data_hora,
                            tipo,
                            modalidade_base,
                            projeto_base,
                            atividade_base,
                            "Registro criado via ajuste aprovado",
                        ),
                    )
                    affected_ids.append(cursor.fetchone()[0])
                else:
                    cursor.execute(
                        """
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            usuario,
                            data_hora,
                            tipo,
                            modalidade_base,
                            projeto_base,
                            atividade_base,
                            "Registro criado via ajuste aprovado",
                        ),
                    )
                    affected_ids.append(cursor.lastrowid)
        elif len(registros_dia) == 1:
            reg_id, tipo_existente, mod_existente, proj_existente, atividade_existente = registros_dia[0]
            tipo_norm = self._normalizar_tipo(tipo_existente)
            modalidade_base = mod_existente or modalidade_base
            projeto_base = proj_existente or projeto_base
            atividade_base = atividade_existente or atividade_base

            if tipo_norm == "inicio":
                cursor.execute(
                    f"""
                    UPDATE registros_ponto
                    SET data_hora = {SQL_PLACEHOLDER}, tipo = 'inicio', modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
                    WHERE id = {SQL_PLACEHOLDER}
                    """,
                    (dt_inicio, modalidade_base, projeto_base, reg_id),
                )
                affected_ids.append(reg_id)
                novo_tipo = "fim"
                novo_dt = dt_saida
            elif tipo_norm == "fim":
                cursor.execute(
                    f"""
                    UPDATE registros_ponto
                    SET data_hora = {SQL_PLACEHOLDER}, tipo = 'fim', modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
                    WHERE id = {SQL_PLACEHOLDER}
                    """,
                    (dt_saida, modalidade_base, projeto_base, reg_id),
                )
                affected_ids.append(reg_id)
                novo_tipo = "inicio"
                novo_dt = dt_inicio
            else:
                novo_tipo = None
                novo_dt = None

            if novo_tipo:
                if database_module.USE_POSTGRESQL:
                    cursor.execute(
                        f"""
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                        RETURNING id
                        """,
                        (
                            usuario,
                            novo_dt,
                            novo_tipo,
                            modalidade_base,
                            projeto_base,
                            atividade_base,
                            "Registro criado via ajuste aprovado",
                        ),
                    )
                    affected_ids.append(cursor.fetchone()[0])
                else:
                    cursor.execute(
                        """
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            usuario,
                            novo_dt,
                            novo_tipo,
                            modalidade_base,
                            projeto_base,
                            atividade_base,
                            "Registro criado via ajuste aprovado",
                        ),
                    )
                    affected_ids.append(cursor.lastrowid)
            else:
                # Tipo único inesperado: cria ambos para garantir par válido.
                for data_hora, tipo in ((dt_inicio, "inicio"), (dt_saida, "fim")):
                    cursor.execute(
                        f"""
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                        """,
                        (
                            usuario,
                            data_hora,
                            tipo,
                            modalidade_base,
                            projeto_base,
                            atividade_base,
                            "Registro criado via ajuste aprovado",
                        ),
                    )
        else:
            inicio_id = None
            fim_id = None
            for reg in registros_dia:
                reg_id, tipo_existente, _, _, _ = reg
                tipo_norm = self._normalizar_tipo(tipo_existente)
                if tipo_norm == "inicio" and inicio_id is None:
                    inicio_id = reg_id
                if tipo_norm == "fim":
                    fim_id = reg_id

            if inicio_id is None:
                inicio_id = registros_dia[0][0]
            if fim_id is None:
                fim_id = registros_dia[-1][0]

            cursor.execute(
                f"""
                UPDATE registros_ponto
                SET data_hora = {SQL_PLACEHOLDER}, tipo = 'inicio'
                WHERE id = {SQL_PLACEHOLDER}
                """,
                (dt_inicio, inicio_id),
            )
            cursor.execute(
                f"""
                UPDATE registros_ponto
                SET data_hora = {SQL_PLACEHOLDER}, tipo = 'fim'
                WHERE id = {SQL_PLACEHOLDER}
                """,
                (dt_saida, fim_id),
            )
            affected_ids.extend([inicio_id, fim_id])

        for reg_id in affected_ids:
            cursor.execute(
                f"""
                INSERT INTO auditoria_correcoes
                    (registro_id, gestor, justificativa, data_correcao)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                """,
                (
                    reg_id,
                    gestor,
                    observacoes or "Complemento de jornada aprovado",
                    self._now(),
                ),
            )

        return {"success": True}

    def _stop_job(self, solicitacao_id: int) -> None:
        notification_manager.stop_repeating_notification(
            f"ajuste_registro_{solicitacao_id}"
        )

    # Adicionar verificação de conexão ao banco de dados
    def _check_database_connection(self) -> bool:
        try:
            logger.debug("Verificando conexão com o banco de dados...")
            conn = self._get_connection()
            return_connection(conn)
            logger.debug("Conexão com o banco de dados bem-sucedida.")
            return True
        except Exception as exc:
            logger.error(f"Erro ao conectar ao banco de dados: {exc}")
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
            return_connection(conn)

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
            return_connection(conn)

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
            return_connection(conn)

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
            return_connection(conn)

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
            if database_module.USE_POSTGRESQL:
                cursor.execute(
                    f"""
                    INSERT INTO solicitacoes_ajuste_ponto
                        (usuario, aprovador_solicitado, dados_solicitados, justificativa, data_solicitacao)
                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
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
            return_connection(conn)

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
            if acao not in {"corrigir", "criar", "complementar_jornada"}:
                return {"success": False, "message": "Tipo de ajuste inválido."}

            data_auditoria = None
            if acao == "corrigir":
                data_auditoria = dados_para_aplicar.get("nova_data")
            elif acao == "criar":
                data_auditoria = dados_para_aplicar.get("data")
            elif acao == "complementar_jornada":
                data_auditoria = dados_para_aplicar.get("data_referencia") or dados_para_aplicar.get("data")

            entrada_original = saida_original = None
            if data_auditoria:
                entrada_original, saida_original = self._obter_entrada_saida_dia_cursor(
                    cursor, usuario, str(data_auditoria)
                )

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

                if database_module.USE_POSTGRESQL:
                    cursor.execute(
                        f"""
                        INSERT INTO registros_ponto
                            (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
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

            elif acao == "complementar_jornada":
                resultado_complemento = self._aplicar_complemento_jornada(
                    cursor=cursor,
                    usuario=usuario,
                    dados_para_aplicar=dados_para_aplicar,
                    gestor=gestor,
                    observacoes=observacoes,
                )
                if not resultado_complemento.get("success"):
                    return resultado_complemento

            if data_auditoria:
                entrada_corrigida, saida_corrigida = self._obter_entrada_saida_dia_cursor(
                    cursor, usuario, str(data_auditoria)
                )
                self._registrar_auditoria_alteracao_cursor(
                    cursor=cursor,
                    usuario_afetado=usuario,
                    data_registro=str(data_auditoria),
                    entrada_original=entrada_original,
                    saida_original=saida_original,
                    entrada_corrigida=entrada_corrigida,
                    saida_corrigida=saida_corrigida,
                    tipo_alteracao=f"ajuste_{acao}",
                    realizado_por=gestor,
                    justificativa=observacoes,
                    detalhes=f"Solicitação #{solicitacao_id} aplicada",
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
            return_connection(conn)

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
            return_connection(conn)

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
