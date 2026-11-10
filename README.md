# Pipeline Olist

Pipeline de dados em Python para explorar o dataset público de e-commerce da Olist. O projeto organiza os dados em duas etapas no DuckDB: ingestão dos arquivos originais no schema `raw` e transformação para o schema `refined`.

## Requisitos

- Python 3.14 ou superior
- [uv](https://docs.astral.sh/uv/)

As dependências do projeto são gerenciadas pelo `uv` e declaradas em `pyproject.toml`.

## Começando

Na raiz do projeto, instale as dependências:

```bash
uv sync
```

Os nove arquivos `.csv.gz` de origem devem estar em `dados/raw/`. Para carregar os dados no banco `olist.duckdb`, execute:

```bash
uv run python -m pipeline.ingestao
```

A ingestão cria ou substitui as tabelas do schema `raw`. Em seguida, transforme os dados para `refined`:

```bash
uv run python -m pipeline.transformacao
```

A transformação lê as tabelas de `raw` e cria ou substitui as tabelas correspondentes em `refined`. O banco fica na raiz do projeto.

## Explorar o banco

Depois da ingestão, inicie a interface DuckDB com:

```bash
uv run python ui.py
```

A interface fica disponível em <http://localhost:4213>. Encerre o processo com `Ctrl+C`.

## Estrutura

```text
.
├── dados/
│   └── raw/              # Arquivos de origem compactados
├── specs/
│   └── transformacao.md  # Regras da etapa refined
├── pipeline/
│   ├── db.py             # Conexão e operações compartilhadas com DuckDB
│   ├── ingestao.py       # Carga dos arquivos para o schema raw
│   └── transformacao.py  # Transformações de raw para refined
├── olist.duckdb          # Banco DuckDB criado na raiz
├── pyproject.toml        # Projeto e dependências
└── ui.py                 # Interface para explorar o banco
```

## Dados

O conjunto de dados contém informações de pedidos, itens, pagamentos, avaliações, clientes, vendedores, produtos, categorias e geolocalização da Olist Store. Os arquivos compactados estão em `dados/raw/`; consulte [`dados/README.md`](dados/README.md) para a lista de arquivos, contagens de referência, origem e licença.

## Fluxo resumido

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
```



