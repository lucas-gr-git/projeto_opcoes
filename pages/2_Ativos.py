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
.heat-wrap {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px; margin: .8rem 0 1.4rem;
}
.heat-setor {
    background: #11141c; border: 1px solid #23262f; border-radius: 10px; padding: .6rem .6rem .7rem;
}
.heat-setor-title {
    font-size: .72rem; color: #8892a6; text-transform: uppercase;
    letter-spacing: .5px; margin: .1rem 0 .5rem .1rem; font-weight: 700;
}
.heat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.heat-tile { border-radius: 6px; padding: .45rem .5rem; min-height: 54px; }
.heat-tile.up   { background: #1e6b3a; }
.heat-tile.down { background: #8a2c2c; }
.heat-tile.flat { background: #2a2d3a; }
.heat-ticker { font-weight: 800; font-size: .78rem; color: #fff; line-height: 1.1; }
.heat-preco  { font-size: .74rem; color: #e4e4e4; margin-top: 3px; }
.heat-var    { font-size: .74rem; font-weight: 700; margin-top: 1px; color: #f2f2f2; }
</style>
""", unsafe_allow_html=True)

def cor_classe(var_pct: float, preco: float) -> str:
    if not preco:
        return "flat"
    if var_pct > 0:
        return "up"
    if var_pct < 0:
        return "down"
    return "flat"

def montar_heatmap_html(catalogo: dict, cotacoes: dict) -> str:
    blocos = []
    for setor, ativos in catalogo.items():
        tiles = []
        for ticker, _nome in ativos:
            c = cotacoes.get(ticker, {})
            preco = c.get("preco", 0)
            var   = c.get("var_pct", 0)
            classe = cor_classe(var, preco)
            p_fmt = f"R$ {preco:.2f}" if preco else "R$ 0,00"
            v_fmt = f"{var:+.2f}%" if preco else "+0,00%"
            tiles.append(
                f'<div class="heat-tile {classe}">'
                f'<div class="heat-ticker">{ticker}</div>'
                f'<div class="heat-preco">{p_fmt}</div>'
                f'<div class="heat-var">{v_fmt}</div>'
                f'</div>'
            )
        blocos.append(
            f'<div class="heat-setor">'
            f'<div class="heat-setor-title">{setor}</div>'
            f'<div class="heat-grid">{"".join(tiles)}</div>'
            f'</div>'
        )
    return f'<div class="heat-wrap">{"".join(blocos)}</div>'

CATALOGO = {
    "🏦 Financeiro": [
        ("ITUB4","Itaú Unibanco PN"),("BBDC4","Bradesco PN"),("BBAS3","Banco do Brasil ON"),
        ("BPAC11","BTG Pactual UNT"),("SANB11","Santander BR UNT"),("B3SA3","B3 ON"),
        ("BBSE3","BB Seguridade ON"),("CXSE3","Caixa Seguridade ON"),
        ("IRBR3","IRB Brasil RE ON"),("PSSA3","Porto Seguro ON"),
    ],
    "⛽ Petróleo e Gás": [
        ("PETR4","Petrobras PN"),("PETR3","Petrobras ON"),("PRIO3","PetroRio ON"),
        ("CSAN3","Cosan ON"),("UGPA3","Ultrapar ON"),
        ("RECV3","PetroReconcavo ON"),("ENAT3","Enauta ON"),
        ("RRRP3","3R Petroleum ON"),("VBBR3","Vibra Energia ON"),
    ],
    "⛏️ Mineração / Siderurgia": [
        ("VALE3","Vale ON"),("GGBR4","Gerdau PN"),("CSNA3","CSN ON"),("USIM5","Usiminas PNA"),
        ("GOAU4","Metalúrgica Gerdau PN"),("CMIN3","CSN Mineração ON"),("BRAP4","Bradespar PN"),
    ],
    "🏥 Saúde": [
        ("RDOR3","Rede D'Or ON"),("HAPV3","Hapvida ON"),("FLRY3","Fleury ON"),
        ("RADL3","Raia Drogasil ON"),("MATD3","Mater Dei ON"),
    ],
    "🚚 Logística": [
        ("RAIL3","Rumo ON"),("AZUL4","Azul PN"),("CCRO3","CCR ON"),("GOLL4","Gol PN"),
    ],
    "🛒 Varejo / Consumo": [
        ("LREN3","Lojas Renner ON"),("MGLU3","Magazine Luiza ON"),
        ("NTCO3","Grupo Natura ON"),("ALOS3","Allos ON"),("ASAI3","Assaí ON"),
        ("CRFB3","Carrefour Brasil ON"),("RENT3","Localiza ON"),("PCAR3","Pão de Açúcar ON"),
        ("VIVA3","Vivara ON"),("ARZZ3","Arezzo ON"),
    ],
    "⚡ Energia Elétrica": [
        ("EQTL3","Equatorial ON"),("ELET3","Eletrobras ON"),("ELET6","Eletrobras PNB"),
        ("CMIG4","Cemig PN"),("CPLE6","Copel PN"),("ENGI11","Energisa UNT"),
        ("TRPL4","Transmissão Paulista PN"),("TAEE11","Taesa UNT"),("EGIE3","Engie Brasil ON"),
    ],
    "🍔 Alimentos e Bebidas": [
        ("ABEV3","Ambev ON"),("MRFG3","Marfrig ON"),("BEEF3","Minerva ON"),
        ("JBSS3","JBS ON"),("BRFS3","BRF ON"),("SMTO3","São Martinho ON"),
    ],
    "🏗️ Construção / Imobiliário": [
        ("CYRE3","Cyrela ON"),("MRVE3","MRV ON"),("MULT3","Multiplan ON"),
        ("EZTC3","Eztec ON"),("TEND3","Construtora Tenda ON"),
    ],
    "🚰 Saneamento": [
        ("SBSP3","Sabesp ON"),("CSMG3","Copasa ON"),("SAPR11","Sanepar UNT"),
    ],
    "📡 Telecom / TI": [
        ("VIVT3","Telefônica Brasil ON"),("TIMS3","TIM ON"),("TOTVS3","Totvs ON"),
    ],
    "🏭 Industrial": [
        ("WEGE3","Weg ON"),("EMBR3","Embraer ON"),("ECOR3","EcoRodovias ON"),
    ],
    "🌲 Papel / Celulose / Agro": [
        ("SUZB3","Suzano ON"),("KLBN11","Klabin UNT"),("SLCE3","SLC Agrícola ON"),
    ],
}

def get_token():
    try:
        return st.secrets["BRAPI_TOKEN"]
    except Exception:
        return ""

@st.cache_data(ttl=300)
def buscar_um(ticker: str, token: str) -> dict:
    """Busca cotação de UM ticker por vez (mais compatível com plano free da BRAPI)."""
    url = f"https://brapi.dev/api/quote/{ticker}?range=1d&interval=1d&fundamental=false"
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                q = results[0]
                return {
                    "preco":    round(q.get("regularMarketPrice") or 0, 2),
                    "abertura": round(q.get("regularMarketOpen") or 0, 2),
                    "var_pct":  round(q.get("regularMarketChangePercent") or 0, 2),
                }
    except Exception:
        pass
    return {"preco": 0, "abertura": 0, "var_pct": 0}

@st.cache_data(ttl=300)
def buscar_todos(tickers_tuple: tuple, token: str) -> dict:
    """Busca cotações ticker por ticker (evita limite de múltiplos símbolos no plano free)."""
    resultado = {}
    for ticker in tickers_tuple:
        resultado[ticker] = buscar_um(ticker, token)
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

# ── Mapa de calor — atualiza sozinho a cada 5 minutos ───────────────────────
@st.fragment(run_every="5m")
def bloco_heatmap():
    token_hm = get_token()
    todos_tickers_hm = tuple(t for v in CATALOGO.values() for t, _ in v)
    with st.spinner("Atualizando mapa de calor..."):
        cotacoes_hm = buscar_todos(todos_tickers_hm, token_hm)
    st.markdown(montar_heatmap_html(CATALOGO, cotacoes_hm), unsafe_allow_html=True)
    st.caption(f"🔥 Mapa de calor · atualizado às {datetime.now().strftime('%H:%M:%S')} "
               "· atualiza automaticamente a cada 5 min")

bloco_heatmap()
st.divider()

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

with st.spinner(f"Buscando cotações de {len(todos_tickers)} ativos..."):
    cotacoes = buscar_todos(todos_tickers, token)

teve_dados = any(v["preco"] > 0 for v in cotacoes.values())

if teve_dados:
    n_ok = sum(1 for v in cotacoes.values() if v["preco"] > 0)
    st.success(f"✅ {n_ok}/{len(todos_tickers)} ativos carregados · {datetime.now().strftime('%H:%M:%S')}")
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
