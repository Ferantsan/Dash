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
        
        # Categorize items
        df_melted['Categoria'] = df_melted['Item'].apply(categorize_items)
        
        # Separate data types
        volume_data = df_melted[df_melted['Item'].isin(['Caixas Vendidas', 'Caixas Produzidas'])].copy()
        cost_data = df_melted[df_melted['Categoria'] != 'Volume'].copy()
        
        return df_melted, volume_data, cost_data
        
    except Exception as e:
        st.error(f"Erro ao processar dados: {str(e)}")
        return None, None, None

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
    elif 'Despesas' in item:
        return 'Despesas Operacionais'
    elif 'Depreciação' in item:
        return 'Depreciação'
    else:
        return 'Outros Custos'

def create_executive_kpis(volume_data, cost_data, latest_date):
    """Create executive-level KPIs"""
    # Get latest month data
    latest_volume = volume_data[volume_data['Data'] == latest_date]
    latest_costs = cost_data[cost_data['Data'] == latest_date]
    
    # Calculate total production and sales
    total_production = latest_volume[
        (latest_volume['Item'] == 'Caixas Produzidas') & 
        (latest_volume['Empresa'] == 'GERAL')
    ]['Valor'].sum()
    
    total_sales = latest_volume[
        (latest_volume['Item'] == 'Caixas Vendidas') & 
        (latest_volume['Empresa'] == 'GERAL')
    ]['Valor'].sum()
    
    # Calculate total costs
    total_costs = latest_costs[latest_costs['Empresa'] == 'GERAL']['Valor'].sum()
    
    # Calculate efficiency metrics
    efficiency_rate = (total_sales / total_production * 100) if total_production > 0 else 0
    cost_per_box = total_costs / total_sales if total_sales > 0 else 0
    
    # Get previous month for comparison
    prev_date = cost_data[cost_data['Data'] < latest_date]['Data'].max()
    if pd.notna(prev_date):
        prev_costs = cost_data[(cost_data['Data'] == prev_date) & (cost_data['Empresa'] == 'GERAL')]['Valor'].sum()
        cost_variation = ((total_costs - prev_costs) / prev_costs * 100) if prev_costs > 0 else 0
    else:
        cost_variation = 0
    
    return {
        'total_production': total_production,
        'total_sales': total_sales,
        'total_costs': total_costs,
        'efficiency_rate': efficiency_rate,
        'cost_per_box': cost_per_box,
        'cost_variation': cost_variation
    }

# File upload
uploaded_file = st.file_uploader(
    "📁 Faça upload do arquivo 'Base de dados Historico maio.xlsx'",
    type=['xlsx'],
    help="Selecione o arquivo Excel com os dados históricos compilados"
)

