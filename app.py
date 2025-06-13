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
    elif 'Custo Ração' in str(item):
        return 'Custo Ração'
    elif 'Custo Logística' in str(item):
        return 'Custo Logística'
    elif 'Custo Embalagem' in str(item):
        return 'Custo Embalagem'
    elif 'Custo Produção' in str(item):
        return 'Custo Produção'
    elif 'Custo Manutenção' in str(item):
        return 'Custo Manutenção'
    elif 'Custo Utilidades' in str(item):
        return 'Custo Utilidades'
    elif 'Custo Exportação' in str(item):
        return 'Custo Exportação'
    elif 'Despesas' in str(item):
        return 'Despesas Operacionais'
    elif 'Depreciação' in str(item):
        return 'Depreciação'
    elif 'Suporte' in str(item):
        return 'Suporte Operacional'
    elif 'Vacinas' in str(item) or 'Medicamentos' in str(item):
        return 'Sanidade Animal'
    elif 'Integração' in str(item):
        return 'Integração'
    elif 'Perdas' in str(item):
        return 'Perdas Operacionais'
    elif 'Custo Caixa' in str(item):
        return 'Custo Caixa Total'
    else:
        return 'Outros'

def safe_divide(a, b):
    """Safe division to avoid division by zero and NaN issues"""
    try:
        if pd.isna(a) or pd.isna(b) or b == 0:
            return 0
        result = a / b
        if pd.isna(result) or np.isinf(result):
            return 0
        return result
    except:
        return 0

