"""Funções de integração do timer de hora extra com Streamlit."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

import streamlit as st

from hora_extra_timer_system import HoraExtraTimerSystem
from notifications import notification_manager


def exibir_button_solicitar_hora_extra(
    usuario: str,
    hora_saida: datetime,
    timer_system: HoraExtraTimerSystem,
) -> bool:
    """Exibe botão para solicitar hora extra se passou da hora de saída."""
    agora = datetime.now()
    
    if agora > hora_saida and not st.session_state.get("hora_extra_ativa", False):
        st.warning("⏰ Você passou do horário de saída. Deseja registrar horas extras?")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Solicitar Horas Extras"):
                st.session_state.hora_extra_ativa = True
                st.session_state.hora_extra_inicio = agora.isoformat()
                st.session_state.hora_extra_timeout = (agora + timedelta(hours=1)).isoformat()
                st.rerun()
        
        return True
    
    return False


def exibir_modal_timer_hora_extra(
    usuario: str,
    timer_system: HoraExtraTimerSystem,
) -> Optional[Dict[str, Any]]:
    """Exibe modal com timer de hora extra em tempo real."""
    if not st.session_state.get("hora_extra_ativa", False):
        return None
    
    inicio_str = st.session_state.get("hora_extra_inicio")
    if not inicio_str:
        return None
    
    inicio = datetime.fromisoformat(inicio_str)
    agora = datetime.now()
    tempo_decorrido = agora - inicio
    
    # Formatar tempo
    horas = int(tempo_decorrido.total_seconds() // 3600)
    minutos = int((tempo_decorrido.total_seconds() % 3600) // 60)
    segundos = int(tempo_decorrido.total_seconds() % 60)
    tempo_formatado = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
    
    st.metric("⏱️ Tempo de Hora Extra", tempo_formatado)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛑 Finalizar Hora Extra"):
            st.session_state.exibir_dialog_justificativa = True
    
    with col2:
        if st.button("❌ Cancelar"):
            st.session_state.hora_extra_ativa = False
            st.session_state.hora_extra_inicio = None
            st.rerun()
    
    return {
        "tempo_decorrido": tempo_decorrido.total_seconds(),
        "tempo_formatado": tempo_formatado,
    }


def exibir_popup_continuar_hora_extra() -> Optional[str]:
    """Exibe popup a cada 1 hora perguntando se deseja continuar."""
    if not st.session_state.get("exibir_popup_hora_extra_expirou", False):
        return None
    
    st.warning("⏱️ Completou-se 1 hora de trabalho extra. Deseja continuar?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Continuar"):
            st.session_state.hora_extra_timeout = (
                datetime.now() + timedelta(hours=1)
            ).isoformat()
            st.session_state.exibir_popup_hora_extra_expirou = False
            st.rerun()
    
    with col2:
        if st.button("⛔ Parar"):
            st.session_state.exibir_dialog_justificativa = True
            st.session_state.exibir_popup_hora_extra_expirou = False
            st.rerun()
    
    return "popup_shown"


def exibir_dialog_justificativa_hora_extra(
    usuario: str,
    gestores: list[str],
) -> Optional[Dict[str, Any]]:
    """Exibe diálogo para justificar e selecionar aprovador."""
    if not st.session_state.get("exibir_dialog_justificativa", False):
        return None
    
    st.info("📝 Por favor, forneça uma justificativa e selecione um aprovador.")
    
    justificativa = st.text_area(
        "Justificativa para horas extras:",
        placeholder="Descreva por que precisou trabalhar além do horário...",
    )
    
    aprovador = st.selectbox(
        "Selecione o aprovador:",
        options=[g for g in gestores if g != usuario],
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Enviar Solicitação"):
            if not justificativa.strip():
                st.error("A justificativa é obrigatória!")
                return None
            
            st.session_state.hora_extra_ativa = False
            st.session_state.hora_extra_inicio = None
            st.session_state.exibir_dialog_justificativa = False
            
            return {
                "justificativa": justificativa,
                "aprovador": aprovador,
                "status": "enviado",
            }
    
    with col2:
        if st.button("❌ Cancelar"):
            st.session_state.exibir_dialog_justificativa = False
            st.rerun()
    
    return None


def exibir_notificacoes_hora_extra_pendente(usuario: str) -> None:
    """Exibe notificações de horas extras pendentes."""
    notificacoes = notification_manager.get_notifications(usuario)
    
    for notif in notificacoes:
        if notif.get("type") == "hora_extra_pendente":
            st.info(f"📢 {notif.get('message', 'Nova notificação')}")


__all__ = [
    "exibir_button_solicitar_hora_extra",
    "exibir_modal_timer_hora_extra",
    "exibir_popup_continuar_hora_extra",
    "exibir_dialog_justificativa_hora_extra",
    "exibir_notificacoes_hora_extra_pendente",
]
