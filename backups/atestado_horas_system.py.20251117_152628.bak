"""
Sistema de Atestado de Horas - Ponto ExSA v3.0
Permite registro de ausências parciais com controle de horas específicas
"""

import sqlite3
import os
from database_postgresql import get_connection, USE_POSTGRESQL
from datetime import datetime, timedelta
import uuid
import json

# SQL Placeholder para compatibilidade SQLite/PostgreSQL
SQL_PLACEHOLDER = "%s" if USE_POSTGRESQL else "?"


def _parse_datetime(value):
    """Converte valores retornados do banco para datetime (aceita datetime ou string)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.strptime(value.split(".")[0], "%Y-%m-%d %H:%M:%S")
    return None


class AtestadoHorasSystem:
    def __init__(self):
        self.init_database()

    def init_database(self):
        """Inicializa as tabelas necessárias para o sistema de atestado de horas"""
        conn = get_connection()
        cursor = conn.cursor()

        # Tabela para atestados de horas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS atestado_horas (
                id SERIAL PRIMARY KEY,
                usuario TEXT NOT NULL,
                data DATE NOT NULL,
                hora_inicio TIME NOT NULL,
                hora_fim TIME NOT NULL,
                total_horas REAL NOT NULL,
                motivo TEXT,
                arquivo_comprovante TEXT,
                nao_possui_comprovante INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pendente',
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                aprovado_por TEXT,
                data_aprovacao TIMESTAMP,
                observacoes TEXT
            )
        """)

        # Tabela para uploads de arquivos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                id SERIAL PRIMARY KEY,
                usuario TEXT NOT NULL,
                nome_original TEXT NOT NULL,
                nome_arquivo TEXT NOT NULL,
                tipo_arquivo TEXT NOT NULL,
                tamanho INTEGER NOT NULL,
                caminho TEXT NOT NULL,
                relacionado_a TEXT,
                relacionado_id INTEGER,
                data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def calcular_horas_ausencia(self, hora_inicio, hora_fim):
        """Calcula o total de horas entre início e fim da ausência"""
        try:
            inicio = datetime.strptime(hora_inicio, "%H:%M")
            fim = datetime.strptime(hora_fim, "%H:%M")

            # Se fim for menor que início, assumir que passou para o próximo dia
            if fim < inicio:
                fim += timedelta(days=1)

            diferenca = fim - inicio
            return diferenca.total_seconds() / 3600  # Retorna em horas
        except:
            return 0

    def registrar_atestado_horas(self, usuario, data, hora_inicio, hora_fim, motivo, arquivo_comprovante=None, nao_possui_comprovante=0):
        """Registra um novo atestado de horas

        nao_possui_comprovante: inteiro (0/1) indicando se o usuário informou que não possui atestado físico.
        """
        total_horas = self.calcular_horas_ausencia(hora_inicio, hora_fim)

        if total_horas <= 0:
            return {"success": False, "message": "Horários inválidos"}

        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Persistir o indicador nao_possui_comprovante conforme informado pela UI
            cursor.execute(f"""
                INSERT INTO atestado_horas 
                (usuario, data, hora_inicio, hora_fim, total_horas, motivo, arquivo_comprovante, nao_possui_comprovante)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
            """, (usuario, data, hora_inicio, hora_fim, total_horas, motivo, arquivo_comprovante, 1 if nao_possui_comprovante else 0))

            atestado_id = cursor.lastrowid
            conn.commit()

            return {
                "success": True,
                "message": "Atestado de horas registrado com sucesso",
                "id": atestado_id,
                "total_horas": total_horas
            }
        except Exception as e:
            return {"success": False, "message": f"Erro ao registrar: {str(e)}"}
        finally:
            conn.close()

    def listar_atestados_usuario(self, usuario, data_inicio=None, data_fim=None):
        """Lista atestados de horas de um usuário"""
        conn = get_connection()
        cursor = conn.cursor()

        query = f"SELECT * FROM atestado_horas WHERE usuario = {SQL_PLACEHOLDER}"
        params = [usuario]

        if data_inicio and data_fim:
            query += " AND data BETWEEN %s AND %s"
            params.extend([data_inicio, data_fim])

        query += " ORDER BY data DESC, hora_inicio ASC"

        cursor.execute(query, params)
        atestados = cursor.fetchall()
        conn.close()

        # Converter para lista de dicionários
        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'total_horas',
                   'motivo', 'arquivo_comprovante', 'nao_possui_comprovante', 'status', 'data_registro',
                   'aprovado_por', 'data_aprovacao', 'observacoes']

        return [dict(zip(colunas, atestado)) for atestado in atestados]

    def listar_todos_atestados(self, status=None):
        """Lista todos os atestados (para gestores)"""
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM atestado_horas"
        params = []

        if status:
            query += f" WHERE status = {SQL_PLACEHOLDER}"
            params.append(status)

        query += " ORDER BY data_registro DESC"

        cursor.execute(query, params)
        atestados = cursor.fetchall()
        conn.close()

        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'total_horas',
                   'motivo', 'arquivo_comprovante', 'nao_possui_comprovante', 'status', 'data_registro',
                   'aprovado_por', 'data_aprovacao', 'observacoes']

        return [dict(zip(colunas, atestado)) for atestado in atestados]

    def aprovar_atestado(self, atestado_id, aprovado_por, observacoes=None):
        """Aprova um atestado de horas"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                UPDATE atestado_horas 
                SET status = 'aprovado', aprovado_por = {SQL_PLACEHOLDER}, data_aprovacao = {SQL_PLACEHOLDER}, observacoes = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
            """, (aprovado_por, datetime.now().isoformat(), observacoes, atestado_id))

            conn.commit()
            return {"success": True, "message": "Atestado aprovado com sucesso"}
        except Exception as e:
            return {"success": False, "message": f"Erro ao aprovar: {str(e)}"}
        finally:
            conn.close()

    def rejeitar_atestado(self, atestado_id, rejeitado_por, observacoes):
        """Rejeita um atestado de horas"""
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                UPDATE atestado_horas 
                SET status = 'rejeitado', aprovado_por = {SQL_PLACEHOLDER}, data_aprovacao = {SQL_PLACEHOLDER}, observacoes = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
            """, (rejeitado_por, datetime.now().isoformat(), observacoes, atestado_id))

            conn.commit()
            return {"success": True, "message": "Atestado rejeitado"}
        except Exception as e:
            return {"success": False, "message": f"Erro ao rejeitar: {str(e)}"}
        finally:
            conn.close()

    def calcular_horas_trabalhadas_com_atestado(self, usuario, data):
        """Calcula horas trabalhadas descontando atestados de horas aprovados"""
        # Buscar registros de ponto do dia
        conn = get_connection()
        cursor = conn.cursor()

        # Registros de ponto
        cursor.execute(f"""
            SELECT data_hora, tipo FROM registros_ponto 
            WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER} 
            ORDER BY data_hora
        """, (usuario, data))
        registros_ponto = cursor.fetchall()

        # Atestados de horas aprovados
        cursor.execute(f"""
            SELECT total_horas FROM atestado_horas 
            WHERE usuario = {SQL_PLACEHOLDER} AND data = {SQL_PLACEHOLDER} AND status = 'aprovado'
        """, (usuario, data))
        atestados = cursor.fetchall()

        conn.close()

        # Calcular horas trabalhadas pelos registros de ponto
        horas_trabalhadas = 0
        if len(registros_ponto) >= 2:
            primeiro_dt = _parse_datetime(registros_ponto[0][0])
            ultimo_dt = _parse_datetime(registros_ponto[-1][0])

            if not primeiro_dt or not ultimo_dt:
                return {
                    "horas_registradas": 0,
                    "horas_atestado": 0,
                    "horas_liquidas": 0
                }

            # Lógica simplificada: diferença entre primeiro e último registro
            primeiro_time = primeiro_dt.time()
            ultimo_time = ultimo_dt.time()

            primeiro_dt = datetime.combine(datetime.min, primeiro_time)
            ultimo_dt = datetime.combine(datetime.min, ultimo_time)

            if ultimo_dt < primeiro_dt:
                ultimo_dt += timedelta(days=1)

            diferenca = ultimo_dt - primeiro_dt
            horas_trabalhadas = diferenca.total_seconds() / 3600

            # Descontar 1 hora de almoço se trabalhou mais de 6 horas
            if horas_trabalhadas > 6:
                horas_trabalhadas -= 1

        # Descontar horas de atestado
        total_horas_atestado = sum([atestado[0] for atestado in atestados])
        horas_liquidas = max(0, horas_trabalhadas - total_horas_atestado)

        return {
            "horas_registradas": horas_trabalhadas,
            "horas_atestado": total_horas_atestado,
            "horas_liquidas": horas_liquidas
        }

    def gerar_relatorio_atestados(self, data_inicio, data_fim, usuario=None):
        """Gera relatório de atestados de horas por período"""
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT usuario, data, hora_inicio, hora_fim, total_horas, motivo, status
            FROM atestado_horas 
            WHERE data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
        """
        params = [data_inicio, data_fim]

        if usuario:
            query += f" AND usuario = {SQL_PLACEHOLDER}"
            params.append(usuario)

        query += " ORDER BY data DESC, usuario ASC"

        cursor.execute(query, params)
        dados = cursor.fetchall()
        conn.close()

        # Agrupar por usuário
        relatorio = {}
        for linha in dados:
            usuario_rel = linha[0]
            if usuario_rel not in relatorio:
                relatorio[usuario_rel] = {
                    "total_horas": 0,
                    "total_atestados": 0,
                    "aprovados": 0,
                    "pendentes": 0,
                    "rejeitados": 0,
                    "detalhes": []
                }

            relatorio[usuario_rel]["total_atestados"] += 1
            relatorio[usuario_rel]["total_horas"] += linha[4]  # total_horas

            status = linha[6]
            if status == "aprovado":
                relatorio[usuario_rel]["aprovados"] += 1
            elif status == "pendente":
                relatorio[usuario_rel]["pendentes"] += 1
            elif status == "rejeitado":
                relatorio[usuario_rel]["rejeitados"] += 1

            relatorio[usuario_rel]["detalhes"].append({
                "data": linha[1],
                "hora_inicio": linha[2],
                "hora_fim": linha[3],
                "total_horas": linha[4],
                "motivo": linha[5],
                "status": linha[6]
            })

        return relatorio

    def validar_conflito_ponto(self, usuario, data, hora_inicio, hora_fim):
        """Verifica se há conflito com registros de ponto existentes"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT data_hora FROM registros_ponto 
            WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER} 
            ORDER BY data_hora
        """, (usuario, data))
        registros = cursor.fetchall()
        conn.close()

        if not registros:
            return {"conflito": False, "message": "Nenhum registro de ponto encontrado"}

        # Converter horários para comparação
        inicio_atestado = datetime.strptime(hora_inicio, "%H:%M").time()
        fim_atestado = datetime.strptime(hora_fim, "%H:%M").time()

        conflitos = []
        for registro in registros:
            # Extrair apenas a parte da hora do registro de ponto
            registro_dt = _parse_datetime(registro[0])
            if not registro_dt:
                continue

            hora_registro = registro_dt.time()
            hora_registro_str = hora_registro.strftime("%H:%M")

            if inicio_atestado <= hora_registro <= fim_atestado:
                conflitos.append(hora_registro_str)

        if conflitos:
            return {
                "conflito": True,
                "message": f"Conflito com registros de ponto: {', '.join(conflitos)}"
            }

        return {"conflito": False, "message": "Nenhum conflito encontrado"}

# Funções utilitárias para integração com Streamlit


def format_time_duration(horas):
    """Formata duração em horas para exibição"""
    if horas < 1:
        minutos = int(horas * 60)
        return f"{minutos} min"
    else:
        h = int(horas)
        m = int((horas - h) * 60)
        return f"{h}h {m}min" if m > 0 else f"{h}h"


def get_status_color(status):
    """Retorna cor para status do atestado"""
    colors = {
        "pendente": "orange",
        "aprovado": "green",
        "rejeitado": "red"
    }
    return colors.get(status, "gray")


def get_status_emoji(status):
    """Retorna emoji para status do atestado"""
    emojis = {
        "pendente": "⏳",
        "aprovado": "✅",
        "rejeitado": "❌"
    }
    return emojis.get(status, "📄")

