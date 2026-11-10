from decimal import Decimal

import duckdb
import pytest

from pipeline import transformacao


DEFINICAO = {
    "nome": "itens_teste",
    "colunas": (
        ("order_id", "pedido_id"),
        ("price", "preco"),
        ("purchase", "data_compra"),
    ),
    "chave": ("pedido_id",),
}


@pytest.fixture
def con():
    conexao = duckdb.connect(":memory:")
    conexao.execute("CREATE SCHEMA raw")
    conexao.execute("CREATE SCHEMA refined")
    yield conexao
    conexao.close()


def test_expressao_sql_aplica_tipos_e_preserva_coluna_textual():
    assert transformacao._expressao_sql("price", "preco") == (
        'CAST("price" AS DECIMAL(10,2))'
    )
    assert transformacao._expressao_sql("purchase", "data_compra") == (
        'strptime("purchase", \'%Y-%m-%d %H:%M:%S\')'
    )
    assert transformacao._expressao_sql("city", "cidade") == '"city"'


def test_transformar_tabela_remove_repeticao_identica_e_preserva_nulo(con):
    con.execute(
        "CREATE TABLE raw.itens_teste AS SELECT * FROM (VALUES "
        "('p1', '10.25', '2024-01-01 12:30:00'), "
        "('p1', '10.25', '2024-01-01 12:30:00'), "
        "('p2', NULL, '2024-01-02 13:30:00')"
        ") AS dados(order_id, price, purchase)"
    )

    resultado = transformacao._transformar_tabela(con, DEFINICAO)
    linhas = con.execute(
        "SELECT pedido_id, preco, data_compra "
        "FROM refined.itens_teste ORDER BY pedido_id"
    ).fetchall()
    tipos = {
        linha[0]: linha[1]
        for linha in con.execute("DESCRIBE refined.itens_teste").fetchall()
    }

    assert resultado == (3, 2, 1)
    assert [linha[:2] for linha in linhas] == [
        ("p1", Decimal("10.25")),
        ("p2", None),
    ]
    assert str(linhas[0][2]) == "2024-01-01 12:30:00"
    assert str(linhas[1][2]) == "2024-01-02 13:30:00"
    assert tipos == {
        "pedido_id": "VARCHAR",
        "preco": "DECIMAL(10,2)",
        "data_compra": "TIMESTAMP",
    }


def test_falha_de_cast_mostra_tabela_coluna_e_valor(con):
    con.execute(
        "CREATE TABLE raw.itens_teste AS SELECT "
        "'p1' AS order_id, 'valor-invalido' AS price, "
        "'2024-01-01 12:30:00' AS purchase"
    )

    with pytest.raises(ValueError, match="raw.itens_teste.price") as erro:
        transformacao._validar_conversoes(con, DEFINICAO)

    assert "valor-invalido" in str(erro.value)


def test_chave_com_conteudo_conflitante_interrompe(con, capsys):
    con.execute(
        "CREATE TABLE raw.itens_teste AS SELECT * FROM (VALUES "
        "('p1', '10.25', '2024-01-01 12:30:00'), "
        "('p1', '10.26', '2024-01-01 12:30:00')"
        ") AS dados(order_id, price, purchase)"
    )

    with pytest.raises(SystemExit) as erro:
        transformacao._conferir_chaves(con, DEFINICAO)

    saida = capsys.readouterr().out
    assert erro.value.code == 1
    assert "itens_teste" in saida
    assert "p1" in saida
    assert "10.25" in saida and "10.26" in saida
