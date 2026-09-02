"""
Teste: confirmar que (1) conseguimos aceder a uma pagina de mapstat
usando um slug generico/inventado (nao precisamos do slug real), e
(2) que o parser extrai corretamente os jogadores e ratings.
"""

from fetcher import fetch_page
from parse_players import parse_jogadores_do_mapa

# Propositadamente um slug ERRADO, para testar se o HLTV ignora
# esse texto e usa so o numero do mapstat_id.
url_teste = "https://www.hltv.org/stats/matches/mapstatsid/236101/qualquer-coisa-aqui"

html = fetch_page(url_teste)

if html is None:
    print("Falhou ao aceder a pagina.")
else:
    print(f"Pagina acedida com sucesso ({len(html)} caracteres).\n")
    dados = parse_jogadores_do_mapa(html)

    for equipa in dados:
        print(f"Equipa: {equipa['equipa_nome']}")
        for jogador in equipa["jogadores"]:
            print(f"  {jogador['nome']} (id={jogador['player_id']}) - rating: {jogador['rating']}")
        print()