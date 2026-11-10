CONTEXTO
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
   Entram as nove tabelas: pedidos, itens_pedido, pagamentos, clientes,
   vendedores, produtos, traducao_categorias, avaliacoes e geolocalizacao.
   Nenhuma tabela fica de fora.
   geolocalizacao entra como observações geográficas distintas; não será
   reduzida a uma linha por CEP porque o CEP não identifica uma coordenada
   única.

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
   geolocalizacao
     geolocation_zip_code_prefix -> cep_prefixo
     geolocation_lat -> latitude            geolocation_lng -> longitude
     geolocation_city -> cidade             geolocation_state -> uf

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
   Em geolocalizacao, latitude e longitude viram DECIMAL(23,20). Motivo:
     as coordenadas são medidas decimais, com até 20 casas fracionárias e
     até três algarismos inteiros neste snapshot; esse tipo mantém os dígitos
     recebidos sem a aproximação de DOUBLE. cep_prefixo, cidade e uf ficam
     VARCHAR. CEP continua sendo identificador; cidade e UF são rótulos, não
     medidas.
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
     geolocalizacao (cep_prefixo, latitude, longitude, cidade, uf)
       — não há id de observação nem chave única por CEP. A chave é a linha
         completa: registros com o mesmo CEP e outros valores diferentes
         são observações distintas, não conflitos.
   Linha inteira repetida: mantém uma, e conta quantas saíram.
   Chave repetida com conteúdo diferente: para, mostra a chave e as linhas
   conflitantes, sys.exit(1). Não escolhe uma por conta própria.
   Para geolocalizacao, só a repetição da linha completa é duplicata; não
   agrega coordenadas, não escolhe cidade/UF e não filtra coordenadas
   extremas. Motivo: 17.823 CEPs têm mais de uma observação distinta, 8.556
   têm mais de um rótulo de cidade e 8 têm mais de um rótulo de UF. Colapsar
   essas linhas escolheria uma localização sem regra de negócio.
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
   responde. geolocalizacao não tem nulos nas cinco colunas neste snapshot;
   nenhum valor será preenchido ou removido por nulo.

7. SAÍDA NA TELA
   Uma linha por tabela, no formato:
     refined.pedidos            99.441 -> 99.441 linhas  (0 duplicatas)
     refined.geolocalizacao     1.000.163 -> 738.332 linhas  (261.831 duplicatas)
   Abaixo dela, indentadas, as colunas com nulo e a contagem:
       nulos mantidos: data_aprovacao 160, data_envio 1.783, data_entrega 2.965
   As contagens vêm do banco, milhar separado por ponto. Linha final com o
   total. Para geolocalizacao, não há resumo de nulos quando todas as cinco
   colunas têm contagem zero. stdout reconfigurado para utf-8.

REEXECUÇÃO
   CREATE OR REPLACE TABLE, nunca acrescenta. Rodar dez vezes = rodar uma.

ERRO
   Antes de transformar, verifica se as nove tabelas de entrada existem em
   raw. Faltando qualquer uma: lista quais, diz para rodar
   "uv run python -m pipeline.ingestao" e encerra com sys.exit(1).

CRITÉRIOS DE ACEITE
- Nove tabelas em refined. Nas oito tabelas já especificadas, as 550.759
  linhas entram e saem sem duplicatas. Em geolocalizacao, 1.000.163 entram,
  738.332 saem e 261.831 linhas inteiras repetidas são removidas. Total:
  1.550.922 linhas de entrada e 1.289.091 de saída.
- refined.geolocalizacao tem 19.015 CEPs distintos; 17.823 CEPs continuam
  com mais de uma observação, 8.556 com mais de uma cidade e 8 com mais de
  uma UF. Os 4.354 CEPs distintos iniciados por zero continuam VARCHAR.
- DESCRIBE refined.geolocalizacao mostra cep_prefixo, cidade e uf como
  VARCHAR, e latitude e longitude como DECIMAL(23,20).
- Cada uma das cinco colunas de geolocalizacao tem zero nulos antes e depois;
  nenhuma latitude ou longitude falha na conversão estrita.
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
