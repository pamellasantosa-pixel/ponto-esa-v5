"""
Sistema de Cálculo de Horas - Ponto ExSA v5.0
Implementa regras de negócio para cálculo de horas trabalhadas
"""

import sqlite3
try:
    from database_postgresql import get_connection, USE_POSTGRESQL, SQL_PLACEHOLDER
except ImportError as e:
    print(f"DEBUG: Import direto falhou em calculo_horas_system: {e}")
    try:
        from ponto_esa_v5.database_postgresql import get_connection, USE_POSTGRESQL, SQL_PLACEHOLDER
    except ImportError as e2:
        print(f"DEBUG: Import absoluto falhou em calculo_horas_system: {e2}")
        try:
            from .database_postgresql import get_connection, USE_POSTGRESQL, SQL_PLACEHOLDER
        except ImportError:
            from database import get_connection, USE_POSTGRESQL, SQL_PLACEHOLDER
from datetime import datetime, timedelta, date
import calendar


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
        self._test_db_path = db_path

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
            # Garantir fechamento da conexão mesmo em caso de exceção
            try:
                conn.close()
            except Exception:
                pass

    def calcular_horas_periodo(self, usuario, data_inicio, data_fim):
        """Calcula horas trabalhadas em um período"""
        data_atual = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        data_final = datetime.strptime(data_fim, "%Y-%m-%d").date()

        total_horas = 0
        total_horas_normais = 0
        total_horas_extras = 0
        total_domingos_feriados = 0
        dias_trabalhados = 0

        detalhes_por_dia = []

        while data_atual <= data_final:
            calculo_dia = self.calcular_horas_dia(
                usuario, data_atual.strftime("%Y-%m-%d"))

            # Usar .get para evitar KeyError caso um cálculo retorne menos chaves
            horas_finais = calculo_dia.get("horas_finais", 0)
            horas_liquidas = calculo_dia.get("horas_liquidas", 0)
            eh_domingo = calculo_dia.get("eh_domingo", False)
            eh_feriado = calculo_dia.get("eh_feriado", False)

            if horas_finais > 0:
                dias_trabalhados += 1
                total_horas += horas_finais

                if eh_domingo or eh_feriado:
                    total_domingos_feriados += horas_liquidas
                else:
                    total_horas_normais += horas_liquidas

                detalhes_por_dia.append({
                    "data": data_atual.strftime("%Y-%m-%d"),
                    "horas": horas_finais,
                    "tipo": "domingo_feriado" if (eh_domingo or eh_feriado) else "normal",
                    "detalhes": calculo_dia
                })

            data_atual += timedelta(days=1)

        return {
            "total_horas": total_horas,
            "total_horas_normais": total_horas_normais,
            "total_domingos_feriados": total_domingos_feriados,
            "dias_trabalhados": dias_trabalhados,
            "periodo": {"inicio": data_inicio, "fim": data_fim},
            "detalhes_por_dia": detalhes_por_dia
        }

    def validar_registros_dia(self, usuario, data):
        """Valida se os registros do dia seguem as regras de negócio"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
                SELECT tipo, COUNT(*) FROM registros_ponto 
                WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER} 
                GROUP BY tipo
            """, (usuario, data))

        contadores = dict(cursor.fetchall())
        conn.close()

        erros = []

        # Validar máximo de 1 início e 1 fim por dia
        if contadores.get("Início", 0) > 1:
            erros.append(
                f"Múltiplos registros de 'Início' encontrados: {contadores['Início']}")

        if contadores.get("Fim", 0) > 1:
            erros.append(
                f"Múltiplos registros de 'Fim' encontrados: {contadores['Fim']}")

        # Intermediários são ilimitados (não validar)

        return {
            "valido": len(erros) == 0,
            "erros": erros,
            "contadores": contadores
        }

    def pode_registrar_tipo(self, usuario, data, tipo):
        """Verifica se o usuário pode registrar um tipo específico de ponto"""
        validacao = self.validar_registros_dia(usuario, data)

        if tipo == "Início":
            return validacao["contadores"].get("Início", 0) == 0
        elif tipo == "Fim":
            return validacao["contadores"].get("Fim", 0) == 0
        elif tipo == "Intermediário":
            return True  # Intermediários são sempre permitidos

        return False

    def _eh_feriado(self, data):
        """Verifica se uma data é feriado"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM feriados 
                WHERE data = %s
            """, (data.strftime("%Y-%m-%d"),))

            eh_feriado = cursor.fetchone()[0] > 0
            return eh_feriado
        except Exception:
            # Se a tabela feriados não existir ou houver erro, considerar não feriado
            return False
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def obter_feriados_periodo(self, data_inicio, data_fim):
        """Obtém lista de feriados em um período"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT data, nome, tipo FROM feriados 
            WHERE data BETWEEN %s AND %s
            ORDER BY data
        """, (data_inicio, data_fim))

        feriados = cursor.fetchall()
        conn.close()

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
            conn.close()
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
        except:
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
        except:
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

        conn.close()

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
        cursor.execute("""
            SELECT nome, tipo FROM feriados 
            WHERE data = %s
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
        print(f"Erro ao verificar feriado: {e}")
        return {
            'eh_feriado': False,
            'nome_feriado': None,
            'tipo': None
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass


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
