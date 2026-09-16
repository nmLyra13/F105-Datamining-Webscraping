"""
Pre-processamento - F105 Datamining e Webscraping
Le dados_brutos.csv (saida do coleta.py) e gera dados_tratados.csv.

Por que esse script existe:
As categorias da API do mercadapp usadas para "oleo" (category_id 13799,
"Temperos") e "ovos" (category_id 13797, "Mercearia") sao categorias amplas do
catalogo do site - nao existem categorias dedicadas so a "oleo de cozinha" ou
so a "ovos" no nivel usado pela API (confirmado navegando manualmente pelo
site: 13799 mistura oleos com temperos, molhos e maionese; 13797 mistura ovos
com sopas, enlatados e mistura para bolo). Coletar por essas categorias e
correto (e' a granularidade que a API oferece), mas os dados brutos incluem
produtos que nao sao o item basico pretendido.

Este script aplica um FILTRO DE RELEVANCIA por palavra-chave no nome do
produto, especifico por item_basico, para remover esse ruido antes da analise.
Os itens de arroz/feijao/acucar tambem passam pelo filtro porque o mesmo
efeito colateral foi observado neles em menor escala (ex.: "BISCOITO ARROZ..."
aparece dentro da categoria de arroz).

Uso:
    python3 tratamento.py
"""

import re

import pandas as pd

ARQUIVO_ENTRADA = "dados_brutos.csv"
ARQUIVO_SAIDA = "dados_tratados.csv"
ARQUIVO_EXCLUIDOS = "itens_excluidos_pelo_filtro.csv"

# Um padrao por item_basico: o produto so e mantido se o NOME COMECAR com um
# dos padroes abaixo (case-insensitive). Usar "comeca com" em vez de "contem"
# e o que evita falsos positivos como "BISCOITO ARROZ..." (contem "ARROZ" mas
# nao e arroz) ou "OVOMALTINE" (contem "OVO" mas nao e ovo).
FILTROS_RELEVANCIA = {
    "arroz": re.compile(r"^\s*ARROZ\b", re.IGNORECASE),
    "feijao": re.compile(r"^\s*FEIJ[AÃ]O\b", re.IGNORECASE),
    "acucar": re.compile(r"^\s*A[CÇ][UÚ]CAR\b", re.IGNORECASE),
    # Restrito aos tipos de oleo de cozinha (soja/milho/canola/girassol/coco/
    # algodao/amendoim). Isso deixa de fora, de proposito, azeite de oliva
    # (produto distinto, mais caro, que distorceria a comparacao de precos do
    # "oleo" da cesta basica) e itens nao-alimenticios que aparecem na mesma
    # categoria (ex.: "OLEO REPAIR DOVE", "OLEO DE PEROBA" - oleo para
    # madeira/moveis).
    "oleo": re.compile(
        r"^\s*[OÓ]LEO\s+DE\s+(SOJA|MILHO|CANOLA|GIRASSOL|COCO|ALGOD[AÃ]O|AMENDOIM)\b",
        re.IGNORECASE,
    ),
    "ovos": re.compile(r"^\s*OVOS?\b", re.IGNORECASE),
}


# Mapeamento category_id -> item_basico, usado apenas como fallback caso o
# dados_brutos.csv tenha sido gerado por uma versao mais antiga do coleta.py
# que ainda nao gravava a coluna item_basico diretamente.
CATEGORY_ID_PARA_ITEM = {
    13758: "arroz",
    13759: "feijao",
    13760: "acucar",
    13799: "oleo",
    13797: "ovos",
}


def carregar_dados(caminho: str) -> pd.DataFrame:
    df = pd.read_csv(caminho, encoding="utf-8-sig")
    if "item_basico" not in df.columns:
        df["item_basico"] = df["categoria_id"].map(CATEGORY_ID_PARA_ITEM)
        print(
            "[tratamento] coluna item_basico nao encontrada no CSV; "
            "reconstruida a partir de categoria_id (versao antiga do coleta.py)."
        )
    return df


def tratar_valores_ausentes(df: pd.DataFrame) -> pd.DataFrame:
    antes = len(df)
    # nome_produto e preco sao essenciais: sem eles o registro nao serve.
    df = df.dropna(subset=["nome_produto", "preco"]).copy()
    # preco_original ausente (ou vazio) significa "sem desconto" -> repete o preco.
    df["preco_original"] = df["preco_original"].fillna(df["preco"])
    removidos = antes - len(df)
    if removidos:
        print(f"[tratamento] {removidos} registro(s) removido(s) por falta de nome/preco.")
    return df


def tratar_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    antes = len(df)
    chave = "codigo_barras" if "codigo_barras" in df.columns else "slug"
    df = df.drop_duplicates(subset=[chave], keep="first").copy()
    removidos = antes - len(df)
    if removidos:
        print(f"[tratamento] {removidos} duplicata(s) removida(s) (chave: {chave}).")
    return df


def _normalizar_preco(valor) -> float:
    """Aceita tanto numero puro (ja e o formato salvo pelo coleta.py, ex.:
    6.39) quanto uma eventual string no formato BR (ex.: "R$ 1.234,56"), caso
    o dado venha de outra fonte no futuro."""
    if pd.isna(valor):
        return valor
    s = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")  # 1.234,56 -> 1234.56
    elif "," in s:
        s = s.replace(",", ".")  # 6,39 -> 6.39
    # se so tem ponto (ou nenhum separador) o valor ja esta em formato
    # python (ex.: 6.39) e nao precisa de conversao adicional
    return round(float(s), 2)


def padronizar_precos_e_nomes(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("preco", "preco_original"):
        df[col] = df[col].apply(_normalizar_preco)
    df["nome_produto"] = (
        df["nome_produto"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    )
    return df


def filtrar_por_relevancia(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mantem so os produtos cujo nome bate com o filtro do seu item_basico."""

    def relevante(row):
        padrao = FILTROS_RELEVANCIA.get(row["item_basico"])
        if padrao is None:
            return True  # item_basico sem filtro definido: nao mexe
        return bool(padrao.search(str(row["nome_produto"])))

    mask = df.apply(relevante, axis=1)
    mantidos, excluidos = df[mask].copy(), df[~mask].copy()
    return mantidos, excluidos


if __name__ == "__main__":
    df = carregar_dados(ARQUIVO_ENTRADA)
    print(f"Registros brutos carregados: {len(df)}")

    df = tratar_valores_ausentes(df)
    df = tratar_duplicados(df)
    df = padronizar_precos_e_nomes(df)

    df, excluidos = filtrar_por_relevancia(df)
    if not excluidos.empty:
        print(
            f"[tratamento] {len(excluidos)} registro(s) excluido(s) pelo filtro de "
            f"relevancia (produto da categoria mas fora do item basico):"
        )
        print(excluidos.groupby("item_basico")["nome_produto"].apply(list).to_string())
        excluidos.to_csv(ARQUIVO_EXCLUIDOS, index=False, encoding="utf-8-sig")
        print(f"  -> lista completa salva em {ARQUIVO_EXCLUIDOS} (util para o anexo do relatorio).")

    df.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig")
    print(f"\nRegistros tratados: {len(df)} -> {ARQUIVO_SAIDA}")
    if not df.empty:
        print(df["item_basico"].value_counts())
