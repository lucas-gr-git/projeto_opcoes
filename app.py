"""
app.py — RCO Assistant | Página inicial
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
.main-title {
    font-size: 2.4rem; font-weight: 900;
    background: linear-gradient(135deg, #1f77b4, #2ca02c);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.aviso {
    background: #1e1a00; border-left: 4px solid #f39c12;
    padding: .6rem 1rem; border-radius: 6px;
    font-size: 0.82rem; color: #c8a400; margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">📊 RCO Assistant</p>', unsafe_allow_html=True)
st.markdown("**Plataforma de análise de opções** baseada na metodologia Jimmy Carvalho · Renda Com Opções")
st.divider()

st.markdown("### Navegue pelas páginas:")
st.info("👈 Use o **menu lateral esquerdo** para acessar as páginas. Se estiver recolhido, clique na **seta `>`** no canto superior esquerdo.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("#### 🧮 Calculadora")
    st.markdown("Preço teórico, gregas Delta/Theta/Gamma/Vega e **gráfico de payoff colorido**")

with col2:
    st.markdown("#### 📋 Ativos & Cotações")
    st.markdown("Lista de ativos por setor com **cotação ao vivo** e variação do dia")

with col3:
    st.markdown("#### 🏠 Dashboard")
    st.markdown("Maiores altas/baixas, indicadores macro: IBOV, Selic, Dólar, IPCA")

with col4:
    st.markdown("#### 🎯 Estratégias RCO")
    st.markdown("Venda Coberta, Wheel, Travas, Straddle com **recomendação inteligente**")

st.divider()
st.markdown('<div class="aviso">⚠️ Fins exclusivamente educacionais. Não constitui recomendação de investimento.</div>', unsafe_allow_html=True)
