# app.py  –  v2.1  (robusto a “ORÇ”, “Orçado”, “Plan”)
# Run:  streamlit run app.py
# Reqs: streamlit, pandas, numpy, plotly, openpyxl
# ---------------------------------------------------------------------

import re
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────  CONFIG  ─────────────
st.set_page_config(
    page_title="Dashboard de Custo Caixa – Global Eggs",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("🥚 Dashboard de Custo Caixa – Global Eggs e Subsidiárias")
st.markdown("---")

# ─────────────  UPLOAD  ─────────────
uploaded_file = st.file_uploader(
    "📁 Faça upload do arquivo **Base de dados Historico … .xlsx**",
    type=["xlsx"],
    help="Planilha deve conter a aba 'Base' com Empresa / Tipo de Caixa / Item e colunas mensais",
)

# ─────────────  LOAD & PARSE  ───────
@st.cache_data(show_spinner=False)
def load_data(xls) -> pd.DataFrame:
    df = pd.read_excel(xls, sheet_name="Base")

    # — padroniza nomes de colunas base —
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

    id_vars = ["Empresa", "Tipo de Caixa", "Item"]

    # — identifica colunas mensais + cenário —
    # aceita sufixos: ORC, ORÇ, ORCADO, ORÇADO, PLAN, REAL
    scen_map = {
        "orc": "ORC",
        "orç": "ORC",
        "orcado": "ORC",
        "orçado": "ORC",
        "plan": "ORC",
        "budget": "ORC",
        "real": "REAL",
    }
    month_re = re.compile(r"([a-z]{3}/\d{2})(?:\s+([a-zç]+))?$", re.I)

    meta, month_cols = [], []
    for col in df.columns:
        m = month_re.fullmatch(str(col))
        if m:
            mes_str, raw_scen = m.groups()
            scen = scen_map.get((raw_scen or "real").lower(), "REAL")
            meta.append((col, mes_str.lower(), scen))
            month_cols.append(col)

    if not month_cols:
        raise ValueError("Nenhuma coluna mensal encontrada (ex.: 'jan/24 REAL').")

    long = df.melt(
        id_vars=id_vars,
        value_vars=month_cols,
        var_name="ColSrc",
        value_name="Valor",
    )
    meta_df = pd.DataFrame(meta, columns=["ColSrc", "MesStr", "Cenário"])
    long = long.merge(meta_df, on="ColSrc").drop(columns="ColSrc")

    # — converte mês para datetime —
    month_map = {
        "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
    }
    long["Mês"] = long["MesStr"].apply(
        lambda s: datetime(2000 + int(s[-2:]), month_map[s[:3]], 1)
    )
    long = long.drop(columns="MesStr")
    long["Valor"] = pd.to_numeric(long["Valor"], errors="coerce")
    long = long.dropna(subset=["Valor"])

    # — pivot Plan × Real —
    piv = (
        long.pivot_table(
            index=["Empresa", "Mês", "Item"],
            columns="Cenário",
            values="Valor",
            aggfunc="sum",
        )
        .reset_index()
        .fillna(0)
    )

    # garante que existam as colunas ORC & REAL (mesmo que vazias)
    for col in ["ORC", "REAL"]:
        if col not in piv.columns:
            piv[col] = 0.0

    piv["DESVIO"] = piv["REAL"] - piv["ORC"]
    piv["DESVIO_%"] = np.where(piv["ORC"] != 0, piv["DESVIO"] / piv["ORC"], np.nan)

    return piv


if uploaded_file is None:
    st.info("👆 Faça upload para começar.")
    st.stop()

try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error(f"Erro ao processar: {e}")
    st.stop()

# ─────────────  SIDEBAR  ────────────
st.sidebar.header("🔧 Filtros")
emp = st.sidebar.multiselect("🏢 Empresas", sorted(df["Empresa"].unique()), default=sorted(df["Empresa"].unique()))
itens = st.sidebar.multiselect("💰 Itens", sorted(df["Item"].unique()), default=sorted(df["Item"].unique()))
cen = st.sidebar.radio("📊 Cenário", ["REAL", "ORC", "DESVIO"], index=0)
min_d, max_d = df["Mês"].min(), df["Mês"].max()
d_ini, d_fim = st.sidebar.slider("📅 Período", min_value=min_d, max_value=max_d,
                                 value=(min_d, max_d), format="MM/YYYY")

mask = df["Empresa"].isin(emp) & df["Item"].isin(itens) & df["Mês"].between(d_ini, d_fim)
data = df.loc[mask].copy()
data["ValorSel"] = data[cen]

# ─────────────  TABS  ───────────────
tabs = st.tabs(["📈 Visão Geral", "🍰 Por Categoria", "📊 Plan × Real", "📋 Tabela"])

# —— 1. Visão Geral ——————————————————
with tabs[0]:
    st.subheader("KPIs")
    kpi = data.groupby("Mês")["ValorSel"].sum().reset_index()
    mes_atual = kpi["Mês"].max()
    mes_ant = kpi[kpi["Mês"] < mes_atual]["Mês"].max()
    v_atual = kpi.loc[kpi["Mês"] == mes_atual, "ValorSel"].values[0]
    v_ant = kpi.loc[kpi["Mês"] == mes_ant, "ValorSel"].values[0] if pd.notna(mes_ant) else np.nan
    delta = (v_atual - v_ant) / v_ant * 100 if pd.notna(v_ant) and v_ant else 0

    c1, c2 = st.columns(2)
    c1.metric(f"Total {cen} ({mes_atual:%b/%y})", f"R$ {v_atual:,.2f}", f"{delta:+.1f}%")
    top = (
        data[data["Mês"] == mes_atual]
        .groupby("Empresa")["ValorSel"]
        .sum()
        .sort_values()
    )
    if not top.empty:
        c2.metric("Menor ↔ Maior", f"{top.index[0]} ↔ {top.index[-1]}",
                  f"R$ {top.iloc[0]:,.0f} ↔ R$ {top.iloc[-1]:,.0f}")

    st.markdown("---")
    fig_tot = px.line(kpi, x="Mês", y="ValorSel",
                      title=f"Evolução Total – {cen}", labels={"ValorSel": "R$", "Mês": "Mês"})
    st.plotly_chart(fig_tot, use_container_width=True)

# —— 2. Categorias ——————————————
with tabs[1]:
    st.subheader("Distribuição por Categoria")
    cat = data.groupby(["Mês", "Item"])["ValorSel"].sum().reset_index()
    fig_area = px.area(cat, x="Mês", y="ValorSel", color="Item",
                       title=f"Peso das Categorias – {cen}",
                       groupnorm="fraction", stackgroup="one")
    st.plotly_chart(fig_area, use_container_width=True)

# —— 3. Plan × Real ——————————————
with tabs[2]:
    st.subheader("Plan × Real – Último Mês")
    ultimo = data[data["Mês"] == mes_atual]
    bar_df = (
        ultimo.groupby("Empresa")[["ORC", "REAL", "DESVIO"]]
        .sum()
        .reset_index()
        .sort_values("REAL", ascending=False)
    )

    fig_pr = go.Figure()
    fig_pr.add_bar(x=bar_df["Empresa"], y=bar_df["ORC"], name="ORC")
    fig_pr.add_bar(x=bar_df["Empresa"], y=bar_df["REAL"], name="REAL")
    fig_pr.update_layout(barmode="group", yaxis_title="R$", title=f"Plan x Real ({mes_atual:%b/%y})")
    st.plotly_chart(fig_pr, use_container_width=True)

    desv = bar_df.sort_values("DESVIO")
    fig_desv = px.bar(desv, x="DESVIO", y="Empresa", orientation="h",
                      color="DESVIO", color_continuous_scale="RdYlGn",
                      title="Desvio (REAL − ORC)", labels={"DESVIO": "R$"})
    fig_desv.add_vline(x=0, line_dash="dot")
    st.plotly_chart(fig_desv, use_container_width=True)

# —— 4. Tabela ————————————————
with tabs[3]:
    st.subheader("Tabela Detalhada")
    tbl = data[["Empresa", "Mês", "Item", "ORC", "REAL", "DESVIO", "DESVIO_%"]].copy()
    tbl["Mês"] = tbl["Mês"].dt.strftime("%b/%y")
    tbl["DESVIO_%"] = tbl["DESVIO_%"].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "")
    st.dataframe(tbl, use_container_width=True, height=450)
    csv = tbl.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Baixar CSV", csv,
                       file_name=f"custo_caixa_{datetime.now():%Y%m%d}.csv",
                       mime="text/csv")

# —— Metodologia ———————————————
st.markdown("---")
with st.expander("📖 Metodologia"):
    st.markdown(
        """
* **Fonte**: aba **Base** do Excel Histórico.  
* **Reconhecimento de sufixos**: `ORC`, `ORÇ`, `Orçado`, `Plan`, etc.  
* Cenários exibidos: **ORC** (Planejado), **REAL**, **DESVIO** (REAL − ORC).  
* Filtros na barra lateral atualizam tudo em tempo real.
"""
    )
