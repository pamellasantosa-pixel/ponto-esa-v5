from datetime import date

from ponto_esa_v5.pendencias_ponto import detectar_pendencias_ponto


def test_detecta_tipos_principais_de_pendencia():
    usuarios = ["ana", "bob"]
    usuarios_mapa = {"ana": "Ana", "bob": "Bob"}

    # Segunda-feira 2026-03-09 e terça-feira 2026-03-10
    inicio = date(2026, 3, 9)
    fim = date(2026, 3, 10)

    registros_raw = [
        # ana: entrada sem saida no dia 9
        ("ana", "2026-03-09", "2026-03-09 08:00:00", "inicio"),
        # ana: jornada muito alta no dia 10
        ("ana", "2026-03-10", "2026-03-10 06:00:00", "inicio"),
        ("ana", "2026-03-10", "2026-03-10 20:30:00", "fim"),
        # bob: saida sem entrada no dia 9
        ("bob", "2026-03-09", "2026-03-09 18:00:00", "fim"),
        # bob: sem registro no dia 10
    ]

    pendencias = detectar_pendencias_ponto(
        usuarios_considerados=usuarios,
        usuarios_mapa=usuarios_mapa,
        data_inicio=inicio,
        data_fim=fim,
        registros_raw=registros_raw,
        feriados_periodo=set(),
        ignoradas=set(),
    )

    tipos = {(p["usuario"], p["data"], p["tipo_key"]) for p in pendencias}

    assert ("ana", "2026-03-09", "entrada_sem_saida") in tipos
    assert ("ana", "2026-03-10", "horas_muito_altas") in tipos
    assert ("bob", "2026-03-09", "saida_sem_entrada") in tipos
    assert ("bob", "2026-03-10", "dia_sem_registro") in tipos


def test_respeita_ignoradas_feriados_e_fim_de_semana():
    usuarios = ["ana"]
    usuarios_mapa = {"ana": "Ana"}

    # Sexta (13), sábado (14), domingo (15), segunda (16)
    inicio = date(2026, 3, 13)
    fim = date(2026, 3, 16)

    registros_raw = [
        ("ana", "2026-03-13", "2026-03-13 08:00:00", "inicio"),
    ]

    ignoradas = {("ana", "2026-03-13", "entrada_sem_saida")}
    feriados = {"2026-03-16"}

    pendencias = detectar_pendencias_ponto(
        usuarios_considerados=usuarios,
        usuarios_mapa=usuarios_mapa,
        data_inicio=inicio,
        data_fim=fim,
        registros_raw=registros_raw,
        feriados_periodo=feriados,
        ignoradas=ignoradas,
    )

    # sexta foi ignorada, sab/dom sao filtrados, segunda e feriado.
    assert pendencias == []
