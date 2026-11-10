"""Inicia no navegador a interface DuckDB para explorar o banco do pipeline.

O script abre o olist.duckdb da raiz do projeto e instala/carrega a extensão
ui antes de chamar start_ui(), que serve a interface em http://localhost:4213
e abre o navegador. Verificar o arquivo antes de conectar evita criar um
banco vazio que pareça uma ingestão quebrada; por isso este script não usa
conectar() de pipeline.db, que cria o banco se ele estiver ausente.

A conexão fica aberta e o processo aguarda Ctrl+C porque o servidor da
extensão depende da conexão viva e o arquivo DuckDB mantém bloqueio enquanto
está aberto. No Ctrl+C a conexão é fechada sem traceback para que a ingestão
possa rodar logo depois. O stdout usa UTF-8 para que as instruções apareçam
corretamente no Prompt de Comando do Windows. A interface e a ingestão são
independentes; cada uma é iniciada pelo seu próprio comando.
"""

from pathlib import Path
import sys
import threading

import duckdb


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    caminho_banco = Path(__file__).resolve().parent / "olist.duckdb"
    if not caminho_banco.is_file():
        print(
            f"Banco não encontrado em {caminho_banco}. "
            "É preciso rodar a ingestão antes."
        )
        raise SystemExit(1)

    con = duckdb.connect(str(caminho_banco))
    try:
        con.execute("INSTALL ui")
        con.execute("LOAD ui")
        con.execute("CALL start_ui()")
        print("Interface disponível em http://localhost:4213")
        print("Ctrl+C para encerrar")
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        con.close()


if __name__ == "__main__":
    main()
