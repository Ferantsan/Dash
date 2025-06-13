import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import io

# Required libraries: streamlit, pandas, numpy, plotly, openpyxl

st.set_page_config(
    page_title="Dashboard de Custo Caixa – Global Eggs e Subsidiárias",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and header
st.title("🥚 Dashboard de Custo Caixa – Global Eggs e Subsidiárias")
st.markdown("---")

@st.cache_data
def load_and_process_data(uploaded_file):
    """Load and process the Excel data"""
    try:
        # Read the Excel file
        df = pd.read_excel(uploaded_file, sheet_name='Base')
        
        # Get month columns (everything except first 3 columns)
        month_cols = [col for col in df.columns if '/' in str(col)]
        
        # Melt the dataframe to long format
        df_melted = df.melt(
            id_vars=['Empresa', 'Tipo de Caixa', 'Item'],
            value_vars=month_cols,
            var_name='Data',
            value_name='Valor'
        )
        
        # Convert Data to proper datetime (first day of each month)
        def convert_date(date_str):
            try:
                month, year = date_str.split('/')
                month_map = {
                    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
                }
                return datetime(2000 + int(year), month_map[month], 1)
            except:
                return None
        
        df_melted['Data'] = df_melted['Data'].apply(convert_date)
        df_melted = df_melted.dropna(subset=['Data'])
        
        # Filter for cost items (starts with "Custo" or is exactly "Custo Caixa EBT")
        cost_items = df_melted[
            (df_melted['Item'].str.startswith('Custo', na=False)) |
            (df_melted['Item'] == 'Custo Caixa EBT')
        ].copy()
        
        # Get production/sales data for cost per box calculation
        boxes_data = df_melted[
            df_melted['Item'].isin(['Caixas Vendidas', 'Caixas Produzidas'])
        ].copy()
        
        # Merge cost data with boxes data for cost per box calculation
        cost_with_boxes = cost_items.merge(
            boxes_data[['Empresa', 'Tipo de Caixa', 'Data', 'Valor']],
            on=['Empresa', 'Tipo de Caixa', 'Data'],
            suffixes=('_cost', '_boxes'),
            how='left'
        )
        
        # Calculate cost per box
        cost_with_boxes['Custo_por_Caixa'] = np.where(
            cost_with_boxes['Valor_boxes'] > 0,
            cost_with_boxes['Valor_cost'] / cost_with_boxes['Valor_boxes'],
            0
        )
        
        return cost_items, cost_with_boxes, boxes_data
        
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return None, None, None

# File upload
uploaded_file = st.file_uploader(
    "📁 Faça upload do arquivo 'Base de dados Historico maio.xlsx'",
    type=['xlsx'],
    help="Selecione o arquivo Excel com os dados históricos"
)

if uploaded_file is not None:
    # Load data
    with st.spinner("Carregando e processando dados..."):
        cost_data, cost_with_boxes, boxes_data = load_and_process_data(uploaded_file)
    
    if cost_data is not None:
        # Sidebar filters
        st.sidebar.header("🔧 Filtros")
        
        # Date range filter
        min_date = cost_data['Data'].min()
        max_date = cost_data['Data'].max()
        
        date_range = st.sidebar.date_input(
            "📅 Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Company filter
        companies = sorted([comp for comp in cost_data['Empresa'].unique() if comp != 'GERAL'])
        selected_companies = st.sidebar.multiselect(
            "🏢 Empresas",
            options=companies,
            default=companies[:5]  # Default to first 5 companies
        )
        
        # Box type filter
        box_types = cost_data['Tipo de Caixa'].unique()
        selected_box_type = st.sidebar.selectbox(
            "📦 Tipo de Caixa",
            options=box_types,
            index=0
        )
        
        # Cost item filter
        cost_items = sorted(cost_data['Item'].unique())
        selected_cost_items = st.sidebar.multiselect(
            "💰 Itens de Custo",
            options=cost_items,
            default=cost_items[:3]  # Default to first 3 items
        )
        
        # Filter data
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_data = cost_data[
                (cost_data['Data'] >= pd.Timestamp(start_date)) &
                (cost_data['Data'] <= pd.Timestamp(end_date)) &
                (cost_data['Empresa'].isin(selected_companies)) &
                (cost_data['Tipo de Caixa'] == selected_box_type) &
                (cost_data['Item'].isin(selected_cost_items))
            ].copy()
        else:
            filtered_data = cost_data[
                (cost_data['Empresa'].isin(selected_companies)) &
                (cost_data['Tipo de Caixa'] == selected_box_type) &
                (cost_data['Item'].isin(selected_cost_items))
            ].copy()
        
        if len(filtered_data) > 0:
            # Aggregate costs by company and date
            agg_data = filtered_data.groupby(['Empresa', 'Data'])['Valor'].sum().reset_index()
            
            # Calculate KPIs
            latest_date = agg_data['Data'].max()
            latest_data = agg_data[agg_data['Data'] == latest_date]
            
            if len(latest_data) > 0:
                # Portfolio average
                portfolio_avg = latest_data['Valor'].mean()
                
                # Best and worst performers
                best_company = latest_data.loc[latest_data['Valor'].idxmin()]
                worst_company = latest_data.loc[latest_data['Valor'].idxmax()]
                
                # Month-over-month change
                prev_date = agg_data[agg_data['Data'] < latest_date]['Data'].max()
                if pd.notna(prev_date):
                    prev_data = agg_data[agg_data['Data'] == prev_date]
                    prev_avg = prev_data['Valor'].mean()
                    mom_change = ((portfolio_avg - prev_avg) / prev_avg) * 100 if prev_avg > 0 else 0
                else:
                    mom_change = 0
                
                # KPI Cards
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "💰 Custo Médio Portfolio",
                        f"R$ {portfolio_avg:,.2f}",
                        f"{mom_change:+.1f}%" if mom_change != 0 else None
                    )
                
                with col2:
                    st.metric(
                        "🏆 Menor Custo",
                        f"{best_company['Empresa']}",
                        f"R$ {best_company['Valor']:,.2f}"
                    )
                
                with col3:
                    st.metric(
                        "⚠️ Maior Custo",
                        f"{worst_company['Empresa']}",
                        f"R$ {worst_company['Valor']:,.2f}"
                    )
                
                with col4:
                    st.metric(
                        "📈 Variação M/M",
                        f"{mom_change:+.1f}%",
                        delta_color="inverse"
                    )
            
            st.markdown("---")
            
            # Visualizations
            col1, col2 = st.columns(2)
            
            # Bar chart - latest month
            with col1:
                st.subheader("📊 Custo por Empresa - Mês Atual")
                if len(latest_data) > 0:
                    fig_bar = px.bar(
                        latest_data.sort_values('Valor'),
                        x='Valor',
                        y='Empresa',
                        orientation='h',
                        title="Custo Total por Empresa",
                        labels={'Valor': 'Custo (R$)', 'Empresa': 'Empresa'}
                    )
                    fig_bar.update_layout(height=400)
                    fig_bar.update_traces(
                        texttemplate='R$ %{x:,.0f}',
                        textposition='outside'
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            # Time series
            with col2:
                st.subheader("📈 Evolução Temporal")
                fig_line = px.line(
                    agg_data,
                    x='Data',
                    y='Valor',
                    color='Empresa',
                    title="Tendência de Custos",
                    labels={'Valor': 'Custo (R$)', 'Data': 'Data'}
                )
                fig_line.update_layout(height=400)
                st.plotly_chart(fig_line, use_container_width=True)
            
            # Heatmap
            st.subheader("🔥 Mapa de Calor - Custo por Empresa x Mês")
            pivot_data = agg_data.pivot(index='Empresa', columns='Data', values='Valor')
            
            fig_heatmap = px.imshow(
                pivot_data.values,
                x=[d.strftime('%b/%y') for d in pivot_data.columns],
                y=pivot_data.index,
                aspect='auto',
                color_continuous_scale='RdYlBu_r',
                title="Intensidade dos Custos"
            )
            fig_heatmap.update_layout(height=400)
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # Interactive table
            st.subheader("📋 Tabela Interativa")
            
            # Prepare table data
            table_data = filtered_data.copy()
            table_data['Data'] = table_data['Data'].dt.strftime('%b/%Y')
            table_data['Valor'] = table_data['Valor'].apply(lambda x: f"R$ {x:,.2f}")
            
            # Search functionality
            search_term = st.text_input("🔍 Pesquisar", placeholder="Digite para filtrar...")
            if search_term:
                table_data = table_data[
                    table_data.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
                ]
            
            st.dataframe(
                table_data,
                use_container_width=True,
                height=300
            )
            
            # Download button
            csv = table_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Baixar CSV",
                data=csv,
                file_name=f'custo_caixa_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv'
            )
            
        else:
            st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")
        
        # Methodology section
        st.markdown("---")
        with st.expander("📖 Metodologia"):
            st.markdown("""
            ### Fonte dos Dados
            - **Arquivo**: Base de dados Historico maio.xlsx
            - **Planilha**: Base
            
            ### Definições
            - **Custo Caixa**: Soma de todos os itens que começam com "Custo" ou são exatamente "Custo Caixa EBT"
            - **Período**: Dados históricos de janeiro/2024 a maio/2025
            - **Empresas**: Todas as subsidiárias da Global Eggs (exceto GERAL que representa o consolidado)
            
            ### Cálculos
            - **Custo Médio Portfolio**: Média simples dos custos de todas as empresas selecionadas
            - **Variação M/M**: Percentual de mudança em relação ao mês anterior
            - **Melhor/Pior Performance**: Baseado no custo total mais baixo/alto do mês
            
            ### Filtros
            - **Período**: Permite selecionar intervalo de datas
            - **Empresas**: Seleção múltipla de empresas para análise
            - **Tipo de Caixa**: Caixas Vendidas vs Caixas Produzidas
            - **Itens de Custo**: Categorias específicas de custo para análise detalhada
            """)
    
else:
    st.info("👆 Por favor, faça upload do arquivo Excel para começar a análise.")
    
    # Show sample data structure
    with st.expander("📋 Estrutura Esperada dos Dados"):
        st.markdown("""
        O arquivo Excel deve conter uma planilha chamada **'Base'** com as seguintes colunas:
        
        | Coluna | Tipo | Descrição |
        |--------|------|-----------|
        | Empresa | Texto | Nome da empresa (ex: JOSIDITH, MARUTANI, etc.) |
        | Tipo de Caixa | Texto | "Caixas Vendidas" ou "Caixas Produzidas" |
        | Item | Texto | Categorias de custo (ex: "Custo Ração", "Custo Logística") |
        | jan/24...mai/25 | Número | Valores mensais em formato mmm/aa |
        """)

# Run command: streamlit run app.py
