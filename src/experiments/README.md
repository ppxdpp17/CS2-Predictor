# Experiments

Scripts documenting hypotheses tested throughout the project that were **not** integrated into the final production pipeline. Maintained for methodological transparency — see [`docs/METODOLOGIA.md`](file:///c:/Users/Pedro/Desktop/pp/Projetos/CS2%20Predictor/docs/METODOLOGIA.md) for detailed results and conclusions.

- `test_roster_stability.py` — Evaluates in isolation whether roster stability (whether the team maintained the exact same lineup from the previous match) adds incremental predictive signal. **Result**: No measurable gain over team Elo alone.
- `train_with_players.py` — Tests player-level features (average lineup rating, roster stability) combined with team-level features. **Result**: No measurable gain compared to team Elo alone.
- `collect_players.py` / `parse_players.py` — Scripts that built the initial `jogadores_por_match.csv` dataset used in the experiments above. Deprecated for production — the live dashboard uses `src/processing/team_rosters.py` to fetch active rosters directly from HLTV.