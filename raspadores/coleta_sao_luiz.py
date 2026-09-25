"""
Coleta de precos - F105 Datamining e Webscraping
Fonte: API interna do mercadapp usada pelo site https://mercadinhossaoluiz.com.br
       (loja/market_id 355), descoberta via DevTools > Network > Fetch/XHR.

COMO RODAR:
1) Pegue um token FRESCO no DevTools (Network > Fetch/XHR > items > Headers >
   Authorization) e exporte na hora, sem demora - o token expira rapido:

   export MERCADAPP_TOKEN="cole_aqui_o_token_novo"

2) python3 coleta.py

O script salva o CSV com o que conseguiu coletar mesmo se uma categoria falhar
no meio do caminho (ex.: 403 por excesso de requisicoes) - nao perde o que
ja foi coletado nas categorias anteriores.
"""

import csv
import os
import time

from dotenv import load_dotenv

load_dotenv()  # carrega o .env pra dentro de os.environ

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
LIMITE_POR_TERMO = 5
PAUSA_ENTRE_REQUISICOES = 1.5
MARKET_ID = 355
BASE_URL = f"https://merconnect.mercadapp.com.br/mapp/v3/markets/{MARKET_ID}/items"
# nome do item basico -> category_id (visto na URL como /subcategoria/<id>)
ITENS_BASICOS = {
    "arroz": 13758,
    "feijao": 13759,
    "acucar": 13760,
    "oleo": 13799,
    "ovos": 13797,
}

# Limite de paginas por categoria: nao precisamos de centenas de itens por
# categoria (o minimo da atividade e 30 registros no TOTAL), entao limitamos
# para nao martelar o servidor a toa - boa pratica de coleta responsavel.
MAX_PAGINAS_POR_CATEGORIA = 3
PAUSA_ENTRE_REQUISICOES = 1.5

TOKEN = os.environ.get("MERCADAPP_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "Defina a variavel de ambiente MERCADAPP_TOKEN antes de rodar "
        "(export MERCADAPP_TOKEN='...'). Nao hardcode o token no codigo."
    )

HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Origin": "https://mercadinhossaoluiz.com.br",
    "Referer": "https://mercadinhossaoluiz.com.br/",
}


def coletar_pagina(page: int, category_id: int) -> dict:
    params = {"page": page, "category_id": category_id}
    resp = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def extrair_itens(payload: dict, item_basico: str) -> list[dict]:
    registros = []
    for mix in payload.get("mixes", []):
        for item in mix.get("items", []):
            desconto_percentual = None
            if item.get("original_price"):
                calculo = (1 - (item.get("price") / item.get("original_price"))) * 100
                desconto_percentual = round(calculo, 2)

            slug = item.get("slug")
            registros.append(
                {
                    "item_basico": item_basico,
                    "nome_produto": item.get("description").strip(),
                    "preco": item.get("price"),
                    "preco_original": item.get("original_price"),
                    "desconto_percentual": desconto_percentual,
                    "codigo_produto": item.get("bar_code") or item.get("id"),
                    "categoria_busca": item_basico,
                    "fonte": "saoluiz",
                    "url_produto": (
                        f"https://mercadinhossaoluiz.com.br/produto/{slug}"
                        if slug
                        else None
                    ),
                }
            )
    return registros


def coletar_categoria(item_basico: str, category_id: int) -> list[dict]:
    todos: list[dict] = []
    page = 1
    while len(todos) < LIMITE_POR_TERMO:
        payload = coletar_pagina(page, category_id)
        itens = extrair_itens(payload, item_basico)
        if not itens:
            break
        todos.extend(itens)
        print(
            f"  {item_basico} (cat {category_id}) / página {page}: +{len(itens)} itens (total {len(todos)})"
        )
        if not payload.get("has_next_page"):
            break
        page += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES)
    return todos[:LIMITE_POR_TERMO]


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


if __name__ == "__main__":
    registros: list[dict] = []

    for nome, cat_id in ITENS_BASICOS.items():
        print(f"Coletando {nome} (categoria {cat_id})...")
        try:
            registros.extend(coletar_categoria(nome, cat_id))
        except requests.exceptions.HTTPError as e:
            print(
                f"  [ERRO] Falhou em '{nome}': {e}. Seguindo com o que já foi coletado."
            )
        time.sleep(PAUSA_ENTRE_REQUISICOES)

    salvar_csv(registros)
