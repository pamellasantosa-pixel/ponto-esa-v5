"""
Sistema de Banco de Horas - Ponto ExSA v5.0
Gerencia o saldo de horas dos funcionários
"""

import sqlite3
from database_postgresql import get_connection
from datetime import datetime, timedelta, date, time as time_type
import calendar


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
        # SQLite retorna string
        return datetime.strptime(time_value, "%H:%M")
    return time_value


class BancoHorasSystem:
    def __init__(self):
        pass

            
    def calcular_banco_horas(self, usuario, data_inicio, data_fim):
        """Calcula o saldo do banco de horas para um usuário em um período"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar jornada prevista do usuário
        cursor.execute("""
            SELECT jornada_inicio_previsto, jornada_fim_previsto 
            FROM usuarios WHERE usuario = %s
        """, (usuario,))
        
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
        cursor.execute("""
            SELECT DATE(data_hora) as data, MIN(data_hora) as primeiro, MAX(data_hora) as ultimo,
                   COUNT(*) as total_registros
            FROM registros_ponto 
            WHERE usuario = %s AND DATE(data_hora) BETWEEN %s AND %s
            GROUP BY DATE(data_hora)
            ORDER BY data
        """, (usuario, data_inicio, data_fim))
        
        registros_por_dia = cursor.fetchall()
        
        # Buscar horas extras aprovadas
        cursor.execute("""
            SELECT data, hora_inicio, hora_fim FROM solicitacoes_horas_extras 
            WHERE usuario = %s AND status = 'aprovado' AND data BETWEEN %s AND %s
        """, (usuario, data_inicio, data_fim))
        
        horas_extras_aprovadas = cursor.fetchall()
        
        # Buscar ausências sem comprovante
        cursor.execute("""
            SELECT data_inicio, data_fim FROM ausencias 
            WHERE usuario = %s AND nao_possui_comprovante = 1 
            AND data_inicio <= %s AND data_fim >= %s
        """, (usuario, data_fim, data_inicio))
        
        ausencias_sem_comprovante = cursor.fetchall()
        
        # Buscar atestados de horas aprovados
        cursor.execute("""
            SELECT data, total_horas FROM atestado_horas 
            WHERE usuario = %s AND status = 'aprovado' AND data BETWEEN %s AND %s
        """, (usuario, data_inicio, data_fim))
        
        atestados_aprovados = cursor.fetchall()
        
        conn.close()
        
        # Processar cada dia
        extrato = []
        saldo_total = 0
        
        # Processar registros de ponto
        for registro in registros_por_dia:
            data_reg = registro[0]
            # PostgreSQL retorna datetime, SQLite retorna string
            if isinstance(registro[1], datetime):
                primeiro = registro[1]
            else:
                primeiro = datetime.strptime(registro[1], "%Y-%m-%d %H:%M:%S")
            
            if isinstance(registro[2], datetime):
                ultimo = registro[2]
            else:
                ultimo = datetime.strptime(registro[2], "%Y-%m-%d %H:%M:%S")
            
            # Verificar se é domingo ou feriado
            if isinstance(data_reg, date):
                data_obj = data_reg
            elif isinstance(data_reg, datetime):
                data_obj = data_reg.date()
            else:
                data_obj = datetime.strptime(data_reg, "%Y-%m-%d").date()
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
                    "saldo_parcial": saldo_total + credito
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
                        "saldo_parcial": saldo_total - atraso
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
                        "saldo_parcial": saldo_total - saida_antecipada
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
                            "saldo_parcial": saldo_total
                        })
        
        # Processar horas extras aprovadas
        for he in horas_extras_aprovadas:
            data_he = he[0]
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
                "saldo_parcial": saldo_total + horas_extras
            })
            saldo_total += horas_extras
        
        # Processar ausências sem comprovante
        for ausencia in ausencias_sem_comprovante:
            data_inicio_aus = datetime.strptime(ausencia[0], "%Y-%m-%d").date()
            data_fim_aus = datetime.strptime(ausencia[1], "%Y-%m-%d").date()
            
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
                        "saldo_parcial": saldo_total - horas_previstas_dia
                    })
                    saldo_total -= horas_previstas_dia
        
        # Processar atestados de horas aprovados (desconto)
        for atestado in atestados_aprovados:
            data_at = atestado[0]
            horas_atestado = atestado[1]
            
            extrato.append({
                "data": data_at,
                "tipo": "atestado_horas",
                "descricao": f"Atestado de horas aprovado ({format_time_duration(horas_atestado)})",
                "credito": 0,
                "debito": horas_atestado,
                "saldo_parcial": saldo_total - horas_atestado
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
            "periodo": {"inicio": data_inicio, "fim": data_fim}
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
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usuario, nome_completo FROM usuarios 
            WHERE ativo = 1 AND tipo = 'funcionario'
            ORDER BY nome_completo
        """)
        
        usuarios = cursor.fetchall()
        conn.close()
        
        saldos = []
        for usuario in usuarios:
            saldo = self.obter_saldo_atual(usuario[0])
            saldos.append({
                "usuario": usuario[0],
                "nome": usuario[1] or usuario[0],
                "saldo": saldo
            })
        
        return saldos
    
    def _eh_feriado(self, data):
        """Verifica se uma data é feriado"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM feriados 
            WHERE data = %s
        """, (data.strftime("%Y-%m-%d"),))
        
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
            ultimo_dia.strftime("%Y-%m-%d")
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
