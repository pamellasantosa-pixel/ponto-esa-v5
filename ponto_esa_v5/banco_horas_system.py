"""Sistema de banco de horas com calculo diario consistente com jornada semanal."""

from datetime import datetime, timedelta, date

from database import get_connection, return_connection, SQL_PLACEHOLDER as DB_SQL_PLACEHOLDER

try:
    from calculo_horas_system import CalculoHorasSystem, format_time_duration
    from jornada_semanal_system import obter_jornada_usuario
except ImportError:
    try:
        from ponto_esa_v5.calculo_horas_system import CalculoHorasSystem, format_time_duration
        from ponto_esa_v5.jornada_semanal_system import obter_jornada_usuario
    except ImportError:
        from .calculo_horas_system import CalculoHorasSystem, format_time_duration
        from .jornada_semanal_system import obter_jornada_usuario


SQL_PLACEHOLDER = DB_SQL_PLACEHOLDER


def _to_date(value):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _parse_hhmm(value: str) -> tuple[int, int]:
    txt = str(value or "08:00")
    parts = txt.split(":")
    if len(parts) >= 2:
        return int(parts[0]), int(parts[1])
    return 8, 0


class BancoHorasSystem:
    def __init__(self, connection_manager=None, db_path: str | None = None, **kwargs):
        self.connection_manager = connection_manager
        self.db_path = db_path

    def obter_saldo_atual(self, usuario):
        return self.obter_saldo(usuario)

    def obter_saldo(self, usuario):
        # Mantem janela de 30 dias para saldo rapido em tela.
        hoje = date.today()
        inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
        resultado = self.calcular_banco_horas(usuario, inicio, fim)
        if resultado:
            return resultado.get("saldo_total", 0.0)
        return 0.0

    def adicionar_horas(self, usuario, horas, motivo=""):
        return True

    def remover_horas(self, usuario, horas, motivo=""):
        return True

    def _horas_previstas_dia(self, usuario: str, dia: date) -> float:
        """Calcula horas previstas no dia considerando jornada semanal e intervalo."""
        dias_map = {0: "seg", 1: "ter", 2: "qua", 3: "qui", 4: "sex", 5: "sab", 6: "dom"}
        jornada = obter_jornada_usuario(usuario)
        cfg = jornada.get(dias_map[dia.weekday()], {})

        if not cfg.get("trabalha", False):
            return 0.0

        h_i, m_i = _parse_hhmm(cfg.get("inicio", "08:00"))
        h_f, m_f = _parse_hhmm(cfg.get("fim", "17:00"))
        intervalo_min = int(cfg.get("intervalo", 60) or 0)
        total_min = (h_f * 60 + m_f) - (h_i * 60 + m_i) - intervalo_min
        return max(0.0, round(total_min / 60.0, 2))

    def calcular_banco_horas(self, usuario, data_inicio, data_fim):
        """Calcula extrato de banco de horas comparando horas finais x horas previstas."""
        try:
            calc = CalculoHorasSystem()
            dia_ini = _to_date(data_inicio)
            dia_fim = _to_date(data_fim)

            saldo_parcial = 0.0
            extrato = []
            dia = dia_ini

            while dia <= dia_fim:
                dia_str = dia.strftime("%Y-%m-%d")
                calculo = calc.calcular_horas_dia(usuario, dia_str)

                # horas_finais ja inclui desconto de almoco (1h quando >6h)
                # e multiplicador de domingo/feriado.
                horas_creditaveis = float(calculo.get("horas_finais", 0) or 0)
                horas_previstas = self._horas_previstas_dia(usuario, dia)

                saldo_dia = round(horas_creditaveis - horas_previstas, 2)
                credito = saldo_dia if saldo_dia > 0 else 0.0
                debito = abs(saldo_dia) if saldo_dia < 0 else 0.0
                saldo_parcial = round(saldo_parcial + credito - debito, 2)

                # So adiciona linha no extrato quando houve registro ou expectativa de trabalho.
                if calculo.get("total_registros", 0) > 0 or horas_previstas > 0:
                    extrato.append(
                        {
                            "data": dia_str,
                            "descricao": "Horas trabalhadas x jornada prevista",
                            "credito": round(credito, 2),
                            "debito": round(debito, 2),
                            "saldo_parcial": saldo_parcial,
                        }
                    )

                dia += timedelta(days=1)

            return {"success": True, "saldo_total": round(saldo_parcial, 2), "extrato": extrato}
        except Exception as exc:
            return {"success": False, "message": str(exc), "saldo_total": 0.0, "extrato": []}

    def obter_saldos_todos_usuarios(self):
        """Retorna saldo de todos os funcionarios ativos (ultimos 30 dias)."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"SELECT usuario, nome_completo FROM usuarios WHERE tipo = {SQL_PLACEHOLDER} AND ativo = 1 ORDER BY nome_completo",
                ("funcionario",),
            )
            rows = cursor.fetchall()
            resultado = []
            for usuario, nome_completo in rows:
                saldo = self.obter_saldo(usuario)
                resultado.append({"usuario": usuario, "nome": nome_completo or usuario, "saldo": round(float(saldo or 0), 2)})
            return resultado
        finally:
            return_connection(conn)


def format_saldo_display(saldo_horas):
    """Formata saldo de horas para exibição"""
    if saldo_horas is None:
        return "0h 0m"

    horas = int(abs(saldo_horas))
    minutos = int((abs(saldo_horas) - horas) * 60)

    sinal = "-" if saldo_horas < 0 else ""
    return f"{sinal}{horas}h {minutos:02d}m"


__all__ = ["BancoHorasSystem", "format_saldo_display"]
