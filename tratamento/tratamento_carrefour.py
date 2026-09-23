"""
Pré-processamento - F105 Datamining e Webscraping

Lê:
    dados/dados_brutos_carrefour.csv

Gera:
    dados/dados_tratados_carrefour.csv
    dados/itens_excluidos_carrefour.csv

Tratamentos realizados:
- correção de encoding dos nomes dos produtos;
- remoção de registros sem nome ou preço;
- preenchimento de preco_original quando não há promoção;
- remoção de duplicidades pelo codigo_produto;
- padronização dos preços;
- recálculo do percentual de desconto;
- normalização de acentos para filtro;
- filtro de relevância por categoria pesquisada.
"""

import unicodedata

import pandas as pd

ARQUIVO_ENTRADA = "dados/dados_brutos_carrefour.csv"
ARQUIVO_SAIDA = "dados/dados_tratados_carrefour.csv"
ARQUIVO_EXCLUIDOS = "dados/itens_excluidos_carrefour.csv"


# Termos usados para validar o início do nome do produto.
#
# Os valores estão SEM acentos porque serão comparados
# depois da normalização do texto.
FILTROS_RELEVANCIA = {
    "arroz": "arroz",
    "feijao": "feijao",
    "acucar": "acucar",
    "oleo": "oleo",
    "ovos": "ovo",
}


def corrigir_encoding(texto):
    """
    Corrige problemas de encoding como:

        JoÃ£o      -> João
        FeijÃ£o    -> Feijão
        SeleÃ§Ã£o   -> Seleção
        AÃ§Ãºcar    -> Açúcar
        Ã“leo       -> Óleo

    Caso o texto já esteja correto, mantém o valor original.
    """

    if pd.isna(texto):
        return texto

    texto = str(texto)

    # Pode acontecer mais de uma camada de encoding incorreto.
    # Tentamos corrigir enquanto houver alteração válida.
    for _ in range(2):
        try:
            corrigido = texto.encode("latin1").decode("utf-8")

            if corrigido == texto:
                break

            texto = corrigido

        except (
            UnicodeEncodeError,
            UnicodeDecodeError,
        ):
            break

    return texto


def normalizar_texto(texto):
    """
    Normaliza o texto para comparação.

    Exemplos:

        "Feijão Carioca"
            -> "feijao carioca"

        "Açúcar Refinado"
            -> "acucar refinado"

        "Óleo de Soja"
            -> "oleo de soja"
    """

    if pd.isna(texto):
        return ""

    # Primeiro corrige possíveis problemas de encoding.
    texto = corrigir_encoding(texto)

    # Converte para minúsculas.
    texto = texto.lower()

    # Remove espaços extras.
    texto = " ".join(texto.split())

    # Separa caracteres acentuados.
    texto = unicodedata.normalize(
        "NFD",
        texto,
    )

    # Remove os acentos.
    texto = "".join(
        caractere for caractere in texto if unicodedata.category(caractere) != "Mn"
    )

    return texto


def carregar_dados(
    caminho: str,
) -> pd.DataFrame:

    df = pd.read_csv(
        caminho,
        encoding="utf-8-sig",
    )

    print(f"[tratamento] Registros brutos carregados: {len(df)}")

    return df


def tratar_encoding(
    df: pd.DataFrame,
) -> pd.DataFrame:

    if "nome_produto" in df.columns:
        df["nome_produto"] = df["nome_produto"].apply(corrigir_encoding)

    return df


def tratar_valores_ausentes(
    df: pd.DataFrame,
) -> pd.DataFrame:

    antes = len(df)

    # Nome e preço são dados obrigatórios.
    df = df.dropna(
        subset=[
            "nome_produto",
            "preco",
        ]
    ).copy()

    # Caso o produto não esteja em promoção,
    # o preço original será igual ao preço atual.
    df["preco_original"] = df["preco_original"].fillna(df["preco"])

    removidos = antes - len(df)

    if removidos:
        print(
            f"[tratamento] {removidos} registro(s) removido(s) por falta de nome/preço."
        )

    return df


def tratar_duplicados(
    df: pd.DataFrame,
) -> pd.DataFrame:

    antes = len(df)

    if "codigo_produto" in df.columns:
        df = df.drop_duplicates(
            subset=["codigo_produto"],
            keep="first",
        ).copy()

        chave = "codigo_produto"

    else:
        df = df.drop_duplicates(
            subset=["url_produto"],
            keep="first",
        ).copy()

        chave = "url_produto"

    removidos = antes - len(df)

    if removidos:
        print(f"[tratamento] {removidos} duplicata(s) removida(s) (chave: {chave}).")

    return df


