"""
Componente Streamlit para Push Notifications
=============================================
Integra o sistema de push notifications com o app Streamlit.
Permite ativar/desativar notificações e configurar preferências.

@author: Pâmella SAR - Expressão Socioambiental
@version: 1.0.0
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Optional, Dict
import json

# Importar sistema de push
try:
    from push_notifications import push_system, salvar_subscription, remover_subscription, obter_subscriptions
except ImportError:
    push_system = None


def render_push_button(usuario: str, key: str = "push_enable") -> None:
    """
    Renderiza botão para ativar notificações push.
    
    Args:
        usuario: Username do usuário logado
        key: Chave única para o componente
    """
    if push_system is None or not push_system.is_ready():
        st.warning("⚠️ Sistema de notificações não configurado")
        return
    
    # JavaScript para ativar push
    js_code = f"""
    <div id="push-container-{key}" style="margin: 10px 0;">
        <button 
            id="push-btn-{key}"
            onclick="handlePushClick_{key}()"
            style="
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
            "
            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(76, 175, 80, 0.4)';"
            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(76, 175, 80, 0.3)';"
        >
            <span style="font-size: 18px;">🔔</span>
            <span>Ativar Notificações</span>
        </button>
        <div id="push-status-{key}" style="margin-top: 8px; font-size: 13px;"></div>
    </div>
    
    <script>
    async function handlePushClick_{key}() {{
        const btn = document.getElementById('push-btn-{key}');
        const status = document.getElementById('push-status-{key}');
        
        // Verificar se PontoESA.Push existe
        if (typeof PontoESA === 'undefined' || !PontoESA.Push) {{
            status.innerHTML = '<span style="color: #f44336;">❌ Sistema de push não carregado</span>';
            return;
        }}
        
        btn.disabled = true;
        btn.innerHTML = '<span style="font-size: 18px;">⏳</span><span>Ativando...</span>';
        
        try {{
            const result = await PontoESA.Push.init('{usuario}');
            
            if (result.success) {{
                status.innerHTML = '<span style="color: #4CAF50;">✅ Notificações ativadas!</span>';
                btn.style.background = 'linear-gradient(135deg, #9E9E9E 0%, #757575 100%)';
                btn.innerHTML = '<span style="font-size: 18px;">✓</span><span>Notificações Ativas</span>';
                btn.onclick = null;
                
                // Enviar teste
                setTimeout(async () => {{
                    try {{
                        await PontoESA.Push.sendTest('{usuario}');
                        status.innerHTML += '<br><span style="color: #2196F3;">📨 Notificação de teste enviada!</span>';
                    }} catch (e) {{
                        console.log('Teste opcional falhou:', e);
                    }}
                }}, 2000);
            }} else {{
                status.innerHTML = '<span style="color: #f44336;">❌ ' + result.error + '</span>';
                btn.disabled = false;
                btn.innerHTML = '<span style="font-size: 18px;">🔔</span><span>Tentar Novamente</span>';
            }}
        }} catch (error) {{
            status.innerHTML = '<span style="color: #f44336;">❌ Erro: ' + error.message + '</span>';
            btn.disabled = false;
            btn.innerHTML = '<span style="font-size: 18px;">🔔</span><span>Tentar Novamente</span>';
        }}
    }}
    
    // Verificar status inicial
    (async function() {{
        await new Promise(r => setTimeout(r, 1000)); // Aguardar scripts carregarem
        
        if (typeof PontoESA !== 'undefined' && PontoESA.Push) {{
            const state = PontoESA.Push.getState();
            const btn = document.getElementById('push-btn-{key}');
            const status = document.getElementById('push-status-{key}');
            
            if (!state.isSupported) {{
                status.innerHTML = '<span style="color: #ff9800;">⚠️ Navegador não suporta notificações push</span>';
                btn.disabled = true;
                btn.style.opacity = '0.5';
            }} else if (state.isSubscribed) {{
                btn.style.background = 'linear-gradient(135deg, #9E9E9E 0%, #757575 100%)';
                btn.innerHTML = '<span style="font-size: 18px;">✓</span><span>Notificações Ativas</span>';
                status.innerHTML = '<span style="color: #4CAF50;">✅ Você já está inscrito</span>';
            }} else if (Notification.permission === 'denied') {{
                status.innerHTML = '<span style="color: #f44336;">❌ Notificações bloqueadas. Habilite nas configurações do navegador.</span>';
                btn.disabled = true;
                btn.style.opacity = '0.5';
            }}
        }}
    }})();
    </script>
    """
    
    components.html(js_code, height=100)


def render_push_config(usuario: str) -> None:
    """
    Renderiza configurações de preferências de push.
    
    Args:
        usuario: Username do usuário
    """
    st.subheader("🔔 Configurações de Notificações")
    
    # Verificar subscriptions existentes
    subscriptions = obter_subscriptions(usuario) if push_system else []
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("##### Status")
        if subscriptions:
            st.success(f"✅ {len(subscriptions)} dispositivo(s) registrado(s)")
        else:
            st.warning("⚠️ Nenhum dispositivo registrado")
        
        # Botão para ativar
        if not subscriptions:
            render_push_button(usuario, "config_push")
    
    with col2:
        st.markdown("##### Tipos de Lembrete")
        
        # Carregar preferências atuais
        prefs = carregar_preferencias_push(usuario)
        
        lembrete_entrada = st.checkbox(
            "Lembrete de entrada",
            value=prefs.get('lembrete_entrada', True),
            help="Notificar quando esquecer de registrar entrada"
        )
        
        lembrete_saida = st.checkbox(
            "Lembrete de saída",
            value=prefs.get('lembrete_saida', True),
            help="Notificar quando esquecer de registrar saída"
        )
        
        lembrete_hora_extra = st.checkbox(
            "Alerta de hora extra",
            value=prefs.get('lembrete_hora_extra', True),
            help="Alertar durante horas extras prolongadas"
        )
        
        if st.button("💾 Salvar Preferências", key="save_push_prefs"):
            salvar_preferencias_push(usuario, {
                'lembrete_entrada': lembrete_entrada,
                'lembrete_saida': lembrete_saida,
                'lembrete_hora_extra': lembrete_hora_extra
            })
            st.success("✅ Preferências salvas!")
            st.rerun()


def carregar_preferencias_push(usuario: str) -> Dict:
    """Carrega preferências de push do banco de dados."""
    try:
        from database import get_connection, SQL_PLACEHOLDER
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT lembrete_entrada, lembrete_saida, lembrete_hora_extra
            FROM config_lembretes_push
            WHERE usuario = {SQL_PLACEHOLDER}
        """, (usuario,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'lembrete_entrada': bool(row[0]),
                'lembrete_saida': bool(row[1]),
                'lembrete_hora_extra': bool(row[2])
            }
        
        return {
            'lembrete_entrada': True,
            'lembrete_saida': True,
            'lembrete_hora_extra': True
        }
        
    except Exception as e:
        print(f"Erro ao carregar preferências: {e}")
        return {
            'lembrete_entrada': True,
            'lembrete_saida': True,
            'lembrete_hora_extra': True
        }