if uploaded_file is not None:
    # Load data
    with st.spinner("Carregando e processando dados..."):
        df_melted, volume_data, cost_data = load_and_process_data(uploaded_file)
    
    if df_melted is not None:
        # Sidebar filters
        st.sidebar.markdown('<h2 style="color: #1f77b4;">🔧 Controles Executivos</h2>', unsafe_allow_html=True)
        
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
            default=companies[:8]  # Default to first 8 companies
        )
        
        # Box type filter
        box_types = volume_data['Item'].unique()
        selected_box_type = st.sidebar.selectbox(
            "📦 Tipo de Volume",
            options=box_types,
            index=0
        )
        
        # Analysis type
        analysis_type = st.sidebar.radio(
            "📊 Tipo de Análise",
            ["Visão Consolidada", "Análise por Empresa", "Análise Temporal", "Benchmarking"]
        )
        
        # Filter data
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_volume = volume_data[
                (volume_data['Data'] >= pd.Timestamp(start_date)) &
                (volume_data['Data'] <= pd.Timestamp(end_date))
            ].copy()
            
            filtered_costs = cost_data[
                (cost_data['Data'] >= pd.Timestamp(start_date)) &
                (cost_data['Data'] <= pd.Timestamp(end_date))
            ].copy()
        else:
            filtered_volume = volume_data.copy()
            filtered_costs = cost_data.copy()
        
        # Get latest date for KPIs
        latest_date = filtered_costs['Data'].max()
        
        # Executive KPIs
        st.markdown('<h2 class="section-header">📈 Indicadores Executivos</h2>', unsafe_allow_html=True)
        
        kpis = create_executive_kpis(filtered_volume, filtered_costs, latest_date)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "🏭 Produção Total",
                f"{kpis['total_production']:,.0f}",
                help="Total de caixas produzidas no período"
            )
        
        with col2:
            st.metric(
                "💼 Vendas Total",
                f"{kpis['total_sales']:,.0f}",
                help="Total de caixas vendidas no período"
            )
        
        with col3:
            st.metric(
                "💰 Custo Total",
                f"R$ {kpis['total_costs']:,.0f}",
                f"{kpis['cost_variation']:+.1f}%",
                help="Custo total consolidado"
            )
        
        with col4:
            st.metric(
                "⚡ Eficiência",
                f"{kpis['efficiency_rate']:.1f}%",
                help="Taxa de conversão produção → venda"
            )
        
        with col5:
            st.metric(
                "📦 Custo por Caixa",
                f"R$ {kpis['cost_per_box']:.2f}",
                help="Custo médio por caixa vendida"
            )
        
        st.markdown("---")
        
        # Analysis sections based on selected type
        if analysis_type == "Visão Consolidada":
            st.markdown('<h2 class="section-header">🌍 Visão Consolidada do Grupo</h2>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            # Cost breakdown waterfall
            with col1:
                st.subheader("💧 Composição de Custos")
                latest_costs_geral = filtered_costs[
                    (filtered_costs['Data'] == latest_date) & 
                    (filtered_costs['Empresa'] == 'GERAL')
                ]
                
                cost_by_category = latest_costs_geral.groupby('Categoria')['Valor'].sum().reset_index()
                cost_by_category = cost_by_category.sort_values('Valor', ascending=False)
                
                fig_waterfall = go.Figure(go.Waterfall(
                    name="Custos",
                    orientation="v",
                    measure=["relative"] * len(cost_by_category),
                    x=cost_by_category['Categoria'],
                    y=cost_by_category['Valor'],
                    text=[f"R$ {x:,.0f}" for x in cost_by_category['Valor']],
                    textposition="outside",
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                ))
                fig_waterfall.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_waterfall, use_container_width=True)
            
            # Market share analysis
            with col2:
                st.subheader("🎯 Participação de Mercado")
                market_share = filtered_volume[
                    (filtered_volume['Item'] == selected_box_type) &
                    (filtered_volume['Data'] == latest_date) &
                    (filtered_volume['Empresa'] != 'GERAL')
                ].groupby('Empresa')['Valor'].sum().reset_index()
                
                fig_pie = px.pie(
                    market_share, 
                    values='Valor', 
                    names='Empresa',
                    title="Distribuição por Empresa",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # Trend analysis
            st.subheader("📊 Evolução Temporal dos Principais Indicadores")
            
            # Calculate monthly aggregates
            monthly_costs = filtered_costs[filtered_costs['Empresa'] == 'GERAL'].groupby(['Data', 'Categoria'])['Valor'].sum().reset_index()
            monthly_volume = filtered_volume[
                (filtered_volume['Item'] == selected_box_type) & 
                (filtered_volume['Empresa'] == 'GERAL')
            ].groupby('Data')['Valor'].sum().reset_index()
            monthly_volume['Categoria'] = 'Volume'
            
            # Create area chart
            fig_area = px.area(
                monthly_costs,
                x='Data',
                y='Valor',
                color='Categoria',
                title="Evolução dos Custos por Categoria",
                labels={'Valor': 'Valor (R$)', 'Data': 'Período'}
            )
            fig_area.update_layout(height=400)
            st.plotly_chart(fig_area, use_container_width=True)
        
        elif analysis_type == "Análise por Empresa":
            st.markdown('<h2 class="section-header">🏢 Análise Comparativa por Empresa</h2>', unsafe_allow_html=True)
            
            # Filter for selected companies
            company_costs = filtered_costs[
                (filtered_costs['Empresa'].isin(selected_companies)) &
                (filtered_costs['Data'] == latest_date)
            ]
            
            company_volume = filtered_volume[
                (filtered_volume['Empresa'].isin(selected_companies)) &
                (filtered_volume['Item'] == selected_box_type) &
                (filtered_volume['Data'] == latest_date)
            ]
            
            col1, col2 = st.columns(2)
            
            # Cost efficiency scatter plot
            with col1:
                st.subheader("💡 Eficiência de Custos")
                
                # Calculate cost per box by company
                company_total_costs = company_costs.groupby('Empresa')['Valor'].sum().reset_index()
                company_total_volume = company_volume.groupby('Empresa')['Valor'].sum().reset_index()
                
                efficiency_data = company_total_costs.merge(
                    company_total_volume, 
                    on='Empresa', 
                    suffixes=('_cost', '_volume')
                )
                efficiency_data['cost_per_box'] = efficiency_data['Valor_cost'] / efficiency_data['Valor_volume']
                
                fig_scatter = px.scatter(
                    efficiency_data,
                    x='Valor_volume',
                    y='cost_per_box',
                    text='Empresa',
                    size='Valor_cost',
                    title="Volume vs Custo por Caixa",
                    labels={'Valor_volume': 'Volume de Vendas', 'cost_per_box': 'Custo por Caixa (R$)'}
                )
                fig_scatter.update_traces(textposition='top center')
                fig_scatter.update_layout(height=400)
                st.plotly_chart(fig_scatter, use_container_width=True)
            
            # Stacked bar chart by category
            with col2:
                st.subheader("📊 Composição de Custos por Empresa")
                
                cost_composition = company_costs.groupby(['Empresa', 'Categoria'])['Valor'].sum().reset_index()
                
                fig_stacked = px.bar(
                    cost_composition,
                    x='Empresa',
                    y='Valor',
                    color='Categoria',
                    title="Custos por Categoria e Empresa",
                    labels={'Valor': 'Custo (R$)'}
                )
                fig_stacked.update_layout(height=400, xaxis_tickangle=45)
                st.plotly_chart(fig_stacked, use_container_width=True)
            
            # Ranking table
            st.subheader("🏆 Ranking de Performance")
            ranking_data = efficiency_data.copy()
            ranking_data['rank_volume'] = ranking_data['Valor_volume'].rank(ascending=False)
            ranking_data['rank_efficiency'] = ranking_data['cost_per_box'].rank(ascending=True)
            ranking_data['score'] = (ranking_data['rank_volume'] + ranking_data['rank_efficiency']) / 2
            ranking_data = ranking_data.sort_values('score')
            
            ranking_display = ranking_data[['Empresa', 'Valor_volume', 'cost_per_box', 'Valor_cost']].copy()
            ranking_display.columns = ['Empresa', 'Volume', 'Custo por Caixa', 'Custo Total']
            ranking_display['Volume'] = ranking_display['Volume'].apply(lambda x: f"{x:,.0f}")
            ranking_display['Custo por Caixa'] = ranking_display['Custo por Caixa'].apply(lambda x: f"R$ {x:.2f}")
            ranking_display['Custo Total'] = ranking_display['Custo Total'].apply(lambda x: f"R$ {x:,.0f}")
            
            st.dataframe(ranking_display, use_container_width=True)
        
        elif analysis_type == "Análise Temporal":
            st.markdown('<h2 class="section-header">⏱️ Análise de Tendências Temporais</h2>', unsafe_allow_html=True)
            
            # Multi-line trend analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📈 Evolução de Custos Principais")
                
                main_categories = ['Custo Ração', 'Custo Logística', 'Custo Embalagem', 'Custo Produção']
                trend_data = filtered_costs[
                    (filtered_costs['Categoria'].isin(main_categories)) &
                    (filtered_costs['Empresa'] == 'GERAL')
                ].groupby(['Data', 'Categoria'])['Valor'].sum().reset_index()
                
                fig_trends = px.line(
                    trend_data,
                    x='Data',
                    y='Valor',
                    color='Categoria',
                    title="Tendências dos Principais Custos",
                    labels={'Valor': 'Custo (R$)', 'Data': 'Período'},
                    markers=True
                )
                fig_trends.update_layout(height=400)
                st.plotly_chart(fig_trends, use_container_width=True)
            
            with col2:
                st.subheader("📊 Volatilidade por Categoria")
                
                # Calculate coefficient of variation
                volatility_data = filtered_costs[
                    filtered_costs['Empresa'] == 'GERAL'
                ].groupby('Categoria')['Valor'].agg(['mean', 'std']).reset_index()
                volatility_data['cv'] = (volatility_data['std'] / volatility_data['mean']) * 100
                volatility_data = volatility_data.sort_values('cv', ascending=True)
                
                fig_volatility = px.bar(
                    volatility_data,
                    x='cv',
                    y='Categoria',
                    orientation='h',
                    title="Coeficiente de Variação por Categoria (%)",
                    labels={'cv': 'Coeficiente de Variação (%)'}
                )
                fig_volatility.update_layout(height=400)
                st.plotly_chart(fig_volatility, use_container_width=True)
            
            # Year-over-year comparison
            st.subheader("📅 Comparação Ano a Ano")
            
            # Extract year and month for comparison
            filtered_costs['Year'] = filtered_costs['Data'].dt.year
            filtered_costs['Month'] = filtered_costs['Data'].dt.month
            
            yoy_data = filtered_costs[
                (filtered_costs['Empresa'] == 'GERAL') &
                (filtered_costs['Year'].isin([2024, 2025]))
            ].groupby(['Year', 'Month', 'Categoria'])['Valor'].sum().reset_index()
            
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
        
        elif analysis_type == "Benchmarking":
            st.markdown('<h2 class="section-header">🎯 Benchmarking e Performance</h2>', unsafe_allow_html=True)
            
            # Performance metrics by company
            benchmark_costs = filtered_costs[
                (filtered_costs['Empresa'].isin(selected_companies)) &
                (filtered_costs['Data'] == latest_date)
            ].groupby(['Empresa', 'Categoria'])['Valor'].sum().reset_index()
            
            benchmark_volume = filtered_volume[
                (filtered_volume['Empresa'].isin(selected_companies)) &
                (filtered_volume['Item'] == selected_box_type) &
                (filtered_volume['Data'] == latest_date)
            ].groupby('Empresa')['Valor'].sum().reset_index()
            
            # Create benchmark matrix
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Matriz de Performance")
                
                # Calculate metrics for each company
                metrics_list = []
                for company in selected_companies:
                    company_cost = benchmark_costs[benchmark_costs['Empresa'] == company]['Valor'].sum()
                    company_vol = benchmark_volume[benchmark_volume['Empresa'] == company]['Valor'].iloc[0] if len(benchmark_volume[benchmark_volume['Empresa'] == company]) > 0 else 0
                    
                    if company_vol > 0:
                        metrics_list.append({
                            'Empresa': company,
                            'Custo_Total': company_cost,
                            'Volume': company_vol,
                            'Custo_Unitario': company_cost / company_vol,
                            'Tamanho': company_vol  # For bubble size
                        })
                
                metrics_df = pd.DataFrame(metrics_list)
                
                if len(metrics_df) > 0:
                    fig_matrix = px.scatter(
                        metrics_df,
                        x='Volume',
                        y='Custo_Unitario',
                        size='Tamanho',
                        text='Empresa',
                        title="Volume vs Eficiência de Custos",
                        labels={'Volume': 'Volume de Vendas', 'Custo_Unitario': 'Custo por Caixa (R$)'}
                    )
                    fig_matrix.update_traces(textposition='top center')
                    fig_matrix.update_layout(height=400)
                    st.plotly_chart(fig_matrix, use_container_width=True)
            
            with col2:
                st.subheader("📊 Benchmarking por Categoria")
                
                # Create radar chart for top categories
                main_cats = ['Custo Ração', 'Custo Logística', 'Custo Embalagem']
                radar_data = benchmark_costs[benchmark_costs['Categoria'].isin(main_cats)]
                
                if len(radar_data) > 0:
                    # Normalize data for radar chart
                    for cat in main_cats:
                        cat_data = radar_data[radar_data['Categoria'] == cat]
                        if len(cat_data) > 0:
                            max_val = cat_data['Valor'].max()
                            radar_data.loc[radar_data['Categoria'] == cat, 'Valor_Norm'] = cat_data['Valor'] / max_val * 100
                    
                    fig_radar = go.Figure()
                    
                    for company in selected_companies[:5]:  # Limit to 5 companies for readability
                        company_data = radar_data[radar_data['Empresa'] == company]
                        if len(company_data) > 0:
                            fig_radar.add_trace(go.Scatterpolar(
                                r=company_data['Valor_Norm'].tolist() + [company_data['Valor_Norm'].tolist()[0]],
                                theta=company_data['Categoria'].tolist() + [company_data['Categoria'].tolist()[0]],
                                fill='toself',
                                name=company
                            ))
                    
                    fig_radar.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100]
                            )),
                        showlegend=True,
                        title="Comparação Normalizada por Categoria",
                        height=400
                    )
                    st.plotly_chart(fig_radar, use_container_width=True)
        
        # Advanced Analytics Section
        st.markdown("---")
        st.markdown('<h2 class="section-header">🔬 Analytics Avançados</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Cost correlation analysis
            st.subheader("🔗 Correlação entre Categorias")
            
            correlation_data = filtered_costs[
                filtered_costs['Empresa'] == 'GERAL'
            ].pivot_table(index='Data', columns='Categoria', values='Valor', aggfunc='sum')
            
            correlation_matrix = correlation_data.corr()
            
            fig_corr = px.imshow(
                correlation_matrix,
                title="Matriz de Correlação",
                color_continuous_scale='RdBu',
                aspect='auto'
            )
            fig_corr.update_layout(height=400)
            st.plotly_chart(fig_corr, use_container_width=True)
        
        with col2:
            # Seasonal analysis
            st.subheader("🌍 Análise Sazonal")
            
            seasonal_data = filtered_costs[filtered_costs['Empresa'] == 'GERAL'].copy()
            seasonal_data['Month'] = seasonal_data['Data'].dt.month
            seasonal_summary = seasonal_data.groupby(['Month', 'Categoria'])['Valor'].mean().reset_index()
            
            # Focus on main categories for clarity
            main_seasonal = seasonal_summary[seasonal_summary['Categoria'].isin(['Custo Ração', 'Custo Logística', 'Custo Embalagem'])]
            
            fig_seasonal = px.line(
                main_seasonal,
                x='Month',
                y='Valor',
                color='Categoria',
                title="Padrão Sazonal (Média Mensal)",
                labels={'Month': 'Mês', 'Valor': 'Custo Médio (R$)'},
                markers=True
            )
            fig_seasonal.update_layout(height=400)
            st.plotly_chart(fig_seasonal, use_container_width=True)
        
        # Export functionality
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("📥 Gerar Relatório Executivo", use_container_width=True):
                # Create comprehensive report
                report_data = {
                    'KPIs': kpis,
                    'Data_Analise': latest_date.strftime('%d/%m/%Y'),
                    'Empresas_Analisadas': selected_companies,
                    'Periodo': f"{start_date} a {end_date}"
                }
                
                report_text = f"""
# RELATÓRIO EXECUTIVO - GLOBAL EGGS

## Período: {report_data['Periodo']}

### INDICADORES PRINCIPAIS
- Produção Total: {kpis['total_production']:,.0f} caixas
- Vendas Total: {kpis['total_sales']:,.0f} caixas
- Custo Total: R$ {kpis['total_costs']:,.0f}
- Eficiência Operacional: {kpis['efficiency_rate']:.1f}%
- Custo por Caixa: R$ {kpis['cost_per_box']:.2f}

### ANÁLISE DE PERFORMANCE
- Variação de Custos (M/M): {kpis['cost_variation']:+.1f}%
- Empresas Analisadas: {len(selected_companies)}

### RECOMENDAÇÕES
[Espaço para inserir recomendações baseadas nos dados analisados]
                """
                
                st.download_button(
                    label="📄 Download Relatório",
                    data=report_text,
                    file_name=f"relatorio_executivo_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )
        
        # Methodology section
        with st.expander("📖 Metodologia e Definições"):
            st.markdown("""
            ### Fonte dos Dados
            - **Base**: Compilado mensal de todas as empresas do grupo
            - **Período**: Janeiro 2024 a Maio 2025
            - **Frequência**: Dados mensais consolidados
            
            ### Categorização de Custos
            - **Custo Ração**: Principal insumo produtivo
            - **Custo Logística**: Distribuição e transporte
            - **Custo Embalagem**: Materiais de acondicionamento
            - **Custo Produção**: Mão de obra e processos produtivos
            - **Despesas Operacionais**: Vendas, administrativas e tributárias
            
            ### Métricas Calculadas
            - **Eficiência**: Taxa de conversão produção → vendas
            - **Custo por Caixa**: Custo total / Volume vendido
            - **Coeficiente de Variação**: Medida de volatilidade (σ/μ)
            
            ### Metodologia de Benchmarking
            - Normalização por volume para comparabilidade
            - Análise multivariada para ranking de performance
            - Correlações temporais para identificação de padrões
            """)
    
else:
    st.info("👆 Por favor, faça upload do arquivo Excel para acessar o Dashboard Executivo.")
    
    # Show enhanced data structure info
    with st.expander("📋 Estrutura Esperada dos Dados"):
        st.markdown("""
        ## Estrutura da Base de Dados Consolidada
        
        O arquivo deve conter dados compilados de múltiplas tabelas mensais:
        
        ### Colunas Obrigatórias:
        | Coluna | Tipo | Descrição |
        |--------|------|-----------|
        | **Empresa** | Texto | Nome da subsidiária (JOSIDITH, MARUTANI, etc.) |
        | **Tipo de Caixa** | Texto | "Caixas Vendidas" ou "Caixas Produzidas" |
        | **Item** | Texto | Categoria de custo ou métrica |
        | **jan/24...mai/25** | Numérico | Valores mensais |
        
        ### Categorias de Análise:
        - **Volume**: Caixas Produzidas/Vendidas
        - **Custos Diretos**: Ração, Embalagem, Logística
        - **Custos Indiretos**: Manutenção, Utilidades, M.O.
        - **Despesas**: Vendas, Administrativas, Tributárias
        - **Outros**: Depreciação, Perdas, etc.
        
        ### Empresas do Grupo:
        JOSIDITH, MARUTANI, STRAGLIOTTO, ASA, IANA, AVIMOR, ALEXAVES, 
        MACIAMBU, BL GO, BL STA MARIA, KATAYAMA, VITAGEMA, TAMAGO, GERAL
        """)

# Run command: streamlit run app.py
