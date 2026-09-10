"""
Recolhe dados ao nivel de mapa (não de match completo) da página
hltv.org/stats/matches, filtrada para Top 30 e CS2.

Cada match (ex: FUT vs Legacy, bo3) aparece aqui como 2 ou 3 linhas,
uma por mapa jogado. Isto dá muito mais dados de treino do que
só o resultado final do encontro.
"""

from bs4 import BeautifulSoup
import pandas as pd
import os

from fetcher import fetch_page, gentle_pause, CookieExpiradoError

BASE_URL = "https://www.hltv.org/stats/matches?csVersion=CS2&startDate=all&rankingFilter=Top30"


def parse_pagina_stats(html: str) -> list[dict]:
    """Extrai os dados de cada linha (mapa) de uma página de stats/matches."""
    soup = BeautifulSoup(html, "html.parser")

    linhas = soup.select("tr[class^='group-']")

    mapas = []

    for linha in linhas:
        link_data = linha.find("a", href=True)
        if link_data is None:
            continue

        div_tempo = linha.find("div", class_="time")
        timestamp_unix = div_tempo.get("data-unix") if div_tempo else None

        href_partes = link_data["href"].split("/")
        mapstat_id = href_partes[4] if len(href_partes) > 4 else None

        team_cols = linha.find_all("td", class_="team-col")
        if len(team_cols) != 2:
            continue

        def extrair_equipa(td):
            link = td.find("a")
            nome = link.get_text(strip=True) if link else None
            partes = link["href"].split("/") if link else []
            team_id = partes[3] if len(partes) > 3 else None

            score_tag = td.find("span", class_="score")
            score_texto = score_tag.get_text(strip=True) if score_tag else None
            score = None
            if score_texto:
                score = int(score_texto.strip("()"))

            return nome, team_id, score

        team1_nome, team1_id, team1_score = extrair_equipa(team_cols[0])
        team2_nome, team2_id, team2_score = extrair_equipa(team_cols[1])

        if team1_score is None or team2_score is None:
            continue

        mapa_tag = linha.find("div", class_="dynamic-map-name-full")
        mapa_nome = mapa_tag.get_text(strip=True) if mapa_tag else None

        evento_td = linha.find("td", class_="event-col")
        evento_link = evento_td.find("a") if evento_td else None
        evento_nome = evento_link.get_text(strip=True) if evento_link else None
        evento_id = None
        if evento_link and "event=" in evento_link.get("href", ""):
            evento_id = evento_link["href"].split("event=")[1].split("&")[0]

        vencedor = team1_nome if team1_score > team2_score else team2_nome

        mapas.append({
            "mapstat_id": mapstat_id,
            "timestamp_unix": timestamp_unix,
            "team1_id": team1_id,
            "team1_nome": team1_nome,
            "team1_score": team1_score,
            "team2_id": team2_id,
            "team2_nome": team2_nome,
            "team2_score": team2_score,
            "vencedor": vencedor,
            "mapa": mapa_nome,
            "evento_id": evento_id,
            "evento_nome": evento_nome,
        })

    return mapas


def recolher_tudo(total_esperado: int, por_pagina: int = 50,
                   offset_inicial: int = 0,
                   ficheiro_saida: str = "../../data/mapas_raw.csv") -> None:
    """
    Percorre todas as páginas necessárias para cobrir 'total_esperado'
    resultados, guardando progressivamente no CSV (para não perder
    tudo se algo falhar a meio).
    """
    num_paginas = (total_esperado // por_pagina) + 1

    ja_existe = os.path.exists(ficheiro_saida)
    if ja_existe:
        print(f"AVISO: {ficheiro_saida} ja existe. Novos dados serao "
              f"adicionados ao fim (append).")

    total_recolhido = 0

    for i in range(num_paginas):
        offset = offset_inicial + (i * por_pagina)
        url = f"{BASE_URL}&offset={offset}"
        print(f"Pagina {i + 1}/{num_paginas} (offset={offset})...")

        try:
            html = fetch_page(url)
        except CookieExpiradoError:
            print("\n" + "=" * 60)
            print("COOKIE EXPIRADO. A recolha parou de forma limpa.")
            print(f"Dados ja guardados ate agora em: {ficheiro_saida}")
            print(f"Para retomar: renovar o cf_clearance no .env e voltar a")
            print(f"correr a partir do offset={offset} (ajustar o parametro")
            print(f"'offset_inicial' na chamada a recolher_tudo).")
            print("=" * 60)
            return

        if html is None:
            print("  Falhou, a passar a frente.")
            continue

        mapas = parse_pagina_stats(html)
        print(f"  {len(mapas)} mapas extraidos.")

        if mapas:
            df_pagina = pd.DataFrame(mapas)
            escrever_header = not os.path.exists(ficheiro_saida)
            df_pagina.to_csv(ficheiro_saida, mode="a", index=False, header=escrever_header)
            total_recolhido += len(mapas)

        if i < num_paginas - 1:
            gentle_pause()

    print(f"\nConcluido. Total de mapas guardados nesta sessao: {total_recolhido}")


if __name__ == "__main__":
    recolher_tudo(total_esperado=6822)