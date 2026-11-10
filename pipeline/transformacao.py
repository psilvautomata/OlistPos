"""Transforma raw em refined com conversões e regras explícitas.

Lê apenas oito tabelas de raw e escreve apenas em refined. geolocalizacao
fica fora porque nenhum mart do curso a usa; limpar algo que ninguém lerá não
ajuda a responder às perguntas do curso.

O mapa de nomes é completo e literal, para que os JOINs da aula 3 usem o
vocabulário português definido na spec:
  pedidos: order_id->pedido_id, customer_id->cliente_id,
    order_status->status, order_purchase_timestamp->data_compra,
    order_approved_at->data_aprovacao,
    order_delivered_carrier_date->data_envio,
    order_delivered_customer_date->data_entrega,
    order_estimated_delivery_date->data_entrega_prevista
  itens_pedido: order_id->pedido_id, order_item_id->item_seq,
    product_id->produto_id, seller_id->vendedor_id,
    shipping_limit_date->data_limite_envio, price->preco,
    freight_value->freteCONTEXTO
Estou construindo um pipeline de dados em Python sobre o dataset público da
Olist (e-commerce brasileiro, 2016-2018). Trabalho com spec-driven development:
a spec abaixo é a fonte da verdade e o código é consequência dela. Não
acrescente requisito que não esteja escrito aqui. Se algo estiver ambíguo,
pergunte antes de escrever código.

STACK
- Python 3.13, dependências gerenciadas com uv
- DuckDB, arquivo olist.duckdb na raiz do projeto
- Nenhum orquestrador. Script executável pela linha de comando.

O QUE JÁ EXISTE (use, não reimplemente)
pipeline/db.py expõe:
  conectar()                 abre o olist.duckdb, criando se faltar
  criar_schema(con, nome)    CREATE SCHEMA IF NOT EXISTS
O schema raw, criado pela etapa 1: nove tabelas, todas as colunas VARCHAR,
campo vazio como NULL.

ARTEFATO A PRODUZIR
pipeline/transformacao.py, executável com:
  uv run python -m pipeline.transformacao

SPEC

1. ESCOPO
   Lê de raw, escreve no schema refined. Nunca escreve em raw.
   Entram oito tabelas: pedidos, itens_pedido, pagamentos, clientes,
   vendedores, produtos, traducao_categorias, avaliacoes.
   Fica de fora:
     geolocalizacao  nenhum mart do curso usa. Não se limpa o que
                     ninguém vai ler.

2. NOMES
   Colunas renomeadas para português, snake_case, com o mapa abaixo,
   completo e literal. Nenhuma coluna fora do mapa; nenhuma descartada.
   Motivo: é o vocabulário que vou digitar de memória nos JOINs da aula 3.

   pedidos
     order_id -> pedido_id                 customer_id -> cliente_id
     order_status -> status                order_purchase_timestamp -> data_compra
     order_approved_at -> data_aprovacao   order_delivered_carrier_date -> data_envio
     order_delivered_customer_date -> data_entrega
     order_estimated_delivery_date -> data_entrega_prevista
   itens_pedido
     order_id -> pedido_id                 order_item_id -> item_seq
     product_id -> produto_id              seller_id -> vendedor_id
     shipping_limit_date -> data_limite_envio
     price -> preco                        freight_value -> frete
   pagamentos
     order_id -> pedido_id                 payment_sequential -> pagamento_seq
     payment_type -> tipo                  payment_installments -> parcelas
     payment_value -> valor
   clientes
     customer_id -> cliente_id             customer_unique_id -> cliente_unico_id
     customer_zip_code_prefix -> cep_prefixo
     customer_city -> cidade               customer_state -> uf
   vendedores
     seller_id -> vendedor_id              seller_zip_code_prefix -> cep_prefixo
     seller_city -> cidade                 seller_state -> uf
   produtos
     product_id -> produto_id              product_category_name -> categoria
     product_name_lenght -> tamanho_nome   product_description_lenght -> tamanho_descricao
     product_photos_qty -> qtd_fotos       product_weight_g -> peso_g
     product_length_cm -> comprimento_cm   product_height_cm -> altura_cm
     product_width_cm -> largura_cm
   traducao_categorias
     product_category_name -> categoria
     product_category_name_english -> categoria_en
   avaliacoes
     review_id -> avaliacao_id             order_id -> pedido_id
     review_score -> nota                  review_comment_title -> titulo
     review_comment_message -> comentario
     review_creation_date -> data_criacao
     review_answer_timestamp -> data_resposta

3. TIPOS
   Datas com hora: TIMESTAMP, formato declarado '%Y-%m-%d %H:%M:%S'
     (data_compra, data_aprovacao, data_envio, data_entrega,
      data_limite_envio, data_resposta).
   data_entrega_prevista: DATE. Motivo: a hora é sempre 00:00:00 nas
     99.441 linhas; guardar a hora seria inventar precisão.
   data_criacao: DATE. Motivo: a hora é 00:00:00 em 99.139 das 99.224
     avaliações; nas outras 85 é 01:00:00, efeito de horário de verão, e
     não um horário de verdade.
   Dinheiro (preco, frete, valor): DECIMAL(10,2). Motivo: DOUBLE não
     representa centavos com exatidão, e soma de dinheiro tem que fechar.
   Contagens e medidas (item_seq, pagamento_seq, parcelas, tamanho_nome,
     tamanho_descricao, qtd_fotos, peso_g, comprimento_cm, altura_cm,
     largura_cm, nota): INTEGER.
   Todo o resto continua VARCHAR — inclusive cep_prefixo. Motivo: 23.995
     clientes têm CEP começando com zero; CEP é identificador, nunca é
     somado, e como número perderia o zero.
   A conversão é feita em SQL pelo DuckDB (strptime, CAST), disparada pelo
   Python. Motivo: o dado já está no banco; não há por que trazê-lo para a
   memória só para converter tipo.

4. CONVERSÃO QUE FALHA
   Para tudo. Use strptime e CAST, que estouram, e nunca try_strptime,
   TRY_CAST ou errors="coerce", que transformam falha em nulo.
   Ao falhar: diga tabela, coluna e um exemplo do valor que não converteu,
   e encerre com sys.exit(1).
   Motivo: um nulo fabricado pela conversão fica indistinguível de um nulo
   verdadeiro do dado, para sempre.

5. DUPLICATAS
   Chave de cada tabela:
     pedidos (pedido_id)            itens_pedido (pedido_id, item_seq)
     pagamentos (pedido_id, pagamento_seq)
     clientes (cliente_id)          vendedores (vendedor_id)
     produtos (produto_id)          traducao_categorias (categoria)
     avaliacoes (avaliacao_id, pedido_id)
       — avaliacao_id sozinho não é chave: o mesmo id aparece em mais
         de um pedido.
   Linha inteira repetida: mantém uma, e conta quantas saíram.
   Chave repetida com conteúdo diferente: para, mostra a chave e as linhas
   conflitantes, sys.exit(1). Não escolhe uma por conta própria.
   Motivo: escolher em silêncio é decidir sem dizer que decidiu.

6. NULOS
   Nenhuma linha é apagada por ter nulo. Nenhum nulo é preenchido.
   Motivo: nas datas de pedidos, o nulo é informação — pedido cancelado
   não tem data de entrega porque não foi entregue. Em produtos, 610 sem
   categoria continuam sem categoria; dar um rótulo para eles é decisão
   de mart (aula 3), não de refined. Em avaliacoes, título e comentário
   nulos continuam nulos: avaliação sem texto é a regra, não a exceção.
   Anomalias de negócio também ficam (ex.: 8 pedidos delivered sem
   data_entrega, 166 com data_envio antes da data_compra, pedidos com
   mais de uma avaliação). refined não
   corrige fato; quem decide o que fazer com ele é a pergunta que o mart
   responde.

7. SAÍDA NA TELA
   Uma linha por tabela, no formato:
     refined.pedidos            99.441 -> 99.441 linhas  (0 duplicatas)
   Abaixo dela, indentadas, as colunas com nulo e a contagem:
       nulos mantidos: data_aprovacao 160, data_envio 1.783, data_entrega 2.965
   As contagens vêm do banco, milhar separado por ponto. Linha final com o
   total. stdout reconfigurado para utf-8.

REEXECUÇÃO
   CREATE OR REPLACE TABLE, nunca acrescenta. Rodar dez vezes = rodar uma.

ERRO
   Antes de transformar, verifica se as oito tabelas de entrada existem em
   raw. Faltando qualquer uma: lista quais, diz para rodar
   "uv run python -m pipeline.ingestao" e encerra com sys.exit(1).

CRITÉRIOS DE ACEITE
- Oito tabelas em refined; em cada uma, linhas que saem = linhas que entram
  (com este dado, 0 duplicatas em todas). Total: 550.759.
- DESCRIBE refined.pedidos mostra TIMESTAMP nas cinco datas com hora e DATE
  em data_entrega_prevista.
- Nulos depois = nulos antes, coluna por coluna (pedidos: 160 / 1.783 /
  2.965; produtos: 610 em categoria; avaliacoes: 87.656 em titulo,
  58.247 em comentario).
- sum(preco) em refined.itens_pedido bate com sum(CAST(price AS DECIMAL))
  em raw, centavo por centavo.
- cep_prefixo continua com o zero à esquerda: '01151' e não 1151.
- Rodar duas vezes seguidas imprime exatamente a mesma coisa.

ENTREGA, nesta ordem
1. A spec como docstring no topo do arquivo, dizendo por que cada regra
   existe — não só o que ela manda fazer.
2. O código, com comentários apenas onde a decisão não é óbvia pelo código.
3. Uma lista final do que você assumiu e que não estava na spec. Se a lista
   não estiver vazia, é a minha spec que precisa melhorar.
  pagamentos: order_id->pedido_id, payment_sequential->pagamento_seq,
    payment_type->tipo, payment_installments->parcelas,
    payment_value->valor
  clientes: customer_id->cliente_id, customer_unique_id->cliente_unico_id,
    customer_zip_code_prefix->cep_prefixo, customer_city->cidade,
    customer_state->uf
  vendedores: seller_id->vendedor_id,
    seller_zip_code_prefix->cep_prefixo, seller_city->cidade,
    seller_state->uf
  produtos: product_id->produto_id,
    product_category_name->categoria,
    product_name_lenght->tamanho_nome,
    product_description_lenght->tamanho_descricao,
    product_photos_qty->qtd_fotos, product_weight_g->peso_g,
    product_length_cm->comprimento_cm, product_height_cm->altura_cm,
    product_width_cm->largura_cm
  traducao_categorias: product_category_name->categoria,
    product_category_name_english->categoria_en
  avaliacoes: review_id->avaliacao_id, order_id->pedido_id,
    review_score->nota, review_comment_title->titulo,
    review_comment_message->comentario,
    review_creation_date->data_criacao,
    review_answer_timestamp->data_resposta

Datas com hora viram TIMESTAMP usando o formato declarado
%Y-%m-%d %H:%M:%S. data_entrega_prevista e data_criacao viram DATE: guardar
horários 00:00:00 como precisão ou manter os 85 horários 01:00:00 de
data_criacao como horários reais inventaria precisão que o dado não tem.
preco, frete e valor viram DECIMAL(10,2), para que valores monetários e suas
somas preservem centavos. item_seq, pagamento_seq, parcelas, as medidas e
contagens de produtos e nota viram INTEGER porque representam números
inteiros. O restante fica VARCHAR; em particular cep_prefixo é identificador,
e convertê-lo em número apagaria zeros à esquerda.

As conversões estritas são executadas pelo DuckDB (strptime e CAST), que deve
falhar em vez de fabricar nulos. Em caso de erro, a mensagem identifica
tabela, coluna e valor de exemplo; isso mantém um nulo de origem distinguível
de um problema de qualidade. Nenhuma linha é removida por ter nulos e nenhum
nulo é preenchido: ausências e anomalias de negócio são fatos que os marts
devem decidir como interpretar.

As chaves são pedidos(pedido_id), itens_pedido(pedido_id,item_seq),
pagamentos(pedido_id,pagamento_seq), clientes(cliente_id),
vendedores(vendedor_id), produtos(produto_id),
traducao_categorias(categoria) e avaliacoes(avaliacao_id,pedido_id). Linha
inteira repetida é mantida uma vez e contada; chave com conteúdo conflitante
interrompe a etapa e exibe chave e linhas, pois escolher uma seria uma decisão
de negócio silenciosa. avaliação_id sozinho não identifica a chave.

Antes de transformar, todas as oito entradas são conferidas para evitar
refined parcial por uma ingestão incompleta. CREATE OR REPLACE TABLE torna a
reexecução idempotente, em vez de acrescentar linhas. A saída mostra contagens
de entrada e saída, duplicatas removidas e nulos mantidos, sempre consultadas
no banco e formatadas com ponto nos milhares; o total permite conferir a
carga. stdout usa UTF-8 para exibir acentos corretamente no Prompt de Comando.

Para o snapshot especificado, a conferência esperada é 550.759 linhas no
conjunto das oito tabelas e nenhuma duplicata. As ausências conhecidas devem
continuar iguais antes e depois (pedidos: 160 em data_aprovacao, 1.783 em
data_envio e 2.965 em data_entrega; produtos: 610 em categoria; avaliações:
87.656 em titulo e 58.247 em comentario). Esses valores detectam preenchimento
ou perda acidental de nulos. preco deve continuar somando centavo por centavo
como em raw, e cep_prefixo deve manter zeros à esquerda, pois moeda e CEP têm
semânticas diferentes de números comuns.
"""

