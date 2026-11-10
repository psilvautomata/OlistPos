"""CONTEXTO
Pipeline de dados em Python sobre o dataset público da Olist. Esta spec é a
fonte da verdade; o código é consequência dela e não acrescenta regra de
negócio.

STACK
Python 3.13, uv e DuckDB em olist.duckdb na raiz do projeto.

O QUE JÁ EXISTE
pipeline/db.py expõe conectar() e criar_schema(con, nome). O schema refined
contém as oito tabelas criadas por pipeline/transformacao.py. Os arquivos
sql/marts/*.sql contêm um único SELECT, que pode começar com comentários e
WITH.

ARTEFATO
pipeline/marts.py, executável com uv run python -m pipeline.marts.

1. ESCOPO
Lê de refined e escreve no schema marts. Nunca escreve em raw nem refined.
Apaga e recria marts dentro de uma única transação. Isso impede que marts
removidos do diretório continuem no banco e garante que qualquer falha deixe
o último schema que executou com sucesso. Verifica as oito entradas antes de
recriar marts para não publicar resultados baseados em refined incompleto.

2. UM ARQUIVO, UMA TABELA
Lê sql/marts/*.sql em ordem alfabética. O nome da tabela é o nome do arquivo
sem .sql e sem o prefixo NN_; por exemplo, 01_vendas_mensais.sql cria
marts.vendas_mensais. Executa CREATE TABLE marts.<nome> AS <conteúdo do
arquivo>, removendo somente espaços externos e um ponto e vírgula final. O
Python não altera, monta nem completa a SQL, pois a regra de negócio mora no
arquivo SQL.

3. SAÍDA
Mostra uma linha por mart com a contagem consultada no banco, separador de
milhares por ponto, e uma linha final com número de marts e total de linhas.
As contagens do banco confirmam o que foi gravado. stdout usa UTF-8 para
preservar acentos.

4. ERROS
Antes da recriação, exige as oito tabelas de entrada em refined; se faltar
alguma, lista e orienta rodar uv run python -m pipeline.transformacao. Se
sql/marts não tiver arquivos, avisa e encerra em vez de apagar marts e deixar
um schema vazio. Antes de executar qualquer arquivo SQL, valida todos os
nomes: exige prefixo NN_ e não permite nomes de tabela repetidos, evitando
começar uma carga com nomes inválidos ou colisões. Erros de SQL mostram o
arquivo e a mensagem do DuckDB,
interrompem a sequência e encerram com sys.exit(1). Mart com zero linhas
também interrompe a execução, pois um dashboard vazio pode parecer um negócio
parado quando na verdade um JOIN não casou. Todos os passos de recriação e
carga pertencem à mesma transação; qualquer falha, inclusive mart vazio,
restaura o schema marts da última execução bem-sucedida.

CRITÉRIOS DE ACEITE
- 00_teste.sql com SELECT 1 AS x cria marts.teste com uma linha.
- Apagar 00_teste.sql enquanto ao menos outro arquivo SQL permanece remove
  marts.teste na próxima execução.
- Erro de sintaxe mostra o nome do arquivo, interrompe e mantém marts intacto.
- teste.sql sem prefixo interrompe antes de executar arquivos SQL.
- Duas execuções iguais imprimem a mesma saída.

ENTREGA
Esta docstring registra a spec e o motivo das regras. O código tem comentários
somente quando a decisão não é óbvia. A lista final identifica pressupostos
que não aparecem na spec.
"""

from pathlib import Path
import re
import sys

import duckdb

from pipeline import db


TABELAS_REFINED = (
    "pedidos",
    "itens_pedido",
    "pagamentos",
    "clientes",
    "vendedores",
    "produtos",
    "traducao_categorias",
    "avaliacoes",
)
PASTA_MARTS = Path(__file__).resolve().parent.parent / "sql" / "marts"
PADRAO_ARQUIVO = re.compile(r"[0-9]{2}_(.+)")


class _ErroArquivoMart(Exception):
    def __init__(self, arquivo, mensagem):
        self.arquivo = arquivo
        self.mensagem = mensagem
        super().__init__(mensagem)


