"""
Modulo responsavel por ir buscar paginas da HLTV de forma robusta.

Estrategia: reutilizar um cookie 'cf_clearance' obtido manualmente
ao resolver o desafio da Cloudflare num browser normal. As credenciais
vivem no ficheiro .env (fora do git) por seguranca.

IMPORTANTE: quando o cookie expirar (normalmente algumas horas),
os pedidos voltam a dar 403 / pagina "Um momento...". Nesse caso:
1. Abre o URL num browser normal e resolve o desafio
2. Copia o novo valor de cf_clearance (DevTools > Application > Cookies)
3. Atualiza o ficheiro .env
"""

import os
import time
import random
import requests
from dotenv import load_dotenv

# Apontamos explicitamente para o .env na pasta deste ficheiro
# (src/scraper/), em vez de deixar o load_dotenv() adivinhar - isso
# evita falhas quando o script e corrido a partir de outra pasta
# (ex: src/processing, ou a raiz do projeto via streamlit).
_CAMINHO_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_CAMINHO_ENV)


class CookieExpiradoError(Exception):
    """Levantada quando o cf_clearance deixou de ser valido."""
    pass


CF_CLEARANCE = os.getenv("CF_CLEARANCE")
USER_AGENT = os.getenv("USER_AGENT")

if not CF_CLEARANCE or not USER_AGENT:
    raise RuntimeError(
        "CF_CLEARANCE ou USER_AGENT nao encontrados. "
        "Confirma que o ficheiro .env existe em src/scraper/ e tem "
        "ambas as variaveis definidas."
    )

_session = requests.Session()
_session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
})
_session.cookies.set("cf_clearance", CF_CLEARANCE, domain=".hltv.org")


def fetch_page(url: str, max_retries: int = 3, base_delay: float = 3.0):
    """
    Vai buscar o HTML de uma pagina usando a sessao com cookie valido.

    Devolve o HTML (string) se conseguir, ou None se falhar
    depois de todas as tentativas.
    """
    for tentativa in range(1, max_retries + 1):
        try:
            response = _session.get(url, timeout=15)
        except Exception as erro:
            print(f"  [tentativa {tentativa}] erro de rede: {erro}")
            response = None

        if response is not None and response.status_code == 200:
            if "Um momento" in response.text[:1000] or "Just a moment" in response.text[:1000]:
                print(f"  [tentativa {tentativa}] cookie expirado ou bloqueado (challenge page)")
                print("  >>> Provavelmente precisas de renovar o cf_clearance no .env <<<")
                # Nao vale a pena continuar a tentar com o mesmo cookie invalido.
                # Sinalizamos isto de forma especial para quem chama a funcao
                # poder decidir parar tudo em vez de desperdicar mais tentativas.
                raise CookieExpiradoError(url)
            else:
                return response.text

        elif response is not None:
            print(f"  [tentativa {tentativa}] status code inesperado: {response.status_code}")

        espera = base_delay * tentativa + random.uniform(0, 2)
        print(f"  a aguardar {espera:.1f}s antes de tentar de novo...")
        time.sleep(espera)

    print(f"  FALHOU depois de {max_retries} tentativas: {url}")
    return None


def gentle_pause(min_seconds: float = 2.5, max_seconds: float = 5.0) -> None:
    """Pausa aleatoria entre pedidos normais (nao apos falhas)."""
    time.sleep(random.uniform(min_seconds, max_seconds))