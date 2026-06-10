"""
Ativos & Cotações — Lista por setor com cotação ao vivo
"""
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Ativos | RCO", page_icon="📋", layout="wide")

st.markdown("""
<style>
.setor-header {
    font-size: 1rem; font-weight: 700; color: #4da6ff;
    border-bottom: 1px solid #2a2d3a; padding-bottom: .3rem;
    margin: 1rem 0 .5rem;
}
.up   { color: #2ca02c; font-weight: 700; }
.down { color: #e05252; font-weight: 700; }
.flat { color: #aaa; }
</style>
""", unsafe_allow_html=True)

# ── Catálogo de ativos ────────────────────────────────────────────────────────
CATALOGO = {
    "🏦 Financeiro": [
        ("ITUB4", "Itaú Unibanco PN"),
        ("BBDC4", "Bradesco PN"),
        ("BBAS3", "Banco do Brasil ON"),
        ("BPAC11","BTG Pactual UNT"),
        ("SANB11","Santander BR UNT"),
        ("B3SA3", "B3 ON"),
    ],
    "⛽ Energia / Petróleo": [
        ("PETR4", "Petrobras PN"),
        ("PETR3", "Petrobras ON"),
        ("PRIO3", "PetroRio ON"),
        ("CSAN3", "Cosan ON"),
        ("UGPA3", "Ultrapar ON"),
        ("EQTL3", "Equatorial ON"),
    ],
    "⛏️ Mineração / Siderurgia": [
        ("VALE3", "Vale ON"),
        ("GGBR4", "Gerdau PN"),
        ("CSNA3", "CSN ON"),
        ("USIM5", "Usiminas PNA"),
    ],
    "🏭 Industrial": [
        ("WEGE3", "Weg ON"),
        ("RAIL3", "Rumo ON"),
        ("EMBR3", "Embraer ON"),
        ("ECOR3", "EcoRodovias ON"),
    ],
    "🛒 Varejo / Consumo": [
        ("ABEV3", "Ambev ON"),
        ("LREN3", "Lojas Renner ON"),
        ("MGLU3", "Magazine Luiza ON"),
        ("NTCO3", "Grupo Natura ON"),
        ("BRFS3", "BRF ON"),
    ],
    "🏥 Saúde": [
        ("RDOR3", "Rede D'Or ON"),
        ("HAPV3", "Hapvida ON"),
        ("FLRY3", "Fleury ON"),
    ],
    "📡 Telecom": [
        ("VIVT3", "Telefônica ON"),
        ("TIMS3", "TIM ON"),
    ],
    "🌲 Papel / Celulose / Agro": [
        ("SUZB3", "Suzano ON"),
        ("KLBN11","Klabin UNT"),
        ("SLCE3", "SLC Agrícola ON"),
    ],
    "🏗️ Imobiliário": [
        ("CYRE3", "Cyrela ON"),
        ("MRVE3", "MRV ON"),
        ("MULT3", "Multiplan ON"),
    ],
}

# ── Busca de cotações em batch ────────────────────────────────────────────────
@st.cache_data(ttl=180)
def buscar_lote(tickers: tuple) -> dict:
    """Busca cotações de vários tickers de uma vez via Yahoo Finance."""
    resultado = {}
    symbols = ",".join(f"{t}.SA" for t in tickers)
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        quotes = r.json().get("quoteResponse", {}).get("result", [])
        for q in quotes:
            ticker = q.get("symbol", "").replace(".SA", "")
            resultado[ticker] = {
                "preco":    round(q.get("regularMarketPrice", 0), 2),
                "abertura": round(q.get("regularMarketOpen", 0), 2),
                "bid":      round(q.get("bid", 0), 2),
                "ask":      round(q.get("ask", 0), 2),
                "var_pct":  round(q.get("regularMarketChangePercent", 0), 2),
                "var_sem":  round(q.get("fiftyTwoWeekChangePercent", 0) / 52 * 1, 2),
            }
    except Exception:
        pass
    return resultado

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📋 Ativos & Cotações")
st.caption("Cotações ao vivo · Agrupadas por setor · Atualização a cada 3 minutos")

# Botão de atualização manual
col_h1, col_h2 = st.columns([5, 1])
with col_h2:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

# Filtro por setor
setores = ["Todos"] + list(CATALOGO.keys())
setor_filtro = st.selectbox("Filtrar por setor", setores, label_visibility="collapsed")

# Coleta todos os tickers
todos_tickers = tuple(t for tickers in CATALOGO.values() for t, _ in tickers)

with st.spinner("Buscando cotações..."):
    cotacoes = buscar_lote(todos_tickers)

ultimo_update = datetime.now().strftime("%H:%M:%S")
st.caption(f"🕐 Última atualização: {ultimo_update}")

# ── Renderizar por setor ──────────────────────────────────────────────────────
setores_render = {k: v for k, v in CATALOGO.items()
                  if setor_filtro == "Todos" or k == setor_filtro}

for setor, ativos in setores_render.items():
    st.markdown(f'<div class="setor-header">{setor}</div>', unsafe_allow_html=True)

    rows = []
    for ticker, nome in ativos:
        c = cotacoes.get(ticker, {})
        preco   = c.get("preco",    0)
        var_pct = c.get("var_pct",  0)
        abertura= c.get("abertura", 0)
        bid     = c.get("bid",      0)
        ask     = c.get("ask",      0)

        seta = "▲" if var_pct > 0 else ("▼" if var_pct < 0 else "─")
        rows.append({
            "Ativo":          ticker,
            "Nome":           nome,
            "Último (R$)":    f"R$ {preco:.2f}" if preco else "—",
            "Variação":       f"{seta} {var_pct:+.2f}%" if preco else "—",
            "Abertura":       f"R$ {abertura:.2f}" if abertura else "—",
            "Compra (Bid)":   f"R$ {bid:.2f}" if bid else "—",
            "Venda (Ask)":    f"R$ {ask:.2f}" if ask else "—",
        })

    df = pd.DataFrame(rows)

    def colorir_variacao(val):
        if "▲" in str(val):
            return "color: #2ca02c; font-weight: bold"
        if "▼" in str(val):
            return "color: #e05252; font-weight: bold"
        return "color: #aaa"

    st.dataframe(
        df.style.applymap(colorir_variacao, subset=["Variação"]),
        width="stretch",
        hide_index=True,
        height=min(35 * len(rows) + 38, 320),
    )

    # Botão de usar ativo na calculadora
    tickers_setor = [t for t, _ in ativos]
    ticker_sel = st.selectbox(
        f"Abrir na Calculadora",
        ["—"] + tickers_setor,
        key=f"sel_{setor}",
        label_visibility="collapsed",
    )
    if ticker_sel != "—":
        preco_sel = cotacoes.get(ticker_sel, {}).get("preco", 0)
        if preco_sel:
            st.info(f"**{ticker_sel}**: R$ {preco_sel:.2f} · Vá para **🧮 Calculadora** e digite `{ticker_sel}` na busca.")

st.divider()
st.caption("📋 Fonte: Yahoo Finance · Apenas fins educacionais")
