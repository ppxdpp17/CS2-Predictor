"""
Cresce o dataset histórico automaticamente: verifica se há jogos novos (que não estão atualmente no dataset)
(tier 1, Top30) desde a última recolha, adiciona-os ao mapas_raw.csv, reconstrói matches_clean.csv e features_dataset.csv, 
e re-treina os modelos de produção.

Pensado para correr periodicamente via GitHub Actions, sem
intervenção manual (exceto a renovação ocasional do cookie).
"""

import os
import sys

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(_ROOT, "src", "scraper"))
sys.path.append(os.path.join(_ROOT, "src", "processing"))
sys.path.append(os.path.join(_ROOT, "src", "models"))

from fetcher import fetch_page, gentle_pause, CookieExpiradoError
from parse_map_stats import parse_pagina_stats, BASE_URL
from build_matches import construir_matches
from build_features import construir_features
from train_production_model import treinar_modelo_producao
from train_production_xgboost import treinar_modelo_producao_xgb

_DATA_DIR = os.path.join(_ROOT, "data")
CAMINHO_MAPAS_RAW = os.path.join(_DATA_DIR, "mapas_raw.csv")


def buscar_mapas_novos(por_pagina: int = 50, max_paginas: int = 20) -> int:
    """
    Percorre as páginas mais recentes de stats/matches e adiciona ao
    mapas_raw.csv qualquer mapstat_id que ainda nao conheçamos.

    Pára assim que uma página inteira só tiver mapas já conhecidos.

    Devolve o número de mapas novos adicionados.
    """
    df_existente = pd.read_csv(CAMINHO_MAPAS_RAW)
    ids_conhecidos = set(df_existente["mapstat_id"].astype(str))

    novos_total = []

    for pagina in range(max_paginas):
        offset = pagina * por_pagina
        url = f"{BASE_URL}&offset={offset}"
        print(f"A verificar pagina {pagina + 1} (offset={offset})...")

        html = fetch_page(url)  # deixa CookieExpiradoError propagar para o main()
        if html is None:
            print("  Falhou a aceder a pagina, a parar por seguranca.")
            break

        mapas = parse_pagina_stats(html)
        novos_nesta_pagina = [m for m in mapas if str(m["mapstat_id"]) not in ids_conhecidos]

        print(f"  {len(mapas)} mapas na pagina, {len(novos_nesta_pagina)} novos.")

        if len(novos_nesta_pagina) == 0:
            print("  Pagina inteira ja conhecida - apanhou tudo o que faltava.")
            break

        novos_total.extend(novos_nesta_pagina)
        ids_conhecidos.update(str(m["mapstat_id"]) for m in novos_nesta_pagina)

        gentle_pause()

    if novos_total:
        df_novos = pd.DataFrame(novos_total)
        df_atualizado = pd.concat([df_existente, df_novos], ignore_index=True)
        df_atualizado.to_csv(CAMINHO_MAPAS_RAW, index=False)
        print(f"\n{len(novos_total)} mapas novos adicionados ao mapas_raw.csv.")
    else:
        print("\nNenhum mapa novo encontrado.")

    return len(novos_total)


def main():
    try:
        num_novos = buscar_mapas_novos()
    except CookieExpiradoError:
        print("ERRO: cookie expirado. Renova o CF_CLEARANCE.")
        sys.exit(1)

    if num_novos == 0:
        print("Dataset ja atualizado - nada a re-treinar.")
        return

    print("\nA reconstruir matches_clean.csv...")
    construir_matches(
        caminho_entrada=os.path.join(_DATA_DIR, "mapas_raw.csv"),
        caminho_saida=os.path.join(_DATA_DIR, "matches_clean.csv"),
    )

    print("\nA reconstruir features_dataset.csv...")
    construir_features(
        caminho_matches=os.path.join(_DATA_DIR, "matches_clean.csv"),
        caminho_saida=os.path.join(_DATA_DIR, "features_dataset.csv"),
    )

    print("\nA re-treinar modelo 'Regressao Logistica'...")
    treinar_modelo_producao()

    print("\nA re-treinar modelo 'XGBoost'...")
    treinar_modelo_producao_xgb()

    print("\nPipeline de atualizacao concluido com sucesso.")


if __name__ == "__main__":
    main()