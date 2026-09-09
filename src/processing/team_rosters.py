"""
Obtém o roster ATUAL de cada equipa, diretamente da página da equipa
na HLTV (não do histórico de jogos, que fica desatualizado quando
uma equipa troca de jogadores).

Usa uma cache local em JSON para não repetir pedidos desnecessários -
um roster só é considerado "desatualizado" ao fim de alguns dias.
"""

import os
import json
from datetime import datetime, timedelta

import pandas as pd
from bs4 import BeautifulSoup

from fetcher import fetch_page

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CAMINHO_CACHE = os.path.join(_BASE_DIR, "..", "..", "data", "rosters_cache.json")
_CAMINHO_MATCHES = os.path.join(_BASE_DIR, "..", "..", "data", "matches_clean.csv")
_CAMINHO_JOGADORES = os.path.join(_BASE_DIR, "..", "..", "data", "jogadores_por_match.csv")

DIAS_VALIDADE_CACHE = 3


def _carregar_cache() -> dict:
    if os.path.exists(_CAMINHO_CACHE):
        with open(_CAMINHO_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _guardar_cache(cache: dict) -> None:
    with open(_CAMINHO_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _buscar_roster_na_hltv(team_id) -> list:
    """Vai buscar o roster atual diretamente a pagina da equipa."""
    url = f"https://www.hltv.org/team/{int(team_id)}/x"
    html = fetch_page(url)
    if html is None:
        return []

    soup = BeautifulSoup(html, "html.parser")
    bloco_roster = soup.find("div", class_="bodyshot-team")
    if bloco_roster is None:
        return []

    jogadores = []
    for link in bloco_roster.find_all("a", class_="col-custom"):
        nome_tag = link.find("span", class_="text-ellipsis bold")
        if nome_tag:
            jogadores.append(nome_tag.get_text(strip=True))

    return jogadores


_CAMINHO_CACHE_LINEUPS_MATCH = os.path.join(_BASE_DIR, "..", "..", "data", "lineups_match_cache.json")
MINUTOS_VALIDADE_CACHE_MATCH = 60


def obter_lineup_confirmado_do_jogo(match_id) -> dict:
    """
    Vai buscar o lineup confirmado especificamente para este encontro,
    diretamente à página do jogo. Isto inclui stand-ins que não aparecem na 
    página geral da equipa.

    Devolve {"1": [jogadores...], "2": [jogadores...]} - "1" e "2"
    correspondem a team1/team2, tal como na página da lista de jogos.
    Devolve {} se a página não tiver esta seção ainda (jogo muito
    distante no tempo, lineup por confirmar).

    Usa cache de 1 hora por match_id, para não bombardear a HLTV com
    um pedido por jogo de cada vez que o dashboard atualiza.
    """
    match_id_str = str(int(match_id))
    cache = {}
    if os.path.exists(_CAMINHO_CACHE_LINEUPS_MATCH):
        with open(_CAMINHO_CACHE_LINEUPS_MATCH, "r", encoding="utf-8") as f:
            cache = json.load(f)

    entrada = cache.get(match_id_str)
    if entrada is not None:
        atualizado_em = datetime.fromisoformat(entrada["atualizado_em"])
        if datetime.now() - atualizado_em < timedelta(minutes=MINUTOS_VALIDADE_CACHE_MATCH):
            return entrada["lineups"]

    url = f"https://www.hltv.org/matches/{int(match_id)}/x"
    html = fetch_page(url)
    if html is None:
        return entrada["lineups"] if entrada else {}

    soup = BeautifulSoup(html, "html.parser")
    blocos_players = soup.find_all("div", class_="players")

    resultado = {}
    for bloco in blocos_players:
        nomes_ordinal = {}
        for div_jogador in bloco.select("div.player-compare.flagAlign"):
            ordinal = div_jogador.get("data-team-ordinal")
            nome_tag = div_jogador.find("div", class_="text-ellipsis")
            if ordinal and nome_tag:
                nomes_ordinal.setdefault(ordinal, []).append(nome_tag.get_text(strip=True))

        for ordinal, nomes in nomes_ordinal.items():
            resultado[ordinal] = nomes

    cache[match_id_str] = {
        "lineups": resultado,
        "atualizado_em": datetime.now().isoformat(),
    }
    with open(_CAMINHO_CACHE_LINEUPS_MATCH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    return resultado


def obter_lineup_atual(team_id) -> list:
    """
    Devolve o roster atual de uma equipa, utilizando cache local 
    para não pedir a mesma equipa repetidamente em pouco tempo.
    """
    team_id_str = str(int(team_id))
    cache = _carregar_cache()

    entrada = cache.get(team_id_str)
    if entrada is not None:
        atualizado_em = datetime.fromisoformat(entrada["atualizado_em"])
        if datetime.now() - atualizado_em < timedelta(days=DIAS_VALIDADE_CACHE):
            return entrada["jogadores"]

    jogadores = _buscar_roster_na_hltv(team_id)

    if jogadores:
        cache[team_id_str] = {
            "jogadores": jogadores,
            "atualizado_em": datetime.now().isoformat(),
        }
        _guardar_cache(cache)
        return jogadores

    if entrada is not None:
        return entrada["jogadores"]

    return []


def obter_lineups_para_equipas(team_ids) -> dict:
    """Devolve {team_id: [jogadores]} só para as equipas pedidas (evita ir buscar
    o roster de todas as +80 equipas do histórico quando só precisamos de umas poucas -
    as que têm jogos agora)."""
    return {tid: obter_lineup_atual(tid) for tid in team_ids}


def obter_ultimo_lineup_por_equipa() -> dict:
    if not os.path.exists(_CAMINHO_JOGADORES) or not os.path.exists(_CAMINHO_MATCHES):
        return {}

    df_matches = pd.read_csv(_CAMINHO_MATCHES)
    df_matches["data"] = pd.to_datetime(df_matches["data"])
    df_matches = df_matches.sort_values("data")

    df_jogadores = pd.read_csv(_CAMINHO_JOGADORES)
    grupos = df_jogadores.groupby(["match_id", "team_label"])

    ultimo_lineup = {}
    for _, match in df_matches.iterrows():
        for label, team_id in [("a", match["team_a_id"]), ("b", match["team_b_id"])]:
            try:
                lineup = grupos.get_group((match["match_id"], label))
                ultimo_lineup[team_id] = list(lineup["player_nome"])
            except KeyError:
                continue

    return ultimo_lineup