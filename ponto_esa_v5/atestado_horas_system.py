"""Compat shim that re-exports the canonical `AtestadoHorasSystem` implementation."""

import sys
import os
from datetime import datetime

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

def format_time_duration(minutos):
    """Formata duração de tempo em horas e minutos"""
    if minutos is None:
        return "0h 0m"
    
    horas = minutos // 60
    mins = minutos % 60
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
