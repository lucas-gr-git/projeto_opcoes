"""
Dashboard de Mercado — Macro, maiores altas/baixas, IBOV
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
.macro-var-up   { font-size: .82rem; color: #2ca02c; }
.macro-var-down { font-size: .82rem; color: #e05252; }
.news-item {
    background: #1a1d27; border-radius: 10px; padding: .9rem 1rem;
    border-left: 3px solid #2a2d3a; margin-bottom: .4rem;
}
.news-title  { font-size: .9rem; font-weight: 600; color: #e0e0e0; }
.news-source { font-size: .75rem; color: #888; margin-top: .2rem; }
.rank-up   { color: #2ca02c; font-weight: 700; }
.rank-down { color: #e05252; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── Buscas ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def buscar_macro():
    """Busca IBOV, Dólar, BTC e uma cesta de ativos para altas/baixas."""
    tickers_macro = ["^BVSP", "USDBRL=X", "BTC-USD"]
    tickers_ativos = [
        "PETR4.SA","VALE3.SA","ITUB4.SA","BBDC4.SA","BBAS3.SA",
        "ABEV3.SA","WEGE3.SA","MGLU3.SA","PRIO3.SA","RENT3.SA",
        "GGBR4.SA","SUZB3.SA","RDOR3.SA","VIVT3.SA","LREN3.SA",
        "BPAC11.SA","SLCE3.SA","TIMS3.SA","CYRE3.SA","EQTL3.SA",
        "EMBR3.SA","RAIL3.SA","HAPV3.SA","KLBN11.SA","SANB11.SA",
    ]
    todos = tickers_macro + tickers_ativos
    symbols = ",".join(todos)
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        quotes = r.json().get("quoteResponse", {}).get("result", [])
        return {q["symbol"]: q for q in quotes}
    except Exception:
        return {}

def get_val(data, sym, field, default=0):
    return data.get(sym, {}).get(field, default)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏠 Dashboard de Mercado")

col_refresh, col_time = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Carregando dados de mercado..."):
    data = buscar_macro()

st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} · Fonte: Yahoo Finance")
st.divider()

# ── Indicadores Macro ─────────────────────────────────────────────────────────
st.markdown("### 📊 Indicadores Macro")

macro_items = [
    ("^BVSP",     "IBOVESPA",      "pts",  1,     "regularMarketPrice", "regularMarketChangePercent"),
    ("USDBRL=X",  "Dólar (USD)",   "R$",   1,     "regularMarketPrice", "regularMarketChangePercent"),
    ("BTC-USD",   "Bitcoin",       "USD",  1,     "regularMarketPrice", "regularMarketChangePercent"),
]

# Dados fixos para Selic/IPCA (não estão no Yahoo Finance)
macro_fixos = [
    ("SELIC",  "Selic (a.a.)",  "14,50%",  "+0,00%",  True),
    ("IPCA",   "IPCA (12M)",    "4,39%",   "+0,37%",  True),
    ("CDI",    "CDI (a.a.)",    "14,40%",  "+0,00%",  True),
]

cols_macro = st.columns(6)

idx = 0
for sym, label, unidade, mult, field_preco, field_var in macro_items:
    preco = get_val(data, sym, field_preco, 0) * mult
    var   = get_val(data, sym, field_var,   0)
    sinal = "▲" if var > 0 else "▼"
    cor   = "macro-var-up" if var > 0 else "macro-var-down"
    fmt   = f"{preco:,.2f}" if preco else "—"
    if sym == "^BVSP":
        fmt = f"{preco:,.0f}"
    with cols_macro[idx]:
        st.markdown(f"""
        <div class="macro-card">
            <div class="macro-label">{label}</div>
            <div class="macro-value">{unidade} {fmt}</div>
            <div class="{cor}">{sinal} {var:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    idx += 1

for sym, label, valor, variacao, up in macro_fixos:
    cor = "macro-var-up" if up else "macro-var-down"
    with cols_macro[idx]:
        st.markdown(f"""
        <div class="macro-card">
            <div class="macro-label">{label}</div>
            <div class="macro-value">{valor}</div>
            <div class="{cor}">{variacao}</div>
        </div>
        """, unsafe_allow_html=True)
    idx += 1

st.divider()

# ── Maiores Altas e Baixas ────────────────────────────────────────────────────
tickers_ativos = [k for k in data.keys() if ".SA" in k]
ranking = []
for sym in tickers_ativos:
    preco = get_val(data, sym, "regularMarketPrice", 0)
    var   = get_val(data, sym, "regularMarketChangePercent", 0)
    nome  = get_val(data, sym, "shortName", sym.replace(".SA",""))
    if preco > 0:
        ranking.append({
            "ticker": sym.replace(".SA",""),
            "nome":   nome[:25],
            "preco":  preco,
            "var":    round(var, 2),
        })

ranking.sort(key=lambda x: x["var"], reverse=True)
altas  = ranking[:5]
baixas = ranking[-5:][::-1]

col_al, col_bx = st.columns(2)

with col_al:
    st.markdown("### 📈 Maiores Altas")
    for i, item in enumerate(altas, 1):
        st.markdown(f"""
        <div class="news-item" style="border-left-color:#2ca02c">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <span style="color:#4da6ff;font-weight:700;font-size:1rem">{item['ticker']}</span>
                    <span style="color:#888;font-size:.82rem;margin-left:.5rem">{item['nome']}</span>
                </div>
                <div style="text-align:right">
                    <div style="color:#e0e0e0;font-weight:700">R$ {item['preco']:.2f}</div>
                    <div class="rank-up">▲ {item['var']:+.2f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_bx:
    st.markdown("### 📉 Maiores Baixas")
    for i, item in enumerate(baixas, 1):
        st.markdown(f"""
        <div class="news-item" style="border-left-color:#e05252">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <span style="color:#4da6ff;font-weight:700;font-size:1rem">{item['ticker']}</span>
                    <span style="color:#888;font-size:.82rem;margin-left:.5rem">{item['nome']}</span>
                </div>
                <div style="text-align:right">
                    <div style="color:#e0e0e0;font-weight:700">R$ {item['preco']:.2f}</div>
                    <div class="rank-down">▼ {item['var']:+.2f}%</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Tabela completa ───────────────────────────────────────────────────────────
with st.expander("📋 Ver todos os ativos monitorados"):
    rows = []
    for item in sorted(ranking, key=lambda x: x["ticker"]):
        seta = "▲" if item["var"] > 0 else "▼"
        rows.append({
            "Ticker": item["ticker"],
            "Nome": item["nome"],
            "Preço": f"R$ {item['preco']:.2f}",
            "Variação": f"{seta} {item['var']:+.2f}%",
        })
    df = pd.DataFrame(rows)

    def colorir(val):
        if "▲" in str(val): return "color: #2ca02c; font-weight: bold"
        if "▼" in str(val): return "color: #e05252; font-weight: bold"
        return ""

    st.dataframe(
        df.style.applymap(colorir, subset=["Variação"]),
        use_container_width=True, hide_index=True
    )

st.divider()
st.caption("🏠 Dashboard RCO · Yahoo Finance · Apenas fins educacionais")
