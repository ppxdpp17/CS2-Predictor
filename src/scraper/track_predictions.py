"""
Regista as previsoes feitas ao longo do tempo pelos 3 modelos, num
ficheiro persistente (previsoes_log.csv), e verifica periodicamente
se os jogos ja terminaram, comparando cada previsao com o resultado
real - permitindo calcular a accuracy real de CADA modelo em producao.
"""

import os
from bs4 import BeautifulSoup
import pandas as pd

from fetcher import fetch_page

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAMINHO_LOG = os.path.join(_BASE_DIR, "..", "..", "data", "previsoes_log.csv")

NOMES_MODELOS = ["modelo1", "modelo2", "modelo3"]


def carregar_log() -> pd.DataFrame:
    colunas = [
        "match_id", "data_previsao", "data_hora_jogo", "team1_nome", "team2_nome",
        "elo_team1", "elo_team2", "formato",
        "prob1_modelo1", "prob1_modelo2", "prob1_modelo3",
        "vencedor_previsto_modelo1", "vencedor_previsto_modelo2", "vencedor_previsto_modelo3",
        "resultado_real",
        "acertou_modelo1", "acertou_modelo2", "acertou_modelo3",
    ]
    if os.path.exists(CAMINHO_LOG):
        return pd.read_csv(CAMINHO_LOG)
    return pd.DataFrame(columns=colunas)


def registar_previsoes(df_previsoes: pd.DataFrame) -> None:
    log_atual = carregar_log()
    match_ids_ja_registados = set(log_atual["match_id"].astype(str))

    novas_linhas = []
    for _, jogo in df_previsoes.iterrows():
        if str(jogo["match_id"]) in match_ids_ja_registados:
            continue

        linha = {
            "match_id": jogo["match_id"],
            "data_previsao": pd.Timestamp.now(),
            "data_hora_jogo": jogo["data_hora"],
            "team1_nome": jogo["team1_nome"],
            "team2_nome": jogo["team2_nome"],
            "elo_team1": jogo["elo_team1"],
            "elo_team2": jogo["elo_team2"],
            "formato": jogo["formato"],
            "resultado_real": None,
        }

        for m in NOMES_MODELOS:
            prob1 = jogo[f"prob1_{m}"]
            linha[f"prob1_{m}"] = prob1
            linha[f"vencedor_previsto_{m}"] = (
                jogo["team1_nome"] if prob1 > 0.5 else jogo["team2_nome"]
            )
            linha[f"acertou_{m}"] = None

        novas_linhas.append(linha)

    if novas_linhas:
        df_novas = pd.DataFrame(novas_linhas)
        log_atualizado = pd.concat([log_atual, df_novas], ignore_index=True)
        log_atualizado.to_csv(CAMINHO_LOG, index=False)


def _buscar_resultados_recentes(max_paginas: int = 2) -> dict:
    resultados = {}
    for pagina in range(max_paginas):
        offset = pagina * 100
        url = f"https://www.hltv.org/results?offset={offset}"
        html = fetch_page(url)
        if html is None:
            continue

        soup = BeautifulSoup(html, "html.parser")
        blocos = soup.find_all("div", class_="result")

        for bloco in blocos:
            link_tag = bloco.parent
            href = link_tag.get("href", "")
            partes = href.split("/")
            if len(partes) <= 2:
                continue
            match_id = partes[2]

            team_divs = bloco.find_all("div", class_="team")
            if len(team_divs) < 2:
                continue

            team1_venceu = "team-won" in team_divs[0].get("class", [])
            vencedor = (team_divs[0].get_text(strip=True) if team1_venceu
                       else team_divs[1].get_text(strip=True))

            resultados[match_id] = vencedor

    return resultados


def verificar_resultados(max_paginas: int = 2) -> int:
    log = carregar_log()
    pendentes = log[log["resultado_real"].isna()]

    if len(pendentes) == 0:
        return 0

    resultados_recentes = _buscar_resultados_recentes(max_paginas)

    resolvidos = 0
    for idx, linha in pendentes.iterrows():
        match_id = str(linha["match_id"])
        if match_id in resultados_recentes:
            vencedor_real = resultados_recentes[match_id]
            log.at[idx, "resultado_real"] = vencedor_real
            for m in NOMES_MODELOS:
                log.at[idx, f"acertou_{m}"] = (
                    vencedor_real == linha[f"vencedor_previsto_{m}"]
                )
            resolvidos += 1

    if resolvidos > 0:
        log.to_csv(CAMINHO_LOG, index=False)

    return resolvidos


def obter_estatisticas() -> dict:
    log = carregar_log()
    resolvidos = log[log["resultado_real"].notna()]

    stats = {
        "total_previsoes": len(log),
        "total_resolvidos": len(resolvidos),
        "total_pendentes": len(log) - len(resolvidos),
    }

    for m in NOMES_MODELOS:
        col = f"acertou_{m}"
        if len(resolvidos) > 0 and col in resolvidos.columns:
            stats[f"accuracy_{m}"] = resolvidos[col].mean()
        else:
            stats[f"accuracy_{m}"] = None

    return stats