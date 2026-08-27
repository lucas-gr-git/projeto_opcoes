"""
Estratégias RCO — Venda Coberta, Wheel, Travas, Straddle
Cada estratégia mostra variações como CARDS clicáveis por perfil de risco
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from rco_core import (
    Mercado, recomendar,
    gerar_venda_coberta_variacoes, gerar_venda_put_variacoes, gerar_wheel_variacoes,
    gerar_trava_alta_variacoes, gerar_trava_baixa_variacoes,
    gerar_straddle_strangle_variacoes,
    calcular_atr,  # <- Importando a nova função ATR
)

st.set_page_config(page_title="Estratégias | RCO", page_icon="🎯", layout="wide")

# ... (Mantém todo o CSS que você já tinha) ...

# ... (Mantém a função buscar_preco e ATIVOS) ...

# Nova função para buscar dados históricos para o gráfico e ATR
@st.cache_data(ttl=300)
def buscar_historico(ticker, periodo="3mo", intervalo="1d"):
    """Busca dados históricos completos do ativo usando BRAPI."""
    try:
        token = st.secrets["BRAPI_TOKEN"]
    except Exception:
        token = ""
    
    url = f"https://brapi.dev/api/quote/{ticker}?range={periodo}&interval={intervalo}&fundamental=false"
    if token:
        url += f"&token={token}"
    
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json().get("results", [])
            if data and "historicalDataPrice" in data[0]:
                hist = data[0]["historicalDataPrice"]
                # Converte para o formato esperado pela função ATR
                dados_atr = [{
                    "date": datetime.utcfromtimestamp(item["date"]).strftime('%Y-%m-%d'),
                    "open": item["open"],
                    "high": item["high"],
                    "low": item["low"],
                    "close": item["close"]
                } for item in hist if item["open"] and item["close"]]
                return dados_atr
    except Exception as e:
        st.error(f"Erro ao buscar histórico: {e}")
    
    return None

# ... (Mantém sidebar e definição do mkt até o Header) ...

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"## 🎯 Estratégias RCO — {ticker_label}")
# ... (Mantém métricas) ...

st.divider()

# ── GRÁFICO DO ATIVO ──────────────────────────────────────────────────────────
st.markdown("### 📈 Gráfico do Ativo")
with st.expander("Ver gráfico de preços", expanded=False):
    if ticker_sel != "OUTRO":
        dados_hist = buscar_historico(ticker_sel)
        if dados_hist:
            df_hist = pd.DataFrame(dados_hist)
            df_hist["date"] = pd.to_datetime(df_hist["date"])
            df_hist.set_index("date", inplace=True)
            
            st.line_chart(df_hist["close"], color="#4da6ff")
            
            # Tabela de últimos 5 pregões
            st.caption("Últimos 5 pregões")
            st.dataframe(df_hist[["open", "high", "low", "close"]].tail(5), width="stretch")
        else:
            st.info("Não foi possível buscar o gráfico para este ativo.")
    else:
        st.info("Selecione um ticker na sidebar para ver o gráfico.")

# ── TABS ─────────────────────────────────────────────────────────────────────
tabs = st.tabs(["🎯 Recomendação","💼 Venda Coberta","🔻 Venda Put (com ATR)",
                "🔄 WHEEL","📈 Trava Alta","📉 Trava Baixa",
                "💥 Straddle/Strangle","🛡️ Gestão Risco"])

# ... (Mantém Tabs 0, 1 e 2) ...

# ── Venda Put ─────────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader(f"🔻 Venda de Put — {ticker_label}")
    st.caption("Escolha o perfil de risco — clique no card para ver detalhes")

    dados = gerar_venda_put_variacoes(mkt, n_variacoes)
    labels = rotular_perfis(len(dados))

    # ... (Mantém a lógica de seleção de perfil) ...

    with st.expander("📊 ATR (Average True Range) e Níveis de Preço", expanded=True):
        if ticker_sel != "OUTRO":
            dados_hist_atr = buscar_historico(ticker_sel, periodo="3mo", intervalo="1d")
            if dados_hist_atr:
                resultado_atr = calcular_atr(dados_hist_atr, periodo=14)
                
                if "erro" not in resultado_atr:
                    # CSS para os níveis
                    st.markdown("""
                    <style>
                    .atr-card {
                        background: #1a1d27; border-radius: 10px; padding: 1rem;
                        border: 1px solid #2a2d3a; margin-bottom: .5rem;
                    }
                    .atr-titulo { font-size: .85rem; color: #888; margin-bottom: .5rem; }
                    .atr-valor { font-size: 1.5rem; font-weight: 800; color: #4da6ff; }
                    .nivel-pill {
                        display: inline-block; padding: .3rem .8rem; border-radius: 20px;
                        background: #2a2d3a; color: #888; font-size: .8rem; margin: .2rem;
                        font-weight: 700;
                    }
                    .nivel-pill.azul { background: #1c2433; color: #4da6ff; }
                    .nivel-pill.vermelho { background: #2b0d0d; color: #e05252; }
                    .nivel-pill.verde { background: #0d2b1a; color: #2ca02c; }
                    </style>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown('<div class="atr-card">'
                                    f'<div class="atr-titulo">ATR (Período 14)</div>'
                                    f'<div class="atr-valor">R$ {resultado_atr["atr"]:.2f}</div>'
                                    f'<div class="atr-titulo" style="margin-top:.5rem">({resultado_atr["atr_pct"]}% do preço)</div>'
                                    '</div>', unsafe_allow_html=True)
                    with c2:
                        st.markdown(f'<div class="atr-card">'
                                    f'<div class="atr-titulo">Preço Atual</div>'
                                    f'<div class="atr-valor" style="color:#e0e0e0">R$ {resultado_atr["preco_atual"]:.2f}</div>'
                                    '</div>', unsafe_allow_html=True)

                    st.markdown("### Níveis de Preço (baseados no ATR)")
                    
                    # Exibe botões como na sua imagem
                    cols = st.columns(6)
                    niveis = resultado_atr["niveis"]
                    labels_ordem = ["±0,236", "±0,382", "±0,5", "±0,618", "±0,786", "+1"]
                    labels_extra = ["+2", "+3"]
                    
                    for i, label in enumerate(labels_ordem):
                        val = niveis[label]
                        cor = "azul" if "+" in label else "verde"
                        with cols[i % 6]:
                            st.markdown(f'<div class="nivel-pill {cor}">{label}<br>R$ {val:.2f}</div>', unsafe_allow_html=True)
                    
                    cols_extra = st.columns(2)
                    for i, label in enumerate(labels_extra):
                        val = niveis[label]
                        with cols_extra[i]:
                            st.markdown(f'<div class="nivel-pill vermelho">{label}<br>R$ {val:.2f}</div>', unsafe_allow_html=True)

                    # Gráfico de velas (Candlestick)
                    st.markdown("### 📊 Gráfico de Velas (Candlestick) e Níveis")
                    
                    # Usa Altair para criar um gráfico de velas básico
                    import altair as alt
                    
                    df_atr = pd.DataFrame(resultado_atr["dados"][-30:])  # Últimos 30 dias
                    df_atr["date"] = pd.to_datetime(df_atr["date"])
                    
                    # Base do gráfico
                    base = alt.Chart(df_atr).encode(
                        x=alt.X("date:T", title="Data"),
                        y=alt.Y("low:Q", scale=alt.Scale(zero=False), title="Preço")
                    )
                    
                    # Barras de Alta e Baixa
                    rule = base.mark_rule().encode(
                        y="low:Q",
                        y2="high:Q"
                    )
                    
                    # Corpos
                    candlestick = base.mark_bar().encode(
                        y="open:Q",
                        y2="close:Q",
                        color=alt.condition(
                            alt.datum.close > alt.datum.open,
                            alt.value("#2ca02c"),
                            alt.value("#e05252")
                        )
                    )
                    
                    # Linhas de níveis
                    nivel_data = [{"date": df_atr["date"].iloc[0], "y": niveis[label], "label": label} for label in labels_ordem + labels_extra]
                    nivel_df = pd.DataFrame(nivel_data)
                    
                    rules_niveis = alt.Chart(nivel_df).mark_rule(
                        strokeDash=[4, 4],
                        color="#f0b429",
                        strokeWidth=1.5
                    ).encode(
                        y="y:Q"
                    )
                    
                    # Texto dos níveis
                    text_niveis = alt.Chart(nivel_df).mark_text(
                        align="left",
                        dx=5,
                        color="#f0b429",
                        fontSize=10
                    ).encode(
                        y="y:Q",
                        text="label"
                    )
                    
                    chart = (rule + candlestick + rules_niveis + text_niveis).properties(
                        height=400,
                        background="#0e1117"
                    ).configure_axis(
                        gridColor="#2a2d3a",
                        labelColor="#aaa",
                        titleColor="#aaa"
                    ).configure_view(strokeOpacity=0)
                    
                    st.altair_chart(chart, width="stretch")
                    
                else:
                    st.warning(resultado_atr["erro"])
            else:
                st.warning("Não foi possível buscar os dados históricos para o ATR.")
        else:
            st.info("Selecione um ticker na sidebar para calcular o ATR.")

    # ... (Mantém a seleção do perfil de venda de put e a tabela) ...

# ... (Mantém as outras tabs) ...
