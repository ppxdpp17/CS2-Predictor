"""
Treina o modelo XGBoost de PRODUCAO, usando os melhores hiperparametros
ja encontrados via GridSearchCV (max_depth=2, n_estimators=50,
learning_rate=0.05), agora com 100% dos dados historicos disponiveis.
"""

import os
import joblib
import pandas as pd
from xgboost import XGBClassifier

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CAMINHO_DADOS = os.path.join(_BASE_DIR, "..", "..", "data", "features_dataset.csv")
_CAMINHO_MODELO = os.path.join(_BASE_DIR, "..", "..", "data", "modelo_producao_xgb.pkl")

COLUNAS_NAO_FEATURES = [
    "match_id", "data", "team_a_nome", "team_b_nome", "team_a_venceu",
    "elo_a", "elo_b",
]


def treinar_modelo_producao_xgb():
    df = pd.read_csv(_CAMINHO_DADOS)
    colunas_features = [c for c in df.columns if c not in COLUNAS_NAO_FEATURES]

    X = df[colunas_features]
    y = df["team_a_venceu"]

    modelo = XGBClassifier(
        n_estimators=50,
        max_depth=2,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )
    modelo.fit(X, y)

    joblib.dump({"modelo": modelo, "colunas_features": colunas_features}, _CAMINHO_MODELO)
    print(f"Modelo XGBoost de producao treinado com {len(df)} jogos e guardado em: {_CAMINHO_MODELO}")

    return modelo, colunas_features


if __name__ == "__main__":
    treinar_modelo_producao_xgb()