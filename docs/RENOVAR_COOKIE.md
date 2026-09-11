# How to Renew the HLTV Session Cookie

Live scraping (upcoming/live games) relies on a `cf_clearance` cookie, which proves to Cloudflare that the HTTP request originates from a human-validated browser session. This cookie expires periodically.

## Symptoms of Expiry

- The Streamlit dashboard displays a "Session cookie expired" warning.
- GitHub Actions workflows fail (marked with ❌ in the repository's **Actions** tab).

## Steps to Renew

1. Open `https://www.hltv.org/matches` in a standard desktop browser (Chrome/Edge/Firefox).
2. Complete any Cloudflare security verification until the page loads fully.
3. Open DevTools (**F12**) → Navigate to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox).
4. Under **Cookies** in the left sidebar, select `https://www.hltv.org`.
5. Copy the value of the **`cf_clearance`** key.

## Updating the Cookie Value

### 1. Local Environment
Update `src/scraper/.env`:
```env
CF_CLEARANCE=<your-new-cookie-value-here>
USER_AGENT=<your-current-browser-user-agent-here>
```

### 2. GitHub Actions Automation
1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**.
2. Update the `CF_CLEARANCE` secret (and `USER_AGENT` if changed).
3. *(Optional)* Manually trigger a run under **Actions** → **Run workflow** to verify immediate success without waiting for the next scheduled run.