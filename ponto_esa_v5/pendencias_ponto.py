"""Deteccao de pendencias de ponto em formato puro (sem dependencias de UI)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


def _safe_datetime_parse(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(str(value), fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _normalizar_tipo_ponto(tipo) -> str:
    valor = str(tipo or "").strip().lower()
    if valor in ("início", "inicio", "entrada"):
        return "inicio"
    if valor in ("fim", "saída", "saida"):
        return "fim"
    return valor


def detectar_pendencias_ponto(
    *,
    usuarios_considerados: Sequence[str],
    usuarios_mapa: Dict[str, str],
    data_inicio: date,
    data_fim: date,
    registros_raw: Iterable[Tuple[str, object, object, object]],
    feriados_periodo: Set[str],
    ignoradas: Set[Tuple[str, str, str]],
) -> List[Dict[str, object]]:
    """Retorna lista de pendencias no mesmo formato consumido pela interface."""
    registros_por_dia: Dict[Tuple[str, str], List[Tuple[object, object]]] = {}
    for usuario, data_ref, data_hora, tipo in registros_raw:
        if usuario not in usuarios_considerados:
            continue
        chave = (usuario, str(data_ref))
        registros_por_dia.setdefault(chave, []).append((data_hora, tipo))

    pendencias: List[Dict[str, object]] = []
    total_dias = (data_fim - data_inicio).days + 1
    for usuario in usuarios_considerados:
        for i in range(total_dias):
            dia = data_inicio + timedelta(days=i)
            dia_str = dia.strftime("%Y-%m-%d")

            if dia.weekday() >= 5 or dia_str in feriados_periodo:
                continue

            key = (usuario, dia_str)
            registros = registros_por_dia.get(key, [])

            if not registros:
                tipo_inc = "dia_sem_registro"
                if (usuario, dia_str, tipo_inc) not in ignoradas:
                    pendencias.append(
                        {
                            "usuario": usuario,
                            "nome": usuarios_mapa.get(usuario, usuario),
                            "data": dia_str,
                            "tipo": "Dia sem nenhum registro",
                            "tipo_key": tipo_inc,
                            "horas": None,
                        }
                    )
                continue

            qtd_inicio = 0
            qtd_fim = 0
            primeiro_inicio = None
            ultimo_fim = None
            for data_hora, tipo in sorted(
                registros, key=lambda x: _safe_datetime_parse(x[0]) or datetime.min
            ):
                dt = _safe_datetime_parse(data_hora)
                if not dt:
                    continue
                tipo_norm = _normalizar_tipo_ponto(tipo)
                if tipo_norm == "inicio":
                    qtd_inicio += 1
                    if primeiro_inicio is None:
                        primeiro_inicio = dt
                elif tipo_norm == "fim":
                    qtd_fim += 1
                    ultimo_fim = dt

            horas = None
            if primeiro_inicio and ultimo_fim and ultimo_fim > primeiro_inicio:
                horas = round((ultimo_fim - primeiro_inicio).total_seconds() / 3600, 2)

            if qtd_inicio > qtd_fim:
                tipo_inc = "entrada_sem_saida"
                if (usuario, dia_str, tipo_inc) not in ignoradas:
                    pendencias.append(
                        {
                            "usuario": usuario,
                            "nome": usuarios_mapa.get(usuario, usuario),
                            "data": dia_str,
                            "tipo": "Entrada registrada sem saída",
                            "tipo_key": tipo_inc,
                            "horas": horas,
                        }
                    )
            elif qtd_fim > qtd_inicio:
                tipo_inc = "saida_sem_entrada"
                if (usuario, dia_str, tipo_inc) not in ignoradas:
                    pendencias.append(
                        {
                            "usuario": usuario,
                            "nome": usuarios_mapa.get(usuario, usuario),
                            "data": dia_str,
                            "tipo": "Saída registrada sem entrada",
                            "tipo_key": tipo_inc,
                            "horas": horas,
                        }
                    )

            if horas is not None and horas > 12:
                tipo_inc = "horas_muito_altas"
                if (usuario, dia_str, tipo_inc) not in ignoradas:
                    pendencias.append(
                        {
                            "usuario": usuario,
                            "nome": usuarios_mapa.get(usuario, usuario),
                            "data": dia_str,
                            "tipo": "Horas trabalhadas muito altas (>12h)",
                            "tipo_key": tipo_inc,
                            "horas": horas,
                        }
                    )

    return pendencias
