"""
Tenta ir buscar a página de resultados da HLTV para perceber como funciona 
um pedido HTTP e o que acontece quando o site tem proteção anti-bot.
"""

import cloudscraper

url = "https://www.hltv.org/results"

scraper = cloudscraper.create_scraper()

response = scraper.get(url, timeout=15)

print("Status code:", response.status_code)
print("Tamanho da resposta (caractéres):", len(response.text))
print("Primeiros 500 caractéres do HTML:")
print(response.text[:500])