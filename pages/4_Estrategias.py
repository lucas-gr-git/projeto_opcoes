"""
Estratégias RCO — Venda Coberta, Wheel, Travas, Straddle
Cada estratégia mostra variações como CARDS clicáveis por perfil de risco
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
from rco_core import (
    Mercado, recomendar,
    gerar_venda_coberta_variacoes, gerar_venda_put_variacoes, gerar_wheel_variacoes,
    gerar_trava_alta_variacoes, gerar_trava_baixa_variacoes,
    gerar_straddle_strangle_variacoes,
)

st.set_page_config(page_title="Estratégias | RCO", page_icon="🎯", layout="wide")

st.markdown("""
<style>
.rec-card { border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: .6rem; border-left: 5px solid; }
.rec-alta  { background: #0d2b1a; border-color: #2ca02c; }
.rec-media { background: #2b200d; border-color: #f39c12; }
.rule-box {
    background: #1a1d27; border-left: 4px solid #1f77b4;
    padding: .8rem 1rem; border-radius: 6px; font-size: .88rem; margin-top: 1rem;
}
.aviso { background: #1e1a00; border-left: 4px solid #f39c12;
    padding: .6rem 1rem; border-radius: 6px; font-size: .8rem; color: #c8a400; }

.perfil-card {
    background: #1a1d27; border-radius: 12px; padding: 1rem 1.1rem;
    border: 2px solid #2a2d3a; margin-bottom: .5rem; cursor: pointer;
    transition: border-color .15s;
}
.perfil-card.selecionado { border-color: #4da6ff; background: #1c2433; }
.perfil-tag {
    font-size: .68rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: 1px; padding: .15rem .6rem; border-radius: 20px;
    display: inline-block; margin-bottom: .4rem;
}
.tag-conservadora { background: #0d2b1a; color: #2ca02c; }
.tag-moderada     { background: #2b200d; color: #f39c12; }
.tag-agressiva    { background: #2b0d0d; color: #e05252; }
.perfil-valor-principal { font-size: 1.3rem; font-weight: 800; color: #e0e0e0; margin: .2rem 0; }
.perfil-detalhe { font-size: .78rem; color: #999; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def buscar_preco(ticker):
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

ATIVOS = {
    "PETR4":"Petrobras PN","VALE3":"Vale ON","ITUB4":"Itaú PN",
    "BBDC4":"Bradesco PN","BBAS3":"BB ON","ABEV3":"Ambev ON",
    "WEGE3":"Weg ON","MGLU3":"Magalu ON","PRIO3":"PetroRio ON",
    "GGBR4":"Gerdau PN","SUZB3":"Suzano ON","BPAC11":"BTG UNT",
    "LREN3":"Renner ON","VIVT3":"Telefônica ON","RENT3":"Localiza ON",
    "OUTRO":"Outro (manual)",
}

def fmt_r(v, d=4): return f"R$ {v:,.{d}f}"
def fmt_p(v, d=2): return f"{v:.{d}f}%"

def rule_box(regras, titulo="💡 Regras RCO"):
    conteudo = "".join(f"<li>{r}</li>" for r in regras)
    st.markdown(
        f'<div class="rule-box"><strong>{titulo}</strong>'
        f'<ul style="margin:.4rem 0 0 1rem;padding:0">{conteudo}</ul></div>',
        unsafe_allow_html=True)

def rotular_perfis(n):
    """Distribui N variações em 3 perfis: Conservadora, Moderada, Agressiva."""
    if n <= 1:
        return ["Moderada"]
    if n == 2:
        return ["Conservadora", "Agressiva"]
    if n == 3:
        return ["Conservadora", "Moderada", "Agressiva"]
    # para N>3, distribui igualmente em 3 grupos
    terco = n / 3
    labels = []
    for i in range(n):
        if i < terco:
            labels.append("Conservadora")
        elif i < terco * 2:
            labels.append("Moderada")
        else:
            labels.append("Agressiva")
    return labels

def card_perfil(label, valor_principal, detalhes_html, key, selecionado=False):
    """Renderiza um card clicável (via botão invisível) para cada variação."""
    tag_class = {"Conservadora": "tag-conservadora",
                 "Moderada": "tag-moderada",
                 "Agressiva": "tag-agressiva"}.get(label, "tag-moderada")
    sel_class = "selecionado" if selecionado else ""
    st.markdown(f"""
    <div class="perfil-card {sel_class}">
        <span class="perfil-tag {tag_class}">{label}</span>
        <div class="perfil-valor-principal">{valor_principal}</div>
        <div class="perfil-detalhe">{detalhes_html}</div>
    </div>
    """, unsafe_allow_html=True)
    return st.button("Ver payoff", key=key, width="stretch")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Ativo")
    ticker_sel = st.selectbox("Papel", list(ATIVOS.keys()),
                              format_func=lambda t: f"{t} — {ATIVOS[t]}")
    preco_auto = None
    if ticker_sel != "OUTRO":
        with st.spinner(f"Buscando {ticker_sel}..."):
            preco_auto = buscar_preco(ticker_sel)
        if preco_auto:
            st.success(f"💹 R$ {preco_auto:.2f}")
        else:
            st.warning("Digite manualmente.")

    S = st.number_input("Preço (R$)", min_value=0.01,
                        value=float(preco_auto or 30.0), step=0.50, format="%.2f")

    st.markdown("---")
    vi_pct  = st.slider("Volatilidade Implícita (%)", 5, 120, 35)
    dias    = st.slider("Dias até o vencimento (referência)", 5, 180, 21)
    taxa    = st.number_input("Taxa livre de risco (%)", value=14.50, step=0.25, format="%.2f")
    tend    = st.selectbox("Tendência", ["Alta","Baixa","Lateral","Indefinida"])
    iv_rank = st.slider("IV Rank", 0, 100, 50)
    capital = st.number_input("Capital total (R$)", value=50_000.0, step=1_000.0, format="%.2f")

    st.markdown("---")
    n_variacoes = st.slider("🔢 Variações por estratégia", min_value=3, max_value=9, value=3,
                            step=3,
                            help="Múltiplos de 3 para separar igualmente entre Conservadora/Moderada/Agressiva")

    st.markdown("---")
    st.markdown('<div class="aviso">⚠️ Fins educacionais.</div>', unsafe_allow_html=True)

mkt = Mercado(S=S, vi=vi_pct/100, dias=dias, taxa_juros=taxa/100,
              tendencia=tend.lower(), iv_rank=iv_rank)
ticker_label = ticker_sel if ticker_sel != "OUTRO" else "—"

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"## 🎯 Estratégias RCO — {ticker_label}")
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("Spot",       f"R$ {S:.2f}")
c2.metric("VI",         f"{vi_pct}%",
          delta="Alta→vender" if vi_pct>=35 else "Baixa→comprar",
          delta_color="normal" if vi_pct>=35 else "inverse")
c3.metric("Dias ref.",  f"{dias}d")
c4.metric("IV Rank",    f"{iv_rank}/100")
c5.metric("Tendência",  tend)
st.divider()

tabs = st.tabs(["🎯 Recomendação","💼 Venda Coberta","🔻 Venda Put",
                "🔄 WHEEL","📈 Trava Alta","📉 Trava Baixa",
                "💥 Straddle/Strangle","🛡️ Gestão Risco"])

# ── Recomendação ─────────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("Recomendação Inteligente")
    col_a, col_b = st.columns(2)
    with col_a:
        vi_lbl = "Alta (vender prêmio)" if vi_pct>=35 else ("Baixa (comprar)" if vi_pct<25 else "Neutra")
        st.info(f"Ativo: **{ticker_label}** | Spot: **R$ {S:.2f}**")
        st.info(f"VI: **{vi_pct}%** — {vi_lbl}")
        st.info(f"IV Rank: **{iv_rank}/100**")
        st.info(f"Tendência: **{tend}** | Dias: **{dias}**")
    recs = recomendar(mkt)
    with col_b:
        for r in recs:
            css = "rec-alta" if r["prioridade"]=="Alta" else "rec-media"
            prio_badge = "🟢 Alta" if r["prioridade"]=="Alta" else "🟡 Média"
            st.markdown(
                f'<div class="rec-card {css}"><strong>{r["emoji"]} {r["nome"]}</strong>'
                f' &nbsp; {prio_badge}<br>'
                f'<span style="font-size:.87rem;color:#aaa">{r["motivo"]}</span></div>',
                unsafe_allow_html=True)
    st.caption(f"👉 Veja {n_variacoes} variações prontas em cards (Conservadora/Moderada/Agressiva) nas abas acima.")

# ── Venda Coberta ─────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader(f"💼 Venda Coberta — {ticker_label}")
    st.caption("Escolha o perfil de risco — clique no card para ver o payoff")

    dados = gerar_venda_coberta_variacoes(mkt, n_variacoes)
    labels = rotular_perfis(len(dados))

    if "vc_idx" not in st.session_state:
        st.session_state.vc_idx = 0

    cols = st.columns(len(dados))
    for i, (col, d, label) in enumerate(zip(cols, dados, labels)):
        with col:
            detalhes = (f"Strike R$ {d['strike']:.2f} · {d['dias']}d<br>"
                        f"Delta {d['delta']:.2f} · Theta {d['theta']:.4f}<br>"
                        f"BE: R$ {d['breakeven']:.2f}")
            clicado = card_perfil(label, f"+{d['retorno_pct']}%", detalhes,
                                  key=f"vc_btn_{i}", selecionado=(st.session_state.vc_idx==i))
            if clicado:
                st.session_state.vc_idx = i

    d_sel = dados[st.session_state.vc_idx]
    K_sel = d_sel["strike"]

    st.markdown(f"**Payoff: Strike R$ {K_sel:.2f} · {d_sel['dias']} dias · Prêmio R$ {d_sel['premio']:.4f}**")
    spots = [round(S*m,2) for m in [x/100 for x in range(80,131,2)]]
    payoffs = [{"Spot":sp,"P&L":round(d_sel["premio"] if sp<=K_sel else d_sel["premio"]-(sp-K_sel),4)} for sp in spots]
    st.line_chart(pd.DataFrame(payoffs).set_index("Spot"))

    with st.expander("📋 Ver tabela completa"):
        df = pd.DataFrame([{
            "Perfil": l, "Strike":f"R$ {d['strike']:.2f}", "Vencimento":f"{d['dias']}d",
            "Prêmio":d["premio"], "Retorno":f"{d['retorno_pct']}%",
            "Retorno anualiz.":f"{d['retorno_anualizado_pct']}%",
            "Delta":d["delta"], "Theta/dia":d["theta"], "Break-even":f"R$ {d['breakeven']:.2f}"}
            for d, l in zip(dados, labels)])
        st.dataframe(df, width="stretch", hide_index=True)

    rule_box(["Vender CALL OTM com delta 0.15–0.35","Vencimentos 15–30 dias (theta alto)",
              "Rolar se ativo se aproximar do strike","Meta: 2%–4% ao mês sobre as ações"])

# ── Venda Put ─────────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader(f"🔻 Venda de Put — {ticker_label}")
    st.caption("Escolha o perfil de risco — clique no card para ver detalhes")

    dados = gerar_venda_put_variacoes(mkt, n_variacoes)
    labels = rotular_perfis(len(dados))

    if "vp_idx" not in st.session_state:
        st.session_state.vp_idx = 0

    cols = st.columns(len(dados))
    for i, (col, d, label) in enumerate(zip(cols, dados, labels)):
        with col:
            detalhes = (f"Strike R$ {d['strike']:.2f} · {d['dias']}d<br>"
                        f"Preço efetivo: R$ {d['preco_efetivo']:.2f}<br>"
                        f"Desconto: {d['desconto_pct']}%")
            clicado = card_perfil(label, f"R$ {d['premio']:.4f}", detalhes,
                                  key=f"vp_btn_{i}", selecionado=(st.session_state.vp_idx==i))
            if clicado:
                st.session_state.vp_idx = i

    d_sel = dados[st.session_state.vp_idx]
    K_sel = d_sel["strike"]

    st.markdown(f"**Payoff: Strike R$ {K_sel:.2f} · {d_sel['dias']} dias · Prêmio R$ {d_sel['premio']:.4f}**")
    spots = [round(S*m,2) for m in [x/100 for x in range(70,121,2)]]
    payoffs = [{"Spot":sp,"P&L":round(d_sel["premio"] if sp>=K_sel else d_sel["premio"]-(K_sel-sp),4)} for sp in spots]
    st.line_chart(pd.DataFrame(payoffs).set_index("Spot"))

    with st.expander("📋 Ver tabela completa"):
        df = pd.DataFrame([{
            "Perfil": l, "Strike":f"R$ {d['strike']:.2f}", "Vencimento":f"{d['dias']}d",
            "Prêmio":d["premio"], "Preço efetivo":f"R$ {d['preco_efetivo']:.2f}",
            "Desconto":f"{d['desconto_pct']}%","Delta":d["delta"],"Theta/dia":d["theta"]}
            for d, l in zip(dados, labels)])
        st.dataframe(df, width="stretch", hide_index=True)

    rule_box(["Usar apenas em ativos que você QUER ter","Strike OTM 5%–15% abaixo do spot",
              "Manter capital para o exercício","Combinar com Venda Coberta → WHEEL"])

# ── WHEEL ─────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader(f"🔄 WHEEL — {ticker_label}")
    st.caption("Escolha o ciclo — clique no card para ver detalhes")

    dados = gerar_wheel_variacoes(mkt, n_variacoes)
    labels = rotular_perfis(len(dados))

    if "wh_idx" not in st.session_state:
        st.session_state.wh_idx = 0

    cols = st.columns(len(dados))
    for i, (col, d, label) in enumerate(zip(cols, dados, labels)):
        with col:
            detalhes = (f"Put R$ {d['K_put']:.2f} / Call R$ {d['K_call']:.2f}<br>"
                        f"{d['dias']}d · Anualiz. {d['retorno_anualizado_pct']}%")
            clicado = card_perfil(label, f"+{d['retorno_pct']}%", detalhes,
                                  key=f"wh_btn_{i}", selecionado=(st.session_state.wh_idx==i))
            if clicado:
                st.session_state.wh_idx = i

    d_sel = dados[st.session_state.wh_idx]
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown(f"**Fase 1 — Venda Put** · Strike R$ {d_sel['K_put']:.2f} · Prêmio R$ {d_sel['premio_put']:.4f}")
    with col_r:
        st.markdown(f"**Fase 2 — Venda Coberta** · Strike R$ {d_sel['K_call']:.2f} · Prêmio R$ {d_sel['premio_call']:.4f}")
    st.metric("Renda total do ciclo", f"R$ {d_sel['renda_total']:.4f}",
              delta=f"{d_sel['retorno_pct']}% ({d_sel['retorno_anualizado_pct']}% anualizado)")

    with st.expander("📋 Ver tabela completa"):
        df = pd.DataFrame([{
            "Perfil": l, "Vencimento": f"{d['dias']}d",
            "Put strike": f"R$ {d['K_put']:.2f}", "Call strike": f"R$ {d['K_call']:.2f}",
            "Prêmio Put": d["premio_put"], "Prêmio Call": d["premio_call"],
            "Renda/ciclo": d["renda_total"], "Retorno": f"{d['retorno_pct']}%",
        } for d, l in zip(dados, labels)])
        st.dataframe(df, width="stretch", hide_index=True)

    rule_box(["Use em blue chips líquidas (PETR4, VALE3, ITUB4)","Máx 30% do capital por posição",
              "Rolar a put se o ativo cair muito","Meta: 3%–5% ao mês sobre o capital"])

# ── Trava Alta ────────────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader(f"📈 Trava de Alta — {ticker_label}")
    st.caption("Largura do spread por perfil de risco — clique no card para ver o payoff")

    dados = gerar_trava_alta_variacoes(mkt, n_variacoes)
    labels = rotular_perfis(len(dados))

    if "ta_idx" not in st.session_state:
        st.session_state.ta_idx = 0

    cols = st.columns(len(dados))
    for i, (col, d, label) in enumerate(zip(cols, dados, labels)):
        with col:
            detalhes = (f"K1 R$ {d['K1']:.2f} / K2 R$ {d['K2']:.2f}<br>"
                        f"Largura {d['largura_pct']}% · {d['dias']}d<br>"
                        f"R/R 1:{d['rr']}")
            clicado = card_perfil(label, f"R$ {d['lucro_max']:.2f}", detalhes,
                                  key=f"ta_btn_{i}", selecionado=(st.session_state.ta_idx==i))
            if clicado:
                st.session_state.ta_idx = i

    t = dados[st.session_state.ta_idx]
    st.markdown(f"**Payoff: K1 R$ {t['K1']:.2f} → K2 R$ {t['K2']:.2f} · Débito R$ {t['debito']:.4f}**")
    spots=[round(S*m,2) for m in [x/100 for x in range(85,120)]]
    rows=[{"Spot":sp,"P&L":round(max(min(sp-t["K1"],t["K2"]-t["K1"]),0)-t["debito"],4)} for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))

    with st.expander("📋 Ver tabela completa"):
        df = pd.DataFrame([{
            "Perfil": l, "Vencimento": f"{d['dias']}d", "Largura": f"{d['largura_pct']}%",
            "K1": f"R$ {d['K1']:.2f}", "K2": f"R$ {d['K2']:.2f}",
            "Débito": d["debito"], "Lucro máx": d["lucro_max"],
            "Break-even": f"R$ {d['breakeven']:.2f}", "R/R": f"1:{d['rr']}",
        } for d, l in zip(dados, labels)])
        st.dataframe(df, width="stretch", hide_index=True)

    rule_box(["Alta confirmada na análise técnica","IFR + Bandas de Bollinger",
              "Fechar com 50% do lucro máximo","Máx 5% do capital por operação"])

# ── Trava Baixa ───────────────────────────────────────────────────────────────
with tabs[5]:
    st.subheader(f"📉 Trava de Baixa — {ticker_label}")
    st.caption("Largura do spread por perfil de risco")

    dados = gerar_trava_baixa_variacoes(mkt, n_variacoes)
    labels = rotular_perfis(len(dados))

    if "tb_idx" not in st.session_state:
        st.session_state.tb_idx = 0

    cols = st.columns(len(dados))
    for i, (col, d, label) in enumerate(zip(cols, dados, labels)):
        with col:
            detalhes = (f"K1 R$ {d['K1']:.2f} / K2 R$ {d['K2']:.2f}<br>"
                        f"Largura {d['largura_pct']}% · {d['dias']}d<br>"
                        f"R/R 1:{d['rr']}")
            clicado = card_perfil(label, f"R$ {d['lucro_max']:.2f}", detalhes,
                                  key=f"tb_btn_{i}", selecionado=(st.session_state.tb_idx==i))
            if clicado:
                st.session_state.tb_idx = i

    tb = dados[st.session_state.tb_idx]
    st.markdown(f"**Payoff: K1 R$ {tb['K1']:.2f} → K2 R$ {tb['K2']:.2f} · Débito R$ {tb['debito']:.4f}**")
    spots=[round(S*m,2) for m in [x/100 for x in range(85,115)]]
    rows=[{"Spot":sp,"P&L":round(max(min(tb["K1"]-sp,tb["K1"]-tb["K2"]),0)-tb["debito"],4)} for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))

    with st.expander("📋 Ver tabela completa"):
        df = pd.DataFrame([{
            "Perfil": l, "Vencimento": f"{d['dias']}d", "Largura": f"{d['largura_pct']}%",
            "K1": f"R$ {d['K1']:.2f}", "K2": f"R$ {d['K2']:.2f}",
            "Débito": d["debito"], "Lucro máx": d["lucro_max"],
            "Break-even": f"R$ {d['breakeven']:.2f}", "R/R": f"1:{d['rr']}",
        } for d, l in zip(dados, labels)])
        st.dataframe(df, width="stretch", hide_index=True)

    rule_box(["IFR >70 com resistência clara","Usar como hedge da carteira","Máx 3%–5% do capital"])

# ── Straddle ─────────────────────────────────────────────────────────────────
with tabs[6]:
    st.subheader(f"💥 Straddle/Strangle — {ticker_label}")
    st.caption("De Straddle ATM até Strangle largo — clique no card para ver o payoff")

    dados = gerar_straddle_strangle_variacoes(mkt, n_variacoes)
    labels = rotular_perfis(len(dados))

    if "ss_idx" not in st.session_state:
        st.session_state.ss_idx = 0

    cols = st.columns(len(dados))
    for i, (col, d, label) in enumerate(zip(cols, dados, labels)):
        with col:
            detalhes = (f"{d['nome']} · {d['dias']}d<br>"
                        f"K Put R$ {d['K_put']:.2f} / K Call R$ {d['K_call']:.2f}<br>"
                        f"Mov. necessário: ±{d['mov_necessario_pct']}%")
            clicado = card_perfil(label, f"R$ {d['custo_total']:.2f}", detalhes,
                                  key=f"ss_btn_{i}", selecionado=(st.session_state.ss_idx==i))
            if clicado:
                st.session_state.ss_idx = i

    ss = dados[st.session_state.ss_idx]
    st.markdown(f"**Payoff: {ss['nome']} · Custo total R$ {ss['custo_total']:.4f}**")
    spots=np.linspace(S*0.75,S*1.30,200)
    rows=[{"Spot":sp,
           "P&L":round((max(sp-ss["K_call"],0)+max(ss["K_put"]-sp,0))-ss["custo_total"],4)}
          for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))

    with st.expander("📋 Ver tabela completa"):
        df = pd.DataFrame([{
            "Perfil": l, "Estrutura": d["nome"], "Vencimento": f"{d['dias']}d",
            "K Put": f"R$ {d['K_put']:.2f}", "K Call": f"R$ {d['K_call']:.2f}",
            "Custo total": d["custo_total"],
            "BE inferior": f"R$ {d['be_inf']:.2f}", "BE superior": f"R$ {d['be_sup']:.2f}",
            "Mov. necessário": f"±{d['mov_necessario_pct']}%",
        } for d, l in zip(dados, labels)])
        st.dataframe(df, width="stretch", hide_index=True)

    rule_box(["Usar em eventos: COPOM, resultados, eleições","VI baixa = melhor hora para comprar",
              "Stop: -50% do valor pago","Saída parcial em +100%","Venc mínimo: 20–30 dias"])

# ── Gestão de Risco ───────────────────────────────────────────────────────────
with tabs[7]:
    st.subheader("🛡️ Gestão de Risco")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Máx opção longa (3%)", f"R$ {capital*.03:,.0f}")
    c2.metric("Máx trava (5%)",        f"R$ {capital*.05:,.0f}")
    c3.metric("Reserva exercício (30%)",f"R$ {capital*.30:,.0f}")
    c4.metric("Meta renda mensal (3%)", f"R$ {capital*.03:,.0f}")
    st.markdown("---")
    col_l,col_r = st.columns(2)
    with col_l:
        st.markdown("#### Regras de Saída")
        st.markdown("""
| Operação | Take Profit | Stop |
|---|---|---|
| Opção longa | +100% (parcial 50%) | -50% |
| Trava | 50% lucro máx | -100% débito |
| Venda coberta | Vira pó ✅ | Recomprar 200% |
| Venda put | Vira pó ✅ | Rolar para frente |
        """)
    with col_r:
        st.markdown("#### Calculadora de Posição")
        risco_pct   = st.slider("Risco máximo (%)", 1, 10, 3)
        custo_opc   = st.number_input("Custo da opção (R$)", value=0.50, step=0.01, format="%.4f")
        lote        = st.number_input("Lote mínimo", value=100, step=100)
        risco_cap   = capital * risco_pct / 100
        qtd         = max(1, int(risco_cap / (custo_opc * lote)))
        st.success(f"**{qtd*lote:,} opções** | R$ {qtd*lote*custo_opc:,.2f} ({qtd*lote*custo_opc/capital*100:.1f}%)")
        for c in ["Ativo líquido nas opções?","Sem evento surpresa?","Plano de saída definido?","IFR + BB verificados?"]:
            st.checkbox(c, key=f"ck_{c[:15]}")

st.divider()
st.caption("🎯 Estratégias RCO · Método Jimmy Carvalho · Apenas fins educacionais")
