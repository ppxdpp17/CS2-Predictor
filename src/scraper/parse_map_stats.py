"""
Recolhe dados ao nivel de MAPA (nao de match completo) da pagina
hltv.org/stats/matches, filtrada para Top 30 e CS2.

Cada "match" (ex: FUT vs Legacy, bo3) aparece aqui como 2 ou 3 linhas,
uma por mapa jogado. Isto da-nos muito mais dados de treino do que
so o resultado final do encontro.
"""

from bs4 import BeautifulSoup
import pandas as pd
import os

from fetcher import fetch_page, gentle_pause, CookieExpiradoError

BASE_URL = "https://www.hltv.org/stats/matches?csVersion=CS2&startDate=all&rankingFilter=Top30"


def parse_pagina_stats(html: str) -> list[dict]:
    """Extrai os dados de cada linha (mapa) de uma pagina de stats/matches."""
    soup = BeautifulSoup(html, "html.parser")

    # Nesta pagina, cada linha de mapa e um <tr> com classe que comeca
    # por "group-". Usamos um "seletor CSS" para apanhar as duas
    # variantes (com e sem "first") de uma vez.
    linhas = soup.select("tr[class^='group-']")

    mapas = []

    for linha in linhas:
        # --- Data e ID do mapa ---
        link_data = linha.find("a", href=True)
        if link_data is None:
            continue

        div_tempo = linha.find("div", class_="time")
        timestamp_unix = div_tempo.get("data-unix") if div_tempo else None

        # O href tem o formato /stats/matches/mapstatsid/236101/fut-vs-legacy
        href_partes = link_data["href"].split("/")
        mapstat_id = href_partes[4] if len(href_partes) > 4 else None

        # --- Equipas (ha exatamente 2 <td class="team-col">) ---
        team_cols = linha.find_all("td", class_="team-col")
        if len(team_cols) != 2:
            # Estrutura inesperada, salta esta linha em vez de rebentar
            continue

        def extrair_equipa(td):
            link = td.find("a")
            nome = link.get_text(strip=True) if link else None
            # O ID da equipa esta no href: /stats/teams/13286/fut
            partes = link["href"].split("/") if link else []
            team_id = partes[3] if len(partes) > 3 else None

            score_tag = td.find("span", class_="score")
            # O texto vem como " (11)" -> precisamos limpar parenteses e espacos
            score_texto = score_tag.get_text(strip=True) if score_tag else None
            score = None
            if score_texto:
                score = int(score_texto.strip("()"))

            return nome, team_id, score

        team1_nome, team1_id, team1_score = extrair_equipa(team_cols[0])
        team2_nome, team2_id, team2_score = extrair_equipa(team_cols[1])

        if team1_score is None or team2_score is None:
            continue

        # --- Mapa jogado ---
        mapa_tag = linha.find("div", class_="dynamic-map-name-full")
        mapa_nome = mapa_tag.get_text(strip=True) if mapa_tag else None

        # --- Evento ---
        evento_td = linha.find("td", class_="event-col")
        evento_link = evento_td.find("a") if evento_td else None
        evento_nome = evento_link.get_text(strip=True) if evento_link else None
        evento_id = None
        if evento_link and "event=" in evento_link.get("href", ""):
            # extrai o numero depois de "event="
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
    Percorre TODAS as paginas necessarias para cobrir 'total_esperado'
    resultados, guardando progressivamente no CSV (para nao perder
    tudo se algo falhar a meio).
    """
    num_paginas = (total_esperado // por_pagina) + 1

    # Se ja existe um ficheiro de uma recolha anterior interrompida,
    # avisamos e nao o apagamos sem querer.
    ja_existe = os.path.exists(ficheiro_saida)
    if ja_existe:
        print(f"AVISO: {ficheiro_saida} ja existe. Novos dados serao "
              f"adicionados ao fim (append). Apaga o ficheiro manualmente "
              f"se quiseres comecar do zero.")

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
            print(f"Para retomar: renova o cf_clearance no .env e volta a")
            print(f"correr a partir do offset={offset} (ajusta o parametro")
            print(f"'offset_inicial' na chamada a recolher_tudo).")
            print("=" * 60)
            return

        if html is None:
            print("  Falhou, a passar a frente (fica registado para retomar depois).")
            continue

        mapas = parse_pagina_stats(html)
        print(f"  {len(mapas)} mapas extraidos.")

        if mapas:
            df_pagina = pd.DataFrame(mapas)
            # 'mode a' = append (adicionar ao fim do ficheiro em vez de sobrescrever)
            # so escrevemos o cabecalho (header) se o ficheiro ainda nao existir
            escrever_header = not os.path.exists(ficheiro_saida)
            df_pagina.to_csv(ficheiro_saida, mode="a", index=False, header=escrever_header)
            total_recolhido += len(mapas)

        if i < num_paginas - 1:
            gentle_pause()

    print(f"\nConcluido. Total de mapas guardados nesta sessao: {total_recolhido}")


if __name__ == "__main__":
    # 6822 e o total que vimos na pagina (1 - 50 of 6822).
    # Se quiseres testar primeiro com pouco, muda para um numero pequeno,
    # tipo 150 (3 paginas), antes de correr o total.
    recolher_tudo(total_esperado=6822)