"""Stub do sistema de cálculo de jornada semanal."""
from datetime import date

class JornadaSemanalCalculoSystem:
    @staticmethod
    def obter_tempo_ate_fim_jornada(usuario: str, data: date, margem_minutos: int = 5):
        # Retorno de exemplo indicando que não há margem especial
        return {"dentro_margem": False, "minutos_restantes": None, "horario_fim": "17:00"}


__all__ = ["JornadaSemanalCalculoSystem"]
