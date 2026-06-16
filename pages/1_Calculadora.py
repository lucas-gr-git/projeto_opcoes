"""
Calculadora de Opções — Estruturas com múltiplas pernas
Preço teórico, Gregas, Payoff combinado
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import date, timedelta
from rco_core import black_scholes, gregas

st.set_page_config(page_title="Calculadora | RCO", page_icon="🧮", layout="wide")

# ── CSS dark ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.greek-card {
    background: #1a1d27; border-radius: 12px; padding: .9rem;
    text-align: center; border: 1px solid #2a2d3a;
}
.greek-label { font-size: .68rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.greek-value { font-size: 1.35rem; font-weight: 800; margin-top: .2rem; }
.blue  { color: #4da6ff; } .green { color: #2ca02c; } .red { color: #e05252; }
.gold  { color: #f0b429; } .purple{ color: #a78bfa; }
.panel { background: #1a1d27; border-radius: 14px; padding: 1.2rem; border: 1px solid #2a2d3a; }
</style>
""", unsafe_allow_html=True)

# ── Busca cotação via BRAPI ────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def buscar_preco(ticker: str):
    try:
        token = st.secrets["BRAPI_TOKEN"]
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

# ── Estado: lista de pernas ───────────────────────────────────────────────────
if "pernas" not in st.session_state:
    st.session_state.pernas = [
        {"tipo": "call", "pos": "compra", "strike": 100.0, "vol": 30.0, "qtd": 1},
    ]

def nova_perna(tipo, pos, strike, vol=30.0, qtd=1):
    return {"tipo": tipo, "pos": pos, "strike": round(strike, 2), "vol": vol, "qtd": qtd}

def aplicar_preset(nome, S):
    if nome == "Trava de Alta (Bull Call)":
        st.session_state.pernas = [
            nova_perna("call", "compra", S),
            nova_perna("call", "venda",  S * 1.05),
        ]
    elif nome == "Trava de Baixa (Bear Put)":
        st.session_state.pernas = [
            nova_perna("put", "compra", S),
            nova_perna("put", "venda",  S * 0.95),
        ]
    elif nome == "Straddle (compra)":
        st.session_state.pernas = [
            nova_perna("call", "compra", S),
            nova_perna("put",  "compra", S),
        ]
    elif nome == "Strangle (compra)":
        st.session_state.pernas = [
            nova_perna("call", "compra", S * 1.05),
            nova_perna("put",  "compra", S * 0.95),
        ]
    elif nome == "Straddle (venda)":
        st.session_state.pernas = [
            nova_perna("call", "venda", S),
            nova_perna("put",  "venda", S),
        ]
    elif nome == "Borboleta (Call)":
        st.session_state.pernas = [
            nova_perna("call", "compra", S * 0.95, qtd=1),
            nova_perna("call", "venda",  S,        qtd=2),
            nova_perna("call", "compra", S * 1.05, qtd=1),
        ]
    elif nome == "Condor (Call)":
        st.session_state.pernas = [
            nova_perna("call", "compra", S * 0.90),
            nova_perna("call", "venda",  S * 0.97),
            nova_perna("call", "venda",  S * 1.03),
            nova_perna("call", "compra", S * 1.10),
        ]
    elif nome == "Venda Coberta":
        st.session_state.pernas = [
            nova_perna("call", "venda", S * 1.07),
        ]
    elif nome == "Trava de Calendário (Call)":
        st.session_state.pernas = [
            nova_perna("call", "venda",  S, vol=30),
            nova_perna("call", "compra", S, vol=30),
        ]
    elif nome == "Personalizado (1 perna)":
        st.session_state.pernas = [nova_perna("call", "compra", S)]

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("## 🧮 Calculadora de Opções")
st.caption("Monte estruturas com múltiplas pernas · Preço teórico Black-Scholes · Payoff combinado")

# ── Layout ───────────────────────────────────────────────────────────────────
col_param, col_result = st.columns([1, 2], gap="large")

with col_param:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("#### ⚙️ Ativo e Vencimento")

    ticker_input = st.text_input("🔍 Buscar ativo (ex: PETR4, VALE3...)", "").upper().strip()
    preco_auto = None
    if ticker_input:
        with st.spinner(f"Buscando {ticker_input}..."):
            preco_auto = buscar_preco(ticker_input)
        if preco_auto:
            st.success(f"✅ {ticker_input}: **R$ {preco_auto:.2f}**")
        else:
            st.warning("Ativo não encontrado. Digite manualmente.")

    S = st.number_input("Preço do Ativo", min_value=0.01,
                        value=float(preco_auto) if preco_auto else 100.0,
                        step=0.50, format="%.2f")

    venc_date = st.date_input("Vencimento", value=date.today() + timedelta(days=30),
                               min_value=date.today() + timedelta(days=1))
    dias = (venc_date - date.today()).days
    T = dias / 365
    st.caption(f"⏱ {dias} dias corridos ({T:.3f} anos)")

    taxa = st.number_input("Taxa Livre de Risco (%)", value=14.50, step=0.25, format="%.2f")

    st.markdown("---")
    st.markdown("#### 🎯 Presets de Estrutura")

    presets = [
        "Personalizado (1 perna)",
        "Trava de Alta (Bull Call)",
        "Trava de Baixa (Bear Put)",
        "Straddle (compra)",
        "Strangle (compra)",
        "Straddle (venda)",
        "Borboleta (Call)",
        "Condor (Call)",
        "Venda Coberta",
        "Trava de Calendário (Call)",
    ]
    preset_sel = st.selectbox("Escolha um modelo", presets, label_visibility="collapsed")
    if st.button("📥 Aplicar preset", width="stretch"):
        aplicar_preset(preset_sel, S)
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ── Editor de pernas ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🦵 Pernas da Estrutura")

