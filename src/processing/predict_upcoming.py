"""
Gera previsoes para os jogos futuros/ao vivo listados em hltv.org/matches,
usando 3 modelos em simultaneo:
  Modelo 1 - Baseline Elo (formula de probabilidade Elo padrao, sem treino)
  Modelo 2 - Regressao Logistica (treinada com 100% do historico)
  Modelo 3 - XGBoost afinado (treinado com 100% do historico)
"""

import os
import sys

import joblib
import pandas as pd
from bs4 import BeautifulSoup

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(_BASE_DIR, "..", "models"))
sys.path.append(os.path.join(_BASE_DIR, "..", "scraper"))

from build_features import processar_estado_completo, calcular_probabilidade_elo, calcular_winrate_por_mapa
from get_upcoming_matches import obter_jogos_futuros
from team_rosters import obter_ultimo_lineup_por_equipa
from fetcher import fetch_page

_CAMINHO_MATCHES = os.path.join(_BASE_DIR, "..", "..", "data", "matches_clean.csv")
_CAMINHO_MODELO_LR = os.path.join(_BASE_DIR, "..", "..", "data", "modelo_producao.pkl")
_CAMINHO_MODELO_XGB = os.path.join(_BASE_DIR, "..", "..", "data", "modelo_producao_xgb.pkl")


def _buscar_nome_evento(event_id: str) -> str:
    try:
        html = fetch_page(f"https://www.hltv.org/events/{int(float(event_id))}/x")
        if html is None:
            return f"Evento #{event_id}"
        soup = BeautifulSoup(html, "html.parser")
        titulo = soup.find("h1", class_="event-hub-title")
        if titulo:
            return titulo.get_text(strip=True)
        if soup.title:
            return soup.title.get_text(strip=True).split(" - ")[0]
    except Exception:
        pass
    return f"Evento #{event_id}"