import json
import sys

import duckdb

from pipeline import db


FORMATO_DATA_HORA = "%Y-%m-%d %H:%M:%S"

TABELAS = (
    {
        "nome": "pedidos",
        "colunas": (
            ("order_id", "pedido_id"),
            ("customer_id", "cliente_id"),
            ("order_status", "status"),
            ("order_purchase_timestamp", "data_compra"),
            ("order_approved_at", "data_aprovacao"),
            ("order_delivered_carrier_date", "data_envio"),
            ("order_delivered_customer_date", "data_entrega"),
            ("order_estimated_delivery_date", "data_entrega_prevista"),
        ),
        "chave": ("pedido_id",),
    },
    {
        "nome": "itens_pedido",
        "colunas": (
            ("order_id", "pedido_id"),
            ("order_item_id", "item_seq"),
            ("product_id", "produto_id"),
            ("seller_id", "vendedor_id"),
            ("shipping_limit_date", "data_limite_envio"),
            ("price", "preco"),
            ("freight_value", "frete"),
        ),
        "chave": ("pedido_id", "item_seq"),
    },
    {
        "nome": "pagamentos",
        "colunas": (
            ("order_id", "pedido_id"),
            ("payment_sequential", "pagamento_seq"),
            ("payment_type", "tipo"),
            ("payment_installments", "parcelas"),
            ("payment_value", "valor"),
        ),
        "chave": ("pedido_id", "pagamento_seq"),
    },
    {
        "nome": "clientes",
        "colunas": (
            ("customer_id", "cliente_id"),
            ("customer_unique_id", "cliente_unico_id"),
            ("customer_zip_code_prefix", "cep_prefixo"),
            ("customer_city", "cidade"),
            ("customer_state", "uf"),
        ),
        "chave": ("cliente_id",),
    },
    {
        "nome": "vendedores",
        "colunas": (
            ("seller_id", "vendedor_id"),
            ("seller_zip_code_prefix", "cep_prefixo"),
            ("seller_city", "cidade"),
            ("seller_state", "uf"),
        ),
        "chave": ("vendedor_id",),
    },
    {
        "nome": "produtos",
        "colunas": (
            ("product_id", "produto_id"),
            ("product_category_name", "categoria"),
            ("product_name_lenght", "tamanho_nome"),
            ("product_description_lenght", "tamanho_descricao"),
            ("product_photos_qty", "qtd_fotos"),
            ("product_weight_g", "peso_g"),
            ("product_length_cm", "comprimento_cm"),
            ("product_height_cm", "altura_cm"),
            ("product_width_cm", "largura_cm"),
        ),
        "chave": ("produto_id",),
    },
    {
        "nome": "traducao_categorias",
        "colunas": (
            ("product_category_name", "categoria"),
            ("product_category_name_english", "categoria_en"),
        ),
        "chave": ("categoria",),
    },
    {
        "nome": "avaliacoes",
        "colunas": (
            ("review_id", "avaliacao_id"),
            ("order_id", "pedido_id"),
            ("review_score", "nota"),
            ("review_comment_title", "titulo"),
            ("review_comment_message", "comentario"),
            ("review_creation_date", "data_criacao"),
            ("review_answer_timestamp", "data_resposta"),
        ),
        "chave": ("avaliacao_id", "pedido_id"),
    },
)

