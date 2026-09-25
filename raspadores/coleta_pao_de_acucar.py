"""
Coleta de precos - F105 Datamining e Webscraping
Fonte: Pão de Açúcar (API interna)
Endpoint: POST https://api.vendas.gpa.digital/pa/search/search
"""

import csv
import os
import time

import requests

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
BASE_URL = "https://www.paodeacucar.com"
API_BUSCA = "https://api.vendas.gpa.digital/pa/search/search"
IMG_BASE = "https://static.paodeacucar.com"  # confirme se for diferente
TERMOS = {
    "arroz": 5,
    "feijao": 5,
    "acucar": 5,
    "oleo": 5,
    "ovos": 5,
}

STORE_ID = 461
RESULTS_PER_PAGE = 21

# ⚠️ Este hash provavelmente é gerado por JS no navegador.
# Se a API começar a retornar 400/401, você vai precisar
# capturar um novo (via DevTools ou Playwright).
USER_HASH = "f7f6def747e9cf8597a326df562b8925f3df02f69a5c6bf50a122acea805def6"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/153.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
}

# Opcional: se o DevTools mostrar headers extras (Authorization, x-api-key,
# x-tenant-id, etc.), adicione aqui.
# HEADERS["x-api-key"] = "..."


def criar_sessao():
    session = requests.Session()
    session.headers.update(HEADERS)

    # Aquece a sessão: pega cookies da home e da página de busca
    try:
        session.get(BASE_URL, timeout=30)
        session.get(f"{BASE_URL}/busca?terms=arroz", timeout=30)
    except requests.RequestException:
        pass

    return session


def montar_payload(termo, pagina=1):
    return {
        "terms": termo,
        "page": pagina,
        "sortBy": "relevance",
        "resultsPerPage": RESULTS_PER_PAGE,
        "allowRedirect": True,
        "storeId": STORE_ID,
        "department": "ecom",
        "customerPlus": True,
        "partner": "fallback",
        "userHash": USER_HASH,
    }


def buscar_pagina(session, termo, pagina=1):
    payload = montar_payload(termo, pagina)
    resposta = session.post(API_BUSCA, json=payload, timeout=30)

    if resposta.status_code != 200:
        # Mostra o corpo do erro pra ajudar a diagnosticar
        print(f"  [debug] status={resposta.status_code}")
        print(f"  [debug] body={resposta.text[:500]}")

    resposta.raise_for_status()
    return resposta.json()


def extrair_produtos_da_resposta(data, termo):
    produtos = []

    for item in data.get("products", []):
        nome = item.get("name")
        preco = item.get("price")

        if not nome or preco is None:
            continue

        preco = float(preco)

        preco_original = item.get("priceFrom")
        if preco_original is not None:
            preco_original = float(preco_original)

        desconto = None
        promo = item.get("productPromotion") or {}
        if promo.get("promotionPercentOff"):
            desconto = float(promo["promotionPercentOff"])
        elif preco_original and preco_original > preco:
            desconto = round((1 - preco / preco_original) * 100, 2)

        produtos.append(
            {
                "item_basico": termo,
                "nome_produto": nome,
                "preco": preco,
                "preco_original": preco_original,
                "desconto_percentual": desconto,
                "codigo_produto": item.get("sku") or item.get("id"),
                "categoria_busca": termo,
                "fonte": "paodeacucar",
                "url_produto": item.get("urlDetails"),
            }
        )

    return produtos


def coletar_produtos(session, termo, limite):
    print(f"\nBuscando: {termo}")

    produtos = []
    pagina = 1

    while len(produtos) < limite:
        print(f"  -> página {pagina}")

        try:
            data = buscar_pagina(session, termo, pagina)
        except requests.RequestException as erro:
            print(f"  Erro na página {pagina}: {erro}")
            break

        if pagina == 1:
            print(f"  totalProducts: {data.get('totalProducts')}")
            print(f"  totalPages:    {data.get('totalPages')}")

        novos = extrair_produtos_da_resposta(data, termo)

        if not novos:
            print("  Nenhum produto novo, parando.")
            break

        produtos.extend(novos)

        total_paginas = data.get("totalPages", 1)
        if pagina >= total_paginas:
            break

        pagina += 1
        time.sleep(1.5)

    produtos = produtos[:limite]
    print(f"Produtos válidos: {len(produtos)}")
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
    todos = []

    for termo, limite in TERMOS.items():
        try:
            todos.extend(coletar_produtos(session, termo, limite))
            time.sleep(2)
        except requests.RequestException as erro:
            print(f"Erro ao coletar '{termo}': {erro}")

    print("\n" + "=" * 50)
    print("RESUMO DA COLETA")
    print("=" * 50)
    print(f"Total de produtos: {len(todos)}")

    for termo in TERMOS:
        qtd = sum(1 for p in todos if p["categoria_busca"] == termo)
        print(f"{termo}: {qtd}")

    salvar_csv(todos)


if __name__ == "__main__":
    main()
