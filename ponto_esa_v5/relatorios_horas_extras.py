"""
Sistema de Relatórios e Gráficos de Horas Extras
Gera visualizações e exporta dados para Excel/PDF
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import logging
import os

# Verificar se usa PostgreSQL e importar o módulo correto
USE_POSTGRESQL = os.getenv('USE_POSTGRESQL', 'false').lower() == 'true'

if USE_POSTGRESQL:
    from database_postgresql import get_connection, SQL_PLACEHOLDER
else:
    from database import get_connection, SQL_PLACEHOLDER

from calculo_horas_system import safe_datetime_parse
from streamlit_utils import safe_download_button

logger = logging.getLogger(__name__)


def relatorios_horas_extras_interface():
    """Interface principal de relatórios de horas extras"""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    ">
        <h2 style="margin: 0; color: white;">📊 Relatórios de Horas Extras</h2>
        <p style="margin: 10px 0;">Análises, gráficos e exportação de dados</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        periodo = st.selectbox(
            "Período",
            ["Último Mês", "Últimos 3 Meses", "Últimos 6 Meses", "Último Ano", "Personalizado"]
        )
    
    if periodo == "Personalizado":
        with col2:
            data_inicio = st.date_input("Data Início", value=date.today() - timedelta(days=90))
        with col3:
            data_fim = st.date_input("Data Fim", value=date.today())
    else:
        dias_dict = {
            "Último Mês": 30,
            "Últimos 3 Meses": 90,
            "Últimos 6 Meses": 180,
            "Último Ano": 365
        }
        dias = dias_dict.get(periodo, 30)
        data_inicio = date.today() - timedelta(days=dias)
        data_fim = date.today()
        
        with col2:
            st.info(f"📅 {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}")
    
    # Buscar dados
    df_horas_extras = carregar_dados_horas_extras(st.session_state.usuario, data_inicio, data_fim)
    
    if df_horas_extras.empty:
        st.warning("📊 Nenhum dado encontrado para o período selecionado")
        return
    
    # Métricas gerais
    st.markdown("### 📈 Métricas Gerais")
    col1, col2, col3, col4 = st.columns(4)
    
    total_horas = df_horas_extras['tempo_minutos'].sum() / 60
    total_solicitacoes = len(df_horas_extras)
    aprovadas = len(df_horas_extras[df_horas_extras['status'].isin(['encerrada', 'aprovado'])])
    rejeitadas = len(df_horas_extras[df_horas_extras['status'].isin(['rejeitada', 'rejeitado'])])
    
    with col1:
        st.metric("⏱️ Total de Horas", f"{total_horas:.1f}h")
    with col2:
        st.metric("📋 Solicitações", total_solicitacoes)
    with col3:
        st.metric("✅ Aprovadas", aprovadas, delta=f"{(aprovadas/total_solicitacoes*100):.0f}%")
    with col4:
        st.metric("❌ Rejeitadas", rejeitadas, delta=f"{(rejeitadas/total_solicitacoes*100):.0f}%")
    
    st.markdown("---")
    
    # Gráficos
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Por Mês", "📈 Por Status", "📅 Por Dia da Semana", "📄 Dados Brutos"])
    
    with tab1:
        st.subheader("📊 Horas Extras por Mês")
        grafico_por_mes(df_horas_extras)
    
    with tab2:
        st.subheader("📈 Distribuição por Status")
        grafico_por_status(df_horas_extras)
    
    with tab3:
        st.subheader("📅 Horas Extras por Dia da Semana")
        grafico_por_dia_semana(df_horas_extras)
    
    with tab4:
        st.subheader("📄 Dados Brutos")
        st.dataframe(df_horas_extras, use_container_width=True)
    
    # Exportação
    st.markdown("---")
    st.markdown("### 💾 Exportar Dados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Exportar para Excel
        excel_data = gerar_excel(df_horas_extras)
        safe_download_button(
            label="📥 Baixar Excel",
            data=excel_data,
            file_name=f"horas_extras_{data_inicio}_{data_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        # Exportar para CSV
        csv_data = df_horas_extras.to_csv(index=False)
        safe_download_button(
            label="📥 Baixar CSV",
            data=csv_data,
            file_name=f"horas_extras_{data_inicio}_{data_fim}.csv",
            mime="text/csv",
            use_container_width=True
        )


def carregar_dados_horas_extras(usuario, data_inicio, data_fim):
    """Carrega dados de horas extras do banco"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar de ambas as tabelas
        query = f"""
            SELECT 
                data_inicio as data,
                hora_inicio,
                hora_fim,
                status,
                tempo_decorrido_minutos as tempo_minutos,
                justificativa,
                aprovador,
                data_criacao
            FROM horas_extras_ativas
            WHERE usuario = {SQL_PLACEHOLDER}
            AND data_inicio BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            
            UNION ALL
            
            SELECT 
                data,
                hora_inicio,
                hora_fim,
                status,
                EXTRACT(EPOCH FROM (
                    CAST(hora_fim AS TIME) - CAST(hora_inicio AS TIME)
                )) / 60 as tempo_minutos,
                justificativa,
                aprovador_solicitado as aprovador,
                data_solicitacao as data_criacao
            FROM solicitacoes_horas_extras
            WHERE usuario = {SQL_PLACEHOLDER}
            AND data BETWEEN {SQL_PLACEHOLDER} AND {SQL_PLACEHOLDER}
            
            ORDER BY data DESC
        """
        
        cursor.execute(query, (usuario, data_inicio, data_fim, usuario, data_inicio, data_fim))
        dados = cursor.fetchall()
        
        if not dados:
            return pd.DataFrame()
        
        # Converter para DataFrame
        df = pd.DataFrame(dados, columns=[
            'data', 'hora_inicio', 'hora_fim', 'status', 
            'tempo_minutos', 'justificativa', 'aprovador', 'data_criacao'
        ])
        
        # Converter data para datetime
        df['data'] = pd.to_datetime(df['data'])
        df['tempo_minutos'] = pd.to_numeric(df['tempo_minutos'], errors='coerce').fillna(0)
        
        return df
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados de horas extras: {str(e)}")
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()


