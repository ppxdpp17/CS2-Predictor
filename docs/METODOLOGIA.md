# Metodologia

Este documento explica as principais decisões de design do projeto,
incluindo testes que não tiveram resultados positivos (documentados por transparência).

## 1. Recolha de dados

Dados recolhidos de `hltv.org/stats/matches`, filtrados para equipas
Top 30 do ranking HLTV, apenas no CS2, desde 04/10/2023. Ultrapassar a
proteção Cloudflare exigiu autenticação via cookie `cf_clearance`
obtido manualmente (ver `docs/RENOVAR_COOKIE.md`).

- 6822 mapas individuais recolhidos
- Reconstruídos em 3025 encontros completos (Bo1/Bo3/Bo5), agrupando
  mapas por proximidade temporal (não por "mesmo dia", que causava
  fusão incorreta de encontros distintos)
- 5 encontros excluídos por resultado empatado no scoreboard (decisões
  arbitrais/forfeits não capturáveis a partir dos dados de mapa - ver
  caso documentado: mapa anulado por uso de "Snap Tap" banido)

## 2. Prevenção de data leakage

Regra seguida em todo o pipeline: para prever o jogo do dia D, só se
utiliza informação disponível **antes** de D. Isto implica:

- Processamento estritamente cronológico na construção de features
  (Elo, forma recente, head-to-head)
- Split treino/teste temporal (não aleatório) - treino com os
  primeiros 80% dos jogos por data, teste com os últimos 20%
- A feature de winrate por mapa foi **removida do modelo de produção**,
  porque depende de saber que mapas vão ser jogados - informação que
  só existe depois do veto, não disponível ao prever jogos futuros

## 3. Modelos testados

| Modelo | Accuracy | Log Loss | Notas |
|---|---|---|---|
| Baseline (Elo mais alto ganha) | 61.3% | — | Ponto de referência |
| Regressão Logística | 63.2% | 0.645 | Melhor resultado |
| XGBoost (tuning via GridSearchCV + TimeSeriesSplit) | 61.3% | 0.645 | Convergiu para hiperparâmetros mínimos (max_depth=2), sinal de que mais complexidade não ajuda com este volume de dados |
| Regressão Logística + features de jogador | 62.1% | 0.644 | Sem ganho mensurável - redundante com Elo de equipa |

**Conclusão:** a Regressão Logística foi escolhida como modelo
principal por ter o melhor (ou empatado) desempenho em todas as
métricas, sendo também mais simples e interpretável.

## 4. Validação de calibração

Curva de calibração e Brier Score (0.226, vs. 0.25 de um modelo que
prevê sempre 50%) confirmam que as probabilidades produzidas são
razoavelmente confiáveis, não só a classificação binária.

## 5. Por que features de jogador não ajudaram

Hipótese: o Elo de equipa já captura implicitamente a qualidade dos
jogadores (equipas com jogadores fortes tendem a vencer mais, o que
já eleva o Elo). O rating médio da lineup mostrou coeficiente não-
trivial no modelo, mas redundante com informação já presente.

## 6. Limitações conhecidas

- Dataset cobre ~3 anos (desde o lançamento do CS2) - relativamente
  pequeno para modelos de maior capacidade mostrarem vantagem
- Sem dados de composição de armas/economia por round
- Previsões por mapa (dashboard) são heurísticas simples de winrate
  histórico, não um modelo treinado - dados insuficientes ao nível de
  mapa individual para treino robusto sem overfitting