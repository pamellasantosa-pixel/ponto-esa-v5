import logging
from copy import deepcopy
from datetime import datetime

from database import SQL_PLACEHOLDER, get_connection

logger = logging.getLogger(__name__)

NOMES_DIAS = {
    'seg': 'Segunda-Feira', 'ter': 'Terça-Feira', 'qua': 'Quarta-Feira',
    'qui': 'Quinta-Feira', 'sex': 'Sexta-Feira', 'sab': 'Sábado', 'dom': 'Domingo'
}

_DEFAULT_JORNADA = {
    'seg': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
    'ter': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
    'qua': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
    'qui': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
    'sex': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
    'sab': {'trabalha': False, 'inicio': '08:00', 'fim': '12:00', 'intervalo': 0},
    'dom': {'trabalha': False, 'inicio': '08:00', 'fim': '12:00', 'intervalo': 0},
}


def _format_time_value(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.time().strftime('%H:%M')
    if hasattr(value, 'strftime'):
        return value.strftime('%H:%M')
    return str(value)


def obter_jornada_usuario(usuario: str) -> dict:
    jornada = deepcopy(_DEFAULT_JORNADA)
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT dia, trabalha, inicio, fim, intervalo
            FROM jornada_semanal
            WHERE usuario = {SQL_PLACEHOLDER}
            ORDER BY dia
            """,
            (usuario,)
        )
        for dia, trabalha, inicio, fim, intervalo in cursor.fetchall():
            if dia not in jornada:
                continue
            jornada[dia] = {
                'trabalha': bool(trabalha),
                'inicio': _format_time_value(inicio) or jornada[dia]['inicio'],
                'fim': _format_time_value(fim) or jornada[dia]['fim'],
                'intervalo': int(intervalo) if intervalo is not None else jornada[dia]['intervalo']
            }
    except Exception as exc:
        logger.error("Erro ao carregar jornada semanal", exc_info=exc, extra={'usuario': usuario})
    finally:
        conn.close()

    return jornada


def salvar_jornada_semanal(usuario_id, jornada_config: dict) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        for dia, config in jornada_config.items():
            if dia not in _DEFAULT_JORNADA:
                continue
            trabalha = 1 if config.get('trabalha') else 0
            inicio = config.get('inicio') or _DEFAULT_JORNADA[dia]['inicio']
            fim = config.get('fim') or _DEFAULT_JORNADA[dia]['fim']
            intervalo = int(config.get('intervalo', _DEFAULT_JORNADA[dia]['intervalo']))

            cursor.execute(
                f"""
                INSERT INTO jornada_semanal (usuario, dia, trabalha, inicio, fim, intervalo)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                ON CONFLICT (usuario, dia) DO UPDATE
                SET trabalha = EXCLUDED.trabalha,
                    inicio = EXCLUDED.inicio,
                    fim = EXCLUDED.fim,
                    intervalo = EXCLUDED.intervalo
                """,
                (usuario_id, dia, trabalha, inicio, fim, intervalo)
            )

        conn.commit()
        return True
    except Exception as exc:
        conn.rollback()
        logger.error("Erro ao salvar jornada semanal", exc_info=exc, extra={'usuario': usuario_id})
        return False
    finally:
        conn.close()


def copiar_jornada_padrao_para_dias(usuario_id, dias: list) -> bool:
    jornada = obter_jornada_usuario(usuario_id)
    padrao = jornada.get('seg') or _DEFAULT_JORNADA['seg']

    for dia in dias:
        if dia not in _DEFAULT_JORNADA:
            continue
        jornada[dia] = deepcopy(padrao)

    return salvar_jornada_semanal(usuario_id, jornada)


__all__ = [
    "NOMES_DIAS",
    "obter_jornada_usuario",
    "salvar_jornada_semanal",
    "copiar_jornada_padrao_para_dias",
]