def salvar_preferencias_push(usuario: str, prefs: Dict) -> bool:
    """Salva preferências de push no banco de dados."""
    try:
        from database import get_connection, SQL_PLACEHOLDER
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Usar UPSERT (INSERT ... ON CONFLICT UPDATE para PostgreSQL)
        cursor.execute(f"""
            INSERT INTO config_lembretes_push (usuario, lembrete_entrada, lembrete_saida, lembrete_hora_extra)
            VALUES ({SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER}, {SQL_PLACEHOLDER})
            ON CONFLICT (usuario) DO UPDATE SET
                lembrete_entrada = EXCLUDED.lembrete_entrada,
                lembrete_saida = EXCLUDED.lembrete_saida,
                lembrete_hora_extra = EXCLUDED.lembrete_hora_extra,
                atualizado_em = CURRENT_TIMESTAMP
        """, (
            usuario,
            1 if prefs.get('lembrete_entrada', True) else 0,
            1 if prefs.get('lembrete_saida', True) else 0,
            1 if prefs.get('lembrete_hora_extra', True) else 0
        ))
        
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Erro ao salvar preferências: {e}")
        return False


def render_notification_bell(usuario: str) -> None:
    """
    Renderiza um ícone de sino com badge para notificações.
    Pode ser colocado no header ou sidebar.
    
    Args:
        usuario: Username do usuário
    """
    # Verificar se há notificações não lidas
    count = obter_contagem_notificacoes(usuario)
    
    badge_html = ""
    if count > 0:
        badge_html = f'''
            <span style="
                position: absolute;
                top: -5px;
                right: -5px;
                background: #f44336;
                color: white;
                border-radius: 50%;
                width: 18px;
                height: 18px;
                font-size: 11px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">{count if count < 10 else "9+"}</span>
        '''
    
    html = f'''
    <div style="position: relative; display: inline-block; cursor: pointer;" onclick="toggleNotifications()">
        <span style="font-size: 24px;">🔔</span>
        {badge_html}
    </div>
    '''
    
    st.markdown(html, unsafe_allow_html=True)


def obter_contagem_notificacoes(usuario: str) -> int:
    """Obtém contagem de notificações não lidas (placeholder)."""
    # TODO: Implementar lógica real de contagem
    return 0


# Função de conveniência para adicionar push em qualquer lugar
def add_push_notifications_support(usuario: str) -> None:
    """
    Adiciona suporte a push notifications para o usuário.
    Deve ser chamado após o login.
    
    Args:
        usuario: Username do usuário logado
    """
    # Verificar se já mostrou o prompt de ativação
    if 'push_prompted' not in st.session_state:
        st.session_state.push_prompted = False
    
    # JavaScript para verificar e ativar push automaticamente
    auto_init_js = f"""
    <script>
    (async function() {{
        // Aguardar sistema de push carregar
        await new Promise(resolve => {{
            if (typeof PontoESA !== 'undefined' && PontoESA.Push) {{
                resolve();
            }} else {{
                window.addEventListener('pushReady', resolve, {{ once: true }});
            }}
        }});
        
        const state = PontoESA.Push.getState();
        
        // Se suportado mas não inscrito, mostrar UI de ativação
        if (state.isSupported && !state.isSubscribed && Notification.permission === 'default') {{
            // Mostrar modal após 3 segundos na primeira visita
            const prompted = localStorage.getItem('push_prompted_{usuario}');
            if (!prompted) {{
                setTimeout(() => {{
                    PontoESA.Push.showEnableUI('{usuario}');
                    localStorage.setItem('push_prompted_{usuario}', 'true');
                }}, 3000);
            }}
        }}
    }})();
    </script>
    """
    
    components.html(auto_init_js, height=0)