col_legs_l, col_legs_r = st.columns([3, 1])

with col_legs_r:
    if st.button("➕ Adicionar perna", width="stretch"):
        st.session_state.pernas.append(nova_perna("call", "compra", S))
        st.rerun()
    if st.button("🗑️ Limpar tudo", width="stretch"):
        st.session_state.pernas = [nova_perna("call", "compra", S)]
        st.rerun()

with col_legs_l:
    for i, perna in enumerate(st.session_state.pernas):
        cols = st.columns([1.3, 1.3, 1.5, 1.3, 0.8, 0.6])
        with cols[0]:
            perna["tipo"] = st.selectbox("Tipo", ["call", "put"],
                index=0 if perna["tipo"] == "call" else 1,
                key=f"tipo_{i}", label_visibility="collapsed" if i > 0 else "visible")
        with cols[1]:
            perna["pos"] = st.selectbox("Posição", ["compra", "venda"],
                index=0 if perna["pos"] == "compra" else 1,
                key=f"pos_{i}", label_visibility="collapsed" if i > 0 else "visible")
        with cols[2]:
            perna["strike"] = st.number_input("Strike", min_value=0.01,
                value=float(perna["strike"]), step=0.50, format="%.2f",
                key=f"strike_{i}", label_visibility="collapsed" if i > 0 else "visible")
        with cols[3]:
            perna["vol"] = st.number_input("VI (%)", min_value=1.0, max_value=200.0,
                value=float(perna["vol"]), step=1.0, format="%.1f",
                key=f"vol_{i}", label_visibility="collapsed" if i > 0 else "visible")
        with cols[4]:
            perna["qtd"] = st.number_input("Qtd", min_value=1, max_value=100,
                value=int(perna["qtd"]), step=1,
                key=f"qtd_{i}", label_visibility="collapsed" if i > 0 else "visible")
        with cols[5]:
            if len(st.session_state.pernas) > 1:
                if st.button("✕", key=f"rm_{i}"):
                    st.session_state.pernas.pop(i)
                    st.rerun()
        if i == 0:
            st.caption("Tipo | Posição | Strike | VI (%) | Qtd")

# ── Cálculos da estrutura ─────────────────────────────────────────────────────
r = taxa / 100

resultados_pernas = []
custo_total_liquido = 0.0
gregas_totais = {"delta": 0.0, "theta": 0.0, "gamma": 0.0, "vega": 0.0}

for perna in st.session_state.pernas:
    sigma_p = perna["vol"] / 100
    K = perna["strike"]
    qtd = perna["qtd"]
    sinal = 1 if perna["pos"] == "compra" else -1

    preco_p = black_scholes(S, K, T, r, sigma_p, perna["tipo"]) if T > 0 else (
        max(S - K, 0) if perna["tipo"] == "call" else max(K - S, 0)
    )
    g_p = gregas(S, K, T, r, sigma_p, perna["tipo"])

    custo_perna = sinal * preco_p * qtd
    custo_total_liquido += custo_perna

    for k in gregas_totais:
        gregas_totais[k] += sinal * g_p[k] * qtd

    resultados_pernas.append({
        "tipo": perna["tipo"], "pos": perna["pos"], "strike": K,
        "vol": perna["vol"], "qtd": qtd, "preco": preco_p, "custo": custo_perna,
    })

