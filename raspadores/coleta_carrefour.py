import csv
import os
import re
import time
import unicodedata
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

ARQUIVO_SAIDA = "dados/dados_brutos.csv"
CAMPOS = [
    "item_basico",
    "nome_produto",
    "preco",
    "preco_original",
    "desconto_percentual",
    "codigo_produto",
    "categoria_busca",
    "fonte",
    "url_produto",
]

BASE_URL = "https://mercado.carrefour.com.br"

URL_BUSCA = f"{BASE_URL}/busca"

TERMOS = {
    "arroz": 5,
    "feijao": 5,
    "acucar": 5,
    "oleo": 5,
    "ovos": 5,
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def criar_sessao():
    """
    Cria uma sessão HTTP para reutilizar conexão
    durante a coleta.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    return session


def converter_preco(valor):
    """
    Converte:

        R$ 24,99
        R$ 1.234,56

    para:

        24.99
        1234.56
    """

    if not valor:
        return None

    valor = valor.replace("R$", "").strip()
    valor = valor.replace(".", "").replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return None


def extrair_percentual(texto):
    """
    Extrai o percentual de desconto.

    Exemplo:

        '-20%' -> 20.0
    """

    if not texto:
        return None

    resultado = re.search(r"(\d+(?:,\d+)?)%", texto)

    if not resultado:
        return None

    return float(resultado.group(1).replace(",", "."))


def corrigir_encoding(texto):
    try:
        return texto.encode("latin1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def normalizar_texto(texto):
    texto = corrigir_encoding(texto)

    texto = texto.lower()

    texto = unicodedata.normalize("NFD", texto)

    texto = "".join(
        caractere for caractere in texto if unicodedata.category(caractere) != "Mn"
    )

    return texto


def produto_relevante(nome, termo):
    """
    Evita resultados claramente fora da categoria pesquisada.

    Exemplo:

        busca = arroz
        'Panela de Arroz Elétrica...' -> False

    enquanto:

        'Arroz Branco Camil Tipo 1 1kg' -> True
    """

    nome_normalizado = normalizar_texto(nome)
    termo_normalizado = normalizar_texto(termo)

    if termo_normalizado not in nome_normalizado:
        return False

    palavras_excluir = {
        "panela",
        "elétrica",
        "eletrica",
        "eletrodoméstico",
        "eletrodomestico",
    }

    return not any(palavra in nome_normalizado for palavra in palavras_excluir)


def extrair_produto(card, termo):
    """
    Extrai os dados de um único card de produto.
    """

    nome_elemento = card.select_one("h2")

    if not nome_elemento:
        return None

    nome = nome_elemento.get_text(" ", strip=True)

    if not produto_relevante(nome, termo):
        return None

    # Preço atual
    preco_elemento = card.select_one("span.text-price-default")

    if not preco_elemento:
        return None

    preco = converter_preco(preco_elemento.get_text(" ", strip=True))

    # Preço original
    preco_original_elemento = card.select_one("span.line-through")

    preco_original = None

    if preco_original_elemento:
        preco_original = converter_preco(
            preco_original_elemento.get_text(" ", strip=True)
        )

    desconto = None

    if preco_original and preco:
        calculo = (1 - (preco / preco_original)) * 100
        desconto = round(calculo, 2)

    # URL
    href = card.get("href")

    url_produto = None

    if href:
        url_produto = urljoin(BASE_URL, href)

    # Código presente no final da URL
    codigo_produto = None

    if href:
        partes = href.rstrip("/").split("-")
        codigo_produto = partes[-1]

    return {
        "item_basico": termo,
        "nome_produto": nome,
        "preco": preco,
        "preco_original": preco_original or preco,
        "desconto_percentual": desconto,
        "codigo_produto": codigo_produto,
        "categoria_busca": termo,
        "fonte": "carrefour",
        "url_produto": url_produto,
    }


def coletar_produtos(session, termo, limite):
    """
    Realiza a busca e extrai os produtos encontrados.
    """

    url = f"{URL_BUSCA}?term={quote(termo)}&isPharmacy=false"

    print(f"\nBuscando: {termo}")
    print(f"URL: {url}")

    resposta = session.get(url, timeout=30)

    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")

    cards = soup.select('a[data-testid="search-product-card"]')

    produtos = []

    for card in cards:
        if len(produtos) >= limite:
            break

        produto = extrair_produto(card, termo)

        if produto:
            produtos.append(produto)

    return produtos


def salvar_csv(produtos):
    """Acrescenta linhas ao CSV único, criando header só na primeira vez."""
    if not produtos:
        print("Nenhum produto para salvar.")
        return

    os.makedirs(os.path.dirname(ARQUIVO_SAIDA), exist_ok=True)
    arquivo_existe = os.path.exists(ARQUIVO_SAIDA)

    with open(ARQUIVO_SAIDA, "a", newline="", encoding="utf-8-sig") as arquivo:
        writer = csv.DictWriter(arquivo, fieldnames=CAMPOS, extrasaction="ignore")
        if not arquivo_existe:
            writer.writeheader()
        for produto in produtos:
            writer.writerow({campo: produto.get(campo) for campo in CAMPOS})

    print(f"{len(produtos)} linhas acrescentadas em: {ARQUIVO_SAIDA}")


def main():

    session = criar_sessao()

    todos_produtos = []

    for termo, limite in TERMOS.items():
        try:
            produtos = coletar_produtos(
                session,
                termo,
                limite,
            )

            todos_produtos.extend(produtos)

            # Pequena pausa entre as buscas
            time.sleep(2)

        except requests.RequestException as erro:
            print(f"Erro ao coletar '{termo}': {erro}")

    print("\n" + "=" * 50)
    print("RESUMO DA COLETA")
    print("=" * 50)

    print(f"Total de produtos: {len(todos_produtos)}")

    for termo in TERMOS:
        quantidade = sum(
            1 for produto in todos_produtos if produto["categoria_busca"] == termo
        )

        print(f"{termo}: {quantidade}")

    salvar_csv(todos_produtos)


if __name__ == "__main__":
    main()