def clean_data_for_charts(df):
    """Clean data to avoid chart errors"""
    if df is None or len(df) == 0:
        return df
    
    # Replace NaN and infinite values
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Remove any remaining problematic values
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def calculate_budget_variance(df, selected_companies, latest_date, selected_items):
    """Calculate budget variance analysis with error handling"""
    try:
        # Filter data for analysis
        analysis_data = df[
            (df['Data'] == latest_date) &
            (df['Empresa'].isin(selected_companies + ['GERAL'])) &
            (df['Item'].isin(selected_items))
        ].copy()
        
        if len(analysis_data) == 0:
            return pd.DataFrame()
        
        # Separate real and budget data
        real_data = analysis_data[analysis_data['Tipo_Item'] == 'Real'].copy()
        budget_data = analysis_data[analysis_data['Tipo_Item'] == 'Orçado'].copy()
        
        if len(real_data) == 0 and len(budget_data) == 0:
            return pd.DataFrame()
        
        # Merge real and budget data
        budget_analysis = real_data.merge(
            budget_data[['Empresa', 'Item_Base', 'Valor']], 
            on=['Empresa', 'Item_Base'], 
            suffixes=('_real', '_orcado'),
            how='outer'
        ).fillna(0)
        
        if len(budget_analysis) == 0:
            return pd.DataFrame()
        
        # Calculate variances with safe division
        budget_analysis['Variacao_Absoluta'] = budget_analysis['Valor_real'] - budget_analysis['Valor_orcado']
        budget_analysis['Variacao_Percentual'] = budget_analysis.apply(
            lambda row: safe_divide(row['Variacao_Absoluta'], row['Valor_orcado']) * 100,
            axis=1
        )
        
        # Clean the data
        budget_analysis = clean_data_for_charts(budget_analysis)
        
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
        
        # Enhanced Item filter based on actual Excel structure
        st.sidebar.markdown("### 🎯 Filtro de Itens")
        
        # Get all unique items (excluding volume items and showing only base names)
        all_items = sorted(df_melted['Item'].unique())
        
        # Categorize items based on what we see in the Excel
        volume_items = [item for item in all_items if 'Caixas' in item]
        cost_items = [item for item in all_items if 'Custo' in item]
        expense_items = [item for item in all_items if 'Despesas' in item]
        other_items = [item for item in all_items if item not in volume_items + cost_items + expense_items]
        
        # Item category selection
        item_category = st.sidebar.selectbox(
            "Categoria de Itens",
            ["Todos", "Custos", "Despesas", "Outros", "Seleção Manual"]
        )
        
        if item_category == "Custos":
            available_items = cost_items
        elif item_category == "Despesas":
            available_items = expense_items
        elif item_category == "Outros":
            available_items = other_items
        elif item_category == "Seleção Manual":
            available_items = [item for item in all_items if 'Caixas' not in item]
        else:
            available_items = [item for item in all_items if 'Caixas' not in item]
        
        # Multi-select for specific items
        selected_items = st.sidebar.multiselect(
            "Itens Específicos",
            options=available_items,
            default=available_items[:10] if len(available_items) > 10 else available_items
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
                        variance_pct = safe_divide(total_variance, total_budget) * 100
                        
                        # Count favorable vs unfavorable variances
                        favorable = len(companies_only[companies_only['Variacao_Absoluta'] <= 0])
                        unfavorable = len(companies_only[companies_only['Variacao_Absoluta'] > 0])
                        
                        with col1:
                            st.metric(
                                "💰 Real vs Orçado",
                                f"R$ {total_real:,.0f}",
                                f"{variance_pct:+.1f}%" if variance_pct != 0 else None,
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
                            accuracy = safe_divide(favorable, (favorable + unfavorable)) * 100
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
                        
                        if len(companies_budget) > 0:
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
                        else:
                            st.info("Não há dados suficientes para o gráfico de performance orçamentária.")
                
                with col2:
                    st.subheader("🎯 Análise de Variação")
                    if len(budget_analysis) > 0:
                        companies_budget = budget_analysis[budget_analysis['Empresa'] != 'GERAL'].copy()
                        
                        if len(companies_budget) > 0:
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
                        else:
                            st.info("Não há dados suficientes para o gráfico de variação.")
                
                # Budget accuracy by category
                st.subheader("📋 Precisão Orçamentária por Categoria")
                if len(budget_analysis) > 0:
                    try:
                        category_accuracy = budget_analysis.groupby('Categoria').agg({
                            'Valor_real': 'sum',
                            'Valor_orcado': 'sum',
                            'Variacao_Absoluta': 'sum',
                            'Variacao_Percentual': 'mean'
                        }).reset_index()
                        
                        category_accuracy['Precisao'] = np.abs(category_accuracy['Variacao_Percentual'])
                        category_accuracy = category_accuracy.sort_values('Precisao')
                        category_accuracy = clean_data_for_charts(category_accuracy)
                        
                        if len(category_accuracy) > 0:
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
                        else:
                            st.info("Não há dados suficientes para análise por categoria.")
                    except Exception as e:
                        st.error(f"Erro na análise por categoria: {str(e)}")
            
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
                        
                        if len(time_comparison) > 0:
                            # Aggregate by date and item type
                            time_agg = time_comparison.groupby(['Data', 'Tipo_Item'])['Valor'].sum().reset_index()
                            time_agg = clean_data_for_charts(time_agg)
                            
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
                        else:
                            st.info("Não há dados suficientes para comparação temporal.")
                    
                    with col2:
                        st.subheader("📊 Dispersão de Variações")
                        
                        companies_budget = budget_analysis[budget_analysis['Empresa'] != 'GERAL'].copy()
                        companies_budget = clean_data_for_charts(companies_budget)
                        
                        if len(companies_budget) > 0 and companies_budget['Valor_orcado'].sum() > 0:
                            try:
                                fig_scatter = px.scatter(
                                    companies_budget,
                                    x='Valor_orcado',
                                    y='Valor_real',
                                    text='Empresa',
                                    size='Variacao_Absoluta',
                                    title="Real vs Orçado - Dispersão",
                                    labels={'Valor_orcado': 'Orçado (R$)', 'Valor_real': 'Real (R$)'}
                                )
                                
                                # Add diagonal line (perfect budget)
                                max_val = max(companies_budget['Valor_orcado'].max(), companies_budget['Valor_real'].max())
                                if max_val > 0:
                                    fig_scatter.add_shape(
                                        type="line",
                                        x0=0, y0=0, x1=max_val, y1=max_val,
                                        line=dict(color="gray", width=2, dash="dash")
                                    )
                                
                                fig_scatter.update_traces(textposition='top center')
                                fig_scatter.update_layout(height=400)
                                st.plotly_chart(fig_scatter, use_container_width=True)
                            except Exception as e:
                                st.error(f"Erro no gráfico de dispersão: {str(e)}")
                                st.info("Usando gráfico alternativo...")
                                
                                # Alternative simpler chart
                                fig_alt = px.bar(
                                    companies_budget,
                                    x='Empresa',
                                    y=['Valor_real', 'Valor_orcado'],
                                    title="Comparação Real vs Orçado",
                                    barmode='group'
                                )
                                fig_alt.update_layout(height=400, xaxis_tickangle=45)
                                st.plotly_chart(fig_alt, use_container_width=True)
                        else:
                            st.info("Não há dados suficientes para o gráfico de dispersão.")
                    
                    # Detailed variance table
                    st.subheader("📋 Tabela Detalhada de Variações")
                    
                    # Format table for display
                    display_budget = budget_analysis.copy()
                    display_budget = display_budget[display_budget['Empresa'] != 'GERAL']
                    display_budget = display_budget.sort_values('Variacao_Percentual', key=abs, ascending=False)
                    
                    if len(display_budget) > 0:
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
                    else:
                        st.info("Não há dados de variação para exibir.")
                else:
                    st.info("Não há dados suficientes para análise orçamentária. Verifique se há itens com versões 'Real' e 'Orçado'.")
            
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
                        monthly_costs = clean_data_for_charts(monthly_costs)
                        
                        if len(monthly_costs) > 0:
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
                        else:
                            st.info("Não há dados suficientes para análise de evolução.")
                    
                    with col2:
                        st.subheader("📊 Participação por Categoria")
                        
                        # Cost breakdown by real vs budget
                        latest_costs = cost_data[cost_data['Data'] == latest_date]
                        if len(latest_costs) > 0:
                            category_breakdown = latest_costs.groupby(['Categoria', 'Tipo_Item'])['Valor'].sum().reset_index()
                            category_breakdown = clean_data_for_charts(category_breakdown)
                            
                            if len(category_breakdown) > 0:
                                fig_breakdown = px.sunburst(
                                    category_breakdown,
                                    path=['Tipo_Item', 'Categoria'],
                                    values='Valor',
                                    title="Distribuição dos Custos"
                                )
                                fig_breakdown.update_layout(height=400)
                                st.plotly_chart(fig_breakdown, use_container_width=True)
                            else:
                                st.info("Não há dados suficientes para breakdown por categoria.")
                        else:
                            st.info("Não há dados para o período selecionado.")
                    
                    # Cost trend analysis
                    st.subheader("📊 Análise de Tendência de Custos")
                    
                    # Calculate month-over-month growth
                    monthly_total = cost_data.groupby(['Data', 'Tipo_Item'])['Valor'].sum().reset_index()
                    if len(monthly_total) > 0:
                        monthly_total = monthly_total.sort_values('Data')
                        monthly_total['MoM_Growth'] = monthly_total.groupby('Tipo_Item')['Valor'].pct_change() * 100
                        monthly_total = clean_data_for_charts(monthly_total)
                        
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
                    else:
                        st.info("Não há dados suficientes para análise de tendência.")
                else:
                    st.info("Não há dados de custos para análise.")
            
            elif analysis_type == "Performance por Empresa":
                st.markdown('<h2 class="section-header">🏢 Performance Comparativa por Empresa</h2>', unsafe_allow_html=True)
                
                if len(selected_companies) > 0:
                    # Company performance with budget focus
                    company_data = filtered_data[
                        (filtered_data['Empresa'].isin(selected_companies)) &
                        (filtered_data['Data'] == latest_date)
                    ]
                    
                    if len(company_data) > 0:
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
                                
                                company_summary['Variacao_Percentual'] = company_summary.apply(
                                    lambda row: safe_divide(row['Variacao_Absoluta'], row['Valor_orcado']) * 100,
                                    axis=1
                                )
                                company_summary = clean_data_for_charts(company_summary)
                                
                                companies_only = company_summary[company_summary['Empresa'] != 'GERAL']
                                if len(companies_only) > 0:
                                    fig_perf = px.bar(
                                        companies_only,
                                        x='Empresa',
                                        y='Variacao_Percentual',
                                        title="Variação Orçamentária por Empresa (%)",
                                        color='Variacao_Percentual',
                                        color_continuous_scale='RdYlGn_r'
                                    )
                                    fig_perf.update_layout(height=400, xaxis_tickangle=45)
                                    fig_perf.add_hline(y=0, line_dash="dash", line_color="gray")
                                    st.plotly_chart(fig_perf, use_container_width=True)
                                else:
                                    st.info("Não há dados de empresas para análise de performance orçamentária.")
                            else:
                                st.info("Não há dados suficientes para análise de performance orçamentária.")
                        
                        with col2:
                            st.subheader("📊 Composição de Custos")
                            
                            company_costs = company_data[
                                company_data['Categoria'] != 'Volume'
                            ].groupby(['Empresa', 'Categoria'])['Valor'].sum().reset_index()
                            company_costs = clean_data_for_charts(company_costs)
                            
                            if len(company_costs) > 0:
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
                            else:
                                st.info("Não há dados de custos por empresa.")
                        
                        # Performance ranking
                        st.subheader("🏆 Ranking de Performance Orçamentária")
                        
                        budget_perf = calculate_budget_variance(df_melted, selected_companies, latest_date, selected_items)
                        if len(budget_perf) > 0:
                            company_summary = budget_perf.groupby('Empresa').agg({
                                'Valor_real': 'sum',
                                'Valor_orcado': 'sum',
                                'Variacao_Absoluta': 'sum'
                            }).reset_index()
                            
                            company_summary['Variacao_Percentual'] = company_summary.apply(
                                lambda row: safe_divide(row['Variacao_Absoluta'], row['Valor_orcado']) * 100,
                                axis=1
                            )
                            
                            ranking_data = company_summary[company_summary['Empresa'] != 'GERAL'].copy()
                            if len(ranking_data) > 0:
                                ranking_data['Eficiencia'] = np.where(
                                    ranking_data['Variacao_Percentual'] <= 0, 'Favorável', 'Desfavorável'
                                )
                                ranking_data = ranking_data.sort_values('Variacao_Percentual')
                                ranking_data['Posição'] = range(1, len(ranking_data) + 1)
                                
                                # Format for display
                                ranking_display = ranking_data[['Posição', 'Empresa', 'Valor_real', 'Valor_orcado', 'Variacao_Absoluta', 'Variacao_Percentual', 'Eficiencia']].copy()
                                ranking_display.columns = ['🏆 Pos.', '🏢 Empresa', '💰 Real', '📊 Orçado', '📈 Var. Abs.', '📉 Var. %', '⭐ Status']
                                
                                st.dataframe(ranking_display, use_container_width=True)
                            else:
                                st.info("Não há dados para ranking de empresas.")
                        else:
                            st.info("Não há dados para ranking de performance orçamentária.")
                    else:
                        st.info("Não há dados para as empresas selecionadas no período.")
                else:
                    st.info("Selecione pelo menos uma empresa para análise.")
            
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
                        monthly_trends = clean_data_for_charts(monthly_trends)
                        
                        if len(monthly_trends) > 0:
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
                        else:
                            st.info("Não há dados suficientes para análise temporal.")
                    
                    with col2:
                        st.subheader("📊 Análise de Sazonalidade")
                        
                        # Seasonal analysis
                        seasonal_data = temporal_data.copy()
                        seasonal_data['Month'] = seasonal_data['Data'].dt.month
                        seasonal_summary = seasonal_data.groupby(['Month', 'Tipo_Item'])['Valor'].mean().reset_index()
                        seasonal_summary = clean_data_for_charts(seasonal_summary)
                        
                        if len(seasonal_summary) > 0:
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
                        else:
                            st.info("Não há dados suficientes para análise sazonal.")
                    
                    # Budget accuracy over time
                    st.subheader("📊 Evolução da Precisão Orçamentária")
                    
                    try:
                        # Calculate monthly budget accuracy
                        monthly_accuracy = []
                        unique_dates = temporal_data['Data'].unique()
                        
                        for date in unique_dates:
                            month_variance = calculate_budget_variance(df_melted, selected_companies, date, selected_items)
                            if len(month_variance) > 0:
                                # Consider items with less than 5% variance as accurate
                                accurate_items = len(month_variance[abs(month_variance['Variacao_Percentual']) <= 5])
                                total_items = len(month_variance)
                                accuracy = safe_divide(accurate_items, total_items) * 100
                                monthly_accuracy.append({'Data': date, 'Precisao': accuracy})
                        
                        if monthly_accuracy:
                            accuracy_df = pd.DataFrame(monthly_accuracy)
                            accuracy_df = clean_data_for_charts(accuracy_df)
                            
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
                        else:
                            st.info("Não há dados suficientes para análise de precisão ao longo do tempo.")
                    except Exception as e:
                        st.error(f"Erro na análise de precisão temporal: {str(e)}")
                else:
                    st.info("Não há dados temporais para análise.")
            
            # Export functionality
            st.markdown("---")
            st.subheader("📥 Exportar Dados")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Exportar Dados Filtrados", use_container_width=True):
                    if len(filtered_data) > 0:
                        csv_data = filtered_data.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv_data,
                            file_name=f'dados_filtrados_{datetime.now().strftime("%Y%m%d")}.csv',
                            mime='text/csv'
                        )
                    else:
                        st.warning("Não há dados para exportar.")
            
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
                    else:
                        st.warning("Não há dados orçamentários para exportar.")
        
        # Enhanced Methodology section
        with st.expander("📖 Metodologia e Definições"):
            st.markdown("""
            ### 📊 Fonte dos Dados
            - **Base**: Dados consolidados mensais de todas as empresas do grupo Global Eggs
            - **Período**: Janeiro 2024 a Maio 2025
            - **Estrutura**: Valores reais e orçados para comparação de performance
            
            ### 🎯 Categorização de Itens Disponíveis
            **Volume:**
            - Caixas Vendidas / Caixas Produzidas
            
            **Custos Diretos:**
            - Custo Ração, Custo Embalagem, Custo Logística
            - Custo Produção MO, Custo Exportação
            
            **Custos Indiretos:**
            - Custo Manutenção, Custos de Utilidades
            - Custos Vacinas e Medicamentos
            
            **Despesas:**
            - Despesas Vendas, Despesas Administrativas
            - Despesas Tributárias
            
            **Outros:**
            - Integração, Suporte Operação
            - Perdas Processo Produtivo
            - Depreciação Biológica/Não Biológica
            - Custo Caixa EBT, Custo Caixa Total
            
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
            - **Categoria de Itens**: Custos, Despesas, Outros
            - **Itens Específicos**: Seleção granular de categorias
            
            ### ⚠️ Observações Importantes
            - Valores em R$ (Reais brasileiros)
            - GERAL representa o consolidado do grupo
            - Análises baseadas no último mês disponível
            - Cores: Verde = Favorável, Vermelho = Desfavorável
            - Meta de precisão orçamentária: 80% dos itens com variação ≤ 5%
            - Tratamento automático de valores NaN e infinitos
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
        
        ### 🎯 Itens Identificados na Base:
        
        **Volume:**
        - Caixas Vendidas / Caixas Produzidas
        - Integração
        
        **Custos Principais:**
        - Custo Ração, Custo Logística, Custo Embalagem
        - Custo Produção MO, Custo Exportação
        - Custo Manutenção, Custos de Utilidades
        - Custos Vacinas e Medicamentos
        
        **Despesas:**
        - Despesas Vendas, Despesas Administrativas
        - Despesas Tributárias
        
        **Outros:**
        - Suporte Operação, Perdas Processo Produtivo
        - Depreciação Biológica, Depreciação Não Biológica
        - Custo Caixa EBT, Custo Caixa Total
        
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
        
        ### 🔧 Correções Implementadas:
        - Tratamento de valores NaN e infinitos
        - Validação de dados antes de gráficos
        - Divisão segura para evitar erros
        - Limpeza automática de dados problemáticos
        - Mensagens informativas quando não há dados suficientes
        """)

# Run command: streamlit run app.py
