"""
Extrai os dados de jogador (ID, nome, rating) das duas tabelas de
estatísticas presentes numa página de detalhe de um mapa
(stats/matches/mapstatsid/...).
"""

from bs4 import BeautifulSoup


def parse_jogadores_do_mapa(html: str) -> list[dict]:
    """
    Devolve uma lista com 2 dicionários (um por equipa), cada um
    contendo o nome da equipa e a lista dos 5 jogadores dela
    (id, nome, rating) nesse mapa específico.
    """
    soup = BeautifulSoup(html, "html.parser")
    tabelas = soup.find_all("table", class_="totalstats")

    resultado = []

    for tabela in tabelas:
        th_equipa = tabela.find("th", class_="st-teamname")
        img_equipa = th_equipa.find("img") if th_equipa else None
        nome_equipa = img_equipa.get("alt") if img_equipa else None

        jogadores = []
        linhas_jogador = tabela.find("tbody").find_all("tr")

        for linha in linhas_jogador:
            link_jogador = linha.find("td", class_="st-player").find("a")
            nome_jogador = link_jogador.get_text(strip=True)
            player_id = link_jogador["href"].split("/")[3]

            rating_td = linha.find("td", class_="st-rating")
            rating = float(rating_td.get_text(strip=True)) if rating_td else None

            jogadores.append({
                "player_id": player_id,
                "nome": nome_jogador,
                "rating": rating,
            })

        resultado.append({
            "equipa_nome": nome_equipa,
            "jogadores": jogadores,
        })

    return resultado