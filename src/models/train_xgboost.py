"""
Segundo modelo: XGBoost (Gradient Boosting).

Reutiliza a mesma logica de carregamento/split do baseline, para
garantir uma comparacao justa (mesmos dados de treino/teste, mesmas
features). A diferenca esta so no algoritmo de aprendizagem.
"""

import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss, classification_report

from train_baseline import carregar_dados, split_temporal, COLUNAS_NAO_FEATURES


def treinar_e_avaliar_xgboost():
    df = carregar_dados()
    treino, teste = split_temporal(df)

    colunas_features = [c for c in df.columns if c not in COLUNAS_NAO_FEATURES]

    X_treino = treino[colunas_features]
    y_treino = treino["team_a_venceu"]
    X_teste = teste[colunas_features]
    y_teste = teste["team_a_venceu"]

    # XGBoost nao precisa de StandardScaler - arvores de decisao sao
    # invariantes a escala (nao importa se uma feature vai de 0 a 1
    # e outra de -1000 a 1000, o algoritmo lida bem com isso).
    modelo = XGBClassifier(
        n_estimators=200,      # numero de arvores
        max_depth=4,           # profundidade maxima de cada arvore (controla complexidade)
        learning_rate=0.05,    # o quanto cada arvore nova corrige as anteriores
        subsample=0.8,         # usa 80% dos dados por arvore (reduz overfitting)
        colsample_bytree=0.8,  # usa 80% das features por arvore (idem)
        eval_metric="logloss",
        random_state=42,       # garante resultados reproduziveis
    )
    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict(X_teste)
    probabilidades = modelo.predict_proba(X_teste)[:, 1]

    acc = accuracy_score(y_teste, previsoes)
    ll = log_loss(y_teste, probabilidades)

    print(f"\n=== Resultados do modelo (XGBoost) ===")
    print(f"Accuracy: {acc:.3f}")
    print(f"Log Loss: {ll:.3f}")
    print(f"\nRelatorio detalhado:")
    print(classification_report(y_teste, previsoes, target_names=["team_b_venceu", "team_a_venceu"]))

    importancias = pd.DataFrame({
        "feature": colunas_features,
        "importancia": modelo.feature_importances_,
    }).sort_values("importancia", ascending=False)
    print("\nImportancia das features:")
    print(importancias.to_string(index=False))

    return modelo, teste, previsoes, probabilidades


if __name__ == "__main__":
    treinar_e_avaliar_xgboost()