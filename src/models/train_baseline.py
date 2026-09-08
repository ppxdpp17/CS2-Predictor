"""
Primeiro modelo de Machine Learning: Regressão Logistica.

Usa um split TEMPORAL (não aleatório) entre treino e teste, para
respeitar a mesma regra do resto do projeto: nunca treinar
com informação "do futuro" em relação ao que estamos a testar.

Compara sempre com um baseline ingénuo (prever sempre a equipa
com Elo mais alto), para sabermos se o modelo está genuinamente
a acrescentar valor preditivo.
"""

import os
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, log_loss, classification_report

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CAMINHO_DADOS_DEFAULT = os.path.join(_BASE_DIR, "..", "..", "data", "features_dataset.csv")


COLUNAS_NAO_FEATURES = [
    "match_id", "data", "team_a_nome", "team_b_nome", "team_a_venceu",
    "elo_a", "elo_b",
]


def carregar_dados(caminho: str = None):
    if caminho is None:
        caminho = _CAMINHO_DADOS_DEFAULT
    df = pd.read_csv(caminho)
    df["data"] = pd.to_datetime(df["data"])
    df = df.sort_values("data").reset_index(drop=True)
    return df


def split_temporal(df: pd.DataFrame, proporcao_treino: float = 0.8):
    """
    Divide em treino/teste respeitando a ordem cronológica:
    os primeiros X% (mais antigos) vão para treino, os últimos
    (1-X)% (mais recentes) vão para teste.
    """
    ponto_corte = int(len(df) * proporcao_treino)
    treino = df.iloc[:ponto_corte]
    teste = df.iloc[ponto_corte:]

    print(f"Treino: {len(treino)} jogos ({treino['data'].min().date()} a {treino['data'].max().date()})")
    print(f"Teste:  {len(teste)} jogos ({teste['data'].min().date()} a {teste['data'].max().date()})")

    return treino, teste


def avaliar_baseline_ingenuo(teste: pd.DataFrame) -> None:
    """Baseline: prever sempre que a equipa com Elo mais alto ganha."""
    previsao_ingenua = (teste["elo_diferenca"] > 0).astype(int)
    acc_ingenua = accuracy_score(teste["team_a_venceu"], previsao_ingenua)
    print(f"\nBaseline ingenuo (Elo mais alto ganha sempre): accuracy = {acc_ingenua:.3f}")


def treinar_e_avaliar():
    df = carregar_dados()
    treino, teste = split_temporal(df)

    colunas_features = [c for c in df.columns if c not in COLUNAS_NAO_FEATURES]
    print(f"\nFeatures usadas ({len(colunas_features)}): {colunas_features}")

    X_treino = treino[colunas_features]
    y_treino = treino["team_a_venceu"]
    X_teste = teste[colunas_features]
    y_teste = teste["team_a_venceu"]

    avaliar_baseline_ingenuo(teste)

    modelo = Pipeline([
        ("scaler", StandardScaler()),
        ("classificador", LogisticRegression(max_iter=1000)),
    ])
    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict(X_teste)
    probabilidades = modelo.predict_proba(X_teste)[:, 1]

    acc = accuracy_score(y_teste, previsoes)
    ll = log_loss(y_teste, probabilidades)

    print(f"\n=== Resultados do modelo (Regressao Logistica) ===")
    print(f"Accuracy: {acc:.3f}")
    print(f"Log Loss: {ll:.3f}")
    print(f"\nRelatorio detalhado:")
    print(classification_report(y_teste, previsoes, target_names=["team_b_venceu", "team_a_venceu"]))

    classificador = modelo.named_steps["classificador"]
    importancias = pd.DataFrame({
        "feature": colunas_features,
        "coeficiente": classificador.coef_[0],
    }).sort_values("coeficiente", key=abs, ascending=False)
    print("\nImportancia das features (maior valor absoluto = mais influente):")
    print(importancias.to_string(index=False))

    return modelo, teste, previsoes, probabilidades


if __name__ == "__main__":
    treinar_e_avaliar()