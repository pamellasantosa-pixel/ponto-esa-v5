"""Stub do sistema de cálculo de jornada semanal."""
from datetime import date

class JornadaSemanalCalculoSystem:
    @staticmethod
    def obter_tempo_ate_fim_jornada(usuario: str, data: date, margem_minutos: int = 5):
        # Retorno de exemplo indicando que não há margem especial
        return {"dentro_margem": False, "minutos_restantes": None, "horario_fim": "17:00"}

    @staticmethod
    def detectar_hora_extra_dia(usuario: str, data: date, tolerancia_minutos: int = 5):
        # Stub defensivo para evitar quebra quando o módulo completo não estiver disponível.
        return {
            "tem_hora_extra": False,
            "horas_extra": 0.0,
            "minutos_extra": 0,
            "esperado_minutos": 0,
            "registrado_minutos": 0,
            "categoria": "sem_hora_extra",
            "tolerancia_minutos": tolerancia_minutos,
        }


__all__ = ["JornadaSemanalCalculoSystem"]
