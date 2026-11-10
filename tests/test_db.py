from decimal import Decimal

import duckdb
import pandas as pd

from pipeline import db


def test_criar_schema_eh_idempotente_e_escapa_identificador():
    con = duckdb.connect(":memory:")
    nome = 'schema"teste'
    try:
        db.criar_schema(con, nome)
        db.criar_schema(con, nome)
        resultado = con.execute(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = ?",
            [nome],
        ).fetchall()
    finally:
        con.close()

    assert resultado == [(nome,)]


def test_gravar_substitui_tabela_e_preserva_texto_nulos_e_decimal():
    con = duckdb.connect(":memory:")
    try:
        db.criar_schema(con, "refined")
        con.execute("CREATE TABLE refined.ceps AS SELECT 'antigo' AS cep")
        dados = pd.DataFrame(
            {
                "cep": pd.Series(["00123", None], dtype="object"),
                "valor": pd.Series(
                    [Decimal("12.30"), None],
                    dtype="object",
                ),
            }
        )

        quantidade = db.gravar(con, dados, "refined", "ceps")
        linhas = con.execute(
            "SELECT cep, valor FROM refined.ceps ORDER BY cep NULLS FIRST"
        ).fetchall()
        tipos = con.execute("DESCRIBE refined.ceps").fetchall()
    finally:
        con.close()

    assert quantidade == 2
    assert linhas == [(None, None), ("00123", Decimal("12.30"))]
    assert {linha[0]: linha[1] for linha in tipos} == {
        "cep": "VARCHAR",
        "valor": "DECIMAL(4,2)",
    }
