# Spec de transformação de geolocalização

## Contexto

O schema `raw` contém nove tabelas, todas com colunas `VARCHAR` e campos
vazios como `NULL`. Esta spec define a transformação isolada de
`raw.geolocalizacao` para `refined.geolocalizacao`. Ela é separada de
`specs/transformacao.md`; os critérios das outras oito tabelas e o total de
550.759 linhas permanecem inalterados.

## 1. Escopo

- Lê somente `raw.geolocalizacao` e grava somente `refined.geolocalizacao`.
- Não altera nenhuma tabela de `raw`.
- Este fluxo é executado por um script separado da transformação das outras
  oito tabelas.
- O caminho e o comando do script serão definidos antes da implementação.

## 2. Nomes

Renomeia todas as colunas conforme o mapa completo e literal; não descarta
colunas:

| Coluna de origem | Coluna refined |
|---|---|
| `geolocation_zip_code_prefix` | `cep_prefixo` |
| `geolocation_lat` | `latitude` |
| `geolocation_lng` | `longitude` |
| `geolocation_city` | `cidade` |
| `geolocation_state` | `uf` |

## 3. Tipos

- `latitude`, `longitude`: `DOUBLE`. São medidas contínuas, não valores
  monetários; o snapshot não apresenta falhas de `CAST` nas 1.000.163 linhas.
- `cep_prefixo`: `VARCHAR`. É identificador, não número; 245.733 linhas
  começam com zero.
- `cidade`, `uf`: `VARCHAR`, pois são rótulos.

## 4. Conversão que falha

Conversões usam `CAST` estrito no DuckDB. Não usar `TRY_CAST` nem transformar
falha em nulo. Se houver falha, informar tabela, coluna e um valor de exemplo,
e encerrar com `sys.exit(1)`. O snapshot tem zero falhas ao converter latitude
e longitude.

## 5. Duplicatas e grão

- Grão: um ponto observado, identificado pela linha completa
  (`cep_prefixo`, `latitude`, `longitude`, `cidade`, `uf`).
- `cep_prefixo` não é chave. Há 19.015 CEPs distintos na entrada e até 1.146
  linhas de entrada no mesmo CEP.
- Linha inteira repetida: manter uma e contar a removida. No snapshot,
  1.000.163 linhas de entrada resultam em 738.332 linhas, com 261.831
  duplicatas removidas.
- Não agregar para um ponto por CEP. Média, mediana ou moda respondem a uma
  pergunta analítica; essa regra pertence ao mart que fizer a pergunta.
- CEPs repetidos com coordenadas, cidade ou UF diferentes são observações
  distintas, não conflitos de chave.

## 6. Nulos e anomalias

Nenhuma linha é removida por conter nulo e nenhum nulo é preenchido. No
snapshot, as cinco colunas têm zero nulos; se surgirem nulos, devem ser
mantidos.

Preservar, sem correção ou normalização:

- As 42 linhas fora da caixa geográfica latitude `-33,75..5,27` e longitude
  `-73,99..-34,79`.
- Os 8 CEPs associados a duas UFs.
- Grafias de cidade com e sem acento, como `sao paulo` e `são paulo`.

`refined` preserva os fatos da origem. Interpretar ou corrigir essas
anomalias cabe a quem formular a pergunta analítica.

## 7. Reexecução, erros e saída

- Usar `CREATE OR REPLACE TABLE`; reexecutar não acrescenta linhas.
- Antes de transformar, verificar se `raw.geolocalizacao` existe. Se faltar,
  informar que a tabela está ausente, orientar a execução de
  `uv run python -m pipeline.ingestao` e encerrar com `sys.exit(1)`.
- Exibir linhas de entrada, linhas de saída, duplicatas removidas e nulos
  por coluna; separar milhares com ponto. Reconfigurar stdout para UTF-8.

## Critérios de aceite

- `raw.geolocalizacao`: 1.000.163 linhas; `refined.geolocalizacao`: 738.332
  linhas; 261.831 duplicatas removidas.
- As cinco colunas aparecem em `refined` com os nomes especificados;
  `latitude` e `longitude` são `DOUBLE`, e `cep_prefixo`, `cidade` e `uf`
  são `VARCHAR`.
- Zero falhas de conversão e zero nulos em cada coluna neste snapshot.
- Os 19.015 CEPs distintos permanecem presentes; os CEPs repetidos não são
  agregados. `cep_prefixo` conserva zeros à esquerda.
- Permanecem representadas as 42 linhas fora da caixa, os 8 CEPs associados
  a duas UFs e as grafias de cidade com e sem acento, exceto cópias de linhas
  inteiras removidas pela regra de duplicatas.
- Um JOIN direto com `clientes` por `cep_prefixo` pode multiplicar as
  99.441 linhas para 15.083.455. Consumidores devem reduzir a geolocalização
  a um ponto por CEP em um mart, com a regra de agregação escrita nesse mart.
