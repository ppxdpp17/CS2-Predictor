"""
Calcula o LINEUP MAIS RECENTE conhecido de cada equipa, percorrendo
o historico cronologicamente. Usado para mostrar os jogadores de
cada equipa como tooltip no dashboard (usamos o ultimo lineup
conhecido como aproximacao do roster atual).
"""

import os
import pandas as pd

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CAMINHO_MATCHES = os.path.join(_BASE_DIR, "..", "..", "data", "matches_clean.csv")
_CAMINHO_JOGADORES = os.path.join(_BASE_DIR, "..", "..", "data", "jogadores_por_match.csv")


def obter_ultimo_lineup_por_equipa() -> dict:
    """Devolve {team_id: [nome_jogador1, ..., nome_jogador5]}."""
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