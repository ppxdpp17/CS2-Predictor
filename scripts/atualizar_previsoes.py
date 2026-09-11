"""
Script standalone, pensado para ser corrido periodicamente pelo GitHub Actions.

Este procura jogos futuros, gera previsões dos 3 modelos, regista-as no log, 
e verifica se jogos anteriores já terminaram (atualizando a accuracy real).

Termina com codigo de saída 1 se o cookie estiver expirado, para que
o GitHub Actions marque a execucao como "falhada". Caso isto aconteça, 
é preciso renovar o cf_clearance.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(_ROOT, "src", "processing"))
sys.path.append(os.path.join(_ROOT, "src", "scraper"))
sys.path.append(os.path.join(_ROOT, "src", "models"))

from predict_upcoming import gerar_previsoes
from fetcher import CookieExpiradoError
import track_predictions


def main():
    print("=== Atualizacao automatica de previsoes ===")

    try:
        df = gerar_previsoes()
    except CookieExpiradoError:
        print("ERRO: cookie de sessao (cf_clearance) expirado.")
        print("Renova o secret CF_CLEARANCE nas definicoes do repositorio GitHub.")
        sys.exit(1)
    except Exception as erro:
        print(f"ERRO inesperado ao gerar previsoes: {erro}")
        sys.exit(1)

    if len(df) > 0:
        track_predictions.registar_previsoes(df)
        print(f"Previsoes registadas para {len(df)} jogos.")
    else:
        print("Nenhum jogo futuro/ao vivo encontrado neste momento.")

    try:
        resolvidos = track_predictions.verificar_resultados()
        print(f"{resolvidos} previsoes resolvidas com resultado real.")
    except CookieExpiradoError:
        print("ERRO: cookie expirado ao verificar resultados.")
        sys.exit(1)

    estatisticas = track_predictions.obter_estatisticas()
    print("\n--- Estatisticas atuais ---")
    for chave, valor in estatisticas.items():
        print(f"{chave}: {valor}")

    print("\nConcluido com sucesso.")


if __name__ == "__main__":
    main()