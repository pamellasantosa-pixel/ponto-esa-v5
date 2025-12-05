"""
Dashboard com Gráficos Avançados para Ponto ExSA v5.0
Visualizações bonitas com Plotly
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Cores do tema
THEME_COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'info': '#17a2b8',
    'light': '#f8f9fa',
    'dark': '#343a40',
    'gradient': ['#667eea', '#764ba2', '#f093fb', '#f5576c'],
    'chart_colors': ['#667eea', '#28a745', '#ffc107', '#dc3545', '#17a2b8', '#6c757d', '#fd7e14', '#20c997']
}


def create_gauge_chart(value: float, max_value: float, title: str, 
                       suffix: str = "", color_ranges: List[Dict] = None) -> go.Figure:
    """Cria um gráfico de gauge/velocímetro"""
    
    if color_ranges is None:
        color_ranges = [
            {'range': [0, max_value * 0.33], 'color': THEME_COLORS['success']},
            {'range': [max_value * 0.33, max_value * 0.66], 'color': THEME_COLORS['warning']},
            {'range': [max_value * 0.66, max_value], 'color': THEME_COLORS['danger']}
        ]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16, 'color': THEME_COLORS['dark']}},
        number={'suffix': suffix, 'font': {'size': 24}},
        gauge={
            'axis': {'range': [None, max_value], 'tickwidth': 1, 'tickcolor': THEME_COLORS['dark']},
            'bar': {'color': THEME_COLORS['primary']},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': THEME_COLORS['light'],
            'steps': color_ranges,
            'threshold': {
                'line': {'color': THEME_COLORS['danger'], 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': THEME_COLORS['dark']}
    )
    
    return fig


def create_donut_chart(labels: List[str], values: List[float], 
                       title: str, colors: List[str] = None) -> go.Figure:
    """Cria um gráfico de rosca (donut)"""
    
    if colors is None:
        colors = THEME_COLORS['chart_colors'][:len(labels)]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker_colors=colors,
        textinfo='label+percent',
        textposition='outside',
        textfont_size=12,
        pull=[0.05 if i == 0 else 0 for i in range(len(labels))]
    )])
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': THEME_COLORS['dark']}
        },
        height=350,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=60, b=60),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_bar_chart(x_data: List, y_data: List, title: str, 
                     x_label: str = "", y_label: str = "",
                     horizontal: bool = False, 
                     color_scale: str = None) -> go.Figure:
    """Cria um gráfico de barras com gradiente"""
    
    if horizontal:
        fig = go.Figure(go.Bar(
            y=x_data,
            x=y_data,
            orientation='h',
            marker=dict(
                color=y_data,
                colorscale='Viridis' if color_scale is None else color_scale,
                showscale=False
            ),
            text=y_data,
            textposition='outside'
        ))
    else:
        fig = go.Figure(go.Bar(
            x=x_data,
            y=y_data,
            marker=dict(
                color=y_data,
                colorscale='Viridis' if color_scale is None else color_scale,
                showscale=False
            ),
            text=y_data,
            textposition='outside'
        ))
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': THEME_COLORS['dark']}
        },
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=400,
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    
    return fig


def create_line_chart(x_data: List, y_data: List, title: str,
                      x_label: str = "", y_label: str = "",
                      fill: bool = True) -> go.Figure:
    """Cria um gráfico de linha com área preenchida"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode='lines+markers',
        name='Valor',
        line=dict(color=THEME_COLORS['primary'], width=3),
        marker=dict(size=8, color=THEME_COLORS['primary']),
        fill='tozeroy' if fill else None,
        fillcolor='rgba(102, 126, 234, 0.2)'
    ))
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': THEME_COLORS['dark']}
        },
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=350,
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    
    return fig


def create_multi_line_chart(x_data: List, y_data_dict: Dict[str, List],
                            title: str, x_label: str = "", y_label: str = "") -> go.Figure:
    """Cria gráfico de múltiplas linhas"""
    
    fig = go.Figure()
    colors = THEME_COLORS['chart_colors']
    
    for i, (name, y_values) in enumerate(y_data_dict.items()):
        fig.add_trace(go.Scatter(
            x=x_data,
            y=y_values,
            mode='lines+markers',
            name=name,
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=6, color=colors[i % len(colors)])
        ))
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': THEME_COLORS['dark']}
        },
        xaxis_title=x_label,
        yaxis_title=y_label,
        height=400,
        margin=dict(l=50, r=50, t=60, b=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)')
    
    return fig