class _MartVazio(Exception):
    def __init__(self, arquivo):
        self.arquivo = arquivo
        super().__init__(arquivo)


def _identificador(nome):
    return '"' + nome.replace('"', '""') + '"'


def _formatar(numero):
    return f"{numero:,}".replace(",", ".")


def _tabelas_ausentes(con):
    existentes = {
        linha[0]
        for linha in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'refined' AND table_type = 'BASE TABLE'"
        ).fetchall()
    }
    return [nome for nome in TABELAS_REFINED if nome not in existentes]


def _ler_arquivos():
    arquivos = sorted(PASTA_MARTS.glob("*.sql"), key=lambda caminho: caminho.name)
    if not arquivos:
        print(f"Nenhum arquivo .sql em {PASTA_MARTS}.")
        return None

    sem_prefixo = []
    por_nome = {}
    for arquivo in arquivos:
        correspondencia = PADRAO_ARQUIVO.fullmatch(arquivo.stem)
        if correspondencia is None:
            sem_prefixo.append(arquivo.name)
            continue
        nome_tabela = correspondencia.group(1)
        por_nome.setdefault(nome_tabela.casefold(), []).append(
            (nome_tabela, arquivo)
        )

    duplicados = [
        itens for itens in por_nome.values() if len(itens) > 1
    ]
    if sem_prefixo:
        print("Arquivos sem prefixo NN_:")
        for nome in sem_prefixo:
            print(f"  {nome}")
    if duplicados:
        print("Arquivos com nomes de tabela repetidos:")
        for itens in duplicados:
            print("  " + ", ".join(arquivo.name for _, arquivo in itens))
    if sem_prefixo or duplicados:
        return None

    lidos = []
    for arquivo in arquivos:
        nome_tabela = arquivo.stem[3:]
        try:
            sql = arquivo.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as erro:
            print(f"Falha ao ler {arquivo.name}: {erro}")
            return None
        if sql.endswith(";"):
            sql = sql[:-1]
        lidos.append((nome_tabela, arquivo, sql))
    return lidos


def _recriar_marts(con, arquivos):
    resultados = []
    total_linhas = 0
    try:
        con.execute("BEGIN TRANSACTION")
        con.execute("DROP SCHEMA IF EXISTS marts CASCADE")
        db.criar_schema(con, "marts")

        for nome_tabela, arquivo, sql in arquivos:
            identificador = _identificador(nome_tabela)
            try:
                con.execute(
                    f"CREATE TABLE marts.{identificador} AS {sql}"
                )
                quantidade = con.execute(
                    f"SELECT COUNT(*) FROM marts.{identificador}"
                ).fetchone()[0]
            except duckdb.Error as erro:
                raise _ErroArquivoMart(arquivo.name, str(erro)) from erro

            if quantidade == 0:
                raise _MartVazio(arquivo.name)
            resultados.append((nome_tabela, quantidade))
            total_linhas += quantidade

        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except duckdb.Error:
            pass
        raise

    return resultados, total_linhas


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    con = db.conectar()
    try:
        faltantes = _tabelas_ausentes(con)
        if faltantes:
            print("Tabelas ausentes em refined:")
            for tabela in faltantes:
                print(f"  refined.{tabela}")
            print("Rode: uv run python -m pipeline.transformacao")
            return 1

        arquivos = _ler_arquivos()
        if arquivos is None:
            return 1

        try:
            resultados, total_linhas = _recriar_marts(con, arquivos)
        except _ErroArquivoMart as erro:
            print(f"Falha no arquivo {erro.arquivo}: {erro.mensagem}")
            return 1
        except _MartVazio as erro:
            print(f"Mart vazio no arquivo {erro.arquivo}.")
            return 1
        except duckdb.Error as erro:
            print(f"Falha ao recriar o schema marts: {erro}")
            return 1

        largura = max(len(nome) for nome, _ in resultados)
        for nome, quantidade in resultados:
            print(
                f"✓ marts.{nome:<{largura}}  "
                f"{_formatar(quantidade)} linhas"
            )
        print(
            f"Total: {len(resultados)} marts, "
            f"{_formatar(total_linhas)} linhas"
        )
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
