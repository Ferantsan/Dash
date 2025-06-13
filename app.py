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
    .budget-positive {
        color: #27ae60;
        font-weight: bold;
    }
    .budget-negative {
        color: #e74c3c;
        font-weight: bold;
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
        
        # Clean data - remove zeros and invalid values where appropriate
        df_melted = df_melted[df_melted['Valor'].notna()]
        
        # Identify budget vs actual items
        df_melted['Tipo_Item'] = df_melted['Item'].apply(lambda x: 'Orçado' if 'Orçado' in str(x) else 'Real')
        df_melted['Item_Base'] = df_melted['Item'].apply(lambda x: str(x).replace(' Orçado', '') if 'Orçado' in str(x) else str(x))
        
        # Categorize items for better analysis
        df_melted['Categoria'] = df_melted['Item_Base'].apply(categorize_items)
        
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
    elif 'Integração' in item:
        return 'Integração'
    elif 'Perdas' in item:
        return 'Perdas Operacionais'
    else:
        return 'Outros'

def calculate_budget_variance(df, selected_companies, latest_date, selected_items):
    """Calculate budget variance analysis"""
    try:
        # Filter data for analysis
        analysis_data = df[
            (df['Data'] == latest_date) &
            (df['Empresa'].isin(selected_companies + ['GERAL'])) &
            (df['Item'].isin(selected_items))
        ].copy()
        
        # Separate real and budget data
        real_data = analysis_data[analysis_data['Tipo_Item'] == 'Real'].copy()
        budget_data = analysis_data[analysis_data['Tipo_Item'] == 'Orçado'].copy()
        
        # Merge real and budget data
        budget_analysis = real_data.merge(
            budget_data[['Empresa', 'Item_Base', 'Valor']], 
            on=['Empresa', 'Item_Base'], 
            suffixes=('_real', '_orcado'),
            how='outer'
        ).fillna(0)
        
        # Calculate variances
        budget_analysis['Variacao_Absoluta'] = budget_analysis['Valor_real'] - budget_analysis['Valor_orcado']
        budget_analysis['Variacao_Percentual'] = np.where(
            budget_analysis['Valor_orcado'] != 0,
            (budget_analysis['Variacao_Absoluta'] / budget_analysis['Valor_orcado']) * 100,
            0
        )
        
        return budget_analysis
        
    except Exception as e:
        st.error(f"Erro no cálculo de variação orçamentária: {str(e)}")
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
        
        # Company filter
        companies = sorted([comp for comp in df_melted['Empresa'].unique() if comp != 'GERAL'])
        selected_companies = st.sidebar.multiselect(
            "🏢 Empresas",
            options=companies,
            default=companies[:8] if len(companies) > 8 else companies
        )
        
        # Box type filter
        box_types = [item for item in df_melted['Item'].unique() if 'Caixas' in item and 'Orçado' not in item]
        selected_box_type = st.sidebar.selectbox(
            "📦 Tipo de Volume",
            options=box_types,
            index=0 if len(box_types) > 0 else None
        )
        
        # Enhanced Item filter - showing all items from Excel
        st.sidebar.markdown("### 🎯 Filtro de Itens")
        
        # Get all unique items (excluding volume items)
        all_items = sorted([item for item in df_melted['Item'].unique() if 'Caixas' not in item])
        
        # Item type filter
        item_type_filter = st.sidebar.radio(
            "Tipo de Item",
            ["Todos", "Apenas Reais", "Apenas Orçados", "Pares Real vs Orçado"]
        )
        
        # Filter items based on type selection
        if item_type_filter == "Apenas Reais":
            filtered_items = [item for item in all_items if 'Orçado' not in item]
        elif item_type_filter == "Apenas Orçados":
            filtered_items = [item for item in all_items if 'Orçado' in item]
        elif item_type_filter == "Pares Real vs Orçado":
            # Show only items that have both real and budget versions
            base_items = df_melted[df_melted['Tipo_Item'] == 'Real']['Item_Base'].unique()
            budget_items = df_melted[df_melted['Tipo_Item'] == 'Orçado']['Item_Base'].unique()
            paired_items = list(set(base_items) & set(budget_items))
            filtered_items = []
            for item in paired_items:
                filtered_items.extend([item, item + ' Orçado'])
        else:
            filtered_items = all_items
        
        # Multi-select for specific items
        selected_items = st.sidebar.multiselect(
            "Itens Específicos",
            options=filtered_items,
            default=filtered_items[:10] if len(filtered_items) > 10 else filtered_items
        )
        
        # Analysis type with budget analysis
        analysis_type = st.sidebar.selectbox(
            "📊 Tipo de Análise",
            ["Dashboard Executivo", "Análise Real vs Orçado", "Análise de Custos", "Performance por Empresa", "Análise Temporal"]
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
                # Executive KPIs with budget focus
                st.markdown('<h2 class="section-header">📈 Indicadores Executivos</h2>', unsafe_allow_html=True)
                
                # Calculate budget performance
                budget_analysis = calculate_budget_variance(df_melted, selected_companies, latest_date, selected_items)
                
                if len(budget_analysis) > 0:
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    # Portfolio budget performance
                    companies_only = budget_analysis[budget_analysis['Empresa'] != 'GERAL']
                    if len(companies_only) > 0:
                        total_real = companies_only['Valor_real'].sum()
                        total_budget = companies_only['Valor_orcado'].sum()
                        total_variance = total_real - total_budget
                        variance_pct = (total_variance / total_budget * 100) if total_budget != 0 else 0
                        
                        # Count favorable vs unfavorable variances
                        favorable = len(companies_only[companies_only['Variacao_Absoluta'] <= 0])
                        unfavorable = len(companies_only[companies_only['Variacao_Absoluta'] > 0])
                        
                        with col1:
                            st.metric(
                                "💰 Real vs Orçado",
                                f"R$ {total_real:,.0f}",
                                f"{variance_pct:+.1f}%",
                                delta_color="inverse",
                                help="Total realizado vs orçado"
                            )
                        
                        with col2:
                            st.metric(
                                "📊 Variação Total",
                                f"R$ {total_variance:+,.0f}",
                                help="Diferença absoluta real vs orçado"
                            )
                        
                        with col3:
                            st.metric(
                                "✅ Itens Favoráveis",
                                f"{favorable}",
                                help="Itens abaixo do orçado"
                            )
                        
                        with col4:
                            st.metric(
                                "⚠️ Itens Desfavoráveis",
                                f"{unfavorable}",
                                help="Itens acima do orçado"
                            )
                        
                        with col5:
                            accuracy = (favorable / (favorable + unfavorable) * 100) if (favorable + unfavorable) > 0 else 0
                            st.metric(
                                "🎯 Precisão Orçamentária",
                                f"{accuracy:.1f}%",
                                help="% de itens dentro/abaixo do orçado"
                            )
                
                st.markdown("---")
                
                # Main visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Performance Orçamentária")
                    if len(budget_analysis) > 0:
                        # Show top variances
                        companies_budget = budget_analysis[budget_analysis['Empresa'] != 'GERAL'].copy()
                        companies_budget = companies_budget.sort_values('Variacao_Percentual', ascending=True)
                        
                        fig_budget = go.Figure()
                        
                        # Add budget bars
                        fig_budget.add_trace(go.Bar(
                            name='Orçado',
                            x=companies_budget['Empresa'],
                            y=companies_budget['Valor_orcado'],
                            marker_color='lightblue',
                            opacity=0.7
                        ))
                        
                        # Add actual bars
                        fig_budget.add_trace(go.Bar(
                            name='Real',
                            x=companies_budget['Empresa'],
                            y=companies_budget['Valor_real'],
                            marker_color='darkblue'
                        ))
                        
                        fig_budget.update_layout(
                            title="Real vs Orçado por Empresa",
                            barmode='group',
                            height=400,
                            xaxis_tickangle=45
                        )
                        st.plotly_chart(fig_budget, use_container_width=True)
                
                with col2:
                    st.subheader("🎯 Análise de Variação")
                    if len(budget_analysis) > 0:
                        companies_budget = budget_analysis[budget_analysis['Empresa'] != 'GERAL'].copy()
                        
                        # Create variance waterfall
                        fig_variance = go.Figure(go.Waterfall(
                            name="Variações",
                            orientation="v",
                            measure=["relative"] * len(companies_budget),
                            x=companies_budget['Empresa'],
                            y=companies_budget['Variacao_Absoluta'],
                            text=[f"R$ {x:+,.0f}" for x in companies_budget['Variacao_Absoluta']],
                            textposition="outside",
                            connector={"line": {"color": "rgb(63, 63, 63)"}},
                            increasing={"marker": {"color": "red"}},
                            decreasing={"marker": {"color": "green"}},
                        ))
                        fig_variance.update_layout(
                            title="Variações Orçamentárias por Empresa",
                            height=400,
                            xaxis_tickangle=45
                        )
                        st.plotly_chart(fig_variance, use_container_width=True)
                
                # Budget accuracy by category
                st.subheader("📋 Precisão Orçamentária por Categoria")
                if len(budget_analysis) > 0:
                    category_accuracy = budget_analysis.groupby('Categoria').agg({
                        'Valor_real': 'sum',
                        'Valor_orcado': 'sum',
                        'Variacao_Absoluta': 'sum',
                        'Variacao_Percentual': 'mean'
                    }).reset_index()
                    
                    category_accuracy['Precisao'] = np.abs(category_accuracy['Variacao_Percentual'])
                    category_accuracy = category_accuracy.sort_values('Precisao')
                    
                    fig_accuracy = px.bar(
                        category_accuracy,
                        x='Categoria',
                        y='Precisao',
                        title="Desvio Médio por Categoria (%)",
                        color='Precisao',
                        color_continuous_scale='RdYlGn_r'
                    )
                    fig_accuracy.update_layout(height=400, xaxis_tickangle=45)
                    st.plotly_chart(fig_accuracy, use_container_width=True)
            
            elif analysis_type == "Análise Real vs Orçado":
                st.markdown('<h2 class="section-header">🎯 Análise Detalhada Real vs Orçado</h2>', unsafe_allow_html=True)
                
                budget_analysis = calculate_budget_variance(df_melted, selected_companies, latest_date, selected_items)
                
                if len(budget_analysis) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📈 Comparação Temporal")
                        
                        # Time series comparison for selected items
                        time_comparison = filtered_data[
                            (filtered_data['Empresa'].isin(selected_companies + ['GERAL'])) &
                            (filtered_data['Item'].isin(selected_items))
                        ].copy()
                        
                        # Aggregate by date and item type
                        time_agg = time_comparison.groupby(['Data', 'Tipo_Item'])['Valor'].sum().reset_index()
                        
                        fig_time = px.line(
                            time_agg,
                            x='Data',
                            y='Valor',
                            color='Tipo_Item',
                            title="Evolução Real vs Orçado",
                            labels={'Valor': 'Valor (R$)', 'Tipo_Item': 'Tipo'},
                            markers=True
                        )
                        fig_time.update_layout(height=400)
                        st.plotly_chart(fig_time, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Dispersão de Variações")
                        
                        companies_budget = budget_analysis[budget_analysis['Empresa'] != 'GERAL'].copy()
                        
                        fig_scatter = px.scatter(
                            companies_budget,
                            x='Valor_orcado',
                            y='Valor_real',
                            text='Empresa',
                            size='Variacao_Absoluta',
                            color='Variacao_Percentual',
                            title="Real vs Orçado - Dispersão",
                            labels={'Valor_orcado': 'Orçado (R$)', 'Valor_real': 'Real (R$)'},
                            color_continuous_scale='RdYlGn_r'
                        )
                        
                        # Add diagonal line (perfect budget)
                        max_val = max(companies_budget['Valor_orcado'].max(), companies_budget['Valor_real'].max())
                        fig_scatter.add_shape(
                            type="line",
                            x0=0, y0=0, x1=max_val, y1=max_val,
                            line=dict(color="gray", width=2, dash="dash")
                        )
                        
                        fig_scatter.update_traces(textposition='top center')
                        fig_scatter.update_layout(height=400)
                        st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # Detailed variance table
                    st.subheader("📋 Tabela Detalhada de Variações")
                    
                    # Format table for display
                    display_budget = budget_analysis.copy()
                    display_budget = display_budget[display_budget['Empresa'] != 'GERAL']
                    display_budget = display_budget.sort_values('Variacao_Percentual', key=abs, ascending=False)
                    
                    # Format values
                    display_budget['Real'] = display_budget['Valor_real'].apply(lambda x: f"R$ {x:,.2f}")
                    display_budget['Orçado'] = display_budget['Valor_orcado'].apply(lambda x: f"R$ {x:,.2f}")
                    display_budget['Var. Absoluta'] = display_budget['Variacao_Absoluta'].apply(lambda x: f"R$ {x:+,.2f}")
                    display_budget['Var. %'] = display_budget['Variacao_Percentual'].apply(lambda x: f"{x:+.1f}%")
                    
                    st.dataframe(
                        display_budget[['Empresa', 'Item_Base', 'Real', 'Orçado', 'Var. Absoluta', 'Var. %']],
                        use_container_width=True
                    )
                    
                    # Download variance analysis
                    csv_variance = budget_analysis.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Análise de Variação",
                        data=csv_variance,
                        file_name=f'analise_variacao_{datetime.now().strftime("%Y%m%d")}.csv',
                        mime='text/csv'
                    )
            
            elif analysis_type == "Análise de Custos":
                st.markdown('<h2 class="section-header">💰 Análise Detalhada de Custos</h2>', unsafe_allow_html=True)
                
                # Filter cost data (excluding volume)
                cost_data = filtered_data[
                    (filtered_data['Categoria'] != 'Volume') &
                    (filtered_data['Empresa'].isin(selected_companies + ['GERAL']))
                ]
                
                if len(cost_data) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📈 Evolução dos Custos Principais")
                        
                        # Monthly cost evolution by category
                        monthly_costs = cost_data.groupby(['Data', 'Categoria', 'Tipo_Item'])['Valor'].sum().reset_index()
                        
                        fig_evolution = px.line(
                            monthly_costs,
                            x='Data',
                            y='Valor',
                            color='Categoria',
                            line_dash='Tipo_Item',
                            title="Evolução Mensal dos Custos por Categoria",
                            labels={'Valor': 'Custo (R$)', 'Data': 'Período'}
                        )
                        fig_evolution.update_layout(height=400)
                        st.plotly_chart(fig_evolution, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Participação por Categoria")
                        
                        # Cost breakdown by real vs budget
                        latest_costs = cost_data[cost_data['Data'] == latest_date]
                        category_breakdown = latest_costs.groupby(['Categoria', 'Tipo_Item'])['Valor'].sum().reset_index()
                        
                        fig_breakdown = px.sunburst(
                            category_breakdown,
                            path=['Tipo_Item', 'Categoria'],
                            values='Valor',
                            title="Distribuição dos Custos"
                        )
                        fig_breakdown.update_layout(height=400)
                        st.plotly_chart(fig_breakdown, use_container_width=True)
                    
                    # Cost trend analysis
                    st.subheader("📊 Análise de Tendência de Custos")
                    
                    # Calculate month-over-month growth
                    monthly_total = cost_data.groupby(['Data', 'Tipo_Item'])['Valor'].sum().reset_index()
                    monthly_total = monthly_total.sort_values('Data')
                    monthly_total['MoM_Growth'] = monthly_total.groupby('Tipo_Item')['Valor'].pct_change() * 100
                    
                    fig_growth = px.bar(
                        monthly_total,
                        x='Data',
                        y='MoM_Growth',
                        color='Tipo_Item',
                        title="Crescimento Mensal dos Custos (%)",
                        labels={'MoM_Growth': 'Crescimento M/M (%)'}
                    )
                    fig_growth.update_layout(height=400)
                    st.plotly_chart(fig_growth, use_container_width=True)
            
            elif analysis_type == "Performance por Empresa":
                st.markdown('<h2 class="section-header">🏢 Performance Comparativa por Empresa</h2>', unsafe_allow_html=True)
                
                if len(selected_companies) > 0:
                    # Company performance with budget focus
                    company_data = filtered_data[
                        (filtered_data['Empresa'].isin(selected_companies)) &
                        (filtered_data['Data'] == latest_date)
                    ]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🎯 Budget Performance por Empresa")
                        
                        budget_perf = calculate_budget_variance(df_melted, selected_companies, latest_date, selected_items)
                        
                        if len(budget_perf) > 0:
                            company_summary = budget_perf.groupby('Empresa').agg({
                                'Valor_real': 'sum',
                                'Valor_orcado': 'sum',
                                'Variacao_Absoluta': 'sum'
                            }).reset_index()
                            
                            company_summary['Variacao_Percentual'] = (
                                company_summary['Variacao_Absoluta'] / company_summary['Valor_orcado'] * 100
                            )
                            
                            fig_perf = px.bar(
                                company_summary[company_summary['Empresa'] != 'GERAL'],
                                x='Empresa',
                                y='Variacao_Percentual',
                                title="Variação Orçamentária por Empresa (%)",
                                color='Variacao_Percentual',
                                color_continuous_scale='RdYlGn_r'
                            )
                            fig_perf.update_layout(height=400, xaxis_tickangle=45)
                            fig_perf.add_hline(y=0, line_dash="dash", line_color="gray")
                            st.plotly_chart(fig_perf, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Composição de Custos")
                        
                        company_costs = company_data[
                            company_data['Categoria'] != 'Volume'
                        ].groupby(['Empresa', 'Categoria'])['Valor'].sum().reset_index()
                        
                        fig_composition = px.bar(
                            company_costs,
                            x='Empresa',
                            y='Valor',
                            color='Categoria',
                            title="Composição de Custos por Empresa",
                            labels={'Valor': 'Custo (R$)'}
                        )
                        fig_composition.update_layout(height=400, xaxis_tickangle=45)
                        st.plotly_chart(fig_composition, use_container_width=True)
                    
                    # Performance ranking
                    st.subheader("🏆 Ranking de Performance Orçamentária")
                    
                    if len(budget_perf) > 0:
                        ranking_data = company_summary[company_summary['Empresa'] != 'GERAL'].copy()
                        ranking_data['Eficiencia'] = np.where(
                            ranking_data['Variacao_Percentual'] <= 0, 'Favorável', 'Desfavorável'
                        )
                        ranking_data = ranking_data.sort_values('Variacao_Percentual')
                        ranking_data['Posição'] = range(1, len(ranking_data) + 1)
                        
                        # Format for display
                        ranking_display = ranking_data[['Posição', 'Empresa', 'Valor_real', 'Valor_orcado', 'Variacao_Absoluta', 'Variacao_Percentual', 'Eficiencia']].copy()
                        ranking_display.columns = ['🏆 Pos.', '🏢 Empresa', '💰 Real', '📊 Orçado', '📈 Var. Abs.', '📉 Var. %', '⭐ Status']
                        
                        # Apply styling
                        def style_performance(val):
                            if 'Favorável' in str(val):
                                return 'background-color: #d4edda; color: #155724'
                            elif 'Desfavorável' in str(val):
                                return 'background-color: #f8d7da; color: #721c24'
                            return ''
                        
                        styled_df = ranking_display.style.applymap(style_performance, subset=['⭐ Status'])
                        st.dataframe(styled_df, use_container_width=True)
            
            elif analysis_type == "Análise Temporal":
                st.markdown('<h2 class="section-header">⏱️ Análise de Tendências Temporais</h2>', unsafe_allow_html=True)
                
                temporal_data = filtered_data[
                    (filtered_data['Categoria'] != 'Volume') &
                    (filtered_data['Empresa'].isin(selected_companies + ['GERAL']))
                ]
                
                if len(temporal_data) > 0:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📈 Tendências Real vs Orçado")
                        
                        # Monthly trends by type
                        monthly_trends = temporal_data.groupby(['Data', 'Tipo_Item'])['Valor'].sum().reset_index()
                        
                        fig_trends = px.line(
                            monthly_trends,
                            x='Data',
                            y='Valor',
                            color='Tipo_Item',
                            title="Evolução Temporal Real vs Orçado",
                            labels={'Valor': 'Valor (R$)', 'Data': 'Período'},
                            markers=True
                        )
                        fig_trends.update_layout(height=400)
                        st.plotly_chart(fig_trends, use_container_width=True)
                    
                    with col2:
                        st.subheader("📊 Análise de Sazonalidade")
                        
                        # Seasonal analysis
                        seasonal_data = temporal_data.copy()
                        seasonal_data['Month'] = seasonal_data['Data'].dt.month
                        seasonal_summary = seasonal_data.groupby(['Month', 'Tipo_Item'])['Valor'].mean().reset_index()
                        
                        fig_seasonal = px.line(
                            seasonal_summary,
                            x='Month',
                            y='Valor',
                            color='Tipo_Item',
                            title="Padrão Sazonal (Média Mensal)",
                            labels={'Month': 'Mês', 'Valor': 'Valor Médio (R$)'},
                            markers=True
                        )
                        fig_seasonal.update_layout(height=400)
                        st.plotly_chart(fig_seasonal, use_container_width=True)
                    
                    # Budget accuracy over time
                    st.subheader("📊 Evolução da Precisão Orçamentária")
                    
                    # Calculate monthly budget accuracy
                    monthly_accuracy = []
                    for date in temporal_data['Data'].unique():
                        month_variance = calculate_budget_variance(df_melted, selected_companies, date, selected_items)
                        if len(month_variance) > 0:
                            accuracy = len(month_variance[month_variance['Variacao_Percentual'] <= 5]) / len(month_variance) * 100
                            monthly_accuracy.append({'Data': date, 'Precisao': accuracy})
                    
                    if monthly_accuracy:
                        accuracy_df = pd.DataFrame(monthly_accuracy)
                        
                        fig_accuracy = px.line(
                            accuracy_df,
                            x='Data',
                            y='Precisao',
                            title="Evolução da Precisão Orçamentária (%)",
                            labels={'Precisao': 'Precisão (%)', 'Data': 'Período'},
                            markers=True
                        )
                        fig_accuracy.add_hline(y=80, line_dash="dash", line_color="green", 
                                             annotation_text="Meta: 80%")
                        fig_accuracy.update_layout(height=400)
                        st.plotly_chart(fig_accuracy, use_container_width=True)
            
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
                if st.button("🎯 Exportar Análise Orçamentária", use_container_width=True):
                    budget_analysis = calculate_budget_variance(df_melted, selected_companies, latest_date, selected_items)
                    if len(budget_analysis) > 0:
                        budget_csv = budget_analysis.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download Orçamento CSV",
                            data=budget_csv,
                            file_name=f'analise_orcamentaria_{datetime.now().strftime("%Y%m%d")}.csv',
                            mime='text/csv'
                        )
        
        # Enhanced Methodology section
        with st.expander("📖 Metodologia e Definições"):
            st.markdown("""
            ### 📊 Fonte dos Dados
            - **Base**: Dados consolidados mensais de todas as empresas do grupo Global Eggs
            - **Período**: Janeiro 2024 a Maio 2025
            - **Estrutura**: Valores reais e orçados para comparação de performance
            
            ### 🎯 Categorização de Itens
            - **Volume**: Caixas Vendidas e Caixas Produzidas
            - **Custos Diretos**: Ração, Embalagem, Logística, Produção MO
            - **Custos Indiretos**: Manutenção, Utilidades, Sanidade Animal
            - **Despesas**: Vendas, Administrativas, Tributárias
            - **Outros**: Integração, Exportação, Suporte, Perdas
            
            ### 📈 Análise Orçamentária
            - **Variação Absoluta**: Valor Real - Valor Orçado
            - **Variação Percentual**: (Variação Absoluta / Valor Orçado) × 100
            - **Performance Favorável**: Variação ≤ 0% (abaixo do orçado)
            - **Performance Desfavorável**: Variação > 0% (acima do orçado)
            - **Precisão Orçamentária**: % de itens com variação ≤ 5%
            
            ### 🔍 Filtros Disponíveis
            - **Período**: Intervalo de datas para análise
            - **Empresas**: Seleção múltipla de subsidiárias
            - **Tipo de Caixa**: Vendidas vs Produzidas
            - **Tipo de Item**: Reais, Orçados ou Pares comparativos
            - **Itens Específicos**: Seleção granular de categorias
            
            ### ⚠️ Observações Importantes
            - Valores em R$ (Reais brasileiros)
            - GERAL representa o consolidado do grupo
            - Análises baseadas no último mês disponível
            - Cores: Verde = Favorável, Vermelho = Desfavorável
            - Meta de precisão orçamentária: 80% dos itens com variação ≤ 5%
            """)
    
else:
    st.info("👆 Por favor, faça upload do arquivo Excel para acessar o Dashboard Executivo.")
    
    # Enhanced data structure info
    with st.expander("📋 Estrutura Esperada dos Dados"):
        st.markdown("""
        ## 📊 Estrutura da Base de Dados com Orçamento
        
        O arquivo deve conter dados reais e orçados seguindo a estrutura:
        
        ### 📝 Colunas Obrigatórias:
        | Coluna | Tipo | Descrição | Exemplo |
        |--------|------|-----------|---------|
        | **Empresa** | Texto | Nome da subsidiária | JOSIDITH, MARUTANI, etc. |
        | **Tipo de Caixa** | Texto | Tipo de volume | "Caixas Vendidas" ou "Caixas Produzidas" |
        | **Item** | Texto | Item real ou orçado | "Custo Ração" ou "Custo Ração Orçado" |
        | **jan/24...mai/25** | Numérico | Valores mensais | Formato mmm/aa |
        
        ### 🎯 Itens de Análise Real vs Orçado:
        
        **Custos Principais:**
        - Custo Ração / Custo Ração Orçado
        - Custo Logística / Custo Logística Orçado
        - Custo Embalagem / Custo Embalagem Orçado
        - Custo Produção MO / Custo Produção MO Orçado
        
        **Despesas:**
        - Despesas Vendas / Despesas Vendas Orçado
        - Despesas Administrativas / Despesas Administrativas Orçado
        - Despesas Tributárias / Despesas Tributárias Orçado
        
        **Outros Custos:**
        - Custo Manutenção / Custo Manutenção Orçado
        - Custo Utilidades / Custo Utilidades Orçado
        - Custos Vacinas e Medicamentos / Custos Vacinas e Medicamentos Orçado
        
        ### 📊 Empresas do Grupo:
        JOSIDITH, MARUTANI, STRAGLIOTTO, ASA, IANA, AVIMOR, ALEXAVES, 
        MACIAMBU, BL GO, BL STA MARIA, KATAYAMA, VITAGEMA, TAMAGO
        
        **Consolidado:** GERAL (soma de todas as subsidiárias)
        
        ### 🎯 Funcionalidades de Análise:
        1. **Dashboard Executivo**: Visão geral com foco em performance orçamentária
        2. **Análise Real vs Orçado**: Comparação detalhada com variações
        3. **Análise de Custos**: Evolução e composição dos custos
        4. **Performance por Empresa**: Ranking e comparação entre subsidiárias
        5. **Análise Temporal**: Tendências e sazonalidade dos dados
        """)

# Run command: streamlit run app.py
