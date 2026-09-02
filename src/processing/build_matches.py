"""
Reconstroi os ENCONTROS completos (matches) a partir dos dados ao
nivel de MAPA que recolhemos.

Porque precisamos disto: um Bo3 aparece no nosso CSV como 2 ou 3
linhas separadas (uma por mapa). Para prever "quem ganha o encontro"
(o objetivo real do projeto), precisamos de juntar essas linhas num
so registo com o placar final (ex: 2-0, 2-1) e o vencedor geral.
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

    # Em vez de agrupar por "mesmo dia" (fragil: pode juntar 2 encontros
    # diferentes entre as mesmas equipas no mesmo dia, ex: fase de grupos
    # com double round-robin), agrupamos por PROXIMIDADE TEMPORAL:
    # mapas do mesmo confronto sao sempre jogados com poucas horas de
    # diferenca entre si. Se o intervalo for grande, e um encontro novo.
    LIMITE_HORAS = 4

    df = df.sort_values(["par_chave", "evento_id", "timestamp_unix"]).reset_index(drop=True)

    grupos_match = []
    contador_grupo = 0
    grupo_anterior = None
    tempo_anterior = None

    for _, row in df.iterrows():
        chave_atual = (row["par_chave"], row["evento_id"])

        if chave_atual != grupo_anterior:
            # Mudou de par de equipas/evento -> comeca sempre um novo grupo
            contador_grupo += 1
        elif tempo_anterior is not None:
            diff_horas = (row["timestamp_unix"] - tempo_anterior) / (1000 * 60 * 60)
            if diff_horas > LIMITE_HORAS:
                # Mesmo par/evento, mas muito tempo depois -> encontro novo
                contador_grupo += 1

        grupos_match.append(contador_grupo)
        grupo_anterior = chave_atual
        tempo_anterior = row["timestamp_unix"]

    df["grupo_match"] = grupos_match

    matches = []

    for grupo_id, grupo in df.groupby("grupo_match"):
        # Ordenar os mapas deste confronto pela ordem em que foram jogados
        grupo = grupo.sort_values("timestamp_unix")

        # Usamos a primeira linha para saber quem sao as equipas
        # (o "team1"/"team2" pode trocar de posicao entre mapas,
        # por isso fixamos com base nos IDs, nao nos nomes de coluna)
        primeira = grupo.iloc[0]
        id_a = primeira["team1_id"]
        id_b = primeira["team2_id"]
        nome_a = primeira["team1_nome"]
        nome_b = primeira["team2_nome"]

        mapas_ganhos_a = 0
        mapas_ganhos_b = 0
        mapas_jogados = []

        for _, mapa in grupo.iterrows():
            # Confirmar qual e o vencedor deste mapa em termos de id_a/id_b
            # (porque team1/team2 podem estar trocados face a primeira linha)
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

    # --- Filtrar casos empatados ---
    # Um encontro de CS2 nunca termina empatado no scoreboard. Quando
    # isto acontece nos nossos dados, e sinal de uma decisao arbitral
    # (ex: mapa anulado por infracao de regras, forfeit) que reverte o
    # resultado por motivos administrativos, nao refletidos no placar
    # dos mapas. Estes casos sao raros (~0.15% do dataset) e nao sao
    # previsiveis a partir de features de jogo, por isso excluimo-los
    # em vez de tentar adivinhar o vencedor real.
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