"""Ingestão literal dos arquivos de origem para o schema raw.

Mapa completo, mantido literal para que os nomes em português possam ser
usados nos JOINs das próximas aulas:
  olist_orders_dataset.csv.gz              -> pedidos
  olist_order_items_dataset.csv.gz         -> itens_pedido
  olist_order_payments_dataset.csv.gz      -> pagamentos
  olist_order_reviews_dataset.csv.gz       -> avaliacoes
  olist_customers_dataset.csv.gz            -> clientes
  olist_sellers_dataset.csv.gz              -> vendedores
  olist_products_dataset.csv.gz             -> produtos
  product_category_name_translation.csv.gz -> traducao_categorias
  olist_geolocation_dataset.csv.gz          -> geolocalizacao

Os nove arquivos são verificados antes de abrir o banco para que a falta de
uma origem não produza uma ingestão parcial que pareça correta. A leitura é
direta do gzip com encoding UTF-8 declarado. Todas as colunas são texto e a
inferência fica desligada para preservar, por exemplo, zeros à esquerda em
CEPs; a conversão pertence à etapa refined, onde a decisão será registrada.
Somente campo vazio vira nulo. Linhas não são descartadas nem deduplicadas,
nomes de coluna não mudam e valores não são corrigidos, preenchidos ou
normalizados, pois a fronteira entre dado recebido e dado transformado fica
entre raw e refined.

Cada reexecução substitui as tabelas para que repetir o processo não acrescente
linhas. A tela exibe uma linha por tabela com nome qualificado e contagem lida
do banco, mais o total; o separador de milhar é ponto para facilitar a
conferência visual. Para o dataset esperado, o aceite é 1.550.922 registros.
O stdout é reconfigurado para UTF-8 porque o Prompt de Comando do Windows pode
embaralhar acentos. Este módulo só ingere dados: a interface web é executada
separadamente por ui.py.
"""

import sys

import pandas as pd

from pipeline import db


ARQUIVOS = (
    ("olist_orders_dataset.csv.gz", "pedidos"),
    ("olist_order_items_dataset.csv.gz", "itens_pedido"),
    ("olist_order_payments_dataset.csv.gz", "pagamentos"),
    ("olist_order_reviews_dataset.csv.gz", "avaliacoes"),
    ("olist_customers_dataset.csv.gz", "clientes"),
    ("olist_sellers_dataset.csv.gz", "vendedores"),
    ("olist_products_dataset.csv.gz", "produtos"),
    ("product_category_name_translation.csv.gz", "traducao_categorias"),
    ("olist_geolocation_dataset.csv.gz", "geolocalizacao"),
)


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    faltantes = [nome for nome, _ in ARQUIVOS if not (db.PASTA_RAW / nome).is_file()]
    if faltantes:
        print(f"Arquivos ausentes em {db.PASTA_RAW}:")
        for nome in faltantes:
            print(f"  {nome}")
        raise SystemExit(1)

    con = db.conectar()
    total = 0
    try:
        db.criar_schema(con, "raw")
        for nome_arquivo, tabela in ARQUIVOS:
            dataframe = pd.read_csv(
                db.PASTA_RAW / nome_arquivo,
                compression="gzip",
                encoding="utf-8",
                dtype=str,
                keep_default_na=False,
                na_values=[""],
                skip_blank_lines=False,
            )
            contagem = db.gravar(con, dataframe, "raw", tabela)
            total += contagem
            print(f"raw.{tabela}: {contagem:,}".replace(",", "."))
        print(f"Total: {total:,}".replace(",", "."))
    finally:
        con.close()


if __name__ == "__main__":
    main()
