"""
Percorre varias paginas de resultados da HLTV, extrai os dados de
cada jogo, e guarda tudo num ficheiro CSV.
"""

from bs4 import BeautifulSoup
import pandas as pd

from fetcher import fetch_page, gentle_pause


def parse_pagina(html: str) -> list[dict]:
    """Recebe o HTML de uma pagina de resultados e devolve uma lista
    de dicionarios, um por partida encontrada."""
    soup = BeautifulSoup(html, "html.parser")
    result_blocks = soup.find_all("div", class_="result")

    partidas = []

    for bloco in result_blocks:
        link_tag = bloco.parent
        href = link_tag.get("href", "")
        match_id = href.split("/")[2] if len(href.split("/")) > 2 else None

        team_divs = bloco.find_all("div", class_="team")
        if len(team_divs) < 2:
            continue

        team1_nome = team_divs[0].get_text(strip=True)
        team2_nome = team_divs[1].get_text(strip=True)

        score_lost = bloco.find("span", class_="score-lost")
        score_won = bloco.find("span", class_="score-won")
        if score_lost is None or score_won is None:
            continue

        team1_venceu = "team-won" in team_divs[0].get("class", [])

        evento_tag = bloco.find("span", class_="event-name")
        evento_nome = evento_tag.get_text(strip=True) if evento_tag else None

        formato_tag = bloco.find("div", class_="map-text")
        formato = formato_tag.get_text(strip=True) if formato_tag else None

        partidas.append({
            "match_id": match_id,
            "team1": team1_nome,
            "team2": team2_nome,
            "score_team1": int(score_won.get_text()) if team1_venceu else int(score_lost.get_text()),
            "score_team2": int(score_lost.get_text()) if team1_venceu else int(score_won.get_text()),
            "vencedor": team1_nome if team1_venceu else team2_nome,
            "evento": evento_nome,
            "formato": formato,
        })

    return partidas


def recolher_varias_paginas(num_paginas: int, offset_inicial: int = 0) -> pd.DataFrame:
    """
    Percorre 'num_paginas' paginas de resultados, comecando em
    'offset_inicial', e devolve tudo junto num DataFrame do pandas.

    A HLTV mostra 100 resultados por pagina, por isso o offset
    avanca de 100 em 100.
    """
    todas_as_partidas = []

    for i in range(num_paginas):
        offset = offset_inicial + (i * 100)
        url = f"https://www.hltv.org/results?offset={offset}"
        print(f"Pagina {i + 1}/{num_paginas} (offset={offset})...")

        html = fetch_page(url)

        if html is None:
            print("  Sem dados desta pagina, a continuar para a seguinte.")
            continue

        partidas = parse_pagina(html)
        print(f"  {len(partidas)} partidas extraidas.")
        todas_as_partidas.extend(partidas)

        if i < num_paginas - 1:
            gentle_pause()

    return pd.DataFrame(todas_as_partidas)


if __name__ == "__main__":
    # Por agora, um teste pequeno: 3 paginas (~300 jogos).
    # Quando estivermos confiantes que funciona bem, aumentamos.
    df = recolher_varias_paginas(num_paginas=3)

    print(f"\nTotal de partidas recolhidas: {len(df)}")
    print(df.head())

    # Guardar em CSV dentro da pasta data/
    caminho_saida = "../../data/resultados_raw.csv"
    df.to_csv(caminho_saida, index=False)
    print(f"\nGuardado em: {caminho_saida}")