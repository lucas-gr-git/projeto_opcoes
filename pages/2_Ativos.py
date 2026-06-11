"""
Ativos & Cotações — Lista por setor com cotação ao vivo via BRAPI
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
.brapi-info {
    background: #1a1d27; border-left: 4px solid #4da6ff;
    padding: .7rem 1rem; border-radius: 6px; font-size: .83rem;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

CATALOGO = {
    "🏦 Financeiro": [
        ("ITUB4","Itaú Unibanco PN"),("BBDC4","Bradesco PN"),("BBAS3","Banco do Brasil ON"),
        ("BPAC11","BTG Pactual UNT"),("SANB11","Santander BR UNT"),("B3SA3","B3 ON"),
    ],
    "⛽ Energia / Petróleo": [
        ("PETR4","Petrobras PN"),("PETR3","Petrobras ON"),("PRIO3","PetroRio ON"),
        ("CSAN3","Cosan ON"),("UGPA3","Ultrapar ON"),("EQTL3","Equatorial ON"),
    ],
    "⛏️ Mineração / Siderurgia": [
        ("VALE3","Vale ON"),("GGBR4","Gerdau PN"),("CSNA3","CSN ON"),("USIM5","Usiminas PNA"),
    ],
    "🏭 Industrial": [
        ("WEGE3","Weg ON"),("RAIL3","Rumo ON"),("EMBR3","Embraer ON"),("ECOR3","EcoRodovias ON"),
    ],
    "🛒 Varejo / Consumo": [
        ("ABEV3","Ambev ON"),("LREN3","Lojas Renner ON"),("MGLU3","Magalu ON"),
        ("NTCO3","Grupo Natura ON"),("BRFS3","BRF ON"),
    ],
    "🏥 Saúde": [
        ("RDOR3","Rede D'Or ON"),("HAPV3","Hapvida ON"),("FLRY3","Fleury ON"),
    ],
    "📡 Telecom": [
        ("VIVT3","Telefônica ON"),("TIMS3","TIM ON"),
    ],
    "🌲 Papel / Celulose / Agro": [
        ("SUZB3","Suzano ON"),("KLBN11","Klabin UNT"),("SLCE3","SLC Agrícola ON"),
    ],
    "🏗️ Imobiliário": [
        ("CYRE3","Cyrela ON"),("MRVE3","MRV ON"),("MULT3","Multiplan ON"),
    ],
}

def get_token():
    """Pega o token da BRAPI do secrets do Streamlit, ou usa sem token (limitado)."""
    try:
        return st.secrets["BRAPI_TOKEN"]
    except Exception:
        return None

@st.cache_data(ttl=300)
def buscar_brapi(tickers_tuple: tuple, token: str = None) -> dict:
    """Busca cotações via BRAPI. Funciona com e sem token (sem token = sem dados de mercado fechado)."""
    resultado = {}
    tickers = list(tickers_tuple)
    
    # BRAPI aceita até 10 por request
    for i in range(0, len(tickers), 10):
        lote = tickers[i:i+10]
        symbols = ",".join(lote)
        url = f"https://brapi.dev/api/quote/{symbols}?range=1d&interval=1d&fundamental=false"
        if token:
            url += f"&token={token}"
        try:
            r = requests.get(url, timeout=10, headers={"Accept": "application/json"})
            if r.status_code == 200:
                data = r.json()
                for q in data.get("results", []):
                    sym = q.get("symbol", "")
                    resultado[sym] = {
                        "preco":    round(q.get("regularMarketPrice") or 0, 2),
                        "abertura": round(q.get("regularMarketOpen") or 0, 2),
                        "var_pct":  round(q.get("regularMarketChangePercent") or 0, 2),
                        "bid":      round(q.get("regularMarketPrice") or 0, 2),
                        "ask":      round(q.get("regularMarketPrice") or 0, 2),
                    }
        except Exception:
            pass
    return resultado

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📋 Ativos & Cotações")

token = get_token()

if not token:
    st.markdown("""
    <div class="brapi-info">
    📡 <strong>Para cotações ao vivo:</strong> crie uma conta gratuita em 
    <a href="https://brapi.dev" target="_blank">brapi.dev</a>, copie seu token 
    e adicione em <strong>Streamlit Cloud → Settings → Secrets</strong>:<br><br>
    <code>BRAPI_TOKEN = "seu_token_aqui"</code>
    </div>
    """, unsafe_allow_html=True)

col_h1, col_h2 = st.columns([5, 1])
with col_h2:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

setor_filtro = st.selectbox(
    "Filtrar por setor",
    ["Todos"] + list(CATALOGO.keys()),
    label_visibility="collapsed"
)

todos_tickers = tuple(t for v in CATALOGO.values() for t, _ in v)

with st.spinner("Buscando cotações..."):
    cotacoes = buscar_brapi(todos_tickers, token)

teve_dados = any(v["preco"] > 0 for v in cotacoes.values()) if cotacoes else False

if teve_dados:
    st.success(f"✅ {sum(1 for v in cotacoes.values() if v['preco']>0)} ativos carregados · {datetime.now().strftime('%H:%M:%S')}")
else:
    st.warning("⚠️ Cotações indisponíveis. Verifique o token BRAPI em Secrets ou tente novamente.")
    st.caption("Dados de fim de semana / fora do horário podem retornar zerados mesmo com token.")

setores_render = {k: v for k, v in CATALOGO.items()
                  if setor_filtro == "Todos" or k == setor_filtro}

for setor, ativos in setores_render.items():
    st.markdown(f'<div class="setor-header">{setor}</div>', unsafe_allow_html=True)
    rows = []
    for ticker, nome in ativos:
        c = cotacoes.get(ticker, {})
        preco   = c.get("preco", 0)
        var_pct = c.get("var_pct", 0)
        abertura= c.get("abertura", 0)

        if preco:
            seta = "▲" if var_pct > 0 else ("▼" if var_pct < 0 else "─")
            p_fmt = f"R$ {preco:.2f}"
            v_fmt = f"{seta} {var_pct:+.2f}%"
            a_fmt = f"R$ {abertura:.2f}"
        else:
            p_fmt = v_fmt = a_fmt = "—"

        rows.append({
            "Ativo":       ticker,
            "Nome":        nome,
            "Último (R$)": p_fmt,
            "Variação":    v_fmt,
            "Abertura":    a_fmt,
        })

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        height=min(38 * len(rows) + 40, 300),
    )

st.divider()
st.caption("📋 Fonte: BRAPI (brapi.dev) · Apenas fins educacionais")
