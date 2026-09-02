"""
Treina o MODELO DE PRODUCAO final: usa TODOS os dados historicos
disponiveis (nao reserva conjunto de teste), porque o objetivo aqui
ja nao e avaliar o modelo (isso ja fizemos e documentamos), e sim
maximizar o sinal disponivel para previsoes reais de jogos futuros.

Guarda o modelo treinado em disco (joblib), para o dashboard poder
carrega-lo instantaneamente em vez de o re-treinar a cada atualizacao.
"""

import os
import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CAMINHO_DADOS = os.path.join(_BASE_DIR, "..", "..", "data", "features_dataset.csv")
_CAMINHO_MODELO = os.path.join(_BASE_DIR, "..", "..", "data", "modelo_producao.pkl")

COLUNAS_NAO_FEATURES = [
    "match_id", "data", "team_a_nome", "team_b_nome", "team_a_venceu",
    "elo_a", "elo_b",
]


def treinar_modelo_producao():
    df = pd.read_csv(_CAMINHO_DADOS)

    colunas_features = [c for c in df.columns if c not in COLUNAS_NAO_FEATURES]
    print(f"Features usadas ({len(colunas_features)}): {colunas_features}")

    X = df[colunas_features]
    y = df["team_a_venceu"]

    modelo = Pipeline([
        ("scaler", StandardScaler()),
        ("classificador", LogisticRegression(max_iter=1000)),
    ])
    modelo.fit(X, y)

    joblib.dump({"modelo": modelo, "colunas_features": colunas_features}, _CAMINHO_MODELO)
    print(f"\nModelo de producao treinado com {len(df)} jogos e guardado em: {_CAMINHO_MODELO}")

    return modelo, colunas_features


if __name__ == "__main__":
    treinar_modelo_producao()