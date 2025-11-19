"""
Sistema de Jornada Semanal Variável
Permite configurar horários diferentes para cada dia da semana
"""

import os
import logging
from datetime import datetime, time

# Verificar se usa PostgreSQL e importar o módulo correto
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'

if USE_POSTGRESQL:
    from ponto_esa_v5.database_postgresql import get_connection, SQL_PLACEHOLDER
else:
    from database import get_connection, SQL_PLACEHOLDER

logger = logging.getLogger(__name__)

JORNADA_COLUMNS = [
    # Segunda-feira
    ("trabalha_seg", "INTEGER DEFAULT 1"),
    ("jornada_seg_inicio", "TIME"),
    ("jornada_seg_fim", "TIME"),
    ("intervalo_seg", "INTEGER DEFAULT 60"),  # intervalo em minutos
    
    # Terça-feira
    ("trabalha_ter", "INTEGER DEFAULT 1"),
    ("jornada_ter_inicio", "TIME"),
    ("jornada_ter_fim", "TIME"),
    ("intervalo_ter", "INTEGER DEFAULT 60"),
    
    # Quarta-feira
    ("trabalha_qua", "INTEGER DEFAULT 1"),
    ("jornada_qua_inicio", "TIME"),
    ("jornada_qua_fim", "TIME"),
    ("intervalo_qua", "INTEGER DEFAULT 60"),
    
    # Quinta-feira
    ("trabalha_qui", "INTEGER DEFAULT 1"),
    ("jornada_qui_inicio", "TIME"),
    ("jornada_qui_fim", "TIME"),
    ("intervalo_qui", "INTEGER DEFAULT 60"),
    
    # Sexta-feira
    ("trabalha_sex", "INTEGER DEFAULT 1"),
    ("jornada_sex_inicio", "TIME"),
    ("jornada_sex_fim", "TIME"),
    ("intervalo_sex", "INTEGER DEFAULT 60"),
    
    # Sábado
    ("trabalha_sab", "INTEGER DEFAULT 0"),
    ("jornada_sab_inicio", "TIME"),
    ("jornada_sab_fim", "TIME"),
    ("intervalo_sab", "INTEGER DEFAULT 60"),
    
    # Domingo
    ("trabalha_dom", "INTEGER DEFAULT 0"),
    ("jornada_dom_inicio", "TIME"),
    ("jornada_dom_fim", "TIME"),
    ("intervalo_dom", "INTEGER DEFAULT 60"),
]