def normalizar_preco(
    valor,
) -> float:

    if pd.isna(valor):
        return valor

    valor = str(valor).strip()

    valor = valor.replace("R$", "").replace(" ", "")

    # Exemplo:
    # 1.234,56 -> 1234.56
    if "," in valor and "." in valor:
        valor = valor.replace(".", "").replace(",", ".")

    # Exemplo:
    # 6,39 -> 6.39
    elif "," in valor:
        valor = valor.replace(
            ",",
            ".",
        )

    return round(
        float(valor),
        2,
    )


def padronizar_precos_e_nomes(
    df: pd.DataFrame,
) -> pd.DataFrame:

    for coluna in (
        "preco",
        "preco_original",
    ):
        df[coluna] = df[coluna].apply(normalizar_preco)

    df["nome_produto"] = (
        df["nome_produto"]
        .apply(corrigir_encoding)
        .astype(str)
        .str.strip()
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )

    return df


def calcular_desconto(
    df: pd.DataFrame,
) -> pd.DataFrame:

    # Evita divisão por zero.
    df["desconto_percentual"] = 0.0

    mask = df["preco_original"].notna() & (df["preco_original"] > 0)

    df.loc[
        mask,
        "desconto_percentual",
    ] = (
        (
            1
            - (
                df.loc[mask, "preco"]
                / df.loc[
                    mask,
                    "preco_original",
                ]
            )
        )
        * 100
    ).round(2)

    return df


def filtrar_por_relevancia(
    df: pd.DataFrame,
):

    def relevante(row):

        categoria = str(row["categoria_busca"]).lower().strip()

        termo = FILTROS_RELEVANCIA.get(categoria)

        # Se a categoria não possuir filtro,
        # não exclui o produto.
        if termo is None:
            return True

        nome_normalizado = normalizar_texto(row["nome_produto"])

        # Verifica se o nome começa com o
        # termo pesquisado.
        return nome_normalizado.startswith(termo)

    mask = df.apply(
        relevante,
        axis=1,
    )

    mantidos = df[mask].copy()

    excluidos = df[~mask].copy()

    return (
        mantidos,
        excluidos,
    )


if __name__ == "__main__":
    print("=" * 55)
    print("TRATAMENTO DOS DADOS - CARREFOUR")
    print("=" * 55)

    # --------------------------------------------------
    # 1. CARREGAMENTO
    # --------------------------------------------------

    df = carregar_dados(ARQUIVO_ENTRADA)

    # --------------------------------------------------
    # 2. CORREÇÃO DE ENCODING
    # --------------------------------------------------

    df = tratar_encoding(df)

    # --------------------------------------------------
    # 3. VALORES AUSENTES
    # --------------------------------------------------

    df = tratar_valores_ausentes(df)

    # --------------------------------------------------
    # 4. DUPLICIDADES
    # --------------------------------------------------

    df = tratar_duplicados(df)

    # --------------------------------------------------
    # 5. PADRONIZAÇÃO
    # --------------------------------------------------

    df = padronizar_precos_e_nomes(df)

    # --------------------------------------------------
    # 6. CÁLCULO DO DESCONTO
    # --------------------------------------------------

    df = calcular_desconto(df)

    # --------------------------------------------------
    # 7. FILTRO DE RELEVÂNCIA
    # --------------------------------------------------

    df, excluidos = filtrar_por_relevancia(df)

    # --------------------------------------------------
    # 8. SALVAR EXCLUÍDOS
    # --------------------------------------------------

    if not excluidos.empty:
        print(f"\n[tratamento] {len(excluidos)} registro(s) excluído(s) pelo filtro.")

        print("\nProdutos excluídos:")

        print(
            excluidos[
                [
                    "nome_produto",
                    "categoria_busca",
                ]
            ].to_string(index=False)
        )

        excluidos.to_csv(
            ARQUIVO_EXCLUIDOS,
            index=False,
            encoding="utf-8-sig",
        )

    else:
        print("\n[tratamento] Nenhum produto foi excluído.")

    # --------------------------------------------------
    # 9. SALVAR DADOS TRATADOS
    # --------------------------------------------------

    df.to_csv(
        ARQUIVO_SAIDA,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------
    # 10. RESUMO
    # --------------------------------------------------

    print("\n" + "=" * 55)
    print("RESUMO DO TRATAMENTO")
    print("=" * 55)

    print(f"Registros tratados: {len(df)}")

    print(f"Arquivo: {ARQUIVO_SAIDA}")

    print("\nQuantidade por categoria:")

    print(df["categoria_busca"].value_counts())
