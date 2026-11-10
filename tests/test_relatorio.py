import pandas as pd

import relatorio


def _dados_de_exemplo():
    meses = pd.date_range("2016-09-01", "2018-08-01", freq="MS")
    return {
        "kpis": pd.DataFrame(
            [
                {
                    "ticket_medio": 137.42,
                    "pct_cancelados": 0.63,
                    "pct_frete": 14.2,
                    "dias_entrega": 12.5,
                    "nota_media": 4.09,
                }
            ]
        ),
        "entrega_no_prazo": pd.DataFrame([{"pct_no_prazo": 93.2}]),
        "recompra": pd.DataFrame(
            [{"pedidos_por_cliente": 1, "pct_clientes": 96.96}]
        ),
        "vendas_mensais": pd.DataFrame(
            {"mes": meses, "pedidos": [1] * len(meses), "receita": [10.0] * len(meses)}
        ),
        "top_categorias": pd.DataFrame(
            {"categoria": ["health_beauty", "casa"], "receita": [20.0, 10.0]}
        ),
        "mix_pagamento": pd.DataFrame(
            {"tipo": ["credit_card", "boleto"], "pct_valor": [80.0, 20.0]}
        ),
        "ticket_medio_por_estado": pd.DataFrame(
            {"uf": ["PB", "SP"], "ticket_medio": [140.0, 110.0]}
        ),
        "clientes_por_uf": pd.DataFrame(
            {"uf": ["SP", "PB"], "clientes": [100, 20]}
        ),
        "nota_por_categoria": pd.DataFrame(
            {
                "categoria": ["office_furniture", "casa"],
                "posicao_pior": [1, 2],
                "nota_media": [3.6, 4.0],
            }
        ),
        "vendedores_pareto": pd.DataFrame(
            {"posicao": [1, 2], "pct_acumulado": [60.0, 100.0]}
        ),
    }


def test_html_tem_os_sete_cartoes_as_quatro_faixas_e_ids_fixos():
    html = relatorio._montar_html(_dados_de_exemplo(), "25/10/2026 14:03")

    assert html.count('class="metric-card"') == 7
    assert html.count('class="three"') == 2
    assert all(f'id="g{indice:02d}"' in html for indice in range(1, 8))
    assert html.count("cdn.plot.ly") == 1
    assert "Período · jan/2017 a ago/2018" in html
    assert "Dados de 25/10/2026 14:03" in html
    assert "R$ 137,42" in html
    assert "0,63%" in html
    assert "14,2%" in html
    assert "3,04%" in html
    assert "93,2%" in html
    assert "12,5" in html
    assert "4,09" in html


def test_geracao_com_mesmos_dados_muda_apenas_rodape():
    dados = _dados_de_exemplo()
    primeiro = relatorio._montar_html(dados, "25/10/2026 14:03")
    segundo = relatorio._montar_html(dados, "25/10/2026 14:04")

    assert primeiro.replace("14:03", "HORARIO") == segundo.replace(
        "14:04", "HORARIO"
    )
