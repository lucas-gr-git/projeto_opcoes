"""
Calculadora de Opções — Preço teórico, Gregas, Payoff colorido
"""
import streamlit as st
import pandas as pd
import numpy as np
import math
import requests
from datetime import date, timedelta
from rco_core import black_scholes, gregas, Mercado

st.set_page_config(page_title="Calculadora | RCO", page_icon="🧮", layout="wide")

# ── CSS dark ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.greek-card {
    background: #1a1d27; border-radius: 12px; padding: 1rem;
    text-align: center; border: 1px solid #2a2d3a;
}
.greek-label { font-size: .72rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.greek-value { font-size: 1.6rem; font-weight: 800; margin-top: .2rem; }
.blue  { color: #4da6ff; }
.green { color: #2ca02c; }
.red   { color: #e05252; }
.gold  { color: #f0b429; }
.purple{ color: #a78bfa; }
.panel {
    background: #1a1d27; border-radius: 14px; padding: 1.4rem;
    border: 1px solid #2a2d3a;
}
</style>
""", unsafe_allow_html=True)

# ── Busca cotação ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def buscar_preco(ticker: str):
    """Busca cotação via BRAPI."""
    try:
        token = st.secrets.get("BRAPI_TOKEN", "")
    except Exception:
        token = ""
    url = f"https://brapi.dev/api/quote/{ticker}?range=1d&interval=1d&fundamental=false"
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results and results[0].get("regularMarketPrice"):
                return round(float(results[0]["regularMarketPrice"]), 2)
    except Exception:
        pass
    return None

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("## 🧮 Calculadora de Opções")
st.caption("Preço teórico Black-Scholes · Gregas · Gráfico de Payoff")

# ── Layout: painel esquerdo + direito ────────────────────────────────────────
col_param, col_result = st.columns([1, 2], gap="large")

with col_param:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("#### ⚙️ Parâmetros")

    # Busca de ativo
    ticker_input = st.text_input("🔍 Buscar ativo (ex: PETR4, VALE3...)", "").upper().strip()
    preco_auto = None
    if ticker_input:
        with st.spinner(f"Buscando {ticker_input}..."):
            preco_auto = buscar_preco(ticker_input)
        if preco_auto:
            st.success(f"✅ {ticker_input}: **R$ {preco_auto:.2f}**")
        else:
            st.warning("Ativo não encontrado. Digite o preço manualmente.")

    tipo = st.radio("Tipo de Opção", ["Call", "Put"], horizontal=True)

    col_s, col_k = st.columns(2)
    with col_s:
        S = st.number_input("Preço do Ativo", min_value=0.01,
                            value=float(preco_auto) if preco_auto else 100.0,
                            step=0.50, format="%.2f")
    with col_k:
        K = st.number_input("Strike", min_value=0.01,
                            value=float(preco_auto) if preco_auto else 100.0,
                            step=0.50, format="%.2f")

    # Vencimento por data
    venc_date = st.date_input("Vencimento", value=date.today() + timedelta(days=30),
                               min_value=date.today() + timedelta(days=1))
    dias = (venc_date - date.today()).days
    T = dias / 365
    st.caption(f"⏱ {dias} dias corridos ({T:.3f} anos)")

    col_r, col_v = st.columns(2)
    with col_r:
        taxa = st.number_input("Taxa Livre de Risco (%)", value=14.50, step=0.25, format="%.2f")
    with col_v:
        vol = st.number_input("Volatilidade (%)", value=30.0, step=1.0, format="%.1f")

    # Modo: calcular preço ou calcular VI
    modo = st.radio("Modo", ["Calcular Preço", "Calcular Vol. Imp."], horizontal=True)

    if modo == "Calcular Vol. Imp.":
        preco_mercado = st.number_input("Preço de mercado da opção (R$)",
                                        min_value=0.0001, value=1.50, step=0.01, format="%.4f")

    st.markdown('</div>', unsafe_allow_html=True)

# ── Cálculos ─────────────────────────────────────────────────────────────────
r = taxa / 100
sigma = vol / 100
tipo_bs = tipo.lower()

if modo == "Calcular Vol. Imp.":
    # Bisseção para VI
    def calc_vi(S, K, T, r, tipo, preco_alvo, tol=1e-5, max_iter=200):
        lo, hi = 0.001, 10.0
        for _ in range(max_iter):
            mid = (lo + hi) / 2
            p = black_scholes(S, K, T, r, mid, tipo)
            if abs(p - preco_alvo) < tol:
                return mid
            if p < preco_alvo:
                lo = mid
            else:
                hi = mid
        return mid
    if T > 0:
        sigma = calc_vi(S, K, T, r, tipo_bs, preco_mercado)
        vol   = sigma * 100

preco_teorico = black_scholes(S, K, T, r, sigma, tipo_bs) if T > 0 else max(S-K,0) if tipo_bs=="call" else max(K-S,0)
g = gregas(S, K, T, r, sigma, tipo_bs)

with col_result:
    # ── Gregas ────────────────────────────────────────────────────────────────
    if modo == "Calcular Vol. Imp." and T > 0:
        st.markdown(f"### Volatilidade Implícita: **{vol:.2f}%**")
    else:
        gcols = st.columns(6)
        cards = [
            ("PREÇO TEÓRICO", f"R$ {preco_teorico:.4f}", "blue"),
            ("DELTA",         f"{g['delta']:.4f}",        "green" if g['delta'] > 0 else "red"),
            ("GAMMA",         f"{g['gamma']:.4f}",        "gold"),
            ("THETA",         f"{g['theta']:.4f}",        "red"),
            ("VEGA",          f"{g['vega']:.4f}",         "purple"),
            ("RHO",           f"{g['delta']*T*K*math.exp(-r*T)/100:.4f}", "blue"),
        ]
        for col, (label, val, cor) in zip(gcols, cards):
            with col:
                st.markdown(f"""
                <div class="greek-card">
                    <div class="greek-label">{label}</div>
                    <div class="greek-value {cor}">{val}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Gráfico de Payoff ─────────────────────────────────────────────────────
    st.markdown("#### 📈 Gráfico de Payoff")

    amplitude = max(S * 0.35, 20)
    spots = np.linspace(S - amplitude, S + amplitude, 200)

    if tipo_bs == "call":
        payoffs = np.maximum(spots - K, 0) - preco_teorico
    else:
        payoffs = np.maximum(K - spots, 0) - preco_teorico

    # Montar DataFrame com colunas separadas para área positiva e negativa
    df_payoff = pd.DataFrame({
        "Spot": spots,
        "Lucro":  np.where(payoffs >= 0, payoffs, np.nan),
        "Perda":  np.where(payoffs <  0, payoffs, np.nan),
    }).set_index("Spot")

    # Streamlit não tem área colorida nativa, usamos altair
    try:
        import altair as alt

        df_plot = pd.DataFrame({"Spot": spots, "PnL": payoffs})
        df_plot["Cor"] = np.where(df_plot["PnL"] >= 0, "Lucro", "Perda")

        base = alt.Chart(df_plot).encode(
            x=alt.X("Spot:Q", title="Preço do Ativo no Vencimento (R$)"),
        )

        area = base.mark_area(opacity=0.55).encode(
            y=alt.Y("PnL:Q", title="P&L (R$)"),
            y2=alt.value(0),  # baseline
            color=alt.condition(
                alt.datum.PnL >= 0,
                alt.value("#2ca02c"),
                alt.value("#e05252"),
            )
        )

        line = base.mark_line(color="#4da6ff", strokeWidth=2).encode(
            y="PnL:Q"
        )

        be = preco_teorico + K if tipo_bs == "call" else K - preco_teorico
        rule_spot = alt.Chart(pd.DataFrame({"x": [S]})).mark_rule(
            color="#aaaaaa", strokeDash=[4, 4], strokeWidth=1.5
        ).encode(x="x:Q")

        rule_be = alt.Chart(pd.DataFrame({"x": [be]})).mark_rule(
            color="#f0b429", strokeDash=[4, 4], strokeWidth=1.5
        ).encode(x="x:Q")

        zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            color="#444", strokeWidth=1
        ).encode(y="y:Q")

        chart = (area + line + rule_spot + rule_be + zero_line).properties(
            height=320,
            background="#0e1117",
        ).configure_axis(
            gridColor="#2a2d3a", labelColor="#aaa", titleColor="#aaa"
        ).configure_view(strokeOpacity=0)

        st.altair_chart(chart, width="stretch")

        col1, col2, col3 = st.columns(3)
        col1.metric("Break-even", f"R$ {be:.2f}")
        col2.metric("Prêmio pago/recebido", f"R$ {preco_teorico:.4f}")
        lucro_max = "Ilimitado" if tipo_bs == "call" else f"R$ {K - preco_teorico:.2f}"
        col3.metric("Lucro máximo", lucro_max)

    except ImportError:
        st.line_chart(df_payoff)

    # ── Tabela sensibilidade ──────────────────────────────────────────────────
    with st.expander("📊 Tabela de Sensibilidade (preço × volatilidade)"):
        vols_range  = [vol * m for m in (0.7, 0.85, 1.0, 1.15, 1.3)]
        spots_range = [S * m for m in (0.90, 0.95, 1.00, 1.05, 1.10)]
        tabela = {}
        for v in vols_range:
            col_name = f"VI {v:.0f}%"
            tabela[col_name] = [
                round(black_scholes(sp, K, T, r, v/100, tipo_bs), 4)
                for sp in spots_range
            ]
        df_sens = pd.DataFrame(tabela, index=[f"R$ {sp:.2f}" for sp in spots_range])
        df_sens.index.name = "Spot \\ VI"
        st.dataframe(df_sens,
                     width="stretch")

    # ── Info sobre as gregas ──────────────────────────────────────────────────
    with st.expander("ℹ️ O que significa cada grega?"):
        st.markdown("""
| Grega | Significado | Dica RCO |
|---|---|---|
| **Delta** | Variação do prêmio por R$1 no ativo | Venda coberta: busque delta 0.15–0.35 |
| **Gamma** | Velocidade de mudança do Delta | Alto perto do vencimento — cuidado! |
| **Theta** | Decaimento temporal por dia | Positivo para vendido, negativo para comprado |
| **Vega**  | Sensibilidade à volatilidade (por 1%) | VI alta = melhor para vender |
| **Rho**   | Sensibilidade à taxa de juros | Menos relevante no curto prazo |
        """)

st.divider()
st.caption("🧮 Calculadora RCO · Black-Scholes · Apenas fins educacionais")
