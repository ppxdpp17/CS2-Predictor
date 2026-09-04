"""
Dashboard do CS2 Predictor - mostra as previsoes de 3 modelos em
simultaneo (Baseline Elo, Regressao Logistica, XGBoost), com tracking
de accuracy real de cada um ao longo do tempo.

Corre com: streamlit run app.py
"""

import os
import sys
import base64
from datetime import datetime

import streamlit as st
import pandas as pd

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_BASE_DIR, "src", "processing"))
sys.path.append(os.path.join(_BASE_DIR, "src", "scraper"))

from predict_upcoming import gerar_previsoes
from fetcher import CookieExpiradoError
import track_predictions

def _imagem_para_base64(caminho: str) -> str:
    """Le um ficheiro de imagem e devolve a string base64, para
    podermos usa-la diretamente no CSS (o Streamlit nao serve
    ficheiros locais arbitrarios ao browser)."""
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode()


_CAMINHO_BACKGROUND = os.path.join(_BASE_DIR, "assets", "background.jpg")
_BACKGROUND_B64 = None
if os.path.exists(_CAMINHO_BACKGROUND):
    _BACKGROUND_B64 = _imagem_para_base64(_CAMINHO_BACKGROUND)


MODELOS_INFO = {
    "modelo1": {"nome": "Baseline Elo", "cor": "#8a8a8a"},
    "modelo2": {"nome": "Regressao Logistica", "cor": "#d13c3c"},
    "modelo3": {"nome": "XGBoost", "cor": "#2761d1"},
}

st.set_page_config(page_title="CS2 Predictor", page_icon="🎯", layout="centered")

