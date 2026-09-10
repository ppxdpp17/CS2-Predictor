# Metodologia

Este documento explica as principais decisões de design do projeto,
incluindo testes que não tiveram resultados positivos (documentados
por transparência).

## 1. Recolha de dados

Dados recolhidos de `hltv.org/stats/matches`, filtrados para equipas
Top 30 do ranking HLTV, apenas no CS2, desde 04/10/2023. Ultrapassar a
proteção Cloudflare exigiu autenticação via cookie `cf_clearance`
obtido manualmente (ver `docs/RENOVAR_COOKIE.md`).

- 6822 mapas individuais recolhidos na recolha inicial
- Reconstruídos em 3025 encontros completos (Bo1/Bo3/Bo5), agrupando
  mapas por proximidade temporal (não por "mesmo dia", que causava
  fusão incorreta de encontros distintos)
- 5 encontros excluídos por resultado empatado no scoreboard (decisões
  arbitrais/forfeits não capturáveis a partir dos dados de mapa - ver
  caso documentado: mapa anulado por uso de "Snap Tap" banido)
- **Total inicial: 3020 encontros válidos.** Este número já não é
  fixo - o dataset cresce automaticamente todos os dias (ver secção 8)

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

## 3. Modelos testados (avaliação com holdout temporal)

| Modelo | Accuracy | Log Loss | Notas |
|---|---|---|---|
| Baseline (Elo mais alto ganha) | 61.3% | — | Ponto de referência |
| **Regressão Logística** | **63.2%** | **0.645** | Melhor resultado |
| XGBoost (tuning via GridSearchCV + TimeSeriesSplit) | 61.3% | 0.645 | Convergiu para hiperparâmetros mínimos (max_depth=2), sinal de que mais complexidade não ajuda com este volume de dados |
| Regressão Logística + features de jogador (rating, roster) | 62.1% | 0.644 | Sem ganho mensurável - redundante com Elo de equipa |
| Regressão Logística + estabilidade de roster (isolada) | 63.1% | 0.646 | Sem ganho, mesmo isolando este sinal de outras features de jogador (ver `src/experiments/test_roster_stability.py`) |

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
já eleva o Elo). O rating médio da lineup e a estabilidade de roster
mostraram coeficientes não-triviais no modelo, mas redundantes com
informação já presente no Elo. Testado de duas formas independentes
(combinado com outras features, e isolado) - ambas sem ganho
mensurável face ao Elo de equipa sozinho.

## 6. Limitações conhecidas

- Sem dados de composição de armas/economia por round
- Previsões por mapa (dashboard) são heurísticas/extrapolações, não
  um modelo treinado ao nível de mapa - dados insuficientes para
  treino robusto sem overfitting (ver secção 7)
- Dependente de renovação manual periódica do cookie de sessão HLTV
  (ver `docs/RENOVAR_COOKIE.md`)

## 7. Arquitetura de produção

Ao contrário da avaliação (secção 3), que usa um split temporal 80/20
para validação honesta, o **modelo de produção** é treinado com 100%
dos dados disponíveis a cada momento - não há "conjunto de teste"
reservado em produção, porque o objetivo já não é avaliar, é
maximizar o sinal disponível para previsões reais.

O dashboard mostra em simultâneo as previsões de **3 modelos**:
Baseline Elo, Regressão Logística, e XGBoost (mesmos hiperparâmetros
da secção 3) - permitindo comparação visual direta e tracking
independente da accuracy real de cada um ao longo do tempo (ver
secção 8).

### Previsões por mapa (extrapolação, não modelo treinado)

Quando os mapas de um encontro já foram revelados pelo veto (visível
via atributo `data-maps` na página de listagem da HLTV), o dashboard
mostra uma estimativa adicional por mapa, para cada um dos 3 modelos.
**Importante:** isto não é um modelo treinado ao nível de mapa - é
uma extrapolação, combinando (via média em log-odds) a avaliação
geral de cada modelo sobre o encontro com o winrate histórico de
cada equipa nesse mapa específico. Está claramente identificado como
tal na interface, para não ser confundido com uma previsão genuína
treinada.

### Deteção de stand-ins

Os rosters mostrados no dashboard (tooltip ao passar o rato sobre o
nome da equipa) são obtidos por 3 camadas de fallback:
1. Lineup confirmado especificamente para o encontro (inclui
   stand-ins), obtido da página do próprio jogo
2. Roster oficial da equipa (página geral da equipa), se o lineup do
   jogo ainda não estiver confirmado
3. Lista vazia, como último recurso

## 8. Automação e crescimento do dataset

Dois workflows do GitHub Actions mantêm o sistema a funcionar sem
intervenção manual (exceto renovação ocasional do cookie):

- **De hora a hora**: regista novas previsões dos jogos futuros/ao
  vivo, e verifica se jogos anteriores já têm resultado confirmado -
  permitindo calcular a **accuracy real em produção** de cada modelo,
  distinta da accuracy de backtesting (secção 3). Consultável em
  tempo real no separador "Resultados Passados" do dashboard.
- **Diariamente**: verifica se há mapas novos na HLTV desde a última
  recolha, atualiza o dataset histórico, e re-treina os 2 modelos de
  produção (Regressão Logística e XGBoost) com os dados mais
  recentes. O dataset cresce continuamente - o número reportado na
  secção 1 (3020) é o valor da recolha inicial, não um valor fixo.