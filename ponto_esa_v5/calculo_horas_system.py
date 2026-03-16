"""
Sistema de Cálculo de Horas - Ponto ExSA v5.0
Implementa regras de negócio para cálculo de horas trabalhadas
"""

import logging
import sqlite3
from database import get_connection, return_connection, SQL_PLACEHOLDER
from datetime import datetime, timedelta, date
import calendar

logger = logging.getLogger(__name__)


def safe_datetime_parse(value):
    """Converte value para datetime de forma segura (compatível PostgreSQL/SQLite)"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Tentar formatos comuns
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return None


class CalculoHorasSystem:
    def __init__(self, db_path: str | None = None):
        """Inicializa o sistema de cálculo de horas.

        Args:
            db_path (str|None): Caminho para um banco SQLite local para testes. Se None, usa get_connection().
        """
        global SQL_PLACEHOLDER
        self._test_db_path = db_path
        if self._test_db_path:
            # Em testes com SQLite local, força placeholder compatível neste módulo.
            SQL_PLACEHOLDER = "?"
        else:
            SQL_PLACEHOLDER = __import__("database").SQL_PLACEHOLDER

    def _get_connection(self):
        """Retorna conexão: usa banco de testes (SQLite) se configurado, senão usa get_connection()."""
        if self._test_db_path:
            return sqlite3.connect(self._test_db_path)
        return get_connection()

        
    def calcular_horas_dia(self, usuario, data):
        """Calcula as horas trabalhadas em um dia específico com todas as regras"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Buscar registros do dia
            cursor.execute(f"""
                SELECT data_hora, tipo FROM registros_ponto 
                WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER} 
                ORDER BY data_hora ASC
            """, (usuario, data))

            registros = cursor.fetchall()

            if len(registros) < 2:
                # Retornar um dicionário consistente contendo todas as chaves esperadas
                return {
                    "horas_trabalhadas": 0,
                    "horas_liquidas": 0,
                    "horas_finais": 0,
                    "desconto_almoco": 0,
                    "desconto_atestados": 0,
                    "eh_domingo": False,
                    "eh_feriado": False,
                    "multiplicador": 1,
                    "primeiro_registro": "00:00",
                    "ultimo_registro": "00:00",
                    "total_registros": len(registros),
                    "detalhes": "Registros insuficientes para cálculo"
                }

            # Verificar se é domingo ou feriado
            data_obj = datetime.strptime(data, "%Y-%m-%d").date()
            eh_domingo = data_obj.weekday() == 6
            eh_feriado = self._eh_feriado(data_obj)

            # Calcular horas entre primeiro e último registro
            primeiro = safe_datetime_parse(registros[0][0])
            ultimo = safe_datetime_parse(registros[-1][0])

            if not primeiro or not ultimo:
                return {
                    "horas_trabalhadas": 0,
                    "horas_liquidas": 0,
                    "horas_finais": 0,
                    "desconto_almoco": 0,
                    "desconto_atestados": 0,
                    "eh_domingo": False,
                    "eh_feriado": False,
                    "multiplicador": 1,
                    "primeiro_registro": "00:00",
                    "ultimo_registro": "00:00",
                    "total_registros": len(registros),
                    "detalhes": "Erro ao processar horários"
                }

            horas_trabalhadas = (ultimo - primeiro).total_seconds() / 3600

            # Aplicar desconto de almoço se > 6 horas
            desconto_almoco = 1 if horas_trabalhadas > 6 else 0
            horas_liquidas = horas_trabalhadas - desconto_almoco

            # Aplicar multiplicador para domingos e feriados
            multiplicador = 2 if (eh_domingo or eh_feriado) else 1
            horas_finais = horas_liquidas * multiplicador

            # Buscar atestados de horas aprovados para desconto
            cursor.execute(f"""
                SELECT total_horas FROM atestado_horas 
                WHERE usuario = {SQL_PLACEHOLDER} AND data = {SQL_PLACEHOLDER} AND status = 'aprovado'
            """, (usuario, data))

            atestados = cursor.fetchall()
            total_atestados = sum([a[0] for a in atestados])

            horas_finais = max(0, horas_finais - total_atestados)

            return {
                "horas_trabalhadas": horas_trabalhadas,
                "horas_liquidas": horas_liquidas,
                "horas_finais": horas_finais,
                "desconto_almoco": desconto_almoco,
                "desconto_atestados": total_atestados,
                "eh_domingo": eh_domingo,
                "eh_feriado": eh_feriado,
                "multiplicador": multiplicador,
                "primeiro_registro": primeiro.strftime("%H:%M"),
                "ultimo_registro": ultimo.strftime("%H:%M"),
                "total_registros": len(registros)
            }
        finally:
            # Garantir devolução da conexão ao pool mesmo em caso de exceção
            try:
                return_connection(conn)
            except Exception as e:
                logger.debug("Erro silenciado: %s", e)

    def calcular_horas_periodo(self, usuario, data_inicio, data_fim):
        """Calcula horas trabalhadas em um período - OTIMIZADO (uma única query)"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Buscar todos os registros do período de uma vez
            cursor.execute(f"""
                SELECT DATE(data_hora) as dia, data_hora, tipo 
                FROM registros_ponto 
                WHERE usuario = {SQL_PLACEHOLDER} 
                AND DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
                ORDER BY data_hora ASC
            """, (usuario, data_inicio, data_fim))
            
            todos_registros = cursor.fetchall()
            
            # Agrupar registros por dia
            registros_por_dia = {}
            for row in todos_registros:
                dia = row[0] if isinstance(row[0], str) else str(row[0])
                if dia not in registros_por_dia:
                    registros_por_dia[dia] = []
                registros_por_dia[dia].append((row[1], row[2]))  # (data_hora, tipo)
            
            total_horas = 0
            total_horas_normais = 0
            total_domingos_feriados = 0
            dias_trabalhados = 0
            detalhes_por_dia = []
            
            # Processar cada dia
            for dia_str, registros in registros_por_dia.items():
                # Parse da data
                if isinstance(dia_str, str) and '-' in dia_str:
                    data_obj = datetime.strptime(dia_str, "%Y-%m-%d").date()
                else:
                    data_obj = date.fromisoformat(str(dia_str))
                
                # Verificar se é domingo ou feriado
                info_dia = eh_dia_com_multiplicador(data_obj)
                eh_domingo = info_dia.get("eh_domingo", False)
                eh_feriado = info_dia.get("eh_feriado", False)
                multiplicador = info_dia.get("multiplicador", 1)
                
                # Calcular horas do dia
                horas_trabalhadas = 0
                primeiro_inicio = None
                ultimo_fim = None
                intervalos = []
                
                for data_hora, tipo in registros:
                    dt = safe_datetime_parse(data_hora)
                    if dt is None:
                        continue

                    tipo_norm = str(tipo).strip().lower()

                    if tipo_norm in ("início", "inicio", "entrada"):
                        if primeiro_inicio is None:
                            primeiro_inicio = dt
                    elif tipo_norm in ("fim", "saída", "saida"):
                        ultimo_fim = dt
                    elif tipo_norm in ("início almoço", "inicio almoço", "saída almoço", "saida almoço", "saida_almoco"):
                        intervalos.append(("inicio_intervalo", dt))
                    elif tipo_norm in ("fim almoço", "retorno", "retorno almoço", "retorno_almoco"):
                        intervalos.append(("fim_intervalo", dt))
                
                # Calcular tempo
                if primeiro_inicio and ultimo_fim and ultimo_fim > primeiro_inicio:
                    horas_trabalhadas = (ultimo_fim - primeiro_inicio).total_seconds() / 3600
                    
                    # Descontar intervalos
                    tempo_intervalos = 0
                    inicio_intervalo = None
                    for tipo_int, dt_int in sorted(intervalos, key=lambda x: x[1]):
                        if tipo_int == "inicio_intervalo":
                            inicio_intervalo = dt_int
                        elif tipo_int == "fim_intervalo" and inicio_intervalo:
                            tempo_intervalos += (dt_int - inicio_intervalo).total_seconds() / 3600
                            inicio_intervalo = None
                    
                    horas_liquidas = max(0, horas_trabalhadas - tempo_intervalos)
                else:
                    horas_liquidas = 0
                
                horas_finais = horas_liquidas * multiplicador
                
                if horas_finais > 0:
                    dias_trabalhados += 1
                    total_horas += horas_finais
                    
                    if eh_domingo or eh_feriado:
                        total_domingos_feriados += horas_liquidas
                    else:
                        total_horas_normais += horas_liquidas
                    
                    detalhes_por_dia.append({
                        "data": dia_str,
                        "horas": horas_finais,
                        "tipo": "domingo_feriado" if (eh_domingo or eh_feriado) else "normal",
                        "detalhes": {
                            "horas_trabalhadas": horas_trabalhadas,
                            "horas_liquidas": horas_liquidas,
                            "horas_finais": horas_finais,
                            "multiplicador": multiplicador,
                            "eh_domingo": eh_domingo,
                            "eh_feriado": eh_feriado
                        }
                    })
            
            return {
                "total_horas": total_horas,
                "total_horas_normais": total_horas_normais,
                "total_domingos_feriados": total_domingos_feriados,
                "dias_trabalhados": dias_trabalhados,
                "periodo": {"inicio": data_inicio, "fim": data_fim},
                "detalhes_por_dia": detalhes_por_dia
            }
        finally:
            try:
                return_connection(conn)
            except Exception as e:
                logger.debug("Erro silenciado: %s", e)

    def validar_registros_dia(self, usuario, data):
        """Valida se os registros do dia seguem as regras de negócio"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                    SELECT data_hora, tipo FROM registros_ponto 
                    WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER} 
                    ORDER BY data_hora ASC
                """, (usuario, data))

            registros = cursor.fetchall()
            contadores = {"Início": 0, "Intermediário": 0, "Fim": 0}
            erros = []

            tipos_ordenados = []
            for _, tipo in registros:
                tipo_norm = str(tipo or "").strip().lower()
                if tipo_norm in ("início", "inicio", "entrada"):
                    contadores["Início"] += 1
                    tipos_ordenados.append("inicio")
                elif tipo_norm in ("fim", "saída", "saida"):
                    contadores["Fim"] += 1
                    tipos_ordenados.append("fim")
                else:
                    contadores["Intermediário"] += 1
                    tipos_ordenados.append("intermediario")

            if contadores["Início"] > 1:
                erros.append(f"Múltiplos registros de 'Início' encontrados: {contadores['Início']}")
            if contadores["Fim"] > 1:
                erros.append(f"Múltiplos registros de 'Fim' encontrados: {contadores['Fim']}")
            if tipos_ordenados:
                if tipos_ordenados[0] != "inicio":
                    erros.append("O primeiro registro do dia deve ser 'Início'.")
                if "fim" in tipos_ordenados:
                    indice_fim = tipos_ordenados.index("fim")
                    if any(tipo != "fim" for tipo in tipos_ordenados[indice_fim + 1:]):
                        erros.append("Após um registro de 'Fim', não é permitido lançar novos registros no mesmo dia.")
                if contadores["Intermediário"] > 0 and contadores["Início"] == 0:
                    erros.append("Não é permitido registrar 'Intermediário' sem um 'Início'.")
                if contadores["Fim"] > 0 and contadores["Início"] == 0:
                    erros.append("Não é permitido registrar 'Fim' sem um 'Início'.")

            return {
                "valido": len(erros) == 0,
                "erros": erros,
                "contadores": contadores
            }
        finally:
            return_connection(conn)

    def pode_registrar_tipo(self, usuario, data, tipo):
        """Verifica se o usuário pode registrar um tipo específico de ponto"""
        validacao = self.validar_registros_dia(usuario, data)

        cont = validacao["contadores"]
        if tipo == "Início":
            return cont.get("Início", 0) == 0 and cont.get("Fim", 0) == 0
        elif tipo == "Fim":
            return cont.get("Início", 0) > 0 and cont.get("Fim", 0) == 0
        elif tipo == "Intermediário":
            return cont.get("Início", 0) > 0 and cont.get("Fim", 0) == 0

        return False

    def _eh_feriado(self, data):
        """Verifica se uma data é feriado"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(f"""
                SELECT COUNT(*) FROM feriados 
                WHERE data = {SQL_PLACEHOLDER}
            """, (data.strftime("%Y-%m-%d"),))

            eh_feriado = cursor.fetchone()[0] > 0
            return eh_feriado
        except Exception:
            # Se a tabela feriados não existir ou houver erro, considerar não feriado
            return False
        finally:
            try:
                return_connection(conn)
            except Exception as e:
                logger.debug("Erro silenciado: %s", e)

    def obter_feriados_periodo(self, data_inicio, data_fim):
        """Obtém lista de feriados em um período"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT data, nome, tipo FROM feriados 
            WHERE data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            ORDER BY data
        """, (data_inicio, data_fim))

        feriados = cursor.fetchall()
        return_connection(conn)

        return [{"data": f[0], "nome": f[1], "tipo": f[2]} for f in feriados]

    def gerar_relatorio_horas_extras(self, usuario, data_inicio, data_fim):
        """Gera relatório de horas extras não aprovadas"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Buscar jornada prevista
        cursor.execute(f"""
            SELECT jornada_inicio_previsto, jornada_fim_previsto 
            FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}
        """, (usuario,))

        jornada = cursor.fetchone()
        if not jornada:
            return_connection(conn)
            return {"success": False, "message": "Usuário não encontrado"}

        jornada_inicio = jornada[0] or "08:00"
        jornada_fim = jornada[1] or "17:00"

        # Calcular horas previstas por dia - usar função robusta de parse
        try:
            if ':' in str(jornada_inicio):
                parts = str(jornada_inicio).split(':')
                if len(parts) == 3:
                    inicio_dt = datetime.strptime(jornada_inicio, "%H:%M:%S")
                else:
                    inicio_dt = datetime.strptime(jornada_inicio, "%H:%M")
            else:
                inicio_dt = datetime.strptime("08:00", "%H:%M")
        except Exception as e:
            logger.warning("Erro ao parsear jornada_inicio '%s': %s", jornada_inicio, e)
            inicio_dt = datetime.strptime("08:00", "%H:%M")
        
        try:
            if ':' in str(jornada_fim):
                parts = str(jornada_fim).split(':')
                if len(parts) == 3:
                    fim_dt = datetime.strptime(jornada_fim, "%H:%M:%S")
                else:
                    fim_dt = datetime.strptime(jornada_fim, "%H:%M")
            else:
                fim_dt = datetime.strptime("17:00", "%H:%M")
        except Exception as e:
            logger.warning("Erro ao parsear jornada_fim '%s': %s", jornada_fim, e)
            fim_dt = datetime.strptime("17:00", "%H:%M")
        horas_previstas = (fim_dt - inicio_dt).total_seconds() / 3600
        if horas_previstas > 6:
            horas_previstas -= 1  # Desconto do almoço

        # Buscar dias com possíveis horas extras
        data_atual = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        data_final = datetime.strptime(data_fim, "%Y-%m-%d").date()

        horas_extras_detectadas = []

        while data_atual <= data_final:
            # Pular finais de semana (sábado e domingo)
            if data_atual.weekday() >= 5:
                data_atual += timedelta(days=1)
                continue

            calculo = self.calcular_horas_dia(
                usuario, data_atual.strftime("%Y-%m-%d"))

            if calculo["horas_liquidas"] > horas_previstas:
                # Verificar se já foi aprovada formalmente
                cursor.execute(f"""
                    SELECT COUNT(*) FROM solicitacoes_horas_extras 
                    WHERE usuario = {SQL_PLACEHOLDER} AND data = {SQL_PLACEHOLDER} AND status = 'aprovado'
                """, (usuario, data_atual.strftime("%Y-%m-%d")))

                ja_aprovada = cursor.fetchone()[0] > 0

                if not ja_aprovada:
                    horas_extras = calculo["horas_liquidas"] - horas_previstas
                    horas_extras_detectadas.append({
                        "data": data_atual.strftime("%Y-%m-%d"),
                        "horas_trabalhadas": calculo["horas_liquidas"],
                        "horas_previstas": horas_previstas,
                        "horas_extras": horas_extras,
                        "primeiro_registro": calculo["primeiro_registro"],
                        "ultimo_registro": calculo["ultimo_registro"]
                    })

            data_atual += timedelta(days=1)

        return_connection(conn)

        return {
            "success": True,
            "horas_extras_detectadas": horas_extras_detectadas,
            "total_horas_extras": sum([he["horas_extras"] for he in horas_extras_detectadas])
        }