def gerar_previsoes() -> pd.DataFrame:
    _, estado = processar_estado_completo(_CAMINHO_MATCHES)
    elo = estado["elo"]
    historico_recente = estado["historico_recente"]
    h2h_vitorias = estado["h2h_vitorias"]
    h2h_jogos = estado["h2h_jogos"]

    df_matches = pd.read_csv(_CAMINHO_MATCHES)
    equipas_conhecidas = set(df_matches["team_a_id"]) | set(df_matches["team_b_id"])

    mapa_eventos = (
        df_matches.groupby("evento_id")["evento_nome"]
        .agg(lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0])
        .to_dict()
    )

    ultimo_lineup = obter_ultimo_lineup_por_equipa()
    winrate_mapa_estado = calcular_winrate_por_mapa(_CAMINHO_MATCHES)
    mapa_vitorias_hist = winrate_mapa_estado["vitorias"]
    mapa_jogos_hist = winrate_mapa_estado["jogos"]
    _cache_nomes_eventos = {}

    df_futuros = obter_jogos_futuros()
    if len(df_futuros) == 0:
        print("Nenhum jogo futuro encontrado (falha de scraping ou pagina vazia).")
        return pd.DataFrame()

    df_futuros = df_futuros.drop_duplicates(subset="match_id").reset_index(drop=True)
    df_futuros["team1_id"] = df_futuros["team1_id"].astype(float).astype(int)
    df_futuros["team2_id"] = df_futuros["team2_id"].astype(float).astype(int)

    df_futuros = df_futuros[
        df_futuros["team1_id"].isin(equipas_conhecidas) &
        df_futuros["team2_id"].isin(equipas_conhecidas)
    ].reset_index(drop=True)

    if len(df_futuros) == 0:
        print("Nenhum jogo futuro entre equipas conhecidas no momento.")
        return pd.DataFrame()

    pacote_lr = joblib.load(_CAMINHO_MODELO_LR)
    modelo_lr = pacote_lr["modelo"]
    colunas_lr = pacote_lr["colunas_features"]

    pacote_xgb = joblib.load(_CAMINHO_MODELO_XGB)
    modelo_xgb = pacote_xgb["modelo"]
    colunas_xgb = pacote_xgb["colunas_features"]

    linhas = []
    for _, jogo in df_futuros.iterrows():
        id_a = jogo["team1_id"]
        id_b = jogo["team2_id"]

        elo_a = elo[id_a]
        elo_b = elo[id_b]

        forma_a_deque = historico_recente[id_a]
        forma_b_deque = historico_recente[id_b]
        forma_a = sum(forma_a_deque) / len(forma_a_deque) if len(forma_a_deque) > 0 else 0.5
        forma_b = sum(forma_b_deque) / len(forma_b_deque) if len(forma_b_deque) > 0 else 0.5
        forma_a_tinha_dados = 1 if len(forma_a_deque) > 0 else 0
        forma_b_tinha_dados = 1 if len(forma_b_deque) > 0 else 0

        h2h_jogos_ab = h2h_jogos[(id_a, id_b)]
        h2h_winrate_a = (h2h_vitorias[(id_a, id_b)] / h2h_jogos_ab
                         if h2h_jogos_ab > 0 else 0.5)
        h2h_tinha_dados = 1 if h2h_jogos_ab > 0 else 0

        linha_features = {
            "elo_diferenca": elo_a - elo_b,
            "forma_recente_a": forma_a,
            "forma_recente_b": forma_b,
            "jogos_historico_a": len(forma_a_deque),
            "jogos_historico_b": len(forma_b_deque),
            "h2h_winrate_a": h2h_winrate_a,
            "h2h_jogos": h2h_jogos_ab,
            "forma_recente_a_tinha_dados": forma_a_tinha_dados,
            "forma_recente_b_tinha_dados": forma_b_tinha_dados,
            "h2h_winrate_a_tinha_dados": h2h_tinha_dados,
        }

        # --- Modelo 1: Baseline Elo (formula padrao, sem treino) ---
        prob1_modelo1 = calcular_probabilidade_elo(elo_a, elo_b)

        # --- Modelo 2: Regressao Logistica ---
        X_lr = pd.DataFrame([linha_features])[colunas_lr]
        prob1_modelo2 = modelo_lr.predict_proba(X_lr)[0, 1]

        # --- Modelo 3: XGBoost ---
        X_xgb = pd.DataFrame([linha_features])[colunas_xgb]
        prob1_modelo3 = modelo_xgb.predict_proba(X_xgb)[0, 1]

        # --- Previsoes heuristicas por mapa (so se ja houver mapas revelados) ---
        previsoes_mapa = []
        mapas_revelados = jogo.get("mapas_revelados", [])
        for mapa in mapas_revelados:
            jogos_a_mapa = mapa_jogos_hist[(id_a, mapa)]
            jogos_b_mapa = mapa_jogos_hist[(id_b, mapa)]
            winrate_a_mapa = (mapa_vitorias_hist[(id_a, mapa)] / jogos_a_mapa
                              if jogos_a_mapa > 0 else 0.5)
            winrate_b_mapa = (mapa_vitorias_hist[(id_b, mapa)] / jogos_b_mapa
                              if jogos_b_mapa > 0 else 0.5)
            soma = winrate_a_mapa + winrate_b_mapa
            prob_a_mapa = winrate_a_mapa / soma if soma > 0 else 0.5
            previsoes_mapa.append({
                "mapa": mapa,
                "prob_team1": prob_a_mapa,
                "prob_team2": 1 - prob_a_mapa,
                "jogos_historico_team1": jogos_a_mapa,
                "jogos_historico_team2": jogos_b_mapa,
            })

        event_id_str = str(jogo["event_id"])
        nome_evento = mapa_eventos.get(float(jogo["event_id"]) if jogo["event_id"] else None)
        if nome_evento is None:
            if event_id_str not in _cache_nomes_eventos:
                _cache_nomes_eventos[event_id_str] = _buscar_nome_evento(event_id_str)
            nome_evento = _cache_nomes_eventos[event_id_str]

        linhas.append({
            "match_id": jogo["match_id"],
            "data_hora": jogo["data_hora"],
            "ao_vivo": jogo["ao_vivo"],
            "formato": jogo["formato"],
            "team1_nome": jogo["team1_nome"],
            "team2_nome": jogo["team2_nome"],
            "elo_team1": round(elo_a),
            "elo_team2": round(elo_b),
            "prob1_modelo1": prob1_modelo1, "prob2_modelo1": 1 - prob1_modelo1,
            "prob1_modelo2": prob1_modelo2, "prob2_modelo2": 1 - prob1_modelo2,
            "prob1_modelo3": prob1_modelo3, "prob2_modelo3": 1 - prob1_modelo3,
            "team1_jogadores": ultimo_lineup.get(id_a, []),
            "team2_jogadores": ultimo_lineup.get(id_b, []),
            "evento_id": jogo["event_id"],
            "evento_nome": nome_evento,
            "previsoes_mapa": previsoes_mapa,
        })

    df_previsoes = pd.DataFrame(linhas).sort_values("data_hora").reset_index(drop=True)
    return df_previsoes


if __name__ == "__main__":
    df = gerar_previsoes()
    print(f"\nTotal de previsoes geradas: {len(df)}\n")
    for _, linha in df.iterrows():
        print(f"{linha['team1_nome']} vs {linha['team2_nome']}")
        print(f"  Modelo 1 (Elo):  {linha['prob1_modelo1']:.1%} / {linha['prob2_modelo1']:.1%}")
        print(f"  Modelo 2 (LR):   {linha['prob1_modelo2']:.1%} / {linha['prob2_modelo2']:.1%}")
        print(f"  Modelo 3 (XGB):  {linha['prob1_modelo3']:.1%} / {linha['prob2_modelo3']:.1%}")