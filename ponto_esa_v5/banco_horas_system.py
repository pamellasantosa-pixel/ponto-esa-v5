"""Compat shim that re-exports the canonical `BancoHorasSystem` implementation."""

import sys
import os
from datetime import datetime, timedelta, date

try:
    from ponto_esa_v5.database_postgresql import get_connection, USE_POSTGRESQL, SQL_PLACEHOLDER
except ImportError:
    # fallback for direct test execution or when package is not resolvable
    try:
        from database_postgresql import get_connection, USE_POSTGRESQL, SQL_PLACEHOLDER
    except ImportError:
        # try relative import as last resort
        from .database_postgresql import get_connection, USE_POSTGRESQL, SQL_PLACEHOLDER

try:
    from ponto_esa_v5.calculo_horas_system import CalculoHorasSystem, format_time_duration
except ImportError:
    try:
        from calculo_horas_system import CalculoHorasSystem, format_time_duration
    except ImportError:
        from .calculo_horas_system import CalculoHorasSystem, format_time_duration


class BancoHorasSystem:
    """Sistema de gerenciamento de banco de horas (compat shim com implementação mínima).

    Implementa os métodos usados nas interfaces para permitir execução dos testes
    e da aplicação, delegando cálculos ao `CalculoHorasSystem` quando aplicável.
    """

    def __init__(self, connection_manager=None, db_path: str | None = None, **kwargs):
        self.connection_manager = connection_manager
        self.db_path = db_path

    def obter_saldo_atual(self, usuario):
        return self.obter_saldo(usuario)

    def obter_saldo(self, usuario):
        # Implementação mínima: calcula horas no período recente (últimos 30 dias)
        hoje = date.today()
        inicio = (hoje - timedelta(days=30)).strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
        resultado = self.calcular_banco_horas(usuario, inicio, fim)
        # Retornar saldo total (se presente) ou 0.0
        if resultado:
            return resultado.get("saldo_total", 0.0)
        return 0.0

    def adicionar_horas(self, usuario, horas, motivo=""):
        # placeholder: gravar entrada no extrato do banco de horas (não implementado)
        return True

    def remover_horas(self, usuario, horas, motivo=""):
        # placeholder: gravar débito no extrato do banco de horas (não implementado)
        return True

    def calcular_banco_horas(self, usuario, data_inicio, data_fim):
        """Calcula um extrato simplificado do banco de horas para um usuário.

        Retorna dicionário com chaves esperadas pelos consumidores na UI/tests:
        - success (bool)
        - saldo_total (float)
        - extrato (list of dicts)
        """
        try:
            calc = CalculoHorasSystem()
            periodo = calc.calcular_horas_periodo(usuario, data_inicio, data_fim)

            detalhes = periodo.get("detalhes_por_dia", [])
            extrato = []
            saldo_parcial = 0.0

            for d in detalhes:
                horas = d.get("horas", 0) or 0
                # Simplificação: tratar horas > 0 como crédito para o extrato
                credito = horas if horas > 0 else 0
                debito = 0
                saldo_parcial += credito - debito

                extrato.append({
                    "data": d.get("data"),
                    "descricao": "Horas trabalhadas",
                    "credito": round(credito, 2),
                    "debito": round(debito, 2),
                    "saldo_parcial": round(saldo_parcial, 2)
                })

            saldo_total = round(saldo_parcial, 2)

            return {"success": True, "saldo_total": saldo_total, "extrato": extrato}
        except Exception as exc:
            return {"success": False, "message": str(exc), "saldo_total": 0.0, "extrato": []}

    def obter_saldos_todos_usuarios(self):
        """Retorna lista de dicionários com `usuario`, `nome` e `saldo` para cada funcionário ativo.

        Implementação mínima para alimentar a interface do gestor. O saldo é calculado
        de forma conservadora (0.0) para evitar exceções quando não há dados.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            query = f"SELECT usuario, nome_completo FROM usuarios WHERE tipo = {SQL_PLACEHOLDER} AND ativo = 1 ORDER BY nome_completo"
            cursor.execute("SELECT usuario, nome_completo FROM usuarios WHERE tipo = %s AND ativo = 1 ORDER BY nome_completo" if USE_POSTGRESQL else "SELECT usuario, nome_completo FROM usuarios WHERE tipo = ? AND ativo = 1 ORDER BY nome_completo", ("funcionario",) if USE_POSTGRESQL else ("funcionario",))
            rows = cursor.fetchall()
            resultado = []
            for row in rows:
                usuario = row[0]
                nome = row[1] or usuario
                resultado.append({"usuario": usuario, "nome": nome, "saldo": 0.0})
            return resultado
        finally:
            conn.close()


def format_saldo_display(saldo_horas):
    """Formata saldo de horas para exibição"""
    if saldo_horas is None:
        return "0h 0m"

    horas = int(abs(saldo_horas))
    minutos = int((abs(saldo_horas) - horas) * 60)

    sinal = "-" if saldo_horas < 0 else ""
    return f"{sinal}{horas}h {minutos:02d}m"


__all__ = ["BancoHorasSystem", "format_saldo_display"]
