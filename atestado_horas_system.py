"""Compat shim that re-exports the canonical `AtestadoHorasSystem` implementation."""

import sys
import os
from datetime import datetime

from database import get_connection, SQL_PLACEHOLDER as DB_SQL_PLACEHOLDER

SQL_PLACEHOLDER = DB_SQL_PLACEHOLDER

# Placeholder implementations
class AtestadoHorasSystem:
    """Sistema de gerenciamento de atestados de horas"""
    def __init__(self, connection_manager=None):
        self.connection_manager = connection_manager
    
    def registrar_atestado_horas(
        self,
        usuario: str,
        data: str,
        hora_inicio: str,
        hora_fim: str,
        motivo: str | None = None,
        arquivo_comprovante: str | None = None,
        nao_possui_comprovante: int = 0,
    ):
        """Registra um atestado de horas simples, compatível com os testes.

        Retorna dict com `success`, `message` e `total_horas`.
        """
        try:
            # Calcular total de horas
            h_inicio, m_inicio = map(int, hora_inicio.split(':'))
            h_fim, m_fim = map(int, hora_fim.split(':'))
            
            minutos_inicio = h_inicio * 60 + m_inicio
            minutos_fim = h_fim * 60 + m_fim
            
            total_minutos = minutos_fim - minutos_inicio
            total_horas = total_minutos / 60.0
            
            conn = get_connection()
            cursor = conn.cursor()
            placeholders = ", ".join([SQL_PLACEHOLDER] * 8)
            cursor.execute(
                f"""
                INSERT INTO atestado_horas (
                    usuario, data, hora_inicio, hora_fim, total_horas,
                    motivo, arquivo_comprovante, nao_possui_comprovante,
                    status
                ) VALUES ({placeholders}, 'pendente')
                """,
                (
                    usuario,
                    data,
                    hora_inicio,
                    hora_fim,
                    round(total_horas, 2),
                    motivo,
                    arquivo_comprovante,
                    nao_possui_comprovante,
                ),
            )
            conn.commit()
            atestado_id = cursor.lastrowid if hasattr(cursor, "lastrowid") else None
            conn.close()
            return {"success": True, "message": "Atestado registrado com sucesso!", "id": atestado_id, "total_horas": total_horas}
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            return {"success": False, "message": str(e), "total_horas": 0}
    
    def listar_atestados_usuario(self, usuario: str):
        """Lista atestados de horas para um usuário (visão completa)."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT id, usuario, data, hora_inicio, hora_fim, total_horas, motivo, status,
                       aprovado_por, data_aprovacao, observacoes, arquivo_comprovante
                FROM atestado_horas WHERE usuario = {SQL_PLACEHOLDER}
                ORDER BY data_registro DESC""",
            (usuario,),
        )
        rows = cursor.fetchall()
        conn.close()
        colunas = [
            "id",
            "usuario",
            "data",
            "hora_inicio",
            "hora_fim",
            "total_horas",
            "motivo",
            "status",
            "aprovado_por",
            "data_aprovacao",
            "observacoes",
            "arquivo_comprovante",
        ]
        return [dict(zip(colunas, r)) for r in rows]
    
    def aprovar_atestado(self, atestado_id, gestor, observacoes=None):
        """Aprova um atestado de horas"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                f"""
                UPDATE atestado_horas
                SET status = {SQL_PLACEHOLDER}, aprovado_por = {SQL_PLACEHOLDER}, data_aprovacao = CURRENT_TIMESTAMP, observacoes = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
                """,
                ("aprovado", gestor, observacoes, atestado_id),
            )
            conn.commit()
            conn.close()
            return {"success": True, "message": "Atestado aprovado"}
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            return {"success": False, "message": str(e)}
    
    def rejeitar_atestado(self, atestado_id, gestor, motivo):
        """Rejeita um atestado: marca como 'rejeitado' e registra observações.

        Retorna dicionário com chave `success` e opcional `message`.
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Atualizar status para 'rejeitado' e registrar quem rejeitou
            cursor.execute(
                f"""
                UPDATE atestado_horas
                SET status = {SQL_PLACEHOLDER}, aprovado_por = {SQL_PLACEHOLDER}, data_aprovacao = CURRENT_TIMESTAMP, observacoes = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
                """,
                ("rejeitado", gestor, motivo, atestado_id)
            )
            conn.commit()
            conn.close()
            return {"success": True, "message": "Atestado rejeitado"}
        except Exception as e:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
            return {"success": False, "message": str(e)}

def format_time_duration(minutos):
    """Formata duração de tempo em horas e minutos"""
    if minutos is None:
        return "0h 0m"
    
    # Garantir que seja float
    minutos = float(minutos)
    
    horas = int(minutos // 60)
    mins = int(minutos % 60)
    return f"{horas}h {mins:02d}m"

def get_status_color(status):
    """Retorna cor para um status"""
    colors = {
        'pendente': '#FFA500',
        'aprovado': '#28A745',
        'rejeitado': '#DC3545',
        'aguardando': '#FFC107',
    }
    return colors.get(status, '#6C757D')

def get_status_emoji(status):
    """Retorna emoji para um status"""
    emojis = {
        'pendente': '⏳',
        'aprovado': '✅',
        'rejeitado': '❌',
        'aguardando': '⏰',
    }
    return emojis.get(status, '❓')

__all__ = [
    "AtestadoHorasSystem",
    "format_time_duration",
    "get_status_color",
    "get_status_emoji"
]
