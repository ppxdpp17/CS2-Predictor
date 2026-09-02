# 🎯 CS2 Tier-1 Predictor

Pipeline de Machine Learning que recolhe dados históricos e em tempo real da [HLTV.org](https://www.hltv.org), treina modelos preditivos, e mostra previsões ao vivo dos jogos profissionais de Counter-Strike 2 (equipas tier 1), num dashboard que atualiza automaticamente — 24/7, mesmo sem intervenção manual — e regista a accuracy real dos modelos ao longo do tempo.

## 🖼️ Demo

*(Adicionar aqui um screenshot ou GIF do dashboard depois de correres a app)*

## Porque este projeto

A generalidade dos "prediction models" de e-sports no GitHub sofrem de dois problemas: usam datasets pequenos/desatualizados, e não validam corretamente contra *data leakage* (usar informação do futuro para prever o passado). Este projeto foi construído com esses dois problemas como preocupação central desde o início — todo o pipeline de features respeita ordem cronológica estrita, e os 3 modelos são avaliados com split temporal (não aleatório).

## O que o projeto faz

1. **Scraping** — recolhe ~3000 encontros tier 1 de CS2 (2023-2026) da HLTV, incluindo dados ao nível de mapa e de jogador, ultrapassando proteção Cloudflare
2. **Feature Engineering** — Elo dinâmico por equipa, forma recente, head-to-head, sempre calculado sem *data leakage* (só usa informação disponível antes de cada jogo)
3. **Modelação** — 3 modelos comparados com rigor: Baseline Elo, Regressão Logística, XGBoost (com tuning via validação cruzada temporal)
4. **Dashboard ao vivo** — Streamlit, mostrando jogos ao vivo/futuros com previsões dos 3 modelos, agrupados por evento, com tooltips de lineup
5. **Tracking automático** — GitHub Actions corre de hora a hora, regista novas previsões e verifica resultados, para calcular a **accuracy real em produção** (não só em backtesting)

## Resultados (validação com holdout temporal)

| Modelo | Accuracy | Log Loss | Brier Score |
|---|---|---|---|
| Baseline (Elo mais alto ganha) | 61.3% | — | — |
| **Regressão Logística** | **63.2%** | **0.645** | **0.226** |
| XGBoost (afinado) | 61.3% | 0.645 | — |

A Regressão Logística é o modelo com melhor relação desempenho/simplicidade. Ver [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) para a análise completa e [`docs/METODOLOGIA.md`](docs/METODOLOGIA.md) para detalhes de cada decisão de design.

## Arquitetura

```
├── src/
│   ├── scraper/       # Recolha de dados da HLTV (histórico + tempo real)
│   ├── processing/     # Feature engineering, reconstrução de matches, previsões
│   └── models/          # Treino e avaliação dos 3 modelos
├── scripts/
│   └── atualizar_previsoes.py   # Corrido pelo GitHub Actions, de hora a hora
├── .github/workflows/           # Automação (scraping + tracking contínuo)
├── notebooks/                   # Análise exploratória
├── data/                        # Datasets processados + modelos treinados
└── app.py                       # Dashboard Streamlit
```

## Como correr localmente

```bash
git clone https://github.com/ppxdpp17/CS2-Predictor.git
cd cs2-tier1-predictor
python -m venv venv
venv\Scripts\Activate   # Windows
pip install -r requirements.txt

streamlit run app.py
```

**Nota sobre o cookie da Cloudflare:** o scraping em tempo real (jogos futuros) depende de um cookie `cf_clearance`, que precisa de ser renovado manualmente a cada alguns dias (ver [`docs/RENOVAR_COOKIE.md`](docs/RENOVAR_COOKIE.md)). O histórico de treino já está incluído no repositório, por isso o dashboard funciona mesmo sem cookie válido (só a secção "jogos futuros/ao vivo" fica indisponível até renovares).

## Limitações conhecidas

- Não incorpora dados de nível de jogador (testado, mas sem ganho mensurável sobre features de equipa - ver metodologia)
- Previsões por mapa são heurísticas simples (winrate histórico), não um modelo treinado - dados insuficientes ao nível de mapa individual
- Dependente de renovação manual periódica do cookie de sessão HLTV

## Stack

Python, pandas, scikit-learn, XGBoost, BeautifulSoup, Streamlit, GitHub Actions

## Licença

MIT