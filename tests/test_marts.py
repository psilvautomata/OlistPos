from pathlib import Path

import duckdb
import pytest

from pipeline import marts


@pytest.fixture
def con():
    conexao = duckdb.connect(":memory:")
    yield conexao
    conexao.close()


def test_formatar_e_identificador():
    assert marts._formatar(1234567) == "1.234.567"
    assert marts._identificador('tabela"x') == '"tabela""x"'


def test_ler_arquivos_ordena_e_remove_apenas_espacos_externos_e_ponto_final(
    monkeypatch,
    tmp_path,
):
    (tmp_path / "02_segundo.sql").write_text("SELECT 2;\n", encoding="utf-8")
    (tmp_path / "01_primeiro.sql").write_text("  SELECT 1;  \n", encoding="utf-8")
    monkeypatch.setattr(marts, "PASTA_MARTS", tmp_path)

    arquivos = marts._ler_arquivos()

    assert [arquivo[0] for arquivo in arquivos] == ["primeiro", "segundo"]
    assert [arquivo[2] for arquivo in arquivos] == ["SELECT 1", "SELECT 2"]


def test_ler_arquivos_rejeita_nome_sem_prefixo(monkeypatch, tmp_path, capsys):
    (tmp_path / "01_certo.sql").write_text("SELECT 1", encoding="utf-8")
    (tmp_path / "sem_prefixo.sql").write_text("SELECT 2", encoding="utf-8")
    monkeypatch.setattr(marts, "PASTA_MARTS", tmp_path)

    assert marts._ler_arquivos() is None
    assert "sem_prefixo.sql" in capsys.readouterr().out


def test_ler_arquivos_rejeita_destinos_duplicados(monkeypatch, tmp_path, capsys):
    for nome in ("01_resumo.sql", "02_resumo.sql"):
        (tmp_path / nome).write_text("SELECT 1", encoding="utf-8")
    monkeypatch.setattr(marts, "PASTA_MARTS", tmp_path)

    assert marts._ler_arquivos() is None
    saida = capsys.readouterr().out
    assert "01_resumo.sql" in saida
    assert "02_resumo.sql" in saida


def test_recriar_marts_substitui_schema_em_transacao(con):
    con.execute("CREATE SCHEMA marts")
    con.execute("CREATE TABLE marts.antiga AS SELECT 9 AS valor")

    resultado, total = marts._recriar_marts(
        con,
        [("nova", Path("01_nova.sql"), "SELECT 1 AS valor")],
    )

    tabelas = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'marts'"
    ).fetchall()
    assert resultado == [("nova", 1)]
    assert total == 1
    assert tabelas == [("nova",)]


def test_erro_sql_faz_rollback_e_preserva_schema_anterior(con):
    con.execute("CREATE SCHEMA marts")
    con.execute("CREATE TABLE marts.anterior AS SELECT 7 AS valor")
    arquivos = [
        ("novo", Path("01_novo.sql"), "SELECT 1 AS valor"),
        ("erro", Path("02_erro.sql"), "SELECT coluna_inexistente"),
    ]

    with pytest.raises(marts._ErroArquivoMart) as erro:
        marts._recriar_marts(con, arquivos)

    assert erro.value.arquivo == "02_erro.sql"
    assert con.execute("SELECT valor FROM marts.anterior").fetchall() == [(7,)]
    assert con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'marts' AND table_name = 'novo'"
    ).fetchone()[0] == 0


def test_mart_vazio_faz_rollback_e_preserva_schema_anterior(con):
    con.execute("CREATE SCHEMA marts")
    con.execute("CREATE TABLE marts.anterior AS SELECT 7 AS valor")

    with pytest.raises(marts._MartVazio):
        marts._recriar_marts(
            con,
            [("vazio", Path("01_vazio.sql"), "SELECT 1 WHERE FALSE")],
        )

    assert con.execute("SELECT valor FROM marts.anterior").fetchall() == [(7,)]