# ── Resultado: gregas totais + tabela de pernas ───────────────────────────────
with col_result:
    st.markdown("#### 📐 Resumo da Estrutura")

    gcols = st.columns(6)
    debito_credito = "Débito" if custo_total_liquido > 0 else "Crédito"
    cor_custo = "red" if custo_total_liquido > 0 else "green"
    cards = [
        (f"{debito_credito.upper()} TOTAL", f"R$ {abs(custo_total_liquido):.4f}", cor_custo),
        ("DELTA",  f"{gregas_totais['delta']:.4f}", "green" if gregas_totais['delta']>=0 else "red"),
        ("GAMMA",  f"{gregas_totais['gamma']:.4f}", "gold"),
        ("THETA",  f"{gregas_totais['theta']:.4f}", "green" if gregas_totais['theta']>=0 else "red"),
        ("VEGA",   f"{gregas_totais['vega']:.4f}",  "purple"),
        ("PERNAS", f"{len(st.session_state.pernas)}", "blue"),
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

    df_pernas = pd.DataFrame([{
        "Posição":  f"{'🟢 Compra' if p['pos']=='compra' else '🔴 Venda'}",
        "Tipo":     p["tipo"].upper(),
        "Strike":   f"R$ {p['strike']:.2f}",
        "VI":       f"{p['vol']:.0f}%",
        "Qtd":      p["qtd"],
        "Prêmio unit.": f"R$ {p['preco']:.4f}",
        "Custo (×qtd)": f"R$ {p['custo']:+.4f}",
    } for p in resultados_pernas])
    st.dataframe(df_pernas, width="stretch", hide_index=True)

    st.markdown("---")
    st.markdown("#### 📈 Gráfico de Payoff Combinado")

    amplitude = max(S * 0.40, 25)
    spots = np.linspace(S - amplitude, S + amplitude, 250)

    payoff_total = np.zeros_like(spots)
    for perna in st.session_state.pernas:
        K = perna["strike"]
        qtd = perna["qtd"]
        sinal = 1 if perna["pos"] == "compra" else -1
        sigma_p = perna["vol"] / 100
        preco_p = black_scholes(S, K, T, r, sigma_p, perna["tipo"]) if T > 0 else (
            max(S - K, 0) if perna["tipo"] == "call" else max(K - S, 0)
        )
        if perna["tipo"] == "call":
            intrinsico = np.maximum(spots - K, 0)
        else:
            intrinsico = np.maximum(K - spots, 0)
        payoff_total += sinal * qtd * (intrinsico - preco_p)

    try:
        import altair as alt

        df_plot = pd.DataFrame({"Spot": spots, "PnL": payoff_total})

        base = alt.Chart(df_plot).encode(x=alt.X("Spot:Q", title="Preço do Ativo no Vencimento (R$)"))

        area = base.mark_area(opacity=0.55).encode(
            y=alt.Y("PnL:Q", title="P&L (R$)"),
            y2=alt.value(0),
            color=alt.condition(alt.datum.PnL >= 0, alt.value("#2ca02c"), alt.value("#e05252")),
        )
        line = base.mark_line(color="#4da6ff", strokeWidth=2).encode(y="PnL:Q")

        rule_spot = alt.Chart(pd.DataFrame({"x": [S]})).mark_rule(
            color="#aaaaaa", strokeDash=[4, 4], strokeWidth=1.5
        ).encode(x="x:Q")

        zero_line = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(
            color="#444", strokeWidth=1
        ).encode(y="y:Q")

        strikes_unicos = sorted(set(p["strike"] for p in st.session_state.pernas))
        rules_strikes = alt.Chart(pd.DataFrame({"x": strikes_unicos})).mark_rule(
            color="#f0b429", strokeDash=[2, 2], strokeWidth=1
        ).encode(x="x:Q")

        chart = (area + line + rule_spot + rules_strikes + zero_line).properties(
            height=340, background="#0e1117"
        ).configure_axis(
            gridColor="#2a2d3a", labelColor="#aaa", titleColor="#aaa"
        ).configure_view(strokeOpacity=0)

        st.altair_chart(chart, width="stretch")

        lucro_max_val = payoff_total.max()
        perda_max_val = payoff_total.min()

        col1, col2, col3 = st.columns(3)
        col1.metric("Lucro máximo (na faixa)", f"R$ {lucro_max_val:.2f}",
                    help="Calculado dentro da faixa de spots simulada; pode ser ilimitado fora dela")
        col2.metric("Perda máxima (na faixa)", f"R$ {perda_max_val:.2f}")

        sign_changes = np.where(np.diff(np.sign(payoff_total)))[0]
        breakevens = [round(spots[idx], 2) for idx in sign_changes]
        be_txt = ", ".join(f"R$ {b:.2f}" for b in breakevens) if breakevens else "—"
        col3.metric("Break-even(s)", be_txt if len(breakevens) <= 2 else f"{len(breakevens)} pontos")

    except ImportError:
        st.line_chart(pd.DataFrame({"Spot": spots, "P&L": payoff_total}).set_index("Spot"))

    with st.expander("ℹ️ O que significa cada grega?"):
        st.markdown("""
| Grega | Significado | Dica RCO |
|---|---|---|
| **Delta** | Variação do prêmio por R$1 no ativo | Estrutura neutra: delta próximo de 0 |
| **Gamma** | Velocidade de mudança do Delta | Alto perto do vencimento — cuidado! |
| **Theta** | Decaimento temporal por dia | Positivo = estrutura ganha com o tempo |
| **Vega**  | Sensibilidade à volatilidade (por 1%) | Positivo = ganha se VI subir |
        """)

st.divider()
st.caption("🧮 Calculadora RCO · Black-Scholes · Apenas fins educacionais")
