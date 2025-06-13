# app.py  ─  v2 (sem Heat-map; novas visões “Plan × Real” e “Top Desvios”)
# ---------------------------------------------------------------------
# ▶ Run:  streamlit run app.py
# ▶ Reqs: streamlit, pandas, numpy, plotly, openpyxl
# ---------------------------------------------------------------------

import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ———————————————————  CONFIG  ———————————————————
st.set_page_config(
    page_title="Dashboard de Custo Caixa – Global Eggs",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🥚 Dashboard de Custo Caixa – Global Eggs e Subsidiárias")
st.markdown("---")

# ———————————————————  UPLOAD  ———————————————————
uploaded_file = st.file_uploader(
    "📁 Faça upload do arquivo **Base de dados Historico … .xlsx**",
    type=["xlsx"],
    help="Planilha deve conter a aba 'Base' com Empresa / Tipo de Caixa / Item e colunas mensais",
)

# ———————————————————  LOAD  ———————————————————
@st.cache_data(show_spinner=False)
def load_data(xls) -> pd.DataFrame:
    df = pd.read_excel(xls, sheet_name="Base")

    # nomes consistentes
    df.columns = df.columns.str.strip()
    rename = {
        "empresa/devolução": "Empresa",
        "empresa": "Empresa",
        "tipo de caixa": "Tipo de Caixa",
        "item": "Item",
        "itens": "Item",
        "categoria": "Item",
    }
    df = df.rename(columns={c: rename.get(c.lower(), c) for c in df.columns})

    # melt
    id_vars = ["Empresa", "Tipo de Caixa", "Item"]
    month_re = re.compile(r"([a-z]{3}/\d{2})\s*(orc|real)?", re.I)
    month_cols, meta = [], []

    for col in df.columns:
        m = month_re.fullmatch(str(col))
        if m:
            mstr, scen = m.groups()
            meta.append((col, mstr.lower(), (scen or "real").upper()))
            month_cols.append(col)

    if not month_cols:
        raise ValueError("Sem colunas mensais (ex.: 'jan/24 REAL').")

    long = df.melt(id_vars=id_vars, value_vars=month_cols, var_name="Col", value_name="Valor")
    meta_df = pd.DataFrame(meta, columns=["Col", "MesStr", "Cenário"])
    long = long.merge(meta_df, on="Col").drop(columns="Col")

    month_map = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
    }
    long["Mês"] = long["MesStr"].apply(lambda s: datetime(2000 + int(s[-2:]), month_map[s[:3]], 1))
    long = long.drop(columns="MesStr")
    long["Valor"] = pd.to_numeric(long["Valor"], errors="coerce")
    long = long.dropna(subset=["Valor"])

    # pivot Plan x Real
    piv = (
        long.pivot_table(index=["Empresa", "Mês", "Item"], columns="Cenário", values="Valor", aggfunc="sum")
        .reset_index()
        .fillna(0)
    )
    piv["DESVIO"] = piv["REAL"] - piv["ORC"]
    piv["DESVIO_%"] = np.where(piv["ORC"] != 0, piv["DESVIO"] / piv["ORC"], np.nan)
    return piv


if uploaded_file is None:
    st.info("👆 Faça upload para começar.")
    st.stop()

try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error(f"Erro: {e}")
    st.stop()

# ———————————————————  SIDEBAR FILTERS  ———————————————————
st.sidebar.header("🔧 Filtros")
emp = st.sidebar.multiselect("🏢 Empresas", sorted(df["Empresa"].unique()), default=sorted(df["Empresa"].unique()))
itens = st.sidebar.multiselect("💰 Itens", sorted(df["Item"].unique()), default=sorted(df["Item"].unique()))
cen = st.sidebar.radio("📊 Cenário", ["REAL", "ORC", "DESVIO"], index=0)
min_d, max_d = df["Mês"].min(), df["Mês"].max()
d_ini, d_fim = st.sidebar.slider("📅 Período", min_value=min_d, max_value=max_d, value=(min_d, max_d), format="MM/YYYY")

mask = (
    df["Empresa"].isin(emp) &
    df["Item"].isin(itens) &
    df["Mês"].between(d_ini, d_fim)
)
data = df.loc[mask].copy()
data["ValorSel"] = data[cen]

# ———————————————————  TABS  ———————————————————
tabs = st.tabs(["📈 Visão Geral", "🍰 Por Categoria", "📊 Plan × Real", "📋 Tabela"])

