"""Contrato comum de conexão e gravação das etapas do curso.

API pública: a constante PASTA_RAW e somente as funções conectar(),
criar_schema(con, nome) e gravar(con, df, schema, tabela). O caminho de
PASTA_RAW e de olist.duckdb é calculado a partir deste arquivo (a raiz do
projeto), pois uma execução iniciada em outra pasta não deve criar um banco
vazio no lugar errado. PASTA_RAW aponta para dados/raw/, que é onde estão os
arquivos deste workspace.

Este módulo não lê CSVs, não conhece nomes de tabelas, não imprime e não
converte tipos. As decisões de cada etapa ficam nela, porque uma regra de
negócio escondida aqui seria aplicada a todas as aulas sem aparecer na spec.

criar_schema usa CREATE SCHEMA IF NOT EXISTS para permitir reexecução sem
falhar quando o schema já existe. gravar usa CREATE OR REPLACE TABLE para
substituir a tabela, preservando colunas, tipos e nulos do DataFrame; assim a
execução não duplica dados nem muda o conteúdo recebido. O registro usado
para copiar o DataFrame é removido ao final para não deixar objeto temporário.
A contagem vem de SELECT count(*) no banco para conferir o que foi gravado,
em vez de confiar na contagem em memória. conectar devolve uma conexão aberta
para o chamador fechar: não há conexão global que esconda ciclo de vida ou
mantenha um bloqueio inesperado no arquivo.
"""

from pathlib import Path as _Path

import duckdb as _duckdb


PASTA_RAW = _Path(__file__).resolve().parent.parent / "dados" / "raw"


def conectar():
    """Abre o banco localizado na raiz do projeto, criando-o se necessário."""
    caminho_banco = _Path(__file__).resolve().parent.parent / "olist.duckdb"
    return _duckdb.connect(str(caminho_banco))


def criar_schema(con, nome):
    """Cria o schema se ainda não existir."""
    identificador = '"' + nome.replace('"', '""') + '"'
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {identificador}")


def gravar(con, df, schema, tabela):
    """Substitui uma tabela pelo DataFrame e devolve a contagem do banco."""
    identificador_schema = '"' + schema.replace('"', '""') + '"'
    identificador_tabela = '"' + tabela.replace('"', '""') + '"'
    nome_registro = f"_df_gravar_{id(df):x}"

    con.register(nome_registro, df)
    try:
        con.execute(
            f"CREATE OR REPLACE TABLE {identificador_schema}.{identificador_tabela} "
            f"AS SELECT * FROM {nome_registro}"
        )
        resultado = con.execute(
            f"SELECT count(*) FROM {identificador_schema}.{identificador_tabela}"
        ).fetchall()
        return resultado[0][0]
    finally:
        con.unregister(nome_registro)
