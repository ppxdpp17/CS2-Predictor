"""
Teste: usar um browser real (via Playwright) com técnicas de stealth
para tentar aceder à página de stats/matches, que bloqueou o cloudscraper
e o Playwright simples.
"""

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

url = "https://www.hltv.org/stats/matches?csVersion=CS2&startDate=all&rankingFilter=Top30"

stealth = Stealth()

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1366, "height": 768},
        locale="pt-PT",
    )
    page = context.new_page()

    stealth.apply_stealth_sync(page)

    print("A navegar para a pagina...")
    page.goto(url, timeout=30000)

    for segundos in range(30):
        titulo_atual = page.title()
        if "moment" not in titulo_atual.lower() and "momento" not in titulo_atual.lower():
            print(f"Desafio ultrapassado depois de ~{segundos}s!")
            break
        page.wait_for_timeout(1000)

    titulo = page.title()
    print(f"Titulo da pagina: {titulo}")

    conteudo = page.content()
    print(f"Tamanho do HTML: {len(conteudo)} caracteres")
    print("Primeiros 300 caracteres:")
    print(conteudo[:300])

    input("Prime ENTER aqui no terminal para fechar o browser...")
    browser.close()