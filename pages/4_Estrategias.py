"""
Estratégias RCO — Venda Coberta, Wheel, Travas, Straddle
"""
import streamlit as st
import pandas as pd
import requests
from rco_core import (
    Mercado, calc_venda_coberta, calc_venda_put, calc_wheel,
    calc_trava_alta, calc_trava_baixa, calc_straddle_strangle, recomendar,
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
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def buscar_preco(ticker):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        p = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return round(float(p), 2)
    except Exception:
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
    dias    = st.slider("Dias até o vencimento", 5, 180, 21)
    taxa    = st.number_input("Taxa livre de risco (%)", value=14.50, step=0.25, format="%.2f")
    tend    = st.selectbox("Tendência", ["Alta","Baixa","Lateral","Indefinida"])
    iv_rank = st.slider("IV Rank", 0, 100, 50)
    capital = st.number_input("Capital total (R$)", value=50_000.0, step=1_000.0, format="%.2f")

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
c3.metric("Dias",       f"{dias}d")
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

# ── Venda Coberta ─────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader(f"💼 Venda Coberta — {ticker_label}")
    dados = calc_venda_coberta(mkt)
    df = pd.DataFrame([{"Strike":f"R$ {d['strike']:.2f}","Moneyness":d["moneyness"],
        "Prêmio":d["premio"],"Retorno %":f"{d['retorno_pct']}%",
        "Delta":d["delta"],"Theta/dia":d["theta"],"Break-even":f"R$ {d['breakeven']:.2f}"}
        for d in dados])
    st.dataframe(df, width="stretch", hide_index=True)
    K_sel = st.selectbox("Strike para payoff", [d["strike"] for d in dados], key="vc")
    d_s = next(d for d in dados if d["strike"]==K_sel)
    spots = [round(S*m,2) for m in [x/100 for x in range(80,131,2)]]
    payoffs = [{"Spot":sp,"P&L":round(d_s["premio"] if sp<=K_sel else d_s["premio"]-(sp-K_sel),4)} for sp in spots]
    st.line_chart(pd.DataFrame(payoffs).set_index("Spot"))
    rule_box(["Vender CALL OTM com delta 0.15–0.35","Vencimentos 15–30 dias (theta alto)",
              "Rolar se ativo se aproximar do strike","Meta: 2%–4% ao mês sobre as ações"])

# ── Venda Put ─────────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader(f"🔻 Venda de Put — {ticker_label}")
    dados = calc_venda_put(mkt)
    df = pd.DataFrame([{"Strike":f"R$ {d['strike']:.2f}","Moneyness":d["moneyness"],
        "Prêmio":d["premio"],"Preço efetivo":f"R$ {d['preco_efetivo']:.2f}",
        "Desconto":f"{d['desconto_pct']}%","Delta":d["delta"],"Theta/dia":d["theta"]}
        for d in dados])
    st.dataframe(df, width="stretch", hide_index=True)
    rule_box(["Usar apenas em ativos que você QUER ter","Strike OTM 5%–10% abaixo do spot",
              "Manter capital para o exercício","Combinar com Venda Coberta → WHEEL"])

# ── WHEEL ─────────────────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader(f"🔄 WHEEL — {ticker_label}")
    w = calc_wheel(mkt)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Put strike",   f"R$ {w['K_put']:.2f}")
    c2.metric("Call strike",  f"R$ {w['K_call']:.2f}")
    c3.metric("Renda/ciclo",  fmt_r(w["renda_total"]))
    c4.metric("Retorno/ciclo",fmt_p(w["retorno_pct"]))
    col_l,col_r = st.columns(2)
    with col_l:
        st.markdown(f"**Fase 1 — Venda Put** · Strike R$ {w['K_put']:.2f} · Prêmio R$ {w['premio_put']:.4f}")
    with col_r:
        st.markdown(f"**Fase 2 — Venda Coberta** · Strike R$ {w['K_call']:.2f} · Prêmio R$ {w['premio_call']:.4f}")
    rule_box(["Use em blue chips líquidas (PETR4, VALE3, ITUB4)","Máx 30% do capital por posição",
              "Rolar a put se o ativo cair muito","Meta: 3%–5% ao mês sobre o capital"])

# ── Trava Alta ────────────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader(f"📈 Trava de Alta — {ticker_label}")
    t = calc_trava_alta(mkt)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Débito",      fmt_r(t["debito"]))
    c2.metric("Lucro máx",   fmt_r(t["lucro_max"]))
    c3.metric("Break-even",  f"R$ {t['breakeven']:.2f}")
    c4.metric("R/R",         f"1:{t['rr']}")
    spots=[round(S*m,2) for m in [x/100 for x in range(85,120)]]
    rows=[{"Spot":sp,"P&L":round(max(min(sp-t["K1"],t["K2"]-t["K1"]),0)-t["debito"],4)} for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))
    rule_box(["Alta confirmada na análise técnica","IFR + Bandas de Bollinger",
              "Fechar com 50% do lucro máximo","Máx 5% do capital por operação"])

# ── Trava Baixa ───────────────────────────────────────────────────────────────
with tabs[5]:
    st.subheader(f"📉 Trava de Baixa — {ticker_label}")
    tb = calc_trava_baixa(mkt)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Débito",      fmt_r(tb["debito"]))
    c2.metric("Lucro máx",   fmt_r(tb["lucro_max"]))
    c3.metric("Break-even",  f"R$ {tb['breakeven']:.2f}")
    c4.metric("R/R",         f"1:{tb['rr']}")
    spots=[round(S*m,2) for m in [x/100 for x in range(85,115)]]
    rows=[{"Spot":sp,"P&L":round(max(min(tb["K1"]-sp,tb["K1"]-tb["K2"]),0)-tb["debito"],4)} for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))
    rule_box(["IFR >70 com resistência clara","Usar como hedge da carteira","Máx 3%–5% do capital"])

# ── Straddle ─────────────────────────────────────────────────────────────────
with tabs[6]:
    st.subheader(f"💥 Straddle/Strangle — {ticker_label}")
    ss = calc_straddle_strangle(mkt)
    col_l,col_r = st.columns(2)
    with col_l:
        st.markdown("#### Straddle (ATM)")
        st.metric("Custo", fmt_r(ss["custo_straddle"]))
        st.markdown(f"Break-even sup: **R$ {ss['be_sup_std']:.2f}** | inf: **R$ {ss['be_inf_std']:.2f}**")
        st.markdown(f"Movimento necessário: **±{ss['mov_necessario_pct']:.1f}%**")
    with col_r:
        st.markdown("#### Strangle (OTM ±5%)")
        st.metric("Custo", fmt_r(ss["custo_strangle"]),
                  delta=f"{ss['economia_strangle_pct']:.1f}% mais barato", delta_color="normal")
    import numpy as np
    spots=np.linspace(S*0.75,S*1.30,200)
    rows=[{"Spot":sp,
           "Straddle":round((max(sp-ss["K_atm"],0)+max(ss["K_atm"]-sp,0))-ss["custo_straddle"],4),
           "Strangle":round((max(sp-ss["K_call"],0)+max(ss["K_put"]-sp,0))-ss["custo_strangle"],4)}
          for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))
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
