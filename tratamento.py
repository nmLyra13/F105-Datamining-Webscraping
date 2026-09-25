"""
Pré-processamento - F105 Datamining e Webscraping

Lê:
    dados/dados_brutos.csv       (gerado pelos 3 raspadores)

Gera:
    dados/dados_tratados.csv
    dados/itens_excluidos.csv

Tratamentos:
- correção de encoding (idempotente, seguro para UTF-8 já correto);
- padronização da coluna `fonte` (carrefour, paodeacucar, saoluiz);
- remoção de registros sem nome ou preço;
- preenchimento de `preco_original` quando não há promoção;
- remoção de duplicidades dentro de cada fonte;
- padronização de preços, nomes e código;
- recálculo do desconto percentual;
- filtro de relevância por item básico (nome precisa começar com o termo).
"""

import re
import unicodedata

import pandas as pd

ARQUIVO_ENTRADA = "dados/dados_brutos.csv"
ARQUIVO_SAIDA = "dados/dados_tratados.csv"
ARQUIVO_EXCLUIDOS = "dados/itens_excluidos.csv"


# Padroniza o campo `fonte` para um identificador curto e sem espaços.
# Qualquer coisa que não estiver mapeada é mantida em minúsculas.
MAPA_FONTE = {
    "carrefour": "carrefour",
    "paodeacucar": "paodeacucar",
    "Mercadinho São Luiz": "saoluiz",
    "mercadinho sao luiz": "saoluiz",
    "mercado sao luiz": "saoluiz",
}


# Regex por item básico. O produto é mantido se o nome (já normalizado
# sem acento, em maiúsculas) começar com o padrão.
#
# Notas:
# - `ovos` aceita "OVO" e "OVOS" (singular/plural).
# - `oleo` aceita "OLEO" ou "ÓLEO" com ou sem acento, e exige que seja
#   "DE <tipo>" para não capturar "Óleo de Peroba" caso apareça.
FILTROS_RELEVANCIA = {
    "arroz": re.compile(r"^ARROZ\b"),
    "feijao": re.compile(r"^FEIJAO\b"),
    "acucar": re.compile(r"^ACUCAR\b"),
    "oleo": re.compile(
        r"^OLEO\s+DE\s+(SOJA|MILHO|CANOLA|GIRASSOL|COCO|ALGODAO|AMENDOIM)\b"
    ),
    "ovos": re.compile(r"^OVOS?\b"),
}


def corrigir_encoding(texto):
    """
    Corrige strings que foram decodificadas como latin1 mas são UTF-8.

    É seguro rodar em texto que já está correto: se `encode("latin1")`
    falhar (porque o texto tem caracteres fora do latin1, como "ã" já
    correto), retorna o original.
    """
    if pd.isna(texto):
        return texto

    texto = str(texto)

    for _ in range(2):
        try:
            corrigido = texto.encode("latin1").decode("utf-8")
            if corrigido == texto:
                break
            texto = corrigido
        except (UnicodeEncodeError, UnicodeDecodeError):
            break

    return texto


def normalizar_texto(texto):
    """
    Deixa o texto em maiúsculas sem acento, para comparação com os regex
    de relevância. Também colapsa espaços múltiplos.
    """
    if pd.isna(texto):
        return ""

    texto = corrigir_encoding(texto)
    texto = str(texto).upper()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def carregar_dados(caminho):
    df = pd.read_csv(caminho, encoding="utf-8-sig", dtype=str)
    print(f"[tratamento] Registros brutos carregados: {len(df)}")
    return df


def padronizar_fonte(df):
    df["fonte"] = (
        df["fonte"].fillna("").astype(str).str.strip().replace(MAPA_FONTE).str.lower()
    )
    # Qualquer valor não mapeado vira o próprio texto em minúsculas sem espaços
    df["fonte"] = df["fonte"].str.replace(r"\s+", "", regex=True)
    return df


def tratar_encoding(df):
    if "nome_produto" in df.columns:
        df["nome_produto"] = df["nome_produto"].apply(corrigir_encoding)
    return df


