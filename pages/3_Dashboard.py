"""
Dashboard de Mercado — Macro, maiores altas/baixas via BRAPI
"""
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests
from datetime import datetime, timedelta

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
    try:
        return st.secrets["BRAPI_TOKEN"]
    except Exception:
        return ""

TICKERS_MONITORADOS = [
    "PETR4","VALE3","ITUB4","BBDC4","BBAS3","ABEV3","WEGE3","MGLU3",
    "PRIO3","RENT3","GGBR4","SUZB3","RDOR3","VIVT3","LREN3",
    "BPAC11","SLCE3","TIMS3","CYRE3","EQTL3","EMBR3","RAIL3","HAPV3",
]

@st.cache_data(ttl=300)
def buscar_um(ticker: str, token: str) -> dict:
    url = f"https://brapi.dev/api/quote/{ticker}?range=1d&interval=1d&fundamental=false"
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                return results[0]
    except Exception:
        pass
    return {}

@st.cache_data(ttl=300)
def buscar_ativos_brapi(tickers_tuple: tuple, token: str) -> dict:
    resultado = {}
    for ticker in tickers_tuple:
        q = buscar_um(ticker, token)
        if q:
            resultado[ticker] = q
    return resultado

# ── Consulta detalhada de ativo ─────────────────────────────────────────────
PERIODOS_CHART = {
    "1 Mês":   {"range": "1mo", "interval": "1d"},
    "6 Meses": {"range": "6mo", "interval": "1d"},
    "1 Ano":   {"range": "1y",  "interval": "1d"},
    "2 Anos":  {"range": "2y",  "interval": "1wk"},
    "5 Anos":  {"range": "5y",  "interval": "1wk"},
}

@st.cache_data(ttl=600)
def buscar_historico_periodo(ticker: str, range_: str, interval: str, token: str) -> pd.DataFrame:
    url = f"https://brapi.dev/api/quote/{ticker}?range={range_}&interval={interval}&fundamental=false"
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                hist = results[0].get("historicalDataPrice", [])
                if hist:
                    df = pd.DataFrame(hist)
                    df["date"] = pd.to_datetime(df["date"], unit="s")
                    df = df.dropna(subset=["close"])
                    return df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

@st.cache_data(ttl=600)
def buscar_historico_diag(ticker: str, range_: str, interval: str, token: str):
    """Igual à buscar_historico_periodo, mas devolve também o MOTIVO da falha
    (HTTP, mensagem de erro da BRAPI, ou "sem dados") — usado nos benchmarks
    para não descartar erros silenciosamente."""
    url = f"https://brapi.dev/api/quote/{ticker}?range={range_}&interval={interval}&fundamental=false"
    if token:
        url += f"&token={token}"
    vazio = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return vazio, f"HTTP {r.status_code}"
        data = r.json()
        if isinstance(data, dict) and data.get("error"):
            return vazio, str(data.get("message", "erro retornado pela BRAPI"))[:120]
        results = data.get("results", [])
        if not results:
            return vazio, "ticker não encontrado na BRAPI"
        item = results[0]
        if item.get("error"):
            return vazio, str(item.get("message", "erro retornado pela BRAPI"))[:120]
        hist = item.get("historicalDataPrice", [])
        if not hist:
            return vazio, "sem histórico de preços para este ticker/plano"
        df = pd.DataFrame(hist)
        df["date"] = pd.to_datetime(df["date"], unit="s")
        df = df.dropna(subset=["close"])
        if df.empty:
            return vazio, "histórico vazio após limpeza"
        return df[["date", "open", "high", "low", "close", "volume"]].sort_values("date").reset_index(drop=True), None
    except Exception as e:
        return vazio, f"exceção: {e}"[:120]

@st.cache_data(ttl=600)
def buscar_fundamentals(ticker: str, token: str) -> dict:
    """P/L, P/VP e DY dependem do plano do token BRAPI — podem vir vazios no plano free."""
    url = f"https://brapi.dev/api/quote/{ticker}?range=1d&interval=1d&fundamental=true"
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                return results[0]
    except Exception:
        pass
    return {}

@st.cache_data(ttl=1800)
def buscar_dividendos(ticker: str, token: str) -> list:
    url = f"https://brapi.dev/api/quote/{ticker}?range=5y&interval=1mo&dividends=true&fundamental=false"
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                dd = results[0].get("dividendsData", {}) or {}
                return dd.get("cashDividends", []) or []
    except Exception:
        pass
    return []

