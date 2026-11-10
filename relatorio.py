"""Gera um relatório HTML local reutilizando leitura e gráficos de painel.py.

O arquivo não acessa o banco ao ser aberto: os dados são lidos uma vez pelo
script, e o HTML guarda cartões, figuras e o horário da geração. IDs fixos
nas figuras evitam diferenças artificiais entre execuções com os mesmos dados.
"""

from datetime import datetime
from html import escape
from pathlib import Path
import sys

import painel


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

INICIO_PADRAO = datetime(2017, 1, 1)
FIM_PADRAO = datetime(2018, 8, 1)


def _cartao(rotulo, valor, definicao):
    return (
        '<article class="metric-card">'
        f'<div class="metric-label" title="{escape(definicao, quote=True)}">'
        f"{escape(rotulo)}</div>"
        f'<div class="metric-value">{escape(valor)}</div>'
        "</article>"
    )


def _figura_html(figura, div_id, incluir_plotly):
    figura.update_layout(autosize=True)
    return figura.to_html(
        full_html=False,
        include_plotlyjs="cdn" if incluir_plotly else False,
        div_id=div_id,
        config={"responsive": True, "displayModeBar": False},
    )


def _montar_html(dados, gerado_em):
    kpis = dados["kpis"].iloc[0]
    entrega = dados["entrega_no_prazo"].iloc[0]
    recompra_uma_compra = dados["recompra"].loc[
        dados["recompra"]["pedidos_por_cliente"] == 1,
        "pct_clientes",
    ].iloc[0]

    cartoes = (
        ("Ticket médio", painel.reais(kpis["ticket_medio"], 2), "Média da receita de itens por pedido válido."),
        ("Cancelados", painel.pct(kpis["pct_cancelados"], 2), "Percentual de todos os pedidos com status cancelado."),
        ("Peso do frete", painel.pct(kpis["pct_frete"], 1), "Frete como parte da soma da receita de itens e frete."),
        ("Recompra", painel.pct(100 - recompra_uma_compra, 2), "Clientes únicos que fizeram mais de um pedido válido."),
        ("No prazo", painel.pct(entrega["pct_no_prazo"], 1), "Entregas no prazo entre as entregas com data observada."),
        ("Dias até entregar", painel.numero(kpis["dias_entrega"], 1), "Média de dias entre a compra e a entrega."),
        ("Nota média", painel.numero(kpis["nota_media"], 2), "Média das notas das avaliações."),
    )
    html_cartoes = "\n".join(_cartao(*cartao) for cartao in cartoes)

    vendas = dados["vendas_mensais"]
    vendas_periodo = vendas.loc[
        (vendas["mes"] >= INICIO_PADRAO) & (vendas["mes"] <= FIM_PADRAO)
    ]
    titulo_periodo = (
        f"{painel.rotulo_mes(INICIO_PADRAO)} a "
        f"{painel.rotulo_mes(FIM_PADRAO)}"
    )
    figura_vendas = painel.grafico_faturamento_mensal(vendas_periodo)
    figura_vendas.update_layout(
        title=f"05 · Faturamento mensal · {titulo_periodo}"
    )

    figuras_linha_3 = (
        painel.grafico_receita_categoria(dados["top_categorias"]),
        painel.grafico_mix_pagamento(dados["mix_pagamento"]),
        painel.grafico_ticket_uf(dados["ticket_medio_por_estado"]),
    )
    figuras_linha_4 = (
        painel.grafico_clientes_uf(dados["clientes_por_uf"]),
        painel.grafico_nota_categoria(dados["nota_por_categoria"]),
        painel.grafico_vendedores_pareto(dados["vendedores_pareto"]),
    )

    graficos_html = [_figura_html(figura_vendas, "g01", True)]
    graficos_html.extend(
        _figura_html(figura, f"g{indice:02d}", False)
        for indice, figura in enumerate((*figuras_linha_3, *figuras_linha_4), start=2)
    )

    faixa_3 = "\n".join(
        f'<section class="chart-card">{graficos_html[indice]}</section>'
        for indice in (1, 2, 3)
    )
    faixa_4 = "\n".join(
        f'<section class="chart-card">{graficos_html[indice]}</section>'
        for indice in (4, 5, 6)
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Olist · visão da operação</title>
  <style>
    :root {{ color-scheme: dark; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: #0b111b;
      color: #e8eef5;
      font-family: Arial, Helvetica, sans-serif;
    }}
    main {{ max-width: 1600px; margin: 0 auto; padding: 28px 32px 20px; }}
    header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 22px; }}
    h1 {{ margin: 0; font-size: clamp(1.6rem, 2.5vw, 2.25rem); letter-spacing: -0.035em; }}
    .period {{ color: #d6e0eb; background: #151f2c; border: 1px solid #2a3747; border-radius: 12px; padding: 12px 16px; font-size: 0.95rem; }}
    .metrics {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }}
    .metric-card, .chart-card {{ background: #111925; border: 1px solid #2a3747; border-radius: 14px; }}
    .metric-card {{ min-height: 94px; padding: 15px 16px; }}
    .metric-label {{ color: #aeb9c8; font-size: 0.88rem; line-height: 1.3; }}
    .metric-value {{ margin-top: 10px; color: #f4f7fb; font-size: clamp(1.15rem, 1.7vw, 1.55rem); font-weight: 700; white-space: nowrap; }}
    .chart-card {{ min-width: 0; padding: 8px; overflow: hidden; }}
    .wide {{ margin-bottom: 16px; }}
    .three {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }}
    footer {{ padding: 12px 2px 0; color: #8f9baa; font-size: 0.82rem; text-align: right; }}
    @media (max-width: 1100px) {{ .metrics {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }} }}
    @media (max-width: 760px) {{
      main {{ padding: 20px 14px; }}
      header {{ align-items: flex-start; flex-direction: column; gap: 14px; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
      .three {{ grid-template-columns: 1fr; gap: 10px; }}
      .metric-card {{ min-height: 82px; padding: 12px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Olist · visão da operação</h1>
      <div class="period">Período · {escape(titulo_periodo)}</div>
    </header>
    <section class="metrics" aria-label="Indicadores da operação">
      {html_cartoes}
    </section>
    <section class="wide chart-card" aria-label="Faturamento mensal">
      {graficos_html[0]}
    </section>
    <section class="three" aria-label="Categorias, pagamentos e ticket por UF">
      {faixa_3}
    </section>
    <section class="three" aria-label="Clientes, notas e vendedores">
      {faixa_4}
    </section>
    <footer>Dados de {gerado_em}</footer>
  </main>
</body>
</html>
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dados = painel.ler(MARTS)
    gerado_em = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    conteudo = _montar_html(dados, gerado_em)
    destino = Path(__file__).resolve().parent / "relatorio.html"
    destino.write_text(conteudo, encoding="utf-8")
    tamanho_kb = destino.stat().st_size / 1024
    print(f"Relatório: {destino}")
    print(f"Tamanho: {tamanho_kb:.1f} KB")


if __name__ == "__main__":
    main()