TIPOS = {
    "data_compra": "TIMESTAMP",
    "data_aprovacao": "TIMESTAMP",
    "data_envio": "TIMESTAMP",
    "data_entrega": "TIMESTAMP",
    "data_limite_envio": "TIMESTAMP",
    "data_resposta": "TIMESTAMP",
    "data_entrega_prevista": "DATE",
    "data_criacao": "DATE",
    "preco": "DECIMAL(10,2)",
    "frete": "DECIMAL(10,2)",
    "valor": "DECIMAL(10,2)",
    "item_seq": "INTEGER",
    "pagamento_seq": "INTEGER",
    "parcelas": "INTEGER",
    "tamanho_nome": "INTEGER",
    "tamanho_descricao": "INTEGER",
    "qtd_fotos": "INTEGER",
    "peso_g": "INTEGER",
    "comprimento_cm": "INTEGER",
    "altura_cm": "INTEGER",
    "largura_cm": "INTEGER",
    "nota": "INTEGER",
}


def _identificador(nome):
    return '"' + nome.replace('"', '""') + '"'


def _expressao_sql(coluna_origem, coluna_destino):
    origem = _identificador(coluna_origem)
    tipo = TIPOS.get(coluna_destino)
    if tipo == "TIMESTAMP":
        return f"strptime({origem}, '{FORMATO_DATA_HORA}')"
    if tipo == "DATE":
        return f"CAST(strptime({origem}, '{FORMATO_DATA_HORA}') AS DATE)"
    if tipo:
        return f"CAST({origem} AS {tipo})"
    return origem


