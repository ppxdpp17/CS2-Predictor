"""
Testa isoladamente se a "estabilidade de roster" (a equipa jogou com
o mesmo lineup do jogo anterior dela, ou mudou alguem?) acrescenta
sinal preditivo, SEM a diluir junto com outras features de jogador
(como fizemos na experiencia anterior).

Reutiliza os dados ja recolhidos (features_jogador.csv) - nao exige
scraping novo.
"""

import sys
import os

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, log_loss, classification_report

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "models"))
from train_baseline import split_temporal


def carregar_dados_com_roster_isolado():
    df_equipa = pd.read_csv("../../data/features_dataset.csv")
    df_jogador = pd.read_csv("../../data/features_jogador.csv")

    # So trazemos as colunas de ESTABILIDADE DE ROSTER, ignorando
    # deliberadamente o rating_medio_lineup (para isolar o efeito).
    colunas_roster = [
        "match_id",
        "roster_estabilidade_a", "roster_estabilidade_b",
        "roster_estabilidade_a_tinha_dados", "roster_estabilidade_b_tinha_dados",
    ]
    df_jogador_isolado = df_jogador[colunas_roster]

    df = df_equipa.merge(df_jogador_isolado, on="match_id", how="left")
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data").reset_index(drop=True)

    for col in ["roster_estabilidade_a", "roster_estabilidade_b"]:
        df[col] = df[col].fillna(0.5)
    for col in ["roster_estabilidade_a_tinha_dados", "roster_estabilidade_b_tinha_dados"]:
        df[col] = df[col].fillna(0)

    return df


COLUNAS_NAO_FEATURES = [
    "match_id", "data", "team_a_nome", "team_b_nome", "team_a_venceu",
    "elo_a", "elo_b",
]


def treinar_e_comparar():
    df = carregar_dados_com_roster_isolado()
    treino, teste = split_temporal(df)

    colunas_features = [c for c in df.columns if c not in COLUNAS_NAO_FEATURES]
    print(f"Features usadas ({len(colunas_features)}): {colunas_features}\n")

    X_treino = treino[colunas_features]
    y_treino = treino["team_a_venceu"]
    X_teste = teste[colunas_features]
    y_teste = teste["team_a_venceu"]

    modelo = Pipeline([
        ("scaler", StandardScaler()),
        ("classificador", LogisticRegression(max_iter=1000)),
    ])
    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict(X_teste)
    probabilidades = modelo.predict_proba(X_teste)[:, 1]

    acc = accuracy_score(y_teste, previsoes)
    ll = log_loss(y_teste, probabilidades)

    print("=== Resultados (Equipa + Estabilidade de Roster ISOLADA) ===")
    print(f"Accuracy: {acc:.3f}  (baseline so-equipa: 0.632)")
    print(f"Log Loss: {ll:.3f}  (baseline so-equipa: 0.645)")
    print(classification_report(y_teste, previsoes, target_names=["team_b_venceu", "team_a_venceu"]))

    classificador = modelo.named_steps["classificador"]
    importancias = pd.DataFrame({
        "feature": colunas_features,
        "coeficiente": classificador.coef_[0],
    }).sort_values("coeficiente", key=abs, ascending=False)
    print("Importancia das features:")
    print(importancias.to_string(index=False))


if __name__ == "__main__":
    treinar_e_comparar()