def ensure_jornada_columns():
    """Garante que as colunas da jornada semanal existam no banco de dados."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if USE_POSTGRESQL:
            for column, definition in JORNADA_COLUMNS:
                cursor.execute(
                    f"ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS {column} {definition}"
                )
        else:
            for column, definition in JORNADA_COLUMNS:
                try:
                    cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {column} {definition}")
                except Exception:
                    # Coluna já existe (SQLite não possui IF NOT EXISTS para ADD COLUMN)
                    continue

        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.warning("Não foi possível garantir colunas de jornada semanal: %s", exc)
    finally:
        conn.close()


ensure_jornada_columns()

DIAS_SEMANA = {
    0: 'seg',  # Segunda-feira
    1: 'ter',  # Terça-feira
    2: 'qua',  # Quarta-feira
    3: 'qui',  # Quinta-feira
    4: 'sex',  # Sexta-feira
    5: 'sab',  # Sábado
    6: 'dom'   # Domingo
}

NOMES_DIAS = {
    'seg': 'Segunda-feira',
    'ter': 'Terça-feira',
    'qua': 'Quarta-feira',
    'qui': 'Quinta-feira',
    'sex': 'Sexta-feira',
    'sab': 'Sábado',
    'dom': 'Domingo'
}

def obter_jornada_usuario(usuario):
    """
    Obtém configuração completa de jornada semanal do usuário
    
    Returns:
        dict: Dicionário com configuração de cada dia da semana
        {
            'seg': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
            'ter': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
            ...
        }
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = f"""
        SELECT 
            trabalha_seg, jornada_seg_inicio, jornada_seg_fim, intervalo_seg,
            trabalha_ter, jornada_ter_inicio, jornada_ter_fim, intervalo_ter,
            trabalha_qua, jornada_qua_inicio, jornada_qua_fim, intervalo_qua,
            trabalha_qui, jornada_qui_inicio, jornada_qui_fim, intervalo_qui,
            trabalha_sex, jornada_sex_inicio, jornada_sex_fim, intervalo_sex,
            trabalha_sab, jornada_sab_inicio, jornada_sab_fim, intervalo_sab,
            trabalha_dom, jornada_dom_inicio, jornada_dom_fim, intervalo_dom,
            jornada_inicio_previsto, jornada_fim_previsto
        FROM usuarios
        WHERE usuario = {SQL_PLACEHOLDER}
    """
    
    cursor.execute(query, (usuario,))
    resultado = cursor.fetchone()
    conn.close()
    
    if not resultado:
        return None
    
    # Criar dicionário com configuração de cada dia
    jornada = {}
    dias_keys = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
    
    for i, dia in enumerate(dias_keys):
        idx = i * 4
        trabalha = bool(resultado[idx]) if resultado[idx] is not None else True
        inicio = resultado[idx + 1] if resultado[idx + 1] else resultado[-2]
        fim = resultado[idx + 2] if resultado[idx + 2] else resultado[-1]
        intervalo = resultado[idx + 3] if resultado[idx + 3] is not None else 60
        
        jornada[dia] = {
            'trabalha': trabalha,
            'inicio': str(inicio) if inicio else '08:00',
            'fim': str(fim) if fim else '17:00',
            'intervalo': int(intervalo) if intervalo else 60  # em minutos
        }
    
    return jornada

def obter_jornada_do_dia(usuario, data=None):
    """
    Obtém horários de trabalho para um dia específico
    
    Args:
        usuario: Nome de usuário
        data: datetime ou date (padrão: hoje)
    
    Returns:
        dict: {'trabalha': bool, 'inicio': str, 'fim': str} ou None
    """
    if data is None:
        data = datetime.now()
    
    dia_semana = data.weekday()  # 0 = segunda, 6 = domingo
    dia_key = DIAS_SEMANA[dia_semana]
    
    jornada = obter_jornada_usuario(usuario)
    if not jornada:
        return None
    
    return jornada.get(dia_key)

def usuario_trabalha_hoje(usuario, data=None):
    """
    Verifica se usuário trabalha em determinada data
    
    Args:
        usuario: Nome de usuário
        data: datetime ou date (padrão: hoje)
    
    Returns:
        bool: True se trabalha, False se não trabalha
    """
    jornada_dia = obter_jornada_do_dia(usuario, data)
    if not jornada_dia:
        return True  # Padrão: considera que trabalha
    
    return jornada_dia.get('trabalha', True)

