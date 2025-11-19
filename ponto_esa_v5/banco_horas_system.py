"""Compat shim that re-exports the canonical `BancoHorasSystem` implementation."""

import sys
import os
from datetime import datetime, timedelta

# Placeholder implementations
class BancoHorasSystem:
    """Sistema de gerenciamento de banco de horas"""
    def __init__(self, connection_manager=None):
        self.connection_manager = connection_manager
    
    def obter_saldo(self, usuario):
        """Obtém saldo do banco de horas do usuário"""
        return 0.0
    
    def adicionar_horas(self, usuario, horas, motivo=""):
        """Adiciona horas ao banco"""
        pass
    
    def remover_horas(self, usuario, horas, motivo=""):
        """Remove horas do banco"""
        pass

def format_saldo_display(saldo_horas):
    """Formata saldo de horas para exibição"""
    if saldo_horas is None:
        return "0h 0m"
    
    horas = int(abs(saldo_horas))
    minutos = int((abs(saldo_horas) - horas) * 60)
    
    sinal = "-" if saldo_horas < 0 else ""
    return f"{sinal}{horas}h {minutos:02d}m"

__all__ = ["BancoHorasSystem", "format_saldo_display"]
