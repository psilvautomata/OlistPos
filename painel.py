"""CONTEXTO
Painel do pipeline de dados público da Olist. A spec é a fonte da verdade;
os números de negócio continuam nos SQLs dos marts.

STACK E ARTEFATOS
Python 3.13, uv, DuckDB, Streamlit e Plotly. painel.py faz leitura,
formatação e gráficos sem importar Streamlit. app.py monta a página e roda
com uv run streamlit run app.py. A pasta marts contém doze consultas, cujos
resultados já estão no schema marts.

1. LEITURA
ler(marts) devolve um dicionário nome -> DataFrame. Para cada nome executa
somente SELECT * FROM marts.<nome>. Abre DuckDB em modo somente leitura e
fecha a conexão dentro de ler(), para que o pipeline possa substituir marts
com o painel aberto.

2. CÁLCULOS
painel.py e app.py não derivam métricas nem agregam ou combinam dados. Só
ordenam, filtram linhas, selecionam as primeiras linhas, renomeiam colunas e
formatam texto. A única conta autorizada é 100 menos o percentual de clientes
com exatamente um pedido; esse complemento expressa a taxa de recompra que
o mart 03 não armazena diretamente. Qualquer outro número ausente exige um
novo SQL em marts, pois uma regra de negócio não deve nascer na tela.

3. LAYOUT
A página usa layout wide. O cabeçalho traz “Olist · visão da operação” à
esquerda e o filtro de período à direita. A primeira faixa tem sete cartões,
nesta ordem: ticket médio em reais; cancelados como percentual de todos os
pedidos; participação do frete; recompra; entregas no prazo; dias entre
compra e entrega; e nota média. Cada rótulo informa a definição curta.

A faixa seguinte mostra faturamento mensal em linha com marcadores. A terceira
faixa tem receita das dez categorias principais em barras horizontais,
participação do valor por tipo de pagamento e ticket médio por UF em barras
horizontais. A quarta faixa tem clientes por UF em barras horizontais, as
dez piores notas por categoria como pontos e concentração de vendedores em
linha, com referência tracejada em 80 por cento. Os gráficos aparecem nessa
ordem, mas cada título usa o índice do arquivo SQL que fornece os dados.
Cada figura usa o tema escuro do rascunho, uma cor de destaque, identifica a
unidade e ocupa a largura disponível.

4. FORMATO E FIGURAS
reais(valor, casas=2), pct(valor, casas=1) e numero(valor, casas=0) são
funções puras, sem banco ou Streamlit. Milhares usam ponto e decimais usam
vírgula, independentemente das configurações regionais da máquina. Cada
função de gráfico recebe um DataFrame e devolve uma figura Plotly; assim o
relatório HTML pode reaproveitar os mesmos gráficos.

5. FILTRO DE PERÍODO
O seletor usa os meses de vendas_mensais e inicia de janeiro de 2017 a agosto
de 2018. Ele recorta somente as linhas do gráfico de faturamento. Cartões e
demais gráficos continuam cobrindo o período inteiro; esse aviso aparece
abaixo do seletor. Recortar linhas é apresentação; recalcular cartões seria
criar regras de negócio fora do SQL.

6. CACHE E ERROS
app.py usa st.cache_data. O botão “Recarregar dados” limpa esse cache. Se
olist.duckdb não existir ou faltar algum dos doze marts, a página apresenta
os nomes ausentes, orienta rodar uv run python -m pipeline.marts e para.

CRITÉRIOS DE ACEITE
Os cartões mostram R$ 137,42; 0,63%; 14,2%; 3,04%; 93,2%; 12,5; e 4,09.
O gráfico mensal abre com vinte meses, de janeiro de 2017 a agosto de 2018,
e mostra vinte e quatro quando o seletor abrange os extremos. Entre os dez
maiores valores por categoria, health_beauty aparece no alto; a nota mostra
office_furniture no alto; no ticket por UF, PB fica no alto e SP embaixo.
Com o painel aberto, o comando do pipeline de marts deve poder atualizar o
banco sem erro de bloqueio.

PRESSUPOSTOS EXPLÍCITOS
Valores nulos nas funções de formato aparecem como travessão. Os nomes de
mart recebidos por ler são nomes confiáveis da lista definida em app.py.
"""

import duckdb
import pandas as pd
import plotly.express as px


COR = "#2F6F73"
MESES_PT = (
    "jan", "fev", "mar", "abr", "mai", "jun",
    "jul", "ago", "set", "out", "nov", "dez",
)


class MartsAusentes(Exception):
    """Indica os marts que não puderam ser lidos por não existirem."""

    def __init__(self, nomes):
        self.nomes = tuple(nomes)
        super().__init__(", ".join(self.nomes))


class ErroLeitura(Exception):
    """Erro de conexão ou leitura do banco DuckDB."""


