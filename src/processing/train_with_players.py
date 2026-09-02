"""
Junta as features de equipa (elo, forma, h2h, mapa) com as novas
features de jogador (rating medio da lineup, estabilidade de roster),
e re-treina a Regressao Logistica para comparar diretamente com o
resultado anterior (so features de equipa: Log Loss 0.645, Acc 63.2%).
"""

import sys
import os

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, log_loss, classification_report

# Permite importar do modulo train_baseline que esta noutra pasta (src/models)
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "models"))
from train_baseline import split_temporal


COLUNAS_NAO_FEATURES = [
    "match_id", "data", "team_a_nome", "team_b_nome", "team_a_venceu",
    "elo_a", "elo_b",
]


def carregar_dados_combinados(
    caminho_features_equipa: str = "../../data/features_dataset.csv",
    caminho_features_jogador: str = "../../data/features_jogador.csv",
):
    df_equipa = pd.read_csv(caminho_features_equipa)
    df_jogador = pd.read_csv(caminho_features_jogador)

    df = df_equipa.merge(df_jogador, on="match_id", how="left")
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data").reset_index(drop=True)

    # Se algum match nao tiver features de jogador (falha de scraping),
    # tratamos como valores em falta, com o mesmo principio de sempre.
    colunas_jogador = [c for c in df_jogador.columns if c != "match_id"]
    for col in colunas_jogador:
        if df[col].isnull().any():
            valor_neutro = 0.5 if "estabilidade" in col or "_tinha_dados" in col else 1.0
            df[col] = df[col].fillna(valor_neutro)

    return df


def treinar_e_comparar():
    df = carregar_dados_combinados()
    treino, teste = split_temporal(df)

    colunas_features = [c for c in df.columns if c not in COLUNAS_NAO_FEATURES]
    print(f"\nTotal de features (equipa + jogador): {len(colunas_features)}")

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

    print(f"\n=== Resultados (Equipa + Jogador) ===")
    print(f"Accuracy: {acc:.3f}  (anterior, so equipa: 0.632)")
    print(f"Log Loss: {ll:.3f}  (anterior, so equipa: 0.645)")
    print(f"\nRelatorio detalhado:")
    print(classification_report(y_teste, previsoes, target_names=["team_b_venceu", "team_a_venceu"]))

    classificador = modelo.named_steps["classificador"]
    importancias = pd.DataFrame({
        "feature": colunas_features,
        "coeficiente": classificador.coef_[0],
    }).sort_values("coeficiente", key=abs, ascending=False)
    print("\nImportancia das features:")
    print(importancias.to_string(index=False))

    return modelo, teste, previsoes, probabilidades


if __name__ == "__main__":
    treinar_e_comparar()