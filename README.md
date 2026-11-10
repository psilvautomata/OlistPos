# Pipeline Olist

Pipeline de dados em Python para o dataset público de e-commerce da Olist. A
pipeline carrega os CSVs em `raw`, transforma oito tabelas em `refined` e
materializa doze consultas SQL no schema `marts`. O painel Streamlit lê os
marts em somente leitura.

## Requisitos

- Python 3.13
- [uv](https://docs.astral.sh/uv/)

As dependências, incluindo DuckDB, Streamlit e Plotly, estão declaradas em
`pyproject.toml` e gerenciadas pelo uv.

## Começando

Na raiz do projeto, instale as dependências:

```bash
uv sync
```

Os nove arquivos `.csv.gz` de origem devem estar em `dados/raw/`. Para carregar
os dados em `olist.duckdb`, execute:

```bash
uv run python -m pipeline.ingestao
uv run python -m pipeline.transformacao
uv run python -m pipeline.marts
```

Essas etapas criam ou substituem os schemas `raw`, `refined` e `marts`, nessa
ordem. O banco DuckDB fica na raiz do projeto.

## Dashboard

Depois de criar os marts, inicie o dashboard:

```bash
uv run streamlit run app.py
```

`app.py` é o ponto de entrada executável: ele monta a página Streamlit e
importa `painel.py`. Este segundo módulo fornece a leitura dos marts, a
formatação e as funções dos gráficos; não precisa ser iniciado separadamente.

Para gerar uma versão estática em um único arquivo HTML, execute:

```bash
uv run python relatorio.py
```

O script grava `relatorio.html` na raiz, pronto para abrir no navegador. Ele
reutiliza os mesmos cartões e gráficos do dashboard; os gráficos carregam a
biblioteca Plotly pelo CDN.

O painel mostra os indicadores da operação, faturamento mensal filtrável e
gráficos de categorias, pagamentos, estados, avaliações e concentração de
vendedores. Os títulos dos gráficos usam o índice do SQL correspondente em
`sql/marts/`. O seletor de período recorta apenas o gráfico de faturamento;
os cartões e os demais gráficos cobrem o período inteiro. O tema escuro e os
cartões com borda seguem a referência visual em
[`dados/design/rascunho.png`](dados/design/rascunho.png); a paleta do Streamlit
fica em `.streamlit/config.toml`.

Referência visual: [rascunho do dashboard](dados/design/rascunho.png).

Para explorar tabelas diretamente no DuckDB, a interface auxiliar continua
disponível com:

```bash
uv run python ui.py
```

A interface auxiliar fica disponível em <http://localhost:4213>. Encerre o
processo com `Ctrl+C`.

## Estrutura

```text
.
├── app.py                     # Página Streamlit
├── painel.py                  # Leitura, formatação e gráficos
├── relatorio.py               # Geração do relatório HTML estático
├── .streamlit/config.toml     # Tema visual do painel
├── dados/
│   ├── raw/                   # CSVs de origem compactados
│   ├── design/rascunho.png    # Referência visual do dashboard
│   └── README.md              # Dados, origem e licença
├── pipeline/
│   ├── db.py                  # Conexão e operações compartilhadas
│   ├── ingestao.py            # Carga para raw
│   ├── transformacao.py       # Transformação de raw para refined
│   └── marts.py               # Criação dos marts a partir de sql/marts/
├── specs/                     # Regras de transformação
├── sql/marts/                 # Uma consulta por mart
├── olist.duckdb               # Banco DuckDB criado na raiz
├── pyproject.toml             # Projeto e dependências
└── ui.py                      # Interface auxiliar de exploração
```

## Dados

O conjunto contém informações de pedidos, itens, pagamentos, avaliações,
clientes, vendedores, produtos, categorias e geolocalização da Olist Store.
Consulte [`dados/README.md`](dados/README.md) para os arquivos, contagens de
referência, origem e licença.

## Fluxo

```text
CSV compactados em dados/raw/
          │
          ▼
   pipeline.ingestao
          │
          ▼
   DuckDB: schema raw
          │
          ▼
 pipeline.transformacao
          │
          ▼
 DuckDB: schema refined
          │
          ▼
   pipeline.marts ← sql/marts/*.sql
          │
          ▼
   DuckDB: schema marts
          │
          ▼
   app.py / painel.py
```
