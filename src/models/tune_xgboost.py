"""
Procura os melhores hiperparâmetros para o XGBoost usando TimeSeriesSplit, 
que respeita a ordem cronológica em cada divisão treino/validacao - nunca testa 
no passado usando informação do futuro, mesmo durante o tuning.
"""

import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import accuracy_score, log_loss, classification_report

from train_baseline import carregar_dados, split_temporal, COLUNAS_NAO_FEATURES


def tunar_e_avaliar_xgboost():
    df = carregar_dados()
    treino, teste = split_temporal(df)

    colunas_features = [c for c in df.columns if c not in COLUNAS_NAO_FEATURES]

    X_treino = treino[colunas_features]
    y_treino = treino["team_a_venceu"]
    X_teste = teste[colunas_features]
    y_teste = teste["team_a_venceu"]

    cv_temporal = TimeSeriesSplit(n_splits=5)

    grelha_parametros = {
        "n_estimators": [50, 100, 150],
        "max_depth": [2, 3, 4],
        "learning_rate": [0.01, 0.05, 0.1],
    }

    modelo_base = XGBClassifier(
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )

    busca = GridSearchCV(
        modelo_base,
        grelha_parametros,
        cv=cv_temporal,
        scoring="neg_log_loss",
        n_jobs=-1,
    )

    print("A procurar os melhores hiperparametros (isto pode demorar 1-2 minutos)...")
    busca.fit(X_treino, y_treino)

    print(f"\nMelhores parametros encontrados: {busca.best_params_}")
    print(f"Melhor log loss medio (validacao cruzada): {-busca.best_score_:.3f}")

    melhor_modelo = busca.best_estimator_

    previsoes = melhor_modelo.predict(X_teste)
    probabilidades = melhor_modelo.predict_proba(X_teste)[:, 1]

    acc = accuracy_score(y_teste, previsoes)
    ll = log_loss(y_teste, probabilidades)

    print(f"\n=== Resultados do XGBoost afinado (no conjunto de teste final) ===")
    print(f"Accuracy: {acc:.3f}")
    print(f"Log Loss: {ll:.3f}")
    print(f"\nRelatorio detalhado:")
    print(classification_report(y_teste, previsoes, target_names=["team_b_venceu", "team_a_venceu"]))

    importancias = pd.DataFrame({
        "feature": colunas_features,
        "importancia": melhor_modelo.feature_importances_,
    }).sort_values("importancia", ascending=False)
    print("\nImportancia das features:")
    print(importancias.to_string(index=False))

    return melhor_modelo, teste, previsoes, probabilidades


if __name__ == "__main__":
    tunar_e_avaliar_xgboost()