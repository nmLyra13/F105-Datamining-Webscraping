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

import os
import time

import pandas as pd
from dotenv import load_dotenv

load_dotenv()  # carrega o .env pra dentro de os.environ

import requests

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
            registros.append(
                {
                    "item_basico": item_basico,
                    "nome_produto": item.get("description"),
                    "preco": item.get("price"),
                    "preco_original": item.get("original_price"),
                    "em_oferta": item.get("is_offer"),
                    "loja_market_id": item.get("market_id"),
                    "categoria_id": item.get("category_id"),
                    "codigo_barras": item.get("bar_code"),
                    "estoque": item.get("stock"),
                    "slug": item.get("slug"),
                    "url_produto": f"https://mercadinhossaoluiz.com.br/produto/{item.get('slug')}",
                }
            )
    return registros


def coletar_categoria(item_basico: str, category_id: int) -> list[dict]:
    todos: list[dict] = []
    page = 1
    while page <= MAX_PAGINAS_POR_CATEGORIA:
        payload = coletar_pagina(page, category_id)
        itens = extrair_itens(payload, item_basico)
        if not itens:
            break
        todos.extend(itens)
        print(
            f"  {item_basico} (cat {category_id}) / pagina {page}: +{len(itens)} itens (total {len(todos)})"
        )
        if not payload.get("has_next_page"):
            break
        page += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES)
    return todos


if __name__ == "__main__":
    registros: list[dict] = []

    for nome, cat_id in ITENS_BASICOS.items():
        print(f"Coletando {nome} (categoria {cat_id})...")
        try:
            registros.extend(coletar_categoria(nome, cat_id))
        except requests.exceptions.HTTPError as e:
            print(
                f"  [ERRO] Falhou em '{nome}': {e}. Seguindo com o que ja foi coletado."
            )
        time.sleep(PAUSA_ENTRE_REQUISICOES)

    df = pd.DataFrame(registros)
    df.to_csv("dados/dados_brutos.csv", index=False, encoding="utf-8-sig")
    print(f"\nColetados {len(df)} registros -> dados/dados_brutos.csv")
    if not df.empty:
        print(df["item_basico"].value_counts())