def salvar_jornada_semanal(usuario_id, jornada_config):
    """
    Salva configuração de jornada semanal para um usuário
    
    Args:
        usuario_id: ID do usuário
        jornada_config: dict com configuração de cada dia
        {
            'seg': {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60},
            ...
        }
    
    Returns:
        bool: True se salvou com sucesso
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Construir query de update dinamicamente
        updates = []
        params = []
        
        for dia in ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']:
            if dia in jornada_config:
                config = jornada_config[dia]
                
                # Trabalha
                updates.append(f"trabalha_{dia} = {SQL_PLACEHOLDER}")
                params.append(int(config.get('trabalha', True)))
                
                # Início
                if config.get('inicio'):
                    updates.append(f"jornada_{dia}_inicio = {SQL_PLACEHOLDER}")
                    params.append(config['inicio'])
                
                # Fim
                if config.get('fim'):
                    updates.append(f"jornada_{dia}_fim = {SQL_PLACEHOLDER}")
                    params.append(config['fim'])
                
                # Intervalo (novo)
                intervalo = int(config.get('intervalo', 60)) if config.get('intervalo') else 60
                updates.append(f"intervalo_{dia} = {SQL_PLACEHOLDER}")
                params.append(intervalo)
        
        # Adicionar ID do usuário ao final dos parâmetros
        params.append(usuario_id)
        
        # Executar update
        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = {SQL_PLACEHOLDER}"
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro ao salvar jornada semanal: {e}")
        conn.close()
        return False

def copiar_jornada_padrao_para_dias(usuario_id, dias=['seg', 'ter', 'qua', 'qui', 'sex']):
    """
    Copia jornada padrão para dias específicos
    
    Args:
        usuario_id: ID do usuário
        dias: Lista de dias para copiar (padrão: seg-sex)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Buscar jornada padrão
        cursor.execute(f"""
            SELECT jornada_inicio_previsto, jornada_fim_previsto
            FROM usuarios
            WHERE id = {SQL_PLACEHOLDER}
        """, (usuario_id,))
        
        resultado = cursor.fetchone()
        if not resultado:
            return False
        
        inicio_padrao, fim_padrao = resultado
        
        # Construir updates
        updates = []
        params = []
        
        for dia in dias:
            updates.append(f"jornada_{dia}_inicio = {SQL_PLACEHOLDER}")
            params.append(inicio_padrao)
            updates.append(f"jornada_{dia}_fim = {SQL_PLACEHOLDER}")
            params.append(fim_padrao)
            updates.append(f"trabalha_{dia} = {SQL_PLACEHOLDER}")
            params.append(1)
        
        params.append(usuario_id)
        
        query = f"UPDATE usuarios SET {', '.join(updates)} WHERE id = {SQL_PLACEHOLDER}"
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro ao copiar jornada padrão: {e}")
        conn.close()
        return False

def verificar_horario_saida_proximo(usuario, margem_minutos=30):
    """
    Verifica se está próximo do horário de saída do usuário
    
    Args:
        usuario: Nome de usuário
        margem_minutos: Quantos minutos antes do fim considerar "próximo"
    
    Returns:
        dict: {
            'proximo': bool,
            'horario_saida': str,
            'minutos_restantes': int
        }
    """
    from datetime import datetime, timedelta
    
    agora = datetime.now()
    jornada_dia = obter_jornada_do_dia(usuario, agora)
    
    if not jornada_dia or not jornada_dia.get('trabalha'):
        return {'proximo': False, 'horario_saida': None, 'minutos_restantes': None}
    
    # Converter horário de saída para datetime de hoje
    horario_saida_val = jornada_dia['fim']

    def parse_hora_minuto(value):
        if isinstance(value, time):
            return value.hour, value.minute

        value_str = str(value).strip() if value is not None else ''
        if not value_str:
            return None

        try:
            # Suporta formatos ISO (ex: 17:30:00 ou 17:30:00+00:00)
            hora_iso = datetime.fromisoformat(value_str)
            return hora_iso.hour, hora_iso.minute
        except (ValueError, TypeError):
            partes = value_str.split(':')
            if len(partes) >= 2:
                try:
                    return int(partes[0]), int(partes[1])
                except ValueError:
                    return None
        return None

    hora_minuto = parse_hora_minuto(horario_saida_val)
    if hora_minuto is None:
        logger.warning(
            "Horário de saída inválido para usuário %s: %s", usuario, horario_saida_val
        )
        return {
            'proximo': False,
            'horario_saida': None,
            'minutos_restantes': None
        }

    hora, minuto = hora_minuto
    horario_saida = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)
    horario_saida_str = f"{hora:02d}:{minuto:02d}"
    
    # Calcular diferença
    diferenca = horario_saida - agora
    minutos_restantes = int(diferenca.total_seconds() / 60)
    
    # Está próximo se faltam menos que margem_minutos E já passou do horário de início
    proximo = 0 <= minutos_restantes <= margem_minutos
    
    return {
        'proximo': proximo,
        'horario_saida': horario_saida_str,
        'minutos_restantes': minutos_restantes if minutos_restantes > 0 else 0
    }
