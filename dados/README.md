# Pipeline Olist — dados do curso

Os dados do curso **Pipeline Olist**: quatro encontros de 1h20 construindo um pipeline
de ponta a ponta, do CSV ao dashboard, sobre vendas reais do e-commerce brasileiro.

Este repositório guarda **só os dados**. O código você escreve durante as aulas.

📖 **Guia do curso:** [ckoliveiraa.github.io/pipeline-olist](https://ckoliveiraa.github.io/pipeline-olist/)
— o roteiro das quatro aulas, publicado via GitHub Pages a partir de [`docs/`](docs/).

## O que tem aqui

Nove arquivos em `raw/`, comprimidos com gzip — 1.550.922 registros no total:

| Arquivo | Registros |
|---|---:|
| `olist_customers_dataset.csv.gz` | 99.441 |
| `olist_geolocation_dataset.csv.gz` | 1.000.163 |
| `olist_order_items_dataset.csv.gz` | 112.650 |
| `olist_order_payments_dataset.csv.gz` | 103.886 |
| `olist_order_reviews_dataset.csv.gz` | 99.224 |
| `olist_orders_dataset.csv.gz` | 99.441 |
| `olist_products_dataset.csv.gz` | 32.951 |
| `olist_sellers_dataset.csv.gz` | 3.095 |
| `product_category_name_translation.csv.gz` | 71 |

Use esta tabela para conferir sua ingestão: se o número na sua tela bate com o daqui,
está certo.

## Como usar

```bash
git clone https://github.com/ckoliveiraa/pipeline-olist.git
```

**Não precisa descompactar.** O pandas lê `.csv.gz` direto, do mesmo jeito que leria
um `.csv`:

```python
import pandas as pd
pedidos = pd.read_csv("raw/olist_orders_dataset.csv.gz")
```

O DuckDB também:

```sql
SELECT * FROM read_csv_auto('raw/olist_orders_dataset.csv.gz') LIMIT 5;
```

São 42 MB comprimidos contra 121 MB crus, e nenhum arquivo passa do limite em que o
GitHub começa a reclamar. O `.gitignore` ignora `raw/*.csv` justamente para ninguém
commitar a versão descompactada sem querer.

## Uma regra

Nunca edite nada dentro de `raw/`. É a fonte da verdade. Abrir um CSV no Excel e
salvar faz o Excel reescrever datas e números no formato dele, e a partir daí o
pipeline inteiro passa a mentir — em silêncio, que é o pior jeito.

## Origem e licença

Dados públicos da Olist Store, via Kaggle:
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
Redistribuídos aqui comprimidos, sem alteração de conteúdo, sob
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Veja
[LICENSE](LICENSE).
