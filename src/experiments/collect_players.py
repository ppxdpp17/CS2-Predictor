"""
Recolhe os dados de jogador (5 por equipa, 10 por match) para todos os
encontros em matches_clean.csv.

Usa sempre o primeiro mapa de cada encontro como referência para o
roster (assume-se estabilidade de lineup ao longo da serie, que é
o caso normal - trocas de jogador a meio de um Bo3 são raras).

Guarda progressivamente (uma linha por jogador-match) e pára de
forma limpa se o cookie expirar, permitindo retomar depois.
"""

import os
import pandas as pd

from fetcher import fetch_page, gentle_pause, CookieExpiradoError
from experiments.parse_players import parse_jogadores_do_mapa


def recolher_dados_jogadores(
    caminho_matches: str = "../../data/matches_clean.csv",
    caminho_saida: str = "../../data/jogadores_por_match.csv",
    limite: int | None = None,
) -> None:

    df_matches = pd.read_csv(caminho_matches)
    if limite:
        df_matches = df_matches.head(limite)

    match_ids_ja_feitos = set()
    if os.path.exists(caminho_saida):
        df_existente = pd.read_csv(caminho_saida)
        contagem_por_match = df_existente.groupby("match_id").size()
        match_ids_completos = set(contagem_por_match[contagem_por_match == 10].index)
        match_ids_incompletos = set(contagem_por_match[contagem_por_match != 10].index)

        if match_ids_incompletos:
            print(f"Encontrados {len(match_ids_incompletos)} matches incompletos "
                  f"(vao ser reprocessados): {match_ids_incompletos}")
            df_existente = df_existente[~df_existente["match_id"].isin(match_ids_incompletos)]
            df_existente.to_csv(caminho_saida, index=False)

        match_ids_ja_feitos = match_ids_completos
        print(f"Ficheiro existente encontrado: {len(match_ids_ja_feitos)} matches completos.")

    total = len(df_matches)
    processados_nesta_sessao = 0

    for i, match in df_matches.iterrows():
        match_id = match["match_id"]

        if match_id in match_ids_ja_feitos:
            continue

        primeiro_mapstat_id = str(match["mapstat_ids"]).split(",")[0]
        url = f"https://www.hltv.org/stats/matches/mapstatsid/{primeiro_mapstat_id}/x"

        print(f"[{i + 1}/{total}] match_id={match_id} (mapstat={primeiro_mapstat_id})...")

        try:
            html = fetch_page(url)
        except CookieExpiradoError:
            print("\n" + "=" * 60)
            print("COOKIE EXPIRADO. Recolha parada de forma limpa.")
            print(f"Progresso guardado em: {caminho_saida}")
            print(f"Matches processados nesta sessao: {processados_nesta_sessao}")
            print("Renova o cf_clearance no .env e corre o script outra vez -")
            print("ele retoma automaticamente a partir de onde ficou.")
            print("=" * 60)
            return

        if html is None:
            print("  Falhou (sem cookie expirado detetado), a passar a frente.")
            continue

        dados_equipas = parse_jogadores_do_mapa(html)

        if len(dados_equipas) != 2:
            print(f"  AVISO: esperava 2 equipas, encontrei {len(dados_equipas)}. A saltar.")
            continue

        linhas = []
        for equipa in dados_equipas:
            nome_equipa_normalizado = equipa["equipa_nome"].strip().lower()
            nome_a_normalizado = str(match["team_a_nome"]).strip().lower()
            nome_b_normalizado = str(match["team_b_nome"]).strip().lower()

            if nome_equipa_normalizado == nome_a_normalizado:
                label_equipa = "a"
                team_id = match["team_a_id"]
            elif nome_equipa_normalizado == nome_b_normalizado:
                label_equipa = "b"
                team_id = match["team_b_id"]
            else:
                print(f"  AVISO: nome de equipa '{equipa['equipa_nome']}' nao "
                      f"corresponde a nenhuma das equipas esperadas. A saltar equipa.")
                continue

            for jogador in equipa["jogadores"]:
                linhas.append({
                    "match_id": match_id,
                    "team_label": label_equipa,
                    "team_id": team_id,
                    "player_id": jogador["player_id"],
                    "player_nome": jogador["nome"],
                    "rating": jogador["rating"],
                })

        if linhas:
            df_linhas = pd.DataFrame(linhas)
            escrever_header = not os.path.exists(caminho_saida)
            df_linhas.to_csv(caminho_saida, mode="a", index=False, header=escrever_header)
            processados_nesta_sessao += 1

        gentle_pause()

    print(f"\nConcluido. Matches processados nesta sessao: {processados_nesta_sessao}")


if __name__ == "__main__":
    recolher_dados_jogadores(limite=10)