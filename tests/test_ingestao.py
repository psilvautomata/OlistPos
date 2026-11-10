from pathlib import Path

import duckdb
import pandas as pd
import pytest

from pipeline import ingestao


class SaidaFalsa:
    def __init__(self):
        self.texto = ""

    def reconfigure(self, **kwargs):
        self.encoding = kwargs["encoding"]

    def write(self, texto):
        self.texto += texto

    def flush(self):
        pass


def test_arquivos_ausentes_param_antes_de_conectar(monkeypatch, tmp_path):
    saida = SaidaFalsa()
    monkeypatch.setattr(ingestao.db, "PASTA_RAW", tmp_path)
    monkeypatch.setattr(ingestao.sys, "stdout", saida)
    monkeypatch.setattr(
        ingestao.db,
        "conectar",
        lambda: pytest.fail("não deveria conectar com arquivos ausentes"),
    )

    with pytest.raises(SystemExit) as erro:
        ingestao.main()

    assert erro.value.code == 1
    assert saida.encoding == "utf-8"
    for nome_arquivo, _ in ingestao.ARQUIVOS:
        assert nome_arquivo in saida.texto


def test_ingestao_grava_nove_tabelas_com_todas_as_linhas(
    monkeypatch,
    tmp_path,
):
    pasta_raw = tmp_path / "raw"
    pasta_raw.mkdir()
    caminho_banco = tmp_path / "teste.duckdb"
    saida = SaidaFalsa()
    chamadas = []

    for nome_arquivo, _ in ingestao.ARQUIVOS:
        (pasta_raw / nome_arquivo).touch()

    def ler_csv(caminho, **kwargs):
        chamadas.append((Path(caminho).name, kwargs))
        return pd.DataFrame(
            {"codigo": pd.Series(["00123", None], dtype="object")}
        )

    monkeypatch.setattr(ingestao.db, "PASTA_RAW", pasta_raw)
    monkeypatch.setattr(ingestao.sys, "stdout", saida)
    monkeypatch.setattr(
        ingestao.db,
        "conectar",
        lambda: duckdb.connect(str(caminho_banco)),
    )
    monkeypatch.setattr(ingestao.pd, "read_csv", ler_csv)

    ingestao.main()

    con = duckdb.connect(str(caminho_banco), read_only=True)
    try:
        tabelas = {
            linha[0]
            for linha in con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'raw'"
            ).fetchall()
        }
        codigo = con.execute(
            "SELECT codigo FROM raw.pedidos WHERE codigo IS NOT NULL"
        ).fetchone()[0]
        nulos = con.execute(
            "SELECT count(*) FROM raw.pedidos WHERE codigo IS NULL"
        ).fetchone()[0]
    finally:
        con.close()

    assert tabelas == {tabela for _, tabela in ingestao.ARQUIVOS}
    assert len(chamadas) == 9
    assert all(
        chamada[1]
        == {
            "compression": "gzip",
            "encoding": "utf-8",
            "dtype": str,
            "keep_default_na": False,
            "na_values": [""],
            "skip_blank_lines": False,
        }
        for chamada in chamadas
    )
    assert codigo == "00123"
    assert nulos == 1
    assert "Total: 18" in saida.texto
