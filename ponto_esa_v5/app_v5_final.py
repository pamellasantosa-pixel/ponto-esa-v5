"""
Ponto ExSA v5.0 - Sistema de Controle de Ponto
Versão com Horas Extras, Banco de Horas, GPS Real e Melhorias  
Desenvolvido por Pâmella SAR para Expressão Socioambiental Pesquisa e Projetos
Última atualização: 24/10/2025 16:45 - TIMEZONE BRASÍLIA CORRIGIDO (get_datetime_br)
Deploy: Render.com | Banco: PostgreSQL
"""

from notifications import notification_manager
from calculo_horas_system import CalculoHorasSystem
from banco_horas_system import BancoHorasSystem, format_saldo_display
from horas_extras_system import HorasExtrasSystem
from upload_system import UploadSystem, format_file_size, get_file_icon, is_image_file, get_category_name
from streamlit_utils import safe_download_button
from atestado_horas_system import AtestadoHorasSystem, format_time_duration, get_status_color, get_status_emoji
from ajuste_registros_system import AjusteRegistrosSystem
from timer_integration_functions import (
    exibir_button_solicitar_hora_extra,
    exibir_modal_timer_hora_extra,
    exibir_dialog_justificativa_hora_extra,
    exibir_popup_continuar_hora_extra,
    exibir_notificacoes_hora_extra_pendente,
)

# Importar novos módulos de refatoração
try:
    from connection_manager import execute_query, execute_update, safe_cursor, safe_database_connection
    from error_handler import log_error, get_logger, log_security_event
    REFACTORING_ENABLED = True
except ImportError:
    REFACTORING_ENABLED = False
    print("[AVISO] Modulos de refatoracao nao disponíveis. Usando get_connection() tradicional.")

import streamlit as st
import os
import hashlib
from datetime import datetime, timedelta, date, time
import pandas as pd
import base64
import json
import uuid
from io import BytesIO
import sys
from dotenv import load_dotenv
import pytz  # Para gerenciar fusos horários
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente
load_dotenv()

# Verificar se usa PostgreSQL
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'

if USE_POSTGRESQL:
    import psycopg2
    from database_postgresql import get_connection, init_db
    # PostgreSQL usa %s como placeholder
    SQL_PLACEHOLDER = '%s'
    get_db_connection = get_connection
else:
    import sqlite3
    from database import init_db, get_connection
    # SQLite usa ? como placeholder
    SQL_PLACEHOLDER = '?'
    get_db_connection = get_connection

# Adicionar ao namespace global para que outros módulos possam acessar
import sys
current_module = sys.modules[__name__]
current_module.SQL_PLACEHOLDER = SQL_PLACEHOLDER

# Adicionar o diretório atual ao path para permitir importações
if os.path.dirname(__file__) not in sys.path:
    sys.path.insert(0, os.path.dirname(__file__))

# Configurar timezone do Brasil (Brasília)
TIMEZONE_BR = pytz.timezone('America/Sao_Paulo')


def get_datetime_br():
    """Retorna datetime atual no fuso horário de Brasília"""
    return datetime.now(TIMEZONE_BR)

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
        # Fallback: agora (evita quebra na UI)
        return datetime.now()

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
            except Exception:
                pass
    return default


# Importar sistemas desenvolvidos

