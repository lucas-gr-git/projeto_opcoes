"""
app.py — RCO Assistant (Streamlit)
Recomendador de Opções baseado no método Jimmy Carvalho (RCO)
"""

import streamlit as st
import pandas as pd
import math
import requests
from rco_core import (
    Mercado, black_scholes, gregas, moneyness,
    calc_venda_coberta, calc_venda_put, calc_wheel,
    calc_trava_alta, calc_trava_baixa, calc_straddle_strangle,
    recomendar,
)

# ── Config ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="RCO Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main-title {
        font-size: 2rem; font-weight: 800;
        background: linear-gradient(135deg, #1f77b4, #2ca02c);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-title { color: #666; font-size: 0.9rem; margin-top: 0; }
    .rec-card {
        border-radius: 10px; padding: 1rem 1.2rem;
        margin-bottom: 0.6rem;
        border-left: 5px solid;
    }
    .rec-alta  { background: #eafaf1; border-color: #2ca02c; }
    .rec-media { background: #fef9e7; border-color: #f39c12; }
    .rec-baixa { background: #fef2f2; border-color: #e74c3c; }
    .rule-box {
        background: #eef6fb; border-left: 4px solid #1f77b4;
        padding: 0.8rem 1rem; border-radius: 6px;
        font-size: 0.88rem; margin-top: 1rem;
    }
    .aviso {
        background: #fff8e1; border-left: 4px solid #f39c12;
        padding: 0.7rem 1rem; border-radius: 6px;
        font-size: 0.82rem; color: #7d6608;
    }
    div[data-testid="stTabs"] button { font-size: 0.85rem; }
    .ticker-badge {
        display: inline-block; background: #1f77b4; color: white;
        padding: 2px 10px; border-radius: 12px; font-weight: 700;
        font-size: 1rem; letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)


# ── Ativos mais líquidos em opções na B3 ──────────────────────────────────

ATIVOS = {
    # Ticker : (nome, setor)
    "PETR4": ("Petrobras PN",          "Energia"),
    "VALE3": ("Vale ON",               "Mineração"),
    "ITUB4": ("Itaú Unibanco PN",      "Financeiro"),
    "BBDC4": ("Bradesco PN",           "Financeiro"),
    "BBAS3": ("Banco do Brasil ON",    "Financeiro"),
    "ABEV3": ("Ambev ON",              "Consumo"),
    "MGLU3": ("Magazine Luiza ON",     "Varejo"),
    "WEGE3": ("Weg ON",                "Industrial"),
    "RENT3": ("Localiza ON",           "Mobilidade"),
    "GGBR4": ("Gerdau PN",             "Siderurgia"),
    "SUZB3": ("Suzano ON",             "Papel/Celulose"),
    "RDOR3": ("Rede D'Or ON",          "Saúde"),
    "PRIO3": ("PetroRio ON",           "Energia"),
    "BPAC11": ("BTG Pactual UNT",      "Financeiro"),
    "EQTL3": ("Equatorial ON",         "Energia"),
    "VIVT3": ("Telefônica ON",         "Telecom"),
    "CSAN3": ("Cosan ON",              "Energia"),
    "UGPA3": ("Ultrapar ON",           "Energia"),
    "BRFS3": ("BRF ON",                "Alimentos"),
    "LREN3": ("Lojas Renner ON",       "Varejo"),
    "OUTRO": ("Outro (digitar manualmente)", ""),
}

@st.cache_data(ttl=300)  # cache 5 minutos
def buscar_preco(ticker: str) -> float | None:
    """Busca o preço via Yahoo Finance. Retorna None se falhar."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=6)
        data = r.json()
        preco = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return round(float(preco), 2)
    except Exception:
        try:
            url2 = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA"
            r2 = requests.get(url2, headers=headers, timeout=6)
            data2 = r2.json()
            preco2 = data2["chart"]["result"][0]["meta"]["regularMarketPrice"]
            return round(float(preco2), 2)
        except Exception:
            return None


# ── Helpers ────────────────────────────────────────────────────────────────

def fmt_r(v, decimais=4):
    return f"R$ {v:,.{decimais}f}"

def fmt_pct(v, decimais=2):
    return f"{v:.{decimais}f}%"

def badge_prio(p):
    if p == "Alta":   return "🟢 Alta"
    if p == "Média":  return "🟡 Média"
    return "🔴 Baixa"

def rule_box(regras: list, titulo="💡 Regras RCO"):
    conteudo = "".join(f"<li>{r}</li>" for r in regras)
    st.markdown(
        f'<div class="rule-box"><strong>{titulo}</strong>'
        f'<ul style="margin:0.4rem 0 0 1rem;padding:0">{conteudo}</ul></div>',
        unsafe_allow_html=True,
    )


# ── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📈 Ativo")

    ticker_sel = st.selectbox(
        "Selecione o papel",
        options=list(ATIVOS.keys()),
        format_func=lambda t: f"{t} — {ATIVOS[t][0]}" if ATIVOS[t][1] else t,
    )

    nome_ativo, setor_ativo = ATIVOS[ticker_sel]

    # Busca automática de preço (exceto "OUTRO")
    preco_auto = None
    if ticker_sel != "OUTRO":
        with st.spinner(f"Buscando cotação de {ticker_sel}..."):
            preco_auto = buscar_preco(ticker_sel)

        if preco_auto:
            st.success(f"💹 Cotação: **R$ {preco_auto:.2f}**")
        else:
            st.warning("⚠️ Não foi possível buscar a cotação. Digite manualmente.")

    # Preço — preenchido automaticamente se disponível
    valor_default = preco_auto if preco_auto else 30.0
    S = st.number_input(
        "Preço do ativo (R$)",
        min_value=0.01,
        value=float(valor_default),
        step=0.50,
        format="%.2f",
        help="Preenchido automaticamente. Você pode ajustar manualmente.",
    )

    if ticker_sel == "OUTRO":
        ticker_label = st.text_input("Código do papel (ex: XXXX3)", value="").upper()
    else:
        ticker_label = ticker_sel

    st.markdown("---")
    st.markdown("## ⚙️ Parâmetros da Opção")

    vi_pct = st.slider("Volatilidade Implícita (%)", 5, 120, 35,
                       help="VI da série que você quer operar. Veja no home broker.")
    dias   = st.slider("Dias até o vencimento", 5, 180, 21)
    taxa   = st.number_input("Taxa livre de risco (% a.a.)", min_value=0.0,
                              max_value=50.0, value=10.75, step=0.25, format="%.2f")

    st.markdown("---")
    tendencia = st.selectbox("Tendência do ativo",
                             ["Alta", "Baixa", "Lateral", "Indefinida"])
    iv_rank   = st.slider("IV Rank", 0, 100, 50,
                          help="0 = VI historicamente baixa | 100 = historicamente alta")

    st.markdown("---")
    capital = st.number_input("Seu capital total (R$)", min_value=100.0,
                               value=50_000.0, step=1_000.0, format="%.2f")

    st.markdown("---")
    st.markdown(
        '<div class="aviso">⚠️ Fins educacionais. '
        'Não constitui recomendação de investimento.</div>',
        unsafe_allow_html=True,
    )

# ── Objeto Mercado ─────────────────────────────────────────────────────────

mkt = Mercado(
    S=S,
    vi=vi_pct / 100,
    dias=dias,
    taxa_juros=taxa / 100,
    tendencia=tendencia.lower(),
    iv_rank=iv_rank,
)

# ── Header ─────────────────────────────────────────────────────────────────

col_t, col_badge = st.columns([5, 1])
with col_t:
    st.markdown('<p class="main-title">📊 RCO Assistant</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-title">Recomendador de Opções — baseado na metodologia Jimmy Carvalho (Renda Com Opções)</p>',
        unsafe_allow_html=True,
    )
with col_badge:
    if ticker_label:
        st.markdown(f'<br><span class="ticker-badge">{ticker_label}</span>', unsafe_allow_html=True)
        if setor_ativo:
            st.caption(setor_ativo)

# ── Métricas rápidas ───────────────────────────────────────────────────────

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Spot",        f"R$ {S:.2f}")
c2.metric("VI",          f"{vi_pct}%",
          delta="Alta → vender" if vi_pct >= 35 else "Baixa → comprar",
          delta_color="normal" if vi_pct >= 35 else "inverse")
c3.metric("Dias p/ venc.", f"{dias}d")
c4.metric("IV Rank",    f"{iv_rank}/100")
c5.metric("Tendência",  tendencia)

st.divider()

# ── Abas ───────────────────────────────────────────────────────────────────

tabs = st.tabs([
    "🎯 Recomendação",
    "💼 Venda Coberta",
    "🔻 Venda de Put",
    "🔄 WHEEL",
    "📈 Trava de Alta",
    "📉 Trava de Baixa",
    "💥 Straddle / Strangle",
    "🛡️ Gestão de Risco",
])

# ── ABA 0 — RECOMENDAÇÃO ───────────────────────────────────────────────────

with tabs[0]:
    st.subheader("Recomendação Inteligente — Método RCO")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("**Cenário detectado**")
        vi_label = ("Alta (vender prêmio 🏷️)" if vi_pct >= 35
                    else ("Baixa (comprar opção 🎯)" if vi_pct < 25 else "Neutra"))
        st.info(f"Ativo: **{ticker_label}** | Spot: **R$ {S:.2f}**")
        st.info(f"VI: **{vi_pct}%** — {vi_label}")
        st.info(f"IV Rank: **{iv_rank}/100** — {'Prêmios gordos' if iv_rank >= 50 else 'Prêmios magros'}")
        st.info(f"Tendência: **{tendencia}** | Dias: **{dias}**")

    recs = recomendar(mkt)
    with col_b:
        st.markdown("**Estratégias recomendadas**")
        for r in recs:
            css = {"Alta": "rec-alta", "Média": "rec-media", "Baixa": "rec-baixa"}[r["prioridade"]]
            st.markdown(
                f'<div class="rec-card {css}">'
                f'<strong>{r["emoji"]} {r["nome"]}</strong> &nbsp;&nbsp; {badge_prio(r["prioridade"])}<br>'
                f'<span style="font-size:0.87rem;color:#444">{r["motivo"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()
    st.caption("Navegue pelas abas acima para ver os cálculos detalhados de cada estratégia.")


# ── ABA 1 — VENDA COBERTA ──────────────────────────────────────────────────

with tabs[1]:
    st.subheader(f"💼 Venda Coberta de CALL — {ticker_label}")
    st.caption("Pilar principal do método RCO. Renda mensal recorrente sobre ações que você já tem.")

    dados = calc_venda_coberta(mkt)
    df = pd.DataFrame([{
        "Strike":       f"R$ {d['strike']:.2f}",
        "Moneyness":    d["moneyness"],
        "Prêmio (R$)":  d["premio"],
        "Retorno %":    f"{d['retorno_pct']}%",
        "Delta":        d["delta"],
        "Theta/dia":    d["theta"],
        "Break-even":   f"R$ {d['breakeven']:.2f}",
    } for d in dados])
    st.dataframe(df, use_container_width=True, hide_index=True)

    K_sel = st.selectbox("Selecione o strike para o gráfico de payoff",
                         [d["strike"] for d in dados], key="vc_strike")
    d_sel = next(d for d in dados if d["strike"] == K_sel)

    spots = [round(S * m, 2) for m in [x/100 for x in range(80, 131, 2)]]
    payoffs = []
    for sp in spots:
        pnl = d_sel["premio"] if sp <= K_sel else d_sel["premio"] - (sp - K_sel)
        payoffs.append({"Spot no vencimento": sp, "P&L (R$)": round(pnl, 4)})
    st.line_chart(pd.DataFrame(payoffs).set_index("Spot no vencimento"))

    rule_box([
        "Vender CALL OTM com delta entre 0.15 e 0.35",
        "Prefira vencimentos de 15 a 30 dias (theta alto)",
        "Rolar para cima se o ativo se aproximar do strike",
        "Nunca vender coberta com divulgação de resultado próxima",
        "Meta de renda: 2%–4% ao mês sobre o patrimônio em ações",
    ])


# ── ABA 2 — VENDA DE PUT ───────────────────────────────────────────────────

with tabs[2]:
    st.subheader(f"🔻 Venda de Put — {ticker_label}")
    st.caption("Receba prêmio e, se exercida, compre o ativo com desconto.")

    dados = calc_venda_put(mkt)
    df = pd.DataFrame([{
        "Strike":             f"R$ {d['strike']:.2f}",
        "Moneyness":          d["moneyness"],
        "Prêmio (R$)":        d["premio"],
        "Preço efetivo":      f"R$ {d['preco_efetivo']:.2f}",
        "Desconto s/ spot":   f"{d['desconto_pct']}%",
        "Delta":              d["delta"],
        "Theta/dia":          d["theta"],
    } for d in dados])
    st.dataframe(df, use_container_width=True, hide_index=True)

    rule_box([
        "Usar apenas em ativos que você QUER ter na carteira",
        "Strike OTM entre 5%–10% abaixo do spot",
        "Manter capital reservado para o exercício",
        "Combinar com Venda Coberta para criar a estratégia WHEEL",
    ])


# ── ABA 3 — WHEEL ─────────────────────────────────────────────────────────

with tabs[3]:
    st.subheader(f"🔄 Estratégia WHEEL — {ticker_label}")
    st.caption("Venda de Put → exercício → Venda Coberta → ciclo infinito de renda.")

    w = calc_wheel(mkt)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Put strike",    f"R$ {w['K_put']:.2f}")
    c2.metric("Call strike",   f"R$ {w['K_call']:.2f}")
    c3.metric("Renda/ciclo",   fmt_r(w["renda_total"]))
    c4.metric("Retorno/ciclo", fmt_pct(w["retorno_pct"]))

    st.markdown("---")
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("#### Fase 1 — Sem ações")
        st.markdown(f"""
| Campo | Valor |
|---|---|
| Estratégia | Venda de Put |
| Strike | R$ {w['K_put']:.2f} (OTM –5%) |
| Prêmio recebido | R$ {w['premio_put']:.4f} |
        """)
    with col_r:
        st.markdown("#### Fase 2 — Com ações")
        st.markdown(f"""
| Campo | Valor |
|---|---|
| Estratégia | Venda Coberta |
| Strike | R$ {w['K_call']:.2f} (OTM +7%) |
| Prêmio recebido | R$ {w['premio_call']:.4f} |
        """)

    st.markdown("---")
    st.markdown("""
**Fluxo da WHEEL:**
```
Vende Put OTM ──► Put vira pó?
                    ├── SIM → repete fase 1
                    └── NÃO (exercida) → compra ações com desconto
                                              ↓
                             Vende Call OTM ──► Call vira pó?
                                                 ├── SIM → repete fase 2
                                                 └── NÃO (exercida) → vende ações com lucro → fase 1
```
""")

    rule_box([
        "Use apenas em blue chips líquidas: PETR4, VALE3, ITUB4...",
        "Nunca alocar mais de 30% do capital em uma posição da Wheel",
        "Se o ativo cair muito, rolar a put para baixo e para frente",
        "Objetivo: 3%–5% de renda ao mês sobre o capital alocado",
    ])


# ── ABA 4 — TRAVA DE ALTA ─────────────────────────────────────────────────

with tabs[4]:
    st.subheader(f"📈 Trava de Alta — {ticker_label}")
    st.caption("Operação direcional com risco limitado para cenário de alta confirmado.")

    t = calc_trava_alta(mkt)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Débito",       fmt_r(t["debito"]))
    c2.metric("Lucro máximo", fmt_r(t["lucro_max"]))
    c3.metric("Break-even",   f"R$ {t['breakeven']:.2f}")
    c4.metric("R/R",          f"1 : {t['rr']}")

    st.markdown("---")
    st.markdown(f"""
| | Valor |
|---|---|
| Compra CALL K1 ATM (R$ {t['K1']:.2f}) | prêmio pago: R$ {t['c1']:.4f} |
| Vende CALL K2 OTM (R$ {t['K2']:.2f})  | prêmio recebido: R$ {t['c2']:.4f} |
| **Débito líquido** | **R$ {t['debito']:.4f}** |
| **Lucro máximo**   | **R$ {t['lucro_max']:.4f}** (spot ≥ K2 no venc.) |
| Perda máxima       | R$ {t['debito']:.4f} (spot ≤ K1 no venc.) |
    """)

    spots = [round(S * m, 2) for m in [x/100 for x in range(85, 120)]]
    rows = [{"Spot": sp,
             "P&L Trava Alta": round(max(min(sp - t["K1"], t["K2"] - t["K1"]), 0) - t["debito"], 4)}
            for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))

    rule_box([
        "Usar quando há visão direcional de alta confirmada",
        "Verificar IFR e Bandas de Bollinger antes de entrar",
        "Spread ideal: 5%–10% entre os strikes",
        "Busque relação R/R de pelo menos 1:2",
        "Fechar com 50% do lucro máximo (não esperar o vencimento)",
    ])


# ── ABA 5 — TRAVA DE BAIXA ────────────────────────────────────────────────

with tabs[5]:
    st.subheader(f"📉 Trava de Baixa — {ticker_label}")
    st.caption("Operação direcional com risco limitado para cenário de queda confirmado.")

    tb = calc_trava_baixa(mkt)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Débito",       fmt_r(tb["debito"]))
    c2.metric("Lucro máximo", fmt_r(tb["lucro_max"]))
    c3.metric("Break-even",   f"R$ {tb['breakeven']:.2f}")
    c4.metric("R/R",          f"1 : {tb['rr']}")

    st.markdown(f"""
| | Valor |
|---|---|
| Compra PUT K1 ATM (R$ {tb['K1']:.2f}) | prêmio pago: R$ {tb['p1']:.4f} |
| Vende PUT K2 OTM (R$ {tb['K2']:.2f})  | prêmio recebido: R$ {tb['p2']:.4f} |
| **Débito líquido** | **R$ {tb['debito']:.4f}** |
| **Lucro máximo**   | **R$ {tb['lucro_max']:.4f}** (spot ≤ K2 no venc.) |
    """)

    spots = [round(S * m, 2) for m in [x/100 for x in range(85, 115)]]
    rows = [{"Spot": sp,
             "P&L Trava Baixa": round(max(min(tb["K1"] - sp, tb["K1"] - tb["K2"]), 0) - tb["debito"], 4)}
            for sp in spots]
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))

    rule_box([
        "Cenário: ativo sobrecomprado no IFR (>70) com resistência clara",
        "Usar também como hedge da carteira de ações",
        "Não alocar mais de 3%–5% do capital",
        "Fechar com 50% do lucro máximo",
    ])


# ── ABA 6 — STRADDLE / STRANGLE ───────────────────────────────────────────

with tabs[6]:
    st.subheader(f"💥 Straddle / Strangle — {ticker_label}")
    st.caption("Para grandes movimentos esperados. Potencial de ganhos acima de 1000%.")

    ss = calc_straddle_strangle(mkt)

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("#### 🎯 Straddle (ATM)")
        st.metric("Custo total", fmt_r(ss["custo_straddle"]))
        st.markdown(f"""
| Campo | Valor |
|---|---|
| Compra Call ATM ({ss['K_atm']:.2f}) | R$ {ss['call_atm']:.4f} |
| Compra Put ATM  ({ss['K_atm']:.2f}) | R$ {ss['put_atm']:.4f}  |
| Break-even sup. | R$ {ss['be_sup_std']:.2f} |
| Break-even inf. | R$ {ss['be_inf_std']:.2f} |
| Mov. necessário | ±{ss['mov_necessario_pct']:.1f}% |
        """)

    with col_r:
        st.markdown("#### 🔍 Strangle (OTM ±5%)")
        st.metric("Custo total", fmt_r(ss["custo_strangle"]),
                  delta=f"{ss['economia_strangle_pct']:.1f}% mais barato",
                  delta_color="normal")
        st.markdown(f"""
| Campo | Valor |
|---|---|
| Compra Call OTM ({ss['K_call']:.2f}) | R$ {ss['call_otm']:.4f} |
| Compra Put OTM  ({ss['K_put']:.2f})  | R$ {ss['put_otm']:.4f}  |
        """)

    spots = [round(S * m, 2) for m in [x/100 for x in range(75, 130)]]
    rows = []
    for sp in spots:
        pnl_std = (max(sp - ss["K_atm"], 0) + max(ss["K_atm"] - sp, 0)) - ss["custo_straddle"]
        pnl_str = (max(sp - ss["K_call"], 0) + max(ss["K_put"] - sp, 0)) - ss["custo_strangle"]
        rows.append({"Spot": sp, "Straddle": round(pnl_std, 4), "Strangle": round(pnl_str, 4)})
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))

    rule_box([
        "Usar em eventos conhecidos: COPOM, resultados, eleições",
        "IV baixa = melhor momento para comprar (opção mais barata)",
        "Strangle é mais barato; Straddle tem break-even mais próximo",
        "Saída parcial quando dobrar o valor (vende 50% da posição)",
        "Nunca alocar mais de 2%–3% do capital por operação",
        "Vencimento mínimo: 20–30 dias",
        "Stop sugerido: -50% do valor pago",
    ])


# ── ABA 7 — GESTÃO DE RISCO ───────────────────────────────────────────────

with tabs[7]:
    st.subheader("🛡️ Gerenciamento de Risco — Regras RCO")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Máx/opção longa (3%)",    f"R$ {capital*0.03:,.0f}")
    c2.metric("Máx/trava (5%)",           f"R$ {capital*0.05:,.0f}")
    c3.metric("Reserva exercício (30%)",  f"R$ {capital*0.30:,.0f}")
    c4.metric("Meta renda mensal (3%)",   f"R$ {capital*0.03:,.0f}")

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### 📤 Regras de Saída")
        st.markdown("""
| Operação | Take Profit | Stop |
|---|---|---|
| Opção longa (Strangle) | +100% (parcial 50%) | -50% |
| Trava alta/baixa | 50% do lucro máx. | -100% débito |
| Venda coberta | Vira pó ✅ | Recomprar se 200% |
| Venda de put | Vira pó ✅ | Rolar para frente |
        """)

    with col_r:
        st.markdown("#### ☑️ Checklist pré-operação")
        checks = [
            "Ativo tem liquidez nas opções?",
            "Não há evento corporativo surpresa?",
            "Alocação respeita os limites de risco?",
            "Plano de saída definido (lucro E perda)?",
            "Verifiquei IFR e Bandas de Bollinger?",
            "Calculei o prêmio teórico?",
            "Anotei a operação para acompanhar o Theta?",
            "Dias até vencimento verificados?",
        ]
        for c in checks:
            st.checkbox(c, key=f"chk_{c[:20]}")

    st.markdown("---")
    st.markdown("#### 📊 Calculadora de Tamanho de Posição")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        risco_max_pct = st.slider("Risco máximo por operação (%)", 1, 10, 3)
    with col_b:
        custo_opcao = st.number_input("Custo da opção (R$)", min_value=0.001,
                                      value=0.50, step=0.01, format="%.4f")
    with col_c:
        lote = st.number_input("Lote mínimo (opções)", min_value=1, value=100, step=100)

    risco_capital = capital * risco_max_pct / 100
    qtd_lotes     = max(1, int(risco_capital / (custo_opcao * lote)))
    custo_total   = qtd_lotes * lote * custo_opcao

    st.success(
        f"**Posição sugerida:** {qtd_lotes} lote(s) × {lote} = "
        f"**{qtd_lotes*lote:,} opções** | "
        f"Custo: **R$ {custo_total:,.2f}** "
        f"({custo_total/capital*100:.1f}% do capital)"
    )

    rule_box([
        "Nunca colocar mais de 30% do capital em vendas a descoberto",
        "Manter sempre reserva em caixa para emergências",
        "Diversifique entre pelo menos 3 ativos diferentes",
        "Nunca deixar posição vendida descoberta próxima ao vencimento",
        "Resultado negativo? Reduza o tamanho, nunca dobre a aposta",
    ], titulo="🛡️ Princípios de Risco RCO")

st.divider()
st.caption("RCO Assistant v2.0 · Baseado na metodologia de Jimmy Carvalho · Apenas fins educacionais")
