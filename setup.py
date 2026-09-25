"""
Pipeline completo - F105 Datamining e Webscraping

Executa em ordem:
    1. Captura o token do São Luiz (grava .env na raiz)
    2. Coleta São Luiz (lê .env automaticamente)
    3. Coleta Carrefour
    4. Coleta Pão de Açúcar
    5. Tratamento dos dados brutos
    6. Análise + gráficos + insights

Uso:
    python setup.py

Os 3 raspadores escrevem no MESMO arquivo dados/dados_brutos.csv via append.
Por isso o setup apaga esse arquivo antes de começar, para evitar duplicação.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DADOS_BRUTOS = RAIZ / "dados" / "dados_brutos.csv"

PIPELINE = [
    ("1/6 - Capturando token do São Luiz", "token/get_token_sao_luiz.py"),
    ("2/6 - Coletando São Luiz",           "raspadores/coleta_sao_luiz.py"),
    ("3/6 - Coletando Carrefour",          "raspadores/coleta_carrefour.py"),
    ("4/6 - Coletando Pão de Açúcar",      "raspadores/coleta_pao_de_acucar.py"),
    ("5/6 - Tratando dados brutos",        "tratamento.py"),
    ("6/6 - Analisando e gerando gráficos", "analise.py"),
]


def banner(texto: str) -> None:
    print("\n" + "=" * 60)
    print(texto)
    print("=" * 60)


def limpar_dados_brutos() -> None:
    if DADOS_BRUTOS.exists():
        DADOS_BRUTOS.unlink()
        print(f"[setup] Removido {DADOS_BRUTOS.relative_to(RAIZ)} (evita duplicação no append)")


def rodar(script_relativo: str) -> None:
    caminho = RAIZ / script_relativo

    if not caminho.exists():
        raise FileNotFoundError(f"Script não encontrado: {caminho}")

    # sys.executable garante que usa o MESMO python da venv atual
    subprocess.run(
        [sys.executable, str(caminho)],
        cwd=RAIZ,          # raiz como cwd: imports e caminhos relativos funcionam
        check=True,        # se falhar, interrompe o pipeline
    )


def main() -> None:
    banner("PIPELINE F105 - Datamining e Webscraping")
    print(f"Raiz do projeto: {RAIZ}")
    print(f"Python: {sys.executable}")

    limpar_dados_brutos()

    inicio = time.time()

    for i, (descricao, script) in enumerate(PIPELINE, start=1):
        banner(descricao)
        t0 = time.time()
        try:
            rodar(script)
        except subprocess.CalledProcessError as e:
            print(f"\n[setup] FALHOU na etapa '{descricao}' (exit code {e.returncode}).")
            print("[setup] Abortando pipeline.")
            sys.exit(e.returncode)
        except FileNotFoundError as e:
            print(f"\n[setup] {e}")
            sys.exit(1)

        duracao = time.time() - t0
        print(f"[setup] OK ({duracao:.1f}s)")

    total = time.time() - inicio
    banner(f"PIPELINE CONCLUÍDO em {total:.1f}s")
    print("Arquivos gerados:")
    print("  dados/dados_brutos.csv")
    print("  dados/dados_tratados.csv")
    print("  dados/itens_excluidos.csv")
    print("  dados/estatisticas_descritivas.csv")
    print("  dados/estatisticas_por_fonte.csv")
    print("  dados/resumo_menor_maior_preco.csv")
    print("  dados/mais_baratos_por_tipo.csv")
    print("  graficos/grafico1_preco_medio.png")
    print("  graficos/grafico2_distribuicao_precos.png")
    print("  graficos/grafico3_menor_maior_preco.png")
    print("  graficos/grafico4_preco_medio_por_fonte.png")
    print("  graficos/dashboard.png")
    print("  insights.txt")


if __name__ == "__main__":
    main()
