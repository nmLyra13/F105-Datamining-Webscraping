import time

from dotenv import set_key
from playwright.sync_api import sync_playwright

SITE_URL = "https://mercadinhossaoluiz.com.br"
ENV_FILE = ".env"

token = None


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    def capturar_token(request):
        global token

        if token is not None:
            return

        # Só nos interessa o tráfego da API do Mercadapp
        if "merconnect.mercadapp.com.br" not in request.url:
            return

        try:
            authorization = request.header_value("authorization")
        except Exception:
            # A requisição pode ter sido encerrada antes de conseguirmos
            # acessar seus headers.
            return

        if not authorization:
            return

        if not authorization.startswith("Bearer "):
            return

        valor = authorization.removeprefix("Bearer ").strip()

        if not valor or valor == "null":
            return

        token = valor
        print(f"Token encontrado: {token[:20]}...")

    page.on("request", capturar_token)

    page.goto(
        SITE_URL,
        wait_until="domcontentloaded",
        timeout=30000,
    )

    inicio = time.monotonic()

    while token is None and time.monotonic() - inicio < 10:
        page.wait_for_timeout(100)

    if token is None:
        print("Não foi possível encontrar um token válido.")
    else:
        set_key(ENV_FILE, "MERCADAPP_TOKEN", token)
        print(f"Token salvo em {ENV_FILE}.")

    # Só fechamos depois que terminamos de capturar o token.
    browser.close()