st.markdown("""
<style>
    .stApp { color: #ffffff; }
    .cs2-header {
        background: linear-gradient(90deg, #1a1a2e 0%, #16162a 100%);
        border: 1px solid #6c4de6; border-radius: 8px;
        padding: 16px 24px; margin-bottom: 8px;
        font-size: 28px; font-weight: 800; letter-spacing: 1px;
    }
    .match-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #211f36 100%);
        border: 1px solid #2e2b4a; border-radius: 10px;
        padding: 18px 22px; margin-bottom: 14px;
    }
    .match-meta { color: #9d9ac2; font-size: 13px; margin-bottom: 10px; }
    .team-row {
        display: flex; justify-content: space-between;
        font-size: 18px; font-weight: 700; margin-bottom: 10px;
    }
    .team-name { cursor: help; border-bottom: 1px dotted #6c4de6; }
    .modelo-label { font-size: 12px; color: #9d9ac2; margin-bottom: 2px; }
    .prob-bar-container {
        position: relative; width: 100%; height: 18px;
        border-radius: 4px; overflow: hidden;
        background: #2761d1; margin: 4px 0 10px 0;
    }
    .prob-bar-fill { position: absolute; left: 0; top: 0; bottom: 0; background: #d13c3c; }
    .prob-bar-marker { position: absolute; top: 0; bottom: 0; width: 3px; background: #000000; }
    .prob-labels { display: flex; justify-content: space-between; font-size: 13px; color: #cfcfe8; }
    .live-badge {
        background: #d13c3c; color: white; font-weight: 700;
        font-size: 12px; padding: 2px 8px; border-radius: 4px;
    }
    .acertou-icone { font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# Bloco de CSS separado, isolado, so para a imagem de fundo -
# evita misturar f-strings com o bloco de CSS grande (chavetas do CSS
# conflituam com a sintaxe de f-string do Python).
if _BACKGROUND_B64:
    _regra_background = (
        'background: linear-gradient(rgba(14,14,22,0.88), rgba(14,14,22,0.88)), '
        'url("data:image/jpg;base64,' + _BACKGROUND_B64 + '") center/cover fixed no-repeat;'
    )
    st.markdown(
        "<style>.stApp { " + _regra_background + " }</style>",
        unsafe_allow_html=True,
    )

st.markdown('<div class="cs2-header">🎯 CS2 PREDICTOR</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Controlos")
    if st.button("🔄 Atualizar agora", use_container_width=True):
        st.cache_data.clear()

    auto_refresh = st.checkbox("Atualizacao automatica (a cada 5 min)", value=False)
    if auto_refresh:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh_timer")

    st.markdown("---")
    st.caption(
        "⚠️ Depende de um cookie de sessao (cf_clearance) que expira "
        "periodicamente. Renova-o no .env se as previsoes pararem."
    )


@st.cache_data(ttl=300)
def carregar_previsoes():
    return gerar_previsoes()


try:
    df = carregar_previsoes()
except CookieExpiradoError:
    st.error(
        "🍪 Cookie de sessao expirado. Renova o `cf_clearance` em "
        "`src/scraper/.env` e clica em 'Atualizar agora'."
    )
    st.stop()
except Exception as erro:
    st.error(f"Erro inesperado: {erro}")
    st.stop()

if len(df) > 0:
    track_predictions.registar_previsoes(df)
track_predictions.verificar_resultados()
estatisticas = track_predictions.obter_estatisticas()

st.caption(f"Ultima atualizacao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
           f"| {estatisticas['total_resolvidos']} de {estatisticas['total_previsoes']} previsoes confirmadas")

cols = st.columns(3)
for i, (chave, info) in enumerate(MODELOS_INFO.items()):
    acc = estatisticas.get(f"accuracy_{chave}")
    cols[i].metric(info["nome"], f"{acc:.1%}" if acc is not None else "—")

st.markdown("---")

df_ao_vivo = df[df["ao_vivo"]] if len(df) > 0 else pd.DataFrame()
df_futuros = df[~df["ao_vivo"]] if len(df) > 0 else pd.DataFrame()
log = track_predictions.carregar_log()
df_passados = log[log["resultado_real"].notna()].sort_values("data_hora_jogo", ascending=False)


def _placar_previsto(prob1, formato):
    """Converte uma probabilidade num placar previsto tipo '2-1'.
    Heuristica simples: quanto mais desequilibrada a probabilidade,
    mais "confortavel" se assume a vitoria (2-0 em vez de 2-1)."""
    formato_str = str(formato).lower()
    max_mapas = 3 if "bo3" in formato_str else (5 if "bo5" in formato_str else 1)
    vencedor_e_team1 = prob1 >= 0.5
    prob_favorito = prob1 if vencedor_e_team1 else (1 - prob1)

    if max_mapas == 1:
        placar = "1-0"
    elif max_mapas == 3:
        placar = "2-0" if prob_favorito >= 0.62 else "2-1"
    else:  # bo5
        if prob_favorito >= 0.70:
            placar = "3-0"
        elif prob_favorito >= 0.55:
            placar = "3-1"
        else:
            placar = "3-2"

    if vencedor_e_team1:
        return placar
    else:
        # inverter o placar para refletir que quem ganha e a team2
        a, b = placar.split("-")
        return f"{b}-{a}"


def _tooltip_jogadores(nome_equipa, jogadores):
    if isinstance(jogadores, str):
        jogadores = []
    lista = ", ".join(jogadores) if jogadores else "Lineup desconhecido"
    return f'<span class="team-name" title="{lista}">{nome_equipa}</span>'


def mostrar_cartao_jogo(jogo):
    status_html = (
        '<span class="live-badge">AO VIVO</span>' if jogo["ao_vivo"]
        else f'🕐 {pd.Timestamp(jogo["data_hora"]).strftime("%d/%m %H:%M")}'
    )

    partes_html = []
    partes_html.append('<div class="match-card">')
    partes_html.append(f'<div class="match-meta">{status_html} &nbsp;|&nbsp; {str(jogo["formato"]).upper()} &nbsp;|&nbsp; {jogo.get("evento_nome", "")}</div>')
    partes_html.append('<div class="team-row">')
    partes_html.append(f'<div>{_tooltip_jogadores(jogo["team1_nome"], jogo.get("team1_jogadores", []))}</div>')
    partes_html.append(f'<div>{_tooltip_jogadores(jogo["team2_nome"], jogo.get("team2_jogadores", []))}</div>')
    partes_html.append('</div>')

    for chave, info in MODELOS_INFO.items():
        prob1 = jogo[f"prob1_{chave}"]
        prob1_pct = round(prob1 * 100, 1)
        placar = _placar_previsto(prob1, jogo["formato"])
        equipa_favorita = jogo["team1_nome"] if prob1 >= 0.5 else jogo["team2_nome"]

        partes_html.append(f'<div class="modelo-label">{info["nome"]} — previsto: <strong>{placar}</strong> ({equipa_favorita})</div>')
        partes_html.append(f'<div class="prob-bar-container"><div class="prob-bar-fill" style="width:{prob1_pct}%;"></div><div class="prob-bar-marker" style="left:{prob1_pct}%;"></div></div>')
        partes_html.append(f'<div class="prob-labels"><span>{jogo[f"prob1_{chave}"]:.1%}</span><span>{jogo[f"prob2_{chave}"]:.1%}</span></div>')

    previsoes_mapa = jogo.get("previsoes_mapa", [])
    if isinstance(previsoes_mapa, list) and len(previsoes_mapa) > 0:
        partes_html.append('<div style="margin-top:10px; padding-top:10px; border-top:1px dashed #3a3760;">')
        partes_html.append('<div style="font-size:12px; color:#9d9ac2; margin-bottom:8px;">Previsoes por mapa (extrapolacao: avaliacao geral de cada modelo ajustada por winrate historico nesse mapa - nao e um modelo treinado ao nivel de mapa)</div>')
        for previsao in previsoes_mapa:
            partes_html.append(f'<div style="font-weight:700; font-size:14px; margin-top:6px;">{previsao["mapa"]}</div>')
            for chave, info in MODELOS_INFO.items():
                prob_mapa = previsao["previsoes_por_modelo"][chave]
                vencedor_mapa = jogo["team1_nome"] if prob_mapa >= 0.5 else jogo["team2_nome"]
                prob_pct = round(prob_mapa * 100, 1)
                partes_html.append(f'<div style="display:flex; justify-content:space-between; font-size:13px; color:#cfcfe8; padding:2px 0;"><span>{info["nome"]}: {vencedor_mapa}</span><span>{max(prob_mapa, 1-prob_mapa):.1%}</span></div>')
        partes_html.append('</div>')

    partes_html.append('</div>')

    html_final = "".join(partes_html)
    st.markdown(html_final, unsafe_allow_html=True)


aba_ao_vivo, aba_eventos, aba_futuros, aba_passados = st.tabs([
    f"🔴 Jogos Live ({len(df_ao_vivo)})",
    "🏆 Eventos Futuros",
    f"🕐 Próximos Jogos ({len(df_futuros)})",
    f"✅ Resultados Passados ({len(df_passados)})",
])

with aba_ao_vivo:
    if len(df_ao_vivo) == 0:
        st.info("Nenhum jogo ao vivo neste momento entre equipas conhecidas.")
    for _, jogo in df_ao_vivo.iterrows():
        mostrar_cartao_jogo(jogo)

with aba_eventos:
    if len(df_futuros) == 0:
        st.info("Sem eventos futuros com jogos conhecidos.")
    else:
        for evento_nome, grupo in df_futuros.groupby("evento_nome"):
            with st.expander(f"🏆 {evento_nome} ({len(grupo)} jogos)", expanded=False):
                for _, jogo in grupo.iterrows():
                    mostrar_cartao_jogo(jogo)

with aba_futuros:
    if len(df_futuros) == 0:
        st.info("Nenhum jogo futuro encontrado neste momento entre equipas conhecidas.")
    for _, jogo in df_futuros.iterrows():
        mostrar_cartao_jogo(jogo)

with aba_passados:
    if len(df_passados) == 0:
        st.info("Ainda sem resultados confirmados.")
    for _, linha in df_passados.iterrows():
        icones = " ".join(
            f'{MODELOS_INFO[m]["nome"]}: {"✅" if linha[f"acertou_{m}"] else "❌"}'
            for m in MODELOS_INFO
        )
        data_fmt = pd.Timestamp(linha["data_hora_jogo"]).strftime("%d/%m/%Y %H:%M")
        html_passado = (
            f'<div class="match-card">'
            f'<div class="match-meta">{data_fmt}</div>'
            f'<div class="team-row"><div>{linha["team1_nome"]} vs {linha["team2_nome"]}</div></div>'
            f'<div style="color:#cfcfe8; font-size:14px; margin-bottom:6px;">Resultado real: {linha["resultado_real"]}</div>'
            f'<div style="font-size:14px;">{icones}</div>'
            f'</div>'
        )
        st.markdown(html_passado, unsafe_allow_html=True)

st.caption(
    "3 modelos comparados em producao: Baseline Elo, Regressao Logistica "
    "e XGBoost, todos treinados com dados historicos de encontros tier 1 (2023-2026)."
)