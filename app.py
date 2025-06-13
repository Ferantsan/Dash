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
    page_title="Dashboard Executivo - Global Eggs e Subsidiárias",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
    }
    .executive-title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0;
    }
    .alert-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 5px solid #e74c3c;
        background-color: #fdf2f2;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="executive-title">🥚 Dashboard Executivo - Global Eggs e Subsidiárias</h1>', unsafe_allow_html=True)

@st.cache_data
def load_and_process_data(uploaded_file):
    """Load and process the Excel data with enhanced analysis"""
    try:
        # Read the Excel file
        df = pd.read_excel(uploaded_file, sheet_name='Base')
        
        # Get month columns
        month_cols = [col for col in df.columns if '/' in str(col)]
        
        # Melt the dataframe to long format
        df_melted = df.melt(
            id_vars=['Empresa', 'Tipo de Caixa', 'Item'],
            value_vars=month_cols,
            var_name='Data',
            value_name='Valor'
        )
        
        # Convert Data to proper datetime
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
        
        # Clean data - remove zeros and invalid values
        df_melted = df_melted[df_melted['Valor'].notna()]
        
        # Categorize items for better analysis
        df_melted['Categoria'] = df_melted['Item'].apply(categorize_items)
        
        return df_melted
        
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return None

def categorize_items(item):
    """Categorize items for better analysis"""
    if item in ['Caixas Vendidas', 'Caixas Produzidas']:
        return 'Volume'
    elif 'Custo Ração' in item:
        return 'Custo Ração'
    elif 'Custo Logística' in item:
        return 'Custo Logística'
    elif 'Custo Embalagem' in item:
        return 'Custo Embalagem'
    elif 'Custo Produção' in item:
        return 'Custo Produção'
    elif 'Custo Manutenção' in item:
        return 'Custo Manutenção'
    elif 'Custo Utilidades' in item:
        return 'Custo Utilidades'
    elif 'Despesas' in item:
        return 'Despesas Operacionais'
    elif 'Depreciação' in item:
        return 'Depreciação'
    elif 'Custo Exportação' in item:
        return 'Custo Exportação'
    elif 'Suporte' in item:
        return 'Suporte Operacional'
    elif 'Vacinas' in item or 'Medicamentos' in item:
        return 'Sanidade Animal'
    else:
        return 'Outros'

def calculate_cost_per_box(df, selected_companies, selected_box_type, latest_date):
    """Calculate cost per box for selected parameters"""
    try:
        # Get volume data
        volume_data = df[
            (df['Item'] == selected_box_type) & 
            (df['Data'] == latest_date) &
            (df['Empresa'].isin(selected_companies + ['GERAL']))
        ]
        
        # Get cost data (excluding volume items)
        cost_data = df[
            (df['Categoria'] != 'Volume') & 
            (df['Data'] == latest_date) &
            (df['Empresa'].isin(selected_companies + ['GERAL']))
        ].groupby('Empresa')['Valor'].sum().reset_index()
        
        # Merge volume and cost data
        volume_summary = volume_data.groupby('Empresa')['Valor'].sum().reset_index()
        volume_summary.columns = ['Empresa', 'Volume']
        
        cost_summary = cost_data.copy()
        cost_summary.columns = ['Empresa', 'Custo_Total']
        
        # Calculate cost per box
        result = cost_summary.merge(volume_summary, on='Empresa', how='inner')
        result['Custo_por_Caixa'] = result['Custo_Total'] / result['Volume']
        result = result[result['Volume'] > 0]  # Remove companies with no volume
        
        return result
    except:
        return pd.DataFrame()

# File upload
uploaded_file = st.file_uploader(
    "📁 Faça upload do arquivo 'Base de dados Historico maio.xlsx'",
    type=['xlsx'],
    help="Selecione o arquivo Excel com os dados históricos compilados"
)

