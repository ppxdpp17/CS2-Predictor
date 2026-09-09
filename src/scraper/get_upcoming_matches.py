"""
Recolhe os jogos futuros (e ao vivo) listados em hltv.org/matches.

Ao contrário dos scrapers anteriores, este é pensado para correr
repetidamente (o dashboard vai chamá-lo sempre que quiser atualizar),
não para uma recolha histórica unica.
"""

from bs4 import BeautifulSoup
import pandas as pd

from fetcher import fetch_page


def obter_jogos_futuros() -> pd.DataFrame:
    url = "https://www.hltv.org/matches"
    html = fetch_page(url)

    if html is None:
        print("Falha ao aceder a pagina de jogos.")
        return pd.DataFrame()

    soup = BeautifulSoup(html, "html.parser")
    blocos = soup.find_all("div", class_="match-wrapper")

    jogos = []

    for bloco in blocos:
        match_id = bloco.get("data-match-id")
        team1_id = bloco.get("team1")
        team2_id = bloco.get("team2")
        event_id = bloco.get("data-event-id")
        ao_vivo = bloco.get("live") == "true"

        teams_container = bloco.find("a", class_="match-teams") or bloco.find("div", class_="match-teams")
        team_divs = teams_container.find_all("div", class_="match-team") if teams_container else []

        team1_div = team_divs[0] if len(team_divs) > 0 else None
        team2_div = team_divs[1] if len(team_divs) > 1 else None

        nome_tag_1 = team1_div.find("div", class_="match-teamname") if team1_div else None
        nome_tag_2 = team2_div.find("div", class_="match-teamname") if team2_div else None

        team1_nome = nome_tag_1.get_text(strip=True) if nome_tag_1 else None
        team2_nome = nome_tag_2.get_text(strip=True) if nome_tag_2 else None

        time_div = bloco.find("div", class_="match-time")
        timestamp_unix = time_div.get("data-unix") if time_div else None

        meta_div = bloco.select_one("div.match-meta:not(.match-meta-live)")
        formato = meta_div.get_text(strip=True) if meta_div else None

        btn_wrapper = bloco.find("div", class_="match-btn-wrapper")
        mapas_str = btn_wrapper.get("data-maps") if btn_wrapper else None
        mapas_revelados = mapas_str.split(",") if mapas_str else []

        if not all([match_id, team1_id, team2_id, team1_nome, team2_nome]):
            continue

        jogos.append({
            "match_id": match_id,
            "team1_id": team1_id,
            "team1_nome": team1_nome,
            "team2_id": team2_id,
            "team2_nome": team2_nome,
            "timestamp_unix": timestamp_unix,
            "event_id": event_id,
            "formato": formato,
            "ao_vivo": ao_vivo,
            "mapas_revelados": mapas_revelados,
        })

    df = pd.DataFrame(jogos)
    if len(df) > 0:
        df["timestamp_unix"] = pd.to_numeric(df["timestamp_unix"], errors="coerce")
        df["data_hora"] = (
            pd.to_datetime(df["timestamp_unix"], unit="ms", errors="coerce", utc=True)
            .dt.tz_convert("Europe/Lisbon")
        )

    return df


if __name__ == "__main__":
    df = obter_jogos_futuros()
    print(f"Total de jogos encontrados: {len(df)}")
    print(df.to_string(index=False))