# Funções utilitárias


def format_time_duration(horas):
    """Formata duração em horas para exibição"""
    if horas == 0:
        return "0h"

    if abs(horas) < 1:
        minutos = int(abs(horas) * 60)
        return f"{minutos}min"
    else:
        h = int(abs(horas))
        m = int((abs(horas) - h) * 60)
        return f"{h}h {m}min" if m > 0 else f"{h}h"


def verificar_se_eh_feriado(data):
    """
    Verifica se uma data é feriado (função pública para uso em interfaces)
    
    Args:
        data: date, datetime ou string no formato 'YYYY-MM-DD'
    
    Returns:
        dict: {'eh_feriado': bool, 'nome_feriado': str ou None, 'tipo': str ou None}
    """
    from datetime import datetime, date
    
    # Converter para date se necessário
    if isinstance(data, str):
        data_obj = datetime.strptime(data, "%Y-%m-%d").date()
    elif isinstance(data, datetime):
        data_obj = data.date()
    else:
        data_obj = data
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"""
            SELECT nome, tipo FROM feriados 
            WHERE data = {SQL_PLACEHOLDER}
        """, (data_obj.strftime("%Y-%m-%d"),))
        
        resultado = cursor.fetchone()
        
        if resultado:
            return {
                'eh_feriado': True,
                'nome_feriado': resultado[0],
                'tipo': resultado[1]
            }
        else:
            return {
                'eh_feriado': False,
                'nome_feriado': None,
                'tipo': None
            }
    except Exception as e:
        logger.warning("Erro ao verificar feriado: %s", e)
        return {
            'eh_feriado': False,
            'nome_feriado': None,
            'tipo': None
        }
    finally:
        try:
            return_connection(conn)
        except Exception as e:
            logger.debug("Erro silenciado: %s", e)


