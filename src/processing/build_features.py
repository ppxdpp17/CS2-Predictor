"""
Constrói as features de nível-equipa para cada match, respeitando
sempre a ordem cronológica (para nao ter data leakage):
- Elo rating de cada equipa, atualizado jogo a jogo
- Forma recente (winrate nos ultimos N jogos)
- Head-to-head (histórico direto entre as duas equipas)
- Winrate por mapa

Para cada match no dataset, as features refletem o estado das
equipas antes desse jogo acontecer - nunca informação do futuro.
"""

from collections import defaultdict, deque

import pandas as pd

ELO_INICIAL = 1500
K_FACTOR = 32 


def calcular_probabilidade_elo(rating_a: float, rating_b: float) -> float:
    """Probabilidade da equipa A ganhar, segundo a fórmula padrao do Elo."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def processar_estado_completo(caminho_matches: str = "../../data/matches_clean.csv"):
    """
    Percorre TODOS os matches cronologicamente e devolve o ESTADO FINAL
    (elo, forma recente, h2h) de cada equipa, tal como fica depois do
    último jogo do dataset.

    Esta função é partilhada entre:
    - a construcao do dataset de treino (features_dataset.csv)
    - o pipeline de previsao de jogos futuros (que precisa do estado
      mais recente de cada equipa para calcular as features de um
      jogo que ainda vai acontecer)

    Este não inclui a feature de winrate por mapa, porque essa
    depende de saber que mapas vão ser jogados - informação que só
    existe depois do veto, e por isso não está disponível para prever
    jogos futuros. Foi removida tambem do modelo de treino, para
    treino e produção usarem exatamente o mesmo conjunto de features.
    """
    df = pd.read_csv(caminho_matches)
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data").reset_index(drop=True)

    elo = defaultdict(lambda: ELO_INICIAL)
    historico_recente = defaultdict(lambda: deque(maxlen=10))
    h2h_vitorias = defaultdict(int)
    h2h_jogos = defaultdict(int)

    linhas_features = []

    for _, match in df.iterrows():
        id_a = match["team_a_id"]
        id_b = match["team_b_id"]

        elo_a_antes = elo[id_a]
        elo_b_antes = elo[id_b]

        forma_a = historico_recente[id_a]
        forma_b = historico_recente[id_b]
        winrate_recente_a = sum(forma_a) / len(forma_a) if len(forma_a) > 0 else None
        winrate_recente_b = sum(forma_b) / len(forma_b) if len(forma_b) > 0 else None

        h2h_jogos_anteriores = h2h_jogos[(id_a, id_b)]
        h2h_winrate_a = (h2h_vitorias[(id_a, id_b)] / h2h_jogos_anteriores
                         if h2h_jogos_anteriores > 0 else None)

        team_a_venceu = 1 if match["vencedor_id"] == id_a else 0

        linhas_features.append({
            "match_id": match["match_id"],
            "data": match["data"],
            "team_a_nome": match["team_a_nome"],
            "team_b_nome": match["team_b_nome"],
            "elo_a": elo_a_antes,
            "elo_b": elo_b_antes,
            "elo_diferenca": elo_a_antes - elo_b_antes,
            "forma_recente_a": winrate_recente_a,
            "forma_recente_b": winrate_recente_b,
            "jogos_historico_a": len(forma_a),
            "jogos_historico_b": len(forma_b),
            "h2h_winrate_a": h2h_winrate_a,
            "h2h_jogos": h2h_jogos_anteriores,
            "team_a_venceu": team_a_venceu,
        })

        prob_a_ganhar = calcular_probabilidade_elo(elo_a_antes, elo_b_antes)
        resultado_real_a = 1 if team_a_venceu else 0
        elo[id_a] = elo_a_antes + K_FACTOR * (resultado_real_a - prob_a_ganhar)
        elo[id_b] = elo_b_antes + K_FACTOR * ((1 - resultado_real_a) - (1 - prob_a_ganhar))

        historico_recente[id_a].append(team_a_venceu)
        historico_recente[id_b].append(1 - team_a_venceu)

        h2h_jogos[(id_a, id_b)] += 1
        h2h_jogos[(id_b, id_a)] += 1
        if team_a_venceu:
            h2h_vitorias[(id_a, id_b)] += 1
        else:
            h2h_vitorias[(id_b, id_a)] += 1

    estado_final = {
        "elo": elo,
        "historico_recente": historico_recente,
        "h2h_vitorias": h2h_vitorias,
        "h2h_jogos": h2h_jogos,
    }

    return pd.DataFrame(linhas_features), estado_final


def construir_features(caminho_matches: str = "../../data/matches_clean.csv",
                        caminho_saida: str = "../../data/features_dataset.csv",
                        janela_forma: int = 10) -> pd.DataFrame:

    df_features, _ = processar_estado_completo(caminho_matches)

    colunas_com_neutro = [
        "forma_recente_a", "forma_recente_b",
        "h2h_winrate_a",
    ]
    for col in colunas_com_neutro:
        df_features[f"{col}_tinha_dados"] = df_features[col].notna().astype(int)
        df_features[col] = df_features[col].fillna(0.5)

    df_features.to_csv(caminho_saida, index=False)
    print(f"Total de linhas geradas: {len(df_features)}")
    print(f"Guardado em: {caminho_saida}")

    return df_features


def calcular_winrate_por_mapa(caminho_matches: str = "../../data/matches_clean.csv") -> dict:
    """
    Percorre todo o histórico e devolve {(team_id, nome_mapa): (vitórias, jogos)}.

    Usado apenas para as previsões informativas por mapa no dashboard
    (não faz parte do modelo principal, que não usa esta informação
    por não estar disponível antes do veto de mapas).

    Tal como no cálculo original, conta-se o mapa como "vitória"
    se a equipa ganhou o encontro em que esse mapa foi jogado, não
    necessariamente esse mapa específico - uma simplificação válida
    dado que não temos sempre o resultado por mapa individual.
    """
    df = pd.read_csv(caminho_matches)

    mapa_vitorias = defaultdict(int)
    mapa_jogos = defaultdict(int)

    for _, match in df.iterrows():
        id_a = match["team_a_id"]
        id_b = match["team_b_id"]
        team_a_venceu = match["vencedor_id"] == id_a
        mapas = str(match["mapas_jogados"]).split(",")

        for m in mapas:
            mapa_jogos[(id_a, m)] += 1
            mapa_jogos[(id_b, m)] += 1
            if team_a_venceu:
                mapa_vitorias[(id_a, m)] += 1
            else:
                mapa_vitorias[(id_b, m)] += 1

    return {"vitorias": mapa_vitorias, "jogos": mapa_jogos}


if __name__ == "__main__":
    construir_features()