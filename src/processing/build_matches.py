"""
Reconstrói os encontros completos (matches) a partir dos dados ao
nível de mapa que recolhemos.

Isto é necessário porque um Bo3 aparece no nosso CSV como 2 ou 3
linhas separadas (uma por mapa). Para prever "quem ganha o encontro"
(o objetivo real do projeto), precisamos de juntar essas linhas num
só registo com o placar final (ex: 2-0, 2-1) e o vencedor geral.
"""

import pandas as pd


def construir_matches(caminho_entrada: str = "../../data/mapas_raw.csv",
                       caminho_saida: str = "../../data/matches_clean.csv") -> pd.DataFrame:

    df = pd.read_csv(caminho_entrada)
    df["data"] = pd.to_datetime(df["timestamp_unix"], unit="ms")

    def chave_par(row):
        ids = sorted([str(row["team1_id"]), str(row["team2_id"])])
        return f"{ids[0]}_{ids[1]}"

    df["par_chave"] = df.apply(chave_par, axis=1)

    LIMITE_HORAS = 4

    df = df.sort_values(["par_chave", "evento_id", "timestamp_unix"]).reset_index(drop=True)

    grupos_match = []
    contador_grupo = 0
    grupo_anterior = None
    tempo_anterior = None

    for _, row in df.iterrows():
        chave_atual = (row["par_chave"], row["evento_id"])

        if chave_atual != grupo_anterior:
            contador_grupo += 1
        elif tempo_anterior is not None:
            diff_horas = (row["timestamp_unix"] - tempo_anterior) / (1000 * 60 * 60)
            if diff_horas > LIMITE_HORAS:
                contador_grupo += 1

        grupos_match.append(contador_grupo)
        grupo_anterior = chave_atual
        tempo_anterior = row["timestamp_unix"]

    df["grupo_match"] = grupos_match

    matches = []

    for grupo_id, grupo in df.groupby("grupo_match"):
        grupo = grupo.sort_values("timestamp_unix")

        primeira = grupo.iloc[0]
        id_a = primeira["team1_id"]
        id_b = primeira["team2_id"]
        nome_a = primeira["team1_nome"]
        nome_b = primeira["team2_nome"]

        mapas_ganhos_a = 0
        mapas_ganhos_b = 0
        mapas_jogados = []

        for _, mapa in grupo.iterrows():
            if mapa["team1_id"] == id_a:
                score_a, score_b = mapa["team1_score"], mapa["team2_score"]
            else:
                score_a, score_b = mapa["team2_score"], mapa["team1_score"]

            if score_a > score_b:
                mapas_ganhos_a += 1
            else:
                mapas_ganhos_b += 1

            mapas_jogados.append(mapa["mapa"])

        vencedor_id = id_a if mapas_ganhos_a > mapas_ganhos_b else id_b
        vencedor_nome = nome_a if mapas_ganhos_a > mapas_ganhos_b else nome_b

        matches.append({
            "match_id": grupo_id,
            "data": primeira["data"],
            "evento_id": primeira["evento_id"],
            "evento_nome": primeira["evento_nome"],
            "team_a_id": id_a,
            "team_a_nome": nome_a,
            "team_b_id": id_b,
            "team_b_nome": nome_b,
            "mapas_ganhos_a": mapas_ganhos_a,
            "mapas_ganhos_b": mapas_ganhos_b,
            "num_mapas": len(grupo),
            "mapas_jogados": ",".join(mapas_jogados),
            "mapstat_ids": ",".join(grupo["mapstat_id"].astype(str)),
            "vencedor_id": vencedor_id,
            "vencedor_nome": vencedor_nome,
        })

    df_matches = pd.DataFrame(matches).sort_values("data").reset_index(drop=True)

    empatados = df_matches[df_matches["mapas_ganhos_a"] == df_matches["mapas_ganhos_b"]]
    if len(empatados) > 0:
        print(f"\nAVISO: {len(empatados)} matches excluidos por resultado empatado "
              f"no scoreboard (provavelmente decisoes arbitrais/forfeits nao "
              f"capturaveis nos dados de mapa). Match IDs excluidos: "
              f"{list(empatados['match_id'])}")
        df_matches = df_matches[df_matches["mapas_ganhos_a"] != df_matches["mapas_ganhos_b"]]
        df_matches = df_matches.reset_index(drop=True)

    df_matches.to_csv(caminho_saida, index=False)

    print(f"Total de mapas originais: {len(df)}")
    print(f"Total de encontros (matches) reconstruidos: {len(df_matches)}")
    print(f"Guardado em: {caminho_saida}")

    return df_matches


if __name__ == "__main__":
    construir_matches()