def eh_dia_com_multiplicador(data):
    """
    Verifica se uma data tem multiplicador de horas (domingo ou feriado)
    
    Args:
        data: date, datetime ou string no formato 'YYYY-MM-DD'
    
    Returns:
        dict: {
            'tem_multiplicador': bool,
            'multiplicador': int (1 ou 2),
            'motivo': str,
            'eh_domingo': bool,
            'eh_feriado': bool,
            'nome_feriado': str ou None
        }
    """
    from datetime import datetime, date
    
    # Converter para date se necessário
    if isinstance(data, str):
        data_obj = datetime.strptime(data, "%Y-%m-%d").date()
    elif isinstance(data, datetime):
        data_obj = data.date()
    else:
        data_obj = data
    
    # Verificar se é domingo
    eh_domingo = data_obj.weekday() == 6
    
    # Verificar se é feriado
    info_feriado = verificar_se_eh_feriado(data_obj)
    eh_feriado = info_feriado['eh_feriado']
    
    # Determinar multiplicador e motivo
    if eh_domingo and eh_feriado:
        motivo = f"Domingo E Feriado ({info_feriado['nome_feriado']})"
        tem_multiplicador = True
    elif eh_domingo:
        motivo = "Domingo"
        tem_multiplicador = True
    elif eh_feriado:
        motivo = f"Feriado: {info_feriado['nome_feriado']}"
        tem_multiplicador = True
    else:
        motivo = "Dia normal"
        tem_multiplicador = False
    
    return {
        'tem_multiplicador': tem_multiplicador,
        'multiplicador': 2 if tem_multiplicador else 1,
        'motivo': motivo,
        'eh_domingo': eh_domingo,
        'eh_feriado': eh_feriado,
        'nome_feriado': info_feriado.get('nome_feriado')
    }