def create_heatmap(data: List[List], x_labels: List[str], y_labels: List[str],
                   title: str, colorscale: str = 'Blues') -> go.Figure:
    """Cria um mapa de calor"""
    
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=x_labels,
        y=y_labels,
        colorscale=colorscale,
        showscale=True,
        text=data,
        texttemplate="%{text}",
        textfont={"size": 12},
        hoverongaps=False
    ))
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': THEME_COLORS['dark']}
        },
        height=400,
        margin=dict(l=80, r=50, t=60, b=50),
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def create_card_metric(label: str, value: Any, delta: Optional[float] = None,
                       icon: str = "📊", color: str = "primary") -> str:
    """Cria um card de métrica estilizado (HTML)"""
    
    color_value = THEME_COLORS.get(color, THEME_COLORS['primary'])
    
    delta_html = ""
    if delta is not None:
        delta_color = THEME_COLORS['success'] if delta >= 0 else THEME_COLORS['danger']
        delta_icon = "↑" if delta >= 0 else "↓"
        delta_html = f'<span style="color: {delta_color}; font-size: 14px;">{delta_icon} {abs(delta):.1f}%</span>'
    
    return f"""
    <div style="
        background: linear-gradient(135deg, {color_value}22, {color_value}11);
        border-left: 4px solid {color_value};
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <p style="color: #666; margin: 0; font-size: 14px;">{label}</p>
                <h2 style="margin: 5px 0; color: {color_value};">{value}</h2>
                {delta_html}
            </div>
            <span style="font-size: 40px;">{icon}</span>
        </div>
    </div>
    """


def create_progress_bar(value: float, max_value: float, label: str,
                        color: str = "primary") -> str:
    """Cria uma barra de progresso estilizada (HTML)"""
    
    percentage = min(100, (value / max_value) * 100) if max_value > 0 else 0
    color_value = THEME_COLORS.get(color, THEME_COLORS['primary'])
    
    return f"""
    <div style="margin: 15px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-weight: 500;">{label}</span>
            <span style="color: {color_value};">{value:.1f}/{max_value:.1f}</span>
        </div>
        <div style="
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
        ">
            <div style="
                background: linear-gradient(90deg, {color_value}, {color_value}cc);
                width: {percentage}%;
                height: 100%;
                border-radius: 10px;
                transition: width 0.5s ease;
            "></div>
        </div>
    </div>
    """


def create_timeline_chart(events: List[Dict], title: str) -> go.Figure:
    """Cria um gráfico de timeline/cronograma"""
    
    if not events:
        return None
    
    df = pd.DataFrame(events)
    
    fig = px.timeline(
        df,
        x_start="inicio",
        x_end="fim",
        y="usuario",
        color="tipo",
        title=title,
        color_discrete_sequence=THEME_COLORS['chart_colors']
    )
    
    fig.update_layout(
        height=max(300, len(set(df['usuario'])) * 50),
        margin=dict(l=100, r=50, t=60, b=50),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Horário",
        yaxis_title="Funcionário"
    )
    
    return fig