if uploaded_file is not None:
    # Load data
    with st.spinner("Carregando e processando dados..."):
        df_melted = load_and_process_data(uploaded_file)
    
    if df_melted is not None:
        # Sidebar filters
        st.sidebar.markdown('<h2 style="color: #1f77b4;">🎛️ Filtros de Análise</h2>', unsafe_allow_html=True)
        
        # Date range filter
        min_date = df_melted['Data'].min()
        max_date = df_melted['Data'].max()
        
        date_range = st.sidebar.date_input(
            "📅 Período de Análise",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        # Company filter (exclude GERAL for operational analysis)
        companies = sorted([comp for comp in df_melted['Empresa'].unique() if comp != 'GERAL'])
        selected_companies = st.sidebar.multiselect(
            "🏢 Empresas",
            options=companies,
            default=companies[:8] if len(companies) > 8 else companies
        )
        
        # Box type filter
        box_types = [item for item in df_melted['Item'].unique() if 'Caixas' in item]
        selected_box_type = st.sidebar.selectbox(
            "📦 Tipo de Volume",
            options=box_types,
            index=0 if len(box_types) > 0 else None
        )
        
        # Item/Category filter - NEW
        st.sidebar.markdown("### 🎯 Filtro de Itens")
        filter_type = st.sidebar.radio(
            "Tipo de Filtro",
            ["Por Categoria", "Por Item Específico"]
        )
        
        if filter_type == "Por Categoria":
            categories = sorted([cat for cat in df_melted['Categoria'].unique() if cat != 'Volume'])
            selected_categories = st.sidebar.multiselect(
                "Categorias de Custo",
                options=categories,
                default=categories[:5] if len(categories) > 5 else categories
            )
            # Filter by categories
            selected_items = df_melted[df_melted['Categoria'].isin(selected_categories)]['Item'].unique()
        else:
            cost_items = sorted([item for item in df_melted['Item'].unique() if 'Caixas' not in item])
            selected_items = st.sidebar.multiselect(
                "Itens Específicos",
                options=cost_items,
                default=cost_items[:5] if len(cost_items) > 5 else cost_items
            )
            selected_categories = df_melted[df_melted['Item'].isin(selected_items)]['Categoria'].unique()
        
        # Analysis type
        analysis_type = st.sidebar.selectbox(
            "📊 Tipo de Análise",
            ["Dashboard Executivo", "Análise de Custos", "Performance por Empresa", "Análise Temporal"]
        )
        
        # Filter data based on selections
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_data = df_melted[
                (df_melted['Data'] >= pd.Timestamp(start_date)) &
                (df_melted['Data'] <= pd.Timestamp(end_date)) &
                (df_melted['Item'].isin(list(selected_items) + [selected_box_type]))
            ].copy()
        else:
            filtered_data = df_melted[
                df_melted['Item'].isin(list(selected_items) + [selected_box_type])
            ].copy()
        
        # Get latest date for KPIs
        latest_date = filtered_data['Data'].max()
        
        # Check if we have enough data
        if len(filtered_data) == 0:
            st.markdown('<div class="alert-box">⚠️ <strong>Atenção:</strong> Nenhum dado encontrado com os filtros selecionados. Ajuste os filtros para visualizar as análises.</div>', unsafe_allow_html=True)
        else:
            
            if analysis_type == "Dashboard Executivo":
                # Executive KPIs
                st.markdown('<h2 class="section-header">📈 Indicadores Executivos</h2>', unsafe_allow_html=True)
                
                # Calculate cost per box
                cost_per_box_data = calculate_cost_per_box(df_melted, selected_companies, selected_box_type, latest_date)
                
                if len(cost_per_box_data) > 0:
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    # Portfolio metrics
                    portfolio_avg_cost = cost_per_box_data[cost_per_box_data['Empresa'] != 'GERAL']['Custo_por_Caixa'].mean()
                    portfolio_total_volume = cost_per_box_data[cost_per_box_data['Empresa'] != 'GERAL']['Volume'].sum()
                    portfolio_total_cost = cost_per_box_data[cost_per_box_data['Empresa'] != 'GERAL']['Custo_Total'].sum()
                    
                    # Best and worst performers
                    companies_only = cost_per_box_data[cost_per_box_data['Empresa'] != 'GERAL']
                    if len(companies_only) > 0:
                        best_company = companies_only.loc[companies_only['Custo_por_Caixa'].idxmin()]
                        worst_company = companies_only.loc[companies_only['Custo_por_Caixa'].idxmax()]
                        
                        with col1:
                            st.metric(
                                "💰 Custo Médio/Caixa",
                                f"R$ {portfolio_avg_cost:.2f}",
                                help="Custo médio por caixa do portfolio"
                            )
                        
                        with col2:
                            st.metric(
                                "📦 Volume Total",
                                f"{portfolio_total_volume:,.0f}",
                                help="Volume total de caixas no período"
                            )
                        
                        with col3:
                            st.metric(
                                "💵 Custo Total",
                                f"R$ {portfolio_total_cost:,.0f}",
                                help="Custo total do portfolio"
                            )
                        
                        with col4:
                            st.metric(
                                "🏆 Melhor Performance",
                                f"{best_company['Empresa']}",
                                f"R$ {best_company['Custo_por_Caixa']:.2f}",
                                help="Empresa com menor custo por caixa"
                            )
                        
                        with col5:
                            st.metric(
                                "⚠️ Atenção Necessária",
                                f"{worst_company['Empresa']}",
                                f"R$ {worst_company['Custo_por_Caixa']:.2f}",
                                delta_color="inverse",
                                help="Empresa com maior custo por caixa"
                            )
                
                st.markdown("---")
                
                # Main visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Custo por Caixa - Ranking")
                    if len(cost_per_box_data) > 0:
                        companies_data = cost_per_box_data[cost_per_box_data['Empresa'] != 'GERAL'].sort_values('Custo_por_Caixa')
                        
                        fig_ranking = px.bar(
                            companies_data,
                            x='Custo_por_Caixa',
                            y='Empresa',
                            orientation='h',
                            title="Ranking de Eficiência - Custo por Caixa",
                            labels={'Custo_por_Caixa': 'Custo por Caixa (R$)', 'Empresa': 'Empresa'},
                            color='Custo_por_Caixa',
                            color_continuous_scale='RdYlGn_r'
                        )
                        fig_ranking.update_layout(height=400)
                        fig_ranking.update_traces(
                            texttemplate='R$ %{x:.2f}',
                            textposition='outside'
                        )
                        st.plotly_chart(fig_ranking, use_container_width=True)
                
                with col2:
                    st.subheader("🎯 Volume vs Eficiência")
                    if len(cost_per_box_data) > 0:
                        companies_data = cost_per_box_data[cost_per_box_data['Empresa'] != 'GERAL']
                        
                        fig_scatter = px.scatter(
                            companies_data,
                            x='Volume',
                            y='Custo_por_Caixa',
                            size='Custo_Total',
                            text='Empresa',
                            title="Volume vs Custo por Caixa",
                            labels={'Volume': 'Volume de Caixas', 'Custo_por_Caixa': 'Custo por Caixa (R$)'},
                            color='Custo_por_Caixa',
                            color_continuous_scale='RdYlGn_r'
                        )
                        fig_scatter.update_traces(textposition='top center')
                        fig_scatter.update_layout(height=400)
                        st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Composition analysis
                st.subheader("🔍 Composição de Custos")
                
                latest_costs = filtered_data[
                    (filtered_data['Data'] == latest_date) & 
                    (filtered_data['Categoria'] != 'Volume') &
                    (filtered_data['Empresa'].isin(selected_companies))
                ]
                
                if len(latest_costs) > 0:
                    cost_composition = latest_costs.groupby(['Empresa', 'Categoria'])['Valor'].sum().reset_index()
                    
                    fig_composition = px.sunburst(
                        cost_composition,
                        path=['Categoria', 'Empresa'],
                        values='Valor',
                        title="Composição de Custos por Categoria e Empresa"
                    )
                    fig_composition.update_layout(height=500)
                    st.plotly_chart(fig_composition, use_container_width=True)
            
            elif analysis_type == "Análise de Custos":
                st.markdown('<h2 class="section-header">💰 Análise Detalhada de Custos</h2>', unsafe_allow_html=True)
                
                # Filter cost data
                cost_data = filtered_data[
                    (filtered_data['Categoria'] != 'Volume') &
                    (filtered_data['Empresa'].isin(selected_companies + ['GERAL']))
                ]
                
                if len(cost_data) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📈 Evolução dos Custos Principais")
                        
                        # Monthly cost evolution by category
                        monthly_costs = cost_data.groupby(['Data', 'Categoria'])['Valor'].sum().reset_index()
                        
                        fig_evolution = px.line(
                            monthly_costs,
                            x='Data',
                            y='Valor',
                            color='Categoria',
                            title="Evolução Mensal dos Custos por Categoria",
                            labels={'Valor': 'Custo (R$)', 'Data': 'Período'}
                        )
                        fig_evolution.update_layout(height=400)
                        st.plotly_chart(fig_evolution, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Participação por Categoria")
                        
                        # Cost breakdown pie chart
                        category_totals = cost_data.groupby('Categoria')['Valor'].sum().reset_index()
                        category_totals = category_totals.sort_values('Valor', ascending=False)
                        
                        fig_pie = px.pie(
                            category_totals,
                            values='Valor',
                            names='Categoria',
                            title="Distribuição dos Custos por Categoria"
                        )
                        fig_pie.update_layout(height=400)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Cost comparison table
                    st.subheader("📋 Comparativo de Custos por Empresa")
                    
                    latest_comparison = cost_data[cost_data['Data'] == latest_date]
                    comparison_table = latest_comparison.pivot_table(
                        index='Empresa',
                        columns='Categoria',
                        values='Valor',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    # Format as currency
                    comparison_formatted = comparison_table.applymap(lambda x: f"R$ {x:,.2f}" if x != 0 else "-")
                    st.dataframe(comparison_formatted, use_container_width=True)
            
            elif analysis_type == "Performance por Empresa":
                st.markdown('<h2 class="section-header">🏢 Performance Comparativa por Empresa</h2>', unsafe_allow_html=True)
                
                if len(selected_companies) > 0:
                    # Company performance metrics
                    company_data = filtered_data[
                        (filtered_data['Empresa'].isin(selected_companies)) &
                        (filtered_data['Data'] == latest_date)
                    ]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🎯 Radar de Performance")
                        
                        # Create radar chart for top categories
                        main_categories = list(selected_categories)[:5]  # Limit to 5 for readability
                        radar_data = company_data[
                            (company_data['Categoria'].isin(main_categories)) &
                            (company_data['Categoria'] != 'Volume')
                        ]
                        
                        if len(radar_data) > 0:
                            radar_pivot = radar_data.pivot_table(
                                index='Empresa',
                                columns='Categoria',
                                values='Valor',
                                aggfunc='sum',
                                fill_value=0
                            )
                            
                            # Normalize for radar chart
                            radar_normalized = radar_pivot.div(radar_pivot.max()) * 100
                            
                            fig_radar = go.Figure()
                            
                            for company in selected_companies[:5]:  # Limit companies for readability
                                if company in radar_normalized.index:
                                    values = radar_normalized.loc[company].tolist()
                                    categories = radar_normalized.columns.tolist()
                                    
                                    fig_radar.add_trace(go.Scatterpolar(
                                        r=values + [values[0]],  # Close the polygon
                                        theta=categories + [categories[0]],
                                        fill='toself',
                                        name=company
                                    ))
                            
                            fig_radar.update_layout(
                                polar=dict(
                                    radialaxis=dict(
                                        visible=True,
                                        range=[0, 100]
                                    )),
                                title="Comparação Normalizada por Categoria (%)",
                                height=400
                            )
                            st.plotly_chart(fig_radar, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Custos por Empresa")
                        
                        company_costs = company_data[
                            company_data['Categoria'] != 'Volume'
                        ].groupby(['Empresa', 'Categoria'])['Valor'].sum().reset_index()
                        
                        fig_company_costs = px.bar(
                            company_costs,
                            x='Empresa',
                            y='Valor',
                            color='Categoria',
                            title="Custos Totais por Empresa e Categoria",
                            labels={'Valor': 'Custo (R$)'}
                        )
                        fig_company_costs.update_layout(height=400, xaxis_tickangle=45)
                        st.plotly_chart(fig_company_costs, use_container_width=True)
                    
                    # Performance ranking
                    st.subheader("🏆 Ranking de Performance")
                    
                    cost_per_box_current = calculate_cost_per_box(df_melted, selected_companies, selected_box_type, latest_date)
                    
                    if len(cost_per_box_current) > 0:
                        ranking_data = cost_per_box_current[cost_per_box_current['Empresa'] != 'GERAL'].copy()
                        ranking_data = ranking_data.sort_values('Custo_por_Caixa')
                        ranking_data['Posição'] = range(1, len(ranking_data) + 1)
                        
                        # Format for display
                        ranking_display = ranking_data[['Posição', 'Empresa', 'Volume', 'Custo_Total', 'Custo_por_Caixa']].copy()
                        ranking_display['Volume'] = ranking_display['Volume'].apply(lambda x: f"{x:,.0f}")
                        ranking_display['Custo_Total'] = ranking_display['Custo_Total'].apply(lambda x: f"R$ {x:,.0f}")
                        ranking_display['Custo_por_Caixa'] = ranking_display['Custo_por_Caixa'].apply(lambda x: f"R$ {x:.2f}")
                        ranking_display.columns = ['🏆 Posição', '🏢 Empresa', '📦 Volume', '💰 Custo Total', '📊 Custo/Caixa']
                        
                        st.dataframe(ranking_display, use_container_width=True, hide_index=True)
            
            elif analysis_type == "Análise Temporal":
                st.markdown('<h2 class="section-header">⏱️ Análise de Tendências Temporais</h2>', unsafe_allow_html=True)
                
                temporal_data = filtered_data[
                    (filtered_data['Categoria'] != 'Volume') &
                    (filtered_data['Empresa'].isin(selected_companies + ['GERAL']))
                ]
                
                if len(temporal_data) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📈 Tendências por Categoria")
                        
                        # Monthly trends by category
                        monthly_trends = temporal_data.groupby(['Data', 'Categoria'])['Valor'].sum().reset_index()
                        
                        fig_trends = px.line(
                            monthly_trends,
                            x='Data',
                            y='Valor',
                            color='Categoria',
                            title="Tendências Mensais por Categoria",
                            labels={'Valor': 'Custo (R$)', 'Data': 'Período'},
                            markers=True
                        )
                        fig_trends.update_layout(height=400)
                        st.plotly_chart(fig_trends, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Variabilidade dos Custos")
                        
                        # Calculate coefficient of variation
                        cv_data = temporal_data.groupby('Categoria')['Valor'].agg(['mean', 'std']).reset_index()
                        cv_data['cv'] = (cv_data['std'] / cv_data['mean']) * 100
                        cv_data = cv_data.sort_values('cv')
                        
                        fig_cv = px.bar(
                            cv_data,
                            x='cv',
                            y='Categoria',
                            orientation='h',
                            title="Coeficiente de Variação por Categoria (%)",
                            labels={'cv': 'Coeficiente de Variação (%)'},
                            color='cv',
                            color_continuous_scale='RdYlBu_r'
                        )
                        fig_cv.update_layout(height=400)
                        st.plotly_chart(fig_cv, use_container_width=True)
                    
                    # Year-over-year comparison
                    st.subheader("📅 Comparação Ano a Ano")
                    
                    temporal_data['Year'] = temporal_data['Data'].dt.year
                    temporal_data['Month'] = temporal_data['Data'].dt.month
                    
                    yoy_data = temporal_data[
                        temporal_data['Year'].isin([2024, 2025])
                    ].groupby(['Year', 'Month', 'Categoria'])['Valor'].sum().reset_index()
                    
                    if len(yoy_data) > 0:
                        fig_yoy = px.bar(
                            yoy_data,
                            x='Month',
                            y='Valor',
                            color='Categoria',
                            facet_col='Year',
                            title="Comparação Mensal 2024 vs 2025",
                            labels={'Valor': 'Custo (R$)', 'Month': 'Mês'}
                        )
                        fig_yoy.update_layout(height=400)
                        st.plotly_chart(fig_yoy, use_container_width=True)
            
            # Export functionality
            st.markdown("---")
            st.subheader("📥 Exportar Dados")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Exportar Dados Filtrados", use_container_width=True):
                    csv_data = filtered_data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f'dados_filtrados_{datetime.now().strftime("%Y%m%d")}.csv',
                        mime='text/csv'
                    )
            
            with col2:
                if len(cost_per_box_data) > 0 and st.button("📈 Exportar Análise de Performance", use_container_width=True):
                    performance_csv = cost_per_box_data.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Performance CSV",
                        data=performance_csv,
                        file_name=f'performance_analysis_{datetime.now().strftime("%Y%m%d")}.csv',
                        mime='text/csv'
                    )
        
        # Methodology section
        with st.expander("📖 Metodologia e Definições"):
            st.markdown("""
            ### 📊 Fonte dos Dados
            - **Base**: Dados consolidados mensais de todas as empresas do grupo Global Eggs
            - **Período**: Janeiro 2024 a Maio 2025
            - **Atualização**: Dados mensais processados automaticamente
            
            ### 🎯 Categorização de Custos
            - **Custo Ração**: Principal insumo produtivo (maior componente de custo)
            - **Custo Logística**: Distribuição, transporte e movimentação
            - **Custo Embalagem**: Materiais de acondicionamento e embalagem
            - **Custo Produção**: Mão de obra direta e processos produtivos
            - **Custo Manutenção**: Manutenção preventiva e corretiva de equipamentos
            - **Despesas Operacionais**: Vendas, administrativas e tributárias
            - **Sanidade Animal**: Vacinas, medicamentos e cuidados veterinários
            
            ### 📈 Métricas Calculadas
            - **Custo por Caixa**: Custo total dividido pelo volume de caixas vendidas/produzidas
            - **Coeficiente de Variação**: Medida de volatilidade dos custos (desvio padrão / média)
            - **Performance Ranking**: Baseado na eficiência de custo por caixa
            - **Participação**: Percentual de cada categoria no custo total
            
            ### 🔍 Filtros Disponíveis
            - **Período**: Seleção de intervalo de datas para análise
            - **Empresas**: Múltipla seleção de subsidiárias
            - **Tipo de Caixa**: Vendidas vs Produzidas
            - **Categorias/Itens**: Filtragem por tipo de custo ou item específico
            
            ### ⚠️ Observações Importantes
            - Valores zerados ou inválidos são automaticamente excluídos
            - Análises baseadas no último mês disponível nos dados
            - GERAL representa o consolidado de todas as empresas
            - Rankings consideram apenas empresas com volume > 0
            """)
    
else:
    st.info("👆 Por favor, faça upload do arquivo Excel para acessar o Dashboard Executivo.")
    
    # Enhanced data structure info
    with st.expander("📋 Estrutura Esperada dos Dados"):
        st.markdown("""
        ## 📊 Estrutura da Base de Dados Consolidada
        
        O arquivo deve conter dados compilados de múltiplas tabelas mensais seguindo a estrutura:
        
        ### 📝 Colunas Obrigatórias:
        | Coluna | Tipo | Descrição | Exemplo |
        |--------|------|-----------|---------|
        | **Empresa** | Texto | Nome da subsidiária | JOSIDITH, MARUTANI, etc. |
        | **Tipo de Caixa** | Texto | Tipo de volume | "Caixas Vendidas" ou "Caixas Produzidas" |
        | **Item** | Texto | Categoria/métrica específica | "Custo Ração", "Despesas Vendas", etc. |
        | **jan/24...mai/25** | Numérico | Valores mensais | Formato mmm/aa |
        
        ### 🏭 Empresas do Grupo Global Eggs:
        **Subsidiárias Operacionais:**
        - JOSIDITH, MARUTANI, STRAGLIOTTO
        - ASA, IANA, AVIMOR, ALEXAVES
        - MACIAMBU, BL GO, BL STA MARIA
        - KATAYAMA, VITAGEMA, TAMAGO
        
        **Consolidado:** GERAL (soma de todas as subsidiárias)
        
        ### 📊 Principais Categorias de Análise:
        
        **Volume:**
        - Caixas Vendidas / Caixas Produzidas
        
        **Custos Diretos:**
        - Custo Ração (maior componente)
        - Custo Embalagem, Logística
        - Custo Produção MO
        
        **Custos Indiretos:**
        - Custo Manutenção, Utilidades
        - Sanidade Animal (Vacinas/Medicamentos)
        
        **Despesas:**
        - Despesas Vendas, Administrativas
        - Despesas Tributárias
        - Depreciação Biológica
        
        ### 🎯 Dicas para Melhores Análises:
        1. **Selecione empresas relevantes** para comparação
        2. **Use filtros de categoria** para análises focadas
        3. **Compare períodos** para identificar tendências
        4. **Analise custo por caixa** para eficiência operacional
        5. **Monitore variabilidade** para gestão de riscos
        """)

# Run command: streamlit run app.py
