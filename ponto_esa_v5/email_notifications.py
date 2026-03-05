"""
Sistema de Notificações por Email - Ponto ExSA
===============================================
Envia notificações por email quando o usuário está offline.
Útil para lembretes de ponto, horas extras pendentes, etc.

Configuração:
- SMTP_HOST: Servidor SMTP (ex: smtp.gmail.com)
- SMTP_PORT: Porta SMTP (ex: 587)
- SMTP_USER: Email de envio
- SMTP_PASSWORD: Senha do email (ou App Password para Gmail)
- EMAIL_FROM_NAME: Nome do remetente

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import os
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURAÇÃO SMTP
# ============================================

SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
EMAIL_FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Ponto ExSA')
EMAIL_FROM = os.getenv('EMAIL_FROM', SMTP_USER)

# URL base do sistema para links nos emails
SYSTEM_URL = os.getenv('SYSTEM_URL', 'https://ponto-exsa.onrender.com')


def is_email_configured() -> bool:
    """Verifica se o email está configurado corretamente."""
    return bool(SMTP_USER and SMTP_PASSWORD and SMTP_HOST)


def get_email_usuario(usuario: str) -> Optional[str]:
    """
    Obtém o email cadastrado de um usuário.
    
    Args:
        usuario: Username do usuário
        
    Returns:
        Email do usuário ou None
    """
    try:
        from database import get_connection, return_connection, SQL_PLACEHOLDER
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            f"SELECT email FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}",
            (usuario,)
        )
        resultado = cursor.fetchone()
        return_connection(conn)
        
        if resultado and resultado[0]:
            return resultado[0]
        return None
        
    except Exception as e:
        logger.error(f"Erro ao obter email do usuário {usuario}: {e}")
        return None


def enviar_email(
    destinatario: str,
    assunto: str,
    corpo_html: str,
    corpo_texto: Optional[str] = None,
    anexos: Optional[List[Dict]] = None
) -> Tuple[bool, str]:
    """
    Envia um email.
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo_html: Corpo do email em HTML
        corpo_texto: Corpo do email em texto puro (opcional)
        anexos: Lista de anexos [{'nome': 'arquivo.pdf', 'dados': bytes}]
        
    Returns:
        Tuple (sucesso, mensagem)
    """
    if not is_email_configured():
        return False, "Sistema de email não configurado"
    
    if not destinatario:
        return False, "Destinatário não informado"
    
    try:
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg['To'] = destinatario
        
        # Adicionar corpo texto (fallback)
        if corpo_texto:
            parte_texto = MIMEText(corpo_texto, 'plain', 'utf-8')
            msg.attach(parte_texto)
        
        # Adicionar corpo HTML
        parte_html = MIMEText(corpo_html, 'html', 'utf-8')
        msg.attach(parte_html)
        
        # Adicionar anexos se houver
        if anexos:
            for anexo in anexos:
                parte = MIMEBase('application', 'octet-stream')
                parte.set_payload(anexo['dados'])
                encoders.encode_base64(parte)
                parte.add_header(
                    'Content-Disposition',
                    f"attachment; filename={anexo['nome']}"
                )
                msg.attach(parte)
        
        # Conectar e enviar - Usar SSL (porta 465) ou TLS (porta 587)
        context = ssl.create_default_context()
        
        if SMTP_PORT == 465:
            # SSL direto (mais confiável em alguns servidores)
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, destinatario, msg.as_string())
        else:
            # STARTTLS (porta 587)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(EMAIL_FROM, destinatario, msg.as_string())
        
        logger.info(f"Email enviado para {destinatario}: {assunto}")
        return True, "Email enviado com sucesso"
        
    except smtplib.SMTPAuthenticationError:
        logger.error("Erro de autenticação SMTP")
        return False, "Erro de autenticação no servidor de email"
    except smtplib.SMTPException as e:
        logger.error(f"Erro SMTP: {e}")
        return False, f"Erro ao enviar email: {str(e)}"
    except OSError as e:
        logger.error(f"Erro de rede ao enviar email: {e}")
        return False, f"Erro: {str(e)}"
    except Exception as e:
        logger.error(f"Erro ao enviar email: {e}")
        return False, f"Erro: {str(e)}"


# ============================================
# TEMPLATES DE EMAIL
# ============================================

def get_template_base(conteudo: str, titulo: str = "Ponto ExSA") -> str:
    """Retorna o template HTML base para emails."""
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titulo}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
        <table cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
            <!-- Header -->
            <tr>
                <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; text-align: center;">
                    <h1 style="color: #00ff9d; margin: 0; font-size: 28px;">⏰ Ponto ExSA</h1>
                    <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 14px;">Sistema de Controle de Ponto</p>
                </td>
            </tr>
            
            <!-- Conteúdo -->
            <tr>
                <td style="padding: 30px;">
                    {conteudo}
                </td>
            </tr>
            
            <!-- Footer -->
            <tr>
                <td style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #dee2e6;">
                    <p style="color: #6c757d; margin: 0; font-size: 12px;">
                        Este é um email automático do sistema Ponto ExSA.
                    </p>
                    <p style="color: #6c757d; margin: 10px 0 0 0; font-size: 12px;">
                        <a href="{SYSTEM_URL}" style="color: #007bff; text-decoration: none;">Acessar Sistema</a>
                    </p>
                    <p style="color: #adb5bd; margin: 15px 0 0 0; font-size: 11px;">
                        Expressão Socioambiental Pesquisa e Projetos
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def template_lembrete_entrada(nome_usuario: str) -> Tuple[str, str]:
    """Template para lembrete de entrada."""
    assunto = "⏰ Lembrete: Registre sua entrada de hoje"
    
    conteudo = f"""
    <h2 style="color: #1a1a2e; margin: 0 0 20px 0;">Bom dia, {nome_usuario}!</h2>
    
    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin-bottom: 20px;">
        <p style="color: #856404; margin: 0; font-weight: bold;">
            ⚠️ Você ainda não registrou sua entrada hoje
        </p>
    </div>
    
    <p style="color: #495057; line-height: 1.6;">
        Não esqueça de registrar seu ponto de entrada para manter seus registros em dia.
    </p>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="{SYSTEM_URL}" style="background: linear-gradient(135deg, #00ff9d 0%, #00d68f 100%); color: #1a1a2e; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            📱 Registrar Ponto Agora
        </a>
    </div>
    
    <p style="color: #6c757d; font-size: 13px; margin-top: 30px;">
        Data: {datetime.now().strftime('%d/%m/%Y')}
    </p>
    """
    
    html = get_template_base(conteudo, "Lembrete de Entrada - Ponto ExSA")
    return assunto, html


def template_lembrete_saida(nome_usuario: str) -> Tuple[str, str]:
    """Template para lembrete de saída."""
    assunto = "🏠 Lembrete: Não esqueça de registrar sua saída"
    
    conteudo = f"""
    <h2 style="color: #1a1a2e; margin: 0 0 20px 0;">Boa tarde, {nome_usuario}!</h2>
    
    <div style="background-color: #d1ecf1; border-left: 4px solid #17a2b8; padding: 15px; margin-bottom: 20px;">
        <p style="color: #0c5460; margin: 0; font-weight: bold;">
            🏠 Hora de encerrar o expediente
        </p>
    </div>
    
    <p style="color: #495057; line-height: 1.6;">
        Seu horário de saída previsto já passou. Não esqueça de registrar sua saída!
    </p>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="{SYSTEM_URL}" style="background: linear-gradient(135deg, #17a2b8 0%, #138496 100%); color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            📱 Registrar Saída Agora
        </a>
    </div>
    
    <p style="color: #6c757d; font-size: 13px; margin-top: 30px;">
        Data: {datetime.now().strftime('%d/%m/%Y')}
    </p>
    """
    
    html = get_template_base(conteudo, "Lembrete de Saída - Ponto ExSA")
    return assunto, html


def template_hora_extra_prolongada(nome_usuario: str, minutos: int) -> Tuple[str, str]:
    """Template para alerta de hora extra prolongada."""
    horas = minutos // 60
    mins = minutos % 60
    tempo_str = f"{horas}h{mins}min" if horas > 0 else f"{mins}min"
    
    assunto = f"⚠️ Alerta: Hora Extra em andamento há {tempo_str}"
    
    conteudo = f"""
    <h2 style="color: #1a1a2e; margin: 0 0 20px 0;">Atenção, {nome_usuario}!</h2>
    
    <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin-bottom: 20px;">
        <p style="color: #721c24; margin: 0; font-weight: bold;">
            ⚠️ Você está em hora extra há {tempo_str}
        </p>
    </div>
    
    <p style="color: #495057; line-height: 1.6;">
        Lembre-se dos limites diários de hora extra estabelecidos pela empresa.
        Se necessário, finalize suas atividades e registre a saída.
    </p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <p style="color: #495057; margin: 0;">
            <strong>Tempo em HE:</strong> {tempo_str}<br>
            <strong>Horário atual:</strong> {datetime.now().strftime('%H:%M')}
        </p>
    </div>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="{SYSTEM_URL}" style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            📱 Acessar Sistema
        </a>
    </div>
    """
    
    html = get_template_base(conteudo, "Alerta de Hora Extra - Ponto ExSA")
    return assunto, html


def template_solicitacoes_pendentes_gestor(nome_gestor: str, resumo: Dict) -> Tuple[str, str]:
    """Template para resumo de solicitações pendentes para gestores."""
    total = sum(resumo.values())
    
    assunto = f"📋 Você tem {total} solicitação(ões) pendente(s) para aprovar"
    
    # Montar lista de pendências
    lista_pendencias = ""
    if resumo.get('horas_extras', 0) > 0:
        lista_pendencias += f"<li>🕐 Horas Extras: <strong>{resumo['horas_extras']}</strong></li>"
    if resumo.get('correcoes', 0) > 0:
        lista_pendencias += f"<li>✏️ Correções de Registro: <strong>{resumo['correcoes']}</strong></li>"
    if resumo.get('atestados', 0) > 0:
        lista_pendencias += f"<li>🏥 Atestados: <strong>{resumo['atestados']}</strong></li>"
    if resumo.get('ajustes', 0) > 0:
        lista_pendencias += f"<li>🔧 Ajustes de Ponto: <strong>{resumo['ajustes']}</strong></li>"
    
    conteudo = f"""
    <h2 style="color: #1a1a2e; margin: 0 0 20px 0;">Olá, {nome_gestor}!</h2>
    
    <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin-bottom: 20px;">
        <p style="color: #155724; margin: 0; font-weight: bold;">
            📋 Resumo de Solicitações Pendentes
        </p>
    </div>
    
    <p style="color: #495057; line-height: 1.6;">
        Você tem <strong>{total} solicitação(ões)</strong> aguardando sua aprovação:
    </p>
    
    <ul style="color: #495057; line-height: 2;">
        {lista_pendencias}
    </ul>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="{SYSTEM_URL}" style="background: linear-gradient(135deg, #28a745 0%, #218838 100%); color: #ffffff; padding: 15px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
            📱 Revisar Solicitações
        </a>
    </div>
    
    <p style="color: #6c757d; font-size: 13px; margin-top: 30px;">
        Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
    </p>
    """
    
    html = get_template_base(conteudo, "Solicitações Pendentes - Ponto ExSA")
    return assunto, html


def template_solicitacao_aprovada(nome_usuario: str, tipo: str, detalhes: str) -> Tuple[str, str]:
    """Template para notificação de solicitação aprovada."""
    assunto = f"✅ Sua solicitação de {tipo} foi aprovada!"
    
    conteudo = f"""
    <h2 style="color: #1a1a2e; margin: 0 0 20px 0;">Parabéns, {nome_usuario}!</h2>
    
    <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin-bottom: 20px;">
        <p style="color: #155724; margin: 0; font-weight: bold;">
            ✅ Sua solicitação foi APROVADA
        </p>
    </div>
    
    <p style="color: #495057; line-height: 1.6;">
        Sua solicitação de <strong>{tipo}</strong> foi aprovada pelo gestor.
    </p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <p style="color: #495057; margin: 0;">
            <strong>Detalhes:</strong><br>
            {detalhes}
        </p>
    </div>
    
    <p style="color: #6c757d; font-size: 13px; margin-top: 30px;">
        Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
    </p>
    """
    
    html = get_template_base(conteudo, "Solicitação Aprovada - Ponto ExSA")
    return assunto, html


def template_solicitacao_rejeitada(nome_usuario: str, tipo: str, motivo: str) -> Tuple[str, str]:
    """Template para notificação de solicitação rejeitada."""
    assunto = f"❌ Sua solicitação de {tipo} não foi aprovada"
    
    conteudo = f"""
    <h2 style="color: #1a1a2e; margin: 0 0 20px 0;">Olá, {nome_usuario}</h2>
    
    <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin-bottom: 20px;">
        <p style="color: #721c24; margin: 0; font-weight: bold;">
            ❌ Sua solicitação não foi aprovada
        </p>
    </div>
    
    <p style="color: #495057; line-height: 1.6;">
        Infelizmente sua solicitação de <strong>{tipo}</strong> não foi aprovada.
    </p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
        <p style="color: #495057; margin: 0;">
            <strong>Motivo:</strong><br>
            {motivo}
        </p>
    </div>
    
    <p style="color: #495057; line-height: 1.6;">
        Se tiver dúvidas, entre em contato com seu gestor.
    </p>
    
    <p style="color: #6c757d; font-size: 13px; margin-top: 30px;">
        Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}
    </p>
    """
    
    html = get_template_base(conteudo, "Solicitação Não Aprovada - Ponto ExSA")
    return assunto, html


# ============================================
# FUNÇÕES DE ENVIO DE NOTIFICAÇÃO
# ============================================

def notificar_lembrete_entrada_email(usuario: str) -> Tuple[bool, str]:
    """Envia lembrete de entrada por email."""
    email = get_email_usuario(usuario)
    if not email:
        return False, "Usuário não possui email cadastrado"
    
    # Buscar nome do usuário
    nome = usuario
    try:
        from database import get_connection, return_connection, SQL_PLACEHOLDER
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (usuario,))
        resultado = cursor.fetchone()
        if resultado and resultado[0]:
            nome = resultado[0].split()[0]  # Primeiro nome
        return_connection(conn)
    except Exception as e:
        logger.debug(f"Falha ao buscar nome para lembrete de entrada: {e}")
    
    assunto, html = template_lembrete_entrada(nome)
    return enviar_email(email, assunto, html)


def notificar_lembrete_saida_email(usuario: str) -> Tuple[bool, str]:
    """Envia lembrete de saída por email."""
    email = get_email_usuario(usuario)
    if not email:
        return False, "Usuário não possui email cadastrado"
    
    # Buscar nome do usuário
    nome = usuario
    try:
        from database import get_connection, return_connection, SQL_PLACEHOLDER
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (usuario,))
        resultado = cursor.fetchone()
        if resultado and resultado[0]:
            nome = resultado[0].split()[0]
        return_connection(conn)
    except Exception as e:
        logger.debug(f"Falha ao buscar nome para lembrete de saída: {e}")
    
    assunto, html = template_lembrete_saida(nome)
    return enviar_email(email, assunto, html)


def notificar_hora_extra_email(usuario: str, minutos: int) -> Tuple[bool, str]:
    """Envia alerta de hora extra prolongada por email."""
    email = get_email_usuario(usuario)
    if not email:
        return False, "Usuário não possui email cadastrado"
    
    # Buscar nome do usuário
    nome = usuario
    try:
        from database import get_connection, return_connection, SQL_PLACEHOLDER
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (usuario,))
        resultado = cursor.fetchone()
        if resultado and resultado[0]:
            nome = resultado[0].split()[0]
        return_connection(conn)
    except Exception as e:
        logger.debug(f"Falha ao buscar nome para alerta de hora extra: {e}")
    
    assunto, html = template_hora_extra_prolongada(nome, minutos)
    return enviar_email(email, assunto, html)


def notificar_gestor_pendencias_email(gestor: str, resumo: Dict) -> Tuple[bool, str]:
    """Envia resumo de pendências para gestor por email."""
    email = get_email_usuario(gestor)
    if not email:
        return False, "Gestor não possui email cadastrado"
    
    if sum(resumo.values()) == 0:
        return False, "Não há pendências para notificar"
    
    # Buscar nome do gestor
    nome = gestor
    try:
        from database import get_connection, return_connection, SQL_PLACEHOLDER
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (gestor,))
        resultado = cursor.fetchone()
        if resultado and resultado[0]:
            nome = resultado[0].split()[0]
        return_connection(conn)
    except Exception as e:
        logger.debug(f"Falha ao buscar nome do gestor para pendências: {e}")
    
    assunto, html = template_solicitacoes_pendentes_gestor(nome, resumo)
    return enviar_email(email, assunto, html)


def notificar_aprovacao_email(usuario: str, tipo: str, detalhes: str) -> Tuple[bool, str]:
    """Envia notificação de aprovação por email."""
    email = get_email_usuario(usuario)
    if not email:
        return False, "Usuário não possui email cadastrado"
    
    nome = usuario
    try:
        from database import get_connection, return_connection, SQL_PLACEHOLDER
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (usuario,))
        resultado = cursor.fetchone()
        if resultado and resultado[0]:
            nome = resultado[0].split()[0]
        return_connection(conn)
    except Exception as e:
        logger.debug(f"Falha ao buscar nome para notificação de aprovação: {e}")
    
    assunto, html = template_solicitacao_aprovada(nome, tipo, detalhes)
    return enviar_email(email, assunto, html)


def notificar_rejeicao_email(usuario: str, tipo: str, motivo: str) -> Tuple[bool, str]:
    """Envia notificação de rejeição por email."""
    email = get_email_usuario(usuario)
    if not email:
        return False, "Usuário não possui email cadastrado"
    
    nome = usuario
    try:
        from database import get_connection, return_connection, SQL_PLACEHOLDER
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT nome_completo FROM usuarios WHERE usuario = {SQL_PLACEHOLDER}", (usuario,))
        resultado = cursor.fetchone()
        if resultado and resultado[0]:
            nome = resultado[0].split()[0]
        return_connection(conn)
    except Exception as e:
        logger.debug(f"Falha ao buscar nome para notificação de rejeição: {e}")
    
    assunto, html = template_solicitacao_rejeitada(nome, tipo, motivo)
    return enviar_email(email, assunto, html)


# ============================================
# CLASSE PRINCIPAL
# ============================================

class EmailNotificationSystem:
    """Sistema unificado de notificações por email."""
    
    def __init__(self):
        self.configured = is_email_configured()
        
    def is_ready(self) -> bool:
        return self.configured
    
    def lembrete_entrada(self, usuario: str) -> Tuple[bool, str]:
        return notificar_lembrete_entrada_email(usuario)
    
    def lembrete_saida(self, usuario: str) -> Tuple[bool, str]:
        return notificar_lembrete_saida_email(usuario)
    
    def alerta_hora_extra(self, usuario: str, minutos: int) -> Tuple[bool, str]:
        return notificar_hora_extra_email(usuario, minutos)
    
    def pendencias_gestor(self, gestor: str, resumo: Dict) -> Tuple[bool, str]:
        return notificar_gestor_pendencias_email(gestor, resumo)
    
    def aprovacao(self, usuario: str, tipo: str, detalhes: str) -> Tuple[bool, str]:
        return notificar_aprovacao_email(usuario, tipo, detalhes)
    
    def rejeicao(self, usuario: str, tipo: str, motivo: str) -> Tuple[bool, str]:
        return notificar_rejeicao_email(usuario, tipo, motivo)


# Instância global
email_system = EmailNotificationSystem()


__all__ = [
    'email_system',
    'EmailNotificationSystem',
    'is_email_configured',
    'enviar_email',
    'notificar_lembrete_entrada_email',
    'notificar_lembrete_saida_email',
    'notificar_hora_extra_email',
    'notificar_gestor_pendencias_email',
    'notificar_aprovacao_email',
    'notificar_rejeicao_email'
]
