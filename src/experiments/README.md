# Experiências

Scripts que documentam hipóteses testadas ao longo do projeto que
**não** entraram no pipeline final de produção. Mantidos por
transparência metodológica - ver `docs/METODOLOGIA.md` para os
resultados e conclusões.

- `test_roster_stability.py` - testa isoladamente se a estabilidade
  de roster (equipa manteve o mesmo lineup do jogo anterior?)
  acrescenta sinal preditivo. Resultado: sem ganho mensurável.
- `train_with_players.py` - testa features de nível de jogador
  (rating médio da lineup, estabilidade de roster) combinadas com
  as features de equipa. Resultado: sem ganho mensurável face ao
  Elo de equipa sozinho.
- `collect_players.py` / `parse_players.py` - scripts que construíram
  o `jogadores_por_match.csv` original (usado nas experiências acima).
  Já não correm em produção - o dashboard usa `team_rosters.py` para
  ir buscar rosters atuais diretamente à HLTV.