def render_dashboard_executivo(dados: Dict[str, Any]):
    """Renderiza o dashboard executivo completo"""
    
    st.markdown("""
    <style>
    .dashboard-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        text-align: center;
    }
    .metric-row {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
    }
    .chart-container {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
    <div class="dashboard-header">
        <h1>📊 Dashboard Executivo</h1>
        <p>Atualizado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # KPIs principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(create_card_metric(
            "Funcionários Ativos",
            dados.get('total_usuarios', 0),
            icon="👥",
            color="primary"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_card_metric(
            "Registros Hoje",
            dados.get('registros_hoje', 0),
            delta=dados.get('delta_registros'),
            icon="📝",
            color="success"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_card_metric(
            "Pendências",
            dados.get('pendencias_total', 0),
            icon="⏳",
            color="warning"
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(create_card_metric(
            "Horas Extras (mês)",
            f"{dados.get('horas_extras_mes', 0):.1f}h",
            icon="⏰",
            color="info"
        ), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráficos principais
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de rosca - Status de presença
        if 'status_presenca' in dados and dados['status_presenca']:
            fig = create_donut_chart(
                labels=list(dados['status_presenca'].keys()),
                values=list(dados['status_presenca'].values()),
                title="📍 Status de Presença Hoje",
                colors=[THEME_COLORS['success'], THEME_COLORS['warning'], THEME_COLORS['danger']]
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Gauge de pontualidade
        pontualidade = dados.get('pontualidade_media', 85)
        fig = create_gauge_chart(
            value=pontualidade,
            max_value=100,
            title="⏱️ Taxa de Pontualidade",
            suffix="%",
            color_ranges=[
                {'range': [0, 60], 'color': THEME_COLORS['danger']},
                {'range': [60, 80], 'color': THEME_COLORS['warning']},
                {'range': [80, 100], 'color': THEME_COLORS['success']}
            ]
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Gráfico de registros por dia (últimos 7 dias)
    if 'registros_semana' in dados and dados['registros_semana']:
        fig = create_line_chart(
            x_data=dados['registros_semana']['datas'],
            y_data=dados['registros_semana']['valores'],
            title="📈 Registros de Ponto - Últimos 7 Dias",
            x_label="Data",
            y_label="Registros",
            fill=True
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap de horários
    col1, col2 = st.columns(2)
    
    with col1:
        if 'horas_extras_por_dept' in dados and dados['horas_extras_por_dept']:
            fig = create_bar_chart(
                x_data=list(dados['horas_extras_por_dept'].keys()),
                y_data=list(dados['horas_extras_por_dept'].values()),
                title="🕐 Horas Extras por Departamento",
                x_label="Departamento",
                y_label="Horas",
                color_scale="Plasma"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'ausencias_tipo' in dados and dados['ausencias_tipo']:
            fig = create_donut_chart(
                labels=list(dados['ausencias_tipo'].keys()),
                values=list(dados['ausencias_tipo'].values()),
                title="🏥 Ausências por Tipo (Mês)"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Barra de progresso para metas
    st.markdown("### 🎯 Metas do Mês")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(create_progress_bar(
            value=dados.get('dias_trabalhados', 0),
            max_value=dados.get('dias_uteis_mes', 22),
            label="Dias Trabalhados",
            color="success"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_progress_bar(
            value=dados.get('atestados_aprovados', 0),
            max_value=dados.get('atestados_total', 1),
            label="Atestados Aprovados",
            color="info"
        ), unsafe_allow_html=True)


def get_dashboard_data_from_db(execute_query_func) -> Dict[str, Any]:
    """Obtém dados do banco para o dashboard"""
    
    dados = {
        'total_usuarios': 0,
        'registros_hoje': 0,
        'pendencias_total': 0,
        'horas_extras_mes': 0,
        'status_presenca': {},
        'pontualidade_media': 85,
        'registros_semana': {'datas': [], 'valores': []},
        'horas_extras_por_dept': {},
        'ausencias_tipo': {},
        'dias_trabalhados': 0,
        'dias_uteis_mes': 22,
        'atestados_aprovados': 0,
        'atestados_total': 0
    }
    
    hoje = date.today().strftime("%Y-%m-%d")
    
    try:
        # Total de usuários
        result = execute_query_func(
            "SELECT COUNT(*) FROM usuarios WHERE ativo = 1 AND tipo = 'funcionario'",
            fetch_one=True
        )
        if result:
            dados['total_usuarios'] = result[0]
        
        # Registros hoje
        result = execute_query_func(
            "SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = %s",
            (hoje,), fetch_one=True
        )
        if result:
            dados['registros_hoje'] = result[0]
        
        # Pendências (ausências + horas extras pendentes)
        result = execute_query_func(
            "SELECT COUNT(*) FROM ausencias WHERE status = 'pendente'",
            fetch_one=True
        )
        ausencias_pend = result[0] if result else 0
        
        result = execute_query_func(
            "SELECT COUNT(*) FROM solicitacoes_horas_extras WHERE status = 'pendente'",
            fetch_one=True
        )
        he_pend = result[0] if result else 0
        dados['pendencias_total'] = ausencias_pend + he_pend
        
        # Status de presença hoje
        result = execute_query_func(
            """SELECT COUNT(DISTINCT usuario_id) FROM registros_ponto 
               WHERE DATE(data_hora) = %s""",
            (hoje,), fetch_one=True
        )
        presentes = result[0] if result else 0
        ausentes = max(0, dados['total_usuarios'] - presentes)
        dados['status_presenca'] = {
            'Presentes': presentes,
            'Ausentes': ausentes
        }
        
        # Registros últimos 7 dias
        datas = []
        valores = []
        for i in range(6, -1, -1):
            data = (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
            result = execute_query_func(
                "SELECT COUNT(*) FROM registros_ponto WHERE DATE(data_hora) = %s",
                (data,), fetch_one=True
            )
            datas.append((date.today() - timedelta(days=i)).strftime("%d/%m"))
            valores.append(result[0] if result else 0)
        
        dados['registros_semana'] = {'datas': datas, 'valores': valores}
        
        # Ausências por tipo no mês
        primeiro_dia_mes = date.today().replace(day=1).strftime("%Y-%m-%d")
        result = execute_query_func(
            """SELECT tipo, COUNT(*) as total FROM ausencias 
               WHERE data_inicio >= %s 
               GROUP BY tipo""",
            (primeiro_dia_mes,), fetch_all=True
        )
        if result:
            for row in result:
                dados['ausencias_tipo'][row[0]] = row[1]
        
        # Atestados do mês
        result = execute_query_func(
            """SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'aprovado' THEN 1 ELSE 0 END) as aprovados
               FROM ausencias 
               WHERE data_inicio >= %s AND tipo LIKE '%%Atestado%%'""",
            (primeiro_dia_mes,), fetch_one=True
        )
        if result:
            dados['atestados_total'] = result[0] or 0
            dados['atestados_aprovados'] = result[1] or 0
        
    except Exception as e:
        logger.error(f"Erro ao obter dados do dashboard: {e}")
    
    return dados


def render_mini_dashboard(dados: Dict[str, Any]):
    """Renderiza versão compacta do dashboard para telas menores"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("👥 Funcionários", dados.get('total_usuarios', 0))
        st.metric("📝 Registros Hoje", dados.get('registros_hoje', 0))
    
    with col2:
        st.metric("⏳ Pendências", dados.get('pendencias_total', 0))
        st.metric("⏰ H.E. Mês", f"{dados.get('horas_extras_mes', 0):.1f}h")
    
    # Mini gráfico de rosca
    if dados.get('status_presenca'):
        fig = create_donut_chart(
            labels=list(dados['status_presenca'].keys()),
            values=list(dados['status_presenca'].values()),
            title="Status Hoje",
            colors=[THEME_COLORS['success'], THEME_COLORS['danger']]
        )
        fig.update_layout(height=250)
        st.plotly_chart(fig, use_container_width=True)