def retorno_ate(df: pd.DataFrame, dias: int):
    """% de variação entre o fechamento mais próximo de 'hoje - dias' e o fechamento mais recente."""
    if df.empty:
        return None
    alvo = df["date"].iloc[-1] - timedelta(days=dias)
    passado = df[df["date"] <= alvo]
    if passado.empty:
        return None
    preco_passado = passado["close"].iloc[-1]
    preco_atual = df["close"].iloc[-1]
    if not preco_passado:
        return None
    return round((preco_atual / preco_passado - 1) * 100, 2)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏠 Dashboard de Mercado")

token = get_token()
col_r, col_t = st.columns([1, 5])
with col_r:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()

with st.spinner("Carregando..."):
    dados = buscar_ativos_brapi(tuple(TICKERS_MONITORADOS), token)
    ibov  = buscar_um("^BVSP", token)

st.caption(f"🕐 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} · Fonte: BRAPI")
st.divider()

# ── Indicadores Macro ─────────────────────────────────────────────────────────
st.markdown("### 📊 Indicadores Macro")

ibov_preco = ibov.get("regularMarketPrice", 0)
ibov_var   = ibov.get("regularMarketChangePercent", 0)

macro_cards = [
    ("IBOVESPA",     f"{ibov_preco:,.0f} pts" if ibov_preco else "—", ibov_var),
    ("SELIC (a.a.)", "14,50%",  1.21),
    ("IPCA (12M)",   "4,39%",   0.37),
    ("CDI (a.a.)",   "14,40%",  1.20),
    ("Dólar",        "R$ 5,17", -0.3),
    ("Euro",         "R$ 5,97", -0.2),
]

cols = st.columns(6)
for col, (label, valor, var) in zip(cols, macro_cards):
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
        st.info("Aguardando dados...")

with col_bx:
    st.markdown("### 📉 Maiores Baixas")
    if ranking:
        for item in ranking[-5:][::-1]:
            st.markdown(card_ativo(item, up=False), unsafe_allow_html=True)
    else:
        st.info("Aguardando dados...")

if ranking:
    with st.expander("📋 Ver todos os ativos"):
        rows = [{"Ticker": i["ticker"], "Nome": i["nome"],
                 "Preço": f"R$ {i['preco']:.2f}",
                 "Variação": f"{'▲' if i['var']>=0 else '▼'} {i['var']:+.2f}%"}
                for i in sorted(ranking, key=lambda x: x["ticker"])]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

st.divider()

# ── Consulta Detalhada de Ativo ──────────────────────────────────────────────
st.markdown("## 🔍 Consulta Detalhada de Ativo")

col_busca, col_periodo = st.columns([2, 2])
with col_busca:
    ticker_consulta = st.text_input("Digite o código do ativo (Ex: PETR4, MGLU3, VALE3):",
                                     value="VALE3", key="dash_ticker_busca").strip().upper()
with col_periodo:
    periodo_sel = st.radio("Período do Gráfico:", list(PERIODOS_CHART.keys()),
                            index=2, horizontal=True, key="dash_periodo_sel")