# Configuração da página
st.set_page_config(
    page_title="Ponto ExSA v5.0",
    page_icon="⏰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado com novo layout
st.markdown("""
<style>
    /* Importar fonte */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e configurações gerais */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #87CEEB 0%, #4682B4 100%);
        min-height: 100vh;
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
</style>

<script>
function updateClock() {
    const now = new Date();
    const dateStr = now.toLocaleDateString('pt-BR');
    const timeStr = now.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
    const elements = document.querySelectorAll('.user-info');
    elements.forEach(el => {
        if (el.textContent.includes('•')) {
            const parts = el.textContent.split(' • ');
            if (parts.length === 2) {
                el.textContent = parts[0] + ' • ' + dateStr + ' ' + timeStr;
            }
        }
    });
}
// Atualizar a cada minuto
setInterval(updateClock, 60000);
// Atualizar imediatamente
updateClock();
</script>
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
                            ❌ Erro ao obter localização: ${error.message}
                        </div>
                    `;
                }
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

// Função para obter coordenadas do sessionStorage
function getStoredGPS() {
    const lat = sessionStorage.getItem('gps_lat');
    const lng = sessionStorage.getItem('gps_lng');
    const timestamp = sessionStorage.getItem('gps_timestamp');
    
    // Verificar se os dados são recentes (menos de 5 minutos)
                longitude: parseFloat(lng),
                timestamp: parseInt(timestamp)
            };
        }
    }
    return null;
}
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

# Funções de banco de dados


def verificar_login(usuario, senha):
    """Verifica credenciais de login"""
    if REFACTORING_ENABLED:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        result = execute_query(
            "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s",
            (usuario, senha_hash),
            fetch_one=True
        )
        if result:
            log_security_event("LOGIN", usuario=usuario, severity="INFO")
        return result
    else:
        conn = get_connection()
        cursor = conn.cursor()
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        cursor.execute(
            "SELECT tipo, nome_completo FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha_hash))
        result = cursor.fetchone()
        conn.close()
        return result


def obter_projetos_ativos():
    """Obtém lista de projetos ativos"""
    if REFACTORING_ENABLED:
        results = execute_query(
            "SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome"
        )
        return [row[0] for row in results] if results else []
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nome FROM projetos WHERE ativo = 1 ORDER BY nome")
        projetos = [row[0] for row in cursor.fetchall()]
        conn.close()
        return projetos


def registrar_ponto(usuario, tipo, modalidade, projeto, atividade, data_registro=None, hora_registro=None, latitude=None, longitude=None):
    """Registra ponto do usuário com GPS real"""
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
    if latitude and longitude:
        localizacao = f"GPS: {latitude:.6f}, {longitude:.6f}"
    else:
        localizacao = "GPS não disponível"

    # Usar placeholder correto baseado no tipo de banco
    placeholders = ', '.join([SQL_PLACEHOLDER] * 9)
    
    if REFACTORING_ENABLED:
        success = execute_update(
            f'''
                INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
                VALUES ({placeholders})
            ''',
            (usuario, data_hora_registro, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
        )
        if success:
            return data_hora_registro
        else:
            log_error("Erro ao registrar ponto", context={"usuario": usuario, "tipo": tipo})
            return None
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            INSERT INTO registros_ponto (usuario, data_hora, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude)
            VALUES ({placeholders})
        ''', (usuario, data_hora_registro, tipo, modalidade, projeto, atividade, localizacao, latitude, longitude))
        conn.commit()
        conn.close()
        return data_hora_registro


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
        cursor = conn.cursor()
        cursor.execute(query, params)
        registros = cursor.fetchall()
        conn.close()
        return registros


def obter_usuarios_para_aprovacao():
    """Obtém lista de usuários que podem aprovar horas extras"""
    if REFACTORING_ENABLED:
        usuarios = execute_query(
            "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo"
        )
        return [{"usuario": u[0], "nome": u[1] or u[0]} for u in usuarios] if usuarios else []
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo")
        usuarios = cursor.fetchall()
        conn.close()
        return [{"usuario": u[0], "nome": u[1] or u[0]} for u in usuarios]


def obter_usuarios_ativos():
    """Obtém lista de usuários ativos (retorna dicionários com 'usuario' e 'nome_completo')."""
    if REFACTORING_ENABLED:
        rows = execute_query(
            "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo"
        )
        return [{"usuario": r[0], "nome_completo": r[1] or r[0]} for r in rows] if rows else []
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT usuario, nome_completo FROM usuarios WHERE ativo = 1 ORDER BY nome_completo")
        rows = cursor.fetchall()
        conn.close()
        return [{"usuario": r[0], "nome_completo": r[1] or r[0]} for r in rows]

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
                "ENTRAR", use_container_width=True)

            if submitted:
                if usuario and senha:
                    resultado = verificar_login(usuario, senha)
                    if resultado:
                        st.session_state.usuario = usuario
                        st.session_state.tipo_usuario = resultado[0]
                        st.session_state.nome_completo = resultado[1]
                        st.session_state.logged_in = True
                        st.success("✅ Login realizado com sucesso!")
                        st.rerun()
                    else:
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
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        agora = get_datetime_br()
        hoje = agora.date()
        
        # Início da semana (segunda-feira)
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        
        # Horas extras hoje
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
        horas_hoje_total = horas_hoje_ativas + horas_hoje_historico
        
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
    finally:
        if conn:
            conn.close()


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
                use_container_width=True, 
                type="primary"
            )
        with col2:
            cancelar = st.form_submit_button(
                "❌ Cancelar", 
                use_container_width=True
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
                            """, (
                                st.session_state.usuario,
                                aprovador,
                                justificativa,
                                agora_sem_tz.strftime('%Y-%m-%d %H:%M:%S'),
                                agora_sem_tz.strftime('%H:%M')
                            ))
                            
                            # Obter ID da hora extra criada
                            cursor.execute("SELECT last_insert_rowid()")
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
                            conn.close()


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
            
            # Se há hora extra ativa, ativar auto-refresh de 30 segundos
            try:
                from streamlit_autorefresh import st_autorefresh
                st_autorefresh(interval=30000, key="hora_extra_counter")
            except ImportError:
                # Biblioteca não instalada - continuar sem auto-refresh
                pass
            
            he_id, aprovador, justificativa, data_inicio, status = hora_extra
            
            # Calcular tempo decorrido
            from calculo_horas_system import safe_datetime_parse
            inicio = safe_datetime_parse(data_inicio)
            agora = datetime.now()
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
                    if st.button("🛑 Encerrar Hora Extra", type="primary", use_container_width=True, key="btn_encerrar_he"):
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
            
            # Se há hora extra ativa, ativar auto-refresh de 30 segundos
            try:
                from streamlit_autorefresh import st_autorefresh
                st_autorefresh(interval=30000, key="hora_extra_counter")
            except ImportError:
                # Biblioteca não instalada - continuar sem auto-refresh
                pass
            
            he_id, aprovador, justificativa, data_inicio, status = hora_extra
            
            # Calcular tempo decorrido
            from calculo_horas_system import safe_datetime_parse
            inicio = safe_datetime_parse(data_inicio)
            agora = datetime.now()
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
                    if st.button("🛑 Encerrar Hora Extra", type="primary", use_container_width=True, key="btn_encerrar_he"):
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
                            conn_encerrar.close()
                
                with col2:
                    st.info("💡 Clique em 'Encerrar' quando finalizar o trabalho para registrar o total de horas extras")
        
        except Exception as e:
            logger.error(f"Erro em exibir_hora_extra_em_andamento: {str(e)}")
        finally:
            if conn:
                conn.close()


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
                
                if st.button("↩️ Voltar ao Menu", use_container_width=True):
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
                    if st.button("✅ Aprovar", key=f"aprovar_{he_id}", type="primary", use_container_width=True):
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
                    if st.button("❌ Rejeitar", key=f"rejeitar_{he_id}", use_container_width=True):
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
            if st.button("↩️ Voltar ao Menu", use_container_width=True):
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
                
                if st.button("↩️ Voltar ao Menu", use_container_width=True):
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
                    if st.button("✅ Aprovar", key=f"aprovar_{he_id}", type="primary", use_container_width=True):
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
                    if st.button("❌ Rejeitar", key=f"rejeitar_{he_id}", use_container_width=True):
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
            if st.button("↩️ Voltar ao Menu", use_container_width=True):
                if 'aprovar_hora_extra' in st.session_state:
                    del st.session_state.aprovar_hora_extra
                st.rerun()
        
        except Exception as e:
            st.error(f"❌ Erro ao buscar solicitações: {str(e)}")
            logger.error(f"Erro em aprovar_hora_extra_rapida_interface: {str(e)}")
        finally:
            if conn:
                conn.close()


def exibir_widget_notificacoes(horas_extras_system):
    """Exibe widget fixo de notificações pendentes até serem respondidas"""
    try:
        # Buscar todas as notificações pendentes
        conn = get_connection()
        cursor = conn.cursor()
        
        # Solicitações de horas extras pendentes (para aprovar)
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        he_pendentes = cursor.fetchone()[0]
        
        # Solicitações de correção de registro pendentes (enviadas pelo usuário)
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_correcao_registro 
            WHERE usuario = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        correcoes_pendentes = cursor.fetchone()[0]
        
        # Atestados de horas pendentes (enviados pelo usuário)
        cursor.execute("""
            SELECT COUNT(*) FROM atestado_horas 
            WHERE usuario = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        atestados_pendentes = cursor.fetchone()[0]
        
        conn.close()
        
        total_notificacoes = he_pendentes + correcoes_pendentes + atestados_pendentes
        
        if total_notificacoes > 0:
            # Criar container de notificações fixo
            st.markdown("""
            <style>
            .notification-widget {
                background: linear-gradient(135deg, #FFA500 0%, #FF6347 100%);
                padding: 15px 20px;
                border-radius: 10px;
                margin: 15px 0;
                box-shadow: 0 4px 12px rgba(255, 99, 71, 0.3);
                border-left: 5px solid #FF4500;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.02); }
            }
            
            .notification-badge {
                background: white;
                color: #FF4500;
                padding: 5px 12px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 16px;
                display: inline-block;
                margin-left: 10px;
            }
            
            .notification-item {
                background: rgba(255, 255, 255, 0.2);
                padding: 8px 12px;
                border-radius: 5px;
                margin: 5px 0;
                color: white;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="notification-widget">
                <h3 style="margin: 0; color: white; display: inline-block;">
                    🔔 Notificações Pendentes
                    <span class="notification-badge">{total_notificacoes}</span>
                </h3>
                <p style="margin: 10px 0 5px 0; color: white; font-size: 14px;">
                    Você tem ações aguardando resposta:
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Mostrar detalhes em colunas
            cols = st.columns(3)
            
            if he_pendentes > 0:
                with cols[0]:
                    if st.button(f"🕐 {he_pendentes} Hora(s) Extra para Aprovar", 
                                use_container_width=True, 
                                type="primary",
                                key="notif_he"):
                        st.session_state.ir_para_notificacoes = True
                        st.rerun()
            
            if correcoes_pendentes > 0:
                with cols[1]:
                    if st.button(f"🔧 {correcoes_pendentes} Correção(ões) Pendente(s)", 
                                use_container_width=True,
                                type="secondary",
                                key="notif_correcao"):
                        st.session_state.ir_para_correcoes = True
                        st.rerun()
            
            if atestados_pendentes > 0:
                with cols[2]:
                    if st.button(f"⏰ {atestados_pendentes} Atestado(s) Pendente(s)", 
                                use_container_width=True,
                                type="secondary",
                                key="notif_atestado"):
                        st.session_state.ir_para_atestados = True
                        st.rerun()
            
            st.markdown("---")
    
    except Exception as e:
        logger.error(f"Erro ao exibir widget de notificações: {e}")


# Interface principal do funcionário
def tela_funcionario():
    """Interface principal para funcionários"""
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

        # Contar todas as notificações pendentes
        conn = get_connection()
        cursor = conn.cursor()
        
        # Horas extras para aprovar
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        he_aprovar = cursor.fetchone()[0]
        
        # Solicitações de correção do usuário
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_correcao_registro 
            WHERE usuario = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        correcoes_pendentes = cursor.fetchone()[0]
        
        # Atestados pendentes
        cursor.execute("""
            SELECT COUNT(*) FROM atestado_horas 
            WHERE usuario = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        atestados_pendentes = cursor.fetchone()[0]
        
        conn.close()
        
        total_notif = he_aprovar + correcoes_pendentes + atestados_pendentes

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
            "📊 Relatórios de Horas Extras",
            "🏦 Meu Banco de Horas",
            "📁 Meus Arquivos",
            f"🔔 Notificações{f' 🔴{total_notif}' if total_notif > 0 else ''}"
        ]

        opcao = st.selectbox("Escolha uma opção:", opcoes_menu)

        if st.button("🚪 Sair", use_container_width=True):
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
    elif opcao == "📊 Relatórios de Horas Extras":
        from relatorios_horas_extras import relatorios_horas_extras_interface
        relatorios_horas_extras_interface()
    elif opcao == "🏦 Meu Banco de Horas":
        banco_horas_funcionario_interface(banco_horas_system)
    elif opcao == "📁 Meus Arquivos":
        meus_arquivos_interface(upload_system)
    elif opcao.startswith("🔔 Notificações"):
        notificacoes_interface(horas_extras_system)


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

    # Inserir script GPS
    st.components.v1.html(GPS_SCRIPT, height=0)

    # Status do GPS
    st.markdown('<div id="gps-status">📍 Obtendo localização...</div>',
                unsafe_allow_html=True)

    st.subheader("➕ Novo Registro")

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

        atividade = st.text_area(
            "📝 Descrição da Atividade",
            placeholder="Descreva brevemente a atividade realizada..."
        )
        
        # Alerta visual para domingo ou feriado
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

        # Validação de registros
        data_str = data_registro.strftime("%Y-%m-%d")
        pode_registrar = calculo_horas_system.pode_registrar_tipo(
            st.session_state.usuario, data_str, tipo_registro)

        if tipo_registro in ["Início", "Fim"] and not pode_registrar:
            st.warning(
                f"⚠️ Você já possui um registro de '{tipo_registro}' para este dia.")

        submitted = st.form_submit_button(
            "✅ Registrar Ponto", use_container_width=True)

        if submitted:
            if not atividade.strip():
                st.error("❌ A descrição da atividade é obrigatória")
            elif tipo_registro in ["Início", "Fim"] and not pode_registrar:
                st.error(f"❌ Registro de '{tipo_registro}' já realizado para este dia.")
            else:
                # Coordenadas GPS (simplificado - GPS desabilitado temporariamente)
                latitude = None
                longitude = None

                # Registrar ponto com horário atual
                data_hora_registro = registrar_ponto(
                    st.session_state.usuario,
                    tipo_registro,
                    modalidade,
                    projeto,
                    atividade,
                    data_registro.strftime("%Y-%m-%d"),
                    None,  # Não passar horário - usar atual
                    latitude,
                    longitude
                )

                st.success(f"✅ Ponto registrado com sucesso!")
                st.info(
                    f"🕐 {data_hora_registro.strftime('%d/%m/%Y às %H:%M')}")

                # ✨ NOVO: Integração com sistema de jornada e hora extra
                if tipo_registro == "Fim":
                    try:
                        from jornada_semanal_calculo_system import JornadaSemanalCalculoSystem
                        
                        # 🔧 CORREÇÃO: Obter tolerância configurada pelo gestor
                        tolerancia_minutos = 5  # padrão
                        try:
                            cursor = get_db_connection().cursor()
                            cursor.execute(
                                "SELECT valor FROM configuracoes WHERE chave = 'tolerancia_atraso_minutos'"
                            )
                            resultado = cursor.fetchone()
                            if resultado:
                                tolerancia_minutos = int(resultado[0])
                            cursor.close()
                        except Exception as e:
                            logger.warning(f"Não foi possível obter tolerância do gestor: {e}")
                        
                        # Detectar hora extra COM a tolerância correta
                        resultado_hora_extra = JornadaSemanalCalculoSystem.detectar_hora_extra_dia(
                            st.session_state.usuario,
                            data_registro,
                            tolerancia_minutos=tolerancia_minutos
                        )
                        
                        if resultado_hora_extra.get('tem_hora_extra', False):
                            horas_extra = resultado_hora_extra.get('horas_extra', 0)
                            minutos_extra = resultado_hora_extra.get('minutos_extra', 0)
                            
                            # Mostrar resultado
                            st.success(f"""
                            ⏱️ **HORA EXTRA DETECTADA!**
                            
                            Você trabalhou:
                            - **{horas_extra:.1f} horas** ({minutos_extra} minutos) de hora extra
                            - Esperado: {resultado_hora_extra.get('esperado_minutos', 0)} min
                            - Registrado: {resultado_hora_extra.get('registrado_minutos', 0)} min
                            """)
                            
                            # Sugerir solicitar aprovação
                            if st.button("📝 Solicitar Aprovação de Hora Extra"):
                                # Preparar dados para solicitar
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
                            # ✅ Expediente finalizado com sucesso dentro da jornada
                            st.success(f"""
                            ✅ **EXPEDIENTE FINALIZADO COM SUCESSO!**
                            
                            - Esperado: {resultado_hora_extra.get('esperado_minutos', 0)} min
                            - Registrado: {resultado_hora_extra.get('registrado_minutos', 0)} min
                            - Status: Dentro da jornada (tolerância: {tolerancia_minutos} min)
                            
                            Bom descanso! 😊
                            """)
                    
                    except ImportError:
                        # Se sistema de jornada não estiver disponível, usar método antigo
                        if horas_extras_system is not None:
                            try:
                                verificacao = horas_extras_system.verificar_fim_jornada(
                                    st.session_state.usuario)
                                if isinstance(verificacao, dict) and verificacao.get("deve_notificar"):
                                    st.info(f"💡 {verificacao.get('message')}")
                            except Exception:
                                st.info("💡 Não foi possível verificar horas extras no momento.")
                    except Exception as e:
                        logger.error(f"Erro ao detectar hora extra: {e}")
                        # Fallback para método antigo
                        if horas_extras_system is not None:
                            try:
                                verificacao = horas_extras_system.verificar_fim_jornada(
                                    st.session_state.usuario)
                                if isinstance(verificacao, dict) and verificacao.get("deve_notificar"):
                                    st.info(f"💡 {verificacao.get('message')}")
                            except Exception:
                                st.info("💡 Não foi possível verificar horas extras no momento.")

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
        df_dia['Hora'] = pd.to_datetime(
            df_dia['Data/Hora']).dt.strftime('%H:%M')
        st.dataframe(
            df_dia[['Hora', 'Tipo', 'Modalidade',
                    'Projeto', 'Atividade', 'Localização']],
            use_container_width=True
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
                conn.close()
    
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
    if st.button("↩️ Voltar ao Menu", use_container_width=True):
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
    if st.button("📊 Ver Histórico Completo", use_container_width=True, type="secondary"):
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
                "✅ Enviar Solicitação", use_container_width=True)

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
                            f"**Solicitado em:** {safe_datetime_parse(solicitacao['data_solicitacao']).strftime('%d/%m/%Y às %H:%M')}")
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
            use_container_width=True
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

    conn = get_connection()
    cursor = conn.cursor()
    
    # Contar notificações
    cursor.execute("""
        SELECT COUNT(*) FROM solicitacoes_horas_extras 
        WHERE aprovador_solicitado = %s AND status = 'pendente'
    """, (st.session_state.usuario,))
    he_aprovar = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM solicitacoes_correcao_registro 
        WHERE usuario = %s AND status = 'pendente'
    """, (st.session_state.usuario,))
    correcoes_pendentes = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM atestado_horas 
        WHERE usuario = %s AND status = 'pendente'
    """, (st.session_state.usuario,))
    atestados_pendentes = cursor.fetchone()[0]
    
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
                        ds_fmt = safe_datetime_parse(solicitacao['data_solicitacao']).strftime('%d/%m/%Y às %H:%M')
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
        st.subheader("� Minhas Solicitações de Correção Pendentes")
        
        cursor.execute("""
            SELECT id, registro_id, data_hora_original, data_hora_nova,
                   tipo_original, tipo_novo, justificativa, 
                   data_solicitacao
            FROM solicitacoes_correcao_registro
            WHERE usuario = %s AND status = 'pendente'
            ORDER BY data_solicitacao DESC
        """, (st.session_state.usuario,))
        
        correcoes = cursor.fetchall()
        
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
                        st.write(f"- Nova Data/Hora: {data_nova}")
                        st.write(f"- Novo Tipo: {tipo_novo}")
                    
                    st.write(f"**Justificativa:** {just}")
                    st.write(f"**Solicitado em:** {data_sol}")
                    st.info("⏳ Aguardando aprovação do gestor...")
        else:
            st.info("✅ Nenhuma correção aguardando aprovação")
    
    # Tab 3: Atestados Pendentes
    with tabs[2]:
        st.subheader("⏰ Meus Atestados de Horas Pendentes")
        
        cursor.execute("""
            SELECT id, data, hora_inicio, hora_fim, total_horas, motivo, 
                   arquivo_comprovante, data_registro
            FROM atestado_horas
            WHERE usuario = %s AND status = 'pendente'
            ORDER BY data_registro DESC
        """, (st.session_state.usuario,))
        
        atestados = cursor.fetchall()
        
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
    
    conn.close()

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
            "✅ Registrar Ausência", use_container_width=True)

    if submitted:
        if not motivo.strip():
            st.error("❌ O motivo é obrigatório")
        elif data_inicio > data_fim:
            st.error(
                "❌ Data de início deve ser anterior ou igual à data de fim")
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
            conn = get_connection()
            cursor = conn.cursor()

            try:
                cursor.execute("""
                    INSERT INTO ausencias 
                    (usuario, data_inicio, data_fim, tipo, motivo, arquivo_comprovante, nao_possui_comprovante)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                st.success("✅ Ausência registrada com sucesso!")

                if nao_possui_comprovante:
                    st.info(
                        "💡 Lembre-se de apresentar o comprovante assim que possível para regularizar sua situação.")

                st.rerun()

            except Exception as e:
                st.error(f"❌ Erro ao registrar ausência: {str(e)}")
            finally:
                conn.close()


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
                    "✅ Registrar Atestado", use_container_width=True)

            if submitted:
                if not motivo.strip():
                    st.error("❌ O motivo é obrigatório")
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
                st.session_state.usuario,
                data_inicio.strftime("%Y-%m-%d"),
                data_fim.strftime("%Y-%m-%d")
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

        # Selecionar data
        data_corrigir = st.date_input(
            "📅 Data do Registro a Corrigir",
            value=date.today(),
            max_value=date.today()
        )

        # Buscar registros do usuário nessa data
        registros = buscar_registros_dia(
            st.session_state.usuario, 
            data_corrigir.strftime("%Y-%m-%d")
        )

        if registros:
            registro_opcoes = [
                f"{r['data_hora']} - {r['tipo']}" for r in registros
            ]
            
            registro_selecionado = st.selectbox(
                "⏰ Selecione o Registro",
                registro_opcoes
            )
            
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
                    # Converter data_hora para datetime se for string
                    if isinstance(registro['data_hora'], str):
                        data_hora_obj = datetime.strptime(registro['data_hora'], "%Y-%m-%d %H:%M:%S")
                    else:
                        data_hora_obj = registro['data_hora']
                    
                    nova_data = st.date_input(
                        "📅 Nova Data",
                        value=data_hora_obj.date()
                    )
                    
                    # Campo de texto livre para hora e minuto
                    nova_hora_input = st.text_input(
                        "🕐 Nova Hora (HH:MM)",
                        value=data_hora_obj.strftime("%H:%M"),
                        help="Digite no formato HH:MM (ex: 08:30, 14:45)"
                    )
                    
                    # Mapear tipos do banco para as opções do selectbox
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
                    
                    novo_tipo = st.selectbox(
                        "📋 Novo Tipo",
                        tipos_opcoes,
                        index=tipos_opcoes.index(tipo_atual)
                    )

                with col2:
                    # Mapear modalidades do banco para as opções
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

                submitted = st.form_submit_button(
                    "✅ Enviar Solicitação", 
                    use_container_width=True
                )

                if submitted:
                    if not justificativa.strip():
                        st.error("❌ A justificativa é obrigatória")
                    else:
                        # Validar formato de hora
                        try:
                            hora_valida = datetime.strptime(nova_hora_input, "%H:%M").time()
                            nova_data_hora = f"{nova_data.strftime('%Y-%m-%d')} {nova_hora_input}:00"
                            
                            # Salvar solicitação no banco
                            conn = get_connection()
                            cursor = conn.cursor()
                            
                            cursor.execute("""
                                INSERT INTO solicitacoes_correcao_registro
                                (usuario, registro_id, data_hora_original, data_hora_nova, 
                                 tipo_original, tipo_novo, modalidade_original, modalidade_nova,
                                 projeto_original, projeto_novo, justificativa, status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pendente')
                            """, (
                                st.session_state.usuario,
                                registro['id'],
                                registro['data_hora'],
                                nova_data_hora,
                                registro['tipo'],
                                novo_tipo,
                                registro['modalidade'],
                                nova_modalidade if nova_modalidade else None,
                                registro['projeto'],
                                novo_projeto if novo_projeto else None,
                                justificativa
                            ))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success("✅ Solicitação enviada com sucesso! Aguarde aprovação do gestor.")
                            st.rerun()
                            
                        except ValueError:
                            st.error("❌ Formato de hora inválido. Use HH:MM (ex: 08:30)")
        else:
            st.info(f"📋 Nenhum registro encontrado para {data_corrigir.strftime('%d/%m/%Y')}")

    with tab2:
        st.subheader("📋 Minhas Solicitações de Correção")
        
        # Buscar solicitações do usuário
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, registro_id, data_hora_original, data_hora_nova,
                   tipo_original, tipo_novo, justificativa, status,
                   data_solicitacao, aprovado_por, data_aprovacao, observacoes
            FROM solicitacoes_correcao_registro
            WHERE usuario = %s
            ORDER BY data_solicitacao DESC
            LIMIT 50
        """, (st.session_state.usuario,))
        
        solicitacoes = cursor.fetchall()
        conn.close()
        
        if solicitacoes:
            for sol in solicitacoes:
                sol_id, reg_id, data_orig, data_nova, tipo_orig, tipo_novo, just, status, data_sol, aprov_por, data_aprov, obs = sol
                
                status_emoji = {
                    'pendente': '⏳',
                    'aprovado': '✅',
                    'rejeitado': '❌'
                }.get(status, '❓')
                
                with st.expander(f"{status_emoji} {data_orig} → {data_nova} - {status.upper()}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Dados Originais:**")
                        st.write(f"- Data/Hora: {data_orig}")
                        st.write(f"- Tipo: {tipo_orig}")
                    
                    with col2:
                        st.write("**Correção Solicitada:**")
                        st.write(f"- Nova Data/Hora: {data_nova}")
                        st.write(f"- Novo Tipo: {tipo_novo}")
                    
                    st.write(f"**Justificativa:** {just}")
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

    # Selecionar funcionário
    usuarios = obter_usuarios_ativos()
    usuario_selecionado = st.selectbox(
        "👤 Selecione o Funcionário",
        [f"{u['nome_completo']} ({u['usuario']})" for u in usuarios]
    )

    if usuario_selecionado:
        usuario = usuario_selecionado.split('(')[-1].replace(')', '')

        # Selecionar data
        data_corrigir = st.date_input(
            "📅 Data do Registro",
            value=date.today(),
            max_value=date.today()
        )

        # Buscar registros do dia
        registros = buscar_registros_dia(
            usuario, data_corrigir.strftime("%Y-%m-%d"))

        if registros:
            st.subheader(
                f"📋 Registros de {data_corrigir.strftime('%d/%m/%Y')}")

            for registro in registros:
                with st.expander(f"⏰ {registro['data_hora']} - {registro['tipo']}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Tipo:** {registro['tipo']}")
                        st.write(
                            f"**Data/Hora Atual:** {registro['data_hora']}")
                        st.write(
                            f"**Modalidade:** {registro['modalidade'] or 'N/A'}")
                        st.write(
                            f"**Projeto:** {registro['projeto'] or 'N/A'}")

                    with col2:
                        # Formulário de edição
                        with st.form(f"editar_registro_{registro['id']}"):
                            novo_tipo = st.selectbox(
                                "Novo Tipo",
                                ["inicio", "intermediario", "fim"],
                                index=["inicio", "intermediario",
                                       "fim"].index(registro['tipo'])
                            )

                            nova_data_hora = st.text_input(
                                "Nova Data/Hora (YYYY-MM-DD HH:MM)",
                                value=registro['data_hora']
                            )

                            nova_modalidade = st.selectbox(
                                "Nova Modalidade",
                                ["", "presencial", "home_office", "campo"],
                                index=["", "presencial", "home_office", "campo"].index(
                                    registro['modalidade'] or "")
                            )

                            novo_projeto = st.selectbox(
                                "Novo Projeto",
                                [""] + obter_projetos_ativos(),
                                index=[""] + obter_projetos_ativos().index(
                                    registro['projeto']) if registro['projeto'] in obter_projetos_ativos() else 0
                            )

                            # Justificativa obrigatória para auditoria da correção
                            justificativa_edicao = st.text_area(
                                "Justificativa da Edição",
                                placeholder="Explique por que esta correção é necessária...",
                                height=120
                            )

                            # Botão de salvar alteração do formulário
                            submitted = st.form_submit_button(
                                "💾 Salvar Alterações", use_container_width=True)

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
                                        st.session_state.usuario
                                    )

                                    if resultado["success"]:
                                        st.success(f"✅ {resultado['message']}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {resultado['message']}")
        else:
            st.info(
                f"📋 Nenhum registro encontrado para {usuario} em {data_corrigir.strftime('%d/%m/%Y')}")


def meus_registros_interface(calculo_horas_system):
    """Interface para visualizar registros com cálculos"""
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
            "Data Início", value=date.today() - timedelta(days=30))
    with col2:
        data_fim = st.date_input("Data Fim", value=date.today())
    with col3:
        projeto_filtro = st.selectbox(
            "Projeto", ["Todos"] + obter_projetos_ativos())

    # Calcular horas do período
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
        df['DataObj'] = pd.to_datetime(df['Data/Hora']).dt.date
        
        # Adicionar informação de multiplicador para cada dia
        from calculo_horas_system import eh_dia_com_multiplicador
        
        def get_badge_dia(data_obj):
            info = eh_dia_com_multiplicador(data_obj)
            if info['tem_multiplicador']:
                if info['eh_domingo'] and info['eh_feriado']:
                    return f"🎉📅 {info['nome_feriado']} (DOMINGO) - x2"
                elif info['eh_domingo']:
                    return "📅 DOMINGO - Horas em DOBRO (x2)"
                elif info['eh_feriado']:
                    return f"🎉 FERIADO: {info['nome_feriado']} - Horas em DOBRO (x2)"
            return ""
        
        # Agrupar por data e exibir com destaque
        st.markdown("### 📅 Registros Detalhados por Dia")
        
        for data_unica in df['DataObj'].unique():
            registros_dia = df[df['DataObj'] == data_unica]
            data_formatada = registros_dia.iloc[0]['Data']
            
            # Verificar se tem multiplicador
            badge = get_badge_dia(data_unica)
            
            if badge:
                # Exibir com destaque
                st.markdown(f"#### {data_formatada}")
                st.warning(f"**{badge}**")
            else:
                st.markdown(f"#### {data_formatada}")
            
            # Exibir registros do dia
            st.dataframe(
                registros_dia[['Hora', 'Tipo', 'Modalidade', 'Projeto', 'Atividade']],
                use_container_width=True,
                hide_index=True
            )
            
            # Calcular horas do dia
            calculo_dia = calculo_horas_system.calcular_horas_dia(
                st.session_state.usuario,
                data_unica.strftime("%Y-%m-%d")
            )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("⏱️ Horas Trabalhadas", 
                         format_time_duration(calculo_dia.get("horas_trabalhadas", 0)))
            with col2:
                st.metric("💼 Horas Líquidas", 
                         format_time_duration(calculo_dia.get("horas_liquidas", 0)))
            with col3:
                multiplicador = calculo_dia.get("multiplicador", 1)
                horas_finais = calculo_dia.get("horas_finais", 0)
                if multiplicador > 1:
                    st.metric("✨ Total Contabilizado", 
                             format_time_duration(horas_finais),
                             delta=f"x{multiplicador}")
                else:
                    st.metric("📊 Total Contabilizado", 
                             format_time_duration(horas_finais))
            
            st.markdown("---")

        # Exibir tabela completa (versão antiga mantida para referência)
        with st.expander("📊 Ver Tabela Completa (Todos os Registros)"):
            st.dataframe(
                df[['Data', 'Hora', 'Tipo', 'Modalidade',
                    'Projeto', 'Atividade', 'Localização']],
                use_container_width=True
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
                    st.write(f"**Upload em:** {safe_datetime_parse(upload['data_upload']).strftime('%d/%m/%Y às %H:%M')}")
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
                        # Redirecionar para a tela de aprovação
                        st.session_state.pagina_atual = "🕐 Aprovar Horas Extras"
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

    # Verificar se há solicitações de hora extra pendentes
    conn = None
    solicitacoes_pendentes_count = 0
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT COUNT(*) FROM horas_extras_ativas
            WHERE aprovador = {SQL_PLACEHOLDER}
            AND status = 'aguardando_aprovacao'
        """, (st.session_state.usuario,))
        result = cursor.fetchone()
        solicitacoes_pendentes_count = result[0] if result else 0
    except Exception as e:
        logger.error(f"Erro ao verificar solicitações pendentes: {str(e)}")
    finally:
        if conn:
            conn.close()
    
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
        
        if st.button("📋 Aprovar Agora", type="primary", use_container_width=True, key="btn_aprovar_rapido"):
            st.session_state.aprovar_hora_extra = True
            st.rerun()
    
    # Se clicou em aprovar hora extra, mostrar interface de aprovação
    if st.session_state.get('aprovar_hora_extra'):
        aprovar_hora_extra_rapida_interface()
        return  # Não exibir resto da interface

    # Menu lateral
    with st.sidebar:
        st.markdown("### 🎛️ Menu do Gestor")
        
        # Contar pendências para badges
        conn = get_connection()
        cursor = conn.cursor()
        
        # Horas extras para aprovar
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_horas_extras 
            WHERE aprovador_solicitado = %s AND status = 'pendente'
        """, (st.session_state.usuario,))
        he_aprovar = cursor.fetchone()[0]
        
        # Atestados pendentes
        cursor.execute("""
            SELECT COUNT(*) FROM atestado_horas 
            WHERE status = 'pendente'
        """)
        atestados_pendentes = cursor.fetchone()[0]
        
        # Correções pendentes (todas - gestor aprova todas)
        cursor.execute("""
            SELECT COUNT(*) FROM solicitacoes_correcao_registro 
            WHERE status = 'pendente'
        """)
        correcoes_pendentes = cursor.fetchone()[0]
        
        conn.close()
        
        total_notif = he_aprovar + atestados_pendentes + correcoes_pendentes
        
        opcoes_menu = [
            "📊 Dashboard",
            "👥 Todos os Registros",
            f"✅ Aprovar Atestados{f' 🔴{atestados_pendentes}' if atestados_pendentes > 0 else ''}",
            f"🕐 Aprovar Horas Extras{f' 🔴{he_aprovar}' if he_aprovar > 0 else ''}",
            "🏦 Banco de Horas Geral",
            "📁 Gerenciar Arquivos",
            "🏢 Gerenciar Projetos",
            "👤 Gerenciar Usuários",
            "📅 Configurar Jornada",
            f"🔧 Corrigir Registros{f' 🔴{correcoes_pendentes}' if correcoes_pendentes > 0 else ''}",
            f"🔔 Notificações{f' 🔴{total_notif}' if total_notif > 0 else ''}",
            "⚙️ Sistema"
        ]
        
        opcao = st.selectbox("Escolha uma opção:", opcoes_menu)

        if st.button("🚪 Sair", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Conteúdo baseado na opção
    if opcao == "📊 Dashboard":
        dashboard_gestor(banco_horas_system, calculo_horas_system)
    elif opcao.startswith("👥 Todos os Registros"):
        todos_registros_interface(calculo_horas_system)
    elif opcao.startswith("✅ Aprovar Atestados"):
        aprovar_atestados_interface(atestado_system)
    elif opcao.startswith("🕐 Aprovar Horas Extras"):
        aprovar_horas_extras_interface(horas_extras_system)
    elif opcao.startswith("🏦 Banco de Horas Geral"):
        banco_horas_gestor_interface(banco_horas_system)
    elif opcao.startswith("📅 Configurar Jornada"):
        configurar_jornada_interface()
    elif opcao.startswith("🔧 Corrigir Registros"):
        aprovar_correcoes_registros_interface()
    elif opcao.startswith("📁 Gerenciar Arquivos"):
        gerenciar_arquivos_interface(upload_system)
    elif opcao.startswith("🏢 Gerenciar Projetos"):
        gerenciar_projetos_interface()
    elif opcao.startswith("👤 Gerenciar Usuários"):
        gerenciar_usuarios_interface()
    elif opcao.startswith("🔔 Notificações"):
        notificacoes_gestor_interface(horas_extras_system, atestado_system)
    elif opcao.startswith("⚙️ Sistema"):
        sistema_interface()


def dashboard_gestor(banco_horas_system, calculo_horas_system):
    """Dashboard principal do gestor com destaque para discrepâncias"""
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Dashboard Executivo</h3>
        <p>Visão geral do sistema de ponto com alertas</p>
    </div>
    """, unsafe_allow_html=True)

    # Métricas gerais com tratamento robusto de erros
    total_usuarios = 0
    registros_hoje = 0
    ausencias_pendentes = 0
    horas_extras_pendentes = 0
    atestados_mes = 0
    hoje = date.today().strftime("%Y-%m-%d")
    
    if REFACTORING_ENABLED:
        try:
            # Total de usuários ativos
            query_usuarios = "SELECT COUNT(*) FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario'"
            resultado = execute_query(query_usuarios, fetch_one=True)
            if resultado:
                total_usuarios = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar total de usuários", e, {"context": "dashboard_gestor"})
            st.error(f"Erro ao buscar total de usuários: {e}")

        try:
            # Registros hoje
            query_registros = "SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = %s"
            resultado = execute_query(query_registros, (hoje,), fetch_one=True)
            if resultado:
                registros_hoje = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar registros de hoje", e, {"data": hoje})
            st.error(f"Erro ao buscar registros de hoje: {e}")

        try:
            # Ausências pendentes
            query_ausencias = "SELECT COUNT(*) FROM ausencias WHERE status = 'pendente'"
            resultado = execute_query(query_ausencias, fetch_one=True)
            if resultado:
                ausencias_pendentes = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar ausências pendentes", e, {"status": "pendente"})
            st.error(f"Erro ao buscar ausências pendentes: {e}")

        try:
            # Horas extras pendentes
            query_he = "SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente'"
            resultado = execute_query(query_he, fetch_one=True)
            if resultado:
                horas_extras_pendentes = resultado[0]
        except Exception as e:
            log_error("Erro ao buscar horas extras pendentes", e, {"status": "pendente"})
            st.error(f"Erro ao buscar horas extras pendentes: {e}")

        try:
            # Atestados do mês
            primeiro_dia_mes = date.today().replace(day=1).strftime("%Y-%m-%d")
            query_atestados = """
                SELECT COUNT(*) FROM ausencias 
                WHERE data_inicio >= %s AND tipo LIKE '%%Atestado%%'
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
                "SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = %s", (hoje,))
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
            cursor.execute("""
                SELECT COUNT(*) FROM ausencias 
                WHERE data_inicio >= %s AND tipo LIKE '%%Atestado%%'
            """, (primeiro_dia_mes,))
            resultado = cursor.fetchone()
            if resultado:
                atestados_mes = resultado[0]
        except Exception as e:
            st.error(f"Erro ao buscar atestados do mês: {e}")

        conn.close()

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
                    query_jornada = "SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = %s"
                    jornada = execute_query(query_jornada, (usuario,), fetch_one=True)
                except Exception as e:
                    log_error("Erro ao buscar jornada do usuário", e, {"usuario": usuario})
                    jornada = None
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = %s", (usuario,))
                jornada = cursor.fetchone()
                conn.close()

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
            use_container_width=True
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
                    use_container_width=True
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

    # Buscar todas as solicitações pendentes
    solicitacoes = None
    
    if REFACTORING_ENABLED:
        try:
            query_solicitacoes = """
                SELECT * FROM solicitacoes_horas_extras 
                WHERE status = 'pendente'
                ORDER BY data_solicitacao ASC
            """
            solicitacoes = execute_query(query_solicitacoes)
        except Exception as e:
            log_error("Erro ao buscar solicitações de horas extras pendentes", e, {"status": "pendente"})
            solicitacoes = []
    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM solicitacoes_horas_extras 
            WHERE status = 'pendente'
            ORDER BY data_solicitacao ASC
        """)
        solicitacoes = cursor.fetchall()
        conn.close()

    if solicitacoes:
        st.warning(
            f"⚠️ {len(solicitacoes)} solicitação(ões) de horas extras aguardando aprovação!")

        colunas = ['id', 'usuario', 'data', 'hora_inicio', 'hora_fim', 'justificativa',
                   'aprovador_solicitado', 'status', 'data_solicitacao', 'aprovado_por',
                   'data_aprovacao', 'observacoes']

        for solicitacao_raw in solicitacoes:
            solicitacao = dict(zip(colunas, solicitacao_raw))

            with st.expander(f"⏳ {solicitacao['usuario']} - {solicitacao['data']} ({solicitacao['hora_inicio']} às {solicitacao['hora_fim']})"):
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
                        f"**Solicitado em:** {safe_datetime_parse(solicitacao['data_solicitacao']).strftime('%d/%m/%Y às %H:%M')}")

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


