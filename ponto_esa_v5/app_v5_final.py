"""
Ponto ExSA v5.0 - Sistema de Controle de Ponto
Versão com Horas Extras, Banco de Horas, GPS Real e Melhorias  
Desenvolvido por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos
Última atualização: 24/10/2025 16:45 - TIMEZONE BRASÍLIA CORRIGIDO (get_datetime_br)
Deploy: Render.com | Banco: PostgreSQL
"""

import sys
import os

# Configuração de PATH deve vir antes de imports locais que podem depender de pacotes
# Adicionar o diretório atual ao path
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Adicionar o diretório pai ao path para permitir importação do pacote ponto_esa_v5
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from notifications import notification_manager
from calculo_horas_system import CalculoHorasSystem, format_time_duration
from banco_horas_system import BancoHorasSystem, format_saldo_display
from horas_extras_system import HorasExtrasSystem, get_status_emoji
from atestado_horas_system import AtestadoHorasSystem
from upload_system import UploadSystem, format_file_size, get_file_icon, is_image_file, get_category_name
from push_scheduler import init_push_system, registrar_subscription, verificar_subscription, get_topic_for_user
# Safe import - provide a robust fallback implementation if streamlit_utils is not available
# Use dynamic import to avoid static analysis import errors when the optional module is missing.
import importlib
try:
    _streamlit_utils = importlib.import_module('streamlit_utils')
    safe_download_button = getattr(_streamlit_utils, 'safe_download_button')
except Exception:
    def safe_download_button(label, data, file_name, mime="application/octet-stream", width="content", key=None):
        """Fallback leve caso `streamlit_utils.safe_download_button` não esteja disponível."""
        from io import BytesIO as _BytesIO

        if data is None:
            import streamlit as _st
            _st.warning("Nenhum arquivo disponível para download.")
            return

        content = data.getvalue() if isinstance(data, _BytesIO) else data
        try:
            import streamlit as _st
            _st.download_button(
                label=label,
                data=content,
                file_name=file_name,
                mime=mime,
                width=width,
                key=key,
            )
        except Exception:
            import base64 as _base64
            import streamlit as _st

            encoded = _base64.b64encode(content).decode()
            href = f'<a href="data:{mime};base64,{encoded}" download="{file_name}">{label}</a>'
            _st.markdown(href, unsafe_allow_html=True)

# Importar novos módulos de refatoração
try:
    from connection_manager import execute_query, execute_update, safe_cursor, safe_database_connection
    from error_handler import log_error, get_logger, log_security_event
    REFACTORING_ENABLED = True
except ImportError:
    # Fallbacks for error_handler functions
    import logging as _logging_fb
    def log_error(msg, *args, **kwargs):
        # Avoid %-format crashes when callers pass exception/context objects as extra args.
        if args or kwargs:
            _logging_fb.getLogger("fallback").error("%s | args=%s | kwargs=%s", msg, args, kwargs)
        else:
            _logging_fb.getLogger("fallback").error(msg)
    def log_security_event(event, **kwargs):
        _logging_fb.getLogger("security").info("[SECURITY] %s %s", event, kwargs)
    REFACTORING_ENABLED = False

import streamlit as st
import os
import hashlib
from datetime import datetime, timedelta, date, time
import pandas as pd
import base64
import json
from io import BytesIO
from dotenv import load_dotenv
import pytz  # Para gerenciar fusos horários

# Configurar logger centralizado
from app_logger import get_logger, log_user_action
from constants import agora_br, agora_br_naive, hoje_br
logger = get_logger(__name__)


def _is_missing_column_error(exc):
    """Detecta erro de coluna ausente em bancos com schema legado."""
    msg = str(exc).lower()
    return "column" in msg and "does not exist" in msg


def _execute_select_with_legacy_fallback(cursor, query, params, legacy_query=None, legacy_suffix=()):
    """Executa SELECT com fallback para schema antigo quando colunas novas não existem."""
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as exc:
        if legacy_query and _is_missing_column_error(exc):
            # PostgreSQL aborta a transacao apos erro; limpar estado antes do fallback.
            try:
                if getattr(cursor, "connection", None):
                    cursor.connection.rollback()
            except Exception:
                pass
            cursor.execute(legacy_query, params)
            rows = cursor.fetchall()
            if legacy_suffix:
                return [tuple(row) + tuple(legacy_suffix) for row in rows]
            return rows
        raise


def _parse_hhmm_or_raise(value: str, field_name: str) -> time:
    """Converte texto HH:MM para time com mensagem amigavel."""
    try:
        return datetime.strptime(str(value).strip(), "%H:%M").time()
    except Exception as exc:
        raise ValueError(f"{field_name} invalido. Use HH:MM (ex: 08:15)") from exc


def _try_upgrade_correcao_schema(conn) -> bool:
    """Tenta atualizar schema legado de solicitacoes_correcao_registro em runtime."""
    try:
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE solicitacoes_correcao_registro ADD COLUMN IF NOT EXISTS tipo_solicitacao TEXT DEFAULT 'ajuste_registro'")
        cursor.execute("ALTER TABLE solicitacoes_correcao_registro ADD COLUMN IF NOT EXISTS data_referencia DATE")
        cursor.execute("ALTER TABLE solicitacoes_correcao_registro ADD COLUMN IF NOT EXISTS hora_inicio_solicitada TEXT")
        cursor.execute("ALTER TABLE solicitacoes_correcao_registro ADD COLUMN IF NOT EXISTS hora_saida_solicitada TEXT")
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

# Carregar variáveis de ambiente
load_dotenv()

from database import get_connection as get_db_connection, return_connection as _return_conn, init_db, SQL_PLACEHOLDER

# Expoe placeholder no namespace atual para compatibilidade
current_module = sys.modules[__name__]
current_module.SQL_PLACEHOLDER = SQL_PLACEHOLDER


def get_connection(db_path: str | None = None):
    """Compat helper que delega para `database.get_connection`."""
    return get_db_connection(db_path=db_path)

# Configurar timezone do Brasil (Brasília)
TIMEZONE_BR = pytz.timezone('America/Sao_Paulo')


def get_datetime_br():
    """Retorna datetime atual no fuso horário de Brasília"""
    return datetime.now(TIMEZONE_BR)


# =============================================
# VALIDAÇÃO DE INPUT — Previne crashes e injeção
# =============================================

def validar_texto(valor, nome_campo: str, min_len: int = 1, max_len: int = 255) -> str:
    """Valida e sanitiza input de texto.

    Args:
        valor: valor a validar.
        nome_campo: nome do campo para mensagem de erro.
        min_len: comprimento mínimo.
        max_len: comprimento máximo.

    Returns:
        String sanitizada.

    Raises:
        ValueError: se a validação falhar.
    """
    if valor is None:
        raise ValueError(f"O campo '{nome_campo}' é obrigatório.")
    texto = str(valor).strip()
    if len(texto) < min_len:
        raise ValueError(f"O campo '{nome_campo}' deve ter pelo menos {min_len} caractere(s).")
    if len(texto) > max_len:
        raise ValueError(f"O campo '{nome_campo}' deve ter no máximo {max_len} caracteres.")
    return texto


def validar_numero(valor, nome_campo: str, min_val=None, max_val=None) -> float:
    """Valida input numérico.

    Args:
        valor: valor a converter e validar.
        nome_campo: nome do campo para mensagem de erro.
        min_val: valor mínimo aceito (opcional).
        max_val: valor máximo aceito (opcional).

    Returns:
        Valor numérico validado.

    Raises:
        ValueError: se não for numérico ou fora do range.
    """
    try:
        num = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"O campo '{nome_campo}' deve ser um número válido. Recebido: '{valor}'")
    if min_val is not None and num < min_val:
        raise ValueError(f"O campo '{nome_campo}' deve ser no mínimo {min_val}.")
    if max_val is not None and num > max_val:
        raise ValueError(f"O campo '{nome_campo}' deve ser no máximo {max_val}.")
    return num


def validar_cpf(cpf: str) -> str:
    """Valida e limpa um CPF (apenas dígitos, 11 caracteres).

    Args:
        cpf: CPF com ou sem formatação.

    Returns:
        CPF limpo (apenas dígitos).

    Raises:
        ValueError: se o CPF for inválido.
    """
    import re
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    if len(cpf_limpo) != 11:
        raise ValueError("CPF deve conter exatamente 11 dígitos.")
    if cpf_limpo == cpf_limpo[0] * 11:
        raise ValueError("CPF inválido (todos os dígitos iguais).")
    return cpf_limpo


def validar_email(email: str) -> str:
    """Valida formato básico de email.

    Args:
        email: endereço de email.

    Returns:
        Email limpo e em lowercase.

    Raises:
        ValueError: se o formato for inválido.
    """
    import re
    email = str(email).strip().lower()
    if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError(f"Email inválido: {email}")
    return email

# Utilitários seguros para datas/horas (compatível com PostgreSQL/SQLite)
def _try_parse_dt(value, fmt):
    try:
        return datetime.strptime(str(value), fmt)
    except Exception:
        return None

def safe_datetime_parse(value):
    """Converte value em datetime de forma resiliente.
    Aceita datetime, date, ISO str, e formatos comuns usados no app.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    # Tentar ISO/strings conhecidas
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d", "%d/%m/%Y"):
        parsed = _try_parse_dt(value, fmt)
        if parsed:
            return parsed
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None

def ensure_time(value, default=time(8, 0)):
    """Garante um objeto datetime.time a partir de time|datetime|str."""
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if value:
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(str(value), fmt).time()
            except Exception as e:
                logger.debug("Erro silenciado: %s", e)
    return default


def normalizar_tipo_ponto(tipo):
    valor = str(tipo or "").strip().lower()
    if valor in ("início", "inicio", "entrada"):
        return "inicio"
    if valor in ("intermediário", "intermediario", "intervalo", "almoco", "almoço"):
        return "intermediario"
    if valor in ("fim", "saída", "saida"):
        return "fim"
    return valor


def normalizar_modalidade_ponto(modalidade):
    """Normaliza variantes de modalidade para os valores persistidos no banco."""
    valor = str(modalidade or "").strip().lower()
    if valor in ("", "none", "null"):
        return ""
    if valor in ("presencial",):
        return "presencial"
    if valor in ("home office", "home_office", "home-office", "homeoffice"):
        return "home_office"
    if valor in ("campo",):
        return "campo"
    return valor


def format_datetime_safe(value, fmt="%d/%m/%Y %H:%M", default="-"):
    """Formata data/hora sem quebrar a UI quando o valor for inválido."""
    valor_txt = str(value or "")
    if "NotFoundError" in valor_txt and "removeChild" in valor_txt:
        return default
    dt = safe_datetime_parse(value)
    return dt.strftime(fmt) if dt else default


def sanitize_ui_text(value, default="-"):
    """Evita exibir stack traces frontend como se fossem dados de negócio."""
    txt = str(value or "").strip()
    if not txt:
        return default

    txt_lower = txt.lower()
    if "notfounderror" in txt_lower and "removechild" in txt_lower:
        return "Erro de interface detectado em solicitação antiga (detalhes técnicos ocultados)."
    if "ponto-esa-v5.onrender.com/static/js/index" in txt_lower:
        return "Erro de interface detectado em solicitação antiga (detalhes técnicos ocultados)."
    return txt


def formatar_localizacao_legivel(localizacao_original, latitude=None, longitude=None):
    """Retorna localização amigável (endereço/CEP quando possível) para exibição."""
    if (latitude is None or longitude is None) and localizacao_original:
        try:
            import re
            match = re.search(r'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)', str(localizacao_original))
            if match:
                latitude = float(match.group(1))
                longitude = float(match.group(2))
        except Exception as e:
            logger.debug("Falha ao extrair coordenadas do texto de localização: %s", e)

    if latitude is None or longitude is None:
        return localizacao_original or "GPS não disponível"

    try:
        from geocoding import formatar_localizacao_gestor
        loc = formatar_localizacao_gestor(latitude, longitude, localizacao_original)
        if loc.get("endereco"):
            return loc["endereco"]
    except Exception as e:
        logger.debug("Falha ao formatar localização legível: %s", e)

    if localizacao_original and localizacao_original != "GPS não disponível":
        return localizacao_original
    return f"GPS: {latitude:.6f}, {longitude:.6f}"


def obter_entrada_saida_dia_cursor(cursor, usuario, data_referencia):
    """Retorna (entrada, saida, horas) para um dia com base nos registros existentes."""
    cursor.execute(f"""
        SELECT data_hora, tipo
        FROM registros_ponto
        WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
        ORDER BY data_hora ASC
    """, (usuario, data_referencia))
    rows = cursor.fetchall()

    primeiro_inicio = None
    ultimo_fim = None
    for data_hora, tipo in rows:
        dt = safe_datetime_parse(data_hora)
        if not dt:
            continue
        tipo_norm = normalizar_tipo_ponto(tipo)
        if tipo_norm == "inicio" and primeiro_inicio is None:
            primeiro_inicio = dt
        elif tipo_norm == "fim":
            ultimo_fim = dt

    entrada = primeiro_inicio.strftime("%H:%M") if primeiro_inicio else None
    saida = ultimo_fim.strftime("%H:%M") if ultimo_fim else None
    horas = None
    if primeiro_inicio and ultimo_fim and ultimo_fim > primeiro_inicio:
        horas = round((ultimo_fim - primeiro_inicio).total_seconds() / 3600, 2)
    return entrada, saida, horas


def obter_registros_dia_validacao_cursor(cursor, usuario, data_referencia, ignorar_registro_id=None):
    """Retorna os registros do dia em ordem cronológica para validações de negócio."""
    query = f"""
        SELECT id, data_hora, tipo
        FROM registros_ponto
        WHERE usuario = {SQL_PLACEHOLDER}
          AND DATE(data_hora) = {SQL_PLACEHOLDER}
    """
    params = [usuario, data_referencia]
    if ignorar_registro_id is not None:
        query += f" AND id <> {SQL_PLACEHOLDER}"
        params.append(ignorar_registro_id)
    query += " ORDER BY data_hora ASC"
    cursor.execute(query, tuple(params))

    registros = []
    for registro_id, data_hora, tipo in cursor.fetchall():
        dt = safe_datetime_parse(data_hora)
        if not dt:
            continue
        registros.append({
            "id": registro_id,
            "data_hora": dt,
            "tipo": normalizar_tipo_ponto(tipo),
        })
    return registros


def validar_novo_registro_cursor(cursor, usuario, data_referencia, tipo, data_hora_proposta=None, ignorar_registro_id=None):
    """Valida regras de sequência do ponto para criação/correção de registros."""
    tipo_norm = normalizar_tipo_ponto(tipo)
    registros = obter_registros_dia_validacao_cursor(cursor, usuario, data_referencia, ignorar_registro_id=ignorar_registro_id)
    proposta_dt = safe_datetime_parse(data_hora_proposta) if data_hora_proposta else None

    registros_inicio = [r for r in registros if r["tipo"] == "inicio"]
    registros_fim = [r for r in registros if r["tipo"] == "fim"]
    primeiro_inicio = registros_inicio[0]["data_hora"] if registros_inicio else None
    ultimo_fim = registros_fim[-1]["data_hora"] if registros_fim else None
    primeiro_registro = registros[0] if registros else None

    if not registros:
        if tipo_norm != "inicio":
            return False, "O primeiro registro do dia deve ser 'Início'."
        return True, ""

    if tipo_norm == "inicio":
        if registros_inicio:
            return False, "O registro de 'Início' só pode ser realizado uma vez por dia."
        if ultimo_fim and ignorar_registro_id is None:
            return False, "Não é permitido registrar novo 'Início' após já existir um 'Fim' no dia."
        if ultimo_fim and proposta_dt and proposta_dt >= ultimo_fim:
            return False, "O registro de 'Início' deve ocorrer antes do 'Fim' do expediente."
        if proposta_dt and primeiro_registro and proposta_dt >= primeiro_registro["data_hora"]:
            return False, "O registro de 'Início' precisa ser o primeiro do dia."
        return True, ""

    if not primeiro_inicio:
        return False, "Registre primeiro um 'Início' antes de lançar outros tipos de ponto."

    if tipo_norm == "intermediario":
        if ultimo_fim:
            return False, "Não é permitido registrar 'Intermediário' após o 'Fim' do expediente."
        if proposta_dt and proposta_dt <= primeiro_inicio:
            return False, "O registro 'Intermediário' deve ocorrer após o 'Início'."
        return True, ""

    if tipo_norm == "fim":
        if registros_fim:
            return False, "O registro de 'Fim' só pode ser realizado uma vez por dia."
        if proposta_dt and proposta_dt <= primeiro_inicio:
            return False, "O registro de 'Fim' deve ocorrer após o 'Início'."
        return True, ""

    return False, "Tipo de registro inválido."


def existe_solicitacao_correcao_pendente_cursor(
    cursor,
    usuario,
    registro_id,
    data_hora_original,
    data_hora_nova,
    tipo_solicitacao="ajuste_registro",
    data_referencia=None,
    hora_inicio=None,
    hora_saida=None,
):
    """Verifica se já existe solicitação pendente equivalente para evitar duplicidades."""
    query = f"""
        SELECT id
        FROM solicitacoes_correcao_registro
        WHERE usuario = {SQL_PLACEHOLDER}
          AND COALESCE(registro_id, 0) = {SQL_PLACEHOLDER}
          AND COALESCE(CAST(data_hora_original AS TEXT), '') = {SQL_PLACEHOLDER}
          AND COALESCE(CAST(data_hora_nova AS TEXT), '') = {SQL_PLACEHOLDER}
          AND COALESCE(tipo_solicitacao, 'ajuste_registro') = {SQL_PLACEHOLDER}
          AND status = 'pendente'
    """
    params = [
        usuario,
        int(registro_id or 0),
        str(data_hora_original or ""),
        str(data_hora_nova or ""),
        tipo_solicitacao,
    ]

    if data_referencia is not None:
        query += f" AND COALESCE(CAST(data_referencia AS TEXT), '') = {SQL_PLACEHOLDER}"
        params.append(str(data_referencia))
    if hora_inicio is not None:
        query += f" AND COALESCE(CAST(hora_inicio_solicitada AS TEXT), '') = {SQL_PLACEHOLDER}"
        params.append(str(hora_inicio))
    if hora_saida is not None:
        query += f" AND COALESCE(CAST(hora_saida_solicitada AS TEXT), '') = {SQL_PLACEHOLDER}"
        params.append(str(hora_saida))

    cursor.execute(query, tuple(params))
    row = cursor.fetchone()
    return row[0] if row else None


def registrar_auditoria_alteracao_ponto_cursor(
    cursor,
    registro_id,
    usuario_afetado,
    data_registro,
    entrada_original,
    saida_original,
    entrada_corrigida,
    saida_corrigida,
    tipo_alteracao,
    realizado_por,
    justificativa=None,
    detalhes=None,
):
    cursor.execute(f"""
        INSERT INTO auditoria_alteracoes_ponto
        (registro_id, usuario_afetado, data_registro, entrada_original, saida_original,
         entrada_corrigida, saida_corrigida, tipo_alteracao, realizado_por,
         data_alteracao, justificativa, detalhes)
        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                CURRENT_TIMESTAMP, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
    """, (
        registro_id,
        usuario_afetado,
        data_registro,
        entrada_original,
        saida_original,
        entrada_corrigida,
        saida_corrigida,
        tipo_alteracao,
        realizado_por,
        justificativa or "Sem justificativa informada",
        detalhes,
    ))


# Importar sistemas desenvolvidos

# Configuração da página
st.set_page_config(
    page_title="Ponto ExSA v5.0",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="auto"
)

# Inicializar sistema de Push Notifications (ntfy.sh)
try:
    init_push_system()
except Exception as e:
    logger.debug("Push system não inicializado: %s", e)

# CSS personalizado com novo layout - cacheado como string para melhor performance
@st.cache_data
def get_custom_css():
    """Retorna CSS customizado (cacheado para evitar re-processamento)"""
    return """
<style>
    /* Importar fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e configurações gerais */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #87CEEB 0%, #4682B4 100%);
        min-height: 100vh;
        overflow-x: hidden;
    }

    html, body, [data-testid="stAppViewContainer"] {
        max-width: 100%;
        overflow-x: hidden;
    }

    .main .block-container {
        max-width: 100%;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Container principal de login */
    .login-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        padding: 40px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        max-width: 400px;
        margin: 0 auto;
        margin-top: 5vh;
        text-align: center;
    }
    
    /* Logo e título */
    .logo-container {
        margin-bottom: 30px;
    }
    
    .main-title {
        color: #8B4513;
        font-size: 24px;
        font-weight: 600;
        margin: 20px 0;
        text-shadow: 1px 1px 2px rgba(139, 69, 19, 0.3);
        filter: drop-shadow(0 2px 4px rgba(139, 69, 19, 0.2));
    }
    
    .subtitle {
        color: #666;
        font-size: 14px;
        margin-bottom: 30px;
    }
    
    /* Textos de rodapé */
    .footer-left {
        position: fixed;
        bottom: 20px;
        left: 20px;
        color: #333;
        font-size: 12px;
        font-weight: 500;
        background: rgba(255, 255, 255, 0.8);
        padding: 8px 12px;
        border-radius: 8px;
        backdrop-filter: blur(5px);
    }
    
    .footer-right {
        position: fixed;
        bottom: 20px;
        right: 20px;
        color: #333;
        font-size: 12px;
        font-weight: 500;
        background: rgba(255, 255, 255, 0.8);
        padding: 8px 12px;
        border-radius: 8px;
        backdrop-filter: blur(5px);
    }
                    
    /* Interface principal */
    .main-header {
        background: linear-gradient(135deg, #4682B4, #87CEEB);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .user-welcome {
        font-size: 24px;
        font-weight: 600;
        margin-bottom: 5px;
    }
    
    .user-info {
        font-size: 14px;
        opacity: 0.9;
    }
    
    /* Cards de funcionalidades */
    .feature-card {
        background: white;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border-left: 4px solid #4682B4;
    }
    
    .feature-card h3 {
        color: #4682B4;
        margin-bottom: 15px;
        font-weight: 600;
    }

    [data-testid="stDataFrame"], .stTable {
        max-width: 100%;
        overflow-x: auto;
    }

    pre {
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }
    
    /* Notificações */
    .notification-badge {
        background: #ff4444;
        color: white;
        border-radius: 50%;
        padding: 2px 6px;
        font-size: 12px;
        font-weight: bold;
        margin-left: 5px;
    }
    
    /* Status badges */
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .status-pendente {
        background: #fff3cd;
        color: #856404;
    }
    
    .status-aprovado {
        background: #d4edda;
        color: #155724;
    }
    
    .status-rejeitado {
        background: #f8d7da;
        color: #721c24;
    }
    
    /* Saldo do banco de horas */
    .saldo-positivo {
        color: #28a745;
        font-weight: bold;
    }
    
    .saldo-negativo {
        color: #dc3545;
        font-weight: bold;
    }
    
    .saldo-zero {
        color: #6c757d;
        font-weight: bold;
    }
    
    /* Destaque para discrepâncias */
    .discrepancia-alta {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
    }
    
    /* GPS status */
    .gps-status {
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .gps-success {
        background: #d4edda;
        color: #155724;
    }
    
    .gps-error {
        background: #f8d7da;
        color: #721c24;
    }
    
    /* Ocultar campos de GPS da interface do usuário - esconder containers completos */
    /* Usar seletor de atributo para inputs com placeholders GPS */
    div.stTextInput:has(input[placeholder="GPS Lat"]),
    div.stTextInput:has(input[placeholder="GPS Lng"]),
    div.stTextInput:has(input[placeholder="Latitude GPS"]),
    div.stTextInput:has(input[placeholder="Longitude GPS"]),
    div.stTextInput:has(input[placeholder="GPS Longo"]),
    div.stTextInput:has(input[aria-label="Latitude GPS"]),
    div.stTextInput:has(input[aria-label="Longitude GPS"]),
    div[data-testid="stTextInput"]:has(input[placeholder="GPS Lat"]),
    div[data-testid="stTextInput"]:has(input[placeholder="GPS Lng"]),
    div[data-testid="stTextInput"]:has(input[placeholder="Latitude GPS"]),
    div[data-testid="stTextInput"]:has(input[placeholder="Longitude GPS"]),
    div[data-testid="stTextInput"]:has(input[placeholder="GPS Longo"]),
    div[data-testid="stTextInput"]:has(input[aria-label="Latitude GPS"]),
    div[data-testid="stTextInput"]:has(input[aria-label="Longitude GPS"]) {
        display: none !important;
        height: 0 !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Fallback para navegadores que não suportam :has() */
    input[placeholder="GPS Lat"],
    input[placeholder="GPS Lng"],
    input[placeholder="Latitude GPS"],
    input[placeholder="Longitude GPS"],
    input[placeholder="GPS Longo"],
    input[aria-label="Latitude GPS"],
    input[aria-label="Longitude GPS"] {
        position: absolute !important;
        left: -9999px !important;
        opacity: 0 !important;
        pointer-events: none !important;
        height: 0 !important;
        width: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
    }

    .gps-hidden-field,
    .gps-hidden-field * {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        overflow: hidden !important;
    }

    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.6rem;
            padding-right: 0.6rem;
            padding-top: 0.8rem;
        }

        .main-header {
            padding: 14px;
            border-radius: 10px;
            margin-bottom: 12px;
        }

        .user-welcome {
            font-size: 20px;
            line-height: 1.2;
        }

        .user-info {
            font-size: 12px;
        }

        .feature-card {
            padding: 14px;
            border-radius: 12px;
            margin-bottom: 12px;
        }

        .feature-card h3 {
            font-size: 1.1rem;
            margin-bottom: 10px;
        }

        [data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
            gap: 0.5rem !important;
        }

        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 0 !important;
        }

        .footer-left,
        .footer-right {
            position: static;
            display: block;
            margin: 8px 0 0 0;
            width: fit-content;
            max-width: 100%;
            font-size: 11px;
        }
    }
</style>
<script>
// Fallback seguro: esconder apenas o input, sem alterar containers do React/Streamlit.
function hideGpsInputsSafely() {
    document.querySelectorAll('input[placeholder="GPS Lat"], input[placeholder="GPS Lng"], input[placeholder="Latitude GPS"], input[placeholder="Longitude GPS"], input[placeholder="GPS Longo"], input[aria-label="Latitude GPS"], input[aria-label="Longitude GPS"]').forEach(function(input) {
        input.style.position = 'absolute';
        input.style.left = '-9999px';
        input.style.opacity = '0';
        input.style.pointerEvents = 'none';
        input.style.height = '0';
        input.style.width = '0';

        // Esconder também o container visual sem removê-lo do DOM.
        var wrap = input.closest('div[data-testid="stTextInput"]');
        if (wrap) {
            wrap.classList.add('gps-hidden-field');
        }
    });
}
hideGpsInputsSafely();
setTimeout(hideGpsInputsSafely, 300);
setTimeout(hideGpsInputsSafely, 900);
setTimeout(hideGpsInputsSafely, 1600);
</script>
"""

# Aplicar CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# Obter chave VAPID do ambiente para injetar no JavaScript
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')

# Scripts JS separados para não bloquear renderização
st.markdown(f"""

<script>
// Configurar VAPID para Push Notifications
window.VAPID_CONFIG = {{
    publicKey: '{VAPID_PUBLIC_KEY}',
    configured: {str(bool(VAPID_PUBLIC_KEY)).lower()}
}};

function updateClock() {{
    const now = new Date();
    const dateStr = now.toLocaleDateString('pt-BR');
    const timeStr = now.toLocaleTimeString('pt-BR', {{hour: '2-digit', minute: '2-digit'}});
    const elements = document.querySelectorAll('.user-info');
    elements.forEach(el => {{
        if (el.textContent.includes('•')) {{
            const parts = el.textContent.split(' • ');
            if (parts.length === 2) {{
                el.textContent = parts[0] + ' • ' + dateStr + ' ' + timeStr;
            }}
        }}
    }});
}}
// Atualizar a cada minuto
setInterval(updateClock, 60000);
// Atualizar imediatamente
updateClock();
</script>

<!-- Push Notifications Script - Versão Simplificada para Streamlit -->
<script src="/app/static/push-simple.js"></script>
""", unsafe_allow_html=True)

# JavaScript para captura de GPS
GPS_SCRIPT = """
<script>
function getLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                const accuracy = position.coords.accuracy;
                
                // Armazenar no sessionStorage
                sessionStorage.setItem('gps_lat', lat);
                sessionStorage.setItem('gps_lng', lng);
                sessionStorage.setItem('gps_accuracy', accuracy);
                sessionStorage.setItem('gps_timestamp', Date.now());
                
                // Preencher campos ocultos do Streamlit
                setTimeout(function() {
                    // Encontrar e preencher campos de latitude e longitude
                    const inputs = document.querySelectorAll('input[type="text"]');
                    inputs.forEach(function(input) {
                        const label = input.closest('.stTextInput');
                        if (label) {
                            const labelText = label.querySelector('label');
                            if (labelText) {
                                if (labelText.innerText.includes('GPS_LAT_HIDDEN')) {
                                    input.value = lat.toString();
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    input.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                                if (labelText.innerText.includes('GPS_LNG_HIDDEN')) {
                                    input.value = lng.toString();
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    input.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                            }
                        }
                    });
                }, 1000);
                
                // Atualizar display
                const gpsDiv = document.getElementById('gps-status');
                if (gpsDiv) {
                    gpsDiv.innerHTML = `
                        <div class="gps-status gps-success">
                            📍 GPS: ${lat.toFixed(6)}, ${lng.toFixed(6)} (±${Math.round(accuracy)}m)
                        </div>
                    `;
                }
            },
            function(error) {
                console.error('Erro GPS:', error);
                const gpsDiv = document.getElementById('gps-status');
                if (gpsDiv) {
                    gpsDiv.innerHTML = `
                        <div class="gps-status gps-error">
                            ⚠️ GPS não disponível: ${error.message}
                        </div>
                    `;
                }
                // Marcar que GPS falhou
                sessionStorage.setItem('gps_error', error.message);
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 60000
            }
        );
    } else {
        const gpsDiv = document.getElementById('gps-status');
        if (gpsDiv) {
            gpsDiv.innerHTML = `
                <div class="gps-status gps-error">
                    ❌ GPS não suportado pelo navegador
                </div>
            `;
        }
    }
}

// Executar quando a página carregar
document.addEventListener('DOMContentLoaded', getLocation);
// Também executar imediatamente
getLocation();
</script>
"""

# Inicializar sistemas


@st.cache_resource
def init_systems():
    """Inicializa os sistemas"""
    atestado_system = AtestadoHorasSystem()
    upload_system = UploadSystem()
    horas_extras_system = HorasExtrasSystem()
    banco_horas_system = BancoHorasSystem()
    calculo_horas_system = CalculoHorasSystem()
    return atestado_system, upload_system, horas_extras_system, banco_horas_system, calculo_horas_system


@st.cache_data(ttl=30)
def _get_login_row_cached(usuario: str):
    """Busca credenciais do usuário com cache curto para reduzir pressão no banco."""
    if not usuario:
        return None

    if REFACTORING_ENABLED:
        return execute_query(
            f"SELECT senha, tipo, nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}",
            (usuario,),
            fetch_one=True,
        )

    conn_local = get_connection()
    try:
        cursor = conn_local.cursor()
        cursor.execute(
            f"SELECT senha, tipo, nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}",
            (usuario,),
        )
        return cursor.fetchone()
    finally:
        _return_conn(conn_local)

# Funções de banco de dados


def verificar_login(usuario, senha):
    """Verifica credenciais de login (suporta bcrypt e SHA256 legado com migração automática)"""
    usuario = (usuario or "").strip()
    senha = senha or ""
    if not usuario or not senha:
        return None

    try:
        from password_utils import verify_and_upgrade
        _has_password_utils = True
    except Exception as _imp_err:
        logger.warning("password_utils indisponível (%s), usando SHA256 puro", _imp_err)
        _has_password_utils = False

    def _check_password(plain, hashed, user):
        """Verifica senha via password_utils."""
        if not hashed:
            return False
        if _has_password_utils:
            return verify_and_upgrade(plain, hashed, user)
        return False

    def _exec_login_once():
        row_local = _get_login_row_cached(usuario)
        if row_local and _check_password(senha, row_local[0], usuario):
            log_security_event("LOGIN", usuario=usuario, severity="INFO")
            return (row_local[1], row_local[2])
        return None

    try:
        return _exec_login_once()
    except Exception as login_err:
        erro_txt = str(login_err).lower()
        transient_db_error = (
            "ssl connection has been closed unexpectedly" in erro_txt
            or "server closed the connection unexpectedly" in erro_txt
            or "terminating connection" in erro_txt
        )
        if transient_db_error:
            logger.warning("Falha transitória no login de %s; tentando reconexão", usuario)
            try:
                return _exec_login_once()
            except Exception as retry_err:
                logger.error("Erro ao verificar login para %s após retry: %s", usuario, retry_err, exc_info=True)
                return None

        logger.error("Erro ao verificar login para %s: %s", usuario, login_err, exc_info=True)
        return None


@st.cache_data(ttl=300)  # Cache de 5 minutos para projetos
def obter_projetos_ativos():
    """Obtém lista de projetos ativos (com cache)"""
    if REFACTORING_ENABLED:
        results = execute_query(
            "SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome"
        )
        return [row[0] for row in results] if results else []
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome")
            projetos = [row[0] for row in cursor.fetchall()]
            return projetos
        finally:
            _return_conn(conn)


def registrar_ponto(usuario, tipo, modalidade, projeto, atividade, data_registro=None, hora_registro=None, latitude=None, longitude=None, conn_external=None):
    """Registra ponto do usuário com GPS real.
    Se conn_external for fornecido, usa a conexão existente (transação do caller)."""
    # Se não especificada, usar data/hora atual no fuso horário de Brasília
    if data_registro and hora_registro:
        data_obj = datetime.strptime(data_registro, "%Y-%m-%d")
        hora_obj = datetime.strptime(hora_registro, "%H:%M:%S").time() if isinstance(hora_registro, str) else hora_registro
        data_hora_registro = datetime.combine(data_obj, hora_obj)
    elif data_registro:
        agora = get_datetime_br()
        data_obj = datetime.strptime(data_registro, "%Y-%m-%d")
        # Pegar hora/minuto/segundo de Brasília, mas salvar sem timezone
        data_hora_registro = data_obj.replace(
            hour=agora.hour, minute=agora.minute, second=agora.second)
    else:
        # Usar horário atual de Brasília, mas remover timezone antes de salvar
        agora_br = get_datetime_br()
        data_hora_registro = agora_br.replace(tzinfo=None)

    # Formatar localização
    if latitude is not None and longitude is not None:
        localizacao = formatar_localizacao_legivel(None, latitude, longitude)
    else:
        localizacao = "GPS não disponível"

    # Usar placeholder correto baseado no tipo de banco
    placeholders = ', '.join([SQL_PLACEHOLDER] * 9)

    tipo_norm = normalizar_tipo_ponto(tipo)
    
    owns_conn = conn_external is None
    conn = conn_external if conn_external else get_connection()
    try:
        cursor = conn.cursor()
        data_ref = data_hora_registro.strftime("%Y-%m-%d")

        valido_fluxo, mensagem_fluxo = validar_novo_registro_cursor(
            cursor,
            usuario,
            data_ref,
            tipo_norm,
            data_hora_proposta=data_hora_registro,
        )
        if not valido_fluxo:
            raise ValueError(mensagem_fluxo)

        entrada_antes, saida_antes, _ = obter_entrada_saida_dia_cursor(cursor, usuario, data_ref)

        cursor.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
            VALUES ({placeholders})
        ''', (usuario, data_hora_registro, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude))

        entrada_depois, saida_depois, _ = obter_entrada_saida_dia_cursor(cursor, usuario, data_ref)
        registrar_auditoria_alteracao_ponto_cursor(
            cursor,
            registro_id=None,
            usuario_afetado=usuario,
            data_registro=data_ref,
            entrada_original=entrada_antes,
            saida_original=saida_antes,
            entrada_corrigida=entrada_depois,
            saida_corrigida=saida_depois,
            tipo_alteracao="registro_ponto_criado",
            realizado_por=usuario,
            justificativa="Registro realizado pelo colaborador",
            detalhes=f"tipo={tipo}; modalidade={modalidade}; projeto={projeto}",
        )

        if owns_conn:
            conn.commit()
        return data_hora_registro
    except Exception:
        if owns_conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if owns_conn:
            _return_conn(conn)


def obter_registros_usuario(usuario, data_inicio=None, data_fim=None):
    """Obtém registros de ponto do usuário"""
    query = f"SELECT * FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER}"
    params = [usuario]

    if data_inicio and data_fim:
        query += f" AND DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}"
        params.extend([data_inicio, data_fim])

    query += " ORDER BY data_hora DESC"

    if REFACTORING_ENABLED:
        return execute_query(query, tuple(params))
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            registros = cursor.fetchall()
            return registros
        finally:
            _return_conn(conn)


def obter_usuarios_para_aprovacao():
    """Obtém lista de usuários que podem aprovar horas extras"""
    if REFACTORING_ENABLED:
        usuarios = execute_query(
            "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo"
        )
        return [{"usuario": u[0], "nome": u[1] or u[0]} for u in usuarios] if usuarios else []
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo")
            usuarios = cursor.fetchall()
            return [{"usuario": u[0], "nome": u[1] or u[0]} for u in usuarios]
        finally:
            _return_conn(conn)


@st.cache_data(ttl=120)  # Cache de 2 minutos para usuários
def obter_usuarios_ativos():
    """Obtém lista de usuários ativos (retorna dicionários com 'usuario' e 'nome_completo')."""
    if REFACTORING_ENABLED:
        rows = execute_query(
            "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo"
        )
        return [{"usuario": r[0], "nome_completo": r[1] or r[0]} for r in rows] if rows else []
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo")
            rows = cursor.fetchall()
            return [{"usuario": r[0], "nome_completo": r[1] or r[0]} for r in rows]
        finally:
            _return_conn(conn)


@st.cache_data(ttl=20)
def obter_badges_gestor_cached(usuario: str):
    """Obtém contadores de badges do gestor em uma única consulta com cache curto."""
    if REFACTORING_ENABLED:
        row = execute_query(
            f"""
            SELECT
                (SELECT COUNT(*) FROM solicitacoes_horas_extras
                 WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente') AS he_aprovar,
                (SELECT COUNT(*) FROM atestado_horas
                 WHERE status = 'pendente') AS atestados_pendentes,
                (SELECT COUNT(*) FROM (
                    SELECT DISTINCT
                        COALESCE(CAST(registro_id AS TEXT), '0') || '|' ||
                        COALESCE(usuario, '') || '|' ||
                        COALESCE(CAST(data_hora_original AS TEXT), '') || '|' ||
                        COALESCE(CAST(data_hora_nova AS TEXT), '')
                    FROM solicitacoes_correcao_registro
                    WHERE status = 'pendente'
                ) x) AS correcoes_pendentes
            """,
            (usuario,),
            fetch_one=True,
        )
        if not row:
            return 0, 0, 0
        return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT
                (SELECT COUNT(*) FROM solicitacoes_horas_extras
                 WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente') AS he_aprovar,
                (SELECT COUNT(*) FROM atestado_horas
                 WHERE status = 'pendente') AS atestados_pendentes,
                (SELECT COUNT(*) FROM (
                    SELECT DISTINCT
                        COALESCE(CAST(registro_id AS TEXT), '0') || '|' ||
                        COALESCE(usuario, '') || '|' ||
                        COALESCE(CAST(data_hora_original AS TEXT), '') || '|' ||
                        COALESCE(CAST(data_hora_nova AS TEXT), '')
                    FROM solicitacoes_correcao_registro
                    WHERE status = 'pendente'
                ) x) AS correcoes_pendentes
            """,
            (usuario,),
        )
        row = cursor.fetchone()
        if not row:
            return 0, 0, 0
        return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)
    finally:
        _return_conn(conn)


@st.cache_data(ttl=15)
def obter_solicitacoes_pendentes_count_cached(usuario: str) -> int:
    """Conta solicitações de HE aguardando aprovação com cache curto."""
    if REFACTORING_ENABLED:
        result = execute_query(
            f"SELECT COUNT(*) FROM horas_extras_ativas WHERE aprovador = {SQL_PLACEHOLDER} AND status = 'aguardando_aprovacao'",
            (usuario,),
            fetch_one=True,
        )
        return int(result[0]) if result else 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT COUNT(*) FROM horas_extras_ativas
            WHERE aprovador = {SQL_PLACEHOLDER}
              AND status = 'aguardando_aprovacao'
            """,
            (usuario,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        _return_conn(conn)


@st.cache_data(ttl=20)
def obter_mensagens_nao_lidas_count_cached(usuario: str) -> int:
    """Conta mensagens diretas não lidas para o usuário com cache curto."""
    if not usuario:
        return 0

    if REFACTORING_ENABLED:
        result = execute_query(
            f"SELECT COUNT(*) FROM mensagens_diretas WHERE destinatario = {SQL_PLACEHOLDER} AND lida = FALSE",
            (usuario,),
            fetch_one=True,
        )
        return int(result[0]) if result else 0

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT COUNT(*) FROM mensagens_diretas WHERE destinatario = {SQL_PLACEHOLDER} AND lida = FALSE",
            (usuario,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        _return_conn(conn)

# Interface de login


def tela_login():
    """Exibe tela de login"""
    # Criar diretório static se não existir
    os.makedirs("static", exist_ok=True)

  # Copiar imagem de fundo se existir
    if os.path.exists("/home/ubuntu/upload/Exsafundo.jpg") and not os.path.exists("static/Exsafundo.jpg"):
        import shutil
        shutil.copy("/home/ubuntu/upload/Exsafundo.jpg",
                    "static/Exsafundo.jpg")

    # Imagem de fundo
    if os.path.exists("static/Exsafundo.jpg"):
        with open("static/Exsafundo.jpg", "rb") as f:
            img_data = base64.b64encode(f.read()).decode()

        st.markdown(f"""
        <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{img_data}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
            }}
        </style>
        """, unsafe_allow_html=True)

   # Container centralizado
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="logo-container">
                <div style="width: 80px; height: 80px; background: #4682B4; border-radius: 50%; margin: 0 auto 20px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-size: 24px; font-weight: bold;">ExSA</span>
                </div>
            </div>
            <h1 class="main-title">Ponto ExSA - Sistema de Controle de Ponto</h1>
            <p class="subtitle">Expressão Socioambiental Pesquisa e Projetos</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            usuario = st.text_input(
                "👤 Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("🔒 Senha", type="password",
                                  placeholder="Digite sua senha")

            submitted = st.form_submit_button(
                "ENTRAR", width="stretch")

            if submitted:
                if usuario and senha:
                    resultado = verificar_login(usuario, senha)
                    if resultado:
                        st.session_state.usuario = usuario
                        st.session_state.tipo_usuario = resultado[0]
                        st.session_state.nome_completo = resultado[1]
                        st.session_state.logged_in = True
                        log_user_action(usuario, "login", f"tipo={resultado[0]}")
                        st.success("✅ Login realizado com sucesso!")
                        st.rerun()
                    else:
                        logger.warning("Tentativa de login falhou para usuario=%s", usuario)
                        st.error("❌ Usuário ou senha incorretos")
                else:
                    st.warning("⚠️ Preencha todos os campos")


def validar_limites_horas_extras(usuario):
    """
    Valida se o usuário pode fazer hora extra segundo limites da CLT
    - Máximo 2h extras por dia
    - Máximo 10h extras por semana
    """
    from datetime import datetime, timedelta
    
    try:
        agora = get_datetime_br()
        hoje = agora.date()
        
        # Início da semana (segunda-feira)
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        
        horas_hoje_ativas = 0
        horas_hoje_historico = 0
        horas_semana_ativas = 0
        horas_semana_historico = 0
        
        if REFACTORING_ENABLED:
            try:
                # Horas extras hoje (ativas)
                query_hoje_ativas = f"""
                    SELECT COALESCE(SUM(tempo_decorrido_minutos), 0) / 60.0
                    FROM horas_extras_ativas
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND DATE(data_inicio) = {SQL_PLACEHOLDER}
                    AND status IN ('encerrada', 'em_execucao')
                """
                result = execute_query(query_hoje_ativas, (usuario, hoje), fetch_one=True)
                horas_hoje_ativas = result[0] or 0 if result else 0
                
                # Horas extras hoje (histórico)
                query_hoje_hist = f"""
                    SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (
                        CAST(hora_fim AS TIME) - CAST(hora_inicio AS TIME)
                    )) / 3600), 0)
                    FROM solicitacoes_horas_extras
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND data = {SQL_PLACEHOLDER}
                    AND status = 'aprovado'
                """
                result = execute_query(query_hoje_hist, (usuario, hoje), fetch_one=True)
                horas_hoje_historico = result[0] or 0 if result else 0
                
                # Horas extras esta semana (ativas)
                query_semana_ativas = f"""
                    SELECT COALESCE(SUM(tempo_decorrido_minutos), 0) / 60.0
                    FROM horas_extras_ativas
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND DATE(data_inicio) >= {SQL_PLACEHOLDER}
                    AND status IN ('encerrada', 'em_execucao')
                """
                result = execute_query(query_semana_ativas, (usuario, inicio_semana), fetch_one=True)
                horas_semana_ativas = result[0] or 0 if result else 0
                
                # Horas extras esta semana (histórico)
                query_semana_hist = f"""
                    SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (
                        CAST(hora_fim AS TIME) - CAST(hora_inicio AS TIME)
                    )) / 3600), 0)
                    FROM solicitacoes_horas_extras
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND data >= {SQL_PLACEHOLDER}
                    AND status = 'aprovado'
                """
                result = execute_query(query_semana_hist, (usuario, inicio_semana), fetch_one=True)
                horas_semana_historico = result[0] or 0 if result else 0
            except Exception as e:
                log_error("Erro ao buscar limites de horas extras", e, {"usuario": usuario})
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()

                # Horas extras hoje (ativas)
                cursor.execute(f"""
                    SELECT COALESCE(SUM(tempo_decorrido_minutos), 0) / 60.0
                    FROM horas_extras_ativas
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND DATE(data_inicio) = {SQL_PLACEHOLDER}
                    AND status IN ('encerrada', 'em_execucao')
                """, (usuario, hoje))

                horas_hoje_ativas = cursor.fetchone()[0] or 0

                cursor.execute(f"""
                    SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (
                        CAST(hora_fim AS TIME) - CAST(hora_inicio AS TIME)
                    )) / 3600), 0)
                    FROM solicitacoes_horas_extras
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND data = {SQL_PLACEHOLDER}
                    AND status = 'aprovado'
                """, (usuario, hoje))

                horas_hoje_historico = cursor.fetchone()[0] or 0

                # Horas extras esta semana
                cursor.execute(f"""
                    SELECT COALESCE(SUM(tempo_decorrido_minutos), 0) / 60.0
                    FROM horas_extras_ativas
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND DATE(data_inicio) >= {SQL_PLACEHOLDER}
                    AND status IN ('encerrada', 'em_execucao')
                """, (usuario, inicio_semana))

                horas_semana_ativas = cursor.fetchone()[0] or 0

                cursor.execute(f"""
                    SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (
                        CAST(hora_fim AS TIME) - CAST(hora_inicio AS TIME)
                    )) / 3600), 0)
                    FROM solicitacoes_horas_extras
                    WHERE usuario = {SQL_PLACEHOLDER}
                    AND data >= {SQL_PLACEHOLDER}
                    AND status = 'aprovado'
                """, (usuario, inicio_semana))

                horas_semana_historico = cursor.fetchone()[0] or 0
            finally:
                _return_conn(conn)
        
        horas_hoje_total = horas_hoje_ativas + horas_hoje_historico
        horas_semana_total = horas_semana_ativas + horas_semana_historico
        
        # Verificar limites CLT
        LIMITE_DIA = 2.0  # 2 horas por dia
        LIMITE_SEMANA = 10.0  # 10 horas por semana
        
        pode_fazer = True
        mensagem = ""
        
        if horas_hoje_total >= LIMITE_DIA:
            pode_fazer = False
            mensagem = f"Limite diário de horas extras atingido ({horas_hoje_total:.1f}h de {LIMITE_DIA}h)"
        elif horas_semana_total >= LIMITE_SEMANA:
            pode_fazer = False
            mensagem = f"Limite semanal de horas extras atingido ({horas_semana_total:.1f}h de {LIMITE_SEMANA}h)"
        
        return {
            'pode_fazer_hora_extra': pode_fazer,
            'mensagem': mensagem,
            'horas_hoje': horas_hoje_total,
            'horas_semana': horas_semana_total,
            'limite_dia': LIMITE_DIA,
            'limite_semana': LIMITE_SEMANA
        }
        
    except Exception as e:
        logger.error(f"Erro ao validar limites de horas extras: {str(e)}")
        # Em caso de erro, permitir (não bloquear por erro de sistema)
        return {
            'pode_fazer_hora_extra': True,
            'mensagem': '',
            'horas_hoje': 0,
            'horas_semana': 0,
            'limite_dia': 2.0,
            'limite_semana': 10.0
        }


def iniciar_hora_extra_interface():
    """Interface para iniciar hora extra com seleção de aprovador e justificativa"""
    from datetime import datetime
    
    st.markdown("""
    <div class="feature-card">
        <h3>🕐 Iniciar Hora Extra</h3>
        <p>Solicite autorização para trabalhar além do horário previsto</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Buscar gestores disponíveis para aprovação
    gestores = obter_usuarios_para_aprovacao()
    
    if not gestores:
        st.error("❌ Nenhum gestor disponível para aprovar hora extra")
        if st.button("⬅️ Voltar"):
            st.session_state.solicitar_horas_extras = False
            st.rerun()
        return
    
    # Mostrar informação do horário de saída previsto
    horario_previsto = st.session_state.get('horario_saida_previsto', 'não definido')
    st.info(f"📅 Seu horário de saída previsto para hoje: **{horario_previsto}**")
    
    with st.form("form_iniciar_hora_extra"):
        st.markdown("### 👤 Selecione o Gestor para Aprovação")
        
        aprovador = st.selectbox(
            "Gestor Responsável:",
            options=[g['usuario'] for g in gestores],
            format_func=lambda x: next(g['nome_completo'] for g in gestores if g['usuario'] == x)
        )
        
        st.markdown("### 📝 Justificativa da Hora Extra")
        justificativa = st.text_area(
            "Por que você precisa fazer hora extra?",
            placeholder="Ex: Finalizar relatório urgente solicitado pela diretoria para entrega amanhã...",
            height=120,
            help="Seja específico sobre o motivo e a urgência da hora extra"
        )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button(
                "✅ Iniciar Hora Extra", 
                width="stretch", 
                type="primary"
            )
        with col2:
            cancelar = st.form_submit_button(
                "❌ Cancelar", 
                width="stretch"
            )
        
        if cancelar:
            st.session_state.solicitar_horas_extras = False
            st.rerun()
        
        if submitted:
            if not justificativa.strip():
                st.error("❌ A justificativa é obrigatória!")
            else:
                # Validar limites CLT de horas extras
                validacao = validar_limites_horas_extras(st.session_state.usuario)
                
                if not validacao['pode_fazer_hora_extra']:
                    st.error(f"❌ {validacao['mensagem']}")
                    st.warning("⚠️ **Limite Legal Atingido:** A CLT estabelece limites de horas extras para proteção do trabalhador.")
                    
                    with st.expander("📋 Ver detalhes dos limites"):
                        st.write(f"**Horas extras hoje:** {validacao['horas_hoje']:.1f}h de 2h permitidas")
                        st.write(f"**Horas extras esta semana:** {validacao['horas_semana']:.1f}h de 10h permitidas")
                        st.markdown("""
                        **Limites CLT:**
                        - Máximo de 2 horas extras por dia
                        - Máximo de 10 horas extras por semana
                        - Descanso mínimo entre jornadas: 11 horas
                        """)
                else:
                    # Mostrar aviso se estiver próximo do limite
                    if validacao['horas_hoje'] >= 1.5:
                        st.warning(f"⚠️ Você já fez {validacao['horas_hoje']:.1f}h extras hoje. Limite: 2h")
                    if validacao['horas_semana'] >= 8:
                        st.warning(f"⚠️ Você já fez {validacao['horas_semana']:.1f}h extras esta semana. Limite: 10h")
                    
                    # Registrar hora extra ativa
                    if REFACTORING_ENABLED:
                        try:
                            agora = get_datetime_br()
                            agora_sem_tz = agora.replace(tzinfo=None)
                            
                            insert_query = f"""
                                INSERT INTO horas_extras_ativas
                                (usuario, aprovador, justificativa, data_inicio, hora_inicio, status)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aguardando_aprovacao')
                            """
                            hora_extra_id = execute_update(insert_query, (
                                st.session_state.usuario,
                                aprovador,
                                justificativa,
                                agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S'),
                                agora_sem_tz.strftime('%H:%M')
                            ), return_id=True)
                            
                            # Criar notificação para o gestor
                            try:
                                from notifications import NotificationManager
                                notif_manager = NotificationManager()
                                notif_manager.criar_notificacao(
                                    usuario_destino=aprovador,
                                    tipo='aprovacao_hora_extra',
                                    titulo=f"🕐 Solicitação de Hora Extra - {st.session_state.nome_completo}",
                                    mensagem=f"Justificativa: {justificativa}",
                                    dados_extras={'hora_extra_id': hora_extra_id}
                                )
                            except Exception as e:
                                # Não bloquear se notificação falhar
                                print(f"Erro ao criar notificação: {e}")
                            
                            log_security_event("HOUR_EXTRA_REQUESTED", usuario=st.session_state.usuario, context={"he_id": hora_extra_id, "aprovador": aprovador})
                            st.session_state.hora_extra_ativa_id = hora_extra_id
                            st.session_state.solicitar_horas_extras = False
                            
                            st.success("✅ Solicitação de hora extra enviada com sucesso!")
                            st.info(f"⏳ Aguardando aprovação do gestor **{next(g['nome_completo'] for g in gestores if g['usuario'] == aprovador)}**")
                            st.balloons()
                            
                            if st.button("🔙 Voltar para o Menu Principal"):
                                st.rerun()
                        
                        except Exception as e:
                            log_error("Erro ao registrar hora extra", e, {"usuario": st.session_state.usuario, "aprovador": aprovador})
                            st.error(f"❌ Erro ao registrar hora extra: {e}")
                    else:
                        # Fallback original
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        try:
                            agora = get_datetime_br()
                            agora_sem_tz = agora.replace(tzinfo=None)
                            
                            cursor.execute(f"""
                                INSERT INTO horas_extras_ativas
                                (usuario, aprovador, justificativa, data_inicio, hora_inicio, status)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aguardando_aprovacao')
                                RETURNING id
                            """, (
                                st.session_state.usuario,
                                aprovador,
                                justificativa,
                                agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S'),
                                agora_sem_tz.strftime('%H:%M')
                            ))
                            
                            # Obter ID da hora extra criada
                            hora_extra_id = cursor.fetchone()[0]
                            
                            conn.commit()
                            
                            # Criar notificação para o gestor
                            try:
                                from notifications import NotificationManager
                                notif_manager = NotificationManager()
                                notif_manager.criar_notificacao(
                                    usuario_destino=aprovador,
                                    tipo='aprovacao_hora_extra',
                                    titulo=f"🕐 Solicitação de Hora Extra - {st.session_state.nome_completo}",
                                    mensagem=f"Justificativa: {justificativa}",
                                    dados_extras={'hora_extra_id': hora_extra_id}
                                )
                            except Exception as e:
                                # Não bloquear se notificação falhar
                                print(f"Erro ao criar notificação: {e}")
                            
                            st.session_state.hora_extra_ativa_id = hora_extra_id
                            st.session_state.solicitar_horas_extras = False
                            
                            st.success("✅ Solicitação de hora extra enviada com sucesso!")
                            st.info(f"⏳ Aguardando aprovação do gestor **{next(g['nome_completo'] for g in gestores if g['usuario'] == aprovador)}**")
                            st.balloons()
                            
                            if st.button("🔙 Voltar para o Menu Principal"):
                                st.rerun()
                        
                        except Exception as e:
                            st.error(f"❌ Erro ao registrar hora extra: {e}")
                        finally:
                            _return_conn(conn)


def exibir_hora_extra_em_andamento():
    """Exibe contador de hora extra em andamento com opção de encerrar"""
    from datetime import datetime
    
    # Verificar se tem hora extra ativa
    if REFACTORING_ENABLED:
        try:
            # Verificar se tabela existe (compatibilidade com bancos antigos)
            check_query = f"""
                SELECT id, aprovador, justificativa, data_inicio, status
                FROM horas_extras_ativas
                WHERE usuario = {SQL_PLACEHOLDER} AND status IN ('aguardando_aprovacao', 'em_execucao')
                ORDER BY data_inicio DESC
                LIMIT 1
            """
            try:
                hora_extra = execute_query(check_query, (st.session_state.usuario,), fetch_one=True)
            except Exception as e:
                # Tabela não existe ou erro de acesso - retornar silenciosamente
                if 'does not exist' in str(e) or 'no such table' in str(e):
                    return
                raise e
            
            if not hora_extra:
                return
            
            he_id, aprovador, justificativa, data_inicio, status = hora_extra
            
            # Calcular tempo decorrido
            from calculo_horas_system import safe_datetime_parse
            inicio = safe_datetime_parse(data_inicio)
            agora = agora_br_naive()
            tempo_decorrido = agora - inicio
            
            horas = int(tempo_decorrido.total_seconds() // 3600)
            minutos = int((tempo_decorrido.total_seconds() % 3600) // 60)
            
            if status == 'aguardando_aprovacao':
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 10px 0;
                    color: white;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">
                    <h3 style="margin: 0; color: white;">⏳ AGUARDANDO APROVAÇÃO DE HORA EXTRA</h3>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>Gestor:</strong> {aprovador}<br>
                        <strong>Iniciado em:</strong> {inicio.strftime('%H:%M')}<br>
                        <strong>Tempo decorrido:</strong> {horas}h {minutos}min<br>
                        <strong>Justificativa:</strong> {justificativa[:100]}{'...' if len(justificativa) > 100 else ''}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            elif status == 'em_execucao':
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 10px 0;
                    color: white;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">
                    <h3 style="margin: 0; color: white;">⏱️ HORA EXTRA EM ANDAMENTO</h3>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>Aprovada por:</strong> {aprovador}<br>
                        <strong>Iniciado em:</strong> {inicio.strftime('%H:%M')}<br>
                        <strong>⏱️ Tempo decorrido:</strong> <span style="font-size: 24px; font-weight: bold;">{horas}h {minutos}min</span>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🛑 Encerrar Hora Extra", type="primary", width="stretch", key="btn_encerrar_he"):
                        # Encerrar hora extra
                        try:
                            agora = get_datetime_br()
                            agora_sem_tz = agora.replace(tzinfo=None)
                            tempo_total_minutos = int(tempo_decorrido.total_seconds() / 60)
                            
                            update_query = f"""
                                UPDATE horas_extras_ativas
                                SET status = 'encerrada',
                                    data_fim = {SQL_PLACEHOLDER},
                                    hora_fim = {SQL_PLACEHOLDER},
                                    tempo_decorrido_minutos = {SQL_PLACEHOLDER}
                                WHERE id = {SQL_PLACEHOLDER}
                            """
                            execute_update(update_query, (
                                agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S'),
                                agora_sem_tz.strftime('%H:%M'),
                                tempo_total_minutos,
                                he_id
                            ))
                            
                            # Registrar na tabela de solicitações de horas extras
                            insert_query = f"""
                                INSERT INTO solicitacoes_horas_extras
                                (usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado, status, aprovado_por, data_aprovacao)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aprovada', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            """
                            execute_update(insert_query, (
                                st.session_state.usuario,
                                inicio.strftime('%Y-%m-%d'),
                                inicio.strftime('%H:%M'),
                                agora_sem_tz.strftime('%H:%M'),
                                justificativa,
                                aprovador,
                                aprovador,
                                agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S')
                            ))
                            
                            log_security_event("HOUR_EXTRA_ENDED", usuario=st.session_state.usuario, context={"he_id": he_id, "tempo_minutos": tempo_total_minutos})
                            st.success(f"✅ Hora extra encerrada! Total trabalhado: **{horas}h {minutos}min**")
                            st.balloons()
                            
                            # Aguardar um pouco para mostrar a mensagem
                            import time
                            time.sleep(2)
                            st.rerun()
                            
                        except Exception as e:
                            log_error("Erro ao encerrar hora extra", e, {"he_id": he_id, "usuario": st.session_state.usuario})
                            st.error(f"❌ Erro ao encerrar hora extra: {e}")
                
                with col2:
                    st.info("💡 Clique em 'Encerrar' quando finalizar o trabalho para registrar o total de horas extras")
        
        except Exception as e:
            logger.error(f"Erro em exibir_hora_extra_em_andamento: {str(e)}")
    else:
        # Fallback original
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Verificar se tabela existe (compatibilidade com bancos antigos)
            try:
                cursor.execute(f"""
                    SELECT id, aprovador, justificativa, data_inicio, status
                    FROM horas_extras_ativas
                    WHERE usuario = {SQL_PLACEHOLDER} AND status IN ('aguardando_aprovacao', 'em_execucao')
                    ORDER BY data_inicio DESC
                    LIMIT 1
                """, (st.session_state.usuario,))
                
                hora_extra = cursor.fetchone()
            except Exception as e:
                # Tabela não existe ou erro de acesso - retornar silenciosamente
                if 'does not exist' in str(e) or 'no such table' in str(e):
                    return
                raise e
            
            if not hora_extra:
                return
            
            he_id, aprovador, justificativa, data_inicio, status = hora_extra
            
            # Calcular tempo decorrido
            from calculo_horas_system import safe_datetime_parse
            inicio = safe_datetime_parse(data_inicio)
            agora = agora_br_naive()
            tempo_decorrido = agora - inicio
            
            horas = int(tempo_decorrido.total_seconds() // 3600)
            minutos = int((tempo_decorrido.total_seconds() % 3600) // 60)
            
            if status == 'aguardando_aprovacao':
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 10px 0;
                    color: white;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">
                    <h3 style="margin: 0; color: white;">⏳ AGUARDANDO APROVAÇÃO DE HORA EXTRA</h3>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>Gestor:</strong> {aprovador}<br>
                        <strong>Iniciado em:</strong> {inicio.strftime('%H:%M')}<br>
                        <strong>Tempo decorrido:</strong> {horas}h {minutos}min<br>
                        <strong>Justificativa:</strong> {justificativa[:100]}{'...' if len(justificativa) > 100 else ''}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            elif status == 'em_execucao':
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 10px 0;
                    color: white;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">
                    <h3 style="margin: 0; color: white;">⏱️ HORA EXTRA EM ANDAMENTO</h3>
                    <p style="margin: 10px 0; font-size: 16px;">
                        <strong>Aprovada por:</strong> {aprovador}<br>
                        <strong>Iniciado em:</strong> {inicio.strftime('%H:%M')}<br>
                        <strong>⏱️ Tempo decorrido:</strong> <span style="font-size: 24px; font-weight: bold;">{horas}h {minutos}min</span>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🛑 Encerrar Hora Extra", type="primary", width="stretch", key="btn_encerrar_he"):
                        # Encerrar hora extra
                        conn_encerrar = get_connection()
                        cursor_encerrar = conn_encerrar.cursor()
                        
                        try:
                            agora = get_datetime_br()
                            agora_sem_tz = agora.replace(tzinfo=None)
                            tempo_total_minutos = int(tempo_decorrido.total_seconds() / 60)
                            
                            cursor_encerrar.execute(f"""
                                UPDATE horas_extras_ativas
                                SET status = 'encerrada',
                                    data_fim = {SQL_PLACEHOLDER},
                                    hora_fim = {SQL_PLACEHOLDER},
                                    tempo_decorrido_minutos = {SQL_PLACEHOLDER}
                                WHERE id = {SQL_PLACEHOLDER}
                            """, (
                                agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S'),
                                agora_sem_tz.strftime('%H:%M'),
                                tempo_total_minutos,
                                he_id
                            ))
                            
                            # Registrar na tabela de solicitações de horas extras
                            cursor_encerrar.execute(f"""
                                INSERT INTO solicitacoes_horas_extras
                                (usuario, data, hora_inicio, hora_fim, justificativa, aprovador_solicitado, status, aprovado_por, data_aprovacao)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'aprovada', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            """, (
                                st.session_state.usuario,
                                inicio.strftime('%Y-%m-%d'),
                                inicio.strftime('%H:%M'),
                                agora_sem_tz.strftime('%H:%M'),
                                justificativa,
                                aprovador,
                                aprovador,
                                agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S')
                            ))
                            
                            conn_encerrar.commit()
                            
                            st.success(f"✅ Hora extra encerrada! Total trabalhado: **{horas}h {minutos}min**")
                            st.balloons()
                            
                            # Aguardar um pouco para mostrar a mensagem
                            import time
                            time.sleep(2)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao encerrar hora extra: {e}")
                        finally:
                            _return_conn(conn_encerrar)
                
                with col2:
                    st.info("💡 Clique em 'Encerrar' quando finalizar o trabalho para registrar o total de horas extras")
        
        except Exception as e:
            logger.error(f"Erro em exibir_hora_extra_em_andamento: {str(e)}")
        finally:
            if conn:
                _return_conn(conn)


def aprovar_hora_extra_rapida_interface():
    """Interface rápida para gestor aprovar/rejeitar hora extra"""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        color: white;
    ">
        <h2 style="margin: 0; color: white;">📋 Aprovar Hora Extra</h2>
        <p style="margin: 10px 0;">Você tem solicitações de hora extra aguardando aprovação</p>
    </div>
    """, unsafe_allow_html=True)
    
    if REFACTORING_ENABLED:
        try:
            # Buscar solicitações pendentes para este gestor
            query = f"""
                SELECT 
                    he.id,
                    u.nome_completo,
                    he.justificativa,
                    he.data_inicio,
                    he.hora_inicio,
                    he.usuario
                FROM horas_extras_ativas he
                JOIN usuarios u ON u.usuario = he.usuario
                WHERE he.aprovador = {SQL_PLACEHOLDER}
                AND he.status = 'aguardando_aprovacao'
                ORDER BY he.data_criacao DESC
            """
            solicitacoes = execute_query(query, (st.session_state.usuario,))
            
            if not solicitacoes:
                st.info("✅ Nenhuma solicitação pendente no momento")
                
                if st.button("↩️ Voltar ao Menu", width="stretch"):
                    if 'aprovar_hora_extra' in st.session_state:
                        del st.session_state.aprovar_hora_extra
                    st.rerun()
                return
            
            # Exibir cada solicitação
            for idx, sol in enumerate(solicitacoes):
                he_id, nome_funcionario, justificativa, data_inicio, hora_inicio, funcionario = sol
                
                # Converter data/hora
                data_inicio_obj = safe_datetime_parse(data_inicio) if isinstance(data_inicio, str) else data_inicio
                hora_inicio_obj = safe_datetime_parse(hora_inicio) if isinstance(hora_inicio, str) else hora_inicio
                
                data_formatada = data_inicio_obj.strftime('%d/%m/%Y') if data_inicio_obj else 'N/A'
                hora_formatada = hora_inicio_obj.strftime('%H:%M') if hora_inicio_obj else 'N/A'
                
                st.markdown(f"""
                <div style="
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 15px 0;
                    border-left: 5px solid #f5576c;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h4 style="margin: 0 0 10px 0; color: #333;">👤 {nome_funcionario}</h4>
                    <p style="margin: 5px 0; color: #666;">
                        <strong>📅 Data:</strong> {data_formatada} às {hora_formatada}<br>
                        <strong>💬 Justificativa:</strong> {justificativa if justificativa else 'Não informada'}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Aprovar", key=f"aprovar_{he_id}", type="primary", width="stretch"):
                        # Atualizar status para em_execucao
                        update_query = f"""
                            UPDATE horas_extras_ativas
                            SET status = 'em_execucao'
                            WHERE id = {SQL_PLACEHOLDER}
                        """
                        execute_update(update_query, (he_id,))
                        
                        # Criar notificação para o funcionário
                        from notifications import NotificationManager
                        notification_manager = NotificationManager()
                        
                        notification_manager.criar_notificacao(
                            usuario=funcionario,
                            tipo='hora_extra_aprovada',
                            titulo='✅ Hora Extra Aprovada',
                            mensagem=f'Sua solicitação de hora extra foi aprovada por {st.session_state.nome_completo}. O contador está rodando!',
                            dados_extra={'hora_extra_id': he_id}
                        )
                        
                        log_security_event("HOUR_EXTRA_APPROVED", usuario=st.session_state.usuario, context={"he_id": he_id, "funcionario": funcionario})
                        st.success(f"✅ Hora extra de {nome_funcionario} aprovada com sucesso!")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
                
                with col2:
                    if st.button("❌ Rejeitar", key=f"rejeitar_{he_id}", width="stretch"):
                        # Atualizar status para rejeitada
                        update_query = f"""
                            UPDATE horas_extras_ativas
                            SET status = 'rejeitada'
                            WHERE id = {SQL_PLACEHOLDER}
                        """
                        execute_update(update_query, (he_id,))
                        
                        # Criar notificação para o funcionário
                        from notifications import NotificationManager
                        notification_manager = NotificationManager()
                        
                        notification_manager.criar_notificacao(
                            usuario=funcionario,
                            tipo='hora_extra_rejeitada',
                            titulo='❌ Hora Extra Rejeitada',
                            mensagem=f'Sua solicitação de hora extra foi rejeitada por {st.session_state.nome_completo}.',
                            dados_extra={'hora_extra_id': he_id}
                        )
                        
                        log_security_event("HOUR_EXTRA_REJECTED", usuario=st.session_state.usuario, context={"he_id": he_id, "funcionario": funcionario})
                        st.warning(f"❌ Hora extra de {nome_funcionario} rejeitada")
                        time.sleep(1.5)
                        st.rerun()
                
                st.markdown("---")
            
            # Botão para voltar
            if st.button("↩️ Voltar ao Menu", width="stretch"):
                if 'aprovar_hora_extra' in st.session_state:
                    del st.session_state.aprovar_hora_extra
                st.rerun()
        
        except Exception as e:
            log_error("Erro ao buscar solicitações de hora extra", e, {"gestor": st.session_state.usuario})
            st.error(f"❌ Erro ao buscar solicitações: {str(e)}")
    else:
        # Fallback original
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Buscar solicitações pendentes para este gestor
            cursor.execute(f"""
                SELECT 
                    he.id,
                    u.nome_completo,
                    he.justificativa,
                    he.data_inicio,
                    he.hora_inicio,
                    he.usuario
                FROM horas_extras_ativas he
                JOIN usuarios u ON u.usuario = he.usuario
                WHERE he.aprovador = {SQL_PLACEHOLDER}
                AND he.status = 'aguardando_aprovacao'
                ORDER BY he.data_criacao DESC
            """, (st.session_state.usuario,))
            
            solicitacoes = cursor.fetchall()
            
            if not solicitacoes:
                st.info("✅ Nenhuma solicitação pendente no momento")
                
                if st.button("↩️ Voltar ao Menu", width="stretch"):
                    if 'aprovar_hora_extra' in st.session_state:
                        del st.session_state.aprovar_hora_extra
                    st.rerun()
                return
            
            # Exibir cada solicitação
            for idx, sol in enumerate(solicitacoes):
                he_id, nome_funcionario, justificativa, data_inicio, hora_inicio, funcionario = sol
                
                # Converter data/hora
                data_inicio_obj = safe_datetime_parse(data_inicio) if isinstance(data_inicio, str) else data_inicio
                hora_inicio_obj = safe_datetime_parse(hora_inicio) if isinstance(hora_inicio, str) else hora_inicio
                
                data_formatada = data_inicio_obj.strftime('%d/%m/%Y') if data_inicio_obj else 'N/A'
                hora_formatada = hora_inicio_obj.strftime('%H:%M') if hora_inicio_obj else 'N/A'
                
                st.markdown(f"""
                <div style="
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 15px 0;
                    border-left: 5px solid #f5576c;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                ">
                    <h4 style="margin: 0 0 10px 0; color: #333;">👤 {nome_funcionario}</h4>
                    <p style="margin: 5px 0; color: #666;">
                        <strong>📅 Data:</strong> {data_formatada} às {hora_formatada}<br>
                        <strong>💬 Justificativa:</strong> {justificativa if justificativa else 'Não informada'}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Aprovar", key=f"aprovar_{he_id}", type="primary", width="stretch"):
                        # Atualizar status para em_execucao
                        cursor.execute(f"""
                            UPDATE horas_extras_ativas
                            SET status = 'em_execucao'
                            WHERE id = {SQL_PLACEHOLDER}
                        """, (he_id,))
                        conn.commit()
                        
                        # Criar notificação para o funcionário
                        from notifications import NotificationManager
                        notification_manager = NotificationManager()
                        
                        cursor.execute(f"""
                            SELECT usuario FROM horas_extras_ativas WHERE id = {SQL_PLACEHOLDER}
                        """, (he_id,))
                        result = cursor.fetchone()
                        if result:
                            funcionario = result[0]
                            
                            notification_manager.criar_notificacao(
                                usuario=funcionario,
                                tipo='hora_extra_aprovada',
                                titulo='✅ Hora Extra Aprovada',
                                mensagem=f'Sua solicitação de hora extra foi aprovada por {st.session_state.nome_completo}. O contador está rodando!',
                                dados_extra={'hora_extra_id': he_id}
                            )
                        
                        st.success(f"✅ Hora extra de {nome_funcionario} aprovada com sucesso!")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
                
                with col2:
                    if st.button("❌ Rejeitar", key=f"rejeitar_{he_id}", width="stretch"):
                        # Atualizar status para rejeitada
                        cursor.execute(f"""
                            UPDATE horas_extras_ativas
                            SET status = 'rejeitada'
                            WHERE id = {SQL_PLACEHOLDER}
                        """, (he_id,))
                        conn.commit()
                        
                        # Criar notificação para o funcionário
                        from notifications import NotificationManager
                        notification_manager = NotificationManager()
                        
                        cursor.execute(f"""
                            SELECT usuario FROM horas_extras_ativas WHERE id = {SQL_PLACEHOLDER}
                        """, (he_id,))
                        result = cursor.fetchone()
                        if result:
                            funcionario = result[0]
                            
                            notification_manager.criar_notificacao(
                                usuario=funcionario,
                                tipo='hora_extra_rejeitada',
                                titulo='❌ Hora Extra Rejeitada',
                                mensagem=f'Sua solicitação de hora extra foi rejeitada por {st.session_state.nome_completo}.',
                                dados_extra={'hora_extra_id': he_id}
                            )
                        
                        st.warning(f"❌ Hora extra de {nome_funcionario} rejeitada")
                        time.sleep(1.5)
                        st.rerun()
                
                st.markdown("---")
            
            # Botão para voltar
            if st.button("↩️ Voltar ao Menu", width="stretch"):
                if 'aprovar_hora_extra' in st.session_state:
                    del st.session_state.aprovar_hora_extra
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ Erro ao buscar solicitações: {str(e)}")
            logger.error(f"Erro em aprovar_hora_extra_rapida_interface: {str(e)}")
        finally:
            if conn:
                _return_conn(conn)


def exibir_widget_notificacoes(horas_extras_system):
    """Exibe widget fixo de notificações pendentes até serem respondidas - OTIMIZADO"""
    try:
        # ⚡ OTIMIZAÇÃO: Usar cache para buscar notificações
        try:
            from db_optimized import get_notificacoes_funcionario, get_solicitacoes_he_pendentes
            
            notif = get_notificacoes_funcionario(st.session_state.usuario)
            he_pendentes = notif["he_aprovar"]
            correcoes_pendentes = notif["correcoes_pendentes"]
            atestados_pendentes = notif["atestados_pendentes"]
            
            # Buscar detalhes apenas se houver HE pendentes
            solicitacoes_he_detalhes = []
            if he_pendentes > 0:
                solicitacoes_he_detalhes = get_solicitacoes_he_pendentes(st.session_state.usuario)
            
        except ImportError:
            # Fallback para queries sem cache
            he_pendentes = 0
            correcoes_pendentes = 0
            atestados_pendentes = 0
            solicitacoes_he_detalhes = []
            
            if REFACTORING_ENABLED:
                try:
                    solicitacoes_he_detalhes = execute_query(
                        f"""SELECT id, usuario, data, hora_inicio, hora_fim, total_horas, justificativa, data_solicitacao
                           FROM solicitacoes_horas_extras 
                           WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
                           ORDER BY data_solicitacao DESC""",
                        (st.session_state.usuario,)
                    ) or []
                    he_pendentes = len(solicitacoes_he_detalhes)
                    
                    result_corr = execute_query(
                        f"SELECT COUNT(*) FROM solicitacoes_correcao_registro WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'",
                        (st.session_state.usuario,),
                        fetch_one=True
                    )
                    correcoes_pendentes = result_corr[0] if result_corr else 0
                    
                    result_at = execute_query(
                        f"SELECT COUNT(*) FROM atestado_horas WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'",
                        (st.session_state.usuario,),
                        fetch_one=True
                    )
                    atestados_pendentes = result_at[0] if result_at else 0
                except Exception as e:
                    log_error("Erro ao buscar notificações pendentes", e, {"usuario": st.session_state.usuario})
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()

                    cursor.execute(f"""
                        SELECT id, usuario, data, hora_inicio, hora_fim, total_horas, justificativa, data_solicitacao
                        FROM solicitacoes_horas_extras 
                        WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
                        ORDER BY data_solicitacao DESC
                    """, (st.session_state.usuario,))
                    solicitacoes_he_detalhes = cursor.fetchall()
                    he_pendentes = len(solicitacoes_he_detalhes)

                    cursor.execute(f"""
                        SELECT COUNT(*) FROM solicitacoes_correcao_registro 
                        WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                    """, (st.session_state.usuario,))
                    correcoes_pendentes = cursor.fetchone()[0]

                    cursor.execute(f"""
                        SELECT COUNT(*) FROM atestado_horas 
                        WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                    """, (st.session_state.usuario,))
                    atestados_pendentes = cursor.fetchone()[0]

                finally:
                    _return_conn(conn)
        
        total_notificacoes = he_pendentes + correcoes_pendentes + atestados_pendentes
        
        # ========== NOTIFICAÇÃO URGENTE DE HORAS EXTRAS PARA APROVAR ==========
        if he_pendentes > 0:
            st.markdown("""
            <style>
            .urgente-he-widget {
                background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
                padding: 20px;
                border-radius: 15px;
                margin: 15px 0;
                box-shadow: 0 4px 20px rgba(220, 53, 69, 0.5);
                border: 3px solid #fff;
                animation: urgente-pulse 1s infinite;
            }
            
            @keyframes urgente-pulse {
                0%, 100% { box-shadow: 0 4px 20px rgba(220, 53, 69, 0.5); }
                50% { box-shadow: 0 4px 30px rgba(220, 53, 69, 0.8); }
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="urgente-he-widget">
                <h2 style="margin: 0; color: white; text-align: center;">
                    ⚠️🕐 SOLICITAÇÃO DE HORAS EXTRAS AGUARDANDO SUA APROVAÇÃO! ⚠️
                </h2>
                <p style="margin: 10px 0; color: white; text-align: center; font-size: 16px;">
                    Você tem <strong>{he_pendentes}</strong> solicitação(ões) pendente(s). Por favor, responda!
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Mostrar detalhes de cada solicitação pendente
            for sol in solicitacoes_he_detalhes:
                # Suportar tanto dicionário (cache) quanto tuple (fallback)
                if isinstance(sol, dict):
                    sol_id = sol["id"]
                    sol_usuario = sol["usuario"]
                    sol_data = sol["data"]
                    sol_h_inicio = sol["hora_inicio"]
                    sol_h_fim = sol["hora_fim"]
                    sol_total = sol["total_horas"]
                    sol_just = sol["justificativa"]
                else:
                    sol_id, sol_usuario, sol_data, sol_h_inicio, sol_h_fim, sol_total, sol_just, sol_data_sol = sol
                
                # Buscar nome do solicitante
                nome_solicitante = sol_usuario
                try:
                    if REFACTORING_ENABLED:
                        result = execute_query(
                            f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}",
                            (sol_usuario,),
                            fetch_one=True
                        )
                        if result:
                            nome_solicitante = result[0]
                    else:
                        conn = get_connection()
                        try:
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (sol_usuario,))
                            result = cursor.fetchone()
                            if result:
                                nome_solicitante = result[0]
                        finally:
                            _return_conn(conn)
                except Exception as e:
                    logger.debug(f"Erro ao buscar nome do solicitante: {e}")
                
                with st.expander(f"🕐 {nome_solicitante} - {sol_data} - {format_time_duration(sol_total)}", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Solicitante:** {nome_solicitante} ({sol_usuario})")
                        st.write(f"**Data:** {sol_data}")
                        st.write(f"**Horário:** {sol_h_inicio} às {sol_h_fim}")
                        st.write(f"**Total:** {format_time_duration(sol_total)}")
                        st.write(f"**Justificativa:** {sol_just}")
                    
                    with col2:
                        observacoes_he = st.text_area(
                            "Observações:",
                            key=f"obs_he_widget_{sol_id}",
                            height=80
                        )
                        
                        col_apr, col_rej = st.columns(2)
                        
                        with col_apr:
                            if st.button("✅ Aprovar", key=f"apr_he_widget_{sol_id}", width="stretch", type="primary"):
                                try:
                                    conn = get_connection()
                                    try:
                                        cursor = conn.cursor()
                                        cursor.execute(f"""
                                            UPDATE solicitacoes_horas_extras 
                                            SET status = 'aprovado', aprovado_por = {SQL_PLACEHOLDER}, 
                                                data_aprovacao = NOW(), observacoes = {SQL_PLACEHOLDER}
                                            WHERE id = {SQL_PLACEHOLDER}
                                        """, (st.session_state.usuario, observacoes_he, sol_id))
                                        conn.commit()
                                    finally:
                                        _return_conn(conn)
                                    st.success("✅ Horas extras aprovadas!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")
                        
                        with col_rej:
                            if st.button("❌ Rejeitar", key=f"rej_he_widget_{sol_id}", width="stretch"):
                                if not observacoes_he or not observacoes_he.strip():
                                    st.error("❌ Informe o motivo da rejeição!")
                                else:
                                    try:
                                        conn = get_connection()
                                        try:
                                            cursor = conn.cursor()
                                            cursor.execute(f"""
                                                UPDATE solicitacoes_horas_extras 
                                                SET status = 'rejeitado', aprovado_por = {SQL_PLACEHOLDER}, 
                                                    data_aprovacao = NOW(), observacoes = {SQL_PLACEHOLDER}
                                                WHERE id = {SQL_PLACEHOLDER}
                                            """, (st.session_state.usuario, observacoes_he, sol_id))
                                            conn.commit()
                                        finally:
                                            _return_conn(conn)
                                        st.warning("❌ Horas extras rejeitadas.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro: {e}")
            
            st.markdown("---")
        
        # ========== OUTRAS NOTIFICAÇÕES ==========
        if correcoes_pendentes > 0 or atestados_pendentes > 0:
            st.markdown("""
            <style>
            .notification-widget {
                background: linear-gradient(135deg, #FFA500 0%, #FF6347 100%);
                padding: 15px 20px;
                border-radius: 10px;
                margin: 15px 0;
                box-shadow: 0 4px 12px rgba(255, 99, 71, 0.3);
                border-left: 5px solid #FF4500;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="notification-widget">
                <h3 style="margin: 0; color: white; display: inline-block;">
                    🔔 Notificações Pendentes
                </h3>
                <p style="margin: 10px 0 5px 0; color: white; font-size: 14px;">
                    Você tem ações aguardando resposta:
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            cols = st.columns(2)
            
            if correcoes_pendentes > 0:
                with cols[0]:
                    if st.button(f"🔧 {correcoes_pendentes} Correção(ões) Pendente(s)", 
                                width="stretch",
                                type="secondary",
                                key="notif_correcao"):
                        st.session_state.ir_para_correcoes = True
                        st.rerun()
            
            if atestados_pendentes > 0:
                with cols[1]:
                    if st.button(f"⏰ {atestados_pendentes} Atestado(s) Pendente(s)", 
                                width="stretch",
                                type="secondary",
                                key="notif_atestado"):
                        st.session_state.ir_para_atestados = True
                        st.rerun()
            
            st.markdown("---")
    
    except Exception as e:
        logger.error(f"Erro ao exibir widget de notificações: {e}")


# Interface principal do funcionário
def tela_funcionario():
    """Interface principal para funcionários - OTIMIZADO"""
    atestado_system, upload_system, horas_extras_system, banco_horas_system, calculo_horas_system = init_systems()

    # Header
    st.markdown(f"""
    <div class="main-header">
        <div class="user-welcome">👋 Olá, {st.session_state.nome_completo}</div>
        <div class="user-info">Funcionário • {get_datetime_br().strftime('%d/%m/%Y %H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)

    # Widget de notificações persistentes
    exibir_widget_notificacoes(horas_extras_system)

    # Exibir hora extra em andamento (se houver)
    exibir_hora_extra_em_andamento()

    # ✨ NOVO: Alerta avançado de fim de jornada usando novo sistema
    exibir_alerta_fim_jornada_avancado()

    # Menu lateral
    with st.sidebar:
        st.markdown("### 📋 Menu Principal")

        # ⚡ OTIMIZAÇÃO: Usar cache para contagem de notificações
        try:
            from db_optimized import get_notificacoes_funcionario
            notif = get_notificacoes_funcionario(st.session_state.usuario)
            he_aprovar = notif["he_aprovar"]
            correcoes_pendentes = notif["correcoes_pendentes"]
            atestados_pendentes = notif["atestados_pendentes"]
            total_notif = notif["total"]
        except ImportError:
            # Fallback para queries sem cache
            if REFACTORING_ENABLED:
                try:
                    result_he = execute_query(
                        f"SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'",
                        (st.session_state.usuario,),
                        fetch_one=True
                    )
                    he_aprovar = result_he[0] if result_he else 0
                    
                    result_corr = execute_query(
                        f"SELECT COUNT(*) FROM solicitacoes_correcao_registro WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'",
                        (st.session_state.usuario,),
                        fetch_one=True
                    )
                    correcoes_pendentes = result_corr[0] if result_corr else 0
                    
                    result_at = execute_query(
                        f"SELECT COUNT(*) FROM atestado_horas WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'",
                        (st.session_state.usuario,),
                        fetch_one=True
                    )
                    atestados_pendentes = result_at[0] if result_at else 0
                except Exception as e:
                    log_error("Erro ao contar notificações da sidebar", e, {"usuario": st.session_state.usuario})
                    he_aprovar = correcoes_pendentes = atestados_pendentes = 0
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()

                    cursor.execute(f"""
                        SELECT COUNT(*) FROM solicitacoes_horas_extras 
                        WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
                    """, (st.session_state.usuario,))
                    he_aprovar = cursor.fetchone()[0]

                    cursor.execute(f"""
                        SELECT COUNT(*) FROM solicitacoes_correcao_registro 
                        WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                    """, (st.session_state.usuario,))
                    correcoes_pendentes = cursor.fetchone()[0]

                    cursor.execute(f"""
                        SELECT COUNT(*) FROM atestado_horas 
                        WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                    """, (st.session_state.usuario,))
                    atestados_pendentes = cursor.fetchone()[0]

                finally:
                    _return_conn(conn)
            
            total_notif = he_aprovar + correcoes_pendentes + atestados_pendentes
            
        # Contar mensagens não lidas (fora do bloco try/except)
        msgs_nao_lidas = 0
        try:
            msgs_nao_lidas = obter_mensagens_nao_lidas_count_cached(st.session_state.usuario)
        except Exception as e:
            logger.debug(f"Erro ao contar mensagens não lidas: {e}")

        # CSS para badges
        st.markdown("""
        <style>
        .menu-badge {
            background: #FF4500;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 5px;
        }
        </style>
        """, unsafe_allow_html=True)

        opcoes_menu = [
            "🕐 Registrar Ponto",
            "📋 Meus Registros",
            f"🔧 Solicitar Correção de Registro{f' 🔴{correcoes_pendentes}' if correcoes_pendentes > 0 else ''}",
            "🏥 Registrar Ausência",
            f"⏰ Atestado de Horas{f' 🔴{atestados_pendentes}' if atestados_pendentes > 0 else ''}",
            f"🕐 Horas Extras{f' 🔴{he_aprovar}' if he_aprovar > 0 else ''}",
            "🏦 Meu Banco de Horas",
            "📊 Minhas Horas por Projeto",
            "📁 Meus Arquivos",
            f"💬 Mensagens{f' 🔴{msgs_nao_lidas}' if msgs_nao_lidas > 0 else ''}",
            f"🔔 Notificações{f' 🔴{total_notif}' if total_notif > 0 else ''}"
        ]

        # 🔧 CORREÇÃO: Persistir opção selecionada no session_state após st.rerun()
        if 'menu_func_index' not in st.session_state:
            st.session_state.menu_func_index = 0
        
        opcao = st.selectbox(
            "Escolha uma opção:", 
            opcoes_menu,
            index=st.session_state.menu_func_index,
            key="menu_func_selectbox"
        )
        
        # Atualizar índice no session_state
        if opcao in opcoes_menu:
            st.session_state.menu_func_index = opcoes_menu.index(opcao)
        else:
            for i, opt in enumerate(opcoes_menu):
                if opcao.split('🔴')[0].strip() == opt.split('🔴')[0].strip():
                    st.session_state.menu_func_index = i
                    break

        st.markdown("---")
        
        # Sistema de Push Notifications (ntfy.sh - funciona mesmo com app fechado)
        st.markdown("#### 🔔 Lembretes de Ponto")
        
        # Verificar se já está inscrito
        try:
            topic, push_ativo = verificar_subscription(st.session_state.usuario)
        except Exception as e:
            logger.debug(f"Erro ao verificar subscription push (funcionário): {e}")
            topic, push_ativo = None, False
        
        ntfy_topic = get_topic_for_user(st.session_state.usuario)
        
        if push_ativo:
            st.success("✅ Push ativo!")
            
            st.markdown(f"""
            <div style="font-size: 13px; padding: 12px; background: #e8f5e9; border-radius: 8px; margin: 10px 0;">
                <p style="margin: 0 0 10px 0;"><b>📲 Para receber no celular:</b></p>
                <ol style="margin: 0; padding-left: 20px; line-height: 2;">
                    <li>Instale o app <a href="https://ntfy.sh" target="_blank">ntfy</a></li>
                    <li>Inscreva-se no tópico:</li>
                </ol>
                <div style="background: #fff; padding: 8px 12px; border-radius: 6px; margin-top: 8px; text-align: center;">
                    <code style="font-size: 14px; font-weight: bold; color: #1976d2;">{ntfy_topic}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Configurar horários personalizados
            with st.expander("⏰ Configurar Horários"):
                from push_scheduler import obter_horarios_usuario, atualizar_horarios_usuario
                
                horarios = obter_horarios_usuario(st.session_state.usuario)
                
                h_entrada = st.text_input("🌅 Entrada:", value=horarios['entrada'], key="h_entrada")
                h_almoco_s = st.text_input("🍽️ Saída Almoço:", value=horarios['almoco_saida'], key="h_almoco_s")
                h_almoco_r = st.text_input("☕ Retorno Almoço:", value=horarios['almoco_retorno'], key="h_almoco_r")
                h_saida = st.text_input("🏠 Saída:", value=horarios['saida'], key="h_saida")
                
                if st.button("💾 Salvar Horários", key="salvar_horarios"):
                    if atualizar_horarios_usuario(
                        st.session_state.usuario, 
                        h_entrada, h_almoco_s, h_almoco_r, h_saida
                    ):
                        st.success("✅ Horários atualizados!")
                    else:
                        st.error("❌ Erro ao salvar")
            
            if st.button("🔕 Desativar", width="stretch", key="btn_desativar_push"):
                from push_scheduler import desativar_subscription
                desativar_subscription(st.session_state.usuario)
                st.rerun()
        else:
            st.info("📱 Receba lembretes mesmo com o app fechado!")
            
            if st.button("🔔 Ativar Lembretes", width="stretch", key="btn_ativar_push"):
                topic = registrar_subscription(st.session_state.usuario)
                st.success(f"✅ Ativado! Seu tópico: **{ntfy_topic}**")
                st.rerun()

        st.markdown("---")

        if st.button("🚪 Sair", width="stretch"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Redirecionar se clicou em algum botão do widget de notificações
    if st.session_state.get('ir_para_notificacoes'):
        del st.session_state.ir_para_notificacoes
        opcao = "🔔 Notificações"
    elif st.session_state.get('ir_para_correcoes'):
        del st.session_state.ir_para_correcoes
        # Encontrar a opção correta (pode ter badge)
        for opt in opcoes_menu:
            if opt.startswith("🔧 Solicitar Correção"):
                opcao = opt
                break
    elif st.session_state.get('ir_para_atestados'):
        del st.session_state.ir_para_atestados
        # Encontrar a opção correta (pode ter badge)
        for opt in opcoes_menu:
            if opt.startswith("⏰ Atestado de Horas"):
                opcao = opt
                break

    # Conteúdo principal baseado na opção selecionada
    if opcao == "🕐 Registrar Ponto":
        registrar_ponto_interface(calculo_horas_system, horas_extras_system)
    elif opcao == "📋 Meus Registros":
        meus_registros_interface(calculo_horas_system)
    elif opcao.startswith("🔧 Solicitar Correção"):
        solicitar_correcao_registro_interface()
    elif opcao == "🏥 Registrar Ausência":
        registrar_ausencia_interface(upload_system)
    elif opcao.startswith("⏰ Atestado de Horas"):
        atestado_horas_interface(atestado_system, upload_system)
    elif opcao.startswith("🕐 Horas Extras"):
        horas_extras_interface(horas_extras_system)
    elif opcao == "🏦 Meu Banco de Horas":
        banco_horas_funcionario_interface(banco_horas_system)
    elif opcao == "📊 Minhas Horas por Projeto":
        minhas_horas_projeto_interface()
    elif opcao == "📁 Meus Arquivos":
        meus_arquivos_interface(upload_system)
    elif opcao.startswith("💬 Mensagens"):
        mensagens_funcionario_interface()
    elif opcao.startswith("🔔 Notificações"):
        notificacoes_interface(horas_extras_system)


def mensagens_funcionario_interface():
    """Interface para visualizar mensagens diretas recebidas"""
    from push_scheduler import obter_mensagens_usuario, marcar_mensagem_lida
    
    st.markdown("""
    <div class="feature-card">
        <h3>💬 Minhas Mensagens</h3>
        <p>Mensagens diretas enviadas pelo gestor</p>
    </div>
    """, unsafe_allow_html=True)
    
    mensagens = obter_mensagens_usuario(st.session_state.usuario)
    
    if mensagens:
        nao_lidas = [m for m in mensagens if not m[4]]
        lidas = [m for m in mensagens if m[4]]
        
        if nao_lidas:
            st.markdown("### 🔴 Não Lidas")
            for msg in nao_lidas:
                msg_id, remetente, texto, data_envio, lida, nome_remetente = msg
                
                with st.expander(f"💬 {nome_remetente or remetente} - {data_envio.strftime('%d/%m/%Y %H:%M')}", expanded=True):
                    st.markdown(f"**De:** {nome_remetente or remetente}")
                    st.markdown(f"**Data:** {data_envio.strftime('%d/%m/%Y %H:%M')}")
                    st.info(texto)
                    
                    if st.button("✅ Marcar como lida", key=f"ler_msg_{msg_id}"):
                        marcar_mensagem_lida(msg_id)
                        st.rerun()
        
        if lidas:
            st.markdown("### ✅ Lidas")
            for msg in lidas:
                msg_id, remetente, texto, data_envio, lida, nome_remetente = msg
                
                with st.expander(f"💬 {nome_remetente or remetente} - {data_envio.strftime('%d/%m/%Y %H:%M')}"):
                    st.markdown(f"**De:** {nome_remetente or remetente}")
                    st.markdown(f"**Data:** {data_envio.strftime('%d/%m/%Y %H:%M')}")
                    st.markdown(texto)
    else:
        st.info("📭 Você não tem mensagens")


# ====================================================================
# Funções auxiliares extraídas de registrar_ponto_interface()
# ====================================================================

def _render_gps_capture_js():
    """Injeta JavaScript otimizado para captura de coordenadas GPS."""
    gps_js = """
    <div id="gps-status" style="padding: 10px; margin-bottom: 10px;">
        <div style="padding: 8px; background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 8px; text-align: center;">
            📍 Obtendo localização GPS...
        </div>
    </div>
    <script>
    (function() {
        const cachedLat = sessionStorage.getItem('gps_latitude');
        const cachedLng = sessionStorage.getItem('gps_longitude');
        const cachedAcc = sessionStorage.getItem('gps_accuracy');
        const cachedTime = sessionStorage.getItem('gps_timestamp');
        const cacheValid = cachedTime && (Date.now() - parseInt(cachedTime)) < 120000;

        function findGpsInput(kind) {
            const all = Array.from(document.querySelectorAll('input[type="text"]'));
            const isLat = kind === 'lat';
            return all.find(function(input) {
                const p = (input.getAttribute('placeholder') || '').toLowerCase();
                const a = (input.getAttribute('aria-label') || '').toLowerCase();
                const ref = (p + ' ' + a).trim();
                if (!ref.includes('gps') && !ref.includes('lat') && !ref.includes('long')) {
                    return false;
                }
                if (isLat) {
                    return ref.includes('lat');
                }
                return ref.includes('lng') || ref.includes('long');
            }) || null;
        }

        function fillInputs(lat, lng, retries) {
            const latField = findGpsInput('lat');
            const lngField = findGpsInput('lng');
            if (latField && lngField) {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                latField.value = lat.toString();
                latField.dispatchEvent(new Event('input', { bubbles: true }));
                latField.dispatchEvent(new Event('change', { bubbles: true }));
                nativeInputValueSetter.call(latField, lat.toString());
                latField.dispatchEvent(new Event('input', { bubbles: true }));
                lngField.value = lng.toString();
                lngField.dispatchEvent(new Event('input', { bubbles: true }));
                lngField.dispatchEvent(new Event('change', { bubbles: true }));
                nativeInputValueSetter.call(lngField, lng.toString());
                lngField.dispatchEvent(new Event('input', { bubbles: true }));
                console.log('GPS fields filled:', lat, lng);
            } else {
                const remaining = (typeof retries === 'number') ? retries : 12;
                if (remaining > 0) {
                    setTimeout(function() { fillInputs(lat, lng, remaining - 1); }, 300);
                } else {
                    console.log('GPS fields not found after retries.');
                }
            }
        }

        function updateGpsStatus(success, message) {
            const gpsDiv = document.getElementById('gps-status');
            if (gpsDiv) {
                if (success) {
                    gpsDiv.innerHTML = '<div style="padding: 8px; background: linear-gradient(135deg, #c8e6c9 0%, #a5d6a7 100%); border-radius: 8px; color: #1b5e20; text-align: center; font-weight: 500;">✅ ' + message + '</div>';
                } else {
                    gpsDiv.innerHTML = '<div style="padding: 8px; background: linear-gradient(135deg, #fff3cd 0%, #ffe082 100%); border-radius: 8px; color: #856404; text-align: center;">⚠️ ' + message + '</div>';
                }
            }
        }

        if (cacheValid && cachedLat && cachedLng) {
            updateGpsStatus(true, 'GPS: ' + parseFloat(cachedLat).toFixed(6) + ', ' + parseFloat(cachedLng).toFixed(6) + ' (±' + Math.round(cachedAcc || 0) + 'm)');
            setTimeout(() => fillInputs(cachedLat, cachedLng, 12), 300);
        }

        if (navigator.geolocation) {
            const options = { enableHighAccuracy: false, timeout: 5000, maximumAge: 120000 };
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    const acc = position.coords.accuracy;
                    sessionStorage.setItem('gps_latitude', lat);
                    sessionStorage.setItem('gps_longitude', lng);
                    sessionStorage.setItem('gps_accuracy', acc);
                    sessionStorage.setItem('gps_timestamp', Date.now());
                    updateGpsStatus(true, 'GPS: ' + lat.toFixed(6) + ', ' + lng.toFixed(6) + ' (±' + Math.round(acc) + 'm)');
                    setTimeout(() => fillInputs(lat, lng, 12), 300);
                    if (acc > 100) {
                        navigator.geolocation.getCurrentPosition(
                            function(p) {
                                if (p.coords.accuracy < acc) {
                                    sessionStorage.setItem('gps_latitude', p.coords.latitude);
                                    sessionStorage.setItem('gps_longitude', p.coords.longitude);
                                    sessionStorage.setItem('gps_accuracy', p.coords.accuracy);
                                    sessionStorage.setItem('gps_timestamp', Date.now());
                                    updateGpsStatus(true, 'GPS: ' + p.coords.latitude.toFixed(6) + ', ' + p.coords.longitude.toFixed(6) + ' (±' + Math.round(p.coords.accuracy) + 'm)');
                                    fillInputs(p.coords.latitude, p.coords.longitude, 12);
                                }
                            },
                            function() {},
                            { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                        );
                    }
                },
                function(error) {
                    console.log('GPS Error:', error.message);
                    sessionStorage.setItem('gps_error', error.message);
                    if (!cacheValid) {
                        updateGpsStatus(false, 'GPS não disponível - registro será feito sem localização');
                    }
                },
                options
            );
        } else {
            if (!cacheValid) {
                updateGpsStatus(false, 'Navegador não suporta GPS');
            }
        }
    })();
    </script>
    """
    st.components.v1.html(gps_js, height=60)


def _handle_post_registration_overtime(data_registro, horas_extras_system):
    """Detecta e exibe informações de hora extra após registro de Fim."""
    try:
        try:
            from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        except ImportError:
            JornadaSemanalCalculoSystem = None
            logger.warning("Módulo 'jornada_semanal_calculo_system' não encontrado.")

        tolerancia_minutos = 5
        if REFACTORING_ENABLED:
            try:
                result = execute_query(
                    "SELECT valor FROM configuracoes WHERE chave = 'tolerancia_atraso_minutos'",
                    fetch_one=True
                )
                if result:
                    tolerancia_minutos = int(result[0])
            except Exception as e:
                logger.warning(f"Não foi possível obter tolerância do gestor: {e}")
        else:
            try:
                cursor = get_db_connection().cursor()
                cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'tolerancia_atraso_minutos'")
                resultado = cursor.fetchone()
                if resultado:
                    tolerancia_minutos = int(resultado[0])
                cursor.close()
            except Exception as e:
                logger.warning(f"Não foi possível obter tolerância do gestor: {e}")

        resultado_hora_extra = JornadaSemanalCalculoSystem.detectar_hora_extra_dia(
            st.session_state.usuario,
            data_registro,
            tolerancia_minutos=tolerancia_minutos
        )

        if resultado_hora_extra.get('tem_hora_extra', False):
            horas_extra = resultado_hora_extra.get('horas_extra', 0)
            minutos_extra = resultado_hora_extra.get('minutos_extra', 0)
            st.success(f"""
            ⏱️ **HORA EXTRA DETECTADA!**

            Você trabalhou:
            - **{horas_extra:.1f} horas** ({minutos_extra} minutos) de hora extra
            - Esperado: {resultado_hora_extra.get('esperado_minutos', 0)} min
            - Registrado: {resultado_hora_extra.get('registrado_minutos', 0)} min
            """)
            if st.button("📝 Solicitar Aprovação de Hora Extra"):
                st.session_state.solicitar_hora_extra = True
                st.session_state.hora_extra_horas = horas_extra
                st.session_state.hora_extra_data = data_registro
                st.rerun()

        elif resultado_hora_extra.get('categoria') == 'abaixo_jornada':
            minutos_faltando = abs(resultado_hora_extra.get('minutos_extra', 0))
            st.warning(f"""
            ⏰ **REGISTRO ABAIXO DA JORNADA**

            Você trabalhou {minutos_faltando} minutos a menos que o esperado.
            """)
        else:
            st.success(f"""
            ✅ **EXPEDIENTE FINALIZADO COM SUCESSO!**

            - Esperado: {resultado_hora_extra.get('esperado_minutos', 0)} min
            - Registrado: {resultado_hora_extra.get('registrado_minutos', 0)} min
            - Status: Dentro da jornada (tolerância: {tolerancia_minutos} min)

            Bom descanso! 😊
            """)

    except ImportError:
        if horas_extras_system is not None:
            try:
                verificacao = horas_extras_system.verificar_fim_jornada(st.session_state.usuario)
                if isinstance(verificacao, dict) and verificacao.get("deve_notificar"):
                    st.info(f"💡 {verificacao.get('message')}")
            except Exception:
                st.info("💡 Não foi possível verificar horas extras no momento.")
    except Exception as e:
        logger.error(f"Erro ao detectar hora extra: {e}")
        if horas_extras_system is not None:
            try:
                verificacao = horas_extras_system.verificar_fim_jornada(st.session_state.usuario)
                if isinstance(verificacao, dict) and verificacao.get("deve_notificar"):
                    st.info(f"💡 {verificacao.get('message')}")
            except Exception:
                st.info("💡 Não foi possível verificar horas extras no momento.")


def registrar_ponto_interface(calculo_horas_system, horas_extras_system=None):
    """Interface para registro de ponto com GPS real

    horas_extras_system é opcional para compatibilidade com versões antigas.
    Se for None, funcionalidades relacionadas a verificação/solicitação de horas extras
    serão ignoradas de forma segura.
    """
    st.markdown("""
    <div class="feature-card">
        <h3>🕐 Registrar Ponto</h3>
        <p>Registre sua entrada, atividades intermediárias e saída</p>
        <p><small>💡 <strong>Registro Retroativo:</strong> Você pode registrar ponto para qualquer um dos últimos 3 dias.</small></p>
    </div>
    """, unsafe_allow_html=True)

    # ========== SEÇÃO DE HORAS EXTRAS ==========
    from jornada_semanal_system import obter_jornada_usuario
    
    # Verificar se está no horário de fim de expediente (usar timezone Brasil)
    agora = get_datetime_br()
    hoje = agora.date()
    dia_semana_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
    dia_semana = dia_semana_map.get(hoje.weekday(), 'seg')
    
    jornada = obter_jornada_usuario(st.session_state.usuario)
    config_dia = jornada.get(dia_semana, {})
    
    # Obter horário de fim da jornada
    horario_fim_jornada = config_dia.get('fim', '17:00')
    try:
        h_fim, m_fim = map(int, horario_fim_jornada.split(':'))
        hora_fim_jornada = agora.replace(hour=h_fim, minute=m_fim, second=0, microsecond=0)
    except Exception as e:
        logger.debug(f"Erro ao parsear horário fim jornada '{horario_fim_jornada}', usando 17:00: {e}")
        hora_fim_jornada = agora.replace(hour=17, minute=0, second=0, microsecond=0)
    
    # Verificar se passou do horário de fim
    passou_horario_fim = agora >= hora_fim_jornada and config_dia.get('trabalha', False)
    
    # Verificar se já registrou entrada hoje (case-insensitive)
    ja_registrou_inicio = False
    ja_registrou_fim = False
    if REFACTORING_ENABLED:
        try:
            result = execute_query(
                f"SELECT LOWER(tipo) FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}",
                (st.session_state.usuario, hoje.strftime("%Y-%m-%d"))
            )
            if result:
                tipos = [r[0].lower() if r[0] else '' for r in result]
                ja_registrou_inicio = 'início' in tipos or 'inicio' in tipos
                ja_registrou_fim = 'fim' in tipos
        except Exception as e:
            logger.warning(f"Erro ao verificar registros de ponto do dia: {e}")
    else:
        try:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT LOWER(tipo) FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}",
                    (st.session_state.usuario, hoje.strftime("%Y-%m-%d"))
                )
                tipos = [r[0].lower() if r[0] else '' for r in cursor.fetchall()]
                ja_registrou_inicio = 'início' in tipos or 'inicio' in tipos
                ja_registrou_fim = 'fim' in tipos
            finally:
                _return_conn(conn)
        except Exception as e:
            logger.warning(f"Erro ao verificar registros de ponto do dia (legacy): {e}")
    
    # Inicializar session_state para horas extras
    if 'horas_extras_ativa' not in st.session_state:
        st.session_state.horas_extras_ativa = False
    if 'horas_extras_inicio' not in st.session_state:
        st.session_state.horas_extras_inicio = None
    if 'popup_hora_extra_mostrado' not in st.session_state:
        st.session_state.popup_hora_extra_mostrado = False
    if 'ultima_notif_continuar' not in st.session_state:
        st.session_state.ultima_notif_continuar = None
    
    # Obter lista de TODOS os usuários cadastrados (exceto o solicitante) para aprovação
    usuarios_lista = []
    if REFACTORING_ENABLED:
        try:
            usuarios = execute_query(
                f"SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 AND usuario != {SQL_PLACEHOLDER} ORDER BY nome_completo",
                (st.session_state.usuario,)
            )
            if usuarios:
                usuarios_lista = [f"{u[1]} ({u[0]})" for u in usuarios]
        except Exception as e:
            logger.warning(f"Erro ao listar usuários para aprovação: {e}")
    else:
        try:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 AND usuario != {SQL_PLACEHOLDER} ORDER BY nome_completo",
                    (st.session_state.usuario,)
                )
                usuarios = cursor.fetchall()
                usuarios_lista = [f"{u[1]} ({u[0]})" for u in usuarios]
            finally:
                _return_conn(conn)
        except Exception as e:
            logger.warning(f"Erro ao listar usuários para aprovação (legacy): {e}")
    
    # ========== POPUP: Deseja fazer horas extras? ==========
    if passou_horario_fim and ja_registrou_inicio and not ja_registrou_fim and not st.session_state.popup_hora_extra_mostrado and not st.session_state.horas_extras_ativa:
        st.markdown(f"""
        <style>
        .hora-extra-popup {{
            background: linear-gradient(135deg, #ff9800, #f57c00);
            padding: 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(255, 152, 0, 0.4);
        }}
        </style>
        <div class="hora-extra-popup">
            <h3>⏰ Expediente Encerrado!</h3>
            <p>Seu horário de trabalho terminou às {horario_fim_jornada}. Deseja fazer horas extras?</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_sim, col_nao = st.columns(2)
        with col_sim:
            if st.button("✅ Sim, fazer horas extras", width="stretch", type="primary"):
                st.session_state.horas_extras_ativa = True
                st.session_state.horas_extras_inicio = get_datetime_br()
                st.session_state.popup_hora_extra_mostrado = True
                st.session_state.ultima_notif_continuar = get_datetime_br()
                st.rerun()
        
        with col_nao:
            if st.button("❌ Não, encerrar expediente", width="stretch"):
                # Registrar fim automaticamente
                st.session_state.popup_hora_extra_mostrado = True
                latitude = None
                longitude = None
                data_hora_registro = registrar_ponto(
                    st.session_state.usuario,
                    "Fim",
                    "Presencial",
                    obter_projetos_ativos()[0] if obter_projetos_ativos() else "Geral",
                    "Fim de expediente automático",
                    hoje.strftime("%Y-%m-%d"),
                    None,
                    latitude,
                    longitude
                )
                st.success("✅ Expediente encerrado automaticamente!")
                st.rerun()
    
    # ========== PAINEL DE HORAS EXTRAS - SEMPRE VISÍVEL ==========
    # Contador e botões sempre visíveis (como no layout)
    
    # Calcular tempo de horas extras (se ativa)
    tempo_he_str = "00:00:00"
    tempo_total_segundos = 0
    if st.session_state.horas_extras_ativa and st.session_state.horas_extras_inicio:
        agora_br = get_datetime_br()
        inicio_he = st.session_state.horas_extras_inicio
        if inicio_he.tzinfo is None:
            inicio_he = TIMEZONE_BR.localize(inicio_he)
        tempo_decorrido = agora_br - inicio_he
        tempo_total_segundos = int(tempo_decorrido.total_seconds())
        horas = int(tempo_decorrido.total_seconds() // 3600)
        minutos = int((tempo_decorrido.total_seconds() % 3600) // 60)
        segundos = int(tempo_decorrido.total_seconds() % 60)
        tempo_he_str = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
    
    # Verificar se botões devem estar ativos
    pode_iniciar_he = ja_registrou_inicio and not ja_registrou_fim and passou_horario_fim and not st.session_state.horas_extras_ativa
    he_em_andamento = st.session_state.horas_extras_ativa
    
    # Mensagem após 1 hora de horas extras
    if he_em_andamento and tempo_total_segundos >= 3600:
        horas_completas = tempo_total_segundos // 3600
        st.warning(f"⏰ **Atenção!** Você está fazendo horas extras há **{horas_completas} hora(s)**. Lembre-se de finalizar quando terminar.")
    
    # CSS para o painel de horas extras - contador menor e letras brancas
    st.markdown("""
    <style>
    .he-contador {
        background: #1a1a2e;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        font-size: 1.4em;
        font-weight: bold;
        padding: 8px 15px;
        border-radius: 6px;
        display: inline-block;
        min-width: 100px;
        text-align: center;
    }
    .he-contador-ativo {
        background: #2d5a3d;
        color: #ffffff;
        animation: pulse 1s infinite;
    }
    .he-contador-inativo {
        background: #333;
        color: #888;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.8; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Evitar auto-refresh agressivo que pode causar reconexões em sessões web/mobile.
    
    # Layout do painel de horas extras
    col_btn1, col_contador, col_aprovador, col_btn2 = st.columns([1.2, 1, 1.5, 1.2])
    
    with col_btn1:
        if he_em_andamento:
            st.button("🕐 HE em Andamento", disabled=True, width="stretch")
        elif pode_iniciar_he:
            if st.button("▶️ Solicitar Horas Extras", width="stretch", type="primary"):
                st.session_state.horas_extras_ativa = True
                st.session_state.horas_extras_inicio = get_datetime_br()
                st.session_state.popup_hora_extra_mostrado = True
                st.session_state.ultima_notif_continuar = get_datetime_br()
                st.rerun()
        else:
            btn_help = "Registre entrada primeiro" if not ja_registrou_inicio else "Disponível após " + horario_fim_jornada if not passou_horario_fim else "Já registrou saída"
            st.button("▶️ Solicitar Horas Extras", disabled=True, width="stretch", help=btn_help)
    
    with col_contador:
        contador_class = "he-contador he-contador-ativo" if he_em_andamento else "he-contador he-contador-inativo"
        st.markdown(f'<div class="{contador_class}">{tempo_he_str}</div>', unsafe_allow_html=True)
    
    with col_aprovador:
        aprovador_key = "aprovador_he_panel"
        if he_em_andamento:
            st.session_state.aprovador_he_selecionado = st.selectbox(
                "Quem deve autorizar:",
                ["Selecione..."] + usuarios_lista,
                key=aprovador_key,
                label_visibility="collapsed"
            )
        else:
            st.selectbox(
                "Quem deve autorizar:",
                ["Quem deve autorizar ↓"],
                disabled=True,
                key=f"{aprovador_key}_disabled",
                label_visibility="collapsed"
            )
    
    with col_btn2:
        if he_em_andamento:
            if st.button("⏹️ Finalizar Horas Extras", width="stretch", type="primary"):
                st.session_state.mostrar_finalizar_he = True
        else:
            st.button("⏹️ Finalizar Horas Extras", disabled=True, width="stretch")
    
    # Modal de finalização de horas extras
    if st.session_state.get('mostrar_finalizar_he', False) and he_em_andamento:
        st.markdown("---")
        st.subheader("📝 Finalizar Horas Extras")
        
        justificativa_he = st.text_area(
            "📋 Justificativa (obrigatória):",
            placeholder="Descreva o motivo das horas extras realizadas...",
            key="justificativa_he_final"
        )
        
        col_confirmar, col_cancelar = st.columns(2)
        
        with col_confirmar:
            if st.button("✅ Confirmar e Enviar", width="stretch", type="primary", key="btn_confirmar_he"):
                aprovador_sel = st.session_state.get('aprovador_he_selecionado', 'Selecione...')
                if aprovador_sel == "Selecione...":
                    st.error("❌ Selecione quem vai autorizar as horas extras!")
                elif not justificativa_he or not justificativa_he.strip():
                    st.error("❌ A justificativa é obrigatória!")
                else:
                    # Extrair username do aprovador
                    aprovador_username = aprovador_sel.split("(")[1].rstrip(")")
                    
                    # Calcular tempo total
                    agora_final = get_datetime_br()
                    inicio_he = st.session_state.horas_extras_inicio
                    if inicio_he.tzinfo is None:
                        inicio_he = TIMEZONE_BR.localize(inicio_he)
                    tempo_total = agora_final - inicio_he
                    horas_total = tempo_total.total_seconds() / 3600
                    
                    try:
                        # Transação atômica: HE + ponto de Fim
                        conn = get_connection()
                        try:
                            cursor = conn.cursor()

                            hora_inicio = inicio_he.strftime("%H:%M")
                            hora_fim = agora_final.strftime("%H:%M")

                            cursor.execute(f"""
                                INSERT INTO solicitacoes_horas_extras 
                                (usuario, data, hora_inicio, hora_fim, total_horas, justificativa, 
                                 aprovador_solicitado, status, data_solicitacao)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 
                                        {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                        {SQL_PLACEHOLDER}, 'pendente', NOW())
                            """, (
                                st.session_state.usuario,
                                hoje.strftime("%Y-%m-%d"),
                                hora_inicio,
                                hora_fim,
                                round(horas_total, 2),
                                justificativa_he.strip(),
                                aprovador_username
                            ))

                            # Registrar fim do expediente NA MESMA transação
                            registrar_ponto(
                                st.session_state.usuario,
                                "Fim",
                                "Presencial",
                                obter_projetos_ativos()[0] if obter_projetos_ativos() else "Geral",
                                f"Fim com horas extras: {justificativa_he.strip()[:100]}",
                                hoje.strftime("%Y-%m-%d"),
                                None, None, None,
                                conn_external=conn,
                            )

                            conn.commit()
                        except Exception:
                            conn.rollback()
                            raise
                        finally:
                            _return_conn(conn)
                        
                        # Limpar session state
                        st.session_state.horas_extras_ativa = False
                        st.session_state.horas_extras_inicio = None
                        st.session_state.mostrar_finalizar_he = False
                        
                        st.success(f"✅ Horas extras registradas! Total: {int(horas_total)}h {int((horas_total % 1) * 60)}min")
                        st.balloons()
                        import time as _time_mod
                        _time_mod.sleep(2)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)}")
        
        with col_cancelar:
            if st.button("❌ Cancelar", width="stretch", key="btn_cancelar_he"):
                st.session_state.mostrar_finalizar_he = False
                st.rerun()
    
    st.markdown("---")

    # Seção de ativação de Push (ntfy)
    with st.expander("📲 Push (ntfy) - Ativar / Desativar"):
        st.write("Ative notificações push para receber lembretes no celular via ntfy.sh")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔔 Ativar Push (ntfy)", key="ativar_push"):
                try:
                    from push_scheduler import registrar_subscription, get_topic_for_user
                    topic = registrar_subscription(st.session_state.usuario)
                    st.success(f"Push ativado. Inscreva-se no tópico: {topic}")
                    st.markdown(f"**Tópico:** `{topic}`")
                    st.markdown(f"**URL de inscrição:** https://ntfy.sh/{topic}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao ativar push: {e}")
        with col_b:
            if st.button("🔕 Desativar Push", key="desativar_push"):
                try:
                    from push_scheduler import desativar_subscription
                    desativar_subscription(st.session_state.usuario)
                    st.info("Push desativado para seu usuário.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao desativar push: {e}")

        st.markdown("---")
        st.markdown("**Instruções rápidas para ativar no celular:**")
        st.markdown("- Instale o app `ntfy` (Android: Play Store - 'ntfy') ou use um app compatível com topic subscription.")
        st.markdown("- No app, adicione nova subscription e informe o tópico mostrado acima (ex.: `ponto-exsa-xxxx`).")
        st.markdown("- Alternativamente, inscreva-se usando a URL: `https://ntfy.sh/<tópico>` no app ou navegador que suporte subscriptions.")
        st.markdown("- Após a inscrição, você receberá notificações mesmo com o app em segundo plano.")
    
    st.subheader("➕ Novo Registro")
    
    _render_gps_capture_js()

    with st.form("registro_ponto"):
        col1, col2 = st.columns(2)

        with col1:
            data_registro = st.date_input(
                "📅 Data do Registro",
                value=date.today(),
                min_value=date.today() - timedelta(days=3),
                max_value=date.today(),
                help="Você pode registrar ponto para hoje ou até 3 dias retroativos"
            )

            modalidade = st.selectbox(
                "🏢 Modalidade de Trabalho",
                ["Presencial", "Home Office", "Trabalho em Campo"]
            )

        with col2:
            tipo_registro = st.selectbox(
                "⏰ Tipo de Registro",
                ["Início", "Intermediário", "Fim"]
            )

            projeto = st.selectbox("📊 Projeto", obter_projetos_ativos())

        # Horário sempre automático no momento do clique em "Registrar Ponto"
        st.info("🕐 O horário do registro é automático no momento do envio.")

        atividade = st.text_area(
            "📝 Descrição da Atividade",
            placeholder="Descreva brevemente a atividade realizada..."
        )
        
        
        # Alerta visual para domingo ou feriado
        try:
            from calculo_horas_system import eh_dia_com_multiplicador
            
            info_dia = eh_dia_com_multiplicador(data_registro)
            if info_dia['tem_multiplicador']:
                if info_dia['eh_domingo'] and info_dia['eh_feriado']:
                    st.warning(f"""
                    ⚠️ 🎉📅 **ATENÇÃO: DOMINGO E FERIADO ({info_dia['nome_feriado']})!**
                    
                    As horas trabalhadas neste dia serão **contabilizadas em DOBRO** (x2).
                    """)
                elif info_dia['eh_domingo']:
                    st.warning(f"""
                    ⚠️ 📅 **ATENÇÃO: DOMINGO!**
                    
                    As horas trabalhadas neste dia serão **contabilizadas em DOBRO** (x2).
                    """)
                elif info_dia['eh_feriado']:
                    st.warning(f"""
                    ⚠️ 🎉 **ATENÇÃO: FERIADO - {info_dia['nome_feriado']}!**
                
                As horas trabalhadas neste dia serão **contabilizadas em DOBRO** (x2).
                """)
        except Exception as _feriado_err:
            logger.debug("Erro ao verificar feriado/domingo: %s", _feriado_err)

        # Validação de registros
        data_str = data_registro.strftime("%Y-%m-%d")
        pode_registrar = True
        mensagem_validacao_registro = ""
        try:
            conn_valid = get_connection()
            try:
                cursor_valid = conn_valid.cursor()
                pode_registrar, mensagem_validacao_registro = validar_novo_registro_cursor(
                    cursor_valid,
                    st.session_state.usuario,
                    data_str,
                    tipo_registro,
                )
            finally:
                _return_conn(conn_valid)
        except Exception as _val_err:
            logger.warning("Erro ao validar registro: %s", _val_err)

        if mensagem_validacao_registro:
            st.warning(f"⚠️ {mensagem_validacao_registro}")

        # Campos ocultos para capturar GPS via JavaScript
        # O CSS global oculta esses campos automaticamente baseado no placeholder
        # Usar session_state para persistir valores do GPS
        if 'gps_lat_value' not in st.session_state:
            st.session_state.gps_lat_value = ""
        if 'gps_lng_value' not in st.session_state:
            st.session_state.gps_lng_value = ""
        
        # Campos GPS - ocultos via CSS (placeholder="GPS Lat" e "GPS Lng")
        gps_lat_input = st.text_input("Latitude GPS", value=st.session_state.gps_lat_value, key="gps_lat_field", label_visibility="collapsed", placeholder="GPS Lat")
        gps_lng_input = st.text_input("Longitude GPS", value=st.session_state.gps_lng_value, key="gps_lng_field", label_visibility="collapsed", placeholder="GPS Lng")

        submitted = st.form_submit_button(
            "✅ Registrar Ponto", width="stretch")

        if submitted:
            if not atividade.strip():
                st.error("❌ A descrição da atividade é obrigatória")
            elif not pode_registrar:
                st.error(f"❌ {mensagem_validacao_registro or 'Registro inválido para este momento do dia.'}")
            else:
                # GPS: Obter coordenadas dos campos preenchidos via JavaScript
                latitude = None
                longitude = None
                try:
                    lat_raw = gps_lat_input or st.session_state.get("gps_lat_field", "")
                    lng_raw = gps_lng_input or st.session_state.get("gps_lng_field", "")

                    if lat_raw and str(lat_raw).strip():
                        latitude = float(str(lat_raw).strip().replace(",", "."))
                    if lng_raw and str(lng_raw).strip():
                        longitude = float(str(lng_raw).strip().replace(",", "."))
                except (ValueError, TypeError):
                    # Se não conseguir converter, registra sem GPS
                    latitude = None
                    longitude = None

                # Horário automático no exato momento do clique em registrar
                hora_str = get_datetime_br().strftime("%H:%M:%S")
                data_hora_registro = registrar_ponto(
                    st.session_state.usuario,
                    tipo_registro,
                    modalidade,
                    projeto,
                    atividade,
                    data_registro.strftime("%Y-%m-%d"),
                    hora_str,
                    latitude,
                    longitude
                )

                # Mostrar info de GPS se disponível
                if latitude and longitude:
                    st.success(f"✅ Ponto registrado com sucesso! 📍 GPS: {latitude:.6f}, {longitude:.6f}")
                else:
                    st.success(f"✅ Ponto registrado com sucesso!")
                st.info(
                    f"🕐 {data_hora_registro.strftime('%d/%m/%Y às %H:%M')}")

                

                # Detecção de hora extra pós-registro (extraído para legibilidade)
                if tipo_registro == "Fim":
                    _handle_post_registration_overtime(data_registro, horas_extras_system)

                st.rerun()

    # Mostrar registros do dia selecionado
    data_selecionada = st.date_input(
        "📅 Ver registros do dia:",
        value=date.today(),
        key="ver_registros_data"
    )

    registros_dia = obter_registros_usuario(
        st.session_state.usuario,
        data_selecionada.strftime("%Y-%m-%d"),
        data_selecionada.strftime("%Y-%m-%d")
    )

    if registros_dia:
        st.subheader(f"📋 Registros de {data_selecionada.strftime('%d/%m/%Y')}")

        # Calcular horas do dia
        calculo_dia = calculo_horas_system.calcular_horas_dia(
            st.session_state.usuario,
            data_selecionada.strftime("%Y-%m-%d")
        )

        if calculo_dia["horas_finais"] > 0:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("⏱️ Horas Trabalhadas", format_time_duration(
                    calculo_dia["horas_trabalhadas"]))
            with col2:
                st.metric("🍽️ Desconto Almoço",
                          f"{calculo_dia['desconto_almoco']}h" if calculo_dia['desconto_almoco'] > 0 else "Não aplicado")
            with col3:
                multiplicador_text = f"x{calculo_dia['multiplicador']}" if calculo_dia['multiplicador'] > 1 else ""
                st.metric(
                    "✅ Horas Finais", f"{format_time_duration(calculo_dia['horas_finais'])} {multiplicador_text}")

        df_dia = pd.DataFrame(registros_dia, columns=[
            'ID', 'Usuário', 'Data/Hora', 'Tipo', 'Modalidade', 'Projeto', 'Atividade', 'Localização', 'Latitude', 'Longitude', 'Registro'
        ])
        df_dia['Localização'] = df_dia.apply(
            lambda r: formatar_localizacao_legivel(r['Localização'], r['Latitude'], r['Longitude']),
            axis=1
        )
        df_dia['Hora'] = pd.to_datetime(
            df_dia['Data/Hora']).dt.strftime('%H:%M')
        st.dataframe(
            df_dia[['Hora', 'Tipo', 'Modalidade',
                    'Projeto', 'Atividade', 'Localização']],
            width="stretch"
        )
    else:
        st.info(
            f"📋 Nenhum registro encontrado para {data_selecionada.strftime('%d/%m/%Y')}")


def historico_horas_extras_interface():
    """Interface completa de histórico de horas extras com filtros avançados"""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    ">
        <h2 style="margin: 0; color: white;">📊 Histórico Completo de Horas Extras</h2>
        <p style="margin: 10px 0;">Visualize todas as suas horas extras: ativas, aprovadas, rejeitadas e finalizadas</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filtros avançados
    st.markdown("### 🔍 Filtros")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filtro = st.multiselect(
            "Status",
            ["aguardando_aprovacao", "em_execucao", "encerrada", "rejeitada", "pendente", "aprovado", "rejeitado"],
            default=["aguardando_aprovacao", "em_execucao", "encerrada"]
        )
    
    with col2:
        data_inicio_filtro = st.date_input(
            "Data Início",
            value=date.today() - timedelta(days=30)
        )
    
    with col3:
        data_fim_filtro = st.date_input(
            "Data Fim",
            value=date.today()
        )
    
    # Buscar dados de ambas as tabelas
    horas_extras_completo = []
    
    if REFACTORING_ENABLED:
        try:
            # Buscar de horas_extras_ativas
            query_ativas = f"""
                SELECT 
                    'ativa' as origem,
                    id,
                    aprovador,
                    justificativa,
                    data_inicio,
                    hora_inicio,
                    status,
                    data_fim,
                    hora_fim,
                    tempo_decorrido_minutos,
                    data_criacao
                FROM horas_extras_ativas
                WHERE usuario = {SQL_PLACEHOLDER}
                AND data_inicio BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            """
            ativas = execute_query(query_ativas, (st.session_state.usuario, data_inicio_filtro, data_fim_filtro))
            
            # Buscar de solicitacoes_horas_extras
            query_historico = f"""
                SELECT 
                    'historico' as origem,
                    id,
                    aprovador_solicitado,
                    justificativa,
                    data,
                    hora_inicio,
                    status,
                    NULL as data_fim,
                    hora_fim,
                    NULL as tempo_decorrido,
                    data_solicitacao
                FROM solicitacoes_horas_extras
                WHERE usuario = {SQL_PLACEHOLDER}
                AND data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            """
            historico = execute_query(query_historico, (st.session_state.usuario, data_inicio_filtro, data_fim_filtro))
            
            # Combinar e filtrar por status
            for registro in (ativas or []) + (historico or []):
                origem, id_reg, aprovador, justificativa, data_reg, hora_inicio, status, data_fim, hora_fim, tempo_min, data_criacao = registro
                
                if status in status_filtro:
                    horas_extras_completo.append({
                        'origem': origem,
                        'id': id_reg,
                        'aprovador': aprovador,
                        'justificativa': justificativa,
                        'data': data_reg,
                        'hora_inicio': hora_inicio,
                        'status': status,
                        'data_fim': data_fim,
                        'hora_fim': hora_fim,
                        'tempo_minutos': tempo_min,
                        'data_criacao': data_criacao
                    })
            
            # Ordenar por data decrescente
            horas_extras_completo.sort(key=lambda x: x['data'], reverse=True)
            
        except Exception as e:
            log_error("Erro ao buscar histórico de horas extras", e, {"usuario": st.session_state.usuario})
            st.error(f"❌ Erro ao buscar histórico: {str(e)}")
            return
    else:
        # Fallback original
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Buscar de horas_extras_ativas
            cursor.execute(f"""
                SELECT 
                    'ativa' as origem,
                    id,
                    aprovador,
                    justificativa,
                    data_inicio,
                    hora_inicio,
                    status,
                    data_fim,
                    hora_fim,
                    tempo_decorrido_minutos,
                    data_criacao
                FROM horas_extras_ativas
                WHERE usuario = {SQL_PLACEHOLDER}
                AND data_inicio BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            """, (st.session_state.usuario, data_inicio_filtro, data_fim_filtro))
            
            ativas = cursor.fetchall()
            
            # Buscar de solicitacoes_horas_extras
            cursor.execute(f"""
                SELECT 
                    'historico' as origem,
                    id,
                    aprovador_solicitado,
                    justificativa,
                    data,
                    hora_inicio,
                    status,
                    NULL as data_fim,
                    hora_fim,
                    NULL as tempo_decorrido,
                    data_solicitacao
                FROM solicitacoes_horas_extras
                WHERE usuario = {SQL_PLACEHOLDER}
                AND data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            """, (st.session_state.usuario, data_inicio_filtro, data_fim_filtro))
            
            historico = cursor.fetchall()
            
            # Combinar e filtrar por status
            for registro in ativas + historico:
                origem, id_reg, aprovador, justificativa, data_reg, hora_inicio, status, data_fim, hora_fim, tempo_min, data_criacao = registro
                
                if status in status_filtro:
                    horas_extras_completo.append({
                        'origem': origem,
                        'id': id_reg,
                        'aprovador': aprovador,
                        'justificativa': justificativa,
                        'data': data_reg,
                        'hora_inicio': hora_inicio,
                        'status': status,
                        'data_fim': data_fim,
                        'hora_fim': hora_fim,
                        'tempo_minutos': tempo_min,
                        'data_criacao': data_criacao
                    })
            
            # Ordenar por data decrescente
            horas_extras_completo.sort(key=lambda x: x['data'], reverse=True)
            
        except Exception as e:
            st.error(f"❌ Erro ao buscar histórico: {str(e)}")
            logger.error(f"Erro em historico_horas_extras_interface: {str(e)}")
            return
        finally:
            if conn:
                _return_conn(conn)
    
    # Exibir resumo
    if horas_extras_completo:
        st.markdown("### 📈 Resumo do Período")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_horas = sum([r['tempo_minutos'] or 0 for r in horas_extras_completo if r['status'] in ['encerrada', 'aprovado']]) / 60
        aguardando = len([r for r in horas_extras_completo if r['status'] == 'aguardando_aprovacao'])
        em_execucao = len([r for r in horas_extras_completo if r['status'] == 'em_execucao'])
        finalizadas = len([r for r in horas_extras_completo if r['status'] in ['encerrada', 'aprovado']])
        
        with col1:
            st.metric("⏱️ Total de Horas", f"{total_horas:.1f}h")
        with col2:
            st.metric("⏳ Aguardando", aguardando)
        with col3:
            st.metric("▶️ Em Execução", em_execucao)
        with col4:
            st.metric("✅ Finalizadas", finalizadas)
        
        st.markdown("---")
        st.markdown(f"### 📋 Registros Encontrados ({len(horas_extras_completo)})")
        
        # Exibir registros em cards
        for he in horas_extras_completo:
            # Definir cor do card baseado no status
            if he['status'] == 'aguardando_aprovacao':
                bg_color = "#fff3cd"
                border_color = "#ffc107"
                icon = "⏳"
            elif he['status'] == 'em_execucao':
                bg_color = "#d1ecf1"
                border_color = "#17a2b8"
                icon = "▶️"
            elif he['status'] in ['encerrada', 'aprovado']:
                bg_color = "#d4edda"
                border_color = "#28a745"
                icon = "✅"
            else:
                bg_color = "#f8d7da"
                border_color = "#dc3545"
                icon = "❌"
            
            # Converter datas
            from calculo_horas_system import safe_datetime_parse
            data_obj = safe_datetime_parse(he['data']) if isinstance(he['data'], str) else he['data']
            data_formatada = data_obj.strftime('%d/%m/%Y') if data_obj else 'N/A'
            
            hora_inicio_obj = safe_datetime_parse(he['hora_inicio']) if isinstance(he['hora_inicio'], str) else he['hora_inicio']
            hora_inicio_formatada = hora_inicio_obj.strftime('%H:%M') if hora_inicio_obj else 'N/A'
            
            hora_fim_formatada = 'N/A'
            if he['hora_fim']:
                hora_fim_obj = safe_datetime_parse(he['hora_fim']) if isinstance(he['hora_fim'], str) else he['hora_fim']
                hora_fim_formatada = hora_fim_obj.strftime('%H:%M') if hora_fim_obj else 'N/A'
            
            tempo_texto = "Em andamento"
            if he['tempo_minutos']:
                horas = he['tempo_minutos'] // 60
                minutos = he['tempo_minutos'] % 60
                tempo_texto = f"{int(horas)}h {int(minutos)}min"
            
            st.markdown(f"""
            <div style="
                background: {bg_color};
                padding: 15px;
                border-radius: 8px;
                border-left: 5px solid {border_color};
                margin-bottom: 15px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #333;">{icon} {data_formatada} - {he['status'].replace('_', ' ').title()}</h4>
                    <span style="background: {border_color}; color: white; padding: 5px 10px; border-radius: 5px; font-size: 12px;">
                        {he['origem'].upper()}
                    </span>
                </div>
                <p style="margin: 10px 0; color: #666;">
                    <strong>⏰ Horário:</strong> {hora_inicio_formatada} {f'até {hora_fim_formatada}' if hora_fim_formatada != 'N/A' else ''}<br>
                    <strong>⏱️ Duração:</strong> {tempo_texto}<br>
                    <strong>👤 Aprovador:</strong> {he['aprovador'] if he['aprovador'] else 'Não definido'}<br>
                    <strong>💬 Justificativa:</strong> {he['justificativa'] if he['justificativa'] else 'Não informada'}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
    else:
        st.info("📋 Nenhum registro encontrado para os filtros selecionados")
    
    # Botão voltar
    if st.button("↩️ Voltar ao Menu", width="stretch"):
        st.rerun()


def horas_extras_interface(horas_extras_system):
    """Interface para solicitação e acompanhamento de horas extras"""
    st.markdown("""
    <div class="feature-card">
        <h3>🕐 Horas Extras</h3>
        <p>Solicite aprovação para horas extras trabalhadas</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Botão para acessar histórico completo
    if st.button("📊 Ver Histórico Completo", width="stretch", type="secondary"):
        st.session_state.ver_historico_completo = True
        st.rerun()
    
    # Se clicou em ver histórico, mostrar interface de histórico
    if st.session_state.get('ver_historico_completo'):
        historico_horas_extras_interface()
        # Botão para voltar
        if st.button("↩️ Voltar para Horas Extras"):
            del st.session_state.ver_historico_completo
            st.rerun()
        return

    tab1, tab2 = st.tabs(["📝 Nova Solicitação", "📋 Minhas Solicitações"])

    with tab1:
        st.subheader("📝 Solicitar Horas Extras")

        with st.form("solicitar_horas_extras"):
            col1, col2 = st.columns(2)

            with col1:
                data_horas_extras = st.date_input(
                    "📅 Data das Horas Extras",
                    value=date.today(),
                    max_value=date.today()
                )

                hora_inicio = st.time_input("🕐 Horário de Início")

            with col2:
                hora_fim = st.time_input("🕕 Horário de Fim")

                # Calcular horas automaticamente
                if hora_inicio and hora_fim:
                    inicio_dt = datetime.combine(date.today(), hora_inicio)
                    fim_dt = datetime.combine(date.today(), hora_fim)
                    if fim_dt <= inicio_dt:
                        fim_dt += timedelta(days=1)

                    total_horas = (fim_dt - inicio_dt).total_seconds() / 3600
                    st.info(
                        f"⏱️ Total de horas: {format_time_duration(total_horas)}")

            justificativa = st.text_area(
                "📝 Justificativa",
                placeholder="Explique o motivo das horas extras..."
            )

            # Seletor de aprovador
            aprovadores = obter_usuarios_para_aprovacao()
            aprovadores_opcoes = [
                f"{a['nome']} ({a['usuario']})" for a in aprovadores if a['usuario'] != st.session_state.usuario]

            aprovador_selecionado = st.selectbox(
                "👤 Selecionar Aprovador",
                aprovadores_opcoes,
                help="Escolha quem deve aprovar suas horas extras"
            )

            submitted = st.form_submit_button(
                "✅ Enviar Solicitação", width="stretch")

            if submitted:
                if not justificativa.strip():
                    st.error("❌ A justificativa é obrigatória")
                elif hora_inicio >= hora_fim:
                    st.error(
                        "❌ Horário de início deve ser anterior ao horário de fim")
                elif not aprovador_selecionado:
                    st.error("❌ Selecione um aprovador")
                else:
                    # Extrair usuário do aprovador selecionado
                    aprovador_usuario = aprovador_selecionado.split(
                        '(')[-1].replace(')', '')

                    resultado = horas_extras_system.solicitar_horas_extras(
                        usuario=st.session_state.usuario,
                        data=data_horas_extras.strftime("%Y-%m-%d"),
                        hora_inicio=hora_inicio.strftime("%H:%M"),
                        hora_fim=hora_fim.strftime("%H:%M"),
                        justificativa=justificativa,
                        aprovador_solicitado=aprovador_usuario
                    )

                    if resultado["success"]:
                        st.success(f"✅ {resultado['message']}")
                        st.info(
                            f"⏱️ Total de horas solicitadas: {format_time_duration(resultado['total_horas'])}")
                        st.rerun()
                    else:
                        st.error(f"❌ {resultado['message']}")

    with tab2:
        st.subheader("📋 Minhas Solicitações de Horas Extras")

        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            status_filtro = st.selectbox(
                "Status", ["Todos", "pendente", "aprovado", "rejeitado"])
        with col2:
            periodo = st.selectbox(
                "Período", ["Últimos 30 dias", "Últimos 7 dias", "Todos"])

        # Buscar solicitações
        solicitacoes = horas_extras_system.listar_solicitacoes_usuario(
            st.session_state.usuario,
            None if status_filtro == "Todos" else status_filtro
        )

        # Aplicar filtro de período
        if periodo != "Todos":
            dias = 7 if periodo == "Últimos 7 dias" else 30
            data_limite = (get_datetime_br() - timedelta(days=dias)).date()

            def parse_data_value(value):
                if isinstance(value, datetime):
                    return value.date()
                if isinstance(value, date):
                    return value
                try:
                    return safe_datetime_parse(value).date()
                except Exception:
                    try:
                        return datetime.strptime(str(value), "%Y-%m-%d").date()
                    except Exception:
                        return None

            solicitacoes = [
                s for s in solicitacoes
                if (parsed := parse_data_value(s["data"])) is not None and parsed >= data_limite
            ]

        if solicitacoes:
            for solicitacao in solicitacoes:
                with st.expander(f"{get_status_emoji(solicitacao['status'])} {solicitacao['data']} - {solicitacao['hora_inicio']} às {solicitacao['hora_fim']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Data:** {solicitacao['data']}")
                        st.write(
                            f"**Horário:** {solicitacao['hora_inicio']} às {solicitacao['hora_fim']}")
                        st.write(
                            f"**Aprovador:** {solicitacao['aprovador_solicitado']}")

                    with col2:
                        st.write(
                            f"**Status:** {solicitacao['status'].title()}")
                        st.write(
                            f"**Solicitado em:** {format_datetime_safe(solicitacao['data_solicitacao'], '%d/%m/%Y às %H:%M')}")
                        if solicitacao['aprovado_por']:
                            st.write(
                                f"**Processado por:** {solicitacao['aprovado_por']}")

                    if solicitacao['justificativa']:
                        st.write(
                            f"**Justificativa:** {solicitacao['justificativa']}")

                    if solicitacao['observacoes']:
                        st.write(
                            f"**Observações:** {solicitacao['observacoes']}")
        else:
            st.info("📋 Nenhuma solicitação de horas extras encontrada")


def minhas_horas_projeto_interface():
    """
    Interface para funcionário visualizar suas horas por projeto.
    Mostra distribuição percentual do tempo dedicado a cada projeto.
    """
    from horas_projeto_system import (
        HorasProjetoSystem,
        format_horas_projeto,
        format_percentual,
        get_cor_projeto
    )
    
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Minhas Horas por Projeto</h3>
        <p>Veja quanto tempo você dedicou a cada projeto</p>
    </div>
    """, unsafe_allow_html=True)
    
    horas_projeto_system = HorasProjetoSystem()
    usuario = st.session_state.usuario
    
    # Filtros de período
    st.markdown("### 📅 Selecione o Período")
    
    tipo_periodo = st.radio(
        "Tipo de período:",
        ["Mês atual", "Mês específico", "Período personalizado"],
        horizontal=True,
        key="mhp_tipo_periodo"
    )
    
    if tipo_periodo == "Mês atual":
        data_inicio = date.today().replace(day=1)
        data_fim = date.today()
    elif tipo_periodo == "Mês específico":
        col1, col2 = st.columns(2)
        with col1:
            anos = list(range(date.today().year, date.today().year - 2, -1))
            ano = st.selectbox("Ano:", anos, key="mhp_ano")
        with col2:
            meses = [
                (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
                (4, "Abril"), (5, "Maio"), (6, "Junho"),
                (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
                (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
            ]
            mes = st.selectbox(
                "Mês:",
                meses,
                format_func=lambda x: x[1],
                index=date.today().month - 1,
                key="mhp_mes"
            )[0]
        
        data_inicio = date(ano, mes, 1)
        if mes == 12:
            data_fim = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            data_fim = date(ano, mes + 1, 1) - timedelta(days=1)
    else:
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input(
                "Data início:",
                value=date.today().replace(day=1),
                key="mhp_data_inicio"
            )
        with col2:
            data_fim = st.date_input(
                "Data fim:",
                value=date.today(),
                key="mhp_data_fim"
            )
    
    st.markdown("---")
    
    # Buscar dados
    resultado = horas_projeto_system.calcular_horas_por_projeto_periodo(
        usuario=usuario,
        data_inicio=data_inicio.strftime('%Y-%m-%d'),
        data_fim=data_fim.strftime('%Y-%m-%d')
    )
    
    if resultado.get('success') and resultado.get('projetos'):
        projetos = resultado['projetos']
        total_horas = resultado.get('total_horas', 0)
        
        # Métricas principais
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Total de Horas", format_horas_projeto(total_horas))
        with col2:
            st.metric("📁 Projetos", len(projetos))
        with col3:
            dias_periodo = (data_fim - data_inicio).days + 1
            media_dia = total_horas / dias_periodo if dias_periodo > 0 else 0
            st.metric("📊 Média/Dia", format_horas_projeto(media_dia))
        
        st.markdown("---")
        st.markdown("### 🥧 Distribuição por Projeto")
        
        # Visualização com barras de progresso e percentuais
        for i, proj in enumerate(projetos):
            cor = get_cor_projeto(i)
            percentual = proj['percentual']
            horas = proj['horas']
            nome = proj['projeto']
            
            st.markdown(f"""
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: bold; font-size: 16px;">
                        <span style="color: {cor};">●</span> {nome}
                    </span>
                    <span style="font-size: 18px; font-weight: bold; color: {cor};">
                        {format_horas_projeto(horas)}
                    </span>
                </div>
                <div style="background-color: #e0e0e0; border-radius: 10px; height: 30px; overflow: hidden; position: relative;">
                    <div style="
                        background: linear-gradient(90deg, {cor}, {cor}cc);
                        width: {percentual}%;
                        height: 100%;
                        border-radius: 10px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: bold;
                        font-size: 14px;
                        text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                    ">
                        {format_percentual(percentual)}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Resumo em cards
        st.markdown("### 📋 Resumo")
        
        num_cols = min(len(projetos), 4)
        cols = st.columns(num_cols)
        
        for i, proj in enumerate(projetos[:num_cols]):
            with cols[i]:
                cor = get_cor_projeto(i)
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {cor}15, {cor}30);
                    border: 2px solid {cor};
                    border-radius: 12px;
                    padding: 15px;
                    text-align: center;
                ">
                    <h4 style="color: {cor}; margin: 0 0 10px 0; font-size: 14px;">{proj['projeto']}</h4>
                    <p style="font-size: 24px; font-weight: bold; margin: 0; color: #333;">{format_horas_projeto(proj['horas'])}</p>
                    <p style="font-size: 16px; color: {cor}; margin: 5px 0 0 0;">{format_percentual(proj['percentual'])}</p>
                </div>
                """, unsafe_allow_html=True)
        
        # Tabela detalhada
        st.markdown("---")
        with st.expander("📊 Ver tabela detalhada"):
            df = pd.DataFrame(projetos)
            df['Horas'] = df['horas'].apply(format_horas_projeto)
            df['Percentual'] = df['percentual'].apply(lambda x: f"{x:.1f}%")
            df = df.rename(columns={'projeto': 'Projeto'})
            
            st.dataframe(
                df[['Projeto', 'Horas', 'Percentual']],
                width="stretch",
                hide_index=True
            )
    else:
        st.info("📭 Nenhum registro de horas encontrado para o período selecionado.")
        st.markdown("""
        **Dicas:**
        - Verifique se você selecionou projetos ao registrar seu ponto
        - Tente selecionar um período diferente
        """)


def banco_horas_funcionario_interface(banco_horas_system):
    """Interface do banco de horas para funcionários"""
    st.markdown("""
    <div class="feature-card">
        <h3>🏦 Meu Banco de Horas</h3>
        <p>Acompanhe seu saldo de horas trabalhadas</p>
    </div>
    """, unsafe_allow_html=True)

    # Saldo atual
    saldo_atual = banco_horas_system.obter_saldo_atual(
        st.session_state.usuario)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Saldo Atual", format_saldo_display(saldo_atual))
    with col2:
        st.metric("📅 Período", "Ano Atual")
    with col3:
        if saldo_atual > 0:
            st.success("✅ Saldo Positivo")
        elif saldo_atual < 0:
            st.error("❌ Saldo Negativo")
        else:
            st.info("⚖️ Saldo Zerado")

    # Filtros para extrato
    st.subheader("📊 Extrato Detalhado")

    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input(
            "Data Início", value=date.today() - timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data Fim", value=date.today())

    # Calcular extrato
    resultado = banco_horas_system.calcular_banco_horas(
        st.session_state.usuario,
        data_inicio.strftime("%Y-%m-%d"),
        data_fim.strftime("%Y-%m-%d")
    )

    if resultado["success"] and resultado["extrato"]:
        # Resumo do período
        total_creditos = sum([item["credito"]
                             for item in resultado["extrato"]])
        total_debitos = sum([item["debito"] for item in resultado["extrato"]])
        saldo_periodo = total_creditos - total_debitos

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("➕ Créditos", format_time_duration(total_creditos))
        with col2:
            st.metric("➖ Débitos", format_time_duration(total_debitos))
        with col3:
            st.metric("💰 Saldo Período", format_saldo_display(saldo_periodo))

        # Tabela do extrato
        df_extrato = pd.DataFrame(resultado["extrato"])
        df_extrato["Crédito"] = df_extrato["credito"].apply(
            lambda x: f"+{format_time_duration(x)}" if x > 0 else "")
        df_extrato["Débito"] = df_extrato["debito"].apply(
            lambda x: f"-{format_time_duration(x)}" if x > 0 else "")
        df_extrato["Saldo Parcial"] = df_extrato["saldo_parcial"].apply(
            format_saldo_display)

        st.dataframe(
            df_extrato[["data", "descricao", "Crédito", "Débito", "Saldo Parcial"]].rename(columns={
                "data": "Data",
                "descricao": "Descrição"
            }),
            width="stretch"
        )

        # Botão de exportação
        if st.button("📊 Exportar Extrato"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_extrato.to_excel(
                    writer, sheet_name='Banco_Horas', index=False)

            safe_download_button(
                label="💾 Download Excel",
                data=output.getvalue(),
                file_name=f"banco_horas_{st.session_state.usuario}_{data_inicio}_{data_fim}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("📋 Nenhuma movimentação encontrada no período selecionado")


def notificacoes_interface(horas_extras_system):
    """Interface centralizada de notificações - mostra todas as pendências"""
    st.markdown("""
    <div class="feature-card">
        <h3>🔔 Central de Notificações</h3>
        <p>Todas as suas solicitações e aprovações pendentes</p>
    </div>
    """, unsafe_allow_html=True)

    # Contar notificações
    he_aprovar = 0
    correcoes_pendentes = 0
    atestados_pendentes = 0
    
    if REFACTORING_ENABLED:
        try:
            # Horas extras para aprovar
            result = execute_query(
                f"SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'",
                (st.session_state.usuario,),
                fetch_one=True
            )
            he_aprovar = result[0] if result else 0
            
            # Correções de registro pendentes
            result = execute_query(
                f"SELECT COUNT(*) FROM solicitacoes_correcao_registro WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'",
                (st.session_state.usuario,),
                fetch_one=True
            )
            correcoes_pendentes = result[0] if result else 0
            
            # Atestados pendentes
            result = execute_query(
                f"SELECT COUNT(*) FROM atestado_horas WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'",
                (st.session_state.usuario,),
                fetch_one=True
            )
            atestados_pendentes = result[0] if result else 0
        except Exception as e:
            log_error("Erro ao contar notificações", e, {"usuario": st.session_state.usuario})
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Contar notificações
            cursor.execute(f"""
                SELECT COUNT(*) FROM solicitacoes_horas_extras 
                WHERE aprovador_solicitado = {SQL_PLACEHOLDER} AND status = 'pendente'
            """, (st.session_state.usuario,))
            he_aprovar = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT COUNT(*) FROM solicitacoes_correcao_registro 
                WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
            """, (st.session_state.usuario,))
            correcoes_pendentes = cursor.fetchone()[0]

            cursor.execute(f"""
                SELECT COUNT(*) FROM atestado_horas 
                WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
            """, (st.session_state.usuario,))
            atestados_pendentes = cursor.fetchone()[0]

        finally:
            _return_conn(conn)
    
    total = he_aprovar + correcoes_pendentes + atestados_pendentes
    
    # Resumo
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total Pendente", total)
    with col2:
        st.metric("🕐 Horas Extras", he_aprovar)
    with col3:
        st.metric("🔧 Correções", correcoes_pendentes)
    with col4:
        st.metric("⏰ Atestados", atestados_pendentes)
    
    st.markdown("---")
    
    tabs = st.tabs(["🕐 Horas Extras para Aprovar", "🔧 Minhas Correções", "⏰ Meus Atestados"])
    
    # Tab 1: Horas Extras para Aprovar
    with tabs[0]:
        st.subheader("🕐 Solicitações de Horas Extras Aguardando Aprovação")
        
        solicitacoes_pendentes = horas_extras_system.listar_solicitacoes_para_aprovacao(
            st.session_state.usuario)

        if solicitacoes_pendentes:
            st.warning(
                f"⚠️ Você tem {len(solicitacoes_pendentes)} solicitação(ões) aguardando sua aprovação!")

            for solicitacao in solicitacoes_pendentes:
                with st.expander(f"⏳ {solicitacao['usuario']} - {solicitacao['data']} ({solicitacao['hora_inicio']} às {solicitacao['hora_fim']})"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**Funcionário:** {solicitacao['usuario']}")
                        st.write(f"**Data:** {solicitacao['data']}")
                        st.write(
                            f"**Horário:** {solicitacao['hora_inicio']} às {solicitacao['hora_fim']}")
                        st.write(
                            f"**Justificativa:** {solicitacao['justificativa']}")
                        ds_fmt = format_datetime_safe(solicitacao['data_solicitacao'], '%d/%m/%Y às %H:%M')
                        st.write(f"**Solicitado em:** {ds_fmt}")

                    with col2:
                        observacoes = st.text_area(
                            f"Observações", key=f"obs_notif_{solicitacao['id']}")

                        col_aprovar, col_rejeitar = st.columns(2)
                        with col_aprovar:
                            if st.button("✅ Aprovar", key=f"aprovar_notif_{solicitacao['id']}"):
                                resultado = horas_extras_system.aprovar_solicitacao(
                                    solicitacao['id'],
                                    st.session_state.usuario,
                                    observacoes
                                )
                                if resultado["success"]:
                                    st.success("✅ Solicitação aprovada!")
                                    st.rerun()
                                else:
                                    st.error(f"❌ {resultado['message']}")

                        with col_rejeitar:
                            if st.button("❌ Rejeitar", key=f"rejeitar_notif_{solicitacao['id']}", type="secondary"):
                                if observacoes.strip():
                                    resultado = horas_extras_system.rejeitar_solicitacao(
                                        solicitacao['id'],
                                        st.session_state.usuario,
                                        observacoes
                                    )
                                    if resultado["success"]:
                                        st.success("❌ Solicitação rejeitada!")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {resultado['message']}")
                                else:
                                    st.warning(
                                        "⚠️ Observações são obrigatórias para rejeição")
        else:
            st.info("✅ Nenhuma solicitação de horas extras aguardando sua aprovação")
    
    # Tab 2: Correções Pendentes
    with tabs[1]:
        st.subheader("🔧 Minhas Solicitações de Correção Pendentes")
        
        if REFACTORING_ENABLED:
            correcoes = execute_query(f"""
                SELECT id, registro_id, data_hora_original, data_hora_nova,
                       tipo_original, tipo_novo, justificativa, 
                       data_solicitacao
                FROM solicitacoes_correcao_registro
                WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                ORDER BY data_solicitacao DESC
            """, (st.session_state.usuario,))
        else:
            conn2 = get_connection()
            try:
                cursor2 = conn2.cursor()
                cursor2.execute(f"""
                    SELECT id, registro_id, data_hora_original, data_hora_nova,
                           tipo_original, tipo_novo, justificativa, 
                           data_solicitacao
                    FROM solicitacoes_correcao_registro
                    WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                    ORDER BY data_solicitacao DESC
                """, (st.session_state.usuario,))
                
                correcoes = cursor2.fetchall()
            finally:
                _return_conn(conn2)
        
        if correcoes:
            st.warning(f"⏳ Você tem {len(correcoes)} solicitação(ões) aguardando aprovação do gestor")
            
            for corr in correcoes:
                sol_id, reg_id, data_orig, data_nova, tipo_orig, tipo_novo, just, data_sol = corr
                
                with st.expander(f"⏳ {data_orig} → {data_nova}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Dados Originais:**")
                        st.write(f"- Data/Hora: {data_orig}")
                        st.write(f"- Tipo: {tipo_orig}")
                    
                    with col2:
                        st.write("**Correção Solicitada:**")
                        st.write(f"- Nova Data/Hora: {sanitize_ui_text(data_nova, default='-')}")
                        st.write(f"- Novo Tipo: {tipo_novo}")
                    
                    st.write(f"**Justificativa:** {sanitize_ui_text(just, default='Sem justificativa')}")
                    st.write(f"**Solicitado em:** {data_sol}")
                    st.info("⏳ Aguardando aprovação do gestor...")
        else:
            st.info("✅ Nenhuma correção aguardando aprovação")
    
    # Tab 3: Atestados Pendentes
    with tabs[2]:
        st.subheader("⏰ Meus Atestados de Horas Pendentes")
        
        if REFACTORING_ENABLED:
            atestados = execute_query(f"""
                SELECT id, data, hora_inicio, hora_fim, total_horas, motivo, 
                       arquivo_comprovante, data_registro
                FROM atestado_horas
                WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                ORDER BY data_registro DESC
            """, (st.session_state.usuario,))
        else:
            conn3 = get_connection()
            try:
                cursor3 = conn3.cursor()
                cursor3.execute(f"""
                    SELECT id, data, hora_inicio, hora_fim, total_horas, motivo, 
                           arquivo_comprovante, data_registro
                    FROM atestado_horas
                    WHERE usuario = {SQL_PLACEHOLDER} AND status = 'pendente'
                    ORDER BY data_registro DESC
                """, (st.session_state.usuario,))
                atestados = cursor3.fetchall()
            finally:
                _return_conn(conn3)
        
        if atestados:
            st.warning(f"⏳ Você tem {len(atestados)} atestado(s) aguardando aprovação do gestor")
            
            for at in atestados:
                at_id, data, h_inicio, h_fim, total_h, motivo, arquivo, data_reg = at
                
                with st.expander(f"⏳ {data} - {format_time_duration(total_h)}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Data:** {data}")
                        st.write(f"**Horário:** {h_inicio} às {h_fim}")
                        st.write(f"**Total:** {format_time_duration(total_h)}")
                    
                    with col2:
                        st.write(f"**Motivo:** {motivo}")
                        st.write(f"**Registrado em:** {data_reg}")
                        if arquivo:
                            st.write(f"**Comprovante:** ✅ Anexado")
                    
                    st.info("⏳ Aguardando aprovação do gestor...")
        else:
            st.info("✅ Nenhum atestado aguardando aprovação")

# Continuar com as outras interfaces...


def registrar_ausencia_interface(upload_system):
    """Interface para registrar ausências com opção 'não tenho comprovante'"""
    st.markdown("""
    <div class="feature-card">
        <h3>🏥 Registrar Ausência</h3>
        <p>Registre faltas, férias, atestados e outras ausências</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("ausencia_form"):
        col1, col2 = st.columns(2)

        with col1:
            data_inicio = st.date_input("📅 Data de Início")
            tipo_ausencia = st.selectbox(
                "📋 Tipo de Ausência",
                ["Atestado Médico", "Falta Justificada",
                    "Férias", "Licença", "Outros"]
            )

        with col2:
            data_fim = st.date_input("📅 Data de Fim", value=data_inicio)

        motivo = st.text_area("📝 Motivo da Ausência",
                              placeholder="Descreva o motivo da ausência...")

        # Checkbox para indicar que não possui comprovante
        nao_possui_comprovante = st.checkbox(
            "❌ Não possuo comprovante físico no momento",
            help="Marque se não houver documento para anexar agora"
        )
        
        # Upload de comprovante (se não marcou o checkbox)
        uploaded_file = None
        if not nao_possui_comprovante:
            uploaded_file = st.file_uploader(
                "📎 Anexar Comprovante (Atestado Médico, etc.)",
                type=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'],
                help="Tamanho máximo: 10MB"
            )
        else:
            st.warning(
                "⚠️ Ausência será registrada sem documento. "
                "Lembre-se de apresentar o comprovante assim que possível."
            )

        submitted = st.form_submit_button(
            "✅ Registrar Ausência", width="stretch")

    if submitted:
        if not motivo.strip():
            st.error("❌ O motivo é obrigatório")
        elif data_inicio > data_fim:
            st.error(
                "❌ Data de início deve ser anterior ou igual à data de fim")
        elif not nao_possui_comprovante and uploaded_file is None:
            st.error("❌ Você deve anexar um comprovante OU marcar a opção 'Não possuo comprovante físico no momento'")
        else:
            arquivo_comprovante = None
            
            # Se upload foi feito, processar arquivo
            if uploaded_file is not None:
                file_content = uploaded_file.read()
                upload_result = upload_system.save_file(
                    file_content=file_content,
                    usuario=st.session_state.usuario,
                    original_filename=uploaded_file.name,
                    categoria='ausencia',
                    relacionado_a='ausencia'
                )

                if upload_result["success"]:
                    arquivo_comprovante = upload_result["path"]
                else:
                    st.error(f"❌ Erro ao enviar comprovante: {upload_result['message']}")
                    return

            # Registrar ausência no banco
            try:
                if REFACTORING_ENABLED:
                    query = f"""
                        INSERT INTO ausencias 
                        (usuario, data_inicio, data_fim, tipo, motivo, arquivo_comprovante, nao_possui_comprovante)
                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                    """
                    execute_update(query, (
                        st.session_state.usuario,
                        data_inicio.strftime("%Y-%m-%d"),
                        data_fim.strftime("%Y-%m-%d"),
                        tipo_ausencia,
                        motivo,
                        arquivo_comprovante,
                        1 if nao_possui_comprovante else 0
                    ))
                    log_security_event("AUSENCIA_REGISTERED", usuario=st.session_state.usuario, context={"tipo": tipo_ausencia, "data_inicio": data_inicio.strftime("%Y-%m-%d")})
                else:
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()

                        cursor.execute(f"""
                            INSERT INTO ausencias 
                            (usuario, data_inicio, data_fim, tipo, motivo, arquivo_comprovante, nao_possui_comprovante)
                            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                        """, (
                            st.session_state.usuario,
                            data_inicio.strftime("%Y-%m-%d"),
                            data_fim.strftime("%Y-%m-%d"),
                            tipo_ausencia,
                            motivo,
                            arquivo_comprovante,
                            1 if nao_possui_comprovante else 0
                        ))

                        conn.commit()
                    finally:
                        _return_conn(conn)

                st.success("✅ Ausência registrada com sucesso!")

                if nao_possui_comprovante:
                    st.info(
                        "💡 Lembre-se de apresentar o comprovante assim que possível para regularizar sua situação.")

                st.rerun()

            except Exception as e:
                log_error("Erro ao registrar ausência", str(e), {"usuario": st.session_state.usuario})
                st.error(f"❌ Erro ao registrar ausência: {str(e)}")


def atestado_horas_interface(atestado_system, upload_system):
    """Interface para atestado de horas"""
    try:
        st.markdown("""
        <div class="feature-card">
            <h3>⏰ Atestado de Horas</h3>
            <p>Registre ausências parciais com horários específicos</p>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["📝 Novo Atestado", "📋 Meus Atestados"])

        with tab1:
            st.subheader("📝 Registrar Novo Atestado de Horas")

            with st.form("atestado_horas_form"):
                col1, col2 = st.columns(2)

                with col1:
                    data_atestado = st.date_input("📅 Data da Ausência")
                    hora_inicio_input = st.text_input(
                        "⏰ Horário de Início da Ausência",
                        value="08:00",
                        help="Digite no formato HH:MM (ex: 08:30)"
                    )

                with col2:
                    st.write("")  # Espaçamento
                    st.write("")  # Espaçamento
                    hora_fim_input = st.text_input(
                        "⏰ Horário de Fim da Ausência",
                        value="12:00",
                        help="Digite no formato HH:MM (ex: 17:30)"
                    )

                st.warning("⚠️ Digite horários válidos no formato HH:MM")

                motivo = st.text_area("📝 Motivo da Ausência",
                                      placeholder="Descreva o motivo da ausência...")

                # Upload de comprovante (opcional)
                st.markdown("📎 **Comprovante**")
                
                # Checkbox para indicar que não possui atestado físico
                nao_possui_comprovante = st.checkbox(
                    "❌ Não possuo atestado físico no momento",
                    help="Marque se não houver documento para anexar agora"
                )
                
                # Mostrar upload apenas se NÃO marcou o checkbox
                uploaded_file = None
                if not nao_possui_comprovante:
                    uploaded_file = st.file_uploader(
                        "Anexe um comprovante (atestado médico, declaração, etc.)",
                        type=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx'],
                        help="Tamanho máximo: 10MB"
                    )
                else:
                    st.warning(
                        "⚠️ Atestado será registrado sem documento. "
                        "O gestor receberá notificação para análise. "
                        "As horas podem ser lançadas como débito no banco de horas até apresentação do comprovante."
                    )

                submitted = st.form_submit_button(
                    "✅ Registrar Atestado", width="stretch")

            if submitted:
                if not motivo.strip():
                    st.error("❌ O motivo é obrigatório")
                elif not nao_possui_comprovante and uploaded_file is None:
                    st.error("❌ Você deve anexar um comprovante OU marcar a opção 'Não possuo atestado físico no momento'")
                else:
                    # Validar formato de hora
                    try:
                        hora_inicio_time = datetime.strptime(hora_inicio_input, "%H:%M").time()
                        hora_fim_time = datetime.strptime(hora_fim_input, "%H:%M").time()
                        
                        if hora_inicio_time >= hora_fim_time:
                            st.error("❌ Horário de início deve ser anterior ao horário de fim")
                        else:
                            arquivo_comprovante = None
                            
                            # Processar upload se houver e se não marcou nao_possui_comprovante
                            if uploaded_file and not nao_possui_comprovante:
                                upload_result = upload_system.save_file(
                                    file_content=uploaded_file.read(),
                                    usuario=st.session_state.usuario,
                                    original_filename=uploaded_file.name,
                                    categoria='atestado_horas',
                                    relacionado_a='atestado_horas'
                                )

                                if upload_result["success"]:
                                    arquivo_comprovante = upload_result["path"]
                                    st.success(
                                        f"📎 Arquivo enviado: {uploaded_file.name}")
                                else:
                                    st.error(
                                        f"❌ Erro no upload: {upload_result['message']}")
                                    return

                            # Registrar atestado
                            resultado = atestado_system.registrar_atestado_horas(
                                usuario=st.session_state.usuario,
                                data=data_atestado.strftime("%Y-%m-%d"),
                                hora_inicio=hora_inicio_input,
                                hora_fim=hora_fim_input,
                                motivo=motivo,
                                arquivo_comprovante=arquivo_comprovante,
                                nao_possui_comprovante=1 if 'nao_possui_comprovante' in locals(
                                ) and nao_possui_comprovante else 0
                            )

                            if resultado["success"]:
                                st.success(f"✅ {resultado['message']}")
                                st.info(
                                    f"⏱️ Total de horas registradas: {format_time_duration(resultado['total_horas'])}")
                                st.rerun()
                            else:
                                st.error(f"❌ {resultado['message']}")
                    except ValueError:
                        st.error("❌ Formato de hora inválido. Use HH:MM (ex: 08:30)")

        with tab2:
            st.subheader("📋 Meus Atestados de Horas")

            # Filtros
            col1, col2, col3 = st.columns(3)
            with col1:
                data_inicio = st.date_input(
                    "Data Início", value=date.today() - timedelta(days=30))
            with col2:
                data_fim = st.date_input("Data Fim", value=date.today())
            with col3:
                status_filtro = st.selectbox(
                    "Status", ["Todos", "pendente", "aprovado", "rejeitado"])

            # Buscar atestados
            atestados = atestado_system.listar_atestados_usuario(
                st.session_state.usuario
            )

            if status_filtro != "Todos":
                atestados = [
                    a for a in atestados if a["status"] == status_filtro]

            if atestados:
                for atestado in atestados:
                    with st.expander(f"{get_status_emoji(atestado['status'])} {atestado['data']} - {format_time_duration(atestado['total_horas'])}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Data:** {atestado['data']}")
                            st.write(
                                f"**Horário:** {atestado['hora_inicio']} às {atestado['hora_fim']}")
                            st.write(
                                f"**Total:** {format_time_duration(atestado['total_horas'])}")

                        with col2:
                            st.write(
                                f"**Status:** {atestado['status'].title()}")
                            if atestado['aprovado_por']:
                                st.write(
                                    f"**Aprovado por:** {atestado['aprovado_por']}")
                            if atestado['data_aprovacao']:
                                data_aprovacao = atestado['data_aprovacao']
                                if isinstance(data_aprovacao, datetime):
                                    data_aprovacao_fmt = data_aprovacao.strftime('%d/%m/%Y %H:%M')
                                elif isinstance(data_aprovacao, date):
                                    data_aprovacao_fmt = data_aprovacao.strftime('%d/%m/%Y')
                                else:
                                    data_aprovacao_fmt = str(data_aprovacao)[:16]
                                st.write(
                                    f"**Data aprovação:** {data_aprovacao_fmt}")

                        if atestado['motivo']:
                            st.write(f"**Motivo:** {atestado['motivo']}")

                        if atestado['observacoes']:
                            st.write(
                                f"**Observações:** {atestado['observacoes']}")

                        if atestado['arquivo_comprovante']:
                            st.write(
                                f"📎 **Comprovante:** {atestado['arquivo_comprovante']}")
            else:
                st.info(
                    "📋 Nenhum atestado de horas encontrado no período selecionado")
    except Exception as e:
        st.error(f"❌ Erro na página de atestado de horas: {str(e)}")
        st.code(str(e))


def solicitar_correcao_registro_interface():
    """Interface para funcionários solicitarem correção de registros"""
    st.markdown("""
    <div class="feature-card">
        <h3>🔧 Solicitar Correção de Registro</h3>
        <p>Solicite correção de um registro de ponto incorreto</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📝 Nova Solicitação", "📋 Minhas Solicitações"])

    with tab1:
        st.subheader("📝 Solicitar Correção")

        data_corrigir = st.date_input(
            "📅 Data do Registro a Corrigir",
            value=date.today(),
            max_value=date.today()
        )

        usuario_logado = st.session_state.usuario
        data_ref_str = data_corrigir.strftime("%Y-%m-%d")
        registros = buscar_registros_dia(usuario_logado, data_ref_str)

        if len(registros) > 1:
            registro_opcoes = [f"{r['data_hora']} - {r['tipo']}" for r in registros]
            registro_selecionado = st.selectbox("⏰ Selecione o Registro", registro_opcoes)
            idx = registro_opcoes.index(registro_selecionado)
            registro = registros[idx]

            with st.form("solicitar_correcao"):
                st.markdown("### 📝 Dados Atuais")
                col1, col2 = st.columns(2)

                with col1:
                    st.info(f"**Data/Hora:** {registro['data_hora']}")
                    st.info(f"**Tipo:** {registro['tipo']}")

                with col2:
                    st.info(f"**Modalidade:** {registro['modalidade'] or 'N/A'}")
                    st.info(f"**Projeto:** {registro['projeto'] or 'N/A'}")

                st.markdown("### ✏️ Correção Solicitada")
                col1, col2 = st.columns(2)

                with col1:
                    if isinstance(registro['data_hora'], str):
                        data_hora_obj = safe_datetime_parse(registro['data_hora'])
                    else:
                        data_hora_obj = registro['data_hora']
                    data_hora_obj = data_hora_obj or datetime.combine(data_corrigir, time(8, 0))

                    nova_data = st.date_input("📅 Nova Data", value=data_hora_obj.date())
                    nova_hora_input = st.text_input(
                        "🕐 Nova Hora (HH:MM)",
                        value=data_hora_obj.strftime("%H:%M"),
                        help="Digite no formato HH:MM (ex: 08:30, 14:45)"
                    )

                    tipo_mapeamento = {
                        'Início': 'inicio',
                        'Intermediário': 'intermediario',
                        'Fim': 'fim',
                        'inicio': 'inicio',
                        'intermediario': 'intermediario',
                        'fim': 'fim'
                    }
                    tipo_atual = tipo_mapeamento.get(registro['tipo'], 'inicio')
                    tipos_opcoes = ["inicio", "intermediario", "fim"]
                    novo_tipo = st.selectbox("📋 Novo Tipo", tipos_opcoes, index=tipos_opcoes.index(tipo_atual))

                with col2:
                    modalidade_mapeamento = {
                        'Presencial': 'presencial',
                        'Home Office': 'home_office',
                        'Campo': 'campo',
                        'presencial': 'presencial',
                        'home_office': 'home_office',
                        'campo': 'campo',
                        None: '',
                        '': ''
                    }
                    modalidade_atual = modalidade_mapeamento.get(registro['modalidade'], '')
                    modalidades_opcoes = ["", "presencial", "home_office", "campo"]
                    nova_modalidade = st.selectbox(
                        "🏢 Nova Modalidade",
                        modalidades_opcoes,
                        index=modalidades_opcoes.index(modalidade_atual)
                    )

                    projetos = obter_projetos_ativos()
                    novo_projeto = st.selectbox(
                        "📊 Novo Projeto",
                        [""] + projetos,
                        index=(projetos.index(registro['projeto']) + 1) if registro['projeto'] in projetos else 0
                    )

                justificativa = st.text_area(
                    "📝 Justificativa da Correção *",
                    placeholder="Explique detalhadamente por que este registro precisa ser corrigido...",
                    help="Campo obrigatório"
                )

                submitted = st.form_submit_button("✅ Enviar Solicitação", width="stretch")
                if submitted:
                    if not justificativa.strip():
                        st.error("❌ A justificativa é obrigatória")
                    else:
                        try:
                            datetime.strptime(nova_hora_input, "%H:%M")
                            nova_data_hora = f"{nova_data.strftime('%Y-%m-%d')} {nova_hora_input}:00"
                            conn = get_connection()
                            try:
                                cursor = conn.cursor()
                                solicitacao_duplicada_id = existe_solicitacao_correcao_pendente_cursor(
                                    cursor,
                                    usuario=usuario_logado,
                                    registro_id=registro['id'],
                                    data_hora_original=registro['data_hora'],
                                    data_hora_nova=nova_data_hora,
                                    tipo_solicitacao='ajuste_registro',
                                )
                                if solicitacao_duplicada_id:
                                    st.warning("⚠️ Já existe uma solicitação pendente idêntica para este registro.")
                                    return
                                try:
                                    cursor.execute(f"""
                                        INSERT INTO solicitacoes_correcao_registro
                                        (usuario, registro_id, data_hora_original, data_hora_nova,
                                         tipo_original, tipo_novo, modalidade_original, modalidade_nova,
                                         projeto_original, projeto_novo, tipo_solicitacao,
                                         data_referencia, hora_inicio_solicitada, hora_saida_solicitada,
                                         justificativa, status)
                                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                                {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                                {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'ajuste_registro',
                                                {SQL_PLACEHOLDER}, NULL, NULL, {SQL_PLACEHOLDER}, 'pendente')
                                    """, (
                                        usuario_logado,
                                        registro['id'],
                                        registro['data_hora'],
                                        nova_data_hora,
                                        registro['tipo'],
                                        novo_tipo,
                                        registro['modalidade'],
                                        nova_modalidade if nova_modalidade else None,
                                        registro['projeto'],
                                        novo_projeto if novo_projeto else None,
                                        nova_data.strftime("%Y-%m-%d"),
                                        justificativa.strip(),
                                    ))
                                except Exception as insert_exc:
                                    if not _is_missing_column_error(insert_exc):
                                        raise
                                    conn.rollback()
                                    cursor.execute(f"""
                                        INSERT INTO solicitacoes_correcao_registro
                                        (usuario, registro_id, data_hora_original, data_hora_nova,
                                         tipo_original, tipo_novo, modalidade_original, modalidade_nova,
                                         projeto_original, projeto_novo, justificativa, status)
                                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                                {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                                {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'pendente')
                                    """, (
                                        usuario_logado,
                                        registro['id'],
                                        registro['data_hora'],
                                        nova_data_hora,
                                        registro['tipo'],
                                        novo_tipo,
                                        registro['modalidade'],
                                        nova_modalidade if nova_modalidade else None,
                                        registro['projeto'],
                                        novo_projeto if novo_projeto else None,
                                        justificativa.strip(),
                                    ))
                                conn.commit()
                            finally:
                                _return_conn(conn)

                            log_security_event(
                                "CORRECAO_REGISTRO_REQUESTED",
                                usuario=usuario_logado,
                                context={"registro_id": registro['id'], "data_solicacao": nova_data_hora}
                            )
                            st.success("✅ Solicitação enviada com sucesso! Aguarde aprovação do gestor.")
                            st.rerun()
                        except ValueError:
                            st.error("❌ Formato de hora inválido. Use HH:MM (ex: 08:30)")
                        except Exception as e:
                            st.error(f"❌ Erro ao enviar solicitação: {str(e)}")

        else:
            unico_registro = registros[0] if len(registros) == 1 else None
            if unico_registro:
                st.warning("⚠️ Este dia possui apenas um registro. Informe início e saída para solicitar complemento.")
            else:
                st.info("📋 Nenhum registro encontrado no dia. Você pode solicitar a criação de início e saída.")

            default_inicio = time(8, 0)
            default_saida = time(17, 0)
            if unico_registro:
                dt_unico = safe_datetime_parse(unico_registro.get('data_hora'))
                tipo_unico = str(unico_registro.get('tipo') or '').strip().lower()
                if dt_unico:
                    if tipo_unico in ('início', 'inicio', 'entrada'):
                        default_inicio = dt_unico.time().replace(second=0, microsecond=0)
                    elif tipo_unico in ('fim', 'saída', 'saida'):
                        default_saida = dt_unico.time().replace(second=0, microsecond=0)

            modalidade_original = unico_registro['modalidade'] if unico_registro else None
            projeto_original = unico_registro['projeto'] if unico_registro else None

            with st.form("solicitar_correcao_complemento"):
                st.markdown("### 🧩 Complemento de Jornada")
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    hora_inicio_txt = st.text_input("🕐 Hora de início (HH:MM)", value=default_inicio.strftime("%H:%M"))
                with col_h2:
                    hora_saida_txt = st.text_input("🕕 Hora de saída (HH:MM)", value=default_saida.strftime("%H:%M"))

                col_m1, col_m2 = st.columns(2)
                modalidades_comp = ["presencial", "home_office", "campo"]
                modalidade_default = (
                    str(modalidade_original or "").strip().lower()
                    if unico_registro else ""
                )
                if modalidade_default not in modalidades_comp:
                    modalidade_default = "presencial"

                projetos_comp = obter_projetos_ativos()
                projeto_default = projeto_original if unico_registro else None
                if not projeto_default and projetos_comp:
                    projeto_default = projetos_comp[0]

                with col_m1:
                    modalidade_complemento = st.selectbox(
                        "🏢 Modalidade de trabalho *",
                        modalidades_comp,
                        index=modalidades_comp.index(modalidade_default),
                    )
                with col_m2:
                    projeto_complemento = st.selectbox(
                        "📊 Projeto *",
                        projetos_comp if projetos_comp else [""],
                        index=(projetos_comp.index(projeto_default) if (projetos_comp and projeto_default in projetos_comp) else 0),
                    )

                justificativa = st.text_area(
                    "📝 Justificativa da Correção *",
                    placeholder="Explique por que precisa completar/criar os registros deste dia...",
                    help="Campo obrigatório"
                )

                submitted_comp = st.form_submit_button("✅ Enviar Solicitação", width="stretch")
                if submitted_comp:
                    if not justificativa.strip():
                        st.error("❌ A justificativa é obrigatória")
                    elif not projeto_complemento:
                        st.error("❌ Selecione um projeto para o complemento")
                    else:
                        try:
                            hora_inicio = _parse_hhmm_or_raise(hora_inicio_txt, "Hora de inicio")
                            hora_saida = _parse_hhmm_or_raise(hora_saida_txt, "Hora de saida")
                        except ValueError as hora_err:
                            st.error(f"❌ {hora_err}")
                            return

                        dt_inicio = datetime.combine(data_corrigir, hora_inicio)
                        dt_saida = datetime.combine(data_corrigir, hora_saida)
                        if dt_saida <= dt_inicio:
                            st.error("❌ A hora de saída deve ser maior que a hora de início")
                        else:
                            registro_id_ref = unico_registro['id'] if unico_registro else 0
                            data_hora_original = unico_registro['data_hora'] if unico_registro else datetime.combine(data_corrigir, time(0, 0))
                            tipo_original = unico_registro['tipo'] if unico_registro else None

                            conn = get_connection()
                            try:
                                cursor = conn.cursor()
                                solicitacao_duplicada_id = existe_solicitacao_correcao_pendente_cursor(
                                    cursor,
                                    usuario=usuario_logado,
                                    registro_id=registro_id_ref,
                                    data_hora_original=data_hora_original,
                                    data_hora_nova=dt_inicio,
                                    tipo_solicitacao='complemento_jornada',
                                    data_referencia=data_ref_str,
                                    hora_inicio=hora_inicio.strftime("%H:%M"),
                                    hora_saida=hora_saida.strftime("%H:%M"),
                                )
                                if solicitacao_duplicada_id:
                                    st.warning("⚠️ Já existe uma solicitação pendente idêntica para este dia.")
                                    return
                                cursor.execute(f"""
                                    INSERT INTO solicitacoes_correcao_registro
                                    (usuario, registro_id, data_hora_original, data_hora_nova,
                                     tipo_original, tipo_novo, modalidade_original, modalidade_nova,
                                     projeto_original, projeto_novo, tipo_solicitacao,
                                     data_referencia, hora_inicio_solicitada, hora_saida_solicitada,
                                     justificativa, status)
                                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                            {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                            {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'complemento_jornada',
                                            {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'pendente')
                                """, (
                                    usuario_logado,
                                    registro_id_ref,
                                    data_hora_original,
                                    dt_inicio,
                                    tipo_original,
                                    'inicio_e_fim',
                                    modalidade_original,
                                    modalidade_complemento,
                                    projeto_original,
                                    projeto_complemento,
                                    data_ref_str,
                                    hora_inicio.strftime("%H:%M"),
                                    hora_saida.strftime("%H:%M"),
                                    justificativa.strip(),
                                ))
                                conn.commit()
                            except Exception as e:
                                if _is_missing_column_error(e):
                                    conn.rollback()
                                    if _try_upgrade_correcao_schema(conn):
                                        try:
                                            cursor = conn.cursor()
                                            cursor.execute(f"""
                                                INSERT INTO solicitacoes_correcao_registro
                                                (usuario, registro_id, data_hora_original, data_hora_nova,
                                                 tipo_original, tipo_novo, modalidade_original, modalidade_nova,
                                                 projeto_original, projeto_novo, tipo_solicitacao,
                                                 data_referencia, hora_inicio_solicitada, hora_saida_solicitada,
                                                 justificativa, status)
                                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                                        {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER},
                                                        {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'complemento_jornada',
                                                        {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'pendente')
                                            """, (
                                                usuario_logado,
                                                registro_id_ref,
                                                data_hora_original,
                                                dt_inicio,
                                                tipo_original,
                                                'inicio_e_fim',
                                                modalidade_original,
                                                modalidade_complemento,
                                                projeto_original,
                                                projeto_complemento,
                                                data_ref_str,
                                                hora_inicio.strftime("%H:%M"),
                                                hora_saida.strftime("%H:%M"),
                                                justificativa.strip(),
                                            ))
                                            conn.commit()
                                        except Exception as retry_exc:
                                            log_error("Erro ao reenviar complemento apos migracao", retry_exc, {"usuario": usuario_logado})
                                            raise
                                    else:
                                        st.error("❌ O banco de produção ainda não foi migrado para complemento de jornada. Contate o suporte.")
                                        log_error("Schema desatualizado para complemento de jornada", e, {"usuario": usuario_logado})
                                        return
                                else:
                                    raise
                            finally:
                                _return_conn(conn)

                            log_security_event(
                                "CORRECAO_REGISTRO_COMPLEMENTO_REQUESTED",
                                usuario=usuario_logado,
                                context={
                                    "data_referencia": data_ref_str,
                                    "hora_inicio": hora_inicio.strftime("%H:%M"),
                                    "hora_saida": hora_saida.strftime("%H:%M"),
                                    "modalidade": modalidade_complemento,
                                    "projeto": projeto_complemento,
                                }
                            )
                            st.success("✅ Solicitação enviada com sucesso! Aguarde aprovação do gestor.")
                            st.rerun()

    with tab2:
        st.subheader("📋 Minhas Solicitações de Correção")
        
        solicitacoes = None
        conn = get_connection()
        try:
            cursor = conn.cursor()
            solicitacoes = _execute_select_with_legacy_fallback(
                cursor,
                f"""
                    SELECT id, registro_id, data_hora_original, data_hora_nova,
                           tipo_original, tipo_novo, justificativa, status,
                           data_solicitacao, aprovado_por, data_aprovacao, observacoes,
                           COALESCE(tipo_solicitacao, 'ajuste_registro'), data_referencia,
                           hora_inicio_solicitada, hora_saida_solicitada
                    FROM solicitacoes_correcao_registro
                    WHERE usuario = {SQL_PLACEHOLDER}
                    ORDER BY data_solicitacao DESC
                    LIMIT 50
                """,
                (st.session_state.usuario,),
                legacy_query=f"""
                    SELECT id, registro_id, data_hora_original, data_hora_nova,
                           tipo_original, tipo_novo, justificativa, status,
                           data_solicitacao, aprovado_por, data_aprovacao, observacoes
                    FROM solicitacoes_correcao_registro
                    WHERE usuario = {SQL_PLACEHOLDER}
                    ORDER BY data_solicitacao DESC
                    LIMIT 50
                """,
                legacy_suffix=('ajuste_registro', None, None, None),
            )
        except Exception as e:
            log_error("Erro ao buscar solicitações de correção", e, {"usuario": st.session_state.usuario})
            solicitacoes = []
        finally:
            _return_conn(conn)
        
        if solicitacoes:
            for sol in solicitacoes:
                (sol_id, reg_id, data_orig, data_nova, tipo_orig, tipo_novo, just, status,
                 data_sol, aprov_por, data_aprov, obs, tipo_solicitacao, data_referencia,
                 hora_inicio_sol, hora_saida_sol) = sol
                
                status_emoji = {
                    'pendente': '⏳',
                    'aprovado': '✅',
                    'rejeitado': '❌'
                }.get(status, '❓')
                
                if tipo_solicitacao == 'complemento_jornada':
                    titulo = f"{status_emoji} {data_referencia} - Complemento de Jornada - {status.upper()}"
                else:
                    titulo = f"{status_emoji} {data_orig} → {data_nova} - {status.upper()}"

                with st.expander(titulo):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Dados Originais:**")
                        st.write(f"- Data/Hora: {data_orig}")
                        st.write(f"- Tipo: {tipo_orig}")

                    with col2:
                        st.write("**Correção Solicitada:**")
                        if tipo_solicitacao == 'complemento_jornada':
                            st.write(f"- Data: {data_referencia}")
                            st.write(f"- Hora início: {hora_inicio_sol}")
                            st.write(f"- Hora saída: {hora_saida_sol}")
                        else:
                            st.write(f"- Nova Data/Hora: {sanitize_ui_text(data_nova, default='-')}")
                            st.write(f"- Novo Tipo: {tipo_novo}")
                    
                    st.write(f"**Justificativa:** {sanitize_ui_text(just, default='Sem justificativa')}")
                    st.write(f"**Solicitado em:** {data_sol}")
                    
                    if status != 'pendente':
                        st.write(f"**Aprovado por:** {aprov_por or 'N/A'}")
                        st.write(f"**Data aprovação:** {data_aprov or 'N/A'}")
                        if obs:
                            st.write(f"**Observações:** {obs}")
        else:
            st.info("📋 Você ainda não fez nenhuma solicitação de correção")


def corrigir_registros_interface():
    """Interface para gestores corrigirem registros de ponto dos funcionários"""
    st.markdown("""
    <div class="feature-card">
        <h3>🔧 Corrigir Registros de Ponto</h3>
        <p>Edite registros de ponto dos funcionários quando necessário</p>
    </div>
    """, unsafe_allow_html=True)

    # Mostrar toda a fila de pendências para o gestor tratar todas de uma vez.
    # Inclui schema novo (complemento_jornada) com fallback para schema legado.
    pendencias = []
    conn_pend = get_connection()
    try:
        cur_pend = conn_pend.cursor()
        pendencias = _execute_select_with_legacy_fallback(
            cur_pend,
            """
                SELECT c.id, c.registro_id, c.usuario, c.data_hora_original, c.data_hora_nova,
                       c.justificativa, c.data_solicitacao, u.nome_completo,
                       COALESCE(c.tipo_solicitacao, 'ajuste_registro'), c.data_referencia,
                       c.hora_inicio_solicitada, c.hora_saida_solicitada
                FROM solicitacoes_correcao_registro c
                LEFT JOIN usuarios u ON c.usuario = u.usuario
                WHERE c.status = 'pendente'
                ORDER BY c.data_solicitacao DESC
                LIMIT 200
            """,
            (),
            legacy_query="""
                SELECT c.id, c.registro_id, c.usuario, c.data_hora_original, c.data_hora_nova,
                       c.justificativa, c.data_solicitacao, u.nome_completo
                FROM solicitacoes_correcao_registro c
                LEFT JOIN usuarios u ON c.usuario = u.usuario
                WHERE c.status = 'pendente'
                ORDER BY c.data_solicitacao DESC
                LIMIT 200
            """,
            legacy_suffix=('ajuste_registro', None, None, None),
        ) or []
    except Exception as e:
        logger.debug("Falha ao carregar pendências de correção: %s", e)
    finally:
        _return_conn(conn_pend)

    if pendencias:
        # Deduplicar pendências idênticas (mantém a mais recente por combinação lógica).
        dedup = {}
        for pend in pendencias:
            (pend_id, pend_registro_id, pend_usuario, pend_dt_orig, pend_dt_nova,
             pend_just, pend_data_sol, pend_nome, pend_tipo_solicitacao,
             pend_data_referencia, pend_hora_inicio, pend_hora_saida) = pend
            key = (
                str(pend_usuario or "").strip().lower(),
                int(pend_registro_id or 0),
                str(pend_dt_orig or ""),
                str(pend_dt_nova or ""),
                str(pend_tipo_solicitacao or ""),
                str(pend_data_referencia or ""),
                str(pend_hora_inicio or ""),
                str(pend_hora_saida or ""),
            )
            anterior = dedup.get(key)
            if not anterior or (safe_datetime_parse(pend_data_sol) or datetime.min) > (safe_datetime_parse(anterior[6]) or datetime.min):
                dedup[key] = pend
        pendencias = list(dedup.values())

        st.markdown(f"### 📬 Pendências Abertas ({len(pendencias)})")
        for pend in pendencias:
            (pend_id, pend_registro_id, pend_usuario, pend_dt_orig, pend_dt_nova,
             pend_just, pend_data_sol, pend_nome, pend_tipo_solicitacao,
             pend_data_referencia, pend_hora_inicio, pend_hora_saida) = pend
            if pend_tipo_solicitacao == 'complemento_jornada':
                titulo = f"⏳ {pend_nome or pend_usuario} - {pend_data_referencia} (Entrada/Saida)"
            else:
                titulo = f"⏳ {pend_nome or pend_usuario} - {format_datetime_safe(pend_dt_orig, '%d/%m/%Y %H:%M')}"
            with st.expander(titulo):
                st.markdown(f"**Solicitado em:** {format_datetime_safe(pend_data_sol, '%d/%m/%Y %H:%M')}")
                if pend_tipo_solicitacao == 'complemento_jornada':
                    st.markdown(f"**Tipo:** Complemento de jornada")
                    st.markdown(f"**Data:** `{pend_data_referencia}`")
                    st.markdown(f"**Entrada solicitada:** `{pend_hora_inicio or '-'}`")
                    st.markdown(f"**Saida solicitada:** `{pend_hora_saida or '-'}`")
                else:
                    st.markdown(
                        f"**Alteração:** `{format_datetime_safe(pend_dt_orig, '%d/%m/%Y %H:%M')}` → `{format_datetime_safe(pend_dt_nova, '%d/%m/%Y %H:%M')}`"
                    )
                st.markdown(f"**Justificativa:** {sanitize_ui_text(pend_just, default='Sem justificativa')}")
                if st.button("Abrir para corrigir", key=f"abrir_pend_corr_{pend_id}"):
                    st.session_state.pendencia_usuario_prefill = pend_usuario
                    st.session_state.pendencia_correcao_id_prefill = pend_id
                    st.session_state.pendencia_registro_id_prefill = pend_registro_id
                    st.session_state.pendencia_tipo_solicitacao_prefill = pend_tipo_solicitacao
                    st.session_state.pendencia_data_referencia_prefill = str(pend_data_referencia) if pend_data_referencia else ""
                    st.session_state.pendencia_hora_inicio_prefill = str(pend_hora_inicio) if pend_hora_inicio else ""
                    st.session_state.pendencia_hora_saida_prefill = str(pend_hora_saida) if pend_hora_saida else ""
                    st.session_state.pendencia_datahora_original_prefill = str(pend_dt_orig) if pend_dt_orig else ""
                    st.session_state.pendencia_datahora_nova_prefill = str(pend_dt_nova) if pend_dt_nova else ""
                    st.session_state.pendencia_justificativa_prefill = sanitize_ui_text(pend_just, default="Sem justificativa")
                    dt_pref = safe_datetime_parse(pend_data_referencia) or safe_datetime_parse(pend_dt_nova) or safe_datetime_parse(pend_dt_orig)
                    if dt_pref:
                        st.session_state.pendencia_data_prefill = dt_pref.strftime("%Y-%m-%d")
                    st.rerun()
        st.markdown("---")

    # Selecionar funcionário
    usuarios = obter_usuarios_ativos()
    if not usuarios:
        st.info("📭 Nenhum usuário ativo encontrado para correção.")
        return

    opcoes_usuarios = [f"{u['nome_completo']} ({u['usuario']})" for u in usuarios]

    usuario_prefill = st.session_state.get("pendencia_usuario_prefill")
    data_prefill = st.session_state.get("pendencia_data_prefill")
    registro_id_prefill = st.session_state.get("pendencia_registro_id_prefill")
    tipo_solicitacao_prefill = st.session_state.get("pendencia_tipo_solicitacao_prefill", "ajuste_registro")
    data_referencia_prefill = st.session_state.get("pendencia_data_referencia_prefill", "")
    hora_inicio_prefill = st.session_state.get("pendencia_hora_inicio_prefill", "")
    hora_saida_prefill = st.session_state.get("pendencia_hora_saida_prefill", "")
    dt_orig_prefill_raw = st.session_state.get("pendencia_datahora_original_prefill", "")
    dt_nova_prefill_raw = st.session_state.get("pendencia_datahora_nova_prefill", "")
    justificativa_prefill = st.session_state.get("pendencia_justificativa_prefill", "")
    
    # Normalizar para comparação sem perder o login original usado nas consultas.
    usuario_prefill_norm = usuario_prefill.casefold() if usuario_prefill else None

    idx_padrao = 0
    if usuario_prefill_norm:
        for i, opc in enumerate(opcoes_usuarios):
            # Comparação case-insensitive para encontrar o usuário correto
            if f"({usuario_prefill_norm})" in opc.lower() or f"({usuario_prefill})" in opc:
                idx_padrao = i
                break

    usuario_selecionado = st.selectbox(
        "👤 Selecione o Funcionário",
        opcoes_usuarios,
        index=idx_padrao
    )

    if usuario_selecionado:
        usuario = usuario_selecionado.split('(')[-1].replace(')', '')
        usuario_norm = usuario.casefold()

        # Selecionar data
        data_default = date.today()
        if data_prefill:
            dt_pref = safe_datetime_parse(data_prefill)
            if dt_pref:
                data_default = dt_pref.date()

        data_corrigir = st.date_input(
            "📅 Data do Registro",
            value=data_default,
            max_value=date.today()
        )

        # Buscar registros do dia
        registros = buscar_registros_dia(
            usuario, data_corrigir.strftime("%Y-%m-%d"))

        if registros:
            st.subheader(
                f"📋 Registros de {data_corrigir.strftime('%d/%m/%Y')}")

            if tipo_solicitacao_prefill == 'complemento_jornada' and (hora_inicio_prefill or hora_saida_prefill):
                st.info(
                    "🧩 Solicitação de complemento selecionada: "
                    f"entrada `{hora_inicio_prefill or '-'}` e saida `{hora_saida_prefill or '-'}` em `{data_referencia_prefill or data_corrigir.strftime('%Y-%m-%d')}`"
                )

            # Exibir contexto da solicitação selecionada para o gestor localizar facilmente.
            if usuario_prefill_norm and usuario_norm == usuario_prefill_norm and (dt_orig_prefill_raw or dt_nova_prefill_raw):
                st.info(
                    "🎯 Solicitação selecionada: "
                    f"{format_datetime_safe(dt_orig_prefill_raw, '%d/%m/%Y %H:%M', default='-')} "
                    f"→ {format_datetime_safe(dt_nova_prefill_raw, '%d/%m/%Y %H:%M', default='-')}"
                )
                if justificativa_prefill:
                    st.markdown(f"**Justificativa do pedido:** {justificativa_prefill}")
            elif usuario_prefill_norm and (dt_orig_prefill_raw or dt_nova_prefill_raw):
                # DEBUG: mostrar informações se houver prefill mas o usuario não corresponde
                st.warning(
                    f"⚠️ Você selecionou outro usuário. "
                    f"A solicitação é para **{usuario_prefill}**, mas você está vendo **{usuario_selecionado}**. "
                    f"Selecione **{usuario_prefill}** para ver os detalhes da solicitação."
                )

            projetos_ativos = obter_projetos_ativos()
            tipos_opcoes = ["inicio", "intermediario", "fim"]

            for registro in registros:
                dt_registro = safe_datetime_parse(registro.get('data_hora'))
                dt_orig_prefill = safe_datetime_parse(dt_orig_prefill_raw)
                dt_nova_prefill = safe_datetime_parse(dt_nova_prefill_raw)

                is_registro_alvo = False
                if registro_id_prefill and str(registro.get('id')) == str(registro_id_prefill):
                    is_registro_alvo = True
                elif dt_registro and dt_orig_prefill:
                    # Fallback para solicitações sem registro_id: mesma data/hora com tolerância curta.
                    is_registro_alvo = abs((dt_registro - dt_orig_prefill).total_seconds()) <= 60

                with st.expander(f"⏰ {registro['data_hora']} - {registro['tipo']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        if is_registro_alvo:
                            st.success("🎯 Registro alvo da solicitação selecionada")
                        st.write(f"**Tipo:** {registro['tipo']}")
                        st.write(
                            f"**Data/Hora Atual:** {registro['data_hora']}")
                        if is_registro_alvo and (dt_orig_prefill_raw or dt_nova_prefill_raw):
                            st.write(
                                f"**Alteração Solicitada:** "
                                f"`{format_datetime_safe(dt_orig_prefill_raw, '%Y-%m-%d %H:%M:%S', default='-')}` "
                                f"→ `{format_datetime_safe(dt_nova_prefill_raw, '%Y-%m-%d %H:%M:%S', default='-')}`"
                            )
                        st.write(
                            f"**Modalidade:** {registro['modalidade'] or 'N/A'}")
                        st.write(
                            f"**Projeto:** {registro['projeto'] or 'N/A'}")

                    with col2:
                        # Formulário de edição
                        with st.form(f"editar_registro_{registro['id']}"):
                            tipo_atual = normalizar_tipo_ponto(registro.get('tipo'))
                            if tipo_atual not in tipos_opcoes:
                                tipo_atual = "inicio"

                            novo_tipo = st.selectbox(
                                "Novo Tipo",
                                tipos_opcoes,
                                index=tipos_opcoes.index(tipo_atual)
                            )

                            valor_data_hora_padrao = str(registro['data_hora'])
                            if is_registro_alvo and dt_nova_prefill:
                                valor_data_hora_padrao = dt_nova_prefill.strftime("%Y-%m-%d %H:%M:%S")
                            elif is_registro_alvo and dt_nova_prefill_raw:
                                valor_data_hora_padrao = str(dt_nova_prefill_raw)

                            nova_data_hora = st.text_input(
                                "Nova Data/Hora (YYYY-MM-DD HH:MM)",
                                value=valor_data_hora_padrao
                            )

                            nova_modalidade = st.selectbox(
                                "Nova Modalidade",
                                ["", "presencial", "home_office", "campo"],
                                index=["", "presencial", "home_office", "campo"].index(
                                    normalizar_modalidade_ponto(registro.get('modalidade')))
                            )

                            novo_projeto = st.selectbox(
                                "Novo Projeto",
                                [""] + projetos_ativos,
                                index=(projetos_ativos.index(registro['projeto']) + 1)
                                if registro['projeto'] in projetos_ativos else 0
                            )

                            # Justificativa obrigatória para auditoria da correção
                            justificativa_edicao = st.text_area(
                                "Justificativa da Edição",
                                placeholder="Explique por que esta correção é necessária...",
                                height=120
                            )

                            # Botão de salvar alteração do formulário
                            submitted = st.form_submit_button(
                                "💾 Salvar Alterações", width="stretch")

                            if submitted:
                                if not justificativa_edicao.strip():
                                    st.error(
                                        "❌ Justificativa obrigatória para correções")
                                else:
                                    resultado = corrigir_registro_ponto(
                                        registro['id'],
                                        novo_tipo,
                                        nova_data_hora,
                                        nova_modalidade if nova_modalidade else None,
                                        novo_projeto if novo_projeto else None,
                                        justificativa_edicao,
                                        st.session_state.usuario,
                                        st.session_state.get("pendencia_correcao_id_prefill") if is_registro_alvo else None,
                                    )

                                    if resultado["success"]:
                                        for k in [
                                            "pendencia_correcao_id_prefill",
                                            "pendencia_registro_id_prefill",
                                            "pendencia_tipo_solicitacao_prefill",
                                            "pendencia_data_referencia_prefill",
                                            "pendencia_hora_inicio_prefill",
                                            "pendencia_hora_saida_prefill",
                                            "pendencia_datahora_original_prefill",
                                            "pendencia_datahora_nova_prefill",
                                            "pendencia_justificativa_prefill",
                                        ]:
                                            if k in st.session_state:
                                                del st.session_state[k]
                                        st.success(f"✅ {resultado['message']}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {resultado['message']}")

                            excluir_submitted = st.form_submit_button(
                                "🗑️ Excluir Registro", width="stretch"
                            )

                            if excluir_submitted:
                                if not justificativa_edicao.strip():
                                    st.error("❌ Justificativa obrigatória para excluir registros")
                                else:
                                    resultado = excluir_registro_ponto(
                                        registro['id'],
                                        justificativa_edicao,
                                        st.session_state.usuario,
                                        st.session_state.get("pendencia_correcao_id_prefill") if is_registro_alvo else None,
                                    )
                                    if resultado["success"]:
                                        for k in [
                                            "pendencia_correcao_id_prefill",
                                            "pendencia_registro_id_prefill",
                                            "pendencia_tipo_solicitacao_prefill",
                                            "pendencia_data_referencia_prefill",
                                            "pendencia_hora_inicio_prefill",
                                            "pendencia_hora_saida_prefill",
                                            "pendencia_datahora_original_prefill",
                                            "pendencia_datahora_nova_prefill",
                                            "pendencia_justificativa_prefill",
                                        ]:
                                            if k in st.session_state:
                                                del st.session_state[k]
                                        st.success(f"✅ {resultado['message']}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {resultado['message']}")
        else:
            if tipo_solicitacao_prefill == 'complemento_jornada' and (hora_inicio_prefill or hora_saida_prefill):
                st.warning(
                    "⚠️ Esta solicitação pede entrada e saida (complemento de jornada), mas ainda não há registros no dia. "
                    "Use a aprovação de correções abaixo para aplicar automaticamente os dois registros."
                )
            st.info(
                f"📋 Nenhum registro encontrado para {usuario} em {data_corrigir.strftime('%d/%m/%Y')}")


def pendencias_ponto_interface():
    """Painel de inconsistências de ponto para gestores/RH."""
    try:
        from pendencias_ponto import detectar_pendencias_ponto
    except Exception:
        from ponto_esa_v5.pendencias_ponto import detectar_pendencias_ponto

    st.markdown("""
    <div class="feature-card">
        <h3>⚠️ PENDÊNCIAS DE PONTO</h3>
        <p>Identifique inconsistências nos registros e tome ações rápidas</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        data_inicio = st.date_input("Data inicial", value=date.today() - timedelta(days=7), key="pend_ponto_ini")
    with col2:
        data_fim = st.date_input("Data final", value=date.today(), key="pend_ponto_fim")
    with col3:
        usuarios_ativos = obter_usuarios_ativos()
        opcoes = ["Todos"] + [f"{u['nome_completo']} ({u['usuario']})" for u in usuarios_ativos]
        filtro_usuario = st.selectbox("Funcionário", opcoes, key="pend_ponto_usr")

    if data_inicio > data_fim:
        st.error("❌ Data inicial não pode ser maior que a data final")
        return

    usuario_filtrado = None
    if filtro_usuario != "Todos":
        usuario_filtrado = filtro_usuario.split("(")[-1].replace(")", "")

    usuarios_mapa = {u["usuario"]: u.get("nome_completo") or u["usuario"] for u in usuarios_ativos}
    usuarios_considerados = [usuario_filtrado] if usuario_filtrado else sorted(usuarios_mapa.keys())

    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT usuario, data_referencia, tipo_inconsistencia
            FROM pendencias_ponto_ignoradas
            WHERE DATE(data_referencia) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
        """, (data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")))
        ignoradas = {
            (row[0], str(row[1]), row[2]) for row in cursor.fetchall()
            if row[0] in usuarios_considerados
        }

        if usuario_filtrado:
            cursor.execute(f"""
                SELECT usuario, DATE(data_hora), data_hora, tipo
                FROM registros_ponto
                WHERE usuario = {SQL_PLACEHOLDER}
                  AND DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
                ORDER BY usuario, data_hora
            """, (usuario_filtrado, data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")))
        else:
            cursor.execute(f"""
                SELECT usuario, DATE(data_hora), data_hora, tipo
                FROM registros_ponto
                WHERE DATE(data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
                ORDER BY usuario, data_hora
            """, (data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")))
        registros_raw = cursor.fetchall()

        cursor.execute(f"""
            SELECT data
            FROM feriados
            WHERE ativo = 1
              AND data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
        """, (data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")))
        feriados_periodo = {str(row[0]) for row in cursor.fetchall()}
    finally:
        _return_conn(conn)

    pendencias = detectar_pendencias_ponto(
        usuarios_considerados=usuarios_considerados,
        usuarios_mapa=usuarios_mapa,
        data_inicio=data_inicio,
        data_fim=data_fim,
        registros_raw=registros_raw,
        feriados_periodo=feriados_periodo,
        ignoradas=ignoradas,
    )

    if not pendencias:
        st.success("✅ Nenhuma pendência encontrada no período")
        return

    df = pd.DataFrame([
        {
            "Funcionário": p["nome"],
            "Data": p["data"],
            "Tipo de inconsistência": p["tipo"],
            "Horas registradas": p["horas"] if p["horas"] is not None else "-",
            "Ação": "Selecionar abaixo",
        }
        for p in pendencias
    ])
    # Evita mistura float/str no Arrow (Streamlit) quando há valor numérico e '-'.
    df["Horas registradas"] = df["Horas registradas"].apply(
        lambda v: "-" if v in (None, "") else str(v)
    )
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(f"Total de inconsistências encontradas: {len(pendencias)}")

    st.markdown("### Ações")
    for idx, pend in enumerate(pendencias, start=1):
        titulo = f"{idx}. {pend['nome']} | {pend['data']} | {pend['tipo']}"
        with st.expander(titulo):
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                if st.button("📨 Solicitar correção", key=f"acao_solicitar_{idx}"):
                    try:
                        from push_scheduler import enviar_mensagem_direta
                        msg = (
                            f"Identificamos uma pendência de ponto em {pend['data']}: {pend['tipo']}. "
                            "Por favor, acesse a tela de Solicitar Correção de Registro e regularize o dia."
                        )
                        ok = enviar_mensagem_direta(st.session_state.usuario, pend["usuario"], msg)
                        if ok:
                            st.success("✅ Solicitação enviada ao funcionário")
                        else:
                            st.warning("⚠️ Não foi possível enviar mensagem automática")
                    except Exception as e:
                        st.error(f"❌ Erro ao solicitar correção: {str(e)}")

            with col_b:
                if st.button("🔧 Corrigir registro", key=f"acao_corrigir_{idx}"):
                    st.session_state.pendencia_usuario_prefill = pend["usuario"]
                    st.session_state.pendencia_data_prefill = pend["data"]
                    st.session_state.ir_para_corrigir_registros = True
                    st.rerun()

            with col_c:
                if st.button("🙈 Ignorar", key=f"acao_ignorar_{idx}"):
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute(f"""
                            INSERT INTO pendencias_ponto_ignoradas
                            (usuario, data_referencia, tipo_inconsistencia, ignorado_por, motivo)
                            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                        """, (
                            pend["usuario"],
                            pend["data"],
                            pend["tipo_key"],
                            st.session_state.usuario,
                            "Ignorado no painel de pendências",
                        ))
                        conn.commit()
                        st.success("✅ Pendência ignorada")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"❌ Erro ao ignorar pendência: {str(e)}")
                    finally:
                        _return_conn(conn)


def meus_registros_interface(calculo_horas_system):
    """Interface para visualizar registros com cálculos - OTIMIZADA"""
    st.markdown("""
    <div class="feature-card">
        <h3>📋 Meus Registros</h3>
        <p>Visualize seu histórico de registros de ponto com cálculos de horas</p>
    </div>
    """, unsafe_allow_html=True)

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        data_inicio = st.date_input(
            "Data Início", value=date.today() - timedelta(days=7))  # Reduzido para 7 dias por padrão
    with col2:
        data_fim = st.date_input("Data Fim", value=date.today())
    with col3:
        projeto_filtro = st.selectbox(
            "Projeto", ["Todos"] + obter_projetos_ativos())

    # Calcular horas do período (usa cache)
    calculo_periodo = calculo_horas_system.calcular_horas_periodo(
        st.session_state.usuario,
        data_inicio.strftime("%Y-%m-%d"),
        data_fim.strftime("%Y-%m-%d")
    )

    # Métricas do período
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⏱️ Total de Horas", format_time_duration(
            calculo_periodo["total_horas"]))
    with col2:
        st.metric("📅 Dias Trabalhados", calculo_periodo["dias_trabalhados"])
    with col3:
        st.metric("🌞 Horas Normais", format_time_duration(
            calculo_periodo["total_horas_normais"]))
    with col4:
        st.metric("🎯 Dom/Feriados",
                  format_time_duration(calculo_periodo["total_domingos_feriados"]))

    # Buscar registros
    registros = obter_registros_usuario(
        st.session_state.usuario,
        data_inicio.strftime("%Y-%m-%d"),
        data_fim.strftime("%Y-%m-%d")
    )

    if registros:
        df = pd.DataFrame(registros, columns=[
            'ID', 'Usuário', 'Data/Hora', 'Tipo', 'Modalidade', 'Projeto', 'Atividade', 'Localização', 'Latitude', 'Longitude', 'Registro'
        ])

        # Aplicar filtro de projeto
        if projeto_filtro != "Todos":
            df = df[df['Projeto'] == projeto_filtro]

        # Formatar dados para exibição
        df['Data'] = pd.to_datetime(df['Data/Hora']).dt.strftime('%d/%m/%Y')
        df['Hora'] = pd.to_datetime(df['Data/Hora']).dt.strftime('%H:%M')
        df['Localização'] = df.apply(
            lambda r: formatar_localizacao_legivel(r['Localização'], r['Latitude'], r['Longitude']),
            axis=1
        )
        
        # Exibir tabela simples e rápida
        st.markdown("### 📅 Registros do Período")
        st.dataframe(
            df[['Data', 'Hora', 'Tipo', 'Modalidade', 'Projeto', 'Atividade', 'Localização']],
            width="stretch",
            hide_index=True
        )

        # Botão de exportação
        if st.button("📊 Exportar para Excel"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Registros', index=False)

            safe_download_button(
                label="💾 Download Excel",
                data=output.getvalue(),
                file_name=f"registros_{st.session_state.usuario}_{data_inicio}_{data_fim}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("📋 Nenhum registro encontrado no período selecionado")


def meus_arquivos_interface(upload_system):
    """Interface para gerenciar arquivos do usuário"""
    st.markdown("""
    <div class="feature-card">
        <h3>📁 Meus Arquivos</h3>
        <p>Gerencie seus documentos e comprovantes</p>
    </div>
    """, unsafe_allow_html=True)

    # Estatísticas
    uploads = upload_system.get_user_uploads(st.session_state.usuario)
    total_files = len(uploads)
    total_size = sum(upload['tamanho'] for upload in uploads)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Total de Arquivos", total_files)
    with col2:
        st.metric("💾 Espaço Usado", format_file_size(total_size))
    with col3:
        st.metric("📊 Limite", "10MB por arquivo")

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        categoria_filtro = st.selectbox(
            "Categoria",
            ["Todos", "ausencia", "atestado_horas", "documento"]
        )
    with col2:
        ordenacao = st.selectbox(
            "Ordenar por", ["Data (mais recente)", "Nome", "Tamanho"])

    # Aplicar filtros
    if categoria_filtro != "Todos":
        uploads_filtrados = [u for u in uploads if u.get(
            'relacionado_a') == categoria_filtro]
    else:
        uploads_filtrados = uploads

    # Ordenação
    if ordenacao == "Nome":
        uploads_filtrados.sort(key=lambda x: x['nome_original'])
    elif ordenacao == "Tamanho":
        uploads_filtrados.sort(key=lambda x: x['tamanho'], reverse=True)
    else:
        uploads_filtrados.sort(key=lambda x: x['data_upload'], reverse=True)

    # Lista de arquivos
    if uploads_filtrados:
        for upload in uploads_filtrados:
            with st.expander(f"{get_file_icon(upload['tipo_arquivo'])} {upload['nome_original']} ({format_file_size(upload['tamanho'])})"):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write(
                        f"**Categoria:** {get_category_name(upload.get('relacionado_a', 'documento'))}")
                    st.write(f"**Upload em:** {format_datetime_safe(upload['data_upload'], '%d/%m/%Y às %H:%M')}")
                    st.write(f"**Tipo:** {upload['tipo_arquivo']}")

                with col2:
                    if st.button(f"📥 Download", key=f"download_{upload['id']}"):
                        content, file_info = upload_system.get_file_content(
                            upload['id'], st.session_state.usuario)
                        if content:
                            safe_download_button(
                                label="💾 Baixar Arquivo",
                                data=content,
                                file_name=file_info['nome_original'],
                                mime=file_info['tipo_arquivo']
                            )
                        else:
                            st.error("❌ Erro ao baixar arquivo")

                with col3:
                    if st.button(f"🗑️ Excluir", key=f"delete_{upload['id']}"):
                        resultado = upload_system.delete_file(
                            upload['id'], st.session_state.usuario)
                        if resultado["success"]:
                            st.success("✅ Arquivo excluído")
                            st.rerun()
                        else:
                            st.error(f"❌ {resultado['message']}")

                # Preview para imagens
                if is_image_file(upload['tipo_arquivo']):
                    content, _ = upload_system.get_file_content(
                        upload['id'], st.session_state.usuario)
                    if content:
                        st.image(
                            content, caption=upload['nome_original'], width=300)
    else:
        st.info("📁 Nenhum arquivo encontrado")

# Interface do gestor (simplificada - pode ser expandida)


def tela_gestor():
    """Interface principal para gestores"""
    atestado_system, upload_system, horas_extras_system, banco_horas_system, calculo_horas_system = init_systems()

    # Verificar notificações pendentes
    notificacoes = notification_manager.get_notifications(
        st.session_state.usuario)
    notificacoes_pendentes = [
        n for n in notificacoes if n.get('requires_response', False)]

    if notificacoes_pendentes:
        for notificacao in notificacoes_pendentes:
            with st.container():
                st.warning(
                    f"🔔 {notificacao['title']}: {notificacao['message']}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Responder", key=f"responder_{notificacao['solicitacao_id']}"):
                        # Redirecionar para a tela correta conforme tipo da notificação.
                        notif_type = str(notificacao.get('type', '')).lower()
                        if 'ajuste' in notif_type or 'correc' in notif_type:
                            st.session_state.ir_para_notificacoes = True
                        elif 'atestado' in notif_type:
                            st.session_state['opcao_menu'] = "✅ Aprovar Atestados"
                        else:
                            st.session_state['opcao_menu'] = "🕐 Aprovar Horas Extras"
                        st.rerun()

                with col2:
                    if st.button("⏰ Lembrar Depois", key=f"lembrar_{notificacao['solicitacao_id']}"):
                        # Manter notificação ativa
                        pass

    # Header
    st.markdown(f"""
    <div class="main-header">
        <div class="user-welcome">👑 Olá, {st.session_state.nome_completo}</div>
        <div class="user-info">Gestor • {get_datetime_br().strftime('%d/%m/%Y %H:%M')}</div>
    </div>
    """, unsafe_allow_html=True)

    # Widget de notificações persistentes para gestor
    exibir_widget_notificacoes(horas_extras_system)

    # Contagem consolidada de pendências (usada no dashboard principal e na sidebar).
    try:
        he_aprovar, atestados_pendentes, correcoes_pendentes = obter_badges_gestor_cached(
            st.session_state.usuario
        )
    except Exception as e:
        log_error("Erro ao contar pendências do gestor", e, {"usuario": st.session_state.usuario})
        he_aprovar = atestados_pendentes = correcoes_pendentes = 0

    total_notif = he_aprovar + atestados_pendentes + correcoes_pendentes
    if total_notif > 0:
        st.warning(
            f"🔔 Você tem {total_notif} notificação(ões) pendente(s): "
            f"{he_aprovar} hora(s) extra(s), {correcoes_pendentes} correção(ões) de registro e "
            f"{atestados_pendentes} atestado(s)."
        )

    # Verificar se há solicitações de hora extra pendentes
    solicitacoes_pendentes_count = he_aprovar
    
    # Se houver solicitações pendentes, exibir alerta destacado
    if solicitacoes_pendentes_count > 0:
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            animation: pulse 2s infinite;
        ">
            <h3 style="margin: 0; color: white;">🔔 Solicitações de Hora Extra Pendentes</h3>
            <p style="margin: 10px 0; font-size: 16px;">
                Você tem <strong>{solicitacoes_pendentes_count}</strong> solicitação{'ões' if solicitacoes_pendentes_count > 1 else ''} aguardando aprovação
            </p>
        </div>
        <style>
            @keyframes pulse {{
                0%, 100% {{ box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                50% {{ box-shadow: 0 6px 12px rgba(245, 87, 108, 0.4); }}
            }}
        </style>
        """, unsafe_allow_html=True)
        
        if st.button("📋 Aprovar Agora", type="primary", width="stretch", key="btn_aprovar_rapido"):
            st.session_state.aprovar_hora_extra = True
            st.rerun()
    
    # Se clicou em aprovar hora extra, mostrar interface de aprovação
    if st.session_state.get('aprovar_hora_extra'):
        aprovar_hora_extra_rapida_interface()
        return  # Não exibir resto da interface

    # Menu lateral
    with st.sidebar:
        st.markdown("### 🎛️ Menu do Gestor")
        
        # Reusa a contagem consolidada já calculada no topo da tela.
        
        opcoes_menu = [
            "📊 Dashboard",
            "👥 Todos os Registros",
            "⚠️ Pendências de Ponto",
            f"✅ Aprovar Atestados{f' 🔴{atestados_pendentes}' if atestados_pendentes > 0 else ''}",
            f"🕐 Aprovar Horas Extras{f' 🔴{he_aprovar}' if he_aprovar > 0 else ''}",
            "📈 Relatórios",
            "📊 Horas por Projeto",
            "🏦 Banco de Horas Geral",
            "📁 Gerenciar Arquivos",
            "🏢 Gerenciar Projetos",
            "👤 Gerenciar Usuários",
            "📅 Configurar Jornada",
            f"🔧 Corrigir Registros{f' 🔴{correcoes_pendentes}' if correcoes_pendentes > 0 else ''}",
            f"🔔 Notificações{f' 🔴{total_notif}' if total_notif > 0 else ''}",
            "📢 Comunicação",
            "🏖️ Férias",
            "⚙️ Sistema",
            "🧾 Auditoria de Alterações"
        ]
        
        # 🔧 CORREÇÃO: Persistir opção selecionada no session_state após st.rerun()
        if 'menu_gestor_index' not in st.session_state:
            st.session_state.menu_gestor_index = 0

        # Redirecionamento forçado para Corrigir Registros (ex.: vindo da Central de Notificações)
        if st.session_state.get('ir_para_corrigir_registros'):
            for i, opt in enumerate(opcoes_menu):
                if opt.startswith("🔧 Corrigir Registros"):
                    st.session_state.menu_gestor_index = i
                    st.session_state["menu_gestor_selectbox"] = opt
                    break
            del st.session_state.ir_para_corrigir_registros

        # Redirecionamento forçado para Central de Notificações
        if st.session_state.get('ir_para_notificacoes'):
            for i, opt in enumerate(opcoes_menu):
                if opt.startswith("🔔 Notificações"):
                    st.session_state.menu_gestor_index = i
                    st.session_state["menu_gestor_selectbox"] = opt
                    break
            del st.session_state.ir_para_notificacoes

        if st.session_state.get('ir_para_aprovar_horas_extras'):
            for i, opt in enumerate(opcoes_menu):
                if opt.startswith("🕐 Aprovar Horas Extras"):
                    st.session_state.menu_gestor_index = i
                    st.session_state["menu_gestor_selectbox"] = opt
                    break
            del st.session_state.ir_para_aprovar_horas_extras

        if st.session_state.get('ir_para_aprovar_atestados'):
            for i, opt in enumerate(opcoes_menu):
                if opt.startswith("✅ Aprovar Atestados"):
                    st.session_state.menu_gestor_index = i
                    st.session_state["menu_gestor_selectbox"] = opt
                    break
            del st.session_state.ir_para_aprovar_atestados
        
        # Encontrar índice da opção atual para manter a seleção após rerun
        opcao = st.selectbox(
            "Escolha uma opção:", 
            opcoes_menu,
            index=st.session_state.menu_gestor_index,
            key="menu_gestor_selectbox"
        )
        
        # Atualizar índice no session_state
        if opcao in opcoes_menu:
            st.session_state.menu_gestor_index = opcoes_menu.index(opcao)
        else:
            # Se a opção tem badges dinâmicos, procurar pelo prefixo
            for i, opt in enumerate(opcoes_menu):
                if opcao.split('🔴')[0].strip() == opt.split('🔴')[0].strip():
                    st.session_state.menu_gestor_index = i
                    break

        st.markdown("---")
        
        # Sistema de Push Notifications (ntfy.sh - funciona mesmo com app fechado)
        st.markdown("#### 🔔 Lembretes de Ponto")
        
        # Verificar se já está inscrito
        try:
            topic, push_ativo = verificar_subscription(st.session_state.usuario)
        except Exception as e:
            logger.debug(f"Erro ao verificar subscription push (gestor): {e}")
            topic, push_ativo = None, False
        
        ntfy_topic = get_topic_for_user(st.session_state.usuario)
        
        if push_ativo:
            st.success("✅ Push ativo!")
            
            st.markdown(f"""
            <div style="font-size: 13px; padding: 12px; background: #e8f5e9; border-radius: 8px; margin: 10px 0;">
                <p style="margin: 0 0 10px 0;"><b>📲 Para receber no celular:</b></p>
                <ol style="margin: 0; padding-left: 20px; line-height: 2;">
                    <li>Instale o app <a href="https://ntfy.sh" target="_blank">ntfy</a></li>
                    <li>Inscreva-se no tópico:</li>
                </ol>
                <div style="background: #fff; padding: 8px 12px; border-radius: 6px; margin-top: 8px; text-align: center;">
                    <code style="font-size: 14px; font-weight: bold; color: #1976d2;">{ntfy_topic}</code>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Configurar horários personalizados
            with st.expander("⏰ Configurar Horários"):
                from push_scheduler import obter_horarios_usuario, atualizar_horarios_usuario
                
                horarios = obter_horarios_usuario(st.session_state.usuario)
                
                h_entrada = st.text_input("🌅 Entrada:", value=horarios['entrada'], key="h_entrada_g")
                h_almoco_s = st.text_input("🍽️ Saída Almoço:", value=horarios['almoco_saida'], key="h_almoco_s_g")
                h_almoco_r = st.text_input("☕ Retorno Almoço:", value=horarios['almoco_retorno'], key="h_almoco_r_g")
                h_saida = st.text_input("🏠 Saída:", value=horarios['saida'], key="h_saida_g")
                
                if st.button("💾 Salvar Horários", key="salvar_horarios_g"):
                    if atualizar_horarios_usuario(
                        st.session_state.usuario, 
                        h_entrada, h_almoco_s, h_almoco_r, h_saida
                    ):
                        st.success("✅ Horários atualizados!")
                    else:
                        st.error("❌ Erro ao salvar")
            
            if st.button("🔕 Desativar", width="stretch", key="btn_desativar_push_gestor"):
                from push_scheduler import desativar_subscription
                desativar_subscription(st.session_state.usuario)
                st.rerun()
        else:
            st.info("📱 Receba lembretes mesmo com o app fechado!")
            
            if st.button("🔔 Ativar Lembretes", width="stretch", key="btn_ativar_push_gestor"):
                topic = registrar_subscription(st.session_state.usuario)
                st.success(f"✅ Ativado! Seu tópico: **{ntfy_topic}**")
                st.rerun()

        st.markdown("---")

        if st.button("🚪 Sair", width="stretch"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Conteúdo baseado na opção
    if opcao == "📊 Dashboard":
        dashboard_gestor(banco_horas_system, calculo_horas_system)
    elif opcao.startswith("👥 Todos os Registros"):
        todos_registros_interface(calculo_horas_system)
    elif opcao.startswith("🧾 Auditoria de Alterações"):
        auditoria_alteracoes_interface()
    elif opcao.startswith("⚠️ Pendências de Ponto"):
        pendencias_ponto_interface()
    elif opcao.startswith("✅ Aprovar Atestados"):
        aprovar_atestados_interface(atestado_system)
    elif opcao.startswith("🕐 Aprovar Horas Extras"):
        aprovar_horas_extras_interface(horas_extras_system)
    elif opcao.startswith("📈 Relatórios"):
        relatorios_horas_extras_interface()
    elif opcao.startswith("📊 Horas por Projeto"):
        horas_por_projeto_interface()
    elif opcao.startswith("🏦 Banco de Horas Geral"):
        banco_horas_gestor_interface(banco_horas_system)
    elif opcao.startswith("📅 Configurar Jornada"):
        configurar_jornada_interface()
    elif opcao.startswith("🔧 Corrigir Registros"):
        aprovar_correcoes_registros_interface()
        st.markdown("---")
        corrigir_registros_interface()
    elif opcao.startswith("📁 Gerenciar Arquivos"):
        gerenciar_arquivos_interface(upload_system)
    elif opcao.startswith("🏢 Gerenciar Projetos"):
        gerenciar_projetos_interface()
    elif opcao.startswith("👤 Gerenciar Usuários"):
        gerenciar_usuarios_interface()
    elif opcao.startswith("🔔 Notificações"):
        notificacoes_gestor_interface(horas_extras_system, atestado_system)
    elif opcao.startswith("📢 Comunicação"):
        comunicacao_gestor_interface()
    elif opcao.startswith("🏖️ Férias"):
        ferias_gestor_interface()
    elif opcao.startswith("⚙️ Sistema"):
        sistema_interface()


def comunicacao_gestor_interface():
    """Interface de comunicação do gestor - Avisos e mensagens diretas"""
    from push_scheduler import (
        enviar_aviso_geral, enviar_mensagem_direta, obter_avisos_gestor,
        obter_mensagens_usuario, marcar_mensagem_lida
    )
    
    st.markdown("""
    <div class="feature-card">
        <h3>📢 Central de Comunicação</h3>
        <p>Envie avisos para todos ou mensagens diretas para funcionários</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📢 Enviar Aviso", "💬 Mensagem Direta", "📜 Histórico"])
    
    with tab1:
        st.markdown("### 📢 Enviar Aviso Geral")
        st.info("O aviso será enviado como notificação push para todos os funcionários com lembretes ativados")
        
        titulo = st.text_input("Título do Aviso:", placeholder="Ex: Reunião amanhã", key="aviso_titulo")
        mensagem = st.text_area("Mensagem:", placeholder="Detalhes do aviso...", key="aviso_mensagem", height=100)
        
        # Opção de destinatários
        tipo_dest = st.radio("Enviar para:", ["Todos os funcionários", "Selecionar específicos"], horizontal=True)
        
        destinatarios = 'todos'
        if tipo_dest == "Selecionar específicos":
            # Buscar funcionários
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo")
                funcionarios = cursor.fetchall()
            finally:
                _return_conn(conn)
            
            selecionados = st.multiselect(
                "Selecione os funcionários:",
                options=[f[0] for f in funcionarios],
                format_func=lambda x: next((f[1] for f in funcionarios if f[0] == x), x)
            )
            
            if selecionados:
                destinatarios = ','.join(selecionados)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📤 Enviar Aviso", type="primary", width="stretch"):
                if titulo and mensagem:
                    enviados = enviar_aviso_geral(
                        gestor=st.session_state.usuario,
                        titulo=titulo,
                        mensagem=mensagem,
                        destinatarios=destinatarios
                    )
                    
                    if enviados > 0:
                        st.success(f"✅ Aviso enviado via ntfy para {enviados} funcionário(s)!")
                        st.info("📲 Os funcionários receberão a notificação no app ntfy.")
                    else:
                        st.error(
                            "❌ Não foi possível enviar o aviso. "
                            "Verifique se o serviço ntfy.sh está acessível."
                        )
                else:
                    st.error("❌ Preencha o título e a mensagem")
    
    with tab2:
        st.markdown("### 💬 Enviar Mensagem Direta")
        st.info("A mensagem será enviada como notificação push para o funcionário selecionado")
        
        # Buscar funcionários
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 AND usuario != {SQL_PLACEHOLDER} ORDER BY nome_completo", 
                          (st.session_state.usuario,))
            funcionarios = cursor.fetchall()
        finally:
            _return_conn(conn)
        
        destinatario = st.selectbox(
            "Destinatário:",
            options=[f[0] for f in funcionarios],
            format_func=lambda x: next((f[1] for f in funcionarios if f[0] == x), x),
            key="msg_destinatario"
        )
        
        msg_direta = st.text_area("Mensagem:", placeholder="Digite sua mensagem...", key="msg_direta", height=100)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("📤 Enviar Mensagem", type="primary", width="stretch"):
                if destinatario and msg_direta:
                    sucesso = enviar_mensagem_direta(
                        remetente=st.session_state.usuario,
                        destinatario=destinatario,
                        mensagem=msg_direta
                    )
                    
                    if sucesso:
                        st.success(f"✅ Mensagem enviada!")
                    else:
                        st.error("❌ Erro ao enviar mensagem")
                else:
                    st.error("❌ Selecione o destinatário e escreva a mensagem")
    
    with tab3:
        st.markdown("### 📜 Histórico de Avisos")
        
        avisos = obter_avisos_gestor(20)
        
        if avisos:
            for aviso in avisos:
                aviso_id, gestor, titulo, mensagem, destinatarios, data_envio, nome_gestor = aviso
                
                with st.expander(f"📢 {titulo} - {data_envio.strftime('%d/%m/%Y %H:%M')}"):
                    st.markdown(f"**Enviado por:** {nome_gestor or gestor}")
                    st.markdown(f"**Para:** {'Todos' if destinatarios == 'todos' else destinatarios}")
                    st.markdown(f"**Mensagem:** {mensagem}")
        else:
            st.info("📋 Nenhum aviso enviado ainda")


def ferias_gestor_interface():
    """Interface para gerenciar férias dos funcionários"""
    from push_scheduler import cadastrar_ferias, obter_ferias_funcionarios, excluir_ferias
    
    st.markdown("""
    <div class="feature-card">
        <h3>🏖️ Gerenciar Férias</h3>
        <p>Cadastre férias e configure lembretes automáticos</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Cadastrar Férias", "📋 Férias Cadastradas"])
    
    with tab1:
        st.markdown("### ➕ Cadastrar Férias")
        
        # Buscar funcionários
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario' ORDER BY nome_completo")
            funcionarios = cursor.fetchall()
        finally:
            _return_conn(conn)
        
        funcionario = st.selectbox(
            "Funcionário:",
            options=[f[0] for f in funcionarios],
            format_func=lambda x: next((f[1] for f in funcionarios if f[0] == x), x),
            key="ferias_funcionario"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data de Início:", key="ferias_inicio")
        with col2:
            data_fim = st.date_input("Data de Fim:", key="ferias_fim")
        
        dias_aviso = st.slider("Notificar quantos dias antes:", min_value=1, max_value=30, value=7)
        
        if st.button("💾 Cadastrar Férias", type="primary"):
            if funcionario and data_inicio and data_fim:
                if data_fim >= data_inicio:
                    sucesso = cadastrar_ferias(funcionario, data_inicio, data_fim, dias_aviso)
                    
                    if sucesso:
                        st.success(f"✅ Férias cadastradas! O funcionário será notificado {dias_aviso} dias antes.")
                        st.rerun()
                    else:
                        st.error("❌ Erro ao cadastrar férias")
                else:
                    st.error("❌ A data de fim deve ser maior ou igual à data de início")
            else:
                st.error("❌ Preencha todos os campos")
    
    with tab2:
        st.markdown("### 📋 Férias Cadastradas")
        
        ferias = obter_ferias_funcionarios()
        
        if ferias:
            from datetime import date
            hoje = date.today()
            
            for f in ferias:
                ferias_id, usuario, data_inicio, data_fim, dias_aviso, notificado, nome = f
                
                # Calcular status
                if data_fim < hoje:
                    status = "✅ Concluídas"
                    cor = "#e8f5e9"
                elif data_inicio <= hoje <= data_fim:
                    status = "🏖️ Em férias"
                    cor = "#fff3e0"
                else:
                    dias_restantes = (data_inicio - hoje).days
                    status = f"📅 Em {dias_restantes} dias"
                    cor = "#e3f2fd"
                
                with st.expander(f"{status} | {nome or usuario} - {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"):
                    st.markdown(f"**Funcionário:** {nome or usuario}")
                    st.markdown(f"**Período:** {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
                    duracao = (data_fim - data_inicio).days + 1
                    st.markdown(f"**Duração:** {duracao} dias")
                    st.markdown(f"**Aviso:** {dias_aviso} dias antes")
                    st.markdown(f"**Notificado:** {'Sim' if notificado else 'Não'}")
                    
                    if st.button("🗑️ Excluir", key=f"excluir_ferias_{ferias_id}"):
                        if excluir_ferias(ferias_id):
                            st.success("✅ Férias excluídas!")
                            st.rerun()
        else:
            st.info("📋 Nenhuma férias cadastrada")


def dashboard_gestor(banco_horas_system, calculo_horas_system):
    """Dashboard principal do gestor com gráficos avançados Plotly - OTIMIZADO"""
    
    # Importar módulo de dashboard com gráficos
    try:
        from dashboard_charts import (
            render_dashboard_executivo, get_dashboard_data_from_db,
            create_donut_chart, create_line_chart, create_bar_chart,
            create_card_metric, create_gauge_chart, THEME_COLORS
        )
        CHARTS_ENABLED = True
    except ImportError:
        CHARTS_ENABLED = False
    
    # ⚡ OTIMIZAÇÃO: Usar módulo com cache e connection pooling
    try:
        from db_optimized import get_metricas_dashboard_otimizado, get_registros_semana, get_ausencias_por_tipo
        USE_OPTIMIZED = True
    except ImportError:
        USE_OPTIMIZED = False
    
    # Métricas gerais - OTIMIZADO COM CACHE
    hoje = date.today().strftime("%Y-%m-%d")
    
    if USE_OPTIMIZED:
        # 🚀 Busca todas as métricas de uma vez com cache
        metricas = get_metricas_dashboard_otimizado()
        total_usuarios = metricas["total_usuarios"]
        registros_hoje = metricas["registros_hoje"]
        ausencias_pendentes = metricas["ausencias_pendentes"]
        horas_extras_pendentes = metricas["horas_extras_pendentes"]
        atestados_mes = metricas["atestados_mes"]
    elif REFACTORING_ENABLED:
        # Fallback para queries individuais (mais lento)
        total_usuarios = 0
        registros_hoje = 0
        ausencias_pendentes = 0
        horas_extras_pendentes = 0
        atestados_mes = 0
        
        try:
            # Total de usuários ativos
            query_usuarios = "SELECT COUNT(*) FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario'"
            resultado = execute_query(query_usuarios, fetch_one=True)
            if resultado:
                total_usuarios = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar total de usuários", e, {"context": "dashboard_gestor"})

        try:
            # Registros hoje
            query_registros = f"SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = {SQL_PLACEHOLDER}"
            resultado = execute_query(query_registros, (hoje,), fetch_one=True)
            if resultado:
                registros_hoje = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar registros de hoje", e, {"data": hoje})

        try:
            # Ausências pendentes
            query_ausencias = "SELECT COUNT(*) FROM ausencias WHERE status = 'pendente'"
            resultado = execute_query(query_ausencias, fetch_one=True)
            if resultado:
                ausencias_pendentes = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar ausências pendentes", e, {"status": "pendente"})

        try:
            # Horas extras pendentes
            query_he = "SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente'"
            resultado = execute_query(query_he, fetch_one=True)
            if resultado:
                horas_extras_pendentes = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar horas extras pendentes", e, {"status": "pendente"})

        try:
            # Atestados do mês
            primeiro_dia_mes = date.today().replace(day=1).strftime("%Y-%m-%d")
            query_atestados = f"""
                SELECT COUNT(*) FROM ausencias 
                WHERE data_inicio >= {SQL_PLACEHOLDER} AND tipo LIKE '%%Atestado%%'
            """
            resultado = execute_query(query_atestados, (primeiro_dia_mes,), fetch_one=True)
            if resultado:
                atestados_mes = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar atestados do mês", e, {"context": "dashboard_gestor"})
            st.error(f"Erro ao buscar atestados do mês: {e}")
    else:
        # Fallback original
        conn = get_connection()
        try:
            cursor = conn.cursor()

            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario'")
                resultado = cursor.fetchone()
                if resultado:
                    total_usuarios = resultado[0]
            except Exception as e:
                st.error(f"Erro ao buscar total de usuários: {e}")

            try:
                cursor.execute(
                    f"SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = {SQL_PLACEHOLDER}", (hoje,))
                resultado = cursor.fetchone()
                if resultado:
                    registros_hoje = resultado[0]
            except Exception as e:
                st.error(f"Erro ao buscar registros de hoje: {e}")

            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM ausencias WHERE status = 'pendente'")
                resultado = cursor.fetchone()
                if resultado:
                    ausencias_pendentes = resultado[0]
            except Exception as e:
                st.error(f"Erro ao buscar ausências pendentes: {e}")

            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente'")
                resultado = cursor.fetchone()
                if resultado:
                    horas_extras_pendentes = resultado[0]
            except Exception as e:
                st.error(f"Erro ao buscar horas extras pendentes: {e}")

            try:
                primeiro_dia_mes = date.today().replace(day=1).strftime("%Y-%m-%d")
                cursor.execute(f"""
                    SELECT COUNT(*) FROM ausencias 
                    WHERE data_inicio >= {SQL_PLACEHOLDER} AND tipo LIKE '%%Atestado%%'
                """, (primeiro_dia_mes,))
                resultado = cursor.fetchone()
                if resultado:
                    atestados_mes = resultado[0]
            except Exception as e:
                st.error(f"Erro ao buscar atestados do mês: {e}")

        finally:
            _return_conn(conn)

    # ===== DASHBOARD COM GRÁFICOS PLOTLY =====
    if CHARTS_ENABLED:
        # Header estilizado
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 15px;
            color: white;
            margin-bottom: 30px;
            text-align: center;
        ">
            <h1 style="margin: 0; color: white;">📊 Dashboard Executivo</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Atualizado em: {agora_br().strftime('%d/%m/%Y às %H:%M')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # CSS para estilizar os metrics cards
        st.markdown("""
        <style>
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        [data-testid="stMetric"]:nth-child(1) { border-left-color: #667eea; }
        [data-testid="stMetric"]:nth-child(2) { border-left-color: #28a745; }
        [data-testid="stMetric"]:nth-child(3) { border-left-color: #ffc107; }
        [data-testid="stMetric"]:nth-child(4) { border-left-color: #17a2b8; }
        [data-testid="stMetricLabel"] { font-size: 14px !important; }
        [data-testid="stMetricValue"] { font-size: 28px !important; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)
        
        # Cards de métricas usando st.metric nativo (mais confiável)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="👥 Funcionários Ativos", value=total_usuarios)
        
        with col2:
            st.metric(label="📝 Registros Hoje", value=registros_hoje)
        
        with col3:
            pendencias_total = ausencias_pendentes + horas_extras_pendentes
            st.metric(label="⏳ Pendências", value=pendencias_total)
        
        with col4:
            st.metric(label="🏥 Atestados (mês)", value=atestados_mes)
        
        st.markdown("---")
        
        # Gráficos lado a lado
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de Rosca - Status de presença
            # Calcular presentes hoje
            presentes_hoje = 0
            if REFACTORING_ENABLED:
                try:
                    query_presentes = f"""
                        SELECT COUNT(DISTINCT usuario) FROM registros_ponto 
                        WHERE DATE(data_hora) = {SQL_PLACEHOLDER}
                    """
                    resultado = execute_query(query_presentes, (hoje,), fetch_one=True)
                    if resultado:
                        presentes_hoje = resultado[0]
                except Exception as e:
                    logger.debug("Erro silenciado: %s", e)
            
            ausentes = max(0, total_usuarios - presentes_hoje)
            
            if total_usuarios > 0:
                fig = create_donut_chart(
                    labels=['Presentes', 'Ausentes'],
                    values=[presentes_hoje, ausentes],
                    title="📍 Status de Presença Hoje",
                    colors=[THEME_COLORS['success'], THEME_COLORS['danger']]
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Gauge de taxa de registros
            taxa_pontualidade = (presentes_hoje / total_usuarios * 100) if total_usuarios > 0 else 0
            fig = create_gauge_chart(
                value=taxa_pontualidade,
                max_value=100,
                title="⏱️ Taxa de Presença",
                suffix="%",
                color_ranges=[
                    {'range': [0, 60], 'color': THEME_COLORS['danger']},
                    {'range': [60, 80], 'color': THEME_COLORS['warning']},
                    {'range': [80, 100], 'color': THEME_COLORS['success']}
                ]
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de linha - Registros últimos 7 dias
        datas_semana = []
        valores_semana = []
        for i in range(6, -1, -1):
            data_check = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
            count_dia = 0
            if REFACTORING_ENABLED:
                try:
                    query_dia = f"SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = {SQL_PLACEHOLDER}"
                    resultado = execute_query(query_dia, (data_check,), fetch_one=True)
                    if resultado:
                        count_dia = resultado[0]
                except Exception as e:
                    logger.debug("Erro silenciado: %s", e)
            datas_semana.append((date.today() - timedelta(days=i)).strftime("%d/%m"))
            valores_semana.append(count_dia)
        
        fig = create_line_chart(
            x_data=datas_semana,
            y_data=valores_semana,
            title="📈 Registros de Ponto - Últimos 7 Dias",
            x_label="Data",
            y_label="Registros",
            fill=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráficos de barras
        col1, col2 = st.columns(2)
        
        with col1:
            # Tipos de ausências no mês
            ausencias_por_tipo = {}
            primeiro_dia_mes = date.today().replace(day=1).strftime("%Y-%m-%d")
            if REFACTORING_ENABLED:
                try:
                    query_tipos = f"""
                        SELECT tipo, COUNT(*) as total FROM ausencias 
                        WHERE data_inicio >= {SQL_PLACEHOLDER} 
                        GROUP BY tipo
                    """
                    resultados = execute_query(query_tipos, (primeiro_dia_mes,), fetch_all=True)
                    if resultados:
                        for row in resultados:
                            ausencias_por_tipo[row[0][:20]] = row[1]  # Truncar nome
                except Exception as e:
                    logger.debug("Erro silenciado: %s", e)
            
            if ausencias_por_tipo:
                fig = create_bar_chart(
                    x_data=list(ausencias_por_tipo.keys()),
                    y_data=list(ausencias_por_tipo.values()),
                    title="🏥 Ausências por Tipo (Mês)",
                    x_label="Tipo",
                    y_label="Quantidade",
                    color_scale="Plasma"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Sem dados de ausências no mês")
        
        with col2:
            # Status das solicitações
            status_counts = {'Pendente': 0, 'Aprovado': 0, 'Rejeitado': 0}
            if REFACTORING_ENABLED:
                try:
                    query_status = f"""
                        SELECT status, COUNT(*) FROM ausencias 
                        WHERE data_inicio >= {SQL_PLACEHOLDER} 
                        GROUP BY status
                    """
                    resultados = execute_query(query_status, (primeiro_dia_mes,), fetch_all=True)
                    if resultados:
                        for row in resultados:
                            if row[0] in status_counts:
                                status_counts[row[0].capitalize()] = row[1]
                except Exception as e:
                    logger.debug("Erro silenciado: %s", e)
            
            if any(status_counts.values()):
                fig = create_donut_chart(
                    labels=list(status_counts.keys()),
                    values=list(status_counts.values()),
                    title="📋 Status de Solicitações (Mês)",
                    colors=[THEME_COLORS['warning'], THEME_COLORS['success'], THEME_COLORS['danger']]
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 Sem solicitações no mês")
        
        st.markdown("---")
    
    else:
        # Fallback para métricas simples se Plotly não disponível
        st.markdown("""
        <div class="feature-card">
            <h3>📊 Dashboard Executivo</h3>
            <p>Visão geral do sistema de ponto com alertas</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("👥 Funcionários", total_usuarios)
        with col2:
            st.metric("📊 Registros Hoje", registros_hoje)
        with col3:
            st.metric("⏳ Ausências Pendentes", ausencias_pendentes)
        with col4:
            st.metric("🕐 Horas Extras Pendentes", horas_extras_pendentes)
        with col5:
            st.metric("🏥 Atestados do Mês", atestados_mes)

    # Destaque para horários discrepantes
    st.subheader("⚠️ Alertas de Discrepâncias (>Tolerância configurada)")

    # 🔧 CORREÇÃO: Obter tolerância configurada pelo gestor
    limiar_discrepancia = 15  # padrão
    
    if REFACTORING_ENABLED:
        try:
            query_config = "SELECT valor FROM configuracoes WHERE chave = 'tolerancia_atraso_minutos'"
            resultado = execute_query(query_config, fetch_one=True)
            if resultado:
                limiar_discrepancia = int(resultado[0])
        except Exception as e:
            log_error("Erro ao obter tolerância configurada", e, {"chave": "tolerancia_atraso_minutos"})
            logger.warning(f"Não foi possível obter tolerância do gestor no dashboard: {e}")
    else:
        try:
            cursor = get_db_connection().cursor()
            cursor.execute(
                "SELECT valor FROM configuracoes WHERE chave = 'tolerancia_atraso_minutos'"
            )
            resultado = cursor.fetchone()
            if resultado:
                limiar_discrepancia = int(resultado[0])
            cursor.close()
        except Exception as e:
            logger.warning(f"Não foi possível obter tolerância do gestor no dashboard: {e}")

    # Buscar registros de hoje com possíveis discrepâncias
    registros_hoje_detalhados = obter_registros_usuario(
        None, hoje, hoje)  # Todos os usuários

    discrepancias = []
    usuarios_processados = set()

    for registro in registros_hoje_detalhados:
        usuario = registro[1]
        if usuario in usuarios_processados:
            continue

        # Calcular horas do dia para este usuário
        calculo_dia = calculo_horas_system.calcular_horas_dia(usuario, hoje)

        if calculo_dia["total_registros"] >= 2:
            # Verificar jornada prevista
            jornada = None
            
            if REFACTORING_ENABLED:
                try:
                    query_jornada = f"SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}"
                    jornada = execute_query(query_jornada, (usuario,), fetch_one=True)
                except Exception as e:
                    log_error("Erro ao buscar jornada do usuário", e, {"usuario": usuario})
                    jornada = None
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        f"SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (usuario,))
                    jornada = cursor.fetchone()
                finally:
                    _return_conn(conn)

            if jornada:
                jornada_inicio = jornada[0] or "08:00"
                jornada_fim = jornada[1] or "17:00"

                # Calcular discrepâncias
                inicio_previsto = ensure_time(jornada_inicio, default=time(8, 0))
                fim_previsto = ensure_time(jornada_fim, default=time(17, 0))

                inicio_real = datetime.strptime(
                    calculo_dia["primeiro_registro"], "%H:%M").time()
                fim_real = datetime.strptime(
                    calculo_dia["ultimo_registro"], "%H:%M").time()

                # Calcular diferenças em minutos
                diff_inicio = (datetime.combine(date.today(), inicio_real) -
                               datetime.combine(date.today(), inicio_previsto)).total_seconds() / 60
                diff_fim = (datetime.combine(date.today(), fim_previsto) -
                            datetime.combine(date.today(), fim_real)).total_seconds() / 60

                # 🔧 CORREÇÃO: Usar tolerância configurada ao invés de 15 min fixo
                if abs(diff_inicio) > limiar_discrepancia or abs(diff_fim) > limiar_discrepancia:
                    discrepancias.append({
                        "usuario": usuario,
                        "inicio_previsto": jornada_inicio,
                        "inicio_real": calculo_dia["primeiro_registro"],
                        "diff_inicio": diff_inicio,
                        "fim_previsto": jornada_fim,
                        "fim_real": calculo_dia["ultimo_registro"],
                        "diff_fim": diff_fim
                    })

        usuarios_processados.add(usuario)

    if discrepancias:
        for disc in discrepancias:
            with st.container():
                st.markdown(f"""
                <div class="discrepancia-alta">
                    <strong>👤 {disc['usuario']}</strong><br>
                    🕐 Entrada: {disc['inicio_real']} (previsto: {disc['inicio_previsto']}) - 
                    Diferença: {abs(disc['diff_inicio']):.0f} min {'(atraso)' if disc['diff_inicio'] > 0 else '(antecipado)'}<br>
                    🕕 Saída: {disc['fim_real']} (previsto: {disc['fim_previsto']}) - 
                    Diferença: {abs(disc['diff_fim']):.0f} min {'(antecipado)' if disc['diff_fim'] > 0 else '(tardio)'}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("✅ Nenhuma discrepância significativa detectada hoje!")


def banco_horas_gestor_interface(banco_horas_system):
    """Interface do banco de horas para gestores"""
    st.markdown("""
    <div class="feature-card">
        <h3>🏦 Banco de Horas Geral</h3>
        <p>Visão geral do saldo de horas de todos os funcionários</p>
    </div>
    """, unsafe_allow_html=True)

    # Obter saldos de todos os usuários
    saldos_usuarios = banco_horas_system.obter_saldos_todos_usuarios()

    if saldos_usuarios:
        # Resumo geral
        total_positivo = sum([s["saldo"]
                             for s in saldos_usuarios if s["saldo"] > 0])
        total_negativo = sum([s["saldo"]
                             for s in saldos_usuarios if s["saldo"] < 0])
        usuarios_positivos = len(
            [s for s in saldos_usuarios if s["saldo"] > 0])
        usuarios_negativos = len(
            [s for s in saldos_usuarios if s["saldo"] < 0])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("➕ Saldo Positivo Total",
                      format_time_duration(total_positivo))
        with col2:
            st.metric("➖ Saldo Negativo Total",
                      format_time_duration(abs(total_negativo)))
        with col3:
            st.metric("✅ Usuários com Saldo +", usuarios_positivos)
        with col4:
            st.metric("❌ Usuários com Saldo -", usuarios_negativos)

        # Tabela de saldos
        st.subheader("📊 Saldos por Funcionário")

        df_saldos = pd.DataFrame(saldos_usuarios)
        df_saldos["Saldo Formatado"] = df_saldos["saldo"].apply(
            format_saldo_display)

        # Ordenar por saldo (negativos primeiro)
        df_saldos = df_saldos.sort_values("saldo")

        st.dataframe(
            df_saldos[["nome", "usuario", "Saldo Formatado"]].rename(columns={
                "nome": "Nome",
                "usuario": "Usuário",
                "Saldo Formatado": "Saldo Atual"
            }),
            width="stretch"
        )

        # Filtros para extrato detalhado
        st.subheader("🔍 Extrato Detalhado por Funcionário")

        col1, col2, col3 = st.columns(3)
        with col1:
            usuario_selecionado = st.selectbox(
                "Selecionar Funcionário",
                options=[s["usuario"] for s in saldos_usuarios],
                format_func=lambda x: next(
                    s["nome"] for s in saldos_usuarios if s["usuario"] == x)
            )
        with col2:
            data_inicio = st.date_input(
                "Data Início", value=date.today() - timedelta(days=30))
        with col3:
            data_fim = st.date_input("Data Fim", value=date.today())

        if usuario_selecionado:
            # Calcular extrato do usuário selecionado
            resultado = banco_horas_system.calcular_banco_horas(
                usuario_selecionado,
                data_inicio.strftime("%Y-%m-%d"),
                data_fim.strftime("%Y-%m-%d")
            )

            if resultado["success"] and resultado["extrato"]:
                # Resumo do período
                total_creditos = sum([item["credito"]
                                     for item in resultado["extrato"]])
                total_debitos = sum([item["debito"]
                                    for item in resultado["extrato"]])
                saldo_periodo = total_creditos - total_debitos

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("➕ Créditos",
                              format_time_duration(total_creditos))
                with col2:
                    st.metric("➖ Débitos", format_time_duration(total_debitos))
                with col3:
                    st.metric("💰 Saldo Período",
                              format_saldo_display(saldo_periodo))

                # Tabela do extrato
                df_extrato = pd.DataFrame(resultado["extrato"])
                df_extrato["Crédito"] = df_extrato["credito"].apply(
                    lambda x: f"+{format_time_duration(x)}" if x > 0 else "")
                df_extrato["Débito"] = df_extrato["debito"].apply(
                    lambda x: f"-{format_time_duration(x)}" if x > 0 else "")
                df_extrato["Saldo Parcial"] = df_extrato["saldo_parcial"].apply(
                    format_saldo_display)

                st.dataframe(
                    df_extrato[["data", "descricao", "Crédito", "Débito", "Saldo Parcial"]].rename(columns={
                        "data": "Data",
                        "descricao": "Descrição"
                    }),
                    width="stretch"
                )
            else:
                st.info("📋 Nenhuma movimentação encontrada no período selecionado")
    else:
        st.info("👥 Nenhum funcionário encontrado")


def aprovar_horas_extras_interface(horas_extras_system):
    """Interface para aprovar horas extras (para gestores)"""
    st.markdown("""
    <div class="feature-card">
        <h3>🕐 Aprovar Horas Extras</h3>
        <p>Gerencie aprovações de solicitações de horas extras</p>
    </div>
    """, unsafe_allow_html=True)

    foco_he_id = st.session_state.get("foco_he_aprovacao_id")
    foco_he_encontrado = False

    # Buscar todas as solicitações pendentes
    solicitacoes = None
    
    if REFACTORING_ENABLED:
        try:
            query_solicitacoes = """
                SELECT * FROM solicitacoes_horas_extras 
                WHERE status = 'pendente'
                ORDER BY data_solicitacao ASC
                LIMIT 200
            """
            solicitacoes = execute_query(query_solicitacoes)
        except Exception as e:
            log_error("Erro ao buscar solicitações de horas extras pendentes", e, {"status": "pendente"})
            solicitacoes = []
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM solicitacoes_horas_extras 
                WHERE status = 'pendente'
                ORDER BY data_solicitacao ASC
                LIMIT 200
            """)
            solicitacoes = cursor.fetchall()
        finally:
            _return_conn(conn)

    if solicitacoes:
        st.warning(
            f"⚠️ {len(solicitacoes)} solicitação(ões) de horas extras aguardando aprovação!")

        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'justificativa',
                   'aprovador_solicitado', 'status', 'data_solicitacao', 'aprovado_por',
                   'data_aprovacao', 'observacoes']

        for solicitacao_raw in solicitacoes:
            solicitacao = dict(zip(colunas, solicitacao_raw))

            expandir_he = bool(foco_he_id) and str(solicitacao['id']) == str(foco_he_id)
            if expandir_he:
                foco_he_encontrado = True

            with st.expander(f"⏳ {solicitacao['usuario']} - {solicitacao['data']} ({solicitacao['hora_inicio']} às {solicitacao['hora_fim']})", expanded=expandir_he):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(f"**Funcionário:** {solicitacao['usuario']}")
                    st.write(f"**Data:** {solicitacao['data']}")
                    st.write(
                        f"**Horário:** {solicitacao['hora_inicio']} às {solicitacao['hora_fim']}")
                    st.write(
                        f"**Justificativa:** {solicitacao['justificativa']}")
                    st.write(
                        f"**Aprovador Solicitado:** {solicitacao['aprovador_solicitado']}")
                    st.write(
                        f"**Solicitado em:** {format_datetime_safe(solicitacao['data_solicitacao'], '%d/%m/%Y às %H:%M')}")

                with col2:
                    observacoes = st.text_area(
                        f"Observações", key=f"obs_gestor_{solicitacao['id']}")

                    col_aprovar, col_rejeitar = st.columns(2)
                    with col_aprovar:
                        if st.button("✅ Aprovar", key=f"aprovar_gestor_{solicitacao['id']}"):
                            resultado = horas_extras_system.aprovar_solicitacao(
                                solicitacao['id'],
                                st.session_state.usuario,
                                observacoes
                            )
                            if resultado["success"]:
                                log_security_event("HORA_EXTRA_APPROVED", usuario=st.session_state.usuario, context={"solicitacao_id": solicitacao['id'], "funcionario": solicitacao['usuario']})
                                st.success("✅ Solicitação aprovada!")
                                st.rerun()
                            else:
                                log_error("Erro ao aprovar solicitação de hora extra", resultado.get('message', ''), {"solicitacao_id": solicitacao['id']})
                                st.error(f"❌ {resultado['message']}")

                    with col_rejeitar:
                        if st.button("❌ Rejeitar", key=f"rejeitar_gestor_{solicitacao['id']}", type="secondary"):
                            if observacoes.strip():
                                resultado = horas_extras_system.rejeitar_solicitacao(
                                    solicitacao['id'],
                                    st.session_state.usuario,
                                    observacoes
                                )
                                if resultado["success"]:
                                    log_security_event("HORA_EXTRA_REJECTED", usuario=st.session_state.usuario, context={"solicitacao_id": solicitacao['id'], "funcionario": solicitacao['usuario'], "motivo": observacoes})
                                    st.success("❌ Solicitação rejeitada!")
                                    st.rerun()
                                else:
                                    log_error("Erro ao rejeitar solicitação de hora extra", resultado.get('message', ''), {"solicitacao_id": solicitacao['id']})
                                    st.error(f"❌ {resultado['message']}")
                            else:
                                st.warning(
                                    "⚠️ Observações são obrigatórias para rejeição")
    else:
        st.info("📋 Nenhuma solicitação de horas extras aguardando aprovação")

    if foco_he_id and foco_he_encontrado and "foco_he_aprovacao_id" in st.session_state:
        del st.session_state["foco_he_aprovacao_id"]


def aprovar_correcoes_registros_interface():
    """Interface para gestor aprovar correções de registros solicitadas por funcionários"""
    st.markdown("""
    <div class="feature-card">
        <h3>🔧 Aprovar Correções de Registros</h3>
        <p>Gerencie solicitações de correção de ponto dos funcionários</p>
    </div>
    """, unsafe_allow_html=True)

    foco_correcao_id = st.session_state.get("foco_correcao_aprovacao_id")
    foco_encontrado = False

    # Abas para diferentes status
    tab1, tab2, tab3 = st.tabs([
        "⏳ Pendentes",
        "✅ Aprovadas",
        "❌ Rejeitadas"
    ])

    with tab1:
        st.markdown("### ⏳ Correções Aguardando Aprovação")

        pendentes = None
        conn = get_connection()
        try:
            cursor = conn.cursor()
            pendentes = _execute_select_with_legacy_fallback(
                cursor,
                """
                    SELECT c.id, c.usuario, c.registro_id, c.data_hora_original, c.data_hora_nova,
                           c.tipo_original, c.tipo_novo, c.modalidade_original, c.modalidade_nova,
                           c.projeto_original, c.projeto_novo, c.justificativa,
                           c.data_solicitacao, u.nome_completo,
                           COALESCE(c.tipo_solicitacao, 'ajuste_registro'), c.data_referencia,
                           c.hora_inicio_solicitada, c.hora_saida_solicitada
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'pendente'
                    ORDER BY c.data_solicitacao DESC
                """,
                (),
                legacy_query="""
                    SELECT c.id, c.usuario, c.registro_id, c.data_hora_original, c.data_hora_nova,
                           c.tipo_original, c.tipo_novo, c.modalidade_original, c.modalidade_nova,
                           c.projeto_original, c.projeto_novo, c.justificativa,
                           c.data_solicitacao, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'pendente'
                    ORDER BY c.data_solicitacao DESC
                """,
                legacy_suffix=('ajuste_registro', None, None, None),
            )
        finally:
            _return_conn(conn)

        if pendentes:
            st.info(f"📋 {len(pendentes)} solicitação(ões) aguardando aprovação")

            for correcao in pendentes:
                (correcao_id, usuario, registro_id, dt_original, dt_nova,
                 tipo_orig, tipo_novo, mod_orig, mod_nova, proj_orig, proj_novo,
                 justificativa, data_solicitacao, nome_completo,
                 tipo_solicitacao, data_referencia, hora_inicio_sol, hora_saida_sol) = correcao

                if tipo_solicitacao == 'complemento_jornada':
                    titulo = f"⏳ {nome_completo or usuario} - {data_referencia} (Complemento de Jornada)"
                else:
                    dt_base = safe_datetime_parse(dt_original)
                    titulo_data = dt_base.strftime('%d/%m/%Y %H:%M') if dt_base else str(dt_original)
                    titulo = f"⏳ {nome_completo or usuario} - {titulo_data}"

                expandir = bool(foco_correcao_id) and str(correcao_id) == str(foco_correcao_id)
                if expandir:
                    foco_encontrado = True

                with st.expander(titulo, expanded=expandir):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                        st.markdown(f"**Solicitado em:** {format_datetime_safe(data_solicitacao, '%d/%m/%Y às %H:%M')}")
                        
                        st.markdown("---")
                        st.markdown("### 🔄 Alterações Solicitadas")
                        if tipo_solicitacao == 'complemento_jornada':
                            st.markdown(f"**Data:** `{data_referencia}`")
                            st.markdown(f"**Hora de início solicitada:** `{hora_inicio_sol}`")
                            st.markdown(f"**Hora de saída solicitada:** `{hora_saida_sol}`")
                            if dt_original:
                                st.markdown(f"**Registro original existente:** `{dt_original}` ({tipo_orig or 'N/A'})")
                        else:
                            if dt_original != dt_nova:
                                dt_orig_dt = safe_datetime_parse(dt_original)
                                dt_nova_dt = safe_datetime_parse(dt_nova)
                                dt_orig_fmt = dt_orig_dt.strftime('%d/%m/%Y %H:%M') if dt_orig_dt else str(dt_original)
                                dt_nova_fmt = dt_nova_dt.strftime('%d/%m/%Y %H:%M') if dt_nova_dt else str(dt_nova)
                                st.markdown(f"**Data/Hora:** `{dt_orig_fmt}` → `{dt_nova_fmt}`")
                            if tipo_orig != tipo_novo:
                                st.markdown(f"**Tipo:** `{tipo_orig}` → `{tipo_novo}`")
                            if mod_orig != mod_nova:
                                st.markdown(f"**Modalidade:** `{mod_orig or 'N/A'}` → `{mod_nova or 'N/A'}`")
                            if proj_orig != proj_novo:
                                st.markdown(f"**Projeto:** `{proj_orig or 'N/A'}` → `{proj_novo or 'N/A'}`")
                        
                        st.markdown("---")
                        st.markdown("**Justificativa:**")
                        st.info(justificativa or "Sem justificativa")

                    with col2:
                        st.markdown("### 🎯 Ações")

                        # Observações do gestor
                        observacoes = st.text_area(
                            "Observações:",
                            placeholder="Adicione comentários (opcional)",
                            key=f"obs_corr_{correcao_id}",
                            height=100
                        )

                        st.markdown("---")

                        # Botões de aprovação/rejeição
                        col_a, col_b = st.columns(2)

                        with col_a:
                            if st.button("✅ Aprovar", key=f"aprovar_corr_{correcao_id}", width="stretch", type="primary"):
                                try:
                                    conn = get_connection()
                                    try:
                                        cursor = conn.cursor()
                                        affected_ids = []

                                        data_alvo_auditoria = None
                                        if tipo_solicitacao == 'complemento_jornada' and data_referencia:
                                            data_alvo_auditoria = str(data_referencia)
                                        else:
                                            dt_aud = safe_datetime_parse(dt_nova) or safe_datetime_parse(dt_original)
                                            if dt_aud:
                                                data_alvo_auditoria = dt_aud.strftime("%Y-%m-%d")

                                        entrada_orig = saida_orig = None
                                        if data_alvo_auditoria:
                                            entrada_orig, saida_orig, _ = obter_entrada_saida_dia_cursor(
                                                cursor, usuario, data_alvo_auditoria
                                            )

                                        if tipo_solicitacao == 'complemento_jornada':
                                            if not data_referencia or not hora_inicio_sol or not hora_saida_sol:
                                                raise ValueError("Solicitação de complemento inválida: campos obrigatórios ausentes")

                                            dt_inicio_aprovado = datetime.strptime(f"{data_referencia} {hora_inicio_sol}", "%Y-%m-%d %H:%M")
                                            dt_saida_aprovado = datetime.strptime(f"{data_referencia} {hora_saida_sol}", "%Y-%m-%d %H:%M")
                                            if dt_saida_aprovado <= dt_inicio_aprovado:
                                                raise ValueError("Hora de saída deve ser maior que hora de início")

                                            cursor.execute(f"""
                                                SELECT id, data_hora, tipo, modalidade, projeto, atividade
                                                FROM registros_ponto
                                                WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
                                                ORDER BY data_hora ASC
                                            """, (usuario, data_referencia))
                                            registros_dia = cursor.fetchall()

                                            modalidade_base = mod_nova or mod_orig
                                            projeto_base = proj_novo or proj_orig
                                            atividade_base = None

                                            if len(registros_dia) == 0:
                                                cursor.execute(f"""
                                                    INSERT INTO registros_ponto
                                                    (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                                                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'inicio', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                                """, (
                                                    usuario,
                                                    dt_inicio_aprovado,
                                                    modalidade_base,
                                                    projeto_base,
                                                    atividade_base,
                                                    "Registro criado via aprovação de complemento"
                                                ))
                                                cursor.execute(f"""
                                                    INSERT INTO registros_ponto
                                                    (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                                                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'fim', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                                """, (
                                                    usuario,
                                                    dt_saida_aprovado,
                                                    modalidade_base,
                                                    projeto_base,
                                                    atividade_base,
                                                    "Registro criado via aprovação de complemento"
                                                ))
                                            elif len(registros_dia) == 1:
                                                reg_id, _, tipo_existente, mod_existente, proj_existente, atividade_existente = registros_dia[0]
                                                tipo_existente = str(tipo_existente or '').strip().lower()
                                                modalidade_base = mod_existente or modalidade_base
                                                projeto_base = proj_existente or projeto_base
                                                atividade_base = atividade_existente

                                                if tipo_existente in ('início', 'inicio', 'entrada'):
                                                    cursor.execute(f"""
                                                        UPDATE registros_ponto
                                                        SET data_hora = {SQL_PLACEHOLDER}, tipo = 'inicio', modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
                                                        WHERE id = {SQL_PLACEHOLDER}
                                                    """, (dt_inicio_aprovado, modalidade_base, projeto_base, reg_id))
                                                    affected_ids.append(reg_id)
                                                    cursor.execute(f"""
                                                        INSERT INTO registros_ponto
                                                        (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                                                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'fim', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                                    """, (
                                                        usuario,
                                                        dt_saida_aprovado,
                                                        modalidade_base,
                                                        projeto_base,
                                                        atividade_base,
                                                        "Registro criado via aprovação de complemento"
                                                    ))
                                                elif tipo_existente in ('fim', 'saída', 'saida'):
                                                    cursor.execute(f"""
                                                        UPDATE registros_ponto
                                                        SET data_hora = {SQL_PLACEHOLDER}, tipo = 'fim', modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
                                                        WHERE id = {SQL_PLACEHOLDER}
                                                    """, (dt_saida_aprovado, modalidade_base, projeto_base, reg_id))
                                                    affected_ids.append(reg_id)
                                                    cursor.execute(f"""
                                                        INSERT INTO registros_ponto
                                                        (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                                                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'inicio', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                                    """, (
                                                        usuario,
                                                        dt_inicio_aprovado,
                                                        modalidade_base,
                                                        projeto_base,
                                                        atividade_base,
                                                        "Registro criado via aprovação de complemento"
                                                    ))
                                                else:
                                                    cursor.execute(f"""
                                                        INSERT INTO registros_ponto
                                                        (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                                                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'inicio', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                                    """, (
                                                        usuario,
                                                        dt_inicio_aprovado,
                                                        modalidade_base,
                                                        projeto_base,
                                                        atividade_base,
                                                        "Registro criado via aprovação de complemento"
                                                    ))
                                                    cursor.execute(f"""
                                                        INSERT INTO registros_ponto
                                                        (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao)
                                                        VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, 'fim', {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                                    """, (
                                                        usuario,
                                                        dt_saida_aprovado,
                                                        modalidade_base,
                                                        projeto_base,
                                                        atividade_base,
                                                        "Registro criado via aprovação de complemento"
                                                    ))
                                            else:
                                                # Se já houver múltiplos registros, ajusta apenas o primeiro início e o último fim.
                                                inicio_id = None
                                                fim_id = None
                                                for reg in registros_dia:
                                                    reg_tipo = str(reg[2] or '').strip().lower()
                                                    if reg_tipo in ('início', 'inicio', 'entrada') and inicio_id is None:
                                                        inicio_id = reg[0]
                                                    if reg_tipo in ('fim', 'saída', 'saida'):
                                                        fim_id = reg[0]

                                                if inicio_id is None:
                                                    inicio_id = registros_dia[0][0]
                                                if fim_id is None:
                                                    fim_id = registros_dia[-1][0]

                                                cursor.execute(f"""
                                                    UPDATE registros_ponto
                                                    SET data_hora = {SQL_PLACEHOLDER}, tipo = 'inicio'
                                                    WHERE id = {SQL_PLACEHOLDER}
                                                """, (dt_inicio_aprovado, inicio_id))
                                                cursor.execute(f"""
                                                    UPDATE registros_ponto
                                                    SET data_hora = {SQL_PLACEHOLDER}, tipo = 'fim'
                                                    WHERE id = {SQL_PLACEHOLDER}
                                                """, (dt_saida_aprovado, fim_id))
                                                affected_ids.extend([inicio_id, fim_id])

                                            # Recalcular após a correção aprovada (sem alterar a regra atual de cálculo)
                                            try:
                                                CalculoHorasSystem().calcular_horas_dia(usuario, data_referencia)
                                                BancoHorasSystem().calcular_banco_horas(usuario, data_referencia, data_referencia)
                                            except Exception as recalc_err:
                                                logger.warning(f"Falha no recálculo pós-aprovação da correção {correcao_id}: {recalc_err}")
                                        else:
                                            tipo_novo_norm = str(tipo_novo or '').strip().lower()
                                            if tipo_novo_norm in ('início', 'inicio', 'entrada', 'fim', 'saída', 'saida'):
                                                dt_ref_novo = safe_datetime_parse(dt_nova) or safe_datetime_parse(dt_original)
                                                if dt_ref_novo is not None:
                                                    data_ref_novo = dt_ref_novo.strftime("%Y-%m-%d")
                                                    if tipo_novo_norm in ('início', 'inicio', 'entrada'):
                                                        tipos_check = ('início', 'inicio', 'entrada')
                                                        tipo_label = 'inicio'
                                                    else:
                                                        tipos_check = ('fim', 'saída', 'saida')
                                                        tipo_label = 'fim'

                                                    cursor.execute(
                                                        f"""
                                                            SELECT COUNT(*)
                                                            FROM registros_ponto
                                                            WHERE usuario = {SQL_PLACEHOLDER}
                                                              AND DATE(data_hora) = {SQL_PLACEHOLDER}
                                                              AND id <> {SQL_PLACEHOLDER}
                                                              AND LOWER(tipo) IN ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                                        """,
                                                        (
                                                            usuario,
                                                            data_ref_novo,
                                                            registro_id,
                                                            tipos_check[0],
                                                            tipos_check[1],
                                                            tipos_check[2],
                                                        ),
                                                    )
                                                    if (cursor.fetchone() or [0])[0] > 0:
                                                        raise ValueError(
                                                            f"Nao e permitido aprovar mais de um registro '{tipo_label}' no mesmo dia. "
                                                            "Apenas intermediario pode se repetir."
                                                        )

                                            cursor.execute(f"""
                                                UPDATE registros_ponto
                                                SET data_hora = {SQL_PLACEHOLDER}, tipo = {SQL_PLACEHOLDER}, modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
                                                WHERE id = {SQL_PLACEHOLDER}
                                            """, (dt_nova, tipo_novo, mod_nova, proj_novo, registro_id))

                                        cursor.execute(f"""
                                            UPDATE solicitacoes_correcao_registro
                                            SET status = 'aprovado', aprovado_por = {SQL_PLACEHOLDER},
                                                data_aprovacao = CURRENT_TIMESTAMP, observacoes = {SQL_PLACEHOLDER}
                                            WHERE id = {SQL_PLACEHOLDER}
                                        """, (st.session_state.usuario, observacoes, correcao_id))

                                        if data_alvo_auditoria:
                                            entrada_corr, saida_corr, _ = obter_entrada_saida_dia_cursor(
                                                cursor, usuario, data_alvo_auditoria
                                            )
                                            registrar_auditoria_alteracao_ponto_cursor(
                                                cursor,
                                                registro_id=registro_id if (tipo_solicitacao != 'complemento_jornada') else None,
                                                usuario_afetado=usuario,
                                                data_registro=data_alvo_auditoria,
                                                entrada_original=entrada_orig,
                                                saida_original=saida_orig,
                                                entrada_corrigida=entrada_corr,
                                                saida_corrigida=saida_corr,
                                                tipo_alteracao=(
                                                    "aprovacao_complemento_jornada"
                                                    if tipo_solicitacao == 'complemento_jornada'
                                                    else "aprovacao_correcao_registro"
                                                ),
                                                realizado_por=st.session_state.usuario,
                                                justificativa=justificativa,
                                                detalhes=observacoes,
                                            )

                                        conn.commit()
                                    finally:
                                        _return_conn(conn)
                                    
                                    st.success("✅ Correção aprovada e registro atualizado!")
                                    log_security_event(
                                        "CORRECAO_REGISTRO_APPROVED",
                                        usuario=st.session_state.usuario,
                                        context={"correcao_id": correcao_id, "funcionario": usuario, "registro_id": registro_id, "tipo": tipo_solicitacao}
                                    )
                                    st.rerun()
                                    
                                except Exception as e:
                                    log_error("Erro ao aprovar correção de registro", str(e), {"correcao_id": correcao_id})
                                    st.error(f"❌ Erro ao aprovar: {str(e)}")

                        with col_b:
                            if st.button("❌ Rejeitar", key=f"rejeitar_corr_{correcao_id}", width="stretch"):
                                st.session_state[f'confirm_reject_corr_{correcao_id}'] = True

                        # Confirmação de rejeição
                        if st.session_state.get(f'confirm_reject_corr_{correcao_id}'):
                            st.warning("⚠️ Confirmar rejeição?")
                            motivo = st.text_area(
                                "Motivo da rejeição:",
                                key=f"motivo_corr_{correcao_id}",
                                placeholder="Explique o motivo (obrigatório)"
                            )

                            col_c, col_d = st.columns(2)
                            with col_c:
                                if st.button("Sim, rejeitar", key=f"confirm_yes_corr_{correcao_id}"):
                                    if not motivo:
                                        st.error("❌ Motivo é obrigatório!")
                                    else:
                                        try:
                                            conn = get_connection()
                                            try:
                                                cursor = conn.cursor()
                                                cursor.execute(f"""
                                                    UPDATE solicitacoes_correcao_registro
                                                    SET status = 'rejeitado', aprovado_por = {SQL_PLACEHOLDER},
                                                        data_aprovacao = CURRENT_TIMESTAMP, observacoes = {SQL_PLACEHOLDER}
                                                    WHERE id = {SQL_PLACEHOLDER}
                                                """, (st.session_state.usuario, motivo, correcao_id))
                                                conn.commit()
                                            finally:
                                                _return_conn(conn)
                                            log_security_event("CORRECAO_REGISTRO_REJECTED", usuario=st.session_state.usuario, context={"correcao_id": correcao_id, "funcionario": usuario, "motivo": motivo})
                                            
                                            st.success("❌ Correção rejeitada")
                                            del st.session_state[f'confirm_reject_corr_{correcao_id}']
                                            st.rerun()
                                            
                                        except Exception as e:
                                            st.error(f"❌ Erro ao rejeitar: {str(e)}")

                            with col_d:
                                if st.button("Cancelar", key=f"confirm_no_corr_{correcao_id}"):
                                    del st.session_state[f'confirm_reject_corr_{correcao_id}']
                                    st.rerun()
        else:
            st.success("✅ Nenhuma correção aguardando aprovação!")

        if foco_correcao_id and foco_encontrado and "foco_correcao_aprovacao_id" in st.session_state:
            del st.session_state["foco_correcao_aprovacao_id"]

    with tab2:
        st.markdown("### ✅ Correções Aprovadas")
        
        aprovadas = None
        conn = get_connection()
        try:
            cursor = conn.cursor()
            aprovadas = _execute_select_with_legacy_fallback(
                cursor,
                """
                    SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.tipo_original, c.tipo_novo, c.data_solicitacao,
                           c.data_aprovacao, c.aprovado_por, c.observacoes, u.nome_completo,
                           COALESCE(c.tipo_solicitacao, 'ajuste_registro'), c.data_referencia,
                           c.hora_inicio_solicitada, c.hora_saida_solicitada
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'aprovado'
                    ORDER BY c.data_aprovacao DESC
                    LIMIT 50
                """,
                (),
                legacy_query="""
                    SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.tipo_original, c.tipo_novo, c.data_solicitacao,
                           c.data_aprovacao, c.aprovado_por, c.observacoes, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'aprovado'
                    ORDER BY c.data_aprovacao DESC
                    LIMIT 50
                """,
                legacy_suffix=('ajuste_registro', None, None, None),
            )
        finally:
            _return_conn(conn)
        
        if aprovadas:
            st.info(f"✅ {len(aprovadas)} correção(ões) aprovada(s)")
            
            for correcao in aprovadas:
                (correcao_id, usuario, dt_original, dt_nova, tipo_orig, tipo_novo,
                 data_solicitacao, data_aprovacao, aprovado_por, observacoes, nome_completo,
                 tipo_solicitacao, data_referencia, hora_inicio_sol, hora_saida_sol) = correcao

                dt_aprov = safe_datetime_parse(data_aprovacao)
                dt_aprov_titulo = dt_aprov.strftime('%d/%m/%Y') if dt_aprov else str(data_aprovacao)
                with st.expander(f"✅ {nome_completo or usuario} - {dt_aprov_titulo}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                        if tipo_solicitacao == 'complemento_jornada':
                            st.markdown(f"**Tipo de solicitação:** Complemento de jornada")
                            st.markdown(f"**Data:** `{data_referencia}`")
                            st.markdown(f"**Horas aprovadas:** `{hora_inicio_sol}` às `{hora_saida_sol}`")
                        else:
                            dt_orig_dt = safe_datetime_parse(dt_original)
                            dt_nova_dt = safe_datetime_parse(dt_nova)
                            dt_orig_fmt = dt_orig_dt.strftime('%d/%m/%Y %H:%M') if dt_orig_dt else str(dt_original)
                            dt_nova_fmt = dt_nova_dt.strftime('%d/%m/%Y %H:%M') if dt_nova_dt else str(dt_nova)
                            st.markdown(f"**Data/Hora:** `{dt_orig_fmt}` → `{dt_nova_fmt}`")
                            if tipo_orig != tipo_novo:
                                st.markdown(f"**Tipo:** `{tipo_orig}` → `{tipo_novo}`")
                    
                    with col2:
                        st.markdown(f"**Aprovado por:** {aprovado_por}")
                        dt_aprov_fmt = dt_aprov.strftime('%d/%m/%Y %H:%M') if dt_aprov else str(data_aprovacao)
                        st.markdown(f"**Data aprovação:** {dt_aprov_fmt}")
                        if observacoes:
                            st.markdown(f"**Observações:** {observacoes}")
        else:
            st.info("📋 Nenhuma correção aprovada ainda")

    with tab3:
        st.markdown("### ❌ Correções Rejeitadas")
        
        rejeitadas = None
        conn = get_connection()
        try:
            cursor = conn.cursor()
            rejeitadas = _execute_select_with_legacy_fallback(
                cursor,
                """
                    SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.data_solicitacao, c.data_aprovacao, c.aprovado_por,
                           c.observacoes, u.nome_completo, COALESCE(c.tipo_solicitacao, 'ajuste_registro'),
                           c.data_referencia
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'rejeitado'
                    ORDER BY c.data_aprovacao DESC
                    LIMIT 50
                """,
                (),
                legacy_query="""
                    SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.data_solicitacao, c.data_aprovacao, c.aprovado_por,
                           c.observacoes, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'rejeitado'
                    ORDER BY c.data_aprovacao DESC
                    LIMIT 50
                """,
                legacy_suffix=('ajuste_registro', None),
            )
        finally:
            _return_conn(conn)
        
        if rejeitadas:
            st.warning(f"❌ {len(rejeitadas)} correção(ões) rejeitada(s)")
            
            for correcao in rejeitadas:
                (correcao_id, usuario, dt_original, dt_nova, data_solicitacao,
                 data_rejeicao, rejeitado_por, motivo, nome_completo, tipo_solicitacao,
                 data_referencia) = correcao

                dt_rej = safe_datetime_parse(data_rejeicao)
                dt_rej_titulo = dt_rej.strftime('%d/%m/%Y') if dt_rej else str(data_rejeicao)
                with st.expander(f"❌ {nome_completo or usuario} - {dt_rej_titulo}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    if tipo_solicitacao == 'complemento_jornada':
                        st.markdown(f"**Tipo de solicitação:** Complemento de jornada ({data_referencia})")
                    st.markdown(f"**Rejeitado por:** {rejeitado_por}")
                    dt_rej_fmt = dt_rej.strftime('%d/%m/%Y %H:%M') if dt_rej else str(data_rejeicao)
                    st.markdown(f"**Data rejeição:** {dt_rej_fmt}")
                    st.markdown(f"**Motivo:** {motivo}")
        else:
            st.info("📋 Nenhuma correção rejeitada")


def notificacoes_gestor_interface(horas_extras_system, atestado_system):
    """Interface centralizada de notificações para o gestor"""
    st.markdown("""
    <div class="feature-card">
        <h3>🔔 Central de Notificações</h3>
        <p>Visualize e gerencie todas as solicitações pendentes</p>
    </div>
    """, unsafe_allow_html=True)

    # Abas para diferentes tipos de notificações
    tab1, tab2, tab3 = st.tabs([
        "🕐 Horas Extras",
        "🔧 Correções de Registro",
        "✅ Atestados de Horas"
    ])

    with tab1:
        st.markdown("### 🕐 Solicitações de Horas Extras Pendentes")
        
        # Buscar horas extras pendentes
        he_pendentes = None
        
        if REFACTORING_ENABLED:
            try:
                query_he = """
                      SELECT h.id, h.usuario, h.data, h.hora_inicio, h.hora_fim, h.justificativa,
                          h.data_solicitacao, u.nome_completo
                    FROM solicitacoes_horas_extras h
                    LEFT JOIN usuarios u ON h.usuario = u.usuario
                    WHERE h.status = 'pendente'
                    ORDER BY h.data_solicitacao DESC
                    LIMIT 200
                """
                he_pendentes = execute_query(query_he)
            except Exception as e:
                log_error("Erro ao buscar horas extras pendentes nas notificações", e, {"status": "pendente"})
                he_pendentes = []
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT h.id, h.usuario, h.data, h.hora_inicio, h.hora_fim, h.justificativa,
                           h.data_solicitacao, u.nome_completo
                    FROM solicitacoes_horas_extras h
                    LEFT JOIN usuarios u ON h.usuario = u.usuario
                    WHERE h.status = 'pendente'
                    ORDER BY h.data_solicitacao DESC
                    LIMIT 200
                """)
                he_pendentes = cursor.fetchall()
            finally:
                _return_conn(conn)
        
        if he_pendentes:
            st.info(f"📋 {len(he_pendentes)} solicitação(ões) de horas extras")
            
            for he in he_pendentes:
                # he: id, usuario, data, hora_inicio, hora_fim, justificativa, data_solicitacao, nome_completo
                he_id, usuario, data, hora_inicio, hora_fim, justificativa, data_solicitacao, nome_completo = he

                # Calcular duração em horas a partir de hora_inicio/hora_fim
                horas = 0
                try:
                    if isinstance(hora_inicio, str):
                        fmt = '%H:%M:%S' if hora_inicio.count(':') == 2 else '%H:%M'
                        hi = datetime.strptime(hora_inicio, fmt).time()
                    else:
                        hi = hora_inicio

                    if isinstance(hora_fim, str):
                        fmt = '%H:%M:%S' if hora_fim.count(':') == 2 else '%H:%M'
                        hf = datetime.strptime(hora_fim, fmt).time()
                    else:
                        hf = hora_fim

                    if hi and hf:
                        dt_hi = datetime.combine(date.today(), hi)
                        dt_hf = datetime.combine(date.today(), hf)
                        delta = (dt_hf - dt_hi).total_seconds()
                        if delta < 0:
                            delta += 24 * 3600
                        horas = delta / 3600
                except Exception:
                    horas = 0

                with st.expander(f"⏳ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    st.markdown(f"**Data:** {data}")
                    st.markdown(f"**Horas:** {format_time_duration(horas)}")
                    st.markdown(f"**Solicitado em:** {format_datetime_safe(data_solicitacao, '%d/%m/%Y %H:%M')}")
                    st.markdown("**Justificativa:**")
                    st.info(sanitize_ui_text(justificativa, default="Sem justificativa"))
                    
                    if st.button("Ver detalhes completos", key=f"ver_he_{he_id}"):
                        st.session_state.ir_para_aprovar_horas_extras = True
                        st.session_state.foco_he_aprovacao_id = he_id
                        st.rerun()
        else:
            st.success("✅ Nenhuma solicitação de horas extras pendente")

    with tab2:
        st.markdown("### 🔧 Solicitações de Correção de Registro Pendentes")
        
        corr_pendentes = None
        conn = get_connection()
        try:
            cursor = conn.cursor()
            corr_pendentes = _execute_select_with_legacy_fallback(
                cursor,
                """
                    SELECT c.id, c.registro_id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.justificativa, c.data_solicitacao, u.nome_completo,
                           COALESCE(c.tipo_solicitacao, 'ajuste_registro'), c.data_referencia,
                           c.hora_inicio_solicitada, c.hora_saida_solicitada
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'pendente'
                    ORDER BY c.data_solicitacao DESC
                    LIMIT 200
                """,
                (),
                legacy_query="""
                    SELECT c.id, c.registro_id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.justificativa, c.data_solicitacao, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'pendente'
                    ORDER BY c.data_solicitacao DESC
                    LIMIT 200
                """,
                legacy_suffix=('ajuste_registro', None, None, None),
            ) or []
        except Exception as e:
            log_error("Erro ao buscar correções de registros pendentes nas notificações", e, {"status": "pendente"})
            corr_pendentes = []
        finally:
            _return_conn(conn)
        
        if corr_pendentes:
            st.info(f"📋 {len(corr_pendentes)} solicitação(ões) de correção")
            
            for correcao in corr_pendentes:
                (corr_id, registro_id, usuario, dt_orig, dt_nova, justificativa,
                 data_solicitacao, nome_completo, tipo_solicitacao, data_referencia,
                 hora_inicio_sol, hora_saida_sol) = correcao

                if tipo_solicitacao == 'complemento_jornada':
                    titulo = f"⏳ {nome_completo or usuario} - {data_referencia} (Entrada/Saida)"
                else:
                    titulo = f"⏳ {nome_completo or usuario} - {format_datetime_safe(dt_orig, '%d/%m/%Y %H:%M')}"

                with st.expander(titulo):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    if tipo_solicitacao == 'complemento_jornada':
                        st.markdown("**Tipo:** Complemento de jornada")
                        st.markdown(f"**Data:** `{data_referencia}`")
                        st.markdown(f"**Entrada solicitada:** `{hora_inicio_sol or '-'}`")
                        st.markdown(f"**Saida solicitada:** `{hora_saida_sol or '-'}`")
                    else:
                        dt_orig_fmt = format_datetime_safe(dt_orig, '%d/%m/%Y %H:%M')
                        dt_nova_fmt = format_datetime_safe(dt_nova, '%d/%m/%Y %H:%M')
                        st.markdown(f"**Alteração:** `{dt_orig_fmt}` → `{dt_nova_fmt}`")
                    st.markdown(f"**Solicitado em:** {format_datetime_safe(data_solicitacao, '%d/%m/%Y %H:%M')}")
                    st.markdown("**Justificativa:**")
                    st.info(sanitize_ui_text(justificativa, default="Sem justificativa"))
                    
                    if st.button("Ver detalhes completos", key=f"ver_corr_{corr_id}"):
                        st.session_state.ir_para_corrigir_registros = True
                        st.session_state.foco_correcao_aprovacao_id = corr_id
                        st.session_state.pendencia_correcao_id_prefill = corr_id
                        st.session_state.pendencia_registro_id_prefill = registro_id
                        st.session_state.pendencia_tipo_solicitacao_prefill = tipo_solicitacao
                        st.session_state.pendencia_data_referencia_prefill = str(data_referencia) if data_referencia else ""
                        st.session_state.pendencia_hora_inicio_prefill = str(hora_inicio_sol) if hora_inicio_sol else ""
                        st.session_state.pendencia_hora_saida_prefill = str(hora_saida_sol) if hora_saida_sol else ""
                        st.session_state.pendencia_datahora_original_prefill = str(dt_orig) if dt_orig else ""
                        st.session_state.pendencia_datahora_nova_prefill = str(dt_nova) if dt_nova else ""
                        st.session_state.pendencia_justificativa_prefill = sanitize_ui_text(justificativa, default="Sem justificativa")
                        st.session_state.pendencia_usuario_prefill = usuario
                        dt_pref = safe_datetime_parse(data_referencia) or safe_datetime_parse(dt_nova) or safe_datetime_parse(dt_orig)
                        if dt_pref:
                            st.session_state.pendencia_data_prefill = dt_pref.strftime("%Y-%m-%d")
                        st.rerun()
        else:
            st.success("✅ Nenhuma solicitação de correção pendente")

    with tab3:
        st.markdown("### ✅ Atestados de Horas Pendentes")
        
        atestados_pendentes = None
        
        if REFACTORING_ENABLED:
            try:
                query_atestados = """
                    SELECT a.id, a.usuario, a.data, a.total_horas, a.motivo,
                           a.data_registro, u.nome_completo
                    FROM atestado_horas a
                    LEFT JOIN usuarios u ON a.usuario = u.usuario
                    WHERE a.status = 'pendente'
                    ORDER BY a.data_registro DESC
                    LIMIT 200
                """
                atestados_pendentes = execute_query(query_atestados)
            except Exception as e:
                log_error("Erro ao buscar atestados de horas pendentes nas notificações", e, {"status": "pendente"})
                atestados_pendentes = []
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT a.id, a.usuario, a.data, a.total_horas, a.motivo,
                           a.data_registro, u.nome_completo
                    FROM atestado_horas a
                    LEFT JOIN usuarios u ON a.usuario = u.usuario
                    WHERE a.status = 'pendente'
                    ORDER BY a.data_registro DESC
                    LIMIT 200
                """)
                atestados_pendentes = cursor.fetchall()
            finally:
                _return_conn(conn)
        
        if atestados_pendentes:
            st.info(f"📋 {len(atestados_pendentes)} atestado(s) pendente(s)")
            
            for atestado in atestados_pendentes:
                atestado_id, usuario, data, horas, motivo, data_registro, nome_completo = atestado
                
                with st.expander(f"⏳ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else format_datetime_safe(data, '%d/%m/%Y')
                    st.markdown(f"**Data:** {data_fmt}")
                    st.markdown(f"**Horas:** {format_time_duration(horas)}")
                    st.markdown(f"**Solicitado em:** {format_datetime_safe(data_registro, '%d/%m/%Y %H:%M')}")
                    st.markdown("**Motivo:**")
                    st.info(motivo or "Sem motivo especificado")
                    
                    if st.button("Ver detalhes completos", key=f"ver_atestado_{atestado_id}"):
                        st.session_state.ir_para_aprovar_atestados = True
                        st.session_state.foco_atestado_aprovacao_id = atestado_id
                        st.rerun()
        else:
            st.success("✅ Nenhum atestado pendente")


# Outras interfaces do gestor (simplificadas)


def auditoria_alteracoes_interface():
    """Painel para consulta de auditoria de alterações e correções."""
    st.markdown("""
    <div class="feature-card">
        <h3>🧾 Auditoria de Alterações</h3>
        <p>Consulte mudanças em registros de ponto e aprovações de correção.</p>
    </div>
    """, unsafe_allow_html=True)

    dias = st.number_input("Período (dias)", min_value=1, max_value=365, value=30, step=1)

    # Montar opções de usuários para filtro (inclui ativos e usuários presentes na auditoria)
    usuarios_map = {}
    try:
        for u in obter_usuarios_ativos():
            usr = (u.get("usuario") or "").strip()
            if usr:
                usuarios_map[usr] = (u.get("nome_completo") or usr).strip()
    except Exception as e:
        logger.debug("Falha ao listar usuários ativos para filtro de auditoria: %s", e)

    try:
        conn_users = get_connection()
        try:
            cur_users = conn_users.cursor()
            cur_users.execute("""
                SELECT DISTINCT usuario_afetado
                FROM auditoria_alteracoes_ponto
                WHERE usuario_afetado IS NOT NULL AND TRIM(usuario_afetado) <> ''
            """)
            for row in (cur_users.fetchall() or []):
                usr = (row[0] or "").strip()
                if usr and usr not in usuarios_map:
                    usuarios_map[usr] = usr

            cur_users.execute("""
                SELECT DISTINCT r.usuario
                FROM auditoria_correcoes c
                LEFT JOIN registros_ponto r ON r.id = c.registro_id
                WHERE r.usuario IS NOT NULL AND TRIM(r.usuario) <> ''
            """)
            for row in (cur_users.fetchall() or []):
                usr = (row[0] or "").strip()
                if usr and usr not in usuarios_map:
                    usuarios_map[usr] = usr
        finally:
            _return_conn(conn_users)
    except Exception as e:
        logger.debug("Falha ao complementar usuários da auditoria: %s", e)

    opcoes_usuario = ["Todos"] + [
        f"{usuarios_map[u]} ({u})" if usuarios_map[u] != u else u
        for u in sorted(usuarios_map.keys())
    ]
    usuario_escolhido = st.selectbox("Filtrar por usuário afetado (opcional)", opcoes_usuario, index=0)

    usuario_filtro = None
    if usuario_escolhido != "Todos":
        if "(" in usuario_escolhido and usuario_escolhido.endswith(")"):
            usuario_filtro = usuario_escolhido.split("(")[-1].replace(")", "").strip()
        else:
            usuario_filtro = usuario_escolhido.strip()

    data_limite = agora_br() - timedelta(days=int(dias))
    params_aud = [data_limite]
    params_corr = [data_limite]
    where_user_aud = ""
    where_user_corr = ""

    if usuario_filtro:
        where_user_aud = f" AND a.usuario_afetado = {SQL_PLACEHOLDER}"
        where_user_corr = f" AND r.usuario = {SQL_PLACEHOLDER}"
        params_aud.append(usuario_filtro)
        params_corr.append(usuario_filtro)

    auditoria_rows = []
    correcoes_rows = []

    try:
        if REFACTORING_ENABLED:
            auditoria_rows = execute_query(
                f"""
                SELECT a.data_alteracao, a.usuario_afetado, a.data_registro,
                       a.entrada_original, a.saida_original, a.entrada_corrigida, a.saida_corrigida,
                       a.tipo_alteracao, a.realizado_por, a.justificativa
                FROM auditoria_alteracoes_ponto a
                  WHERE a.data_alteracao >= {SQL_PLACEHOLDER}
                {where_user_aud}
                ORDER BY a.data_alteracao DESC
                LIMIT 500
                """,
                tuple(params_aud)
            ) or []

            correcoes_rows = execute_query(
                f"""
                SELECT c.data_correcao, r.usuario, c.registro_id, c.gestor, c.justificativa
                FROM auditoria_correcoes c
                LEFT JOIN registros_ponto r ON r.id = c.registro_id
                WHERE c.data_correcao >= {SQL_PLACEHOLDER}
                {where_user_corr}
                ORDER BY c.data_correcao DESC
                LIMIT 500
                """,
                tuple(params_corr)
            ) or []
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT a.data_alteracao, a.usuario_afetado, a.data_registro,
                           a.entrada_original, a.saida_original, a.entrada_corrigida, a.saida_corrigida,
                           a.tipo_alteracao, a.realizado_por, a.justificativa
                    FROM auditoria_alteracoes_ponto a
                          WHERE a.data_alteracao >= {SQL_PLACEHOLDER}
                    {where_user_aud}
                    ORDER BY a.data_alteracao DESC
                    LIMIT 500
                    """,
                    tuple(params_aud)
                )
                auditoria_rows = cursor.fetchall() or []

                cursor.execute(
                    f"""
                    SELECT c.data_correcao, r.usuario, c.registro_id, c.gestor, c.justificativa
                    FROM auditoria_correcoes c
                    LEFT JOIN registros_ponto r ON r.id = c.registro_id
                    WHERE c.data_correcao >= {SQL_PLACEHOLDER}
                    {where_user_corr}
                    ORDER BY c.data_correcao DESC
                    LIMIT 500
                    """,
                    tuple(params_corr)
                )
                correcoes_rows = cursor.fetchall() or []
            finally:
                _return_conn(conn)
    except Exception as e:
        st.error(f"❌ Erro ao carregar auditoria: {e}")
        return

    st.markdown("#### 🔄 Histórico de Alterações de Ponto")
    df_aud = None
    if auditoria_rows:
        df_aud = pd.DataFrame(
            auditoria_rows,
            columns=[
                "Data Alteração", "Usuário", "Data Registro", "Entrada Original", "Saída Original",
                "Entrada Corrigida", "Saída Corrigida", "Tipo", "Realizado Por", "Justificativa"
            ]
        )
        st.dataframe(df_aud, width="stretch", hide_index=True)
    else:
        st.info("Nenhuma alteração de ponto encontrada no período.")

    st.markdown("#### ✅ Auditoria de Correções Aplicadas")
    df_corr = None
    if correcoes_rows:
        df_corr = pd.DataFrame(
            correcoes_rows,
            columns=["Data Correção", "Usuário", "Registro ID", "Gestor", "Justificativa"]
        )
        st.dataframe(df_corr, width="stretch", hide_index=True)
    else:
        st.info("Nenhuma correção aplicada encontrada no período.")

    # Exportação consolidada em Excel (duas abas)
    if df_aud is not None or df_corr is not None:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if df_aud is not None:
                df_aud.to_excel(writer, sheet_name='Auditoria_Alteracoes', index=False)
            if df_corr is not None:
                df_corr.to_excel(writer, sheet_name='Auditoria_Correcoes', index=False)

        sufixo_usuario = usuario_filtro if usuario_filtro else "todos"
        nome_arquivo = f"auditoria_{sufixo_usuario}_{agora_br().strftime('%Y%m%d_%H%M')}.xlsx"

        safe_download_button(
            label="📥 Baixar Auditoria em Excel",
            data=output.getvalue(),
            file_name=nome_arquivo,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_auditoria_excel"
        )


def aprovar_atestados_interface(atestado_system):
    """Interface para aprovar atestados de horas"""
    st.markdown("""
    <div class="feature-card">
        <h3>✅ Aprovar Atestados de Horas</h3>
        <p>Gerencie solicitações de atestados de horas dos funcionários</p>
    </div>
    """, unsafe_allow_html=True)

    foco_atestado_id = st.session_state.get("foco_atestado_aprovacao_id")
    foco_atestado_encontrado = False

    # Abas para diferentes status
    tab1, tab2, tab3, tab4 = st.tabs([
        "⏳ Pendentes",
        "✅ Aprovados",
        "❌ Rejeitados",
        "📊 Todos"
    ])

    with tab1:
        st.markdown("### ⏳ Solicitações Pendentes de Aprovação")

        # Buscar atestados pendentes
        if REFACTORING_ENABLED:
            try:
                query = """
                    SELECT a.id, a.usuario, a.data, a.total_horas, 
                           a.motivo, a.data_registro, a.arquivo_comprovante,
                           u.nome_completo
                    FROM atestado_horas a
                    LEFT JOIN usuarios u ON a.usuario = u.usuario
                    WHERE a.status = 'pendente'
                    ORDER BY a.data_registro DESC
                """
                pendentes = execute_query(query)
                if not pendentes:
                    pendentes = []
            except Exception as e:
                log_error("Erro ao buscar atestados pendentes", e, {})
                st.error("❌ Erro ao buscar atestados")
                return
        else:
            # Fallback original
            conn = get_connection()
            try:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT a.id, a.usuario, a.data, a.total_horas, 
                           a.motivo, a.data_registro, a.arquivo_comprovante,
                           u.nome_completo
                    FROM atestado_horas a
                    LEFT JOIN usuarios u ON a.usuario = u.usuario
                    WHERE a.status = 'pendente'
                    ORDER BY a.data_registro DESC
                """)
                pendentes = cursor.fetchall()
            finally:
                _return_conn(conn)

        if pendentes:
            st.info(f"📋 {len(pendentes)} solicitação(ões) aguardando aprovação")

            for atestado in pendentes:
                atestado_id, usuario, data, horas, justificativa, data_solicitacao, arquivo_id, nome_completo = atestado

                expandir_atestado = bool(foco_atestado_id) and str(atestado_id) == str(foco_atestado_id)
                if expandir_atestado:
                    foco_atestado_encontrado = True

                with st.expander(f"⏳ {nome_completo or usuario} - {data} - {format_time_duration(horas)}", expanded=expandir_atestado):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(
                            f"**Funcionário:** {nome_completo or usuario}")
                        # Data pode vir como date (PostgreSQL) ou string (SQLite)
                        data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else format_datetime_safe(data, '%d/%m/%Y')
                        st.markdown(f"**Data do Atestado:** {data_fmt}")
                        st.markdown(
                            f"**Horas Trabalhadas:** {format_time_duration(horas)}")
                        st.markdown(
                            f"**Solicitado em:** {format_datetime_safe(data_solicitacao, '%d/%m/%Y às %H:%M')}")

                        st.markdown("---")
                        st.markdown("**Justificativa:**")
                        st.info(justificativa or "Sem justificativa")

                        # Arquivo anexo
                        if arquivo_id:
                            st.markdown("---")
                            st.markdown("**📎 Documento Anexado:**")

                            # Buscar informações do arquivo pelo caminho
                            conn = get_connection()
                            try:
                                cursor = conn.cursor()
                                cursor.execute(
                                    f"SELECT id, nome_original, tamanho, tipo_arquivo FROM uploads WHERE caminho = {SQL_PLACEHOLDER}",
                                    (arquivo_id,)
                                )
                                arquivo_info = cursor.fetchone()
                            finally:
                                _return_conn(conn)

                            if arquivo_info:
                                id_arquivo, nome_arq, tamanho, tipo_arquivo = arquivo_info
                                st.write(
                                    f"{get_file_icon(tipo_arquivo)} **{nome_arq}** ({format_file_size(tamanho)})")

                                # Botão de download
                                from upload_system import UploadSystem
                                upload_sys = UploadSystem()
                                content, _ = upload_sys.get_file_content(
                                    id_arquivo, usuario)
                                if content:
                                    safe_download_button(
                                        label="⬇️ Baixar Documento",
                                        data=content,
                                        file_name=nome_arq,
                                        mime=tipo_arquivo,
                                        key=f"download_{atestado_id}"
                                    )

                                    # Visualização de imagem
                                    if is_image_file(tipo_arquivo):
                                        st.image(
                                            content, caption=nome_arq, width=400)
                            else:
                                st.warning(f"⚠️ Arquivo não encontrado no sistema: {arquivo_id}")
                        else:
                            st.info("ℹ️ Sem comprovante anexado")

                    with col2:
                        st.markdown("### 🎯 Ações")

                        # Observações do gestor
                        observacoes = st.text_area(
                            "Observações:",
                            placeholder="Adicione comentários (opcional)",
                            key=f"obs_{atestado_id}",
                            height=100
                        )

                        st.markdown("---")

                        # Botões de aprovação/rejeição
                        col_a, col_b = st.columns(2)

                        with col_a:
                            if st.button("✅ Aprovar", key=f"aprovar_{atestado_id}", width="stretch", type="primary"):
                                resultado = atestado_system.aprovar_atestado(
                                    atestado_id,
                                    st.session_state.usuario,
                                    observacoes
                                )

                                if resultado['success']:
                                    log_security_event("ATTESTATION_APPROVED", usuario=st.session_state.usuario, context={"atestado_id": atestado_id, "usuario_afetado": usuario})
                                    st.success(
                                        "✅ Atestado aprovado com sucesso!")
                                    st.rerun()
                                else:
                                    log_error("Erro ao aprovar atestado", resultado.get('message', ''), {"atestado_id": atestado_id})
                                    st.error(f"❌ Erro: {resultado['message']}")

                        with col_b:
                            if st.button("❌ Rejeitar", key=f"rejeitar_{atestado_id}", width="stretch"):
                                st.session_state[f'confirm_reject_{atestado_id}'] = True

                        # Confirmação de rejeição
                        if st.session_state.get(f'confirm_reject_{atestado_id}'):
                            st.warning("⚠️ Confirmar rejeição?")
                            motivo = st.text_area(
                                "Motivo da rejeição:",
                                key=f"motivo_{atestado_id}",
                                placeholder="Explique o motivo (obrigatório)"
                            )

                            col_c, col_d = st.columns(2)
                            with col_c:
                                if st.button("Sim, rejeitar", key=f"confirm_yes_{atestado_id}"):
                                    if not motivo:
                                        st.error("❌ Motivo é obrigatório!")
                                    else:
                                        resultado = atestado_system.rejeitar_atestado(
                                            atestado_id,
                                            st.session_state.usuario,
                                            motivo
                                        )

                                        if resultado['success']:
                                            log_security_event("ATTESTATION_REJECTED", usuario=st.session_state.usuario, context={"atestado_id": atestado_id, "usuario_afetado": usuario, "motivo": motivo[:100]})
                                            st.success("❌ Atestado rejeitado")
                                            del st.session_state[f'confirm_reject_{atestado_id}']
                                            st.rerun()
                                        else:
                                            log_error("Erro ao rejeitar atestado", resultado.get('message', ''), {"atestado_id": atestado_id})
                                            st.error(
                                                f"❌ Erro: {resultado['message']}")

                            with col_d:
                                if st.button("Cancelar", key=f"confirm_no_{atestado_id}"):
                                    del st.session_state[f'confirm_reject_{atestado_id}']
                                    st.rerun()
        else:
            st.success("✅ Nenhuma solicitação aguardando aprovação!")

        if foco_atestado_id and foco_atestado_encontrado and "foco_atestado_aprovacao_id" in st.session_state:
            del st.session_state["foco_atestado_aprovacao_id"]

    with tab2:
        st.markdown("### ✅ Atestados Aprovados")

        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            dias_filtro = st.selectbox("Período:", [
                                       "Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias", "Todos"], key="filtro_aprovados")
        with col2:
            busca_usuario = st.text_input(
                "🔍 Buscar funcionário:", key="busca_aprovados")

        # Determinar período
        if dias_filtro == "Últimos 7 dias":
            dias = 7
        elif dias_filtro == "Últimos 30 dias":
            dias = 30
        elif dias_filtro == "Últimos 90 dias":
            dias = 90
        else:
            dias = None

        # Buscar aprovados
        conn = get_connection()
        try:
            cursor = conn.cursor()

            query = """
                SELECT a.id, a.usuario, a.data, a.total_horas, 
                       a.motivo, a.data_aprovacao, a.aprovado_por,
                       a.observacoes, u.nome_completo, u2.nome_completo as aprovador_nome
                FROM atestado_horas a
                LEFT JOIN usuarios u ON a.usuario = u.usuario
                LEFT JOIN usuarios u2 ON a.aprovado_por = u2.usuario
                WHERE a.status = 'aprovado'
            """
            params = []

            if dias:
                # Compatível com PostgreSQL e SQLite: passamos a data limite via parâmetro
                data_limite = (date.today() - timedelta(days=dias)).strftime("%Y-%m-%d")
                query += f" AND DATE(a.data_aprovacao) >= {SQL_PLACEHOLDER}"
                params.append(data_limite)

            if busca_usuario:
                query += f" AND (a.usuario LIKE {SQL_PLACEHOLDER} OR u.nome_completo LIKE {SQL_PLACEHOLDER})"
                params.extend([f'%{busca_usuario}%', f'%{busca_usuario}%'])

            query += " ORDER BY a.data_aprovacao DESC"

            cursor.execute(query, params)
            aprovados = cursor.fetchall()
        finally:
            _return_conn(conn)

        if aprovados:
            st.info(f"✅ {len(aprovados)} atestado(s) aprovado(s)")

            for atestado in aprovados:
                atestado_id, usuario, data, horas, justificativa, data_aprovacao, aprovado_por, observacoes, nome_completo, aprovador_nome = atestado

                with st.expander(f"✅ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(
                            f"**Funcionário:** {nome_completo or usuario}")
                        data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else format_datetime_safe(data, '%d/%m/%Y')
                        st.markdown(f"**Data:** {data_fmt}")
                        st.markdown(
                            f"**Horas:** {format_time_duration(horas)}")
                        st.markdown(
                            f"**Justificativa:** {justificativa or 'N/A'}")

                        st.markdown("---")
                        st.success(
                            f"✅ Aprovado por **{aprovador_nome or aprovado_por}** em {format_datetime_safe(data_aprovacao, '%d/%m/%Y às %H:%M')}")

                        if observacoes:
                            st.info(f"💬 **Observações:** {observacoes}")

                    with col2:
                        # Opção de reverter aprovação
                        if st.button("🔄 Reverter", key=f"reverter_{atestado_id}", width="stretch"):
                            st.session_state[f'confirm_reverter_{atestado_id}'] = True

                        if st.session_state.get(f'confirm_reverter_{atestado_id}'):
                            st.warning("⚠️ Reverter aprovação?")
                            motivo_rev = st.text_input(
                                "Motivo:", key=f"motivo_rev_{atestado_id}")

                            if st.button("Confirmar", key=f"conf_rev_{atestado_id}"):
                                if motivo_rev:
                                    conn = get_connection()
                                    try:
                                        cursor = conn.cursor()
                                        cursor.execute(f"""
                                            UPDATE atestado_horas 
                                            SET status = 'pendente', 
                                                data_aprovacao = NULL,
                                                aprovado_por = NULL,
                                                observacoes = {SQL_PLACEHOLDER}
                                            WHERE id = {SQL_PLACEHOLDER}
                                        """, (f"Revertido: {motivo_rev}", atestado_id))
                                        conn.commit()
                                    finally:
                                        _return_conn(conn)

                                    st.success("🔄 Aprovação revertida!")
                                    del st.session_state[f'confirm_reverter_{atestado_id}']
                                    st.rerun()
                                else:
                                    st.error("Motivo obrigatório!")
        else:
            st.info("📁 Nenhum atestado aprovado encontrado")

    with tab3:
        st.markdown("### ❌ Atestados Rejeitados")

        # Buscar rejeitados
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Tabela e colunas alinhadas ao schema atual (ver AtestadoHorasSystem)
            cursor.execute("""
                SELECT a.id, a.usuario, a.data, a.total_horas, 
                       a.motivo, a.data_aprovacao, a.aprovado_por,
                       a.observacoes, u.nome_completo
                FROM atestado_horas a
                LEFT JOIN usuarios u ON a.usuario = u.usuario
                WHERE a.status = 'rejeitado'
                ORDER BY a.data_aprovacao DESC
                LIMIT 50
            """)
            rejeitados = cursor.fetchall()
        finally:
            _return_conn(conn)

        if rejeitados:
            st.warning(f"❌ {len(rejeitados)} atestado(s) rejeitado(s)")

            for atestado in rejeitados:
                atestado_id, usuario, data, horas, motivo, data_rejeicao, rejeitado_por, observacoes, nome_completo = atestado

                with st.expander(f"❌ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else format_datetime_safe(data, '%d/%m/%Y')
                    st.markdown(f"**Data:** {data_fmt}")
                    st.markdown(f"**Horas:** {format_time_duration(horas)}")
                    st.markdown(f"**Motivo:** {motivo or 'N/A'}")

                    st.markdown("---")
                    # No schema atual, rejeição usa as colunas aprovado_por/data_aprovacao
                    rejeitador_display = rejeitado_por or 'gestor'
                    st.error(
                        f"❌ Rejeitado por **{rejeitador_display}** em {format_datetime_safe(data_rejeicao, '%d/%m/%Y às %H:%M')}")

                    if observacoes:
                        st.warning(
                            f"📝 **Observações:** {observacoes}")
        else:
            st.info("📁 Nenhum atestado rejeitado")

    with tab4:
        st.markdown("### 📊 Todos os Atestados")

        # Estatísticas gerais
        conn = get_connection()
        try:
            cursor = conn.cursor()

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                cursor.execute("SELECT COUNT(*) FROM atestados_horas")
                total = cursor.fetchone()[0]
                st.metric("Total", total)

            with col2:
                cursor.execute(
                    "SELECT COUNT(*) FROM atestados_horas WHERE status = 'pendente'")
                pendentes_count = cursor.fetchone()[0]
                st.metric("Pendentes", pendentes_count)

            with col3:
                cursor.execute(
                    "SELECT COUNT(*) FROM atestados_horas WHERE status = 'aprovado'")
                aprovados_count = cursor.fetchone()[0]
                st.metric("Aprovados", aprovados_count)

            with col4:
                cursor.execute(
                    "SELECT COUNT(*) FROM atestados_horas WHERE status = 'rejeitado'")
                rejeitados_count = cursor.fetchone()[0]
                st.metric("Rejeitados", rejeitados_count)

            # Listagem completa
            st.markdown("---")

            cursor.execute("""
                SELECT a.id, a.usuario, a.data, a.total_horas, 
                       a.status, a.data_registro, u.nome_completo
                FROM atestado_horas a
                LEFT JOIN usuarios u ON a.usuario = u.usuario
                ORDER BY a.data_registro DESC
                LIMIT 100
            """)
            todos = cursor.fetchall()
        finally:
            _return_conn(conn)

        if todos:
            # Criar DataFrame
            df = pd.DataFrame(todos, columns=[
                'ID', 'Usuário', 'Data', 'Horas', 'Status', 'Data Registro', 'Nome'
            ])

            df['Status'] = df['Status'].map({
                'pendente': '⏳ Pendente',
                'aprovado': '✅ Aprovado',
                'rejeitado': '❌ Rejeitado'
            })

            df['Data'] = pd.to_datetime(df['Data']).dt.strftime('%d/%m/%Y')
            df['Data Registro'] = pd.to_datetime(
                df['Data Registro']).dt.strftime('%d/%m/%Y %H:%M')
            df['Nome'] = df.apply(lambda row: row['Nome']
                                  or row['Usuário'], axis=1)

            # Exibir apenas colunas relevantes
            st.dataframe(
                df[['Nome', 'Data', 'Horas', 'Status', 'Data Registro']],
                width="stretch",
                hide_index=True
            )

            # Exportar
            csv = df.to_csv(index=False).encode('utf-8-sig')
            safe_download_button(
                label="📥 Exportar CSV",
                data=csv,
                file_name=f"atestados_{agora_br().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📁 Nenhum atestado registrado")


def todos_registros_interface(calculo_horas_system):
    """Interface para visualizar todos os registros"""
    st.markdown("""
    <div class="feature-card">
        <h3>👥 Todos os Registros de Ponto</h3>
        <p>Visualize e analise os registros de ponto de todos os funcionários</p>
    </div>
    """, unsafe_allow_html=True)

    # Filtros
    st.markdown("### 🔍 Filtros")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Buscar lista de usuários
        usuarios_list = None
        
        if REFACTORING_ENABLED:
            try:
                query_usuarios = "SELECT DISTINCT usuario, nome_completo FROM usuarios WHERE tipo = 'funcionario' ORDER BY nome_completo"
                usuarios_list = execute_query(query_usuarios)
            except Exception as e:
                log_error("Erro ao buscar lista de usuários para filtro", e, {"tipo": "funcionario"})
                usuarios_list = []
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT usuario, nome_completo FROM usuarios WHERE tipo = 'funcionario' ORDER BY nome_completo")
                usuarios_list = cursor.fetchall()
            finally:
                _return_conn(conn)

        usuario_options = ["Todos"] + \
            [f"{u[1] or u[0]} ({u[0]})" for u in usuarios_list]
        usuario_filter = st.selectbox("👤 Funcionário:", usuario_options)

    with col2:
        # Período padrão: últimos 30 dias
        data_inicio = st.date_input(
            "📅 Data Início:",
            value=hoje_br() - timedelta(days=30)
        )

    with col3:
        data_fim = st.date_input(
            "📅 Data Fim:",
            value=hoje_br()
        )

    with col4:
        tipo_registro = st.selectbox(
            "🕐 Tipo:",
            ["Todos", "Início", "Fim", "Intervalo"]
        )

    # Buscar registros
    registros = None
    
    if REFACTORING_ENABLED:
        try:
            query = f"""
                SELECT r.id, r.usuario, r.data_hora, r.tipo, r.modalidade, 
                       r.projeto, r.atividade, r.localizacao, r.latitude, r.longitude,
                       u.nome_completo
                FROM registros_ponto r
                LEFT JOIN usuarios u ON r.usuario = u.usuario
                WHERE DATE(r.data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            """
            params = [data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")]

            # Aplicar filtro de usuário
            if usuario_filter != "Todos":
                usuario_login = usuario_filter.split("(")[1].rstrip(")")
                query += f" AND r.usuario = {SQL_PLACEHOLDER}"
                params.append(usuario_login)

            # Aplicar filtro de tipo
            if tipo_registro != "Todos":
                query += f" AND r.tipo = {SQL_PLACEHOLDER}"
                params.append(tipo_registro)

            query += " ORDER BY r.data_hora DESC LIMIT 500"

            registros = execute_query(query, tuple(params))
        except Exception as e:
            log_error("Erro ao buscar registros de ponto", e, {"filtros": "data_range"})
            registros = []
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()

            query = f"""
                SELECT r.id, r.usuario, r.data_hora, r.tipo, r.modalidade, 
                       r.projeto, r.atividade, r.localizacao, r.latitude, r.longitude,
                       u.nome_completo
                FROM registros_ponto r
                LEFT JOIN usuarios u ON r.usuario = u.usuario
                WHERE DATE(r.data_hora) BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            """
            params = [data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")]

            # Aplicar filtro de usuário
            if usuario_filter != "Todos":
                usuario_login = usuario_filter.split("(")[1].rstrip(")")
                query += f" AND r.usuario = {SQL_PLACEHOLDER}"
                params.append(usuario_login)

            # Aplicar filtro de tipo
            if tipo_registro != "Todos":
                query += f" AND r.tipo = {SQL_PLACEHOLDER}"
                params.append(tipo_registro)

            query += " ORDER BY r.data_hora DESC LIMIT 500"

            cursor.execute(query, params)
            registros = cursor.fetchall()
        finally:
            _return_conn(conn)

    # Estatísticas gerais
    st.markdown("### 📊 Estatísticas do Período")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total de Registros", len(registros))

    with col2:
        usuarios_unicos = len(set(r[1] for r in registros))
        st.metric("Funcionários", usuarios_unicos)

    with col3:
        registros_inicio = sum(1 for r in registros if r[3] == "Início")
        st.metric("Registros de Início", registros_inicio)

    with col4:
        registros_fim = sum(1 for r in registros if r[3] == "Fim")
        st.metric("Registros de Fim", registros_fim)

    with col5:
        # Calcular média de registros por dia
        dias = (data_fim - data_inicio).days + 1
        media_dia = len(registros) / dias if dias > 0 else 0
        st.metric("Média/Dia", f"{media_dia:.1f}")

    st.markdown("---")

    # Botão de exportação
    if registros:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(
                f"### 📋 Listagem de Registros ({len(registros)} encontrados)")
        with col2:
            # 🔧 CORREÇÃO: Preparar dados para exportação COM horas trabalhadas e previstas
            # Primeiro, organizar registros por usuário e data para calcular horas
            from jornada_semanal_system import obter_jornada_usuario
            
            registros_para_export = {}
            for registro in registros:
                reg_id, usuario, data_hora_str, tipo, modalidade, projeto, atividade, localizacao, lat, lng, nome_completo = registro
                data_hora = safe_datetime_parse(data_hora_str)
                data_str = data_hora.strftime("%Y-%m-%d")
                
                chave = f"{usuario}_{data_str}"
                if chave not in registros_para_export:
                    registros_para_export[chave] = {
                        'usuario': usuario,
                        'nome_completo': nome_completo or usuario,
                        'data': data_hora.date(),
                        'registros': [],
                        'inicio': None,
                        'fim': None
                    }
                
                registros_para_export[chave]['registros'].append({
                    'tipo': tipo,
                    'data_hora': data_hora
                })
                
                if tipo == "Início" and not registros_para_export[chave]['inicio']:
                    registros_para_export[chave]['inicio'] = data_hora
                elif tipo == "Fim":
                    registros_para_export[chave]['fim'] = data_hora
            
            # Calcular horas trabalhadas e previstas
            export_data = []
            for chave, dados in registros_para_export.items():
                usuario = dados['usuario']
                nome_completo = dados['nome_completo']
                data = dados['data']
                inicio = dados['inicio']
                fim = dados['fim']
                
                # Calcular horas trabalhadas
                horas_trabalhadas_min = 0
                if inicio and fim:
                    delta = fim - inicio
                    horas_trabalhadas_min = delta.total_seconds() / 60
                
                # Calcular horas previstas baseado na jornada do usuário
                horas_previstas_min = 0
                try:
                    jornada = obter_jornada_usuario(usuario)
                    # Mapear dia da semana para chave da jornada
                    dias_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
                    dia_semana = dias_map.get(data.weekday(), 'seg')
                    
                    config_dia = jornada.get(dia_semana, {})
                    if config_dia.get('trabalha', False):
                        inicio_jornada = config_dia.get('inicio', '08:00')
                        fim_jornada = config_dia.get('fim', '17:00')
                        intervalo = config_dia.get('intervalo', 60)
                        
                        # Calcular duração da jornada
                        h_inicio, m_inicio = map(int, inicio_jornada.split(':'))
                        h_fim, m_fim = map(int, fim_jornada.split(':'))
                        
                        duracao_jornada_min = (h_fim * 60 + m_fim) - (h_inicio * 60 + m_inicio) - intervalo
                        horas_previstas_min = duracao_jornada_min
                except Exception as e:
                    logger.warning(f"Erro ao calcular jornada para {usuario}: {e}")
                    horas_previstas_min = 480  # 8 horas padrão
                
                # Formatar para exibição
                horas_trabalhadas_str = f"{int(horas_trabalhadas_min // 60)}h {int(horas_trabalhadas_min % 60)}min"
                horas_previstas_str = f"{int(horas_previstas_min // 60)}h {int(horas_previstas_min % 60)}min"
                
                # Calcular saldo (horas extras ou horas devidas)
                saldo_min = horas_trabalhadas_min - horas_previstas_min
                if saldo_min >= 0:
                    saldo_str = f"+{int(saldo_min // 60)}h {int(saldo_min % 60)}min"
                else:
                    saldo_min_abs = abs(saldo_min)
                    saldo_str = f"-{int(saldo_min_abs // 60)}h {int(saldo_min_abs % 60)}min"
                
                export_data.append({
                    'Usuário': usuario,
                    'Nome Completo': nome_completo,
                    'Data': data.strftime('%d/%m/%Y'),
                    'Entrada': inicio.strftime('%H:%M') if inicio else '-',
                    'Saída': fim.strftime('%H:%M') if fim else '-',
                    'Horas Trabalhadas': horas_trabalhadas_str if inicio and fim else '-',
                    'Horas Previstas': horas_previstas_str,
                    'Saldo': saldo_str if inicio and fim else '-',
                    'Qtd Registros': len(dados['registros'])
                })
            
            df_export = pd.DataFrame(export_data)
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            safe_download_button(
                label="📥 Exportar CSV",
                data=csv,
                file_name=f"registros_ponto_{data_inicio}_{data_fim}.csv",
                mime="text/csv",
                width="stretch"
            )
        with col3:
            # Exportar Excel
            buffer = BytesIO()
            df_export.to_excel(buffer, index=False, engine='openpyxl')
            buffer.seek(0)
            safe_download_button(
                label="📥 Exportar Excel",
                data=buffer,
                file_name=f"registros_ponto_{data_inicio}_{data_fim}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )

    # Agrupar por funcionário e data
    if registros:
        # Organizar registros por usuário e data
        registros_agrupados = {}
        for registro in registros:
            reg_id, usuario, data_hora_str, tipo, modalidade, projeto, atividade, localizacao, lat, lng, nome_completo = registro
            data_hora = safe_datetime_parse(data_hora_str)
            data_str = data_hora.strftime("%Y-%m-%d")

            chave = f"{usuario}_{data_str}"
            if chave not in registros_agrupados:
                registros_agrupados[chave] = {
                    'usuario': usuario,
                    'nome_completo': nome_completo or usuario,
                    'data': data_hora.date(),
                    'registros': []
                }

            registros_agrupados[chave]['registros'].append({
                'id': reg_id,
                'data_hora': data_hora,
                'tipo': tipo,
                'modalidade': modalidade,
                'projeto': projeto,
                'atividade': atividade,
                'localizacao': localizacao,
                'latitude': lat,
                'longitude': lng
            })

        # Exibir registros agrupados
        for chave, dados in sorted(registros_agrupados.items(), key=lambda x: (x[1]['data'], x[1]['usuario']), reverse=True):
            usuario = dados['usuario']
            nome_completo = dados['nome_completo']
            data = dados['data']
            regs = sorted(dados['registros'], key=lambda x: x['data_hora'])

            # Calcular horas trabalhadas do dia
            horas_trabalhadas = "N/A"
            inicio = None
            fim = None

            for r in regs:
                if r['tipo'] == "Início" and not inicio:
                    inicio = r['data_hora']
                elif r['tipo'] == "Fim":
                    fim = r['data_hora']

            if inicio and fim:
                delta = fim - inicio
                horas = delta.total_seconds() / 3600
                horas_trabalhadas = f"{int(horas)}h {int((horas % 1) * 60)}min"

            # Exibir card do dia
            with st.expander(f"📅 {data.strftime('%d/%m/%Y')} - 👤 {nome_completo} - ⏱️ {horas_trabalhadas} - {len(regs)} registro(s)"):
                # Informações do usuário
                st.markdown(f"**Funcionário:** {nome_completo} ({usuario})")
                st.markdown(f"**Data:** {data.strftime('%d/%m/%Y (%A)')}")

                if inicio and fim:
                    st.markdown(
                        f"**Jornada:** {inicio.strftime('%H:%M')} às {fim.strftime('%H:%M')} - **Total:** {horas_trabalhadas}")

                st.markdown("---")

                # Tabela de registros do dia
                for i, reg in enumerate(regs, 1):
                    col1, col2, col3 = st.columns([1, 2, 2])

                    with col1:
                        # Ícone baseado no tipo
                        icon = "🟢" if reg['tipo'] == "Início" else "🔴" if reg['tipo'] == "Fim" else "⏸️"
                        st.markdown(f"**{icon} {reg['tipo']}**")
                        st.caption(reg['data_hora'].strftime('%H:%M:%S'))

                    with col2:
                        st.markdown(
                            f"**Modalidade:** {reg['modalidade'] or 'N/A'}")
                        st.markdown(f"**Projeto:** {reg['projeto'] or 'N/A'}")
                        if reg['atividade']:
                            st.caption(f"Atividade: {reg['atividade']}")

                    with col3:
                        localizacao_legivel = formatar_localizacao_legivel(
                            reg['localizacao'], reg['latitude'], reg['longitude']
                        )
                        st.markdown(f"📍 **{localizacao_legivel}**")

                        lat_mapa = reg['latitude']
                        lng_mapa = reg['longitude']
                        if (lat_mapa is None or lng_mapa is None) and reg['localizacao']:
                            try:
                                import re
                                match = re.search(r'(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)', str(reg['localizacao']))
                                if match:
                                    lat_mapa = float(match.group(1))
                                    lng_mapa = float(match.group(2))
                            except Exception as e:
                                logger.debug("Falha ao extrair coordenadas para mapa: %s", e)

                        if lat_mapa is not None and lng_mapa is not None:
                            maps_url = f"https://www.google.com/maps?q={lat_mapa},{lng_mapa}"
                            st.markdown(f"[🗺️ Ver no Mapa]({maps_url})")

                    if i < len(regs):
                        st.markdown("---")

                # Análise de discrepâncias
                if inicio and fim:
                    # Buscar jornada prevista do usuário
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()
                        cursor.execute(
                            f"SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}",
                            (usuario,)
                        )
                        jornada = cursor.fetchone()
                    finally:
                        _return_conn(conn)

                    if jornada and jornada[0] and jornada[1]:
                        jornada_inicio_str = jornada[0]
                        jornada_fim_str = jornada[1]

                        # Converter para string se for time object
                        if isinstance(jornada_inicio_str, time):
                            jornada_inicio_str = jornada_inicio_str.strftime('%H:%M')
                        if isinstance(jornada_fim_str, time):
                            jornada_fim_str = jornada_fim_str.strftime('%H:%M')

                        # Calcular horas previstas
                        h_inicio, m_inicio = map(
                            int, jornada_inicio_str.split(':'))
                        h_fim, m_fim = map(int, jornada_fim_str.split(':'))

                        inicio_previsto = inicio.replace(
                            hour=h_inicio, minute=m_inicio, second=0)
                        fim_previsto = fim.replace(
                            hour=h_fim, minute=m_fim, second=0)

                        horas_previstas = (
                            fim_previsto - inicio_previsto).total_seconds() / 3600
                        horas_reais = (fim - inicio).total_seconds() / 3600
                        diferenca = horas_reais - horas_previstas

                        st.markdown("### 📊 Análise da Jornada")
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Horas Previstas",
                                      f"{horas_previstas:.2f}h")
                        with col2:
                            st.metric("Horas Trabalhadas",
                                      f"{horas_reais:.2f}h")
                        with col3:
                            delta_color = "normal" if abs(
                                diferenca) < 0.5 else "inverse"
                            st.metric(
                                "Diferença",
                                f"{diferenca:+.2f}h",
                                delta_color=delta_color
                            )

                        # Alertas
                        if diferenca > 1:
                            st.success(
                                f"✅ Horas extras potenciais: {diferenca:.2f}h")
                        elif diferenca < -1:
                            st.warning(
                                f"⚠️ Jornada incompleta: {abs(diferenca):.2f}h a menos")
    else:
        st.info("📁 Nenhum registro encontrado com os filtros aplicados")

    # Análise por funcionário (resumo)
    if registros and usuario_filter == "Todos":
        st.markdown("---")
        st.markdown("### 📈 Resumo por Funcionário")

        # Agrupar por usuário
        usuarios_stats = {}
        for registro in registros:
            usuario = registro[1]
            nome = registro[10] or usuario

            if usuario not in usuarios_stats:
                usuarios_stats[usuario] = {
                    'nome': nome,
                    'total_registros': 0,
                    'registros_inicio': 0,
                    'registros_fim': 0
                }

            usuarios_stats[usuario]['total_registros'] += 1
            if registro[3] == "Início":
                usuarios_stats[usuario]['registros_inicio'] += 1
            elif registro[3] == "Fim":
                usuarios_stats[usuario]['registros_fim'] += 1

        # Criar DataFrame
        df_stats = pd.DataFrame([
            {
                'Funcionário': dados['nome'],
                'Total de Registros': dados['total_registros'],
                'Registros de Início': dados['registros_inicio'],
                'Registros de Fim': dados['registros_fim'],
                'Pares Completos': min(dados['registros_inicio'], dados['registros_fim'])
            }
            for usuario, dados in sorted(usuarios_stats.items(), key=lambda x: x[1]['nome'])
        ])

        st.dataframe(df_stats, width="stretch", hide_index=True)


def gerenciar_arquivos_interface(upload_system):
    """Interface para gerenciar todos os arquivos"""
    st.markdown("""
    <div class="feature-card">
        <h3>📁 Gerenciamento de Arquivos</h3>
        <p>Visualize e gerencie todos os arquivos enviados pelos funcionários</p>
    </div>
    """, unsafe_allow_html=True)

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        categoria_filter = st.selectbox(
            "Categoria:",
            ["Todas", "Atestados Médicos", "Comprovantes de Ausência", "Documentos"]
        )

    with col2:
        usuario_filter = st.text_input("� Buscar por usuário:")

    with col3:
        data_filter = st.date_input("📅 Data específica:", value=None)

    # Buscar arquivos
    if REFACTORING_ENABLED:
        try:
            query = """
                SELECT u.id, u.usuario, u.nome_original, u.tipo_arquivo, 
                       u.data_upload, u.tamanho, u.tipo_arquivo as tipo_arquivo, 
                       us.nome_completo
                FROM uploads u
                LEFT JOIN usuarios us ON u.usuario = us.usuario
                WHERE u.status = 'ativo'
            """
            params = []

            # Aplicar filtros
            if categoria_filter != "Todas":
                categoria_map = {
                    "Atestados Médicos": "atestado",
                    "Comprovantes de Ausência": "ausencia",
                    "Documentos": "documento"
                }
                query += f" AND u.relacionado_a = {SQL_PLACEHOLDER}"
                params.append(categoria_map[categoria_filter])

            if usuario_filter:
                query += f" AND (u.usuario LIKE {SQL_PLACEHOLDER} OR us.nome_completo LIKE {SQL_PLACEHOLDER})"
                params.extend([f"%{usuario_filter}%", f"%{usuario_filter}%"])

            if data_filter:
                query += f" AND DATE(u.data_upload) = {SQL_PLACEHOLDER}"
                params.append(data_filter.strftime("%Y-%m-%d"))

            query += " ORDER BY u.data_upload DESC LIMIT 100"

            arquivos = execute_query(query, tuple(params))
            if not arquivos:
                arquivos = []
        except Exception as e:
            log_error("Erro ao buscar arquivos", e, {"usuario_filter": usuario_filter})
            st.error("❌ Erro ao buscar arquivos")
            return
    else:
        # Fallback original
        conn = get_connection()
        try:
            cursor = conn.cursor()

            query = """
                SELECT u.id, u.usuario, u.nome_original, u.tipo_arquivo, 
                       u.data_upload, u.tamanho, u.tipo_arquivo as tipo_arquivo, 
                       us.nome_completo
                FROM uploads u
                LEFT JOIN usuarios us ON u.usuario = us.usuario
                WHERE u.status = 'ativo'
            """
            params = []

            # Aplicar filtros
            if categoria_filter != "Todas":
                categoria_map = {
                    "Atestados Médicos": "atestado",
                    "Comprovantes de Ausência": "ausencia",
                    "Documentos": "documento"
                }
                query += f" AND u.relacionado_a = {SQL_PLACEHOLDER}"
                params.append(categoria_map[categoria_filter])

            if usuario_filter:
                query += f" AND (u.usuario LIKE {SQL_PLACEHOLDER} OR us.nome_completo LIKE {SQL_PLACEHOLDER})"
                params.extend([f"%{usuario_filter}%", f"%{usuario_filter}%"])

            if data_filter:
                query += f" AND DATE(u.data_upload) = {SQL_PLACEHOLDER}"
                params.append(data_filter.strftime("%Y-%m-%d"))

            query += " ORDER BY u.data_upload DESC LIMIT 100"

            cursor.execute(query, params)
            arquivos = cursor.fetchall()
        finally:
            _return_conn(conn)

    # Estatísticas
    st.markdown("### 📊 Estatísticas")
    col1, col2, col3, col4 = st.columns(4)

    if REFACTORING_ENABLED:
        try:
            with col1:
                result = execute_query("SELECT COUNT(*) FROM uploads", fetch_one=True)
                total = result[0] if result else 0
                st.metric("Total de Arquivos", total)

            with col2:
                result = execute_query("SELECT COUNT(DISTINCT usuario) FROM uploads", fetch_one=True)
                usuarios = result[0] if result else 0
                st.metric("Usuários com Uploads", usuarios)

            with col3:
                result = execute_query("SELECT SUM(tamanho) FROM uploads", fetch_one=True)
                tamanho_total = (result[0] if result and result[0] else 0)
                st.metric("Espaço Utilizado", format_file_size(tamanho_total))

            with col4:
                hoje_str = date.today().strftime("%Y-%m-%d")
                query_hoje = f"SELECT COUNT(*) FROM uploads WHERE DATE(data_upload) = {SQL_PLACEHOLDER}"
                result = execute_query(query_hoje, (hoje_str,), fetch_one=True)
                hoje = result[0] if result else 0
                st.metric("Uploads Hoje", hoje)
        except Exception as e:
            log_error("Erro ao buscar estatísticas", e, {})
    else:
        # Fallback original
        conn = get_connection()
        try:
            cursor = conn.cursor()

            with col1:
                cursor.execute("SELECT COUNT(*) FROM uploads")
                total = cursor.fetchone()[0]
                st.metric("Total de Arquivos", total)

            with col2:
                cursor.execute("SELECT COUNT(DISTINCT usuario) FROM uploads")
                usuarios = cursor.fetchone()[0]
                st.metric("Usuários com Uploads", usuarios)

            with col3:
                cursor.execute("SELECT SUM(tamanho) FROM uploads")
                tamanho_total = cursor.fetchone()[0] or 0
                st.metric("Espaço Utilizado", format_file_size(tamanho_total))

            with col4:
                # Evitar funções específicas de SQLite (DATE('now')) e usar parâmetro
                hoje_str = date.today().strftime("%Y-%m-%d")
                cursor.execute(
                    f"SELECT COUNT(*) FROM uploads WHERE DATE(data_upload) = {SQL_PLACEHOLDER}", (hoje_str,))
                hoje = cursor.fetchone()[0]
                st.metric("Uploads Hoje", hoje)

        finally:
            _return_conn(conn)

    # Listagem de arquivos
    st.markdown("### 📋 Arquivos")

    if arquivos:
        st.info(f"Exibindo {len(arquivos)} arquivo(s)")

        for arquivo in arquivos:
            arquivo_id, usuario, nome, tipo_arquivo, data, tamanho, tipo_arquivo, nome_completo = arquivo

            with st.expander(f"{get_file_icon(tipo_arquivo)} {nome} - {nome_completo or usuario}", expanded=False):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Usuário:** {nome_completo or usuario}")
                    st.write(f"**Tipo:** {tipo_arquivo or 'N/A'}")
                    st.write(
                        f"**Data:** {format_datetime_safe(data, '%d/%m/%Y às %H:%M')}")
                    st.write(f"**Tamanho:** {format_file_size(tamanho)}")
                    st.write(f"**Formato:** {tipo_arquivo}")

                with col2:
                    # Botão de download
                    content, _ = upload_system.get_file_content(
                        arquivo_id, usuario)
                    if content:
                        safe_download_button(
                            label="⬇️ Baixar",
                            data=content,
                            file_name=nome,
                            mime=tipo_arquivo,
                            width="stretch",
                            key=f"download_arq_{arquivo_id}"
                        )
                        
                        # Visualização de imagens inline
                        if is_image_file(tipo_arquivo):
                            st.image(content, caption=nome, width=300)
                    else:
                        st.warning("⚠️ Arquivo indisponível")
                        st.caption("O arquivo não está mais acessível no servidor. Solicite ao usuário que faça o re-upload.")

                    # Botão de exclusão (com confirmação)
                    if st.button(f"🗑️ Excluir", key=f"del_{arquivo_id}", width="stretch"):
                        st.session_state[f"confirm_delete_{arquivo_id}"] = True

                    if st.session_state.get(f"confirm_delete_{arquivo_id}"):
                        st.warning("Confirmar exclusão?")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Sim", key=f"yes_{arquivo_id}"):
                                if upload_system.delete_file(arquivo_id, usuario):
                                    log_security_event("FILE_DELETED", usuario=st.session_state.usuario, context={"file_id": arquivo_id})
                                    st.success("Arquivo excluído!")
                                    del st.session_state[f"confirm_delete_{arquivo_id}"]
                                    st.rerun()
                        with col_b:
                            if st.button("❌ Não", key=f"no_{arquivo_id}"):
                                del st.session_state[f"confirm_delete_{arquivo_id}"]
                                st.rerun()
    else:
        st.info("📁 Nenhum arquivo encontrado com os filtros aplicados")


def gerenciar_projetos_interface():
    """Interface para gerenciar projetos"""
    st.markdown("""
    <div class="feature-card">
        <h3>🏢 Gerenciamento de Projetos</h3>
        <p>Cadastre e gerencie os projetos da empresa</p>
    </div>
    """, unsafe_allow_html=True)

    # Abas
    tab1, tab2 = st.tabs(["📋 Lista de Projetos", "➕ Novo Projeto"])

    with tab1:
        st.markdown("### 📋 Projetos Cadastrados")

        # Filtro
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Status:", ["Todos", "Ativos", "Inativos"])
        with col2:
            busca = st.text_input("🔍 Buscar projeto:")

        # Buscar projetos
        if REFACTORING_ENABLED:
            try:
                query = "SELECT id, nome, descricao, ativo FROM projetos WHERE 1=1"
                params = []

                if status_filter == "Ativos":
                    query += " AND ativo = 1"
                elif status_filter == "Inativos":
                    query += " AND ativo = 0"

                if busca:
                    query += f" AND nome LIKE {SQL_PLACEHOLDER}"
                    params.append(f"%{busca}%")

                query += " ORDER BY nome"

                projetos = execute_query(query, tuple(params))
                if not projetos:
                    projetos = []
            except Exception as e:
                log_error("Erro ao buscar projetos", e, {"busca": busca})
                st.error("❌ Erro ao buscar projetos")
                return
        else:
            # Fallback original
            conn = get_connection()
            try:
                cursor = conn.cursor()

                query = "SELECT id, nome, descricao, ativo FROM projetos WHERE 1=1"
                params = []

                if status_filter == "Ativos":
                    query += " AND ativo = 1"
                elif status_filter == "Inativos":
                    query += " AND ativo = 0"

                if busca:
                    query += f" AND nome LIKE {SQL_PLACEHOLDER}"
                    params.append(f"%{busca}%")

                query += " ORDER BY nome"

                cursor.execute(query, params)
                projetos = cursor.fetchall()
            finally:
                _return_conn(conn)

        # Estatísticas
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Projetos", len(projetos))
        with col2:
            ativos = sum(1 for p in projetos if p[3] == 1)
            st.metric("Projetos Ativos", ativos)
        with col3:
            inativos = len(projetos) - ativos
            st.metric("Projetos Inativos", inativos)

        st.markdown("---")

        # Listagem
        if projetos:
            for projeto_id, nome, descricao, ativo in projetos:
                with st.expander(f"{'✅' if ativo else '❌'} {nome}"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        # Edição inline
                        novo_nome = st.text_input(
                            "Nome do Projeto:",
                            value=nome,
                            key=f"nome_{projeto_id}"
                        )
                        nova_descricao = st.text_area(
                            "Descrição:",
                            value=descricao or "",
                            key=f"desc_{projeto_id}"
                        )
                        novo_status = st.checkbox(
                            "Projeto Ativo",
                            value=bool(ativo),
                            key=f"status_{projeto_id}"
                        )

                    with col2:
                        st.write("")
                        st.write("")

                        # Botão de salvar
                        if st.button("💾 Salvar", key=f"save_{projeto_id}", width="stretch"):
                            if REFACTORING_ENABLED:
                                try:
                                    update_query = f"""
                                        UPDATE projetos 
                                        SET nome = {SQL_PLACEHOLDER}, descricao = {SQL_PLACEHOLDER}, ativo = {SQL_PLACEHOLDER}
                                        WHERE id = {SQL_PLACEHOLDER}
                                    """
                                    execute_update(update_query, (novo_nome, nova_descricao, int(novo_status), projeto_id))
                                    log_security_event("PROJECT_UPDATED", usuario=st.session_state.usuario, context={"project_id": projeto_id})
                                    st.success("✅ Projeto atualizado!")
                                    st.rerun()
                                except Exception as e:
                                    log_error("Erro ao atualizar projeto", e, {"projeto_id": projeto_id})
                                    st.error(f"❌ Erro ao atualizar projeto: {e}")
                            else:
                                # Fallback original
                                conn = get_connection()
                                try:
                                    cursor = conn.cursor()

                                    cursor.execute(f"""
                                        UPDATE projetos 
                                        SET nome = {SQL_PLACEHOLDER}, descricao = {SQL_PLACEHOLDER}, ativo = {SQL_PLACEHOLDER}
                                        WHERE id = {SQL_PLACEHOLDER}
                                    """, (novo_nome, nova_descricao, int(novo_status), projeto_id))

                                    conn.commit()
                                finally:
                                    _return_conn(conn)

                                st.success("✅ Projeto atualizado!")
                                st.rerun()

                        # Botão de excluir
                        if st.button("🗑️ Excluir", key=f"del_{projeto_id}", width="stretch"):
                            st.session_state[f"confirm_del_proj_{projeto_id}"] = True

                        if st.session_state.get(f"confirm_del_proj_{projeto_id}"):
                            st.warning("⚠️ Confirmar?")
                            if st.button("Sim", key=f"yes_{projeto_id}"):
                                if REFACTORING_ENABLED:
                                    try:
                                        delete_query = f"DELETE FROM projetos WHERE id = {SQL_PLACEHOLDER}"
                                        execute_update(delete_query, (projeto_id,))
                                        log_security_event("PROJECT_DELETED", usuario=st.session_state.usuario, context={"project_id": projeto_id})
                                        del st.session_state[f"confirm_del_proj_{projeto_id}"]
                                        st.success("✅ Projeto excluído!")
                                        st.rerun()
                                    except Exception as e:
                                        log_error("Erro ao deletar projeto", e, {"projeto_id": projeto_id})
                                        st.error(f"❌ Erro ao deletar: {e}")
                                else:
                                    # Fallback original
                                    conn = get_connection()
                                    try:
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            f"DELETE FROM projetos WHERE id = {SQL_PLACEHOLDER}", (projeto_id,))
                                        conn.commit()
                                    finally:
                                        _return_conn(conn)

                                    del st.session_state[f"confirm_del_proj_{projeto_id}"]
                                    st.success("✅ Projeto excluído!")
                                    st.rerun()
        else:
            st.info("📁 Nenhum projeto encontrado")

    with tab2:
        st.markdown("### ➕ Cadastrar Novo Projeto")

        with st.form("novo_projeto"):
            nome_novo = st.text_input(
                "Nome do Projeto:", placeholder="Ex: Sistema de Controle de Ponto")
            descricao_nova = st.text_area(
                "Descrição (opcional):", placeholder="Descreva o projeto...")
            ativo_novo = st.checkbox("Projeto Ativo", value=True)

            submitted = st.form_submit_button(
                "➕ Cadastrar Projeto", width="stretch")

            if submitted:
                if not nome_novo:
                    st.error("❌ O nome do projeto é obrigatório!")
                else:
                    if REFACTORING_ENABLED:
                        try:
                            insert_query = f"""
                                INSERT INTO projetos (nome, descricao, ativo)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            """
                            execute_update(insert_query, (nome_novo, descricao_nova, int(ativo_novo)))
                            log_security_event("PROJECT_CREATED", usuario=st.session_state.usuario, context={"project_name": nome_novo})
                            st.success(
                                f"✅ Projeto '{nome_novo}' cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            log_error("Erro ao cadastrar projeto", e, {"project_name": nome_novo})
                            st.error(f"❌ Erro ao cadastrar projeto: {e}")
                    else:
                        # Fallback original
                        try:
                            conn = get_connection()
                            try:
                                cursor = conn.cursor()

                                cursor.execute(f"""
                                    INSERT INTO projetos (nome, descricao, ativo)
                                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                """, (nome_novo, descricao_nova, int(ativo_novo)))

                                conn.commit()
                            finally:
                                _return_conn(conn)

                            st.success(
                                f"✅ Projeto '{nome_novo}' cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar projeto: {e}")


def gerenciar_usuarios_interface():
    """Interface para gerenciar usuários"""
    st.markdown("""
    <div class="feature-card">
        <h3>👤 Gerenciamento de Usuários</h3>
        <p>Cadastre e gerencie funcionários e gestores do sistema</p>
    </div>
    """, unsafe_allow_html=True)

    # Abas
    tab1, tab2 = st.tabs(["👥 Lista de Usuários", "➕ Novo Usuário"])

    with tab1:
        st.markdown("### � Usuários Cadastrados")

        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            tipo_filter = st.selectbox(
                "Tipo:", ["Todos", "Funcionários", "Gestores"])
        with col2:
            status_filter = st.selectbox(
                "Status:", ["Todos", "Ativos", "Inativos"])
        with col3:
            busca = st.text_input("🔍 Buscar:")

        # Buscar usuários
        if REFACTORING_ENABLED:
            try:
                query = """
                    SELECT id, usuario, nome_completo, tipo, ativo, 
                           jornada_inicio_previsto, jornada_fim_previsto
                    FROM usuarios WHERE 1=1
                """
                params = []

                if tipo_filter == "Funcionários":
                    query += " AND tipo = 'funcionario'"
                elif tipo_filter == "Gestores":
                    query += " AND tipo = 'gestor'"

                if status_filter == "Ativos":
                    query += " AND ativo = 1"
                elif status_filter == "Inativos":
                    query += " AND ativo = 0"

                if busca:
                    query += f" AND (usuario LIKE {SQL_PLACEHOLDER} OR nome_completo LIKE {SQL_PLACEHOLDER})"
                    params.extend([f"%{busca}%", f"%{busca}%"])

                query += " ORDER BY nome_completo"

                usuarios = execute_query(query, tuple(params))
                if not usuarios:
                    usuarios = []
            except Exception as e:
                log_error("Erro ao buscar usuários", e, {"busca": busca})
                st.error("❌ Erro ao buscar usuários")
                return
        else:
            # Fallback original
            conn = get_connection()
            try:
                cursor = conn.cursor()

                query = """
                    SELECT id, usuario, nome_completo, tipo, ativo, 
                           jornada_inicio_previsto, jornada_fim_previsto
                    FROM usuarios WHERE 1=1
                """
                params = []

                if tipo_filter == "Funcionários":
                    query += " AND tipo = 'funcionario'"
                elif tipo_filter == "Gestores":
                    query += " AND tipo = 'gestor'"

                if status_filter == "Ativos":
                    query += " AND ativo = 1"
                elif status_filter == "Inativos":
                    query += " AND ativo = 0"

                if busca:
                    query += f" AND (usuario LIKE {SQL_PLACEHOLDER} OR nome_completo LIKE {SQL_PLACEHOLDER})"
                    params.extend([f"%{busca}%", f"%{busca}%"])

                query += " ORDER BY nome_completo"

                cursor.execute(query, params)
                usuarios = cursor.fetchall()
            finally:
                _return_conn(conn)

        # Estatísticas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(usuarios))
        with col2:
            funcionarios = sum(1 for u in usuarios if u[3] == 'funcionario')
            st.metric("Funcionários", funcionarios)
        with col3:
            gestores = sum(1 for u in usuarios if u[3] == 'gestor')
            st.metric("Gestores", gestores)
        with col4:
            ativos = sum(1 for u in usuarios if u[4] == 1)
            st.metric("Ativos", ativos)

        st.markdown("---")

        # Listagem
        if usuarios:
            for usuario_id, usuario, nome_completo, tipo, ativo, jornada_inicio, jornada_fim in usuarios:
                status_emoji = "✅" if ativo else "❌"
                tipo_emoji = "👤" if tipo == 'funcionario' else "👑"

                with st.expander(f"{status_emoji} {tipo_emoji} {nome_completo or usuario}"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        # Edição
                        novo_usuario = st.text_input(
                            "Login:",
                            value=usuario,
                            key=f"user_{usuario_id}",
                            disabled=True  # Login não pode ser alterado
                        )
                        novo_nome = st.text_input(
                            "Nome Completo:",
                            value=nome_completo or "",
                            key=f"nome_{usuario_id}"
                        )

                        col_a, col_b = st.columns(2)
                        with col_a:
                            novo_tipo = st.selectbox(
                                "Tipo:",
                                ["funcionario", "gestor"],
                                index=0 if tipo == 'funcionario' else 1,
                                key=f"tipo_{usuario_id}"
                            )
                        with col_b:
                            novo_ativo = st.checkbox(
                                "Usuário Ativo",
                                value=bool(ativo),
                                key=f"ativo_{usuario_id}"
                            )

                        # Jornada de trabalho
                        st.markdown("**Jornada de Trabalho Padrão:**")
                        col_c, col_d = st.columns(2)
                        with col_c:
                            nova_jornada_inicio = st.time_input(
                                "Início:",
                                value=ensure_time(jornada_inicio, default=time(8, 0)),
                                key=f"inicio_{usuario_id}"
                            )
                        with col_d:
                            nova_jornada_fim = st.time_input(
                                "Fim:",
                                value=ensure_time(jornada_fim, default=time(17, 0)),
                                key=f"fim_{usuario_id}"
                            )

                        # Jornada Semanal Variável
                        st.markdown("---")
                        st.markdown("**📅 Jornada Semanal Detalhada:**")
                        st.info("💡 Configure horários diferentes para cada dia da semana")
                        
                        from jornada_semanal_system import obter_jornada_usuario, salvar_jornada_semanal
                        
                        jornada_atual = obter_jornada_usuario(usuario) or {}
                        
                        dias = {
                            'seg': '🔵 Segunda', 'ter': '🔵 Terça', 'qua': '🔵 Quarta',
                            'qui': '🔵 Quinta', 'sex': '🔵 Sexta', 'sab': '🟡 Sábado', 'dom': '🔴 Domingo'
                        }
                        
                        jornada_config = {}
                        
                        for dia_key, dia_nome in dias.items():
                            config_dia = jornada_atual.get(dia_key, {
                                'trabalha': dia_key in ['seg', 'ter', 'qua', 'qui', 'sex'], 
                                'inicio': '08:00', 
                                'fim': '17:00'
                            })
                            
                            col_check, col_inicio, col_fim = st.columns([2, 2, 2])
                            
                            with col_check:
                                trabalha = st.checkbox(
                                    dia_nome,
                                    value=config_dia.get('trabalha', True),
                                    key=f"trabalha_{dia_key}_{usuario_id}"
                                )
                            
                            with col_inicio:
                                if trabalha:
                                    try:
                                        hora_inicio_str = config_dia.get('inicio', '08:00')
                                        if isinstance(hora_inicio_str, str):
                                            hora_parts = hora_inicio_str.split(':')
                                            hora_inicio_val = time(int(hora_parts[0]), int(hora_parts[1]))
                                        else:
                                            hora_inicio_val = time(8, 0)
                                    except Exception as e:
                                        logger.debug(f"Erro ao parsear hora início da jornada, usando 08:00: {e}")
                                        hora_inicio_val = time(8, 0)
                                    
                                    hora_inicio = st.time_input(
                                        "Entrada",
                                        value=hora_inicio_val,
                                        key=f"inicio_{dia_key}_{usuario_id}",
                                        label_visibility="collapsed"
                                    )
                                else:
                                    hora_inicio = None
                                    st.markdown("<small style='color: gray;'>Não trabalha</small>", unsafe_allow_html=True)
                            
                            with col_fim:
                                if trabalha:
                                    try:
                                        hora_fim_str = config_dia.get('fim', '17:00')
                                        if isinstance(hora_fim_str, str):
                                            hora_parts = hora_fim_str.split(':')
                                            hora_fim_val = time(int(hora_parts[0]), int(hora_parts[1]))
                                        else:
                                            hora_fim_val = time(17, 0)
                                    except Exception as e:
                                        logger.debug(f"Erro ao parsear hora fim da jornada, usando 17:00: {e}")
                                        hora_fim_val = time(17, 0)
                                    
                                    hora_fim = st.time_input(
                                        "Saída",
                                        value=hora_fim_val,
                                        key=f"fim_{dia_key}_{usuario_id}",
                                        label_visibility="collapsed"
                                    )
                                else:
                                    hora_fim = None
                                    st.markdown("<small style='color: gray;'>-</small>", unsafe_allow_html=True)
                            
                            jornada_config[dia_key] = {
                                'trabalha': trabalha,
                                'inicio': hora_inicio.strftime('%H:%M') if hora_inicio else None,
                                'fim': hora_fim.strftime('%H:%M') if hora_fim else None
                            }

                        # Alteração de senha - Corrigido: removido expander aninhado
                        st.markdown("**🔑 Alterar Senha:**")
                        nova_senha = st.text_input(
                            "Nova Senha:",
                            type="password",
                            key=f"senha_{usuario_id}"
                        )
                        confirmar_senha = st.text_input(
                            "Confirmar Senha:",
                            type="password",
                            key=f"conf_senha_{usuario_id}"
                        )

                        if st.button("🔑 Alterar Senha", key=f"btn_senha_{usuario_id}"):
                            if not nova_senha:
                                st.error("❌ Digite uma senha!")
                            elif nova_senha != confirmar_senha:
                                st.error("❌ As senhas não conferem!")
                            else:
                                if REFACTORING_ENABLED:
                                    try:
                                        from password_utils import hash_password
                                        senha_hash = hash_password(nova_senha)
                                        update_query = f"UPDATE usuarios SET senha = {SQL_PLACEHOLDER} WHERE id = {SQL_PLACEHOLDER}"
                                        execute_update(update_query, (senha_hash, usuario_id))
                                        log_security_event("PASSWORD_CHANGED", usuario=st.session_state.usuario, context={"target_user_id": usuario_id})
                                        st.success("✅ Senha alterada com sucesso!")
                                    except Exception as e:
                                        log_error("Erro ao alterar senha", e, {"usuario_id": usuario_id})
                                        st.error(f"❌ Erro: {e}")
                                else:
                                    # Fallback original
                                    conn = get_connection()
                                    try:
                                        cursor = conn.cursor()

                                        from password_utils import hash_password
                                        senha_hash = hash_password(nova_senha)
                                        cursor.execute(
                                            f"UPDATE usuarios SET senha = {SQL_PLACEHOLDER} WHERE id = {SQL_PLACEHOLDER}",
                                            (senha_hash, usuario_id)
                                        )

                                        conn.commit()
                                    finally:
                                        _return_conn(conn)

                                    st.success("✅ Senha alterada com sucesso!")

                    with col2:
                        st.write("")
                        st.write("")

                        # Botão de salvar
                        if st.button("💾 Salvar", key=f"save_{usuario_id}", width="stretch"):
                            if REFACTORING_ENABLED:
                                try:
                                    update_query = f"""
                                        UPDATE usuarios 
                                        SET nome_completo = {SQL_PLACEHOLDER}, tipo = {SQL_PLACEHOLDER}, ativo = {SQL_PLACEHOLDER},
                                            jornada_inicio_previsto = {SQL_PLACEHOLDER}, jornada_fim_previsto = {SQL_PLACEHOLDER}
                                        WHERE id = {SQL_PLACEHOLDER}
                                    """
                                    execute_update(update_query, (
                                        novo_nome,
                                        novo_tipo,
                                        int(novo_ativo),
                                        nova_jornada_inicio.strftime("%H:%M"),
                                        nova_jornada_fim.strftime("%H:%M"),
                                        usuario_id
                                    ))
                                    
                                    # Salvar jornada semanal
                                    from jornada_semanal_system import salvar_jornada_semanal
                                    salvar_jornada_semanal(usuario_id, jornada_config)
                                    
                                    log_security_event("USER_UPDATED", usuario=st.session_state.usuario, context={"target_user_id": usuario_id, "target_type": novo_tipo})
                                    st.success("✅ Usuário atualizado!")
                                    st.rerun()
                                except Exception as e:
                                    log_error("Erro ao atualizar usuário", e, {"usuario_id": usuario_id})
                                    st.error(f"❌ Erro ao atualizar: {e}")
                            else:
                                # Fallback original — transação atômica: update usuario + jornada
                                conn = get_connection()
                                try:
                                    cursor = conn.cursor()

                                    cursor.execute(f"""
                                        UPDATE usuarios 
                                        SET nome_completo = {SQL_PLACEHOLDER}, tipo = {SQL_PLACEHOLDER}, ativo = {SQL_PLACEHOLDER},
                                            jornada_inicio_previsto = {SQL_PLACEHOLDER}, jornada_fim_previsto = {SQL_PLACEHOLDER}
                                        WHERE id = {SQL_PLACEHOLDER}
                                    """, (
                                        novo_nome,
                                        novo_tipo,
                                        int(novo_ativo),
                                        nova_jornada_inicio.strftime("%H:%M"),
                                        nova_jornada_fim.strftime("%H:%M"),
                                        usuario_id
                                    ))

                                    # Salvar jornada semanal NA MESMA transação
                                    from jornada_semanal_system import salvar_jornada_semanal
                                    salvar_jornada_semanal(usuario_id, jornada_config, conn_external=conn)

                                    conn.commit()
                                except Exception as e:
                                    conn.rollback()
                                    st.error(f"❌ Erro ao atualizar: {e}")
                                    raise
                                finally:
                                    _return_conn(conn)

                                st.success("✅ Usuário atualizado!")
                                st.rerun()

                        # Botão de excluir
                        if st.button("🗑️ Excluir", key=f"del_{usuario_id}", width="stretch"):
                            st.session_state[f"confirm_del_user_{usuario_id}"] = True

                        if st.session_state.get(f"confirm_del_user_{usuario_id}"):
                            st.warning("⚠️ Confirmar?")
                            if st.button("Sim", key=f"yes_{usuario_id}"):
                                if REFACTORING_ENABLED:
                                    try:
                                        delete_query = f"DELETE FROM usuarios WHERE id = {SQL_PLACEHOLDER}"
                                        execute_update(delete_query, (usuario_id,))
                                        log_security_event("USER_DELETED", usuario=st.session_state.usuario, context={"deleted_user_id": usuario_id})
                                        del st.session_state[f"confirm_del_user_{usuario_id}"]
                                        st.success("✅ Usuário excluído!")
                                        st.rerun()
                                    except Exception as e:
                                        log_error("Erro ao deletar usuário", e, {"usuario_id": usuario_id})
                                        st.error(f"❌ Erro ao deletar: {e}")
                                else:
                                    # Fallback original
                                    conn = get_connection()
                                    try:
                                        cursor = conn.cursor()
                                        cursor.execute(
                                            f"DELETE FROM usuarios WHERE id = {SQL_PLACEHOLDER}", (usuario_id,))
                                        conn.commit()
                                    finally:
                                        _return_conn(conn)

                                    del st.session_state[f"confirm_del_user_{usuario_id}"]
                                    st.success("✅ Usuário excluído!")
                                    st.rerun()
        else:
            st.info("👤 Nenhum usuário encontrado")

    with tab2:
        st.markdown("### ➕ Cadastrar Novo Usuário")

        with st.form("novo_usuario"):
            col1, col2 = st.columns(2)

            with col1:
                novo_login = st.text_input(
                    "Login:*", placeholder="Ex: joao.silva")
                novo_nome = st.text_input(
                    "Nome Completo:*", placeholder="Ex: João Silva")
                novo_cpf = st.text_input(
                    "CPF:*", placeholder="Ex: 123.456.789-00",
                    help="Digite o CPF com ou sem pontuação")
                novo_email = st.text_input(
                    "E-mail:*", placeholder="Ex: joao.silva@empresa.com",
                    help="E-mail obrigatório para recuperação de senha e notificações")
                nova_senha = st.text_input("Senha:*", type="password")

            with col2:
                nova_data_nascimento = st.date_input(
                    "Data de Nascimento:*",
                    value=None,
                    min_value=date(1940, 1, 1),
                    max_value=date.today() - timedelta(days=365*16),  # Mínimo 16 anos
                    help="O funcionário deve ter no mínimo 16 anos")
                confirmar_senha = st.text_input(
                    "Confirmar Senha:*", type="password")
                novo_tipo = st.selectbox(
                    "Tipo de Usuário:*", ["funcionario", "gestor"])
                novo_ativo = st.checkbox("Usuário Ativo", value=True)

            st.markdown("**Jornada de Trabalho Padrão:**")
            col3, col4 = st.columns(2)
            with col3:
                jornada_inicio = st.time_input(
                    "Início da Jornada:", value=time(8, 0))
            with col4:
                jornada_fim = st.time_input(
                    "Fim da Jornada:", value=time(17, 0))
            
            st.markdown("---")
            st.info("💡 **Opcional:** Configure jornada semanal detalhada após criar o usuário na aba de edição")

            submitted = st.form_submit_button(
                "➕ Cadastrar Usuário", width="stretch")

            if submitted:
                # ============================================
                # FUNÇÃO DE VALIDAÇÃO COMPLETA DE CPF
                # Implementa algoritmo oficial da Receita Federal
                # ============================================
                def validar_cpf(cpf: str) -> tuple:
                    """
                    Valida CPF usando o algoritmo oficial dos dígitos verificadores.
                    
                    Args:
                        cpf: String do CPF (com ou sem formatação)
                        
                    Returns:
                        Tuple (cpf_limpo, is_valid, mensagem_erro)
                    """
                    # Remove caracteres não numéricos
                    cpf_limpo = ''.join(filter(str.isdigit, cpf))
                    
                    # Verifica se tem 11 dígitos
                    if len(cpf_limpo) != 11:
                        return None, False, "CPF deve ter 11 dígitos"
                    
                    # Verifica se todos os dígitos são iguais (CPFs inválidos conhecidos)
                    if cpf_limpo == cpf_limpo[0] * 11:
                        return None, False, "CPF inválido (todos os dígitos iguais)"
                    
                    # Calcula o primeiro dígito verificador
                    soma = 0
                    for i in range(9):
                        soma += int(cpf_limpo[i]) * (10 - i)
                    resto = soma % 11
                    digito1 = 0 if resto < 2 else 11 - resto
                    
                    # Verifica primeiro dígito
                    if int(cpf_limpo[9]) != digito1:
                        return None, False, "CPF inválido (dígito verificador incorreto)"
                    
                    # Calcula o segundo dígito verificador
                    soma = 0
                    for i in range(10):
                        soma += int(cpf_limpo[i]) * (11 - i)
                    resto = soma % 11
                    digito2 = 0 if resto < 2 else 11 - resto
                    
                    # Verifica segundo dígito
                    if int(cpf_limpo[10]) != digito2:
                        return None, False, "CPF inválido (dígito verificador incorreto)"
                    
                    return cpf_limpo, True, None
                
                # ============================================
                # FUNÇÃO DE VALIDAÇÃO DE E-MAIL
                # ============================================
                def validar_email(email: str) -> tuple:
                    """
                    Valida formato de e-mail.
                    
                    Args:
                        email: String do e-mail
                        
                    Returns:
                        Tuple (email_limpo, is_valid, mensagem_erro)
                    """
                    import re
                    
                    if not email or not email.strip():
                        return None, False, "E-mail é obrigatório"
                    
                    email_limpo = email.strip().lower()
                    
                    # Regex para validação de e-mail
                    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    
                    if not re.match(pattern, email_limpo):
                        return None, False, "Formato de e-mail inválido"
                    
                    return email_limpo, True, None
                
                # Validações
                cpf_limpo, cpf_valido, cpf_erro = validar_cpf(novo_cpf) if novo_cpf else (None, False, "CPF é obrigatório")
                email_limpo, email_valido, email_erro = validar_email(novo_email)
                
                if not novo_login or not novo_nome or not nova_senha:
                    st.error("❌ Preencha todos os campos obrigatórios!")
                elif not cpf_valido:
                    st.error(f"❌ {cpf_erro}")
                elif not email_valido:
                    st.error(f"❌ {email_erro}")
                elif nova_data_nascimento is None:
                    st.error("❌ Data de Nascimento é obrigatória!")
                elif nova_senha != confirmar_senha:
                    st.error("❌ As senhas não conferem!")
                else:
                    if REFACTORING_ENABLED:
                        try:
                            from password_utils import hash_password
                            senha_hash = hash_password(nova_senha)

                            insert_query = f"""
                                INSERT INTO usuarios 
                                (usuario, senha, tipo, nome_completo, cpf, email, data_nascimento, ativo, 
                                 jornada_inicio_previsto, jornada_fim_previsto)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            """
                            novo_usuario_id = execute_update(insert_query, (
                                novo_login,
                                senha_hash,
                                novo_tipo,
                                novo_nome,
                                cpf_limpo,
                                email_limpo,
                                nova_data_nascimento.strftime("%Y-%m-%d"),
                                int(novo_ativo),
                                jornada_inicio.strftime("%H:%M"),
                                jornada_fim.strftime("%H:%M")
                            ), return_id=True)
                            
                            # Copiar jornada padrão para dias úteis (seg-sex)
                            from jornada_semanal_system import copiar_jornada_padrao_para_dias
                            copiar_jornada_padrao_para_dias(novo_usuario_id, ['seg', 'ter', 'qua', 'qui', 'sex'])
                            
                            log_security_event("USER_CREATED", usuario=st.session_state.usuario, context={"new_user": novo_login, "tipo": novo_tipo})
                            st.success(
                                f"✅ Usuário '{novo_nome}' cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            log_error("Erro ao cadastrar usuário", e, {"novo_login": novo_login})
                            st.error(f"❌ Erro ao cadastrar usuário: {e}")
                    else:
                        # Fallback original — transação atômica: usuario + jornada
                        conn = get_connection()
                        try:
                            cursor = conn.cursor()

                            from password_utils import hash_password
                            senha_hash = hash_password(nova_senha)

                            cursor.execute(f"""
                                INSERT INTO usuarios 
                                (usuario, senha, tipo, nome_completo, cpf, email, data_nascimento, ativo, 
                                 jornada_inicio_previsto, jornada_fim_previsto)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                RETURNING id
                            """, (
                                novo_login,
                                senha_hash,
                                novo_tipo,
                                novo_nome,
                                cpf_limpo,
                                email_limpo,
                                nova_data_nascimento.strftime("%Y-%m-%d"),
                                int(novo_ativo),
                                jornada_inicio.strftime("%H:%M"),
                                jornada_fim.strftime("%H:%M")
                            ))

                            # Obter ID do usuário recém-criado
                            novo_usuario_id = cursor.fetchone()[0]

                            # Copiar jornada padrão NA MESMA transação
                            from jornada_semanal_system import copiar_jornada_padrao_para_dias
                            copiar_jornada_padrao_para_dias(
                                novo_usuario_id,
                                ['seg', 'ter', 'qua', 'qui', 'sex'],
                                conn_external=conn,
                            )

                            conn.commit()

                            st.success(
                                f"✅ Usuário '{novo_nome}' cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"❌ Erro ao cadastrar usuário: {e}")
                        finally:
                            _return_conn(conn)


def horas_por_projeto_interface():
    """
    Interface para visualizar distribuição de horas por projeto.
    Mostra percentuais do tempo dedicado a cada projeto.
    """
    from horas_projeto_system import (
        HorasProjetoSystem, 
        format_horas_projeto, 
        format_percentual,
        get_cor_projeto,
        CORES_PROJETOS
    )
    
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Distribuição de Horas por Projeto</h3>
        <p>Visualize quanto tempo (em horas e percentual) foi dedicado a cada projeto</p>
    </div>
    """, unsafe_allow_html=True)
    
    horas_projeto_system = HorasProjetoSystem()
    
    # Abas
    tab1, tab2, tab3 = st.tabs([
        "📊 Visão Mensal",
        "👤 Por Funcionário",
        "📈 Evolução"
    ])
    
    with tab1:
        st.markdown("### 📅 Distribuição Mensal de Horas por Projeto")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            anos = list(range(date.today().year, date.today().year - 3, -1))
            ano_selecionado = st.selectbox("Ano:", anos, key="hp_ano")
        with col2:
            meses = [
                (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
                (4, "Abril"), (5, "Maio"), (6, "Junho"),
                (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
                (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
            ]
            mes_selecionado = st.selectbox(
                "Mês:",
                meses,
                format_func=lambda x: x[1],
                index=date.today().month - 1,
                key="hp_mes"
            )[0]
        
        # Buscar dados
        resultado = horas_projeto_system.obter_relatorio_mensal_todos_funcionarios(
            ano=ano_selecionado,
            mes=mes_selecionado
        )
        
        if resultado.get('success') and resultado.get('projetos_consolidados'):
            projetos = resultado['projetos_consolidados']
            total_geral = resultado.get('total_geral', 0)
            
            # Métricas principais
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("⏱️ Total de Horas", format_horas_projeto(total_geral))
            with col2:
                st.metric("📁 Projetos Ativos", len(projetos))
            with col3:
                st.metric("👥 Funcionários", len(resultado.get('funcionarios', [])))
            
            st.markdown("---")
            
            # Gráfico de pizza com percentuais
            st.markdown("### 🥧 Distribuição por Projeto")
            
            if projetos:
                # Criar dados para visualização
                df_projetos = pd.DataFrame(projetos)
                
                # Visualização com barras horizontais + percentuais
                for i, proj in enumerate(projetos):
                    cor = get_cor_projeto(i)
                    percentual = proj['percentual']
                    horas = proj['horas']
                    nome = proj['projeto']
                    
                    # Barra de progresso visual
                    st.markdown(f"""
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style="font-weight: bold; color: {cor};">📁 {nome}</span>
                            <span style="font-weight: bold;">{format_horas_projeto(horas)} ({format_percentual(percentual)})</span>
                        </div>
                        <div style="background-color: #e0e0e0; border-radius: 10px; height: 25px; overflow: hidden;">
                            <div style="background-color: {cor}; width: {percentual}%; height: 100%; border-radius: 10px;
                                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                                {format_percentual(percentual) if percentual > 10 else ''}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Tabela detalhada
                st.markdown("### 📋 Tabela Detalhada")
                df_display = df_projetos.copy()
                df_display['Horas'] = df_display['horas'].apply(format_horas_projeto)
                df_display['Percentual'] = df_display['percentual'].apply(lambda x: f"{x:.1f}%")
                df_display = df_display.rename(columns={'projeto': 'Projeto'})
                
                st.dataframe(
                    df_display[['Projeto', 'Horas', 'Percentual']],
                    width="stretch",
                    hide_index=True
                )
                
                # Exportar CSV
                csv_data = df_projetos.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Exportar CSV",
                    data=csv_data,
                    file_name=f"horas_projeto_{ano_selecionado}_{mes_selecionado:02d}.csv",
                    mime="text/csv"
                )
            else:
                st.info("📭 Nenhum registro de horas encontrado para este período.")
        else:
            st.warning("⚠️ Não foi possível carregar os dados. Verifique se há registros no período selecionado.")
    
    with tab2:
        st.markdown("### 👤 Horas por Projeto - Por Funcionário")
        
        # Buscar funcionários
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT usuario, nome_completo 
                FROM usuarios 
                WHERE tipo = 'funcionario' AND ativo = 1
                ORDER BY nome_completo
            """)
            funcionarios = cursor.fetchall()
        finally:
            _return_conn(conn)
        
        if funcionarios:
            # Seleção de funcionário
            func_opcoes = {f[1] or f[0]: f[0] for f in funcionarios}
            func_nome = st.selectbox(
                "Selecione o funcionário:",
                list(func_opcoes.keys()),
                key="hp_func"
            )
            func_usuario = func_opcoes[func_nome]
            
            # Período
            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input(
                    "Data início:",
                    value=date.today().replace(day=1),
                    key="hp_data_inicio"
                )
            with col2:
                data_fim = st.date_input(
                    "Data fim:",
                    value=date.today(),
                    key="hp_data_fim"
                )
            
            # Buscar dados do funcionário
            resultado_func = horas_projeto_system.calcular_horas_por_projeto_periodo(
                usuario=func_usuario,
                data_inicio=data_inicio.strftime('%Y-%m-%d'),
                data_fim=data_fim.strftime('%Y-%m-%d')
            )
            
            if resultado_func.get('success') and resultado_func.get('projetos'):
                projetos = resultado_func['projetos']
                total_horas = resultado_func.get('total_horas', 0)
                
                st.markdown(f"**Total de horas no período:** {format_horas_projeto(total_horas)}")
                st.markdown("---")
                
                # Cards por projeto
                cols = st.columns(min(len(projetos), 3))
                for i, proj in enumerate(projetos):
                    with cols[i % 3]:
                        cor = get_cor_projeto(i)
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, {cor}20, {cor}40);
                            border-left: 4px solid {cor};
                            padding: 15px;
                            border-radius: 8px;
                            margin-bottom: 10px;
                        ">
                            <h4 style="margin: 0; color: {cor};">📁 {proj['projeto']}</h4>
                            <p style="font-size: 24px; font-weight: bold; margin: 10px 0;">{format_horas_projeto(proj['horas'])}</p>
                            <p style="font-size: 18px; color: #666;">{format_percentual(proj['percentual'])} do total</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Gráfico de barras
                st.markdown("### 📊 Visualização")
                df_func = pd.DataFrame(projetos)
                st.bar_chart(df_func.set_index('projeto')['horas'])
                
            else:
                st.info("📭 Nenhum registro encontrado para este funcionário no período selecionado.")
        else:
            st.warning("⚠️ Nenhum funcionário cadastrado.")
    
    with tab3:
        st.markdown("### 📈 Evolução de Horas por Projeto")
        
        # Buscar projetos
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT nome FROM projetos WHERE ativo = 1 ORDER BY nome")
            projetos_lista = [row[0] for row in cursor.fetchall()]
        finally:
            _return_conn(conn)
        
        if projetos_lista:
            projeto_selecionado = st.selectbox(
                "Selecione o projeto:",
                projetos_lista,
                key="hp_evolucao_projeto"
            )
            
            meses_evolucao = st.slider(
                "Período (meses):",
                min_value=3,
                max_value=12,
                value=6,
                key="hp_evolucao_meses"
            )
            
            resultado_evolucao = horas_projeto_system.obter_evolucao_projeto(
                projeto_nome=projeto_selecionado,
                meses=meses_evolucao
            )
            
            if resultado_evolucao.get('success') and resultado_evolucao.get('evolucao'):
                evolucao = resultado_evolucao['evolucao']
                
                df_evolucao = pd.DataFrame(evolucao)
                df_evolucao['Mês'] = df_evolucao['mes']
                df_evolucao['Horas'] = df_evolucao['horas']
                
                st.line_chart(df_evolucao.set_index('Mês')['Horas'])
                
                # Tabela de evolução
                st.markdown("#### 📋 Dados da Evolução")
                df_display = df_evolucao.copy()
                df_display['Horas Formatadas'] = df_display['horas'].apply(format_horas_projeto)
                st.dataframe(
                    df_display[['Mês', 'Horas Formatadas']],
                    width="stretch",
                    hide_index=True
                )
            else:
                st.info("📭 Nenhum dado de evolução encontrado para este projeto.")
        else:
            st.warning("⚠️ Nenhum projeto cadastrado.")


def relatorios_horas_extras_interface():
    """Interface de relatórios de horas extras"""
    from relatorios_horas_extras import (
        gerar_relatorio_horas_extras,
        gerar_relatorio_por_usuario,
        gerar_relatorio_mensal,
        obter_estatisticas_gerais
    )
    
    st.markdown("""
    <div class="feature-card">
        <h3>📈 Relatórios de Horas Extras</h3>
        <p>Visualize e exporte relatórios de horas extras</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Abas de relatórios
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Visão Geral",
        "👤 Por Funcionário",
        "📅 Mensal",
        "🔍 Detalhado"
    ])
    
    with tab1:
        st.markdown("### 📊 Estatísticas Gerais")
        
        stats = obter_estatisticas_gerais()
        
        if stats.get('success'):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Solicitações", stats.get('total_solicitacoes', 0))
            
            with col2:
                st.metric("Total Horas Aprovadas", f"{stats.get('total_horas_aprovadas', 0):.1f}h")
            
            with col3:
                st.metric("Média por Solicitação", f"{stats.get('media_horas_aprovadas', 0):.1f}h")
            
            with col4:
                pendentes = stats.get('por_status', {}).get('pendente', 0)
                st.metric("Pendentes", pendentes)
            
            # Status breakdown
            st.markdown("---")
            st.markdown("### Status das Solicitações")
            
            por_status = stats.get('por_status', {})
            if por_status:
                status_df_data = []
                for status, count in por_status.items():
                    emoji = {'pendente': '⏳', 'aprovado': '✅', 'rejeitado': '❌'}.get(status, '❓')
                    status_df_data.append({
                        'Status': f"{emoji} {status.title()}",
                        'Quantidade': count
                    })
                
                if status_df_data:
                    import pandas as pd
                    df_status = pd.DataFrame(status_df_data)
                    st.dataframe(df_status, width="stretch", hide_index=True)
        else:
            st.warning("Não foi possível carregar as estatísticas.")
    
    with tab2:
        st.markdown("### 👤 Horas Extras por Funcionário")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            data_inicio_usr = st.date_input(
                "Data Inicial",
                value=date.today().replace(day=1),
                key="rel_usr_inicio"
            )
        with col2:
            data_fim_usr = st.date_input(
                "Data Final",
                value=date.today(),
                key="rel_usr_fim"
            )
        
        if st.button("🔄 Gerar Relatório por Usuário", key="btn_rel_usr"):
            relatorio = gerar_relatorio_por_usuario(
                inicio=data_inicio_usr.strftime('%Y-%m-%d'),
                fim=data_fim_usr.strftime('%Y-%m-%d')
            )
            
            if relatorio.get('success') and relatorio.get('usuarios'):
                import pandas as pd
                
                df_data = []
                for usr in relatorio['usuarios']:
                    df_data.append({
                        'Funcionário': usr['nome_completo'],
                        'Solicitações': usr['total_solicitacoes'],
                        'Horas Aprovadas': f"{usr['horas_aprovadas']:.1f}h",
                        'Pendentes': usr['pendentes'],
                        'Aprovadas': usr['aprovadas'],
                        'Rejeitadas': usr['rejeitadas']
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, width="stretch", hide_index=True)
                
                # Exportar CSV
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Exportar CSV",
                    csv,
                    f"horas_extras_por_usuario_{data_inicio_usr}_{data_fim_usr}.csv",
                    "text/csv",
                    key="download_csv_usr"
                )
            else:
                st.info("Nenhum registro encontrado para o período selecionado.")
    
    with tab3:
        st.markdown("### 📅 Relatório Mensal")
        
        col1, col2 = st.columns(2)
        with col1:
            ano = st.selectbox(
                "Ano",
                options=list(range(date.today().year, date.today().year - 3, -1)),
                key="rel_ano"
            )
        with col2:
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            mes_idx = st.selectbox(
                "Mês",
                options=range(1, 13),
                format_func=lambda x: meses[x-1],
                index=date.today().month - 1,
                key="rel_mes"
            )
        
        if st.button("🔄 Gerar Relatório Mensal", key="btn_rel_mes"):
            relatorio = gerar_relatorio_mensal(ano=ano, mes=mes_idx)
            
            if relatorio.get('success'):
                st.markdown(f"**Período:** {meses[mes_idx-1]}/{ano}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Registros", relatorio.get('total_registros', 0))
                with col2:
                    st.metric("Total de Horas", f"{relatorio.get('total_horas', 0):.1f}h")
                with col3:
                    st.metric("Aprovadas", relatorio.get('total_aprovadas', 0))
                
                # Lista de horas extras
                if relatorio.get('horas_extras'):
                    st.markdown("---")
                    st.markdown("### Detalhamento")
                    
                    import pandas as pd
                    df_data = []
                    for he in relatorio['horas_extras']:
                        df_data.append({
                            'Funcionário': he['nome_completo'],
                            'Data': he['data'],
                            'Horário': f"{he['hora_inicio']} - {he['hora_fim']}",
                            'Horas': f"{he['horas']:.1f}h",
                            'Status': he['status'].title()
                        })
                    
                    df = pd.DataFrame(df_data)
                    st.dataframe(df, width="stretch", hide_index=True)
            else:
                st.info("Nenhum registro encontrado para o período selecionado.")
    
    with tab4:
        st.markdown("### 🔍 Relatório Detalhado")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            data_inicio = st.date_input(
                "Data Inicial",
                value=date.today() - timedelta(days=30),
                key="rel_det_inicio"
            )
        
        with col2:
            data_fim = st.date_input(
                "Data Final",
                value=date.today(),
                key="rel_det_fim"
            )
        
        with col3:
            status_filtro = st.selectbox(
                "Status",
                options=["Todos", "pendente", "aprovado", "rejeitado"],
                key="rel_det_status"
            )
        
        # Buscar usuários para filtro
        usuarios_options = ["Todos"]
        if REFACTORING_ENABLED:
            try:
                result = execute_query("SELECT usuario, nome_completo FROM usuarios WHERE tipo = 'funcionario' ORDER BY nome_completo")
                if result:
                    usuarios_options.extend([f"{r[1]} ({r[0]})" for r in result])
            except Exception as e:
                logger.warning(f"Erro ao buscar usuários para filtro de relatório: {e}")
        
        usuario_filtro = st.selectbox("Funcionário", options=usuarios_options, key="rel_det_usr")
        
        if st.button("🔄 Gerar Relatório Detalhado", key="btn_rel_det"):
            # Extrair username se selecionado
            usr_param = None
            if usuario_filtro != "Todos":
                # Extrair do formato "Nome (username)"
                import re
                match = re.search(r'\(([^)]+)\)$', usuario_filtro)
                if match:
                    usr_param = match.group(1)
            
            status_param = None if status_filtro == "Todos" else status_filtro
            
            relatorio = gerar_relatorio_horas_extras(
                usuario=usr_param,
                inicio=data_inicio.strftime('%Y-%m-%d'),
                fim=data_fim.strftime('%Y-%m-%d'),
                status=status_param
            )
            
            if relatorio.get('success') and relatorio.get('horas_extras'):
                st.success(f"✅ {relatorio.get('total_registros', 0)} registros encontrados")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Horas", f"{relatorio.get('total_horas', 0):.1f}h")
                with col2:
                    st.metric("Pendentes", relatorio.get('total_pendentes', 0))
                with col3:
                    st.metric("Aprovadas", relatorio.get('total_aprovadas', 0))
                with col4:
                    st.metric("Rejeitadas", relatorio.get('total_rejeitadas', 0))
                
                st.markdown("---")
                
                import pandas as pd
                df_data = []
                for he in relatorio['horas_extras']:
                    df_data.append({
                        'ID': he['id'],
                        'Funcionário': he['nome_completo'],
                        'Data': he['data'],
                        'Início': he['hora_inicio'],
                        'Fim': he['hora_fim'],
                        'Horas': f"{he['horas']:.1f}h",
                        'Status': he['status'].title(),
                        'Aprovado Por': he.get('aprovado_por', '-')
                    })
                
                df = pd.DataFrame(df_data)
                st.dataframe(df, width="stretch", hide_index=True)
                
                # Exportar
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Exportar CSV",
                    csv,
                    f"relatorio_horas_extras_{data_inicio}_{data_fim}.csv",
                    "text/csv",
                    key="download_csv_det"
                )
            else:
                st.info("Nenhum registro encontrado com os filtros selecionados.")


# ====================================================================
# Funções auxiliares extraídas de sistema_interface() para legibilidade
# ====================================================================

def _render_backup_email_section():
    """Seção de configuração de Backup por Email (Conformidade Legal)."""
    st.markdown("---")
    st.markdown("### 📧 Backup por Email (Conformidade Legal)")

    st.info("""
    ⚖️ **Importante:** Por lei (Portaria 671/2021), os registros de ponto devem ser mantidos por **5 anos**.
    Configure o envio automático de backups para seu email para garantir a conformidade legal.
    """)

    # Verificar se email está configurado
    from email_notifications import is_email_configured

    if not is_email_configured():
        st.warning("""
        ⚠️ **Sistema de email não configurado**

        Para ativar backup por email, adicione no Render:
        - `SMTP_HOST` (ex: smtp.gmail.com)
        - `SMTP_PORT` (ex: 587)
        - `SMTP_USER` (seu email)
        - `SMTP_PASSWORD` (senha de app do Gmail)
        """)
    else:
        st.success("✅ Sistema de email configurado")

        # Buscar configuração atual de email de backup
        email_backup_atual = ''
        backup_email_ativo = '0'
        backup_email_frequencia = 'semanal'

        try:
            conn_bkp = get_connection()
            try:
                cursor_bkp = conn_bkp.cursor()

                cursor_bkp.execute(f"SELECT valor FROM configuracoes WHERE chave = 'backup_email_destino'")
                result = cursor_bkp.fetchone()
                if result:
                    email_backup_atual = result[0] or ''

                cursor_bkp.execute(f"SELECT valor FROM configuracoes WHERE chave = 'backup_email_ativo'")
                result = cursor_bkp.fetchone()
                if result:
                    backup_email_ativo = result[0] or '0'

                cursor_bkp.execute(f"SELECT valor FROM configuracoes WHERE chave = 'backup_email_frequencia'")
                result = cursor_bkp.fetchone()
                if result:
                    backup_email_frequencia = result[0] or 'semanal'
            finally:
                _return_conn(conn_bkp)
        except Exception as e:
            logger.debug("Erro silenciado: %s", e)

        with st.form("config_backup_email"):
            col_be1, col_be2 = st.columns([2, 1])

            with col_be1:
                email_backup = st.text_input(
                    "📬 Email para receber backups",
                    value=email_backup_atual,
                    placeholder="seu.email@empresa.com.br",
                    help="O backup será enviado para este email automaticamente"
                )

            with col_be2:
                frequencia = st.selectbox(
                    "📅 Frequência",
                    options=['semanal', 'quinzenal', 'mensal'],
                    index=['semanal', 'quinzenal', 'mensal'].index(backup_email_frequencia) if backup_email_frequencia in ['semanal', 'quinzenal', 'mensal'] else 0,
                    help="Com que frequência o backup será enviado"
                )

            ativar_backup_email = st.checkbox(
                "✅ Ativar envio automático de backup por email",
                value=backup_email_ativo == '1',
                help="Quando ativado, você receberá o backup completo do sistema no email cadastrado"
            )

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                salvar_config = st.form_submit_button("💾 Salvar Configuração", width="stretch")

            with col_btn2:
                enviar_agora = st.form_submit_button("📤 Enviar Backup Agora", width="stretch", type="secondary")

        if salvar_config:
            if ativar_backup_email and not email_backup:
                st.error("❌ Informe o email para receber os backups")
            else:
                try:
                    conn_bkp = get_connection()
                    try:
                        cursor_bkp = conn_bkp.cursor()

                        configs_backup = [
                            ('backup_email_destino', email_backup, 'Email para envio de backups'),
                            ('backup_email_ativo', '1' if ativar_backup_email else '0', 'Backup por email ativo'),
                            ('backup_email_frequencia', frequencia, 'Frequência do backup por email'),
                        ]

                        for chave, valor, descricao in configs_backup:
                            cursor_bkp.execute(f"""
                                INSERT INTO configuracoes (chave, valor, descricao)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                ON CONFLICT (chave) DO UPDATE SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                            """, (chave, valor, descricao, valor))

                        conn_bkp.commit()
                    finally:
                        _return_conn(conn_bkp)

                    if ativar_backup_email:
                        st.success(f"✅ Backup por email ativado! Você receberá backups {frequencia}mente em **{email_backup}**")
                    else:
                        st.warning("⚠️ Backup por email desativado")

                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {e}")

        if enviar_agora:
            if not email_backup:
                st.error("❌ Informe o email para enviar o backup")
            else:
                with st.spinner("📤 Gerando e enviando backup... Aguarde..."):
                    try:
                        from backup_postgresql import enviar_backup_por_email
                        sucesso, mensagem = enviar_backup_por_email(email_backup, 'json')

                        if sucesso:
                            st.success(f"✅ {mensagem}")
                            st.balloons()
                        else:
                            st.error(f"❌ {mensagem}")
                    except Exception as e:
                        st.error(f"❌ Erro ao enviar backup: {e}")


def _render_push_notifications_config():
    """Seção de configuração de Push Notifications globais."""
    st.markdown("---")
    st.markdown("### 📱 Push Notifications (Lembretes no Celular/Navegador)")

    vapid_key = os.getenv('VAPID_PUBLIC_KEY', '')
    if vapid_key:
        st.success("✅ **Push Notifications configurado** - Sistema pronto para enviar lembretes")

        # Buscar configuração atual
        push_obrigatorio_atual = '1'  # Padrão: obrigatório
        try:
            if REFACTORING_ENABLED:
                result = execute_query(
                    "SELECT valor FROM configuracoes WHERE chave = 'push_notifications_obrigatorio'",
                    fetch_one=True
                )
                if result:
                    push_obrigatorio_atual = result[0]
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'push_notifications_obrigatorio'")
                    result = cursor.fetchone()
                    if result:
                        push_obrigatorio_atual = result[0]
                finally:
                    _return_conn(conn)
        except Exception as e:
            logger.debug("Erro silenciado: %s", e)

        with st.form("config_push_global"):
            st.markdown("#### ⚙️ Configurações Globais de Push")

            push_obrigatorio = st.checkbox(
                "🔒 **Notificações Obrigatórias para Todos**",
                value=push_obrigatorio_atual == '1',
                help="Quando ativado, todos os usuários verão um modal pedindo para ativar notificações ao fazer login. Recomendado para garantir que ninguém esqueça de bater o ponto."
            )

            st.info("""
            📋 **Como funciona:**
            - Após login, um modal aparece pedindo para ativar notificações
            - O usuário pode clicar "Lembrar mais tarde" (aparecerá novamente no próximo dia)
            - Quando ativado, recebe lembretes de entrada, saída e hora extra
            - Apenas você (gestor) pode desabilitar esta obrigatoriedade
            """)

            if st.form_submit_button("💾 Salvar Configuração de Push", width="stretch"):
                try:
                    valor = '1' if push_obrigatorio else '0'

                    if REFACTORING_ENABLED:
                        execute_update(f"""
                            INSERT INTO configuracoes (chave, valor, descricao)
                            VALUES ('push_notifications_obrigatorio', {SQL_PLACEHOLDER}, 'Push notifications obrigatórias para todos')
                            ON CONFLICT (chave) DO UPDATE SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                        """, (valor, valor))
                    else:
                        conn = get_connection()
                        try:
                            cursor = conn.cursor()
                            cursor.execute(f"""
                                INSERT INTO configuracoes (chave, valor, descricao)
                                VALUES ('push_notifications_obrigatorio', {SQL_PLACEHOLDER}, 'Push notifications obrigatórias para todos')
                                ON CONFLICT (chave) DO UPDATE SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                            """, (valor, valor))
                            conn.commit()
                        finally:
                            _return_conn(conn)

                    if push_obrigatorio:
                        st.success("✅ Notificações obrigatórias ATIVADAS! Todos os usuários serão solicitados a ativar.")
                    else:
                        st.warning("⚠️ Notificações obrigatórias DESATIVADAS. Modal não aparecerá mais.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao salvar: {e}")
    else:
        st.warning("""
        ⚠️ **Push Notifications não configurado**

        Para ativar, adicione as seguintes variáveis de ambiente no Render:
        - `VAPID_PUBLIC_KEY`
        - `VAPID_PRIVATE_KEY`
        - `VAPID_CLAIM_EMAIL`
        """)


def _render_auto_notifications_config():
    """Seção de configuração de Notificações Automáticas (Scheduler)."""
    st.markdown("---")
    st.markdown("### 🔔 Notificações Automáticas")
    st.markdown("""
    O sistema envia notificações automáticas para:
    - **Funcionários** que esqueceram de bater ponto (entrada/saída)
    - **Funcionários** em hora extra prolongada
    - **Gestores** sobre solicitações pendentes de aprovação
    """)

    try:
        from background_scheduler import obter_status_scheduler, iniciar_scheduler_background

        status = obter_status_scheduler()

        if status['ativo']:
            st.success("✅ **Scheduler ativo** - Notificações automáticas funcionando!")

            with st.expander("📋 Ver jobs agendados", expanded=False):
                if status['jobs']:
                    for job in status['jobs']:
                        st.markdown(f"- **{job['nome']}**: próxima execução em `{job['proximo_execucao']}`")
                else:
                    st.info("Nenhum job agendado no momento.")

            st.markdown(f"🕐 **Horário do servidor:** {status['data_hora_atual']}")
        else:
            st.warning("⚠️ **Scheduler inativo** - Notificações automáticas desabilitadas")
            st.info("Você pode iniciar agora sem reiniciar o app.")
            if st.button("▶️ Iniciar Scheduler Agora", key="iniciar_scheduler_manual"):
                try:
                    if iniciar_scheduler_background():
                        st.success("✅ Scheduler iniciado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Não foi possível iniciar o scheduler.")
                except Exception as e:
                    st.error(f"❌ Erro ao iniciar scheduler: {e}")

    except ImportError:
        st.info("ℹ️ Módulo de notificações automáticas não disponível.")
    except Exception as e:
        st.error(f"❌ Erro ao verificar scheduler: {e}")

    # ============================================
    # Configuração dos horários de notificação
    # ============================================
    st.markdown("#### ⏰ Configurar Horários")

    # Buscar configurações salvas
    config_notif = {
        'notif_entrada_ativo': '1',
        'notif_entrada_horarios': '08:15,08:30,09:00',
        'notif_saida_ativo': '1',
        'notif_saida_horarios': '17:15,17:30,18:00',
        'notif_hora_extra_ativo': '1',
        'notif_hora_extra_inicio': '18:00',
        'notif_hora_extra_fim': '22:00',
        'notif_aprovadores_ativo': '1',
        'notif_aprovadores_horarios': '09:00,14:00,17:00'
    }

    # Buscar valores do banco
    if REFACTORING_ENABLED:
        try:
            for chave in config_notif.keys():
                result = execute_query(
                    f"SELECT valor FROM configuracoes WHERE chave = {SQL_PLACEHOLDER}",
                    (chave,),
                    fetch_one=True
                )
                if result:
                    config_notif[chave] = result[0]
        except Exception as e:
            logger.debug("Erro silenciado: %s", e)
    else:
        try:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                for chave in config_notif.keys():
                    cursor.execute(f"SELECT valor FROM configuracoes WHERE chave = {SQL_PLACEHOLDER}", (chave,))
                    result = cursor.fetchone()
                    if result:
                        config_notif[chave] = result[0]
            finally:
                _return_conn(conn)
        except Exception as e:
            logger.debug("Erro silenciado: %s", e)

    with st.form("config_notificacoes"):
        # Lembretes de Entrada
        col1, col2 = st.columns([1, 3])
        with col1:
            entrada_ativo = st.checkbox(
                "Lembrete Entrada",
                value=config_notif['notif_entrada_ativo'] == '1',
                help="Notifica funcionários que esqueceram de bater ponto de entrada"
            )
        with col2:
            entrada_horarios = st.text_input(
                "Horários (separados por vírgula)",
                value=config_notif['notif_entrada_horarios'],
                placeholder="08:15,08:30,09:00",
                key="entrada_horarios"
            )

        # Lembretes de Saída
        col1, col2 = st.columns([1, 3])
        with col1:
            saida_ativo = st.checkbox(
                "Lembrete Saída",
                value=config_notif['notif_saida_ativo'] == '1',
                help="Notifica funcionários que esqueceram de bater ponto de saída"
            )
        with col2:
            saida_horarios = st.text_input(
                "Horários (separados por vírgula)",
                value=config_notif['notif_saida_horarios'],
                placeholder="17:15,17:30,18:00",
                key="saida_horarios"
            )

        # Alertas de Hora Extra
        col1, col2, col3 = st.columns([1, 1.5, 1.5])
        with col1:
            hora_extra_ativo = st.checkbox(
                "Alerta Hora Extra",
                value=config_notif['notif_hora_extra_ativo'] == '1',
                help="Notifica funcionários em hora extra prolongada"
            )
        with col2:
            he_inicio = st.time_input(
                "Início monitoramento",
                value=datetime.strptime(config_notif['notif_hora_extra_inicio'], "%H:%M").time(),
                key="he_inicio"
            )
        with col3:
            he_fim = st.time_input(
                "Fim monitoramento",
                value=datetime.strptime(config_notif['notif_hora_extra_fim'], "%H:%M").time(),
                key="he_fim"
            )

        # Lembretes para Aprovadores
        col1, col2 = st.columns([1, 3])
        with col1:
            aprovadores_ativo = st.checkbox(
                "Lembrete Aprovadores",
                value=config_notif['notif_aprovadores_ativo'] == '1',
                help="Notifica gestores sobre solicitações pendentes"
            )
        with col2:
            aprovadores_horarios = st.text_input(
                "Horários (separados por vírgula)",
                value=config_notif['notif_aprovadores_horarios'],
                placeholder="09:00,14:00,17:00",
                key="aprovadores_horarios"
            )

        if st.form_submit_button("💾 Salvar Configurações de Notificação", width="stretch"):
            novas_configs = [
                ('notif_entrada_ativo', '1' if entrada_ativo else '0'),
                ('notif_entrada_horarios', entrada_horarios),
                ('notif_saida_ativo', '1' if saida_ativo else '0'),
                ('notif_saida_horarios', saida_horarios),
                ('notif_hora_extra_ativo', '1' if hora_extra_ativo else '0'),
                ('notif_hora_extra_inicio', he_inicio.strftime("%H:%M")),
                ('notif_hora_extra_fim', he_fim.strftime("%H:%M")),
                ('notif_aprovadores_ativo', '1' if aprovadores_ativo else '0'),
                ('notif_aprovadores_horarios', aprovadores_horarios),
            ]

            try:
                if REFACTORING_ENABLED:
                    for chave, valor in novas_configs:
                        # Insert or update
                        execute_update(f"""
                            INSERT INTO configuracoes (chave, valor, descricao)
                            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            ON CONFLICT (chave) DO UPDATE SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                        """, (chave, valor, f'Config notificação: {chave}', valor))
                else:
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()
                        for chave, valor in novas_configs:
                            cursor.execute(f"""
                                INSERT INTO configuracoes (chave, valor, descricao)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                                ON CONFLICT (chave) DO UPDATE SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                            """, (chave, valor, f'Config notificação: {chave}', valor))
                        conn.commit()
                    finally:
                        _return_conn(conn)

                st.success("✅ Configurações de notificação salvas!")
                st.info("⚠️ As alterações serão aplicadas na próxima reinicialização do app.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro ao salvar: {e}")

    st.markdown("---")
    st.caption("💡 **Dica:** Os horários devem estar no formato HH:MM, separados por vírgula. Ex: 08:15,08:30,09:00")


def sistema_interface():
    """Interface de configurações do sistema"""
    st.markdown("""
    <div class="feature-card">
        <h3>⚙️ Configurações do Sistema</h3>
        <p>Configure parâmetros gerais do sistema de ponto</p>
    </div>
    """, unsafe_allow_html=True)

    # Criar tabela de configurações se não existir
    if REFACTORING_ENABLED:
        try:
            query_create = """
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT,
                    descricao TEXT,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            execute_update(query_create)
        except Exception as e:
            log_error("Erro ao criar tabela de configurações", e, {"table": "configuracoes"})
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT,
                    descricao TEXT,
                    data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            _return_conn(conn)

    # Configurações padrão
    configs_padrao = [
        ('jornada_inicio_padrao', '08:00', 'Horário padrão de início da jornada'),
        ('jornada_fim_padrao', '17:00', 'Horário padrão de fim da jornada'),
        ('tolerancia_atraso_minutos', '10', 'Tolerância de atraso em minutos'),
        ('horas_extras_automatico', '1',
         'Calcular horas extras automaticamente (1=sim, 0=não)'),
        ('notificacao_fim_jornada', '1',
         'Notificar funcionário ao fim da jornada (1=sim, 0=não)'),
        ('backup_automatico', '1', 'Realizar backup automático diário (1=sim, 0=não)'),
        ('gps_obrigatorio', '0', 'Exigir GPS ao registrar ponto (1=sim, 0=não)'),
        ('max_distancia_metros', '1000',
         'Distância máxima permitida do local de trabalho (metros)'),
        ('aprovacao_automatica_atestado', '0',
         'Aprovar atestados automaticamente (1=sim, 0=não)'),
        ('dias_historico_padrao', '30', 'Dias de histórico exibidos por padrão'),
    ]

    if REFACTORING_ENABLED:
        try:
            for chave, valor, descricao in configs_padrao:
                query_insert = f"""
                    INSERT INTO configuracoes (chave, valor, descricao)
                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                    ON CONFLICT (chave) DO NOTHING
                """
                execute_update(query_insert, (chave, valor, descricao))
        except Exception as e:
            log_error("Erro ao inserir configurações padrão", e, {"context": "init_configs"})
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            for chave, valor, descricao in configs_padrao:
                cursor.execute(f"""
                    INSERT INTO configuracoes (chave, valor, descricao)
                    VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                    ON CONFLICT (chave) DO NOTHING
                """, (chave, valor, descricao))
            conn.commit()
        finally:
            _return_conn(conn)

    # Buscar configurações atuais
    configs = None
    
    if REFACTORING_ENABLED:
        try:
            query_configs = "SELECT chave, valor, descricao FROM configuracoes ORDER BY chave"
            configs = execute_query(query_configs)
        except Exception as e:
            log_error("Erro ao buscar configurações", e, {})
            configs = []
    else:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT chave, valor, descricao FROM configuracoes ORDER BY chave")
            configs = cursor.fetchall()
        finally:
            _return_conn(conn)

    # Organizar por categorias
    st.markdown("### ⏰ Configurações de Jornada")

    with st.form("config_jornada"):
        col1, col2 = st.columns(2)

        # Obter valores atuais
        config_dict = {c[0]: c[1] for c in configs}

        with col1:
            jornada_inicio = st.time_input(
                "Horário Padrão de Início:",
                value=datetime.strptime(config_dict.get(
                    'jornada_inicio_padrao', '08:00'), "%H:%M").time()
            )
            tolerancia = st.number_input(
                "Tolerância de Atraso (minutos):",
                min_value=0,
                max_value=60,
                value=int(config_dict.get('tolerancia_atraso_minutos', '10'))
            )

        with col2:
            jornada_fim = st.time_input(
                "Horário Padrão de Fim:",
                value=datetime.strptime(config_dict.get(
                    'jornada_fim_padrao', '17:00'), "%H:%M").time()
            )
            dias_historico = st.number_input(
                "Dias de Histórico Padrão:",
                min_value=7,
                max_value=365,
                value=int(config_dict.get('dias_historico_padrao', '30'))
            )

        if st.form_submit_button("💾 Salvar Configurações de Jornada", width="stretch"):
            configs_jornada = [
                ('jornada_inicio_padrao', jornada_inicio.strftime("%H:%M")),
                ('jornada_fim_padrao', jornada_fim.strftime("%H:%M")),
                ('tolerancia_atraso_minutos', str(tolerancia)),
                ('dias_historico_padrao', str(dias_historico)),
            ]

            try:
                if REFACTORING_ENABLED:
                    for chave, valor in configs_jornada:
                        query_update = f"""
                            UPDATE configuracoes 
                            SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                            WHERE chave = {SQL_PLACEHOLDER}
                        """
                        execute_update(query_update, (valor, chave))
                    log_security_event("SYSTEM_CONFIG_UPDATED", usuario=st.session_state.get('usuario', 'sistema'), context={"configs": [c[0] for c in configs_jornada]})
                else:
                    conn = get_connection()
                    try:
                        cursor = conn.cursor()

                        for chave, valor in configs_jornada:
                            cursor.execute(f"""
                                UPDATE configuracoes 
                                SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                                WHERE chave = {SQL_PLACEHOLDER}
                            """, (valor, chave))

                        conn.commit()
                    finally:
                        _return_conn(conn)

                st.success("✅ Configurações de jornada salvas!")
                st.rerun()
            except Exception as e:
                log_error("Erro ao salvar configurações de jornada", e, {"context": "config_update"})
                st.error(f"❌ Erro ao salvar: {str(e)}")

    st.markdown("---")
    st.markdown("### 🕐 Configurações de Horas Extras")

    with st.form("config_horas_extras"):
        col1, col2 = st.columns(2)

        with col1:
            horas_extras_auto = st.checkbox(
                "Calcular Horas Extras Automaticamente",
                value=bool(
                    int(config_dict.get('horas_extras_automatico', '1')))
            )

        with col2:
            notificar_fim_jornada = st.checkbox(
                "Notificar ao Fim da Jornada",
                value=bool(
                    int(config_dict.get('notificacao_fim_jornada', '1')))
            )

        if st.form_submit_button("💾 Salvar Configurações de Horas Extras", width="stretch"):
            conn = get_connection()
            try:
                cursor = conn.cursor()

                configs_he = [
                    ('horas_extras_automatico', '1' if horas_extras_auto else '0'),
                    ('notificacao_fim_jornada', '1' if notificar_fim_jornada else '0'),
                ]

                for chave, valor in configs_he:
                    cursor.execute(f"""
                        UPDATE configuracoes 
                        SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                        WHERE chave = {SQL_PLACEHOLDER}
                    """, (valor, chave))

                conn.commit()
            finally:
                _return_conn(conn)

            st.success("✅ Configurações de horas extras salvas!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 📍 Configurações de GPS")

    with st.form("config_gps"):
        col1, col2 = st.columns(2)

        with col1:
            gps_obrigatorio = st.checkbox(
                "Exigir GPS ao Registrar Ponto",
                value=bool(int(config_dict.get('gps_obrigatorio', '0')))
            )

        with col2:
            max_distancia = st.number_input(
                "Distância Máxima Permitida (metros):",
                min_value=100,
                max_value=10000,
                value=int(config_dict.get('max_distancia_metros', '1000')),
                step=100
            )

        st.info("💡 Quando GPS obrigatório está ativado, o sistema não permitirá registro de ponto sem localização válida.")

        if st.form_submit_button("💾 Salvar Configurações de GPS", width="stretch"):
            conn = get_connection()
            try:
                cursor = conn.cursor()

                configs_gps = [
                    ('gps_obrigatorio', '1' if gps_obrigatorio else '0'),
                    ('max_distancia_metros', str(max_distancia)),
                ]

                for chave, valor in configs_gps:
                    cursor.execute(f"""
                        UPDATE configuracoes 
                        SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                        WHERE chave = {SQL_PLACEHOLDER}
                    """, (valor, chave))

                conn.commit()
            finally:
                _return_conn(conn)

            st.success("✅ Configurações de GPS salvas!")
            st.rerun()

    st.markdown("---")
    st.markdown("### 🔧 Configurações Gerais")

    with st.form("config_gerais"):
        col1, col2 = st.columns(2)

        with col1:
            backup_auto = st.checkbox(
                "Backup Automático Diário"
            )

        if st.form_submit_button("💾 Salvar Configurações Gerais", width="stretch"):
            conn = get_connection()
            try:
                cursor = conn.cursor()

                configs_gerais = [
                    ('backup_automatico', '1' if backup_auto else '0'),
                ]

                for chave, valor in configs_gerais:
                    cursor.execute(f"""
                        UPDATE configuracoes 
                        SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                        WHERE chave = {SQL_PLACEHOLDER}
                    """, (valor, chave))

                conn.commit()
            finally:
                _return_conn(conn)
            st.success("✅ Configurações salvas!")
            st.rerun()

    # Seções extraídas para funções auxiliares (legibilidade)
    _render_backup_email_section()
    _render_push_notifications_config()
    _render_auto_notifications_config()


# Rodapé unificado
st.markdown("""
<div class="footer-left">
    Sistema de ponto exclusivo da empresa Expressão Socioambiental Pesquisa e Projetos 
</div>
<div class="footer-right">
    feito por Pâmella SAR
</div>
""", unsafe_allow_html=True)


def configurar_jornada_interface():
    """Interface para gestor configurar jornada semanal dos funcionários"""
    from jornada_semanal_system import obter_jornada_usuario, salvar_jornada_semanal, NOMES_DIAS
    
    st.markdown("""
    <div class="feature-card">
        <h3>📅 Configurar Jornada Semanal</h3>
        <p>Configure horários de trabalho variáveis para cada funcionário</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        /* Estilo para campos de hora no formulário de jornada */
        .stTimeInput > div > div > input {
            width: 80px !important;
            height: 38px !important;
            font-size: 14px !important;
        }
        /* Aumenta altura do dropdown de horário */
        [data-baseweb="popover"] [data-baseweb="menu"],
        [data-baseweb="popover"] ul,
        [data-baseweb="popover"] [role="listbox"] {
            max-height: 400px !important;
            overflow-y: auto !important;
        }
        [data-baseweb="menu"] {
            max-height: 400px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### ⏰ Jornada Padrão da Empresa")

    if REFACTORING_ENABLED:
        try:
            query_configs = """
                SELECT chave, valor FROM configuracoes
                WHERE chave IN ('jornada_inicio_padrao', 'jornada_fim_padrao', 'tolerancia_atraso_minutos', 'dias_historico_padrao')
            """
            configs_jornada = execute_query(query_configs)
        except Exception as e:
            log_error("Erro ao carregar jornada padrão", e, {})
            configs_jornada = []
    else:
        conn_cfg = get_connection()
        try:
            cursor_cfg = conn_cfg.cursor()
            cursor_cfg.execute(
                """
                SELECT chave, valor FROM configuracoes
                WHERE chave IN ('jornada_inicio_padrao', 'jornada_fim_padrao', 'tolerancia_atraso_minutos', 'dias_historico_padrao')
                """
            )
            configs_jornada = cursor_cfg.fetchall()
        finally:
            _return_conn(conn_cfg)

    configs_jornada_dict = {chave: valor for chave, valor in configs_jornada}

    with st.form("config_jornada_padrao"):
        col_padrao_1, col_padrao_2 = st.columns(2)

        with col_padrao_1:
            jornada_inicio = st.time_input(
                "Horário padrão de início",
                value=datetime.strptime(configs_jornada_dict.get('jornada_inicio_padrao', '08:00'), "%H:%M").time()
            )
            tolerancia = st.number_input(
                "Tolerância de atraso (min)",
                min_value=0,
                max_value=60,
                value=int(configs_jornada_dict.get('tolerancia_atraso_minutos', '10'))
            )

        with col_padrao_2:
            jornada_fim = st.time_input(
                "Horário padrão de fim",
                value=datetime.strptime(configs_jornada_dict.get('jornada_fim_padrao', '17:00'), "%H:%M").time()
            )
            dias_historico = st.number_input(
                "Dias de histórico padrão",
                min_value=7,
                max_value=365,
                value=int(configs_jornada_dict.get('dias_historico_padrao', '30'))
            )

        if st.form_submit_button("💾 Salvar jornada padrão", width="stretch"):
            novos_valores = [
                ('jornada_inicio_padrao', jornada_inicio.strftime("%H:%M")),
                ('jornada_fim_padrao', jornada_fim.strftime("%H:%M")),
                ('tolerancia_atraso_minutos', str(tolerancia)),
                ('dias_historico_padrao', str(dias_historico)),
            ]

            try:
                if REFACTORING_ENABLED:
                    for chave, valor in novos_valores:
                        update_query = f"""
                            UPDATE configuracoes
                            SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                            WHERE chave = {SQL_PLACEHOLDER}
                        """
                        execute_update(update_query, (valor, chave))
                    log_security_event(
                        "SYSTEM_CONFIG_UPDATED",
                        usuario=st.session_state.get('usuario', 'sistema'),
                        context={"configs": [c[0] for c in novos_valores]},
                    )
                else:
                    conn_cfg_update = get_connection()
                    try:
                        cursor_cfg_update = conn_cfg_update.cursor()
                        for chave, valor in novos_valores:
                            cursor_cfg_update.execute(
                                f"""
                                    UPDATE configuracoes
                                    SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                                    WHERE chave = {SQL_PLACEHOLDER}
                                """,
                                (valor, chave),
                            )
                        conn_cfg_update.commit()
                    finally:
                        _return_conn(conn_cfg_update)

                st.success("✅ Jornada padrão atualizada!")
                st.rerun()
            except Exception as exc:
                log_error("Erro ao salvar jornada padrão", exc, {"context": "config_jornada_padrao"})
                st.error(f"❌ Não foi possível salvar: {exc}")

    st.markdown("---")
    
    # Buscar funcionários ativos
    if REFACTORING_ENABLED:
        try:
            query = """
                SELECT id, usuario, nome_completo
                FROM usuarios
                WHERE tipo = 'funcionario' AND ativo = 1
                ORDER BY nome_completo
            """
            usuarios_result = execute_query(query)
        except Exception as e:
            log_error("Erro ao buscar funcionários", e, {})
            st.error("❌ Erro ao buscar funcionários")
            return
    else:
        # Fallback original
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, usuario, nome_completo
                FROM usuarios
                WHERE tipo = 'funcionario' AND ativo = 1
                ORDER BY nome_completo
            """)
            usuarios_result = cursor.fetchall()
        finally:
            _return_conn(conn)
    
    if not usuarios_result:
        st.warning("❌ Nenhum funcionário ativo encontrado")
        return
    
    # Selectbox para escolher funcionário
    usuarios_dict = {f"{nome or usuario}" if nome else usuario: (user_id, usuario) 
                     for user_id, usuario, nome in usuarios_result}
    usuario_display = st.selectbox("👤 Selecione o funcionário:", list(usuarios_dict.keys()))
    usuario_id, usuario_username = usuarios_dict[usuario_display]
    
    # Obter jornada atual
    jornada_atual = obter_jornada_usuario(usuario_username)
    
    if not jornada_atual:
        st.error("❌ Não foi possível obter jornada do funcionário")
        return
    
    st.markdown("---")
    st.markdown("### 📋 Configuração Semanal")
    
    # Criar 2 colunas com dias úteis + fim de semana
    dias_semana_ordem = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
    
    # Mostrar tabela com resumo
    st.markdown("#### 📊 Resumo da Semana")
    
    # Preparar dados para exibir
    resumo_data = []
    for dia in dias_semana_ordem:
        dia_config = jornada_atual.get(dia, {})
        trabalha = "✅ Trabalha" if dia_config.get('trabalha', False) else "❌ Folga"
        horario = f"{dia_config.get('inicio', '--')} - {dia_config.get('fim', '--')}"
        intervalo = f"{dia_config.get('intervalo', 60)} min"
        resumo_data.append({
            "Dia": NOMES_DIAS.get(dia, dia),
            "Status": trabalha,
            "Horário": horario,
            "Intervalo": intervalo
        })
    
    # Exibir como tabela com expanders para editar cada dia
    cols = st.columns(7)
    
    for idx, dia in enumerate(dias_semana_ordem):
        with cols[idx]:
            dia_config = jornada_atual.get(dia, {})
            trabalha_emoji = "✅" if dia_config.get('trabalha', False) else "❌"
            horario_texto = f"{dia_config.get('inicio', '08:00')}-{dia_config.get('fim', '17:00')}"
            
            # Usar expander para editar
            with st.expander(f"{trabalha_emoji} {NOMES_DIAS.get(dia, dia).split('-')[0]}\n{horario_texto}"):
                # Form para editar este dia
                with st.form(f"form_jornada_{dia}_{usuario_username}"):
                    trabalha_novo = st.checkbox(
                        "Trabalha neste dia",
                        value=dia_config.get('trabalha', True),
                        key=f"trabalha_{dia}_{usuario_username}"
                    )
                    # Garantir variáveis definidas em todos os fluxos (evita UnboundLocalError)
                    hora_inicio_novo = None
                    hora_fim_nova = None
                    intervalo_novo = 0

                    if trabalha_novo:
                        # Campos de hora em layout vertical (um embaixo do outro)
                        # Compatibilidade com formatos 'HH:MM' e 'HH:MM:SS'
                        try:
                            inicio_val = dia_config.get('inicio', '08:00')
                            if isinstance(inicio_val, str) and inicio_val.count(":") == 2:
                                hora_inicio_val = datetime.strptime(inicio_val, '%H:%M:%S').time()
                            else:
                                hora_inicio_val = datetime.strptime(str(inicio_val), '%H:%M').time()
                        except Exception:
                            hora_inicio_val = datetime.strptime('08:00', '%H:%M').time()

                        hora_inicio_novo = st.time_input(
                            "Início",
                            value=hora_inicio_val,
                            key=f"inicio_{dia}_{usuario_username}"
                        )
                        
                        # Compatibilidade com formatos 'HH:MM' e 'HH:MM:SS'
                        try:
                            fim_val = dia_config.get('fim', '17:00')
                            if isinstance(fim_val, str) and fim_val.count(":") == 2:
                                hora_fim_val = datetime.strptime(fim_val, '%H:%M:%S').time()
                            else:
                                hora_fim_val = datetime.strptime(str(fim_val), '%H:%M').time()
                        except Exception:
                            hora_fim_val = datetime.strptime('17:00', '%H:%M').time()

                        hora_fim_nova = st.time_input(
                            "Fim",
                            value=hora_fim_val,
                            key=f"fim_{dia}_{usuario_username}"
                        )
                        
                        intervalo_novo = st.number_input(
                            "Intervalo (min)",
                            value=int(dia_config.get('intervalo', 60)),
                            min_value=0,
                            max_value=240,
                            step=15,
                            key=f"intervalo_{dia}_{usuario_username}"
                        )
                    # (se não trabalha_novo, as variáveis já estão inicializadas acima)

                    # Botão para salvar este dia
                    if st.form_submit_button(f"💾 Salvar {NOMES_DIAS.get(dia, dia)}", width="stretch"):
                        # Atualizar configuração
                        jornada_atual[dia] = {
                            'trabalha': trabalha_novo,
                            'inicio': hora_inicio_novo.strftime('%H:%M') if hora_inicio_novo else '08:00',
                            'fim': hora_fim_nova.strftime('%H:%M') if hora_fim_nova else '17:00',
                            'intervalo': int(intervalo_novo)
                        }
                        
                        # Salvar no banco - usar usuario_username (texto) em vez de usuario_id (número)
                        if salvar_jornada_semanal(usuario_username, jornada_atual):
                            log_security_event("SCHEDULE_UPDATED", usuario=st.session_state.usuario, context={"target_user": usuario_username, "dia": dia})
                            st.success(f"✅ {NOMES_DIAS.get(dia, dia)} atualizado!")
                            st.rerun()
                        else:
                            st.error(f"❌ Erro ao salvar {NOMES_DIAS.get(dia, dia)}")
    
    st.markdown("---")
    
    # Opção para copiar padrão
    st.markdown("#### 🔄 Atalhos")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Copiar para dias úteis (Seg-Sex)", width="stretch"):
            # Copiar config de segunda para ter um padrão
            padrao = jornada_atual.get('seg', {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60})
            for dia in ['ter', 'qua', 'qui', 'sex']:
                jornada_atual[dia] = padrao.copy()
            
            if salvar_jornada_semanal(usuario_username, jornada_atual):
                st.success("✅ Padrão copiado para dias úteis!")
                st.rerun()
            else:
                st.error("❌ Erro ao copiar padrão")
    
    with col2:
        if st.button("🏖️ Desativar fim de semana (Sab-Dom)", width="stretch"):
            for dia in ['sab', 'dom']:
                jornada_atual[dia] = {'trabalha': False, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 0}
            
            if salvar_jornada_semanal(usuario_username, jornada_atual):
                st.success("✅ Fim de semana desativado!")
                st.rerun()
            else:
                st.error("❌ Erro ao desativar fim de semana")
    
    with col3:
        if st.button("🔄 Resetar para padrão", width="stretch"):
            # Resetar para 08:00-17:00 seg-sex
            for dia in dias_semana_ordem:
                if dia in ['seg', 'ter', 'qua', 'qui', 'sex']:
                    jornada_atual[dia] = {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60}
                else:
                    jornada_atual[dia] = {'trabalha': False, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 0}
            
            if salvar_jornada_semanal(usuario_username, jornada_atual):
                st.success("✅ Jornada resetada para padrão!")
                st.rerun()
            else:
                st.error("❌ Erro ao resetar jornada")
    
    # Mostrar histórico de alterações (futura melhoria)
    st.markdown("---")
    st.info("💡 As alterações de jornada são aplicadas imediatamente. Os novos pontos respeitarão estas configurações.")


def exibir_alerta_fim_jornada_avancado():
    """
    Exibe alerta avançado 5 minutos antes do fim da jornada
    Integra com novo sistema de cálculo de jornada semanal
    """
    try:
        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
        from datetime import date
        
        # Usar novo sistema de cálculo
        verificacao = JornadaSemanalCalculoSystem.obter_tempo_ate_fim_jornada(
            st.session_state.usuario,
            date.today(),
            margem_minutos=5
        )
        
        # Se está dentro da margem de 5 minutos
        if verificacao['dentro_margem']:
            minutos_restantes = verificacao['minutos_restantes']
            horario_fim = verificacao['horario_fim']
            
            # Criar card destacado para alerta
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 20px;
                border-radius: 10px;
                margin: 10px 0;
                color: white;
                box-shadow: 0 6px 12px rgba(245, 87, 108, 0.4);
                animation: pulse 1.5s infinite;
            ">
                <h3 style="margin: 0; color: white; font-size: 20px;">⏰ FALTA POUCO PARA O FIM DA JORNADA!</h3>
                <p style="margin: 10px 0; font-size: 16px;">
                    Seu horário de saída é às <strong>{horario_fim}</strong>
                    <br>Faltam apenas <strong>{minutos_restantes} minutos</strong>
                </p>
            </div>
            <style>
                @keyframes pulse {{
                    0%, 100% {{ box-shadow: 0 6px 12px rgba(245, 87, 108, 0.4); }}
                    50% {{ box-shadow: 0 8px 20px rgba(245, 87, 108, 0.8); }}
                }}
            </style>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 1])
            ja_finalizou_hoje = False
            try:
                hoje_str = date.today().strftime("%Y-%m-%d")
                regs_hoje = buscar_registros_dia(st.session_state.usuario, hoje_str)
                ja_finalizou_hoje = any(
                    str(r.get('tipo') or '').strip().lower() in ('fim', 'saída', 'saida')
                    for r in regs_hoje
                )
            except Exception as e:
                logger.debug("Erro ao verificar fim de expediente no alerta: %s", e)

            with col1:
                if st.button("✅ Vou Finalizar", width="stretch", key="btn_vai_finalizar"):
                    st.success("Tudo bem! Trabalhe um ótimo dia 🎉")
            with col2:
                if ja_finalizou_hoje:
                    st.button("⏱️ Vou Fazer Hora Extra", disabled=True, width="stretch", key="btn_vai_fazer_he_disabled")
                else:
                    if st.button("⏱️ Vou Fazer Hora Extra", type="primary", width="stretch", key="btn_vai_fazer_he"):
                        st.session_state.solicitar_horas_extras = True
                        st.session_state.vai_fazer_hora_extra = True
                        st.rerun()
    
    except ImportError:
        # Fallback: usar sistema antigo se jornada_semanal_calculo_system não estiver disponível
        try:
            from jornada_semanal_system import verificar_horario_saida_proximo
            verificacao = verificar_horario_saida_proximo(st.session_state.usuario, margem_minutos=5)
            
            if verificacao.get('proximo'):
                minutos = verificacao.get('minutos_restantes')
                horario = verificacao.get('horario_saida')
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 20px;
                    border-radius: 10px;
                    margin: 10px 0;
                    color: white;
                ">
                    <h3 style="margin: 0;">⏰ Horário de Saída Próximo</h3>
                    <p style="margin: 10px 0;">Faltam <strong>{minutos} minutos</strong> para as {horario}</p>
                </div>
                """, unsafe_allow_html=True)
        except Exception as e:
            logger.debug(f"Erro ao exibir alerta de fim de jornada: {e}")
    except Exception as e:
        logger.debug(f"Erro geral ao exibir alerta: {e}")


def buscar_registros_dia(usuario, data):
    """Busca todos os registros de ponto de um usuário em uma data específica"""
    data_ref = safe_datetime_parse(data)
    if not data_ref:
        return []

    inicio_dia = datetime.combine(data_ref.date(), time.min)
    fim_dia = inicio_dia + timedelta(days=1)

    if REFACTORING_ENABLED:
        try:
            with safe_cursor() as cursor:
                cursor.execute(f"""
                    SELECT id, usuario, data_hora, tipo, modalidade, projeto, atividade
                    FROM registros_ponto 
                    WHERE usuario = {SQL_PLACEHOLDER}
                      AND data_hora >= {SQL_PLACEHOLDER}
                      AND data_hora < {SQL_PLACEHOLDER}
                    ORDER BY data_hora
                """, (usuario, inicio_dia, fim_dia))

                registros = []
                for row in cursor.fetchall():
                    registros.append({
                        'id': row[0],
                        'usuario': row[1],
                        'data_hora': row[2],
                        'tipo': normalizar_tipo_ponto(row[3]),
                        'modalidade': row[4],
                        'projeto': row[5],
                        'atividade': row[6]
                    })

                return registros
        except Exception as e:
            log_error("Erro ao buscar registros do dia", e, {"usuario": usuario, "data": data})
            return []
    else:
        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                SELECT id, usuario, data_hora, tipo, modalidade, projeto, atividade
                FROM registros_ponto 
                WHERE usuario = {SQL_PLACEHOLDER}
                  AND data_hora >= {SQL_PLACEHOLDER}
                  AND data_hora < {SQL_PLACEHOLDER}
                ORDER BY data_hora
            """, (usuario, inicio_dia, fim_dia))

            registros = []
            for row in cursor.fetchall():
                registros.append({
                    'id': row[0],
                    'usuario': row[1],
                    'data_hora': row[2],
                    'tipo': normalizar_tipo_ponto(row[3]),
                    'modalidade': row[4],
                    'projeto': row[5],
                    'atividade': row[6]
                })

            return registros
        finally:
            _return_conn(conn)


def corrigir_registro_ponto(registro_id, novo_tipo, nova_data_hora, nova_modalidade, novo_projeto, justificativa, gestor, correcao_id=None):
    """Corrige um registro de ponto existente"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"SELECT usuario, data_hora FROM registros_ponto WHERE id = {SQL_PLACEHOLDER}",
            (registro_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": "Registro não encontrado"}

        usuario_afetado, data_hora_antiga = row
        data_hora_antiga_dt = safe_datetime_parse(data_hora_antiga)
        if not data_hora_antiga_dt:
            return {"success": False, "message": "Data/hora original inválida no registro"}
        data_antiga = data_hora_antiga_dt.strftime("%Y-%m-%d")

        nova_data_hora_dt = safe_datetime_parse(nova_data_hora)
        if not nova_data_hora_dt:
            return {"success": False, "message": "Nova data/hora inválida"}
        data_nova = nova_data_hora_dt.strftime("%Y-%m-%d")

        valido_fluxo, mensagem_fluxo = validar_novo_registro_cursor(
            cursor,
            usuario_afetado,
            data_nova,
            novo_tipo,
            data_hora_proposta=nova_data_hora_dt,
            ignorar_registro_id=registro_id,
        )
        if not valido_fluxo:
            return {"success": False, "message": mensagem_fluxo}

        entrada_orig_ant, saida_orig_ant, _ = obter_entrada_saida_dia_cursor(cursor, usuario_afetado, data_antiga)
        entrada_orig_nova, saida_orig_nova, _ = (None, None, None)
        if data_nova != data_antiga:
            entrada_orig_nova, saida_orig_nova, _ = obter_entrada_saida_dia_cursor(cursor, usuario_afetado, data_nova)

        cursor.execute(f"""
            UPDATE registros_ponto
            SET tipo = {SQL_PLACEHOLDER}, data_hora = {SQL_PLACEHOLDER}, modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
            WHERE id = {SQL_PLACEHOLDER}
        """, (novo_tipo, nova_data_hora_dt, nova_modalidade, novo_projeto, registro_id))

        cursor.execute(f"""
            INSERT INTO auditoria_correcoes
            (registro_id, gestor, justificativa, data_correcao)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, CURRENT_TIMESTAMP)
        """, (registro_id, gestor, justificativa))

        if correcao_id:
            cursor.execute(f"""
                UPDATE solicitacoes_correcao_registro
                SET status = 'aprovado', aprovado_por = {SQL_PLACEHOLDER},
                    data_aprovacao = CURRENT_TIMESTAMP, observacoes = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
            """, (gestor, justificativa, correcao_id))

        entrada_corr_ant, saida_corr_ant, _ = obter_entrada_saida_dia_cursor(cursor, usuario_afetado, data_antiga)
        registrar_auditoria_alteracao_ponto_cursor(
            cursor,
            registro_id=registro_id,
            usuario_afetado=usuario_afetado,
            data_registro=data_antiga,
            entrada_original=entrada_orig_ant,
            saida_original=saida_orig_ant,
            entrada_corrigida=entrada_corr_ant,
            saida_corrigida=saida_corr_ant,
            tipo_alteracao="correcao_registro_manual",
            realizado_por=gestor,
            justificativa=justificativa,
            detalhes=f"Registro ID {registro_id} ajustado para tipo {novo_tipo}",
        )

        if data_nova != data_antiga:
            entrada_corr_nova, saida_corr_nova, _ = obter_entrada_saida_dia_cursor(cursor, usuario_afetado, data_nova)
            registrar_auditoria_alteracao_ponto_cursor(
                cursor,
                registro_id=registro_id,
                usuario_afetado=usuario_afetado,
                data_registro=data_nova,
                entrada_original=entrada_orig_nova,
                saida_original=saida_orig_nova,
                entrada_corrigida=entrada_corr_nova,
                saida_corrigida=saida_corr_nova,
                tipo_alteracao="correcao_registro_manual",
                realizado_por=gestor,
                justificativa=justificativa,
                detalhes=f"Registro ID {registro_id} movido para nova data",
            )

        conn.commit()
        log_security_event("RECORD_CORRECTION", usuario=gestor, context={"registro_id": registro_id, "tipo": novo_tipo})
        return {"success": True, "message": "Registro corrigido com sucesso"}
    except Exception as e:
        conn.rollback()
        log_error("Erro ao corrigir registro", e, {"registro_id": registro_id, "gestor": gestor})
        return {"success": False, "message": f"Erro ao corrigir registro: {str(e)}"}
    finally:
        _return_conn(conn)


def excluir_registro_ponto(registro_id, justificativa, gestor, correcao_id=None):
    """Exclui um registro de ponto com auditoria obrigatória."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"SELECT usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao FROM registros_ponto WHERE id = {SQL_PLACEHOLDER}",
            (registro_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "message": "Registro não encontrado"}

        usuario_afetado, data_hora, tipo, modalidade, projeto, atividade, localizacao = row
        data_hora_dt = safe_datetime_parse(data_hora)
        if not data_hora_dt:
            return {"success": False, "message": "Data/hora do registro inválida"}

        data_ref = data_hora_dt.strftime("%Y-%m-%d")
        entrada_antes, saida_antes, _ = obter_entrada_saida_dia_cursor(cursor, usuario_afetado, data_ref)

        # Preservar histórico sem violar FK: mover vínculos de auditoria_correcoes para um registro sentinela.
        cursor.execute(
            f"SELECT id FROM registros_ponto WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER} AND id <> {SQL_PLACEHOLDER} ORDER BY data_hora ASC LIMIT 1",
            (usuario_afetado, data_ref, registro_id),
        )
        sentinela = cursor.fetchone()
        sentinela_id = sentinela[0] if sentinela else None

        if sentinela_id:
            # Reatribuir auditoria_correcoes antigos para o sentinela
            cursor.execute(
                f"UPDATE auditoria_correcoes SET registro_id = {SQL_PLACEHOLDER} WHERE registro_id = {SQL_PLACEHOLDER}",
                (sentinela_id, registro_id),
            )
            # Inserir novo auditoria_correcoes referenciando sentinela (evita FK violation)
            cursor.execute(f"""
                INSERT INTO auditoria_correcoes
                (registro_id, gestor, justificativa, data_correcao)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, CURRENT_TIMESTAMP)
            """, (sentinela_id, gestor, justificativa))
        else:
            # Sem registro sentinela no dia, apagar vínculos antigos para permitir limpeza definitiva
            cursor.execute(
                f"DELETE FROM auditoria_correcoes WHERE registro_id = {SQL_PLACEHOLDER}",
                (registro_id,),
            )

        # Deletar o registro ponto DEPOIS de tratar auditoria_correcoes
        cursor.execute(f"DELETE FROM registros_ponto WHERE id = {SQL_PLACEHOLDER}", (registro_id,))

        if correcao_id:
            cursor.execute(f"""
                UPDATE solicitacoes_correcao_registro
                SET status = 'aprovado', aprovado_por = {SQL_PLACEHOLDER},
                    data_aprovacao = CURRENT_TIMESTAMP, observacoes = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
            """, (gestor, justificativa, correcao_id))

        entrada_depois, saida_depois, _ = obter_entrada_saida_dia_cursor(cursor, usuario_afetado, data_ref)
        registrar_auditoria_alteracao_ponto_cursor(
            cursor,
            registro_id=registro_id,
            usuario_afetado=usuario_afetado,
            data_registro=data_ref,
            entrada_original=entrada_antes,
            saida_original=saida_antes,
            entrada_corrigida=entrada_depois,
            saida_corrigida=saida_depois,
            tipo_alteracao="exclusao_registro_manual",
            realizado_por=gestor,
            justificativa=justificativa,
            detalhes=f"Registro excluído: tipo={tipo}; modalidade={modalidade}; projeto={projeto}; atividade={atividade}; localizacao={localizacao}",
        )

        conn.commit()
        log_security_event("RECORD_DELETION", usuario=gestor, context={"registro_id": registro_id, "usuario_afetado": usuario_afetado})
        return {"success": True, "message": "Registro excluído com sucesso"}
    except Exception as e:
        conn.rollback()
        log_error("Erro ao excluir registro", e, {"registro_id": registro_id, "gestor": gestor})
        return {"success": False, "message": f"Erro ao excluir registro: {str(e)}"}
    finally:
        _return_conn(conn)


# Função principal
@st.cache_resource
def _initialize_app_once():
    """Inicializa recursos pesados apenas uma vez (cacheado)"""
    # Inicializar banco de dados
    init_db()

    # Aplicar migrações pendentes
    try:
        from db_migrations import run_pending_migrations
        run_pending_migrations()
    except Exception as e:
        logger.warning("Não foi possível executar migrações: %s", e)
    
    # Iniciar scheduler embutido por padrão.
    # Pode ser desabilitado explicitamente com USE_EMBEDDED_SCHEDULER=false.
    if os.getenv("USE_EMBEDDED_SCHEDULER", "true").lower() == "true":
        try:
            from background_scheduler import iniciar_scheduler_background, is_scheduler_running
            if not is_scheduler_running():
                iniciar_scheduler_background()
                logger.info("✅ Scheduler embutido de notificações iniciado")
        except Exception as e:
            logger.warning(f"Scheduler embutido não iniciado: {e}")
    else:
        logger.info("ℹ️ Scheduler embutido desabilitado (USE_EMBEDDED_SCHEDULER=false)")
    
    # Inicializar sistema de uploads
    try:
        upload_system_init = UploadSystem()
        logger.info("✅ Sistema de uploads inicializado")
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de uploads: {e}")
    
    # Aplicar migration da tabela uploads
    try:
        from apply_uploads_migration import apply_uploads_migration
        apply_uploads_migration()
    except Exception as e:
        logger.warning(f"Não foi possível aplicar migration de uploads: {e}")
    
    return True


def exibir_modal_push_obrigatorio():
    """Exibe modal obrigatório para ativar notificações push após login"""
    # Verificar se push está configurado
    vapid_key = os.getenv('VAPID_PUBLIC_KEY', '')
    if not vapid_key:
        return  # Push não configurado, não exibir modal
    
    # Verificar se já mostrou o modal nesta sessão
    if st.session_state.get('push_modal_shown', False):
        return
    
    # Verificar se notificações globais estão habilitadas (configuração do gestor)
    push_obrigatorio = True  # Padrão: obrigatório
    try:
        if REFACTORING_ENABLED:
            result = execute_query(
                "SELECT valor FROM configuracoes WHERE chave = 'push_notifications_obrigatorio'",
                fetch_one=True
            )
            if result:
                push_obrigatorio = result[0] == '1'
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT valor FROM configuracoes WHERE chave = 'push_notifications_obrigatorio'")
                result = cursor.fetchone()
                if result:
                    push_obrigatorio = result[0] == '1'
            finally:
                _return_conn(conn)
    except Exception as e:
        logger.debug("Erro silenciado: %s", e)  # Se erro, manter padrão (obrigatório)
    
    if not push_obrigatorio:
        return  # Gestor desabilitou notificações obrigatórias
    
    # JavaScript para exibir modal de ativação de push
    usuario = st.session_state.usuario
    st.components.v1.html(f"""
    <script>
    (function() {{
        // Aguardar push system carregar
        function checkAndShowModal() {{
            if (typeof PontoESA === 'undefined' || !PontoESA.Push) {{
                setTimeout(checkAndShowModal, 500);
                return;
            }}
            
            const state = PontoESA.Push.getState();
            
            // Se já está inscrito ou não suporta, não mostrar modal
            if (state.isSubscribed || !state.isSupported) {{
                return;
            }}
            
            // Verificar se já dispensou o modal hoje
            const dismissedDate = localStorage.getItem('push_modal_dismissed_date');
            const today = new Date().toDateString();
            if (dismissedDate === today) {{
                return;
            }}
            
            // Verificar permissão
            if (Notification.permission === 'denied') {{
                return;
            }}
            
            // Mostrar modal após 2 segundos
            setTimeout(function() {{
                showPushModal();
            }}, 2000);
        }}
        
        function showPushModal() {{
            // Verificar se modal já existe
            if (document.getElementById('push-modal-obrigatorio')) return;
            
            const modal = document.createElement('div');
            modal.id = 'push-modal-obrigatorio';
            modal.innerHTML = `
                <div style="
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.7);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 999999;
                    animation: fadeIn 0.3s ease;
                ">
                    <div style="
                        background: white;
                        border-radius: 20px;
                        padding: 35px;
                        max-width: 420px;
                        text-align: center;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.4);
                        animation: slideUp 0.4s ease;
                    ">
                        <div style="font-size: 60px; margin-bottom: 15px;">🔔</div>
                        <h2 style="margin: 0 0 10px; color: #333; font-size: 22px;">Ative as Notificações!</h2>
                        <p style="color: #666; margin-bottom: 20px; font-size: 15px; line-height: 1.5;">
                            Para garantir que você <strong>nunca esqueça</strong> de registrar seu ponto, 
                            ative as notificações e receba lembretes automáticos.
                        </p>
                        <p style="color: #888; margin-bottom: 25px; font-size: 13px;">
                            📱 Você receberá alertas de entrada, saída e hora extra.
                        </p>
                        <div style="display: flex; flex-direction: column; gap: 10px;">
                            <button id="push-modal-yes" style="
                                background: linear-gradient(135deg, #4CAF50, #45a049);
                                color: white;
                                border: none;
                                padding: 14px 28px;
                                border-radius: 10px;
                                font-size: 16px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: transform 0.2s;
                            " onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                                ✅ Ativar Notificações
                            </button>
                            <button id="push-modal-later" style="
                                background: transparent;
                                color: #999;
                                border: none;
                                padding: 10px;
                                font-size: 13px;
                                cursor: pointer;
                            ">
                                Lembrar mais tarde
                            </button>
                        </div>
                    </div>
                </div>
                <style>
                    @keyframes fadeIn {{
                        from {{ opacity: 0; }}
                        to {{ opacity: 1; }}
                    }}
                    @keyframes slideUp {{
                        from {{ opacity: 0; transform: translateY(30px) scale(0.95); }}
                        to {{ opacity: 1; transform: translateY(0) scale(1); }}
                    }}
                </style>
            `;
            
            document.body.appendChild(modal);
            
            // Botão Ativar
            document.getElementById('push-modal-yes').onclick = async function() {{
                const btn = this;
                btn.disabled = true;
                btn.innerHTML = '⏳ Ativando...';
                
                try {{
                    const result = await PontoESA.Push.init('{usuario}');
                    
                    if (result.success) {{
                        btn.innerHTML = '✅ Ativado!';
                        btn.style.background = '#9E9E9E';
                        setTimeout(function() {{
                            modal.remove();
                        }}, 1500);
                    }} else {{
                        btn.innerHTML = '❌ ' + (result.error || 'Erro');
                        btn.disabled = false;
                        setTimeout(function() {{
                            btn.innerHTML = '✅ Ativar Notificações';
                        }}, 3000);
                    }}
                }} catch (e) {{
                    btn.innerHTML = '❌ ' + e.message;
                    btn.disabled = false;
                }}
            }};
            
            // Botão Lembrar mais tarde
            document.getElementById('push-modal-later').onclick = function() {{
                // Salvar que dispensou hoje
                localStorage.setItem('push_modal_dismissed_date', new Date().toDateString());
                modal.remove();
            }};
        }}
        
        // Iniciar verificação
        checkAndShowModal();
    }})();
    </script>
    """, height=0)
    
    # Marcar que já mostrou nesta sessão
    st.session_state.push_modal_shown = True


def main():
    """Função principal que gerencia o estado da aplicação.

    Protegida por try/except global para que nenhuma exceção não
    tratada derrube o processo Streamlit.
    """
    try:
        # Inicializar recursos pesados apenas uma vez
        _initialize_app_once()

        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False

        if st.session_state.logged_in:
            # Exibir modal de ativação de push notifications (obrigatório após login)
            exibir_modal_push_obrigatorio()

            if st.session_state.tipo_usuario == 'funcionario':
                tela_funcionario()
            elif st.session_state.tipo_usuario == 'gestor':
                tela_gestor()
            else:
                st.error(
                    "Tipo de usuário desconhecido. Por favor, faça login novamente.")
                st.session_state.logged_in = False
                st.rerun()
        else:
            tela_login()
    except Exception as e:
        logger.critical("Erro não tratado na aplicação: %s", e, exc_info=True)
        st.error(
            "Ocorreu um erro inesperado. Por favor, recarregue a página. "
            "Se o problema persistir, entre em contato com o suporte."
        )

    # Rodapé unificado
    st.markdown("""
    <div class="footer-left">
        Sistema de ponto exclusivo da empresa Expressão Socioambiental Pesquisa e Projetos 
    </div>
    <div class="footer-right">
        feito por Pâmella SAR
    </div>
    """, unsafe_allow_html=True)


# Executar aplicação
if __name__ == "__main__":
    main()
