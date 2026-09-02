"""
Teste: confirmar se as paginas /results e /matches ainda sao acessiveis
com cloudscraper simples (sem cookie manual), o que e essencial para
conseguirmos automatizar o dashboard sem intervencao humana constante.
"""

import cloudscraper

scraper = cloudscraper.create_scraper()

for nome, url in [
    ("results", "https://www.hltv.org/results"),
    ("matches", "https://www.hltv.org/matches"),
]:
    response = scraper.get(url, timeout=15)
    bloqueado = "Um momento" in response.text[:1000] or "Just a moment" in response.text[:1000]
    print(f"{nome}: status={response.status_code}, bloqueado={bloqueado}, tamanho={len(response.text)}")