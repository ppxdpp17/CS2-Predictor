"""
Corrige manualmente os 3 matches problemáticos, sem depender da
lógica de "já processado" do script principal (que estava, por
alguma razão, a marcá-los incorretamente como completos/saltados).
"""

import pandas as pd
from fetcher import fetch_page
from parse_players import parse_jogadores_do_mapa

CAMINHO_SAIDA = "../../data/jogadores_por_match.csv"

df_matches = pd.read_csv("../../data/matches_clean.csv")
match_ids_para_corrigir = [632, 1154, 1117]

df_existente = pd.read_csv(CAMINHO_SAIDA)
antes = len(df_existente)
df_existente = df_existente[~df_existente["match_id"].isin(match_ids_para_corrigir)]
print(f"Removidas {antes - len(df_existente)} linhas antigas destes match_ids.")
df_existente.to_csv(CAMINHO_SAIDA, index=False)

novas_linhas = []

for match_id in match_ids_para_corrigir:
    match = df_matches[df_matches["match_id"] == match_id].iloc[0]

    primeiro_mapstat_id = str(match["mapstat_ids"]).split(",")[0]
    url = f"https://www.hltv.org/stats/matches/mapstatsid/{primeiro_mapstat_id}/x"

    print(f"A processar match_id={match_id}...")
    html = fetch_page(url)

    if html is None:
        print(f"  FALHOU a aceder. Ignorado - tenta correr este script outra vez.")
        continue

    dados_equipas = parse_jogadores_do_mapa(html)

    for equipa in dados_equipas:
        nome_normalizado = equipa["equipa_nome"].strip().lower()
        nome_a_normalizado = str(match["team_a_nome"]).strip().lower()
        nome_b_normalizado = str(match["team_b_nome"]).strip().lower()

        if nome_normalizado == nome_a_normalizado:
            label_equipa, team_id = "a", match["team_a_id"]
        elif nome_normalizado == nome_b_normalizado:
            label_equipa, team_id = "b", match["team_b_id"]
        else:
            print(f"  AVISO: '{equipa['equipa_nome']}' ainda nao corresponde. A saltar equipa.")
            continue

        for jogador in equipa["jogadores"]:
            novas_linhas.append({
                "match_id": match_id,
                "team_label": label_equipa,
                "team_id": team_id,
                "player_id": jogador["player_id"],
                "player_nome": jogador["nome"],
                "rating": jogador["rating"],
            })

    print(f"  OK - {len([l for l in novas_linhas if l['match_id'] == match_id])} jogadores guardados.")

if novas_linhas:
    df_novas = pd.DataFrame(novas_linhas)
    df_novas.to_csv(CAMINHO_SAIDA, mode="a", index=False, header=False)
    print(f"\n{len(novas_linhas)} novas linhas adicionadas com sucesso.")