def tratar_valores_ausentes(df):
    antes = len(df)

    # Converte preço para numérico antes de checar NaN
    for col in ("preco", "preco_original"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["nome_produto", "preco"]).copy()

    # Sem promoção -> preço original é o próprio preço
    df["preco_original"] = df["preco_original"].fillna(df["preco"])

    removidos = antes - len(df)
    if removidos:
        print(
            f"[tratamento] {removidos} registro(s) removido(s) por falta de nome/preço."
        )
    return df


def tratar_duplicados(df):
    """
    Remove duplicatas DENTRO de cada fonte, pela chave mais confiável
    disponível (codigo_produto). Isso evita derrubar produtos que por
    acaso tenham o mesmo código em fontes diferentes (não deveria
    acontecer, mas é mais seguro).
    """
    antes = len(df)

    if "codigo_produto" not in df.columns:
        df = df.drop_duplicates(subset=["url_produto"], keep="first").copy()
        chave = "url_produto"
    else:
        df["codigo_produto"] = df["codigo_produto"].astype(str).str.strip()
        df = df.drop_duplicates(subset=["fonte", "codigo_produto"], keep="first").copy()
        chave = "fonte+codigo_produto"

    removidos = antes - len(df)
    if removidos:
        print(f"[tratamento] {removidos} duplicata(s) removida(s) (chave: {chave}).")
    return df


def normalizar_preco(valor):
    if pd.isna(valor):
        return valor
    if isinstance(valor, (int, float)):
        return round(float(valor), 2)

    s = str(valor).strip().replace("R$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")

    try:
        return round(float(s), 2)
    except ValueError:
        return None


def padronizar_precos_e_nomes(df):
    for col in ("preco", "preco_original"):
        df[col] = df[col].apply(normalizar_preco)

    df["nome_produto"] = (
        df["nome_produto"]
        .apply(corrigir_encoding)
        .astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    df["codigo_produto"] = df["codigo_produto"].astype(str).str.strip()

    return df


def calcular_desconto(df):
    df["desconto_percentual"] = 0.0
    mask = df["preco_original"].notna() & (df["preco_original"] > 0)

    df.loc[mask, "desconto_percentual"] = (
        (1 - (df.loc[mask, "preco"] / df.loc[mask, "preco_original"])) * 100
    ).round(2)

    # Se o preço atual é maior ou igual ao original, não há desconto real
    df.loc[df["desconto_percentual"] < 0, "desconto_percentual"] = 0.0

    return df


def filtrar_por_relevancia(df):
    def relevante(row):
        item = str(row["item_basico"]).lower().strip()
        padrao = FILTROS_RELEVANCIA.get(item)
        if padrao is None:
            return True

        nome_norm = normalizar_texto(row["nome_produto"])
        return bool(padrao.search(nome_norm))

    mask = df.apply(relevante, axis=1)
    return df[mask].copy(), df[~mask].copy()


if __name__ == "__main__":
    print("=" * 55)
    print("TRATAMENTO DOS DADOS - TODAS AS FONTES")
    print("=" * 55)

    df = carregar_dados(ARQUIVO_ENTRADA)

    df = padronizar_fonte(df)
    df = tratar_encoding(df)
    df = tratar_valores_ausentes(df)
    df = tratar_duplicados(df)
    df = padronizar_precos_e_nomes(df)
    df = calcular_desconto(df)

    df, excluidos = filtrar_por_relevancia(df)

    if not excluidos.empty:
        print(f"\n[tratamento] {len(excluidos)} registro(s) excluído(s) pelo filtro.")
        print("\nProdutos excluídos (agrupados por item_basico):")
        print(excluidos.groupby("item_basico")["nome_produto"].apply(list).to_string())
        excluidos.to_csv(ARQUIVO_EXCLUIDOS, index=False, encoding="utf-8-sig")
    else:
        print("\n[tratamento] Nenhum produto foi excluído.")

    df.to_csv(ARQUIVO_SAIDA, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 55)
    print("RESUMO DO TRATAMENTO")
    print("=" * 55)
    print(f"Registros tratados: {len(df)} -> {ARQUIVO_SAIDA}")
    print("\nQuantidade por fonte:")
    print(df["fonte"].value_counts())
    print("\nQuantidade por item_basico:")
    print(df["item_basico"].value_counts())
    print("\nCruzamento fonte x item_basico:")
    print(pd.crosstab(df["fonte"], df["item_basico"]))
