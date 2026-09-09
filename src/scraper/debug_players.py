"""
Diagnóstico: investigar em detalhe os 3 match_ids problemáticos,
mostrando exatamente o que a página devolve e porque a comparação
de nomes de equipa pode estar a falhar.
"""

import pandas as pd
from fetcher import fetch_page
from parse_players import parse_jogadores_do_mapa

df_matches = pd.read_csv("../../data/matches_clean.csv")

match_ids_problematicos = [632, 1154, 1117]

for match_id in match_ids_problematicos:
    match = df_matches[df_matches["match_id"] == match_id]
    if len(match) == 0:
        print(f"match_id={match_id} nao encontrado em matches_clean.csv")
        continue

    match = match.iloc[0]
    print(f"\n{'=' * 60}")
    print(f"match_id={match_id}")
    print(f"  team_a_nome (repr): {repr(match['team_a_nome'])}")
    print(f"  team_b_nome (repr): {repr(match['team_b_nome'])}")

    primeiro_mapstat_id = str(match["mapstat_ids"]).split(",")[0]
    url = f"https://www.hltv.org/stats/matches/mapstatsid/{primeiro_mapstat_id}/x"
    print(f"  URL: {url}")

    html = fetch_page(url)
    if html is None:
        print("  FALHOU a aceder a pagina (provavelmente erro de rede).")
        continue

    dados = parse_jogadores_do_mapa(html)
    print(f"  Numero de tabelas de equipa encontradas: {len(dados)}")
    for equipa in dados:
        print(f"  Nome extraido da pagina (repr): {repr(equipa['equipa_nome'])}")
        print(f"    Numero de jogadores: {len(equipa['jogadores'])}")