def grafico_por_mes(df):
    """Gera gráfico de horas extras por mês"""
    if df.empty:
        st.info("Sem dados para exibir")
        return
    
    # Agrupar por mês
    df['mes'] = df['data'].dt.to_period('M')
    df_mes = df.groupby('mes').agg({
        'tempo_minutos': 'sum',
        'data': 'count'
    }).reset_index()
    
    df_mes['tempo_horas'] = df_mes['tempo_minutos'] / 60
    df_mes['mes_str'] = df_mes['mes'].astype(str)
    
    # Criar gráfico com Altair
    import altair as alt
    
    chart = alt.Chart(df_mes).mark_bar().encode(
        x=alt.X('mes_str:N', title='Mês'),
        y=alt.Y('tempo_horas:Q', title='Total de Horas'),
        tooltip=['mes_str', 'tempo_horas', alt.Tooltip('data:Q', title='Quantidade')]
    ).properties(
        height=400
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # Tabela resumo
    st.markdown("#### Resumo Mensal")
    df_resumo = df_mes[['mes_str', 'tempo_horas', 'data']].copy()
    df_resumo.columns = ['Mês', 'Total de Horas', 'Quantidade']
    df_resumo['Total de Horas'] = df_resumo['Total de Horas'].round(2)
    st.dataframe(df_resumo, use_container_width=True, hide_index=True)


def grafico_por_status(df):
    """Gera gráfico de distribuição por status"""
    if df.empty:
        st.info("Sem dados para exibir")
        return
    
    # Agrupar por status
    df_status = df.groupby('status').agg({
        'tempo_minutos': 'sum',
        'data': 'count'
    }).reset_index()
    
    df_status['tempo_horas'] = df_status['tempo_minutos'] / 60
    
    # Criar gráfico de pizza
    import altair as alt
    
    chart = alt.Chart(df_status).mark_arc().encode(
        theta=alt.Theta('data:Q', title='Quantidade'),
        color=alt.Color('status:N', title='Status'),
        tooltip=['status', 'data', alt.Tooltip('tempo_horas:Q', title='Total Horas', format='.2f')]
    ).properties(
        height=400
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # Tabela resumo
    st.markdown("#### Resumo por Status")
    df_resumo = df_status[['status', 'tempo_horas', 'data']].copy()
    df_resumo.columns = ['Status', 'Total de Horas', 'Quantidade']
    df_resumo['Total de Horas'] = df_resumo['Total de Horas'].round(2)
    st.dataframe(df_resumo, use_container_width=True, hide_index=True)


def grafico_por_dia_semana(df):
    """Gera gráfico de horas extras por dia da semana"""
    if df.empty:
        st.info("Sem dados para exibir")
        return
    
    # Adicionar dia da semana
    df['dia_semana'] = df['data'].dt.day_name()
    
    # Ordenar dias da semana
    dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dias_pt = {
        'Monday': 'Segunda',
        'Tuesday': 'Terça',
        'Wednesday': 'Quarta',
        'Thursday': 'Quinta',
        'Friday': 'Sexta',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    
    df['dia_semana_pt'] = df['dia_semana'].map(dias_pt)
    
    # Agrupar por dia da semana
    df_dia = df.groupby(['dia_semana', 'dia_semana_pt']).agg({
        'tempo_minutos': 'sum',
        'data': 'count'
    }).reset_index()
    
    df_dia['tempo_horas'] = df_dia['tempo_minutos'] / 60
    
    # Ordenar
    df_dia['ordem'] = df_dia['dia_semana'].map({d: i for i, d in enumerate(dias_ordem)})
    df_dia = df_dia.sort_values('ordem')
    
    # Criar gráfico
    import altair as alt
    
    chart = alt.Chart(df_dia).mark_bar().encode(
        x=alt.X('dia_semana_pt:N', title='Dia da Semana', sort=df_dia['dia_semana_pt'].tolist()),
        y=alt.Y('tempo_horas:Q', title='Total de Horas'),
        tooltip=['dia_semana_pt', 'tempo_horas', alt.Tooltip('data:Q', title='Quantidade')]
    ).properties(
        height=400
    )
    
    st.altair_chart(chart, use_container_width=True)
    
    # Tabela resumo
    st.markdown("#### Resumo por Dia da Semana")
    df_resumo = df_dia[['dia_semana_pt', 'tempo_horas', 'data']].copy()
    df_resumo.columns = ['Dia da Semana', 'Total de Horas', 'Quantidade']
    df_resumo['Total de Horas'] = df_resumo['Total de Horas'].round(2)
    st.dataframe(df_resumo, use_container_width=True, hide_index=True)


def gerar_excel(df):
    """Gera arquivo Excel a partir do DataFrame"""
    from io import BytesIO
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    
    # Criar buffer
    output = BytesIO()
    
    # Escrever DataFrame
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Horas Extras')
        
        # Obter workbook e worksheet
        workbook = writer.book
        worksheet = writer.sheets['Horas Extras']
        
        # Estilizar cabeçalho
        header_fill = PatternFill(start_color="667eea", end_color="667eea", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
        
        # Ajustar largura das colunas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    return output.getvalue()