def _expressao_parametrizada(coluna_destino):
    tipo = TIPOS[coluna_destino]
    if tipo == "TIMESTAMP":
        return f"strptime(?, '{FORMATO_DATA_HORA}')"
    if tipo == "DATE":
        return f"CAST(strptime(?, '{FORMATO_DATA_HORA}') AS DATE)"
    return f"CAST(? AS {tipo})"


def _valor_invalido(con, tabela, coluna_origem, coluna_destino):
    valores = con.execute(
        f"SELECT DISTINCT {_identificador(coluna_origem)} "
        f"FROM raw.{_identificador(tabela)} "
        f"WHERE {_identificador(coluna_origem)} IS NOT NULL"
    ).fetchall()
    expressao = _expressao_parametrizada(coluna_destino)
    for (valor,) in valores:
        try:
            con.execute(f"SELECT {expressao}", [valor]).fetchall()
        except duckdb.Error:
            return valor
    return "<valor não identificado>"


def _validar_conversoes(con, definicao):
    tabela = definicao["nome"]
    for coluna_origem, coluna_destino in definicao["colunas"]:
        if coluna_destino not in TIPOS:
            continue
        expressao = _expressao_sql(coluna_origem, coluna_destino)
        try:
            con.execute(
                f"SELECT COUNT({expressao}) FROM raw.{_identificador(tabela)}"
            ).fetchall()
        except duckdb.Error as erro:
            valor = _valor_invalido(
                con, tabela, coluna_origem, coluna_destino
            )
            raise ValueError(
                f"Falha de conversão em raw.{tabela}.{coluna_origem}; "
                f"valor de exemplo: {valor!r}. Detalhe: {erro}"
            ) from erro


