from datetime import datetime

import duckdb
import pandas as pd
import pytest

import painel


@pytest.mark.parametrize(
    ("funcao", "dados", "titulo"),
    [
        (
            painel.grafico_faturamento_mensal,
            pd.DataFrame(
                {"mes": [datetime(2017, 1, 1)], "receita": [12.0]}
            ),
            "05 · Faturamento mensal",
        ),
        (
            painel.grafico_receita_categoria,
            pd.DataFrame({"categoria": ["casa"], "receita": [12.0]}),
            "04 · Receita por categoria",
        ),
        (
            painel.grafico_mix_pagamento,
            pd.DataFrame({"tipo": ["credit_card"], "pct_valor": [80.0]}),
            "07 · Mix de pagamento",
        ),
        (
            painel.grafico_ticket_uf,
            pd.DataFrame({"uf": ["PB"], "ticket_medio": [12.0]}),
            "06 · Ticket médio por UF",
        ),
        (
            painel.grafico_clientes_uf,
            pd.DataFrame({"uf": ["PB"], "clientes": [12]}),
            "12 · Clientes por UF",
        ),
        (
            painel.grafico_nota_categoria,
            pd.DataFrame(
                {"categoria": ["casa"], "posicao_pior": [1], "nota_media": [3.0]}
            ),
            "02 · Nota por categoria",
        ),
        (
            painel.grafico_vendedores_pareto,
            pd.DataFrame({"posicao": [1], "pct_acumulado": [50.0]}),
            "09 · Concentração de vendedores",
        ),
    ],
)
def test_graficos_plotly_usam_titulos_dos_indices_sql(funcao, dados, titulo):
    figura = funcao(dados)

    assert figura.layout.title.text == titulo
    assert figura.layout.paper_bgcolor == "rgba(0,0,0,0)"


def test_formatadores_usam_separadores_brasileiros():
    assert painel.reais(1003862.14) == "R$ 1.003.862,14"
    assert painel.pct(93.2) == "93,2%"
    assert painel.numero(96470) == "96.470"
    assert painel.numero(float("nan")) == "—"


def test_ler_usa_dados_do_banco_no_diretorio_atual_e_fecha_conexao(
    monkeypatch,
    tmp_path,
):
    monkeypatch.chdir(tmp_path)
    con = duckdb.connect("olist.duckdb")
    con.execute("CREATE SCHEMA marts")
    con.execute("CREATE TABLE marts.exemplo AS SELECT '00123' AS cep")
    con.close()

    dados = painel.ler(("exemplo",))
    escrita = duckdb.connect("olist.duckdb")
    try:
        escrita.execute("CREATE TABLE marts.apos_leitura AS SELECT 1 AS valor")
    finally:
        escrita.close()

    assert dados["exemplo"]["cep"].tolist() == ["00123"]


def test_ler_informa_todos_os_marts_ausentes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    con = duckdb.connect("olist.duckdb")
    con.execute("CREATE SCHEMA marts")
    con.close()

    with pytest.raises(painel.MartsAusentes) as erro:
        painel.ler(("inexistente_a", "inexistente_b"))

    assert erro.value.nomes == ("inexistente_a", "inexistente_b")
