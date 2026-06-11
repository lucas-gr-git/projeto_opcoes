"""
Dashboard de Mercado — Macro, maiores altas/baixas via BRAPI
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Dashboard | RCO", page_icon="🏠", layout="wide")

st.markdown("""
<style>
.macro-card {
    background: #1a1d27; border-radius: 12px; padding: 1.1rem 1.2rem;
    border: 1px solid #2a2d3a; margin-bottom: .5rem;
}
.macro-label { font-size: .72rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.macro-value { font-size: 1.5rem; font-weight: 800; color: #e0e0e0; margin: .15rem 0; }
.macro-up   { font-size: .82rem; color: #2ca02c; }
.macro-down { font-size: .82rem; color: #e05252; }
.news-item {
    background: #1a1d27; border-radius: 10px; padding: .9rem 1rem;
    border-left: 3px solid #2a2d3a; margin-bottom: .4rem;
}
</style>
""", unsafe_allow_html=True)

def get_token():
    """Pega o token da BRAPI do secrets do Streamlit."""
    try:
        return st.secrets["BRAPI_TOKEN"]
    except Exception:
        return ""

@st.cache_data(ttl=300)
def buscar_ativos_brapi(token=None):
    tickers = [
        "PETR4","VALE3","ITUB4","BBDC4","BBAS3","ABEV3","WEGE3","MGLU3",
        "PRIO3","RENT3","GGBR4","SUZB3","RDOR3","VIVT3","LREN3",
        "BPAC11","SLCE3","TIMS3","CYRE3","EQTL3","EMBR3","RAIL3","HAPV3",
    ]
    resultado = {}
    for i in range(0, len(tickers), 10):
        lote = tickers[i:i+10]
        symbols = ",".join(lote)
        url = f"https://brapi.dev/api/quote/{symbols}?range=1d&interval=1d&fundamental=false"
        if token:
            url += f"&token={token}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                for q in r.json().get("results", []):
                    resultado[q["symbol"]] = q
        except Exception:
            pass
    return resultado

@st.cache_data(ttl=600)
def buscar_ibov_brapi(token=None):
    url = "https://brapi.dev/api/quote/%5EBVSP?range=1d&interval=1d"
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                return results[0]
    except Exception:
        pass
    return {}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏠 Dashboard de Mercado")

token = get_token()
col_r, col_t = st.columns([1, 5])
with col_r:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Carregando..."):
    dados   = buscar_ativos_brapi(token)
    ibov    = buscar_ibov_brapi(token)

st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} · Fonte: BRAPI")
st.divider()

# ── Indicadores Macro ─────────────────────────────────────────────────────────
st.markdown("### 📊 Indicadores Macro")

ibov_preco = ibov.get("regularMarketPrice", 0)
ibov_var   = ibov.get("regularMarketChangePercent", 0)

macro_cards = [
    ("IBOVESPA",    f"{ibov_preco:,.0f} pts" if ibov_preco else "—",
     ibov_var, True),
    ("SELIC (a.a.)", "14,50%",  1.21, True),
    ("IPCA (12M)",   "4,39%",   0.37, True),
    ("CDI (a.a.)",   "14,40%",  1.20, True),
    ("Dólar",        "R$ 5,17", -0.3, False),
    ("Euro",         "R$ 5,97", -0.2, False),
]

cols = st.columns(6)
for col, (label, valor, var, up) in zip(cols, macro_cards):
    sinal = "▲" if var > 0 else "▼"
    cor   = "macro-up" if var > 0 else "macro-down"
    with col:
        st.markdown(f"""
        <div class="macro-card">
            <div class="macro-label">{label}</div>
            <div class="macro-value">{valor}</div>
            <div class="{cor}">{sinal} {abs(var):.2f}%</div>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── Maiores Altas e Baixas ────────────────────────────────────────────────────
ranking = []
for sym, q in dados.items():
    preco = q.get("regularMarketPrice", 0)
    var   = q.get("regularMarketChangePercent", 0)
    nome  = q.get("shortName", sym)[:25] if q.get("shortName") else sym
    if preco and preco > 0:
        ranking.append({"ticker": sym, "nome": nome, "preco": preco, "var": round(var, 2)})

ranking.sort(key=lambda x: x["var"], reverse=True)

col_al, col_bx = st.columns(2)

def card_ativo(item, up=True):
    cor_borda = "#2ca02c" if up else "#e05252"
    seta      = "▲" if up else "▼"
    cor_var   = "#2ca02c" if up else "#e05252"
    return f"""
    <div class="news-item" style="border-left-color:{cor_borda}">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
                <span style="color:#4da6ff;font-weight:700;font-size:1rem">{item['ticker']}</span>
                <span style="color:#888;font-size:.82rem;margin-left:.5rem">{item['nome']}</span>
            </div>
            <div style="text-align:right">
                <div style="color:#e0e0e0;font-weight:700">R$ {item['preco']:.2f}</div>
                <div style="color:{cor_var};font-weight:700">{seta} {abs(item['var']):.2f}%</div>
            </div>
        </div>
    </div>"""

with col_al:
    st.markdown("### 📈 Maiores Altas")
    if ranking:
        for item in ranking[:5]:
            st.markdown(card_ativo(item, up=True), unsafe_allow_html=True)
    else:
        st.info("Aguardando dados... Adicione o token BRAPI em Secrets.")

with col_bx:
    st.markdown("### 📉 Maiores Baixas")
    if ranking:
        for item in ranking[-5:][::-1]:
            st.markdown(card_ativo(item, up=False), unsafe_allow_html=True)
    else:
        st.info("Aguardando dados...")

# ── Tabela completa ───────────────────────────────────────────────────────────
if ranking:
    with st.expander("📋 Ver todos os ativos"):
        rows = [{"Ticker": i["ticker"], "Nome": i["nome"],
                 "Preço": f"R$ {i['preco']:.2f}",
                 "Variação": f"{'▲' if i['var']>=0 else '▼'} {i['var']:+.2f}%"}
                for i in sorted(ranking, key=lambda x: x["ticker"])]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

st.divider()

# ── Info token ────────────────────────────────────────────────────────────────
if not token:
    st.info("""
    **💡 Para cotações ao vivo:** adicione seu token BRAPI em  
    Streamlit Cloud → **Settings → Secrets**:
    ```
    BRAPI_TOKEN = "seu_token_aqui"
    ```
    Token gratuito em: https://brapi.dev
    """)

st.caption("🏠 Dashboard RCO · BRAPI · Apenas fins educacionais")