if ticker_consulta:
    cfg = PERIODOS_CHART[periodo_sel]
    with st.spinner(f"Buscando dados de {ticker_consulta}..."):
        df_periodo = buscar_historico_periodo(ticker_consulta, cfg["range"], cfg["interval"], token)
        fund = buscar_fundamentals(ticker_consulta, token)

    if df_periodo.empty:
        st.warning(f"⚠️ Não encontrei dados para **{ticker_consulta}**. Verifique o código ou tente novamente.")
    else:
        preco_atual = df_periodo["close"].iloc[-1]
        preco_ini   = df_periodo["close"].iloc[0]
        var_periodo = (preco_atual / preco_ini - 1) * 100 if preco_ini else 0

        pl  = fund.get("priceEarnings")
        dy  = fund.get("dividendYield")
        pvp = fund.get("priceToBook")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Cotação", f"R$ {preco_atual:,.2f}")
        m2.metric(f"Variação ({periodo_sel})", f"{var_periodo:+.2f}%")
        m3.metric("P/L", f"{pl:.2f}" if pl else "-")
        m4.metric("P/VP", f"{pvp:.2f}" if pvp else "-")
        m5.metric("DY (12M)", f"{dy:.2f}%" if dy else "-")
        st.caption("⚠️ P/L, P/VP e DY dependem do plano do seu token BRAPI — no plano gratuito costumam vir vazios (\"-\").")

        # ── Rentabilidade Histórica ───────────────────────────────────────────
        st.markdown("#### 📈 Rentabilidade Histórica")
        with st.spinner("Calculando rentabilidade histórica..."):
            df_longo = buscar_historico_periodo(ticker_consulta, "10y", "1mo", token)
        base_ret = df_longo if not df_longo.empty else df_periodo
        janelas = [("1 mês", 30), ("3 meses", 91), ("1 ano", 365),
                   ("2 anos", 730), ("5 anos", 1825), ("10 anos", 3650)]
        linha_ret = {}
        for label, dias in janelas:
            r = retorno_ate(base_ret, dias)
            linha_ret[label] = f"{r:+.2f}%" if r is not None else "-"
        st.dataframe(pd.DataFrame([linha_ret], index=["Rentabilidade"]), width="stretch")

        st.download_button("⬇️ Baixar Histórico Completo (.CSV)",
                            data=df_periodo.to_csv(index=False).encode("utf-8"),
                            file_name=f"{ticker_consulta}_historico.csv", mime="text/csv")

        # ── Candlestick + Volume + Médias móveis ──────────────────────────────
        st.markdown("#### 🕯️ Gráfico de Preço e Volume")
        df_c = df_periodo.copy()
        df_c["cor"]  = np.where(df_c["close"] >= df_c["open"], "#2ca02c", "#e05252")
        df_c["ma50"]  = df_c["close"].rolling(50, min_periods=1).mean()
        df_c["ma100"] = df_c["close"].rolling(100, min_periods=1).mean()
        df_c["ma200"] = df_c["close"].rolling(200, min_periods=1).mean()

        base = alt.Chart(df_c).encode(x=alt.X("date:T", title=None))
        vol = base.mark_bar(size=3, opacity=0.35).encode(
            y=alt.Y("volume:Q", axis=alt.Axis(title="Volume"),
                    scale=alt.Scale(domain=[0, df_c["volume"].max() * 4])),
            color=alt.Color("cor:N", scale=None))
        pavio = base.mark_rule().encode(
            y=alt.Y("low:Q", axis=alt.Axis(title="Preço (R$)"), scale=alt.Scale(zero=False)),
            y2="high:Q", color=alt.Color("cor:N", scale=None))
        corpo = base.mark_bar(size=3).encode(
            y=alt.Y("open:Q", scale=alt.Scale(zero=False)), y2="close:Q",
            color=alt.Color("cor:N", scale=None))
        m50  = base.mark_line(color="#4da6ff", strokeWidth=1.3).encode(y=alt.Y("ma50:Q", scale=alt.Scale(zero=False)))
        m100 = base.mark_line(color="#b06fe0", strokeWidth=1.3).encode(y=alt.Y("ma100:Q", scale=alt.Scale(zero=False)))
        m200 = base.mark_line(color="#ffffff", strokeWidth=1.1).encode(y=alt.Y("ma200:Q", scale=alt.Scale(zero=False)))

        # Camadas de preço compartilham UMA escala (resolução padrão "shared" dentro do grupo);
        # só o grupo de preço vs. o volume ficam em escalas independentes entre si.
        camada_precos = alt.layer(pavio, corpo, m50, m100, m200)
        chart_preco = alt.layer(vol, camada_precos).resolve_scale(y="independent").properties(
            height=420, background="#0e1117"
        ).configure_axis(gridColor="#2a2d3a", labelColor="#aaa", titleColor="#aaa").configure_view(strokeOpacity=0)
        st.altair_chart(chart_preco, width="stretch")
        st.caption("Médias móveis: 🔵 50 · 🟣 100 · ⚪ 200 · barras claras no rodapé = volume")
        st.link_button("🗞️ Ver notícias recentes (Google)",
                        f"https://news.google.com/search?q={ticker_consulta}%20a%C3%A7%C3%A3o&hl=pt-BR&gl=BR")

        # ── Comparativo com Benchmarks ─────────────────────────────────────────
        st.markdown("#### 📊 Comparativo de Desempenho e Benchmarks")
        BENCHMARKS = {
            "IBOV (BOVA11)": "BOVA11", "IFIX (XFIX11)": "XFIX11",
            "Small Caps (SMLL)": "SMAL11", "Dividendos (IDIV)": "DIVO11",
            "IVVB11 (S&P500)": "IVVB11",
        }
        series_cmp = []
        falharam = []
        with st.spinner("Buscando benchmarks..."):
            base_ativo = df_periodo[["date", "close"]].copy()
            base_ativo["retorno"] = (base_ativo["close"] / base_ativo["close"].iloc[0] - 1) * 100
            base_ativo["serie"] = ticker_consulta
            series_cmp.append(base_ativo[["date", "retorno", "serie"]])

            for nome_bm, tk_bm in BENCHMARKS.items():
                df_bm, motivo = buscar_historico_diag(tk_bm, cfg["range"], cfg["interval"], token)
                if not df_bm.empty and df_bm["close"].iloc[0]:
                    df_bm = df_bm[["date", "close"]].copy()
                    df_bm["retorno"] = (df_bm["close"] / df_bm["close"].iloc[0] - 1) * 100
                    df_bm["serie"] = nome_bm
                    series_cmp.append(df_bm[["date", "retorno", "serie"]])
                else:
                    falharam.append(f"{nome_bm} — {motivo or 'sem dados'}")

            # CDI / IPCA — estimativa sintética (juros compostos a taxa anual constante)
            for nome_tx, taxa_aa in [("CDI (14,40% a.a., estimado)", 0.1440),
                                      ("IPCA (4,39% a.a., estimado)", 0.0439)]:
                datas = df_periodo["date"]
                dias_desde_inicio = (datas - datas.iloc[0]).dt.days
                retorno_sint = ((1 + taxa_aa) ** (dias_desde_inicio / 365) - 1) * 100
                series_cmp.append(pd.DataFrame({"date": datas, "retorno": retorno_sint, "serie": nome_tx}))

        df_cmp = pd.concat(series_cmp, ignore_index=True)
        chart_cmp = alt.Chart(df_cmp).mark_line().encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("retorno:Q", title="Desempenho acumulado (%)"),
            color=alt.Color("serie:N", title=None),
            tooltip=["serie:N", alt.Tooltip("date:T", format="%d/%m/%Y"), alt.Tooltip("retorno:Q", format=".2f")],
        ).properties(height=380, background="#0e1117").configure_axis(
            gridColor="#2a2d3a", labelColor="#aaa", titleColor="#aaa"
        ).configure_view(strokeOpacity=0)
        st.altair_chart(chart_cmp, width="stretch")
        st.caption("⚠️ CDI e IPCA são estimativas com juros compostos sobre a taxa anual atual (não são séries "
                   "históricas reais). IBOV, IFIX, Small Caps, Dividendos e IVVB11 usam ETFs como proxy "
                   "(BOVA11, XFIX11, SMAL11, DIVO11, IVVB11).")
        if falharam:
            st.warning("Alguns benchmarks não carregaram — motivo retornado pela BRAPI:\n\n" +
                       "\n".join(f"- **{f}**" for f in falharam))

        # ── Calendário de Eventos Corporativos ─────────────────────────────────
        st.markdown("#### 🗓️ Calendário de Eventos Corporativos")
        with st.spinner("Buscando proventos..."):
            divs = buscar_dividendos(ticker_consulta, token)

        if divs:
            df_div = pd.DataFrame(divs)
            col_pgto = "paymentDate" if "paymentDate" in df_div.columns else None
            col_com  = next((c for c in ["lastDatePrior", "approvedOn", "dateCom"] if c in df_div.columns), None)
            ultimo = df_div.iloc[0]

            c1, c2, c3 = st.columns(3)
            c1.metric("Tipo de Provento", str(ultimo.get("label", "Dividendo/JCP")))
            c2.metric("Data Com (Último Evento)", str(ultimo.get(col_com, "-")) if col_com else "-")
            c3.metric("Data de Pagamento", str(ultimo.get(col_pgto, "-")) if col_pgto else "-")

            st.markdown("**Histórico de Proventos**")
            cols_show = [c for c in ["label", col_com, "rate"] if c and c in df_div.columns]
            st.dataframe(df_div[cols_show] if cols_show else df_div, width="stretch", hide_index=True)
        else:
            st.info("Sem histórico de proventos disponível para este ativo (também depende do plano do token BRAPI).")

st.divider()

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
