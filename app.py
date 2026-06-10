"""
app.py — RCO Assistant | Página inicial / navegação
"""
import streamlit as st

st.set_page_config(
    page_title="RCO Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
body { background: #0e1117; }
.main-title {
    font-size: 2.4rem; font-weight: 900;
    background: linear-gradient(135deg, #1f77b4, #2ca02c);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.card {
    background: #1a1d27; border-radius: 14px; padding: 1.6rem 1.4rem;
    border: 1px solid #2a2d3a; cursor: pointer; text-align: center;
    transition: border-color .2s;
}
.card:hover { border-color: #1f77b4; }
.card-icon { font-size: 2.4rem; }
.card-title { font-size: 1.05rem; font-weight: 700; color: #e0e0e0; margin: .5rem 0 .2rem; }
.card-desc  { font-size: 0.8rem; color: #888; }
.aviso {
    background: #1e1a00; border-left: 4px solid #f39c12;
    padding: .6rem 1rem; border-radius: 6px;
    font-size: 0.8rem; color: #c8a400; margin-top: 2rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📊 RCO Assistant</p>', unsafe_allow_html=True)
st.markdown("**Plataforma de análise de opções** baseada na metodologia Jimmy Carvalho · Renda Com Opções")
st.divider()

cols = st.columns(4)

pages = [
    ("🧮", "Calculadora de Opções",   "Preço teórico, gregas Delta/Theta/Gamma/Vega e gráfico de payoff colorido",  "pages/1_Calculadora.py"),
    ("📋", "Ativos & Cotações",        "Lista de ativos por setor com cotação ao vivo e variação do dia",             "pages/2_Ativos.py"),
    ("🏠", "Dashboard de Mercado",     "Maiores altas/baixas, indicadores macro (IBOV, Selic, Dólar, IPCA)",         "pages/3_Dashboard.py"),
    ("🎯", "Estratégias RCO",          "Venda Coberta, Wheel, Travas, Straddle com recomendação inteligente",        "pages/4_Estrategias.py"),
]

for col, (icon, title, desc, _) in zip(cols, pages):
    with col:
        st.markdown(f"""
        <div class="card">
            <div class="card-icon">{icon}</div>
            <div class="card-title">{title}</div>
            <div class="card-desc">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("Use o **menu lateral esquerdo** para navegar entre as páginas.")
st.markdown('<div class="aviso">⚠️ Fins exclusivamente educacionais. Não constitui recomendação de investimento.</div>', unsafe_allow_html=True)
