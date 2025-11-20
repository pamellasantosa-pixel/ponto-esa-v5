"""Stubs e utilitários para jornada semanal."""
from datetime import time

NOMES_DIAS = {
    'seg': 'Segunda-Feira', 'ter': 'Terça-Feira', 'qua': 'Quarta-Feira',
    'qui': 'Quinta-Feira', 'sex': 'Sexta-Feira', 'sab': 'Sábado', 'dom': 'Domingo'
}


def obter_jornada_usuario(usuario: str) -> dict:
    # Retornar configuração padrão simples
    return {
        'seg': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
        'ter': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
        'qua': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
        'qui': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
        'sex': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
        'sab': {'trabalha': False, 'inicio': '08:00', 'fim': '12:00', 'intervalo': 0},
        'dom': {'trabalha': False, 'inicio': '08:00', 'fim': '12:00', 'intervalo': 0},
    }


def salvar_jornada_semanal(usuario_id, jornada_config: dict) -> bool:
    # Stub: não persiste, apenas retorna sucesso
    return True


def copiar_jornada_padrao_para_dias(usuario_id, dias: list) -> bool:
    return True


__all__ = [
    "NOMES_DIAS",
    "obter_jornada_usuario",
    "salvar_jornada_semanal",
    "copiar_jornada_padrao_para_dias"
]
