"""
Constroi features ao nivel de JOGADOR/ROSTER para cada match:
- rating medio historico da lineup (baseado SO em jogos anteriores
  de cada jogador, nunca no jogo atual)
- estabilidade de roster (a equipa jogou com os mesmos jogadores do
  jogo anterior dela, ou mudou alguem?)

Segue a mesma regra de ouro de sempre: processamos os matches por
ordem cronologica, e so atualizamos o "historico" de cada jogador
DEPOIS de termos calculado as features desse match.
"""

from collections import defaultdict

import pandas as pd


def construir_features_jogador(
    caminho_matches: str = "../../data/matches_clean.csv",
    caminho_jogadores: str = "../../data/jogadores_por_match.csv",
    caminho_saida: str = "../../data/features_jogador.csv",
) -> pd.DataFrame:

    df_matches = pd.read_csv(caminho_matches)
    df_matches["data"] = pd.to_datetime(df_matches["data"])
    df_matches = df_matches.sort_values("data").reset_index(drop=True)

    df_jogadores = pd.read_csv(caminho_jogadores)

    grupos_lineup = df_jogadores.groupby(["match_id", "team_label"])

    historico_rating_jogador = defaultdict(list)
    ultimo_lineup_equipa = {}

    linhas_saida = []

    for _, match in df_matches.iterrows():
        match_id = match["match_id"]
        id_a = match["team_a_id"]
        id_b = match["team_b_id"]

        try:
            lineup_a = grupos_lineup.get_group((match_id, "a"))
            lineup_b = grupos_lineup.get_group((match_id, "b"))
        except KeyError:
            linhas_saida.append({
                "match_id": match_id,
                "rating_medio_lineup_a": None,
                "rating_medio_lineup_b": None,
                "roster_estabilidade_a": None,
                "roster_estabilidade_b": None,
            })
            continue

        players_ids_a = set(lineup_a["player_id"])
        players_ids_b = set(lineup_b["player_id"])

        def rating_medio_historico(players_ids):
            ratings_conhecidos = []
            for pid in players_ids:
                historico = historico_rating_jogador[pid]
                if historico:
                    ratings_conhecidos.append(sum(historico) / len(historico))
            if not ratings_conhecidos:
                return None
            return sum(ratings_conhecidos) / len(ratings_conhecidos)

        rating_medio_a = rating_medio_historico(players_ids_a)
        rating_medio_b = rating_medio_historico(players_ids_b)

        def calcular_estabilidade(team_id, players_ids_atuais):
            lineup_anterior = ultimo_lineup_equipa.get(team_id)
            if lineup_anterior is None:
                return None
            intersecao = players_ids_atuais & lineup_anterior
            return len(intersecao) / 5

        estabilidade_a = calcular_estabilidade(id_a, players_ids_a)
        estabilidade_b = calcular_estabilidade(id_b, players_ids_b)

        linhas_saida.append({
            "match_id": match_id,
            "rating_medio_lineup_a": rating_medio_a,
            "rating_medio_lineup_b": rating_medio_b,
            "roster_estabilidade_a": estabilidade_a,
            "roster_estabilidade_b": estabilidade_b,
        })

        for _, jogador in lineup_a.iterrows():
            if pd.notna(jogador["rating"]):
                historico_rating_jogador[jogador["player_id"]].append(jogador["rating"])
        for _, jogador in lineup_b.iterrows():
            if pd.notna(jogador["rating"]):
                historico_rating_jogador[jogador["player_id"]].append(jogador["rating"])

        ultimo_lineup_equipa[id_a] = players_ids_a
        ultimo_lineup_equipa[id_b] = players_ids_b

    df_saida = pd.DataFrame(linhas_saida)

    for col in ["rating_medio_lineup_a", "rating_medio_lineup_b"]:
        df_saida[f"{col}_tinha_dados"] = df_saida[col].notna().astype(int)
        df_saida[col] = df_saida[col].fillna(1.0)

    for col in ["roster_estabilidade_a", "roster_estabilidade_b"]:
        df_saida[f"{col}_tinha_dados"] = df_saida[col].notna().astype(int)
        df_saida[col] = df_saida[col].fillna(0.5)

    df_saida.to_csv(caminho_saida, index=False)
    print(f"Total de linhas: {len(df_saida)}")
    print(f"Guardado em: {caminho_saida}")

    return df_saida


if __name__ == "__main__":
    construir_features_jogador()