def _conferir_chaves(con, definicao):
    tabela = definicao["nome"]
    colunas = definicao["colunas"]
    origem_por_destino = {destino: origem for origem, destino in colunas}
    chave_origem = tuple(origem_por_destino[nome] for nome in definicao["chave"])
    selecao_chave = ", ".join(_identificador(coluna) for coluna in chave_origem)
    duplicadas = con.execute(
        f"SELECT {selecao_chave} FROM raw.{_identificador(tabela)} "
        f"GROUP BY {selecao_chave} HAVING COUNT(*) > 1"
    ).fetchall()
    if not duplicadas:
        return

    condicoes = " AND ".join(
        f"r.{_identificador(coluna)} IS NOT DISTINCT FROM "
        f"d.{_identificador(coluna)}"
        for coluna in chave_origem
    )
    linhas = con.execute(
        f"WITH chaves_duplicadas AS ("
        f"SELECT {selecao_chave} FROM raw.{_identificador(tabela)} "
        f"GROUP BY {selecao_chave} HAVING COUNT(*) > 1) "
        f"SELECT r.* FROM raw.{_identificador(tabela)} AS r "
        f"JOIN chaves_duplicadas AS d ON {condicoes}"
    ).fetchall()
    nomes_origem = [origem for origem, _ in colunas]
    nomes_destino = [destino for _, destino in colunas]
    indices_chave = [nomes_origem.index(coluna) for coluna in chave_origem]
    grupos = {}
    for linha in linhas:
        chave = tuple(linha[indice] for indice in indices_chave)
        grupos.setdefault(chave, []).append(linha)

    conflitos = [
        (chave, registros)
        for chave, registros in grupos.items()
        if len(set(registros)) > 1
    ]
    if conflitos:
        print(f"Chave repetida com conteúdo diferente em raw.{tabela}:")
        for chave, registros in conflitos:
            chave_legivel = dict(zip(definicao["chave"], chave))
            print(f"  chave: {json.dumps(chave_legivel, ensure_ascii=False)}")
            distintos = list(dict.fromkeys(registros))
            for registro in distintos:
                linha_legivel = dict(zip(nomes_destino, registro))
                print(f"  linha: {json.dumps(linha_legivel, ensure_ascii=False)}")
        raise SystemExit(1)