def ler(marts):
    """Lê cada mart pedido e fecha a conexão antes de devolver os dados."""
    try:
        con = duckdb.connect("olist.duckdb", read_only=True)
    except duckdb.Error as erro:
        raise ErroLeitura(str(erro)) from erro

    dados = {}
    ausentes = []
    try:
        for nome in marts:
            try:
                dados[nome] = con.execute(
                    f"SELECT * FROM marts.{nome}"
                ).df()
            except duckdb.CatalogException:
                ausentes.append(nome)
    except duckdb.Error as erro:
        raise ErroLeitura(str(erro)) from erro
    finally:
        con.close()

    if ausentes:
        raise MartsAusentes(ausentes)
    return dados


def _formatar(valor, casas):
    if valor is None or pd.isna(valor):
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\0").replace(".", ",").replace("\0", ".")


def reais(valor, casas=2):
    return f"R$ {_formatar(valor, casas)}"


def pct(valor, casas=1):
    return f"{_formatar(valor, casas)}%"


def numero(valor, casas=0):
    return _formatar(valor, casas)


def rotulo_mes(valor):
    data = pd.Timestamp(valor)
    return f"{MESES_PT[data.month - 1]}/{data.year}"


def _layout(figura, titulo, eixo_x, eixo_y):
    figura.update_layout(
        template="plotly_dark",
        title=titulo,
        xaxis_title=eixo_x,
        yaxis_title=eixo_y,
        colorway=[COR],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#E8EEF5", "family": "sans-serif"},
        title_font={"size": 16},
        margin={"l": 12, "r": 12, "t": 55, "b": 12},
    )
    figura.update_xaxes(
        showgrid=True,
        gridcolor="rgba(150,165,185,0.16)",
        zeroline=False,
        title_font={"size": 12},
        tickfont={"size": 10},
    )
    figura.update_yaxes(
        showgrid=True,
        gridcolor="rgba(150,165,185,0.12)",
        zeroline=False,
        title_font={"size": 12},
        tickfont={"size": 10},
    )
    return figura


def grafico_faturamento_mensal(df):
    dados = df.sort_values("mes").copy()
    dados["mes_rotulo"] = dados["mes"].map(rotulo_mes)
    ordem = dados["mes_rotulo"].tolist()
    figura = px.line(
        dados,
        x="mes_rotulo",
        y="receita",
        markers=True,
        category_orders={"mes_rotulo": ordem},
    )
    figura.update_traces(line={"color": COR, "width": 3}, marker={"size": 7})
    figura.update_yaxes(tickprefix="R$ ")
    return _layout(figura, "05 · Faturamento mensal", "Mês da compra", "Receita (R$)")


def grafico_receita_categoria(df):
    top = df.sort_values("receita", ascending=False).head(10)
    ordem = top["categoria"].tolist()
    figura = px.bar(
        top,
        x="receita",
        y="categoria",
        orientation="h",
        category_orders={"categoria": ordem},
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(tickprefix="R$ ")
    return _layout(figura, "04 · Receita por categoria", "Receita (R$)", "Categoria")


def grafico_mix_pagamento(df):
    dados = df.sort_values("pct_valor", ascending=False)
    ordem = dados["tipo"].tolist()
    figura = px.bar(
        dados,
        x="pct_valor",
        y="tipo",
        orientation="h",
        category_orders={"tipo": ordem},
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(ticksuffix="%")
    return _layout(figura, "07 · Mix de pagamento", "Participação no valor (%)", "Tipo de pagamento")


def grafico_ticket_uf(df):
    dados = df.sort_values("ticket_medio", ascending=False)
    ordem = dados["uf"].tolist()
    figura = px.bar(
        dados,
        x="ticket_medio",
        y="uf",
        orientation="h",
        category_orders={"uf": ordem},
    )
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(tickprefix="R$ ")
    return _layout(figura, "06 · Ticket médio por UF", "Ticket médio (R$)", "UF")


def grafico_clientes_uf(df):
    dados = df.sort_values("clientes", ascending=False)
    ordem = dados["uf"].tolist()
    figura = px.bar(
        dados,
        x="clientes",
        y="uf",
        orientation="h",
        category_orders={"uf": ordem},
    )
    figura.update_yaxes(autorange="reversed")
    return _layout(figura, "12 · Clientes por UF", "Clientes (pessoas)", "UF")


def grafico_nota_categoria(df):
    dados = df.sort_values("posicao_pior").head(10)
    ordem = dados["categoria"].tolist()
    figura = px.scatter(
        dados,
        x="nota_media",
        y="categoria",
        category_orders={"categoria": ordem},
    )
    figura.update_traces(marker={"color": COR, "size": 9})
    figura.update_yaxes(autorange="reversed")
    figura.update_xaxes(range=[1, 5])
    return _layout(figura, "02 · Nota por categoria", "Nota média (1–5)", "Categoria")


def grafico_vendedores_pareto(df):
    dados = df.sort_values("posicao")
    figura = px.line(dados, x="posicao", y="pct_acumulado")
    figura.update_traces(line={"color": COR, "width": 3})
    figura.add_hline(y=80, line_dash="dash", line_color="#E5B94C")
    figura.update_yaxes(ticksuffix="%", rangemode="tozero")
    return _layout(
        figura,
        "09 · Concentração de vendedores",
        "Posição do vendedor",
        "Receita acumulada (%)",
    )
