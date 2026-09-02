# Como renovar o cookie da HLTV

O scraping em tempo real (jogos futuros/ao vivo) depende de um cookie
`cf_clearance`, que prova à Cloudflare que o pedido vem de uma sessão
já validada por um humano. Este cookie expira periodicamente
(observado: durou ~4 dias numa sessão de teste, mas pode variar).

## Sintoma de que precisa de renovação

- O dashboard mostra um erro "Cookie de sessão expirado"
- O GitHub Action (separador "Actions" do repositório) aparece com ❌

## Passos para renovar

1. Abre `https://www.hltv.org/matches` num browser normal (Chrome/Edge/Firefox)
2. Resolve a verificação de segurança até a página carregar por completo
3. Abre as DevTools (F12) → separador **Application** (Chrome/Edge) ou
   **Storage** (Firefox)
4. No menu lateral: **Cookies** → `https://www.hltv.org`
5. Copia o valor da linha **`cf_clearance`**

## Onde colocar o novo valor

### Se estiveres a correr localmente
Atualiza `src/scraper/.env`:
```
CF_CLEARANCE=<o-novo-valor-aqui>
USER_AGENT=<o-teu-user-agent>
```

### Para o GitHub Action continuar a funcionar
1. Vai ao repositório no GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Edita o secret `CF_CLEARANCE` com o novo valor
3. (Opcional) Corre o workflow manualmente: separador **Actions** →
   "Atualizar previsoes CS2" → **Run workflow**, para confirmar que
   voltou a funcionar sem esperar pela próxima hora agendada