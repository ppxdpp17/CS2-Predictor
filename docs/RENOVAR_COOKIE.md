# Como renovar o cookie da HLTV

O scraping em tempo real (jogos futuros/ao vivo) depende de um cookie
`cf_clearance`, que prova à Cloudflare que o pedido vem de uma sessão
já validada por um humano. Este cookie expira periodicamente.

## Sintoma de que precisa de renovação

- O dashboard mostra um erro "Cookie de sessão expirado"
- O GitHub Action (separador "Actions" do repositório) aparece com ❌

## Passos para renovar

1. Abrir `https://www.hltv.org/matches` num browser normal (Chrome/Edge/Firefox)
2. Resolver a verificação de segurança até a página carregar por completo
3. Abrir as DevTools (F12) → separador **Application** (Chrome/Edge) ou
   **Storage** (Firefox)
4. No menu lateral: **Cookies** → `https://www.hltv.org`
5. Copiar o valor da linha **`cf_clearance`**

## Onde colocar o novo valor

### Se estiver a correr localmente
Atualizar `src/scraper/.env`:
```
CF_CLEARANCE=<o-novo-valor-aqui>
USER_AGENT=<o-user-agent-atual-aqui>
```

### Para o GitHub Action continuar a funcionar
1. Ir ao repositório no GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Atualizar o secret `CF_CLEARANCE`
3. (Opcional) Correr o workflow manualmente: separador **Actions** →
   "Atualizar previsoes CS2" → **Run workflow**, para confirmar que
   voltou a funcionar sem esperar pela próxima hora agendada