# —— 1. Visão Geral ——————————————————————————————————————
with tabs[0]:
    st.subheader("KPIs")
    grp = data.groupby("Mês")["ValorSel"].sum().reset_index()
    mes_atual = grp["Mês"].max()
    mes_ant = grp[grp["Mês"] < mes_atual]["Mês"].max()
    val_atual = grp.loc[grp["Mês"] == mes_atual, "ValorSel"].values[0]
    val_ant = grp.loc[grp["Mês"] == mes_ant, "ValorSel"].values[0] if pd.notna(mes_ant) else np.nan
    delta = (val_atual - val_ant) / val_ant * 100 if pd.notna(val_ant) and val_ant else 0

    col1, col2 = st.columns(2)
    col1.metric(f"Total {cen} ({mes_atual:%b/%y})", f"R$ {val_atual:,.2f}", f"{delta:+.1f}%")
    top_emp = (
        data[data["Mês"] == mes_atual]
        .groupby("Empresa")["ValorSel"]
        .sum()
        .sort_values()
    )
    if not top_emp.empty:
        col2.metric("Menor ↔ Maior custo", f"{top_emp.index[0]} ↔ {top_emp.index[-1]}",
                     f"R$ {top_emp.iloc[0]:,.0f} ↔ R$ {top_emp.iloc[-1]:,.0f}")

    st.markdown("---")
    # linha temporal total
    fig_tot = px.line(grp, x="Mês", y="ValorSel", title=f"Evolução Total – {cen}",
                      labels={"ValorSel": "R$", "Mês": "Mês"})
    st.plotly_chart(fig_tot, use_container_width=True)

# —— 2. Por Categoria ——————————————————————————————————————
with tabs[1]:
    st.subheader("Distribuição por Categoria")
    cat = data.groupby(["Mês", "Item"])["ValorSel"].sum().reset_index()
    fig_area = px.area(cat, x="Mês", y="ValorSel", color="Item",
                       title=f"Peso das Categorias – {cen}",
                       groupnorm="fraction", stackgroup="one")
    st.plotly_chart(fig_area, use_container_width=True)

# —— 3. Plan × Real (nova aba) ————————————————————————————
with tabs[2]:
    st.subheader("Plan × Real – Último Mês")
    ultimo = data[data["Mês"] == mes_atual].copy()

    # gráfico colunas agrupadas (Plan vs Real)
    bar_df = (
        ultimo.groupby("Empresa")[["ORC", "REAL", "DESVIO"]].sum()
        .reset_index()
        .sort_values("REAL", ascending=False)
    )

    fig_plan_real = go.Figure()
    fig_plan_real.add_bar(x=bar_df["Empresa"], y=bar_df["ORC"], name="ORC")
    fig_plan_real.add_bar(x=bar_df["Empresa"], y=bar_df["REAL"], name="REAL")
    fig_plan_real.update_layout(barmode="group", yaxis_title="R$", title=f"Plan x Real ({mes_atual:%b/%y})")
    st.plotly_chart(fig_plan_real, use_container_width=True)

    # gráfico barra divergente (desvio)
    desv = bar_df.sort_values("DESVIO")
    fig_desv = px.bar(desv, x="DESVIO", y="Empresa", orientation="h",
                      color="DESVIO", color_continuous_scale="RdYlGn",
                      title="Desvio (REAL − ORC)", labels={"DESVIO": "R$"})
    fig_desv.add_vline(x=0, line_dash="dot")
    st.plotly_chart(fig_desv, use_container_width=True)

# —— 4. Tabela ————————————————————————————————————————————
with tabs[3]:
    st.subheader("Tabela Detalhada")
    tbl = data[["Empresa", "Mês", "Item", "ORC", "REAL", "DESVIO", "DESVIO_%"]].copy()
    tbl["Mês"] = tbl["Mês"].dt.strftime("%b/%y")
    tbl["DESVIO_%"] = tbl["DESVIO_%"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "")

    st.dataframe(tbl, use_container_width=True, height=450)
    csv = tbl.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Baixar CSV", csv, file_name=f"custo_caixa_{datetime.now():%Y%m%d}.csv", mime="text/csv")

# ———————————————————  METODOLOGIA  ———————————————————
st.markdown("---")
with st.expander("📖 Metodologia"):
    st.markdown(
        """
* **Fonte**: arquivo Excel _Base de dados Historico_ (aba **Base**).  
* **Cenários**:  
  * **ORC** – valor orçado / planejado  
  * **REAL** – valor efetivo  
  * **DESVIO** – diferença REAL − ORC  
* Colunas mensais aceitas: `jan/24 ORC`, `jan/24 REAL`, `fev/25 orc`, …  
* Filtros atualizam todas as visualizações em tempo real.  
"""
    )
