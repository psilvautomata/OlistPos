"""Página Streamlit do painel Olist; os cálculos de negócio ficam nos marts."""

from datetime import datetime
from pathlib import Path

import streamlit as st

from painel import (
    ErroLeitura,
    MartsAusentes,
    grafico_clientes_uf,
    grafico_faturamento_mensal,
    grafico_mix_pagamento,
    grafico_nota_categoria,
    grafico_receita_categoria,
    grafico_ticket_uf,
    grafico_vendedores_pareto,
    numero,
    pct,
    reais,
    rotulo_mes,
    ler,
)


MARTS = (
    "vendas_mensais",
    "top_categorias",
    "entrega_no_prazo",
    "nota_por_categoria",
    "recompra",
    "ticket_medio_por_estado",
    "mix_pagamento",
    "nota_por_prazo",
    "vendedores_pareto",
    "tempo_entrega_por_estado",
    "kpis",
    "clientes_por_uf",
)


@st.cache_data(show_spinner="Lendo os marts...")
def carregar_marts(nomes):
    return ler(nomes)


st.set_page_config(page_title="Olist · visão da operação", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
        background: #0b111b;
    }
    [data-testid="stAppViewContainer"] > .main .block-container {
        max-width: 1600px;
        padding-top: 1.35rem;
        padding-bottom: 2rem;
    }
    h1 {
        letter-spacing: -0.035em;
        font-weight: 700;
    }
    [data-testid="stMetric"] {
        min-height: 96px;
        padding: 15px 16px;
        background: linear-gradient(145deg, #151f2c, #111925);
        border: 1px solid #2a3747;
        border-radius: 12px;
    }
    [data-testid="stMetricLabel"] p {
        color: #aeb9c8;
        font-size: 0.88rem;
    }
    [data-testid="stMetricValue"] {
        color: #f4f7fb;
        font-size: 1.55rem;
        font-weight: 700;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #111925;
        border: 1px solid #2a3747;
        border-radius: 14px;
        padding: 0.45rem 0.55rem 0.25rem;
    }
    [data-testid="stPlotlyChart"] {
        background: transparent;
    }
    [data-testid="stCaptionContainer"] {
        color: #aeb9c8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if not Path("olist.duckdb").is_file():
    st.error(
        "Banco olist.duckdb não encontrado. Crie os marts com "
        "uv run python -m pipeline.marts."
    )
    st.stop()

try:
    dados = carregar_marts(MARTS)
except MartsAusentes as erro:
    lista = ", ".join(f"marts.{nome}" for nome in erro.nomes)
    st.error(f"Marts ausentes: {lista}. Rode uv run python -m pipeline.marts.")
    st.stop()
except ErroLeitura as erro:
    st.error(f"Não foi possível ler o banco: {erro}. Rode uv run python -m pipeline.marts.")
    st.stop()


cabecalho, filtro = st.columns([2.2, 1])
with cabecalho:
    st.title("Olist · visão da operação")

with filtro:
    meses = sorted(dados["vendas_mensais"]["mes"].dropna().tolist())
    periodo = st.select_slider(
        "Período",
        options=meses,
        value=(datetime(2017, 1, 1), datetime(2018, 8, 1)),
        format_func=rotulo_mes,
    )
    st.caption("os cartões valem para o período inteiro")
    if st.button("Recarregar dados"):
        carregar_marts.clear()
        st.rerun()


kpis = dados["kpis"].iloc[0]
entrega = dados["entrega_no_prazo"].iloc[0]
recompra_uma_compra = dados["recompra"].loc[
    dados["recompra"]["pedidos_por_cliente"] == 1,
    "pct_clientes",
].iloc[0]

cartoes = st.columns(7)
metricas = (
    ("Ticket médio", reais(kpis["ticket_medio"], 2), "Média da receita de itens por pedido válido."),
    ("Cancelados", pct(kpis["pct_cancelados"], 2), "Percentual de todos os pedidos com status cancelado."),
    ("Peso do frete", pct(kpis["pct_frete"], 1), "Frete como parte da soma da receita de itens e frete."),
    ("Recompra", pct(100 - recompra_uma_compra, 2), "Clientes únicos que fizeram mais de um pedido válido."),
    ("No prazo", pct(entrega["pct_no_prazo"], 1), "Entregas no prazo entre as entregas com data observada."),
    ("Dias até entregar", numero(kpis["dias_entrega"], 1), "Média de dias entre a compra e a entrega."),
    ("Nota média", numero(kpis["nota_media"], 2), "Média das notas das avaliações."),
)
for coluna, (rotulo, valor, definicao) in zip(cartoes, metricas):
    coluna.metric(rotulo, valor, help=definicao)


vendas = dados["vendas_mensais"]
vendas_periodo = vendas.loc[
    (vendas["mes"] >= periodo[0]) & (vendas["mes"] <= periodo[1])
]
with st.container(border=True):
    st.plotly_chart(
        grafico_faturamento_mensal(vendas_periodo),
        width="stretch",
        height=330,
        config={"displayModeBar": False},
    )


receita_col, pagamento_col, ticket_col = st.columns(3)
with receita_col:
    with st.container(border=True):
        st.plotly_chart(
            grafico_receita_categoria(dados["top_categorias"]),
            width="stretch",
            height=330,
            config={"displayModeBar": False},
        )
with pagamento_col:
    with st.container(border=True):
        st.plotly_chart(
            grafico_mix_pagamento(dados["mix_pagamento"]),
            width="stretch",
            height=330,
            config={"displayModeBar": False},
        )
with ticket_col:
    with st.container(border=True):
        st.plotly_chart(
            grafico_ticket_uf(dados["ticket_medio_por_estado"]),
            width="stretch",
            height=330,
            config={"displayModeBar": False},
        )


clientes_col, nota_col, pareto_col = st.columns(3)
with clientes_col:
    with st.container(border=True):
        st.plotly_chart(
            grafico_clientes_uf(dados["clientes_por_uf"]),
            width="stretch",
            height=330,
            config={"displayModeBar": False},
        )
with nota_col:
    with st.container(border=True):
        st.plotly_chart(
            grafico_nota_categoria(dados["nota_por_categoria"]),
            width="stretch",
            height=330,
            config={"displayModeBar": False},
        )
with pareto_col:
    with st.container(border=True):
        st.plotly_chart(
            grafico_vendedores_pareto(dados["vendedores_pareto"]),
            width="stretch",
            height=330,
            config={"displayModeBar": False},
        )
