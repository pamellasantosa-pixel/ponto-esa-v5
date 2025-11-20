"""Compat shim that re-exports the canonical `AtestadoHorasSystem` implementation."""

import sys
import os
from datetime import datetime

try:
    from ponto_esa_v5.database_postgresql import get_connection, USE_POSTGRESQL
except Exception:
    from ponto_esa_v5.database_postgresql import get_connection, USE_POSTGRESQL

# Placeholder implementations
class AtestadoHorasSystem:
    """Sistema de gerenciamento de atestados de horas"""
    def __init__(self, connection_manager=None):
        self.connection_manager = connection_manager
    
    def registrar_atestado(self, usuario, data_inicio, data_fim, tipo, arquivo=None):
        """Registra um novo atestado"""
        pass
    
    def obter_atestados(self, usuario):
        """Obtém atestados do usuário"""
        return []
    
    def aprovar_atestado(self, atestado_id):
        """Aprova um atestado"""
        pass
    
    def rejeitar_atestado(self, atestado_id, gestor, motivo):
        """Rejeita um atestado: marca como 'rejeitado' e registra observações.

        Retorna dicionário com chave `success` e opcional `message`.
        """
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Atualizar status para 'rejeitado' e registrar quem rejeitou
            cursor.execute(
                """
                UPDATE atestado_horas
                SET status = %s, aprovado_por = %s, data_aprovacao = CURRENT_TIMESTAMP, observacoes = %s
                WHERE id = %s
                """ if USE_POSTGRESQL else """
                UPDATE atestado_horas
                SET status = ?, aprovado_por = ?, data_aprovacao = CURRENT_TIMESTAMP, observacoes = ?
                WHERE id = ?
                """,
                ("rejeitado", gestor, motivo, atestado_id) if USE_POSTGRESQL else ("rejeitado", gestor, motivo, atestado_id)
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