def _contagem(con, consulta):
    return con.execute(consulta).fetchall()[0][0]


def _formatar(numero):
    return f"{numero:,}".replace(",", ".")


def _validar_colunas_de_entrada(con):
    for definicao in TABELAS:
        tabela = definicao["nome"]
        colunas_atuais = {
            linha[0]
            for linha in con.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'raw' AND table_name = ?",
                [tabela],
            ).fetchall()
        }
        colunas_mapeadas = {origem for origem, _ in definicao["colunas"]}
        faltantes = sorted(colunas_mapeadas - colunas_atuais)
        extras = sorted(colunas_atuais - colunas_mapeadas)
        if faltantes or extras:
            print(f"Colunas de raw.{tabela} não correspondem ao mapa da spec.")
            if faltantes:
                print(f"  faltantes: {', '.join(faltantes)}")
            if extras:
                print(f"  fora do mapa: {', '.join(extras)}")
            raise SystemExit(1)


def _transformar_tabela(con, definicao):
    tabela = definicao["nome"]
    _conferir_chaves(con, definicao)
    _validar_conversoes(con, definicao)

    entrada = _contagem(
        con, f"SELECT COUNT(*) FROM raw.{_identificador(tabela)}"
    )
    distintos = _contagem(
        con,
        f"SELECT COUNT(*) FROM (SELECT DISTINCT * "
        f"FROM raw.{_identificador(tabela)})",
    )
    removidas = entrada - distintos

    selecao = ", ".join(
        f"{_expressao_sql(origem, destino)} AS {_identificador(destino)}"
        for origem, destino in definicao["colunas"]
    )
    con.execute(
        f"CREATE OR REPLACE TABLE refined.{_identificador(tabela)} AS "
        f"SELECT DISTINCT {selecao} FROM raw.{_identificador(tabela)}"
    ).fetchall()
    saida = _contagem(
        con, f"SELECT COUNT(*) FROM refined.{_identificador(tabela)}"
    )

    colunas_destino = [destino for _, destino in definicao["colunas"]]
    nulos_sql = ", ".join(
        f"COUNT(*) FILTER (WHERE {_identificador(coluna)} IS NULL) "
        f"AS {_identificador(coluna)}"
        for coluna in colunas_destino
    )
    nulos = con.execute(
        f"SELECT {nulos_sql} FROM refined.{_identificador(tabela)}"
    ).fetchone()
    colunas_com_nulos = [
        (coluna, quantidade)
        for coluna, quantidade in zip(colunas_destino, nulos)
        if quantidade > 0
    ]

    print(
        f"refined.{tabela:<24} {_formatar(entrada)} -> "
        f"{_formatar(saida)} linhas  ({_formatar(removidas)} duplicatas)"
    )
    if colunas_com_nulos:
        resumo = ", ".join(
            f"{coluna} {_formatar(quantidade)}"
            for coluna, quantidade in colunas_com_nulos
        )
        print(f"    nulos mantidos: {resumo}")
    return entrada, saida, removidas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con = db.conectar()
    try:
        existentes = {
            linha[0]
            for linha in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'raw' AND table_type = 'BASE TABLE'"
            ).fetchall()
        }
        faltantes = [
            definicao["nome"]
            for definicao in TABELAS
            if definicao["nome"] not in existentes
        ]
        if faltantes:
            print("Tabelas ausentes em raw:")
            for tabela in faltantes:
                print(f"  raw.{tabela}")
            print("Rode: uv run python -m pipeline.ingestao")
            raise SystemExit(1)

        _validar_colunas_de_entrada(con)
        db.criar_schema(con, "refined")
        total_entrada = 0
        total_saida = 0
        total_duplicatas = 0
        for definicao in TABELAS:
            try:
                entrada, saida, duplicatas = _transformar_tabela(con, definicao)
            except ValueError as erro:
                print(erro)
                raise SystemExit(1) from erro
            total_entrada += entrada
            total_saida += saida
            total_duplicatas += duplicatas

        print(
            f"Total: {_formatar(total_entrada)} -> {_formatar(total_saida)} "
            f"linhas  ({_formatar(total_duplicatas)} duplicatas)"
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