def aprovar_correcoes_registros_interface():
    """Interface para gestor aprovar correções de registros solicitadas por funcionários"""
    st.markdown("""
    <div class="feature-card">
        <h3>🔧 Aprovar Correções de Registros</h3>
        <p>Gerencie solicitações de correção de ponto dos funcionários</p>
    </div>
    """, unsafe_allow_html=True)

    # Abas para diferentes status
    tab1, tab2, tab3 = st.tabs([
        "⏳ Pendentes",
        "✅ Aprovadas",
        "❌ Rejeitadas"
    ])

    with tab1:
        st.markdown("### ⏳ Correções Aguardando Aprovação")

        # Buscar correções pendentes
        pendentes = None
        
        if REFACTORING_ENABLED:
            try:
                query_pendentes = """
                    SELECT c.id, c.usuario, c.registro_id, c.data_hora_original, c.data_hora_nova,
                           c.tipo_original, c.tipo_novo, c.modalidade_original, c.modalidade_nova,
                           c.projeto_original, c.projeto_novo, c.justificativa, 
                           c.data_solicitacao, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'pendente'
                    ORDER BY c.data_solicitacao DESC
                """
                pendentes = execute_query(query_pendentes)
            except Exception as e:
                log_error("Erro ao buscar correções de registros pendentes", e, {"status": "pendente"})
                pendentes = []
        else:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT c.id, c.usuario, c.registro_id, c.data_hora_original, c.data_hora_nova,
                       c.tipo_original, c.tipo_novo, c.modalidade_original, c.modalidade_nova,
                       c.projeto_original, c.projeto_novo, c.justificativa, 
                       c.data_solicitacao, u.nome_completo
                FROM solicitacoes_correcao_registro c
                LEFT JOIN usuarios u ON c.usuario = u.usuario
                WHERE c.status = 'pendente'
                ORDER BY c.data_solicitacao DESC
            """)
            pendentes = cursor.fetchall()
            conn.close()

        if pendentes:
            st.info(f"📋 {len(pendentes)} solicitação(ões) aguardando aprovação")

            for correcao in pendentes:
                (correcao_id, usuario, registro_id, dt_original, dt_nova, 
                 tipo_orig, tipo_novo, mod_orig, mod_nova, proj_orig, proj_novo,
                 justificativa, data_solicitacao, nome_completo) = correcao

                with st.expander(f"⏳ {nome_completo or usuario} - {safe_datetime_parse(dt_original).strftime('%d/%m/%Y %H:%M')}"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                        st.markdown(f"**Solicitado em:** {safe_datetime_parse(data_solicitacao).strftime('%d/%m/%Y às %H:%M')}")
                        
                        st.markdown("---")
                        st.markdown("### 🔄 Alterações Solicitadas")
                        
                        # Data/Hora
                        if dt_original != dt_nova:
                            dt_orig_fmt = safe_datetime_parse(dt_original).strftime('%d/%m/%Y %H:%M')
                            dt_nova_fmt = safe_datetime_parse(dt_nova).strftime('%d/%m/%Y %H:%M')
                            st.markdown(f"**Data/Hora:** `{dt_orig_fmt}` → `{dt_nova_fmt}`")
                        
                        # Tipo
                        if tipo_orig != tipo_novo:
                            st.markdown(f"**Tipo:** `{tipo_orig}` → `{tipo_novo}`")
                        
                        # Modalidade
                        if mod_orig != mod_nova:
                            st.markdown(f"**Modalidade:** `{mod_orig or 'N/A'}` → `{mod_nova or 'N/A'}`")
                        
                        # Projeto
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
                            if st.button("✅ Aprovar", key=f"aprovar_corr_{correcao_id}", use_container_width=True, type="primary"):
                                try:
                                    if REFACTORING_ENABLED:
                                        # Atualizar registro original com novos dados
                                        query_update_registro = """
                                            UPDATE registros_ponto 
                                            SET data_hora = %s, tipo = %s, modalidade = %s, projeto = %s
                                            WHERE id = %s
                                        """
                                        execute_update(query_update_registro, (dt_nova, tipo_novo, mod_nova, proj_novo, registro_id))
                                        
                                        # Marcar correção como aprovada
                                        query_update_correcao = """
                                            UPDATE solicitacoes_correcao_registro
                                            SET status = 'aprovado', aprovado_por = %s, 
                                                data_aprovacao = CURRENT_TIMESTAMP, observacoes = %s
                                            WHERE id = %s
                                        """
                                        execute_update(query_update_correcao, (st.session_state.usuario, observacoes, correcao_id))
                                        
                                        log_security_event("CORRECAO_REGISTRO_APPROVED", usuario=st.session_state.usuario, context={"correcao_id": correcao_id, "funcionario": usuario, "registro_id": registro_id})
                                    else:
                                        conn = get_connection()
                                        cursor = conn.cursor()
                                        
                                        # Atualizar registro original com novos dados
                                        cursor.execute("""
                                            UPDATE registros_ponto 
                                            SET data_hora = %s, tipo = %s, modalidade = %s, projeto = %s
                                            WHERE id = %s
                                        """, (dt_nova, tipo_novo, mod_nova, proj_novo, registro_id))
                                        
                                        # Marcar correção como aprovada
                                        cursor.execute("""
                                            UPDATE solicitacoes_correcao_registro
                                            SET status = 'aprovado', aprovado_por = %s, 
                                                data_aprovacao = CURRENT_TIMESTAMP, observacoes = %s
                                            WHERE id = %s
                                        """, (st.session_state.usuario, observacoes, correcao_id))
                                        
                                        conn.commit()
                                        conn.close()
                                    
                                    st.success("✅ Correção aprovada e registro atualizado!")
                                    st.rerun()
                                    
                                except Exception as e:
                                    log_error("Erro ao aprovar correção de registro", str(e), {"correcao_id": correcao_id})
                                    st.error(f"❌ Erro ao aprovar: {str(e)}")

                        with col_b:
                            if st.button("❌ Rejeitar", key=f"rejeitar_corr_{correcao_id}", use_container_width=True):
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
                                            if REFACTORING_ENABLED:
                                                query_reject = """
                                                    UPDATE solicitacoes_correcao_registro
                                                    SET status = 'rejeitado', aprovado_por = %s,
                                                        data_aprovacao = CURRENT_TIMESTAMP, observacoes = %s
                                                    WHERE id = %s
                                                """
                                                execute_update(query_reject, (st.session_state.usuario, motivo, correcao_id))
                                                log_security_event("CORRECAO_REGISTRO_REJECTED", usuario=st.session_state.usuario, context={"correcao_id": correcao_id, "funcionario": usuario, "motivo": motivo})
                                            else:
                                                conn = get_connection()
                                                cursor = conn.cursor()
                                                
                                                cursor.execute("""
                                                    UPDATE solicitacoes_correcao_registro
                                                    SET status = 'rejeitado', aprovado_por = %s,
                                                        data_aprovacao = CURRENT_TIMESTAMP, observacoes = %s
                                                    WHERE id = %s
                                                """, (st.session_state.usuario, motivo, correcao_id))
                                                
                                                conn.commit()
                                                conn.close()
                                            
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

    with tab2:
        st.markdown("### ✅ Correções Aprovadas")
        
        aprovadas = None
        
        if REFACTORING_ENABLED:
            try:
                query_aprovadas = """
                    SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.tipo_original, c.tipo_novo, c.data_solicitacao, 
                           c.data_aprovacao, c.aprovado_por, c.observacoes, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'aprovado'
                    ORDER BY c.data_aprovacao DESC
                    LIMIT 50
                """
                aprovadas = execute_query(query_aprovadas)
            except Exception as e:
                log_error("Erro ao buscar correções de registros aprovadas", e, {"status": "aprovado"})
                aprovadas = []
        else:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                       c.tipo_original, c.tipo_novo, c.data_solicitacao, 
                       c.data_aprovacao, c.aprovado_por, c.observacoes, u.nome_completo
                FROM solicitacoes_correcao_registro c
                LEFT JOIN usuarios u ON c.usuario = u.usuario
                WHERE c.status = 'aprovado'
                ORDER BY c.data_aprovacao DESC
                LIMIT 50
            """)
            aprovadas = cursor.fetchall()
            conn.close()
        
        if aprovadas:
            st.info(f"✅ {len(aprovadas)} correção(ões) aprovada(s)")
            
            for correcao in aprovadas:
                (correcao_id, usuario, dt_original, dt_nova, tipo_orig, tipo_novo,
                 data_solicitacao, data_aprovacao, aprovado_por, observacoes, nome_completo) = correcao
                
                with st.expander(f"✅ {nome_completo or usuario} - {safe_datetime_parse(data_aprovacao).strftime('%d/%m/%Y')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                        dt_orig_fmt = safe_datetime_parse(dt_original).strftime('%d/%m/%Y %H:%M')
                        dt_nova_fmt = safe_datetime_parse(dt_nova).strftime('%d/%m/%Y %H:%M')
                        st.markdown(f"**Data/Hora:** `{dt_orig_fmt}` → `{dt_nova_fmt}`")
                        if tipo_orig != tipo_novo:
                            st.markdown(f"**Tipo:** `{tipo_orig}` → `{tipo_novo}`")
                    
                    with col2:
                        st.markdown(f"**Aprovado por:** {aprovado_por}")
                        st.markdown(f"**Data aprovação:** {safe_datetime_parse(data_aprovacao).strftime('%d/%m/%Y %H:%M')}")
                        if observacoes:
                            st.markdown(f"**Observações:** {observacoes}")
        else:
            st.info("📋 Nenhuma correção aprovada ainda")

    with tab3:
        st.markdown("### ❌ Correções Rejeitadas")
        
        rejeitadas = None
        
        if REFACTORING_ENABLED:
            try:
                query_rejeitadas = """
                    SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.data_solicitacao, c.data_aprovacao, c.aprovado_por, 
                           c.observacoes, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'rejeitado'
                    ORDER BY c.data_aprovacao DESC
                    LIMIT 50
                """
                rejeitadas = execute_query(query_rejeitadas)
            except Exception as e:
                log_error("Erro ao buscar correções de registros rejeitadas", e, {"status": "rejeitado"})
                rejeitadas = []
        else:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                       c.data_solicitacao, c.data_aprovacao, c.aprovado_por, 
                       c.observacoes, u.nome_completo
                FROM solicitacoes_correcao_registro c
                LEFT JOIN usuarios u ON c.usuario = u.usuario
                WHERE c.status = 'rejeitado'
                ORDER BY c.data_aprovacao DESC
                LIMIT 50
            """)
            rejeitadas = cursor.fetchall()
            conn.close()
        
        if rejeitadas:
            st.warning(f"❌ {len(rejeitadas)} correção(ões) rejeitada(s)")
            
            for correcao in rejeitadas:
                (correcao_id, usuario, dt_original, dt_nova, data_solicitacao,
                 data_rejeicao, rejeitado_por, motivo, nome_completo) = correcao
                
                with st.expander(f"❌ {nome_completo or usuario} - {safe_datetime_parse(data_rejeicao).strftime('%d/%m/%Y')}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    st.markdown(f"**Rejeitado por:** {rejeitado_por}")
                    st.markdown(f"**Data rejeição:** {safe_datetime_parse(data_rejeicao).strftime('%d/%m/%Y %H:%M')}")
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
                    SELECT h.id, h.usuario, h.data, h.horas_solicitadas, h.justificativa,
                           h.data_solicitacao, u.nome_completo
                    FROM solicitacoes_horas_extras h
                    LEFT JOIN usuarios u ON h.usuario = u.usuario
                    WHERE h.status = 'pendente'
                    ORDER BY h.data_solicitacao DESC
                """
                he_pendentes = execute_query(query_he)
            except Exception as e:
                log_error("Erro ao buscar horas extras pendentes nas notificações", e, {"status": "pendente"})
                he_pendentes = []
        else:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT h.id, h.usuario, h.data, h.horas_solicitadas, h.justificativa,
                       h.data_solicitacao, u.nome_completo
                FROM solicitacoes_horas_extras h
                LEFT JOIN usuarios u ON h.usuario = u.usuario
                WHERE h.status = 'pendente'
                ORDER BY h.data_solicitacao DESC
            """)
            he_pendentes = cursor.fetchall()
            conn.close()
        
        if he_pendentes:
            st.info(f"📋 {len(he_pendentes)} solicitação(ões) de horas extras")
            
            for he in he_pendentes:
                he_id, usuario, data, horas, justificativa, data_solicitacao, nome_completo = he
                
                with st.expander(f"⏳ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    st.markdown(f"**Data:** {data}")
                    st.markdown(f"**Horas:** {format_time_duration(horas)}")
                    st.markdown(f"**Solicitado em:** {safe_datetime_parse(data_solicitacao).strftime('%d/%m/%Y %H:%M')}")
                    st.markdown("**Justificativa:**")
                    st.info(justificativa)
                    
                    if st.button("Ver detalhes completos", key=f"ver_he_{he_id}"):
                        st.session_state['opcao_menu'] = "🕐 Aprovar Horas Extras"
                        st.rerun()
        else:
            st.success("✅ Nenhuma solicitação de horas extras pendente")

    with tab2:
        st.markdown("### 🔧 Solicitações de Correção de Registro Pendentes")
        
        corr_pendentes = None
        
        if REFACTORING_ENABLED:
            try:
                query_corr = """
                    SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                           c.justificativa, c.data_solicitacao, u.nome_completo
                    FROM solicitacoes_correcao_registro c
                    LEFT JOIN usuarios u ON c.usuario = u.usuario
                    WHERE c.status = 'pendente'
                    ORDER BY c.data_solicitacao DESC
                """
                corr_pendentes = execute_query(query_corr)
            except Exception as e:
                log_error("Erro ao buscar correções de registros pendentes nas notificações", e, {"status": "pendente"})
                corr_pendentes = []
        else:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.id, c.usuario, c.data_hora_original, c.data_hora_nova,
                       c.justificativa, c.data_solicitacao, u.nome_completo
                FROM solicitacoes_correcao_registro c
                LEFT JOIN usuarios u ON c.usuario = u.usuario
                WHERE c.status = 'pendente'
                ORDER BY c.data_solicitacao DESC
            """)
            corr_pendentes = cursor.fetchall()
            conn.close()
        
        if corr_pendentes:
            st.info(f"📋 {len(corr_pendentes)} solicitação(ões) de correção")
            
            for correcao in corr_pendentes:
                corr_id, usuario, dt_orig, dt_nova, justificativa, data_solicitacao, nome_completo = correcao
                
                with st.expander(f"⏳ {nome_completo or usuario} - {safe_datetime_parse(dt_orig).strftime('%d/%m/%Y %H:%M')}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    dt_orig_fmt = safe_datetime_parse(dt_orig).strftime('%d/%m/%Y %H:%M')
                    dt_nova_fmt = safe_datetime_parse(dt_nova).strftime('%d/%m/%Y %H:%M')
                    st.markdown(f"**Alteração:** `{dt_orig_fmt}` → `{dt_nova_fmt}`")
                    st.markdown(f"**Solicitado em:** {safe_datetime_parse(data_solicitacao).strftime('%d/%m/%Y %H:%M')}")
                    st.markdown("**Justificativa:**")
                    st.info(justificativa)
                    
                    if st.button("Ver detalhes completos", key=f"ver_corr_{corr_id}"):
                        st.session_state['opcao_menu'] = "🔧 Corrigir Registros"
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
                """
                atestados_pendentes = execute_query(query_atestados)
            except Exception as e:
                log_error("Erro ao buscar atestados de horas pendentes nas notificações", e, {"status": "pendente"})
                atestados_pendentes = []
        else:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT a.id, a.usuario, a.data, a.total_horas, a.motivo,
                       a.data_registro, u.nome_completo
                FROM atestado_horas a
                LEFT JOIN usuarios u ON a.usuario = u.usuario
                WHERE a.status = 'pendente'
                ORDER BY a.data_registro DESC
            """)
            atestados_pendentes = cursor.fetchall()
            conn.close()
        
        if atestados_pendentes:
            st.info(f"📋 {len(atestados_pendentes)} atestado(s) pendente(s)")
            
            for atestado in atestados_pendentes:
                atestado_id, usuario, data, horas, motivo, data_registro, nome_completo = atestado
                
                with st.expander(f"⏳ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else safe_datetime_parse(data).strftime('%d/%m/%Y')
                    st.markdown(f"**Data:** {data_fmt}")
                    st.markdown(f"**Horas:** {format_time_duration(horas)}")
                    st.markdown(f"**Solicitado em:** {safe_datetime_parse(data_registro).strftime('%d/%m/%Y %H:%M')}")
                    st.markdown("**Motivo:**")
                    st.info(motivo or "Sem motivo especificado")
                    
                    if st.button("Ver detalhes completos", key=f"ver_atestado_{atestado_id}"):
                        st.session_state['opcao_menu'] = "✅ Aprovar Atestados"
                        st.rerun()
        else:
            st.success("✅ Nenhum atestado pendente")


# Outras interfaces do gestor (simplificadas)


def aprovar_atestados_interface(atestado_system):
    """Interface para aprovar atestados de horas"""
    st.markdown("""
    <div class="feature-card">
        <h3>✅ Aprovar Atestados de Horas</h3>
        <p>Gerencie solicitações de atestados de horas dos funcionários</p>
    </div>
    """, unsafe_allow_html=True)

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
            conn.close()

        if pendentes:
            st.info(f"📋 {len(pendentes)} solicitação(ões) aguardando aprovação")

            for atestado in pendentes:
                atestado_id, usuario, data, horas, justificativa, data_solicitacao, arquivo_id, nome_completo = atestado

                with st.expander(f"⏳ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(
                            f"**Funcionário:** {nome_completo or usuario}")
                        # Data pode vir como date (PostgreSQL) ou string (SQLite)
                        data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else safe_datetime_parse(data).strftime('%d/%m/%Y')
                        st.markdown(f"**Data do Atestado:** {data_fmt}")
                        st.markdown(
                            f"**Horas Trabalhadas:** {format_time_duration(horas)}")
                        st.markdown(
                            f"**Solicitado em:** {safe_datetime_parse(data_solicitacao).strftime('%d/%m/%Y às %H:%M')}")

                        st.markdown("---")
                        st.markdown("**Justificativa:**")
                        st.info(justificativa or "Sem justificativa")

                        # Arquivo anexo
                        if arquivo_id:
                            st.markdown("---")
                            st.markdown("**📎 Documento Anexado:**")

                            # Buscar informações do arquivo pelo caminho
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "SELECT id, nome_original, tamanho, tipo_arquivo FROM uploads WHERE caminho = %s",
                                (arquivo_id,)
                            )
                            arquivo_info = cursor.fetchone()
                            conn.close()

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
                            if st.button("✅ Aprovar", key=f"aprovar_{atestado_id}", use_container_width=True, type="primary"):
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
                            if st.button("❌ Rejeitar", key=f"rejeitar_{atestado_id}", use_container_width=True):
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
            query += " AND DATE(a.data_aprovacao) >= %s"
            params.append(data_limite)

        if busca_usuario:
            query += " AND (a.usuario LIKE %s OR u.nome_completo LIKE %s)"
            params.extend([f'%{busca_usuario}%', f'%{busca_usuario}%'])

        query += " ORDER BY a.data_aprovacao DESC"

        cursor.execute(query, params)
        aprovados = cursor.fetchall()
        conn.close()

        if aprovados:
            st.info(f"✅ {len(aprovados)} atestado(s) aprovado(s)")

            for atestado in aprovados:
                atestado_id, usuario, data, horas, justificativa, data_aprovacao, aprovado_por, observacoes, nome_completo, aprovador_nome = atestado

                with st.expander(f"✅ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        st.markdown(
                            f"**Funcionário:** {nome_completo or usuario}")
                        data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else safe_datetime_parse(data).strftime('%d/%m/%Y')
                        st.markdown(f"**Data:** {data_fmt}")
                        st.markdown(
                            f"**Horas:** {format_time_duration(horas)}")
                        st.markdown(
                            f"**Justificativa:** {justificativa or 'N/A'}")

                        st.markdown("---")
                        st.success(
                            f"✅ Aprovado por **{aprovador_nome or aprovado_por}** em {safe_datetime_parse(data_aprovacao).strftime('%d/%m/%Y às %H:%M')}")

                        if observacoes:
                            st.info(f"💬 **Observações:** {observacoes}")

                    with col2:
                        # Opção de reverter aprovação
                        if st.button("🔄 Reverter", key=f"reverter_{atestado_id}", use_container_width=True):
                            st.session_state[f'confirm_reverter_{atestado_id}'] = True

                        if st.session_state.get(f'confirm_reverter_{atestado_id}'):
                            st.warning("⚠️ Reverter aprovação?")
                            motivo_rev = st.text_input(
                                "Motivo:", key=f"motivo_rev_{atestado_id}")

                            if st.button("Confirmar", key=f"conf_rev_{atestado_id}"):
                                if motivo_rev:
                                    conn = get_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        UPDATE atestado_horas 
                                        SET status = 'pendente', 
                                            data_aprovacao = NULL,
                                            aprovado_por = NULL,
                                            observacoes = %s
                                        WHERE id = %s
                                    """, (f"Revertido: {motivo_rev}", atestado_id))
                                    conn.commit()
                                    conn.close()

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
        conn.close()

        if rejeitados:
            st.warning(f"❌ {len(rejeitados)} atestado(s) rejeitado(s)")

            for atestado in rejeitados:
                atestado_id, usuario, data, horas, motivo, data_rejeicao, rejeitado_por, observacoes, nome_completo = atestado

                with st.expander(f"❌ {nome_completo or usuario} - {data} - {format_time_duration(horas)}"):
                    st.markdown(f"**Funcionário:** {nome_completo or usuario}")
                    data_fmt = data.strftime('%d/%m/%Y') if isinstance(data, (datetime, date)) else safe_datetime_parse(data).strftime('%d/%m/%Y')
                    st.markdown(f"**Data:** {data_fmt}")
                    st.markdown(f"**Horas:** {format_time_duration(horas)}")
                    st.markdown(f"**Motivo:** {motivo or 'N/A'}")

                    st.markdown("---")
                    # No schema atual, rejeição usa as colunas aprovado_por/data_aprovacao
                    rejeitador_display = rejeitado_por or 'gestor'
                    st.error(
                        f"❌ Rejeitado por **{rejeitador_display}** em {safe_datetime_parse(data_rejeicao).strftime('%d/%m/%Y às %H:%M')}")

                    if observacoes:
                        st.warning(
                            f"📝 **Observações:** {observacoes}")
        else:
            st.info("📁 Nenhum atestado rejeitado")

    with tab4:
        st.markdown("### 📊 Todos os Atestados")

        # Estatísticas gerais
        conn = get_connection()
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
        conn.close()

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
                use_container_width=True,
                hide_index=True
            )

            # Exportar
            csv = df.to_csv(index=False).encode('utf-8-sig')
            safe_download_button(
                label="📥 Exportar CSV",
                data=csv,
                file_name=f"atestados_{datetime.now().strftime('%Y%m%d')}.csv",
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
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT usuario, nome_completo FROM usuarios WHERE tipo = 'funcionario' ORDER BY nome_completo")
        usuarios_list = cursor.fetchall()
        conn.close()

        usuario_options = ["Todos"] + \
            [f"{u[1] or u[0]} ({u[0]})" for u in usuarios_list]
        usuario_filter = st.selectbox("👤 Funcionário:", usuario_options)

    with col2:
        # Período padrão: últimos 30 dias
        data_inicio = st.date_input(
            "📅 Data Início:",
            value=datetime.now().date() - timedelta(days=30)
        )

    with col3:
        data_fim = st.date_input(
            "📅 Data Fim:",
            value=datetime.now().date()
        )

    with col4:
        tipo_registro = st.selectbox(
            "🕐 Tipo:",
            ["Todos", "Início", "Fim", "Intervalo"]
        )

    # Buscar registros
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT r.id, r.usuario, r.data_hora, r.tipo, r.modalidade, 
               r.projeto, r.atividade, r.localizacao, r.latitude, r.longitude,
               u.nome_completo
        FROM registros_ponto r
        LEFT JOIN usuarios u ON r.usuario = u.usuario
        WHERE DATE(r.data_hora) BETWEEN %s AND %s
    """
    params = [data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d")]

    # Aplicar filtro de usuário
    if usuario_filter != "Todos":
        usuario_login = usuario_filter.split("(")[1].rstrip(")")
        query += " AND r.usuario = %s"
        params.append(usuario_login)

    # Aplicar filtro de tipo
    if tipo_registro != "Todos":
        query += " AND r.tipo = %s"
        params.append(tipo_registro)

    query += " ORDER BY r.data_hora DESC LIMIT 500"

    cursor.execute(query, params)
    registros = cursor.fetchall()
    conn.close()

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
            # Preparar dados para exportação
            df_export = pd.DataFrame(registros, columns=[
                'ID', 'Usuário', 'Data/Hora', 'Tipo', 'Modalidade',
                'Projeto', 'Atividade', 'Localização', 'Latitude', 'Longitude', 'Nome Completo'
            ])
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            safe_download_button(
                label="📥 Exportar CSV",
                data=csv,
                file_name=f"registros_ponto_{data_inicio}_{data_fim}.csv",
                mime="text/csv",
                use_container_width=True
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
                use_container_width=True
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
                        if reg['latitude'] and reg['longitude']:
                            st.markdown(
                                f"📍 **GPS:** {reg['latitude']:.6f}, {reg['longitude']:.6f}")
                            # Link para Google Maps
                            maps_url = f"https://www.google.com/maps?q={reg['latitude']},{reg['longitude']}"
                            st.markdown(f"[🗺️ Ver no Mapa]({maps_url})")
                        else:
                            st.markdown("📍 **GPS:** Não disponível")

                    if i < len(regs):
                        st.markdown("---")

                # Análise de discrepâncias
                if inicio and fim:
                    # Buscar jornada prevista do usuário
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT jornada_inicio_previsto, jornada_fim_previsto FROM usuarios WHERE usuario = %s",
                        (usuario,)
                    )
                    jornada = cursor.fetchone()
                    conn.close()

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

        st.dataframe(df_stats, use_container_width=True, hide_index=True)


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
            query += " AND u.relacionado_a = %s"
            params.append(categoria_map[categoria_filter])

        if usuario_filter:
            query += " AND (u.usuario LIKE %s OR us.nome_completo LIKE %s)"
            params.extend([f"%{usuario_filter}%", f"%{usuario_filter}%"])

        if data_filter:
            query += " AND DATE(u.data_upload) = %s"
            params.append(data_filter.strftime("%Y-%m-%d"))

        query += " ORDER BY u.data_upload DESC LIMIT 100"

        cursor.execute(query, params)
        arquivos = cursor.fetchall()
        conn.close()

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
                "SELECT COUNT(*) FROM uploads WHERE DATE(data_upload) = %s", (hoje_str,))
            hoje = cursor.fetchone()[0]
            st.metric("Uploads Hoje", hoje)

        conn.close()

    # Listagem de arquivos
    st.markdown("### 📋 Arquivos")

    if arquivos:
        st.info(f"Exibindo {len(arquivos)} arquivo(s)")

        for arquivo in arquivos:
            arquivo_id, usuario, nome, tipo_arquivo, data, tamanho, tipo_arquivo, nome_completo = arquivo

            with st.expander(f"{get_file_icon(tipo_arquivo)} {nome} - {nome_completo or usuario}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Usuário:** {nome_completo or usuario}")
                    st.write(f"**Tipo:** {tipo_arquivo or 'N/A'}")
                    st.write(
                        f"**Data:** {safe_datetime_parse(data).strftime('%d/%m/%Y às %H:%M')}")
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
                            use_container_width=True
                        )

                    # Botão de exclusão (com confirmação)
                    if st.button(f"🗑️ Excluir", key=f"del_{arquivo_id}", use_container_width=True):
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

                # Visualização de imagens
                if is_image_file(tipo_arquivo):
                    content, _ = upload_system.get_file_content(
                        arquivo_id, usuario)
                    if content:
                        st.image(content, caption=nome, width=400)
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
            conn.close()

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
                        if st.button("💾 Salvar", key=f"save_{projeto_id}", use_container_width=True):
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
                                cursor = conn.cursor()

                                cursor.execute(f"""
                                    UPDATE projetos 
                                    SET nome = {SQL_PLACEHOLDER}, descricao = {SQL_PLACEHOLDER}, ativo = {SQL_PLACEHOLDER}
                                    WHERE id = {SQL_PLACEHOLDER}
                                """, (novo_nome, nova_descricao, int(novo_status), projeto_id))

                                conn.commit()
                                conn.close()

                                st.success("✅ Projeto atualizado!")
                                st.rerun()

                        # Botão de excluir
                        if st.button("🗑️ Excluir", key=f"del_{projeto_id}", use_container_width=True):
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
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        f"DELETE FROM projetos WHERE id = {SQL_PLACEHOLDER}", (projeto_id,))
                                    conn.commit()
                                    conn.close()

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
                "➕ Cadastrar Projeto", use_container_width=True)

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
                            cursor = conn.cursor()

                            cursor.execute(f"""
                                INSERT INTO projetos (nome, descricao, ativo)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            """, (nome_novo, descricao_nova, int(ativo_novo)))

                            conn.commit()
                            conn.close()

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
                query += " AND (usuario LIKE %s OR nome_completo LIKE %s)"
                params.extend([f"%{busca}%", f"%{busca}%"])

            query += " ORDER BY nome_completo"

            cursor.execute(query, params)
            usuarios = cursor.fetchall()
            conn.close()

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
                                    except:
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
                                    except:
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
                                        senha_hash = hashlib.sha256(
                                            nova_senha.encode()).hexdigest()
                                        update_query = "UPDATE usuarios SET senha = %s WHERE id = %s"
                                        execute_update(update_query, (senha_hash, usuario_id))
                                        log_security_event("PASSWORD_CHANGED", usuario=st.session_state.usuario, context={"target_user_id": usuario_id})
                                        st.success("✅ Senha alterada com sucesso!")
                                    except Exception as e:
                                        log_error("Erro ao alterar senha", e, {"usuario_id": usuario_id})
                                        st.error(f"❌ Erro: {e}")
                                else:
                                    # Fallback original
                                    conn = get_connection()
                                    cursor = conn.cursor()

                                    senha_hash = hashlib.sha256(
                                        nova_senha.encode()).hexdigest()
                                    cursor.execute(
                                        "UPDATE usuarios SET senha = %s WHERE id = %s",
                                        (senha_hash, usuario_id)
                                    )

                                    conn.commit()
                                    conn.close()

                                    st.success("✅ Senha alterada com sucesso!")

                    with col2:
                        st.write("")
                        st.write("")

                        # Botão de salvar
                        if st.button("💾 Salvar", key=f"save_{usuario_id}", use_container_width=True):
                            if REFACTORING_ENABLED:
                                try:
                                    update_query = """
                                        UPDATE usuarios 
                                        SET nome_completo = %s, tipo = %s, ativo = %s,
                                            jornada_inicio_previsto = %s, jornada_fim_previsto = %s
                                        WHERE id = %s
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
                                # Fallback original
                                conn = get_connection()
                                cursor = conn.cursor()

                                cursor.execute("""
                                    UPDATE usuarios 
                                    SET nome_completo = %s, tipo = %s, ativo = %s,
                                        jornada_inicio_previsto = %s, jornada_fim_previsto = %s
                                    WHERE id = %s
                                """, (
                                    novo_nome,
                                    novo_tipo,
                                    int(novo_ativo),
                                    nova_jornada_inicio.strftime("%H:%M"),
                                    nova_jornada_fim.strftime("%H:%M"),
                                    usuario_id
                                ))

                                conn.commit()
                                conn.close()
                                
                                # Salvar jornada semanal
                                from jornada_semanal_system import salvar_jornada_semanal
                                salvar_jornada_semanal(usuario_id, jornada_config)

                                st.success("✅ Usuário atualizado!")
                                st.rerun()

                        # Botão de excluir
                        if st.button("🗑️ Excluir", key=f"del_{usuario_id}", use_container_width=True):
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
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        f"DELETE FROM usuarios WHERE id = {SQL_PLACEHOLDER}", (usuario_id,))
                                    conn.commit()
                                    conn.close()

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
                nova_senha = st.text_input("Senha:*", type="password")

            with col2:
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
                "➕ Cadastrar Usuário", use_container_width=True)

            if submitted:
                # Validações
                if not novo_login or not novo_nome or not nova_senha:
                    st.error("❌ Preencha todos os campos obrigatórios!")
                elif nova_senha != confirmar_senha:
                    st.error("❌ As senhas não conferem!")
                else:
                    if REFACTORING_ENABLED:
                        try:
                            senha_hash = hashlib.sha256(
                                nova_senha.encode()).hexdigest()

                            insert_query = f"""
                                INSERT INTO usuarios 
                                (usuario, senha, tipo, nome_completo, ativo, 
                                 jornada_inicio_previsto, jornada_fim_previsto)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            """
                            novo_usuario_id = execute_update(insert_query, (
                                novo_login,
                                senha_hash,
                                novo_tipo,
                                novo_nome,
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
                        # Fallback original
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()

                            senha_hash = hashlib.sha256(
                                nova_senha.encode()).hexdigest()

                            cursor.execute(f"""
                                INSERT INTO usuarios 
                                (usuario, senha, tipo, nome_completo, ativo, 
                                 jornada_inicio_previsto, jornada_fim_previsto)
                                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
                            """, (
                                novo_login,
                                senha_hash,
                                novo_tipo,
                                novo_nome,
                                int(novo_ativo),
                                jornada_inicio.strftime("%H:%M"),
                                jornada_fim.strftime("%H:%M")
                            ))
                            
                            # Obter ID do usuário recém-criado
                            cursor.execute("SELECT last_insert_rowid()")
                            novo_usuario_id = cursor.fetchone()[0]

                            conn.commit()
                            conn.close()
                            
                            # Copiar jornada padrão para dias úteis (seg-sex)
                            from jornada_semanal_system import copiar_jornada_padrao_para_dias
                            copiar_jornada_padrao_para_dias(novo_usuario_id, ['seg', 'ter', 'qua', 'qui', 'sex'])

                            st.success(
                                f"✅ Usuário '{novo_nome}' cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar usuário: {e}")


def sistema_interface():
    """Interface de configurações do sistema"""
    st.markdown("""
    <div class="feature-card">
        <h3>⚙️ Configurações do Sistema</h3>
        <p>Configure parâmetros gerais do sistema de ponto</p>
    </div>
    """, unsafe_allow_html=True)

    # Criar tabela de configurações se não existir
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT,
            descricao TEXT,
            data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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

    for chave, valor, descricao in configs_padrao:
        cursor.execute("""
            INSERT INTO configuracoes (chave, valor, descricao)
            VALUES (%s, %s, %s)
            ON CONFLICT (chave) DO NOTHING
        """, (chave, valor, descricao))

    conn.commit()

    # Buscar configurações atuais
    cursor.execute(
        "SELECT chave, valor, descricao FROM configuracoes ORDER BY chave")
    configs = cursor.fetchall()
    conn.close()

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

        if st.form_submit_button("💾 Salvar Configurações de Jornada", use_container_width=True):
            conn = get_connection()
            cursor = conn.cursor()

            configs_jornada = [
                ('jornada_inicio_padrao', jornada_inicio.strftime("%H:%M")),
                ('jornada_fim_padrao', jornada_fim.strftime("%H:%M")),
                ('tolerancia_atraso_minutos', str(tolerancia)),
                ('dias_historico_padrao', str(dias_historico)),
            ]

            for chave, valor in configs_jornada:
                cursor.execute(f"""
                    UPDATE configuracoes 
                    SET valor = {SQL_PLACEHOLDER}, data_atualizacao = CURRENT_TIMESTAMP
                    WHERE chave = {SQL_PLACEHOLDER}
                """, (valor, chave))

            conn.commit()
            conn.close()

            st.success("✅ Configurações de jornada salvas!")
            st.rerun()

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

        if st.form_submit_button("💾 Salvar Configurações de Horas Extras", use_container_width=True):
            conn = get_connection()
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
            conn.close()

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

        if st.form_submit_button("💾 Salvar Configurações de GPS", use_container_width=True):
            conn = get_connection()
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
            conn.close()

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

        if st.form_submit_button("💾 Salvar Configurações Gerais", use_container_width=True):
            conn = get_connection()
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
            conn.close()
            st.success("✅ Configurações salvas!")
            st.rerun()


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
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, usuario, nome_completo
            FROM usuarios
            WHERE tipo = 'funcionario' AND ativo = 1
            ORDER BY nome_completo
        """)
        usuarios_result = cursor.fetchall()
        conn.close()
    
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
                with st.form(f"form_jornada_{dia}"):
                    trabalha_novo = st.checkbox(
                        "Trabalha neste dia",
                        value=dia_config.get('trabalha', True),
                        key=f"trabalha_{dia}"
                    )
                    
                    if trabalha_novo:
                        col1, col2 = st.columns(2)
                        with col1:
                            hora_inicio_novo = st.time_input(
                                "Hora Início",
                                value=datetime.strptime(dia_config.get('inicio', '08:00'), '%H:%M').time(),
                                key=f"inicio_{dia}"
                            )
                        
                        with col2:
                            hora_fim_nova = st.time_input(
                                "Hora Fim",
                                value=datetime.strptime(dia_config.get('fim', '17:00'), '%H:%M').time(),
                                key=f"fim_{dia}"
                            )
                        
                        intervalo_novo = st.number_input(
                            "Intervalo (minutos)",
                            value=int(dia_config.get('intervalo', 60)),
                            min_value=0,
                            max_value=240,
                            step=15,
                            key=f"intervalo_{dia}"
                        )
                    else:
                        hora_inicio_novo = None
                        hora_fim_nova = None
                        intervalo_novo = 0
                    
                    # Botão para salvar este dia
                    if st.form_submit_button(f"💾 Salvar {NOMES_DIAS.get(dia, dia)}", use_container_width=True):
                        # Atualizar configuração
                        jornada_atual[dia] = {
                            'trabalha': trabalha_novo,
                            'inicio': hora_inicio_novo.strftime('%H:%M') if hora_inicio_novo else '08:00',
                            'fim': hora_fim_nova.strftime('%H:%M') if hora_fim_nova else '17:00',
                            'intervalo': int(intervalo_novo)
                        }
                        
                        # Salvar no banco
                        if salvar_jornada_semanal(usuario_id, jornada_atual):
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
        if st.button("📋 Copiar para dias úteis (Seg-Sex)", use_container_width=True):
            # Copiar config de segunda para ter um padrão
            padrao = jornada_atual.get('seg', {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60})
            for dia in ['ter', 'qua', 'qui', 'sex']:
                jornada_atual[dia] = padrao.copy()
            
            if salvar_jornada_semanal(usuario_id, jornada_atual):
                st.success("✅ Padrão copiado para dias úteis!")
                st.rerun()
            else:
                st.error("❌ Erro ao copiar padrão")
    
    with col2:
        if st.button("🏖️ Desativar fim de semana (Sab-Dom)", use_container_width=True):
            for dia in ['sab', 'dom']:
                jornada_atual[dia] = {'trabalha': False, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 0}
            
            if salvar_jornada_semanal(usuario_id, jornada_atual):
                st.success("✅ Fim de semana desativado!")
                st.rerun()
            else:
                st.error("❌ Erro ao desativar fim de semana")
    
    with col3:
        if st.button("🔄 Resetar para padrão", use_container_width=True):
            # Resetar para 08:00-17:00 seg-sex
            for dia in dias_semana_ordem:
                if dia in ['seg', 'ter', 'qua', 'qui', 'sex']:
                    jornada_atual[dia] = {'trabalha': True, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 60}
                else:
                    jornada_atual[dia] = {'trabalha': False, 'inicio': '08:00', 'fim': '17:00', 'intervalo': 0}
            
            if salvar_jornada_semanal(usuario_id, jornada_atual):
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
            with col1:
                if st.button("✅ Vou Finalizar", use_container_width=True, key="btn_vai_finalizar"):
                    st.success("Tudo bem! Trabalhe um ótimo dia 🎉")
            with col2:
                if st.button("⏱️ Vou Fazer Hora Extra", type="primary", use_container_width=True, key="btn_vai_fazer_he"):
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
    if REFACTORING_ENABLED:
        try:
            with safe_cursor() as cursor:
                cursor.execute(f"""
                    SELECT id, usuario, data_hora, tipo, modalidade, projeto, atividade
                    FROM registros_ponto 
                    WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
                    ORDER BY data_hora
                """, (usuario, data))

                registros = []
                for row in cursor.fetchall():
                    registros.append({
                        'id': row[0],
                        'usuario': row[1],
                        'data_hora': row[2],
                        'tipo': row[3],
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
                WHERE usuario = {SQL_PLACEHOLDER} AND DATE(data_hora) = {SQL_PLACEHOLDER}
                ORDER BY data_hora
            """, (usuario, data))

            registros = []
            for row in cursor.fetchall():
                registros.append({
                    'id': row[0],
                    'usuario': row[1],
                    'data_hora': row[2],
                    'tipo': row[3],
                    'modalidade': row[4],
                    'projeto': row[5],
                    'atividade': row[6]
                })

            return registros
        finally:
            conn.close()


def corrigir_registro_ponto(registro_id, novo_tipo, nova_data_hora, nova_modalidade, novo_projeto, justificativa, gestor):
    """Corrige um registro de ponto existente"""
    if REFACTORING_ENABLED:
        try:
            # Verificar se o registro existe
            check_query = f"SELECT id FROM registros_ponto WHERE id = {SQL_PLACEHOLDER}"
            result = execute_query(check_query, (registro_id,), fetch_one=True)
            if not result:
                return {"success": False, "message": "Registro não encontrado"}

            # Atualizar registro
            update_query = f"""
                UPDATE registros_ponto 
                SET tipo = {SQL_PLACEHOLDER}, data_hora = {SQL_PLACEHOLDER}, modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
            """
            execute_update(update_query, (novo_tipo, nova_data_hora, nova_modalidade, novo_projeto, registro_id))

            # Registrar auditoria da correção
            audit_query = f"""
                INSERT INTO auditoria_correcoes 
                (registro_id, gestor, justificativa, data_correcao)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, CURRENT_TIMESTAMP)
            """
            execute_update(audit_query, (registro_id, gestor, justificativa))

            log_security_event("RECORD_CORRECTION", usuario=gestor, context={"registro_id": registro_id, "tipo": novo_tipo})
            return {"success": True, "message": "Registro corrigido com sucesso"}
        except Exception as e:
            log_error("Erro ao corrigir registro", e, {"registro_id": registro_id, "gestor": gestor})
            return {"success": False, "message": f"Erro ao corrigir registro: {str(e)}"}
    else:
        # Fallback original
        conn = get_connection()
        cursor = conn.cursor()

        try:
            # Verificar se o registro existe
            cursor.execute(
                f"SELECT id FROM registros_ponto WHERE id = {SQL_PLACEHOLDER}", (registro_id,))
            if not cursor.fetchone():
                return {"success": False, "message": "Registro não encontrado"}

            # Atualizar registro
            cursor.execute(f"""
                UPDATE registros_ponto 
                SET tipo = {SQL_PLACEHOLDER}, data_hora = {SQL_PLACEHOLDER}, modalidade = {SQL_PLACEHOLDER}, projeto = {SQL_PLACEHOLDER}
                WHERE id = {SQL_PLACEHOLDER}
            """, (novo_tipo, nova_data_hora, nova_modalidade, novo_projeto, registro_id))

            # Registrar auditoria da correção
            cursor.execute(f"""
                INSERT INTO auditoria_correcoes 
                (registro_id, gestor, justificativa, data_correcao)
                VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, CURRENT_TIMESTAMP)
            """, (registro_id, gestor, justificativa))

            conn.commit()
            return {"success": True, "message": "Registro corrigido com sucesso"}
        except Exception as e:
            conn.rollback()
            return {"success": False, "message": f"Erro ao corrigir registro: {str(e)}"}
        finally:
            conn.close()


# Função principal
def main():
    """Função principal que gerencia o estado da aplicação"""
    init_db()
    
    # Garantir que o UploadSystem tenha a estrutura correta da tabela
    try:
        upload_system_init = UploadSystem()
        logger.info("✅ Sistema de uploads inicializado")
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema de uploads: {e}")
    
    # Aplicar migration da tabela uploads se necessário
    try:
        from apply_uploads_migration import apply_uploads_migration
        apply_uploads_migration()
    except Exception as e:
        logger.warning(f"Não foi possível aplicar migration de uploads: {e}")

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
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
main()
