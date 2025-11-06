"""
Sistema de Banco de Horas - Ponto ExSA v5.0
Gerencia o saldo de horas dos funcionários
"""

import sqlite3
from database_postgresql import get_connection, USE_POSTGRESQL

# SQL Placeholder para compatibilidade SQLite/PostgreSQL
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"
from datetime import datetime, timedelta, date, time as time_type
import calendar


def safe_datetime_parse(dt_value):
    """Converte para datetime de forma segura entre PostgreSQL e SQLite."""
    if dt_value is None:
        return None
    if isinstance(dt_value, datetime):
        return dt_value
    if isinstance(dt_value, str):
        try:
            return datetime.fromisoformat(dt_value)
        except ValueError:
            try:
                return datetime.strptime(dt_value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.strptime(dt_value.split(".")[0], "%Y-%m-%d %H:%M:%S")
    return dt_value


def safe_date_parse(date_value):
    """Converte para date de forma segura entre PostgreSQL e SQLite."""
    if date_value is None:
        return None
    if isinstance(date_value, date):
        return date_value
    if isinstance(date_value, datetime):
        return date_value.date()
    if isinstance(date_value, str):
        try:
            return datetime.strptime(date_value, "%Y-%m-%d").date()
        except ValueError:
            return datetime.fromisoformat(date_value).date()
    return date_value


def safe_time_parse(time_value):
    """
    Converte para datetime de forma segura (compatível com PostgreSQL e SQLite).
    PostgreSQL retorna time objects, SQLite retorna strings.
    """
    if time_value is None:
        return datetime.strptime("08:00", "%H:%M")
    if isinstance(time_value, time_type):
        # PostgreSQL retorna datetime.time - converter para datetime
        return datetime.combine(date.today(), time_value)
    if isinstance(time_value, str):
        # SQLite retorna string - pode ser HH:MM ou HH:MM:SS
        try:
            return datetime.strptime(time_value, "%H:%M:%S")
        except ValueError:
            return datetime.strptime(time_value, "%H:%M")
    return time_value


class BancoHorasSystem:
    def __init__(self, db_path=None):
        self._db_path = db_path

    def _get_connection(self):
        if isinstance(self._db_path, str):
            return sqlite3.connect(self._db_path)
        if self._db_path:
            return self._db_path
        return get_connection()

    def calcular_banco_horas(self, usuario, data_inicio, data_fim):
        """Calcula o saldo do banco de horas para um usuário em um período"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Buscar jornada prevista do usuário
        cursor.execute(
            f"SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}",
            (usuario,)
        )

        jornada = cursor.fetchone()
        if not jornada:
            conn.close()
            return {"success": False, "message": "Usuário não encontrado"}

        jornada_inicio = jornada[0] or "08:00"
        jornada_fim = jornada[1] or "17:00"

        # Calcular horas previstas por dia (descontando 1h de almoço se > 6h)
        inicio_dt = safe_time_parse(jornada_inicio)
        fim_dt = safe_time_parse(jornada_fim)
        horas_previstas_dia = (fim_dt - inicio_dt).total_seconds() / 3600
        if horas_previstas_dia > 6:
            horas_previstas_dia -= 1  # Desconto do almoço

        # Buscar todos os registros do período
        cursor.execute(
            f"""
            SELECT DATE(data_hora) as data, MIN(data_hora) as primeiro, MAX(data_hora) as ultimo,
                   COUNT(*) as total_registros
            FROM registros_ponto 
            WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            GROUP BY DATE(data_hora)
            ORDER BY data
        """,
            (usuario, data_inicio, data_fim),
        )

        registros_por_dia = cursor.fetchall()

        # Buscar horas extras aprovadas
        cursor.execute(
            f"SELECT data, hora_inicio, hora_fim FROM solicitacoes_horas_extras WHERE usuario = {SQL_PLACEHOLDER} AND status = 'aprovado' AND data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}",
            (usuario, data_inicio, data_fim),
        )

        horas_extras_aprovadas = cursor.fetchall()

        # Buscar ausências sem comprovante
        cursor.execute(
            f"SELECT data_inicio, data_fim FROM ausencias WHERE usuario = {SQL_PLACEHOLDER} AND nao_possui_comprovante = 1 AND data_inicio <= {SQL_PLACEHOLDER} AND data_fim >= {SQL_PLACEHOLDER}",
            (usuario, data_fim, data_inicio),
        )

        ausencias_sem_comprovante = cursor.fetchall()

        # Buscar atestados de horas aprovados
        cursor.execute(
            f"SELECT data, total_horas FROM atestado_horas WHERE usuario = {SQL_PLACEHOLDER} AND status = 'aprovado' AND data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}",
            (usuario, data_inicio, data_fim),
        )

        atestados_aprovados = cursor.fetchall()

        conn.close()

        # Processar cada dia
        extrato = []
        saldo_total = 0

        # Processar registros de ponto
        for registro in registros_por_dia:
            data_reg_date = safe_date_parse(registro[0])
            if data_reg_date is None:
                continue

            data_reg = data_reg_date.strftime("%Y-%m-%d")

            primeiro = safe_datetime_parse(registro[1])
            ultimo = safe_datetime_parse(registro[2])

            if primeiro is None or ultimo is None:
                continue

            data_obj = data_reg_date
            eh_domingo = data_obj.weekday() == 6
            eh_feriado = self._eh_feriado(data_obj)

            # Calcular horas trabalhadas
            horas_trabalhadas = (ultimo - primeiro).total_seconds() / 3600
            if horas_trabalhadas > 6:
                horas_trabalhadas -= 1  # Desconto do almoço

            if eh_domingo or eh_feriado:
                # Domingo ou feriado: 100% de acréscimo
                credito = horas_trabalhadas * 2
                tipo_dia = "Domingo" if eh_domingo else "Feriado"
                extrato.append({
                    "data": data_reg,
                    "tipo": f"trabalho_{tipo_dia.lower()}",
                    "descricao": f"Trabalho em {tipo_dia} (100% acréscimo)",
                    "credito": credito,
                    "debito": 0,
                    "saldo_parcial": saldo_total + credito,
                })
                saldo_total += credito
            else:
                # Dia útil: verificar atrasos e saídas antecipadas

                # Atraso na entrada
                entrada_prevista = datetime.combine(data_obj, safe_time_parse(jornada_inicio).time())
                if primeiro > entrada_prevista:
                    atraso = (primeiro - entrada_prevista).total_seconds() / 3600
                    extrato.append({
                        "data": data_reg,
                        "tipo": "atraso_entrada",
                        "descricao": f"Atraso na entrada ({primeiro.strftime('%H:%M')} vs {jornada_inicio})",
                        "credito": 0,
                        "debito": atraso,
                        "saldo_parcial": saldo_total - atraso,
                    })
                    saldo_total -= atraso

                # Saída antecipada
                saida_prevista = datetime.combine(data_obj, safe_time_parse(jornada_fim).time())
                if ultimo < saida_prevista:
                    saida_antecipada = (saida_prevista - ultimo).total_seconds() / 3600
                    extrato.append({
                        "data": data_reg,
                        "tipo": "saida_antecipada",
                        "descricao": f"Saída antecipada ({ultimo.strftime('%H:%M')} vs {jornada_fim})",
                        "credito": 0,
                        "debito": saida_antecipada,
                        "saldo_parcial": saldo_total - saida_antecipada,
                    })
                    saldo_total -= saida_antecipada

                # Horas extras (além da jornada normal)
                if horas_trabalhadas > horas_previstas_dia:
                    horas_extras = horas_trabalhadas - horas_previstas_dia
                    # Só contabilizar se não foi aprovada formalmente (evitar duplicação)
                    if not any(he[0] == data_reg for he in horas_extras_aprovadas):
                        extrato.append({
                            "data": data_reg,
                            "tipo": "horas_extras_nao_aprovadas",
                            "descricao": f"Horas extras não aprovadas ({format_time_duration(horas_extras)})",
                            "credito": 0,  # Não contabilizar até aprovação
                            "debito": 0,
                            "saldo_parcial": saldo_total,
                        })

        # Processar horas extras aprovadas
        for he in horas_extras_aprovadas:
            data_he_date = safe_date_parse(he[0])
            if data_he_date is None:
                continue

            data_he = data_he_date.strftime("%Y-%m-%d")
            inicio = safe_time_parse(he[1])
            fim = safe_time_parse(he[2])
            if fim <= inicio:
                fim += timedelta(days=1)

            horas_extras = (fim - inicio).total_seconds() / 3600
            extrato.append({
                "data": data_he,
                "tipo": "horas_extras_aprovadas",
                "descricao": f"Horas extras aprovadas ({he[1]} às {he[2]})",
                "credito": horas_extras,
                "debito": 0,
                "saldo_parcial": saldo_total + horas_extras,
            })
            saldo_total += horas_extras

        # Processar ausências sem comprovante
        for ausencia in ausencias_sem_comprovante:
            data_inicio_aus = safe_date_parse(ausencia[0])
            data_fim_aus = safe_date_parse(ausencia[1])

            if not data_inicio_aus or not data_fim_aus:
                continue

            # Calcular dias úteis da ausência
            dias_ausencia = []
            data_atual = data_inicio_aus
            while data_atual <= data_fim_aus:
                if data_atual.weekday() < 5:  # Segunda a sexta
                    dias_ausencia.append(data_atual)
                data_atual += timedelta(days=1)

            for dia in dias_ausencia:
                if data_inicio <= dia.strftime("%Y-%m-%d") <= data_fim:
                    extrato.append({
                        "data": dia.strftime("%Y-%m-%d"),
                        "tipo": "ausencia_sem_comprovante",
                        "descricao": "Ausência não comprovada",
                        "credito": 0,
                        "debito": horas_previstas_dia,
                        "saldo_parcial": saldo_total - horas_previstas_dia,
                    })
                    saldo_total -= horas_previstas_dia

        # Processar atestados de horas aprovados (desconto)
        for atestado in atestados_aprovados:
            data_at_date = safe_date_parse(atestado[0])
            if data_at_date is None:
                continue

            data_at = data_at_date.strftime("%Y-%m-%d")
            horas_atestado = atestado[1]

            extrato.append({
                "data": data_at,
                "tipo": "atestado_horas",
                "descricao": f"Atestado de horas aprovado ({format_time_duration(horas_atestado)})",
                "credito": 0,
                "debito": horas_atestado,
                "saldo_parcial": saldo_total - horas_atestado,
            })
            saldo_total -= horas_atestado

        # Ordenar extrato por data
        extrato.sort(key=lambda x: x["data"])

        # Recalcular saldos parciais
        saldo_acumulado = 0
        for item in extrato:
            saldo_acumulado += item["credito"] - item["debito"]
            item["saldo_parcial"] = saldo_acumulado

        return {
            "success": True,
            "saldo_total": saldo_total,
            "extrato": extrato,
            "periodo": {"inicio": data_inicio, "fim": data_fim},
        }

    def obter_saldo_atual(self, usuario):
        """Obtém o saldo atual do banco de horas de um usuário"""
        # Calcular desde o início do ano até hoje
        hoje = date.today()
        inicio_ano = date(hoje.year, 1, 1)

        resultado = self.calcular_banco_horas(usuario, inicio_ano.strftime("%Y-%m-%d"), hoje.strftime("%Y-%m-%d"))

        if resultado["success"]:
            return resultado["saldo_total"]
        return 0

    def obter_saldos_todos_usuarios(self):
        """Obtém o saldo de banco de horas de todos os usuários ativos"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario' ORDER BY nome_completo"
        )

        usuarios = cursor.fetchall()
        conn.close()

        saldos = []
        for usuario in usuarios:
            saldo = self.obter_saldo_atual(usuario[0])
            saldos.append({
                "usuario": usuario[0],
                "nome": usuario[1] or usuario[0],
                "saldo": saldo,
            })

        return saldos

    def _eh_feriado(self, data):
        """Verifica se uma data é feriado"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT COUNT(*) FROM feriados WHERE data = {SQL_PLACEHOLDER}",
            (data.strftime("%Y-%m-%d"),),
        )

        eh_feriado = cursor.fetchone()[0] > 0
        conn.close()

        return eh_feriado

    def gerar_relatorio_mensal(self, usuario, ano, mes):
        """Gera relatório mensal do banco de horas"""
        # Primeiro e último dia do mês
        primeiro_dia = date(ano, mes, 1)
        ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])

        return self.calcular_banco_horas(
            usuario,
            primeiro_dia.strftime("%Y-%m-%d"),
            ultimo_dia.strftime("%Y-%m-%d"),
        )

# Funções utilitárias
def format_time_duration(horas):
    """Formata duração em horas para exibição"""
    if horas == 0:
        return "0h"
    
    if abs(horas) < 1:
        minutos = int(abs(horas) * 60)
        sinal = "-" if horas < 0 else "+"
        return f"{sinal}{minutos}min"
    else:
        h = int(abs(horas))
        m = int((abs(horas) - h) * 60)
        sinal = "-" if horas < 0 else "+"
        return f"{sinal}{h}h {m}min" if m > 0 else f"{sinal}{h}h"

def format_saldo_display(saldo):
    """Formata saldo para exibição com cores"""
    if saldo > 0:
        return f"✅ +{format_time_duration(saldo)}"
    elif saldo < 0:
        return f"❌ {format_time_duration(saldo)}"
    else:
        return "⚖️ 0h"