def render_funcionario_dashboard(dados: Dict[str, Any], usuario: str):
    """Dashboard pessoal do funcionário"""
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 20px;
    ">
        <h2>👋 Bem-vindo(a), {usuario}!</h2>
        <p>{datetime.now().strftime('%A, %d de %B de %Y')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(create_card_metric(
            "Saldo Banco de Horas",
            dados.get('saldo_banco_horas', "0h"),
            icon="🏦",
            color="primary"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(create_card_metric(
            "Dias Trabalhados (mês)",
            dados.get('dias_trabalhados', 0),
            icon="📅",
            color="success"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(create_card_metric(
            "Horas Extras (mês)",
            f"{dados.get('horas_extras', 0):.1f}h",
            icon="⏰",
            color="info"
        ), unsafe_allow_html=True)
    
    # Gráfico de horas trabalhadas na semana
    if 'horas_semana' in dados and dados['horas_semana']:
        fig = create_bar_chart(
            x_data=dados['horas_semana']['dias'],
            y_data=dados['horas_semana']['horas'],
            title="📊 Horas Trabalhadas esta Semana",
            x_label="Dia",
            y_label="Horas",
            color_scale="Tealgrn"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Próximas ausências programadas
    if dados.get('proximas_ausencias'):
        st.markdown("### 📋 Próximas Ausências Programadas")
        for ausencia in dados['proximas_ausencias'][:3]:
            st.info(f"📅 {ausencia['data']}: {ausencia['tipo']}")


# Teste local
if __name__ == "__main__":
    st.set_page_config(page_title="Dashboard Test", layout="wide")
    
    # Dados de teste
    dados_teste = {
        'total_usuarios': 45,
        'registros_hoje': 128,
        'pendencias_total': 7,
        'horas_extras_mes': 156.5,
        'status_presenca': {'Presentes': 38, 'Ausentes': 7},
        'pontualidade_media': 87,
        'registros_semana': {
            'datas': ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
            'valores': [150, 145, 160, 155, 140, 45, 20]
        },
        'horas_extras_por_dept': {
            'TI': 45.5,
            'RH': 12.0,
            'Vendas': 78.3,
            'Operações': 20.7
        },
        'ausencias_tipo': {
            'Atestado Médico': 8,
            'Férias': 3,
            'Licença': 2,
            'Falta Justificada': 4
        },
        'dias_trabalhados': 15,
        'dias_uteis_mes': 22,
        'atestados_aprovados': 6,
        'atestados_total': 8
    }
    
    render_dashboard_executivo(dados_teste)
