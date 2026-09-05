"""
Obtem o roster ATUAL de cada equipa, diretamente da pagina da equipa
na HLTV (nao do historico de jogos, que fica desatualizado quando
uma equipa troca de jogadores).

Usa uma cache local em JSON para nao repetir pedidos desnecessarios -
um roster so e considerado "desatualizado" ao fim de alguns dias.
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


def obter_lineup_confirmado_do_jogo(match_id) -> dict:
    """
    Vai buscar o lineup CONFIRMADO especificamente para este encontro,
    diretamente na pagina do jogo. Isto inclui stand-ins (substituicoes
    pontuais), que NAO aparecem na pagina geral da equipa.

    Devolve {"1": [jogadores...], "2": [jogadores...]} - "1" e "2"
    correspondem a team1/team2, tal como na pagina de listagem de jogos.
    Devolve {} se a pagina nao tiver esta secao ainda (jogo muito
    distante no tempo, lineup por confirmar).
    """
    url = f"https://www.hltv.org/matches/{int(match_id)}/x"
    html = fetch_page(url)
    if html is None:
        return {}

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

    return resultado


def obter_lineup_atual(team_id) -> list:
    """
    Devolve o roster atual de uma equipa (lista de nicknames),
    usando cache local para nao pedir a mesma equipa repetidamente
    em pouco tempo.
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

    # Se a busca falhar (ex: cookie invalido), usar o valor antigo em
    # cache se existir, mesmo que desatualizado - e melhor que nada.
    if entrada is not None:
        return entrada["jogadores"]

    return []


def obter_lineups_para_equipas(team_ids) -> dict:
    """Versao em lote: devolve {team_id: [jogadores]} so para as
    equipas pedidas (evita ir buscar o roster de todas as +80 equipas
    do historico quando so precisamos de umas poucas, as que tem
    jogos agora)."""
    return {tid: obter_lineup_atual(tid) for tid in team_ids}


# --- Mantido por compatibilidade: versao antiga baseada no historico ---
# (ja nao e usada pelo predict_upcoming, mas fica disponivel caso seja
# util para analises offline)
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