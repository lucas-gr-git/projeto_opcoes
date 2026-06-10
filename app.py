"""
app.py — RCO Assistant (Streamlit)
Recomendador de Opções baseado no método Jimmy Carvalho (RCO)
"""

import streamlit as st
import pandas as pd
import math
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
    .metric-card {
        background: #f8f9fa; border-radius: 10px;
        padding: 1rem; text-align: center;
        border-left: 4px solid #1f77b4;
    }
    .metric-label { font-size: 0.75rem; color: #888; text-transform: uppercase; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #1f77b4; }
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
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────

def fmt_r(v, decimais=4):
    return f"R$ {v:,.{decimais}f}"

def fmt_pct(v, decimais=2):
    return f"{v:.{decimais}f}%"

def badge_mono(m):
    cores = {"ITM": "🟢", "ATM": "🟡", "OTM": "🔵"}
    return f"{cores.get(m, '')} {m}"

def badge_prio(p):
    if p == "Alta":   return "🟢 Alta"
    if p == "Média":  return "🟡 Média"
    return "🔴 Baixa"

def rule_box(regras: list[str], titulo="💡 Regras RCO"):
    conteudo = "".join(f"<li>{r}</li>" for r in regras)
    st.markdown(
        f'<div class="rule-box"><strong>{titulo}</strong><ul style="margin:0.4rem 0 0 1rem;padding:0">'
        f'{conteudo}</ul></div>',
        unsafe_allow_html=True,
    )


# ── Sidebar — entrada de dados ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Parâmetros de Mercado")

    S = st.number_input("Preço do ativo (R$)", min_value=0.01, value=30.00, step=0.50, format="%.2f")
    vi_pct = st.slider("Volatilidade Implícita (%)", 5, 120, 35)
    dias = st.slider("Dias até o vencimento", 5, 180, 21)
    taxa = st.number_input("Taxa de juros livre de risco (%)", min_value=0.0, max_value=50.0,
                           value=10.75, step=0.25, format="%.2f")

    st.markdown("---")
    tendencia = st.selectbox("Tendência do ativo",
                             ["Alta", "Baixa", "Lateral", "Indefinida"])
    iv_rank = st.slider("IV Rank (0 = VI historicamente baixa, 100 = alta)", 0, 100, 50)

    st.markdown("---")
    capital = st.number_input("Seu capital total (R$)", min_value=100.0,
                               value=50_000.0, step=1_000.0, format="%.2f")

    st.markdown("---")
    st.markdown(
        '<div class="aviso">⚠️ Fins educacionais. '
        'Não constitui recomendação de investimento.</div>',
        unsafe_allow_html=True,
    )

# ── Montar objeto Mercado ──────────────────────────────────────────────────

mkt = Mercado(
    S=S,
    vi=vi_pct / 100,
    dias=dias,
    taxa_juros=taxa / 100,
    tendencia=tendencia.lower(),
    iv_rank=iv_rank,
)

# ── Header ─────────────────────────────────────────────────────────────────

st.markdown('<p class="main-title">📊 RCO Assistant</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-title">Recomendador de Opções — baseado na metodologia Jimmy Carvalho (Renda Com Opções)</p>',
    unsafe_allow_html=True,
)

# ── Métricas rápidas ───────────────────────────────────────────────────────

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Ativo",            f"R$ {S:.2f}")
c2.metric("VI",               f"{vi_pct}%",
          delta="Alta → vender" if vi_pct >= 35 else "Baixa → comprar",
          delta_color="normal" if vi_pct >= 35 else "inverse")
c3.metric("Dias p/ venc.",    f"{dias}d")
c4.metric("IV Rank",          f"{iv_rank}/100")
c5.metric("Tendência",        tendencia)

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

# ────────────────────────────────────────────────────────────────────────────
#  ABA 0 — RECOMENDAÇÃO
# ────────────────────────────────────────────────────────────────────────────

with tabs[0]:
    st.subheader("Recomendação Inteligente — Método RCO")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("**Cenário detectado**")
        vi_label = "Alta (vender prêmio 🏷️)" if vi_pct >= 35 else ("Baixa (comprar opção 🎯)" if vi_pct < 25 else "Neutra")
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


# ────────────────────────────────────────────────────────────────────────────
#  ABA 1 — VENDA COBERTA
# ────────────────────────────────────────────────────────────────────────────

with tabs[1]:
    st.subheader("💼 Venda Coberta de CALL — Financiamento")
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

    # Gráfico de payoff simples
    st.markdown("**Payoff no vencimento (por strike)**")
    K_sel = st.selectbox("Selecione o strike para visualizar o payoff",
                         [d["strike"] for d in dados], key="vc_strike")
    d_sel = next(d for d in dados if d["strike"] == K_sel)

    spots = [round(S * m, 2) for m in [x/100 for x in range(80, 131, 2)]]
    payoffs = []
    for sp in spots:
        premio_recebido = d_sel["premio"]
        # Venda coberta: abaixo do strike ganha prêmio; acima, ativo é chamado
        if sp <= K_sel:
            pnl = premio_recebido
        else:
            pnl = premio_recebido - (sp - K_sel)
        payoffs.append({"Spot no vencimento": sp, "P&L da venda coberta (R$)": round(pnl, 4)})

    df_payoff = pd.DataFrame(payoffs).set_index("Spot no vencimento")
    st.line_chart(df_payoff)

    rule_box([
        "Vender CALL OTM com delta entre 0.15 e 0.35",
        "Prefira vencimentos de 15 a 30 dias (theta alto)",
        "Rolar para cima se o ativo se aproximar do strike",
        "Nunca vender coberta com divulgação de resultado próxima",
        "Meta de renda: 2%–4% ao mês sobre o patrimônio em ações",
    ])


# ────────────────────────────────────────────────────────────────────────────
#  ABA 2 — VENDA DE PUT
# ────────────────────────────────────────────────────────────────────────────

with tabs[2]:
    st.subheader("🔻 Venda de Put Coberta (Cash-Secured Put)")
    st.caption("Receba prêmio e, se exercida, compre o ativo com desconto.")

    dados = calc_venda_put(mkt)
    df = pd.DataFrame([{
        "Strike":              f"R$ {d['strike']:.2f}",
        "Moneyness":           d["moneyness"],
        "Prêmio (R$)":         d["premio"],
        "Preço efetivo":       f"R$ {d['preco_efetivo']:.2f}",
        "Desconto s/ spot %":  f"{d['desconto_pct']}%",
        "Delta":               d["delta"],
        "Theta/dia":           d["theta"],
    } for d in dados])
    st.dataframe(df, use_container_width=True, hide_index=True)

    rule_box([
        "Usar apenas em ativos que você QUER ter na carteira",
        "Strike OTM entre 5%–10% abaixo do spot",
        "Manter capital reservado para o exercício",
        "Combinar com Venda Coberta para criar a estratégia WHEEL",
    ])


# ────────────────────────────────────────────────────────────────────────────
#  ABA 3 — WHEEL
# ────────────────────────────────────────────────────────────────────────────

with tabs[3]:
    st.subheader("🔄 Estratégia WHEEL — Roda de Renda")
    st.caption("Venda de Put → exercício → Venda Coberta → ciclo infinito de renda.")

    w = calc_wheel(mkt)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Put strike",    f"R$ {w['K_put']:.2f}")
    col2.metric("Call strike",   f"R$ {w['K_call']:.2f}")
    col3.metric("Renda/ciclo",   fmt_r(w["renda_total"]))
    col4.metric("Retorno/ciclo", fmt_pct(w["retorno_pct"]))

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
                    └── NÃO (exercida) → compra ações no desconto
                                              ↓
                             Vende Call OTM ──► Call vira pó?
                                                 ├── SIM → repete fase 2
                                                 └── NÃO (exercida) → vende ações com lucro → volta fase 1
```
""")

    rule_box([
        "Use apenas em ativos de alta qualidade (blue chips: PETR4, VALE3, ITUB4…)",
        "Nunca alocar mais de 30% do capital em uma única posição da Wheel",
        "Se o ativo cair muito, pode-se rolar a put para baixo e para frente",
        "Objetivo: 3%–5% de renda ao mês sobre o capital alocado",
    ])


# ────────────────────────────────────────────────────────────────────────────
#  ABA 4 — TRAVA DE ALTA
# ────────────────────────────────────────────────────────────────────────────

with tabs[4]:
    st.subheader("📈 Trava de Alta com Call (Bull Call Spread)")
    st.caption("Operação direcional com risco limitado para cenário de alta confirmado.")

    t = calc_trava_alta(mkt)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Débito",          fmt_r(t["debito"]))
    c2.metric("Lucro máximo",    fmt_r(t["lucro_max"]))
    c3.metric("Break-even",      f"R$ {t['breakeven']:.2f}")
    c4.metric("Relação R/R",     f"1 : {t['rr']}")

    st.markdown("---")
    st.markdown(f"""
| | Valor |
|---|---|
| Compra CALL (K1 — ATM) | R$ {t['K1']:.2f} &nbsp;→ prêmio pago: R$ {t['c1']:.4f} |
| Vende CALL (K2 — OTM)  | R$ {t['K2']:.2f} &nbsp;→ prêmio recebido: R$ {t['c2']:.4f} |
| **Débito líquido**      | **R$ {t['debito']:.4f}** |
| **Lucro máximo**        | **R$ {t['lucro_max']:.4f}** (se spot ≥ K2 no venc.) |
| Perda máxima           | R$ {t['debito']:.4f} (se spot ≤ K1 no venc.) |
    """)

    # Payoff
    spots = [round(S * m, 2) for m in [x/100 for x in range(85, 120, 1)]]
    payoffs_ta = []
    for sp in spots:
        pnl = max(min(sp - t["K1"], t["K2"] - t["K1"]), 0) - t["debito"]
        payoffs_ta.append({"Spot": sp, "P&L Trava de Alta": round(pnl, 4)})
    st.line_chart(pd.DataFrame(payoffs_ta).set_index("Spot"))

    rule_box([
        "Usar quando há visão direcional de alta confirmada (análise técnica)",
        "Verificar IFR e Bandas de Bollinger antes de entrar",
        "Prefira spread de 5% a 10% entre os strikes",
        "Busque relação R/R de pelo menos 1:2",
        "Nunca alocar mais de 5% do capital por operação",
        "Fechar com 50% do lucro máximo (não esperar o vencimento)",
    ])


# ────────────────────────────────────────────────────────────────────────────
#  ABA 5 — TRAVA DE BAIXA
# ────────────────────────────────────────────────────────────────────────────

with tabs[5]:
    st.subheader("📉 Trava de Baixa com Put (Bear Put Spread)")
    st.caption("Operação direcional com risco limitado para cenário de queda confirmado.")

    tb = calc_trava_baixa(mkt)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Débito",          fmt_r(tb["debito"]))
    c2.metric("Lucro máximo",    fmt_r(tb["lucro_max"]))
    c3.metric("Break-even",      f"R$ {tb['breakeven']:.2f}")
    c4.metric("Relação R/R",     f"1 : {tb['rr']}")

    st.markdown("---")
    st.markdown(f"""
| | Valor |
|---|---|
| Compra PUT (K1 — ATM) | R$ {tb['K1']:.2f} &nbsp;→ prêmio pago: R$ {tb['p1']:.4f} |
| Vende PUT (K2 — OTM)  | R$ {tb['K2']:.2f} &nbsp;→ prêmio recebido: R$ {tb['p2']:.4f} |
| **Débito líquido**    | **R$ {tb['debito']:.4f}** |
| **Lucro máximo**      | **R$ {tb['lucro_max']:.4f}** (se spot ≤ K2 no venc.) |
| Perda máxima         | R$ {tb['debito']:.4f} (se spot ≥ K1 no venc.) |
    """)

    spots = [round(S * m, 2) for m in [x/100 for x in range(85, 115, 1)]]
    payoffs_tb = []
    for sp in spots:
        pnl = max(min(tb["K1"] - sp, tb["K1"] - tb["K2"]), 0) - tb["debito"]
        payoffs_tb.append({"Spot": sp, "P&L Trava de Baixa": round(pnl, 4)})
    st.line_chart(pd.DataFrame(payoffs_tb).set_index("Spot"))

    rule_box([
        "Cenário: ativo com resistência clara, sobrecomprado no IFR (>70)",
        "Prefira usar como hedge da carteira de ações",
        "Não alocar mais de 3%–5% do capital",
        "Fechar com 50% do lucro máximo",
    ])


# ────────────────────────────────────────────────────────────────────────────
#  ABA 6 — STRADDLE / STRANGLE
# ────────────────────────────────────────────────────────────────────────────

with tabs[6]:
    st.subheader("💥 Straddle / Strangle — Opções Longas Explosivas")
    st.caption("Para grandes movimentos esperados. Potencial de ganhos acima de 1000%.")

    ss = calc_straddle_strangle(mkt)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### 🎯 Straddle (ATM)")
        st.metric("Custo total", fmt_r(ss["custo_straddle"]))
        st.markdown(f"""
| Campo | Valor |
|---|---|
| Compra Call ATM (R$ {ss['K_atm']:.2f}) | R$ {ss['call_atm']:.4f} |
| Compra Put ATM  (R$ {ss['K_atm']:.2f}) | R$ {ss['put_atm']:.4f}  |
| Break-even superior | R$ {ss['be_sup_std']:.2f} |
| Break-even inferior | R$ {ss['be_inf_std']:.2f} |
| Mov. necessário | ±{ss['mov_necessario_pct']:.1f}% |
        """)

    with col_r:
        st.markdown("#### 🔍 Strangle (OTM ±5%)")
        st.metric("Custo total",
                  fmt_r(ss["custo_strangle"]),
                  delta=f"{ss['economia_strangle_pct']:.1f}% mais barato que Straddle",
                  delta_color="normal")
        st.markdown(f"""
| Campo | Valor |
|---|---|
| Compra Call OTM (R$ {ss['K_call']:.2f}) | R$ {ss['call_otm']:.4f} |
| Compra Put OTM  (R$ {ss['K_put']:.2f})  | R$ {ss['put_otm']:.4f}  |
        """)

    st.markdown("---")
    # Payoff straddle
    spots = [round(S * m, 2) for m in [x/100 for x in range(75, 130, 1)]]
    rows = []
    for sp in spots:
        pnl_std = (max(sp - ss["K_atm"], 0) + max(ss["K_atm"] - sp, 0)) - ss["custo_straddle"]
        pnl_str = (max(sp - ss["K_call"], 0) + max(ss["K_put"] - sp, 0)) - ss["custo_strangle"]
        rows.append({"Spot": sp, "Straddle": round(pnl_std, 4), "Strangle": round(pnl_str, 4)})
    st.line_chart(pd.DataFrame(rows).set_index("Spot"))

    rule_box([
        "Usar em eventos conhecidos: COPOM, resultados trimestrais, eleições",
        "IV baixa = melhor momento para comprar (opção mais barata)",
        "Strangle é mais barato; Straddle tem break-even mais próximo",
        "Saída parcial quando dobrar o valor (vende 50% da posição)",
        "Nunca alocar mais de 2%–3% do capital por operação",
        "Vencimento mínimo: 20–30 dias (não compre opções curtas para longas)",
        "Stop sugerido: -50% do valor pago",
    ])


# ────────────────────────────────────────────────────────────────────────────
#  ABA 7 — GESTÃO DE RISCO
# ────────────────────────────────────────────────────────────────────────────

with tabs[7]:
    st.subheader("🛡️ Gerenciamento de Risco — Regras RCO")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Máx/opção longa (3%)",   f"R$ {capital*0.03:,.0f}")
    c2.metric("Máx/trava (5%)",          f"R$ {capital*0.05:,.0f}")
    c3.metric("Reserva exercício (30%)", f"R$ {capital*0.30:,.0f}")
    c4.metric("Meta renda mensal (3%)",  f"R$ {capital*0.03:,.0f}")

    st.markdown("---")

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### 📤 Regras de Saída")
        st.markdown("""
| Operação | Take Profit | Stop Loss |
|---|---|---|
| Opção longa (Strangle/Straddle) | +100% (parcial 50%) | -50% |
| Trava de alta/baixa | 50% do lucro máximo | -100% do débito |
| Venda coberta | Vira pó ✅ | Recomprar se prêmio virar 200% |
| Venda de put | Vira pó ✅ | Rolar para baixo e para frente |
        """)

    with col_r:
        st.markdown("#### ☑️ Checklist pré-operação")
        checks = [
            "O ativo tem liquidez suficiente nas opções?",
            "Não há evento corporativo inesperado próximo?",
            "A alocação respeita os limites de risco?",
            "Tenho plano de saída definido (lucro E perda)?",
            "Verifiquei IFR e Bandas de Bollinger no gráfico?",
            "Calculei o prêmio teórico via Black-Scholes?",
            "Anotei a operação para acompanhar o Theta?",
            "Verificar dias até o vencimento e theta acelerado?",
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
        f"**Posição sugerida:** {qtd_lotes} lote(s) × {lote} opções = "
        f"**{qtd_lotes*lote:,} opções** | "
        f"Custo total: **R$ {custo_total:,.2f}** "
        f"({custo_total/capital*100:.1f}% do capital)"
    )

    rule_box([
        "Nunca colocar mais de 30% do capital em vendas a descoberto",
        "Manter sempre reserva em caixa para emergências e ajustes",
        "Diversifique entre pelo menos 3 ativos diferentes",
        "Nunca deixar posição vendida descoberta próxima ao vencimento",
        "Resultado negativo? Reduza tamanho, nunca aumente a aposta",
    ], titulo="🛡️ Princípios de Risco RCO")

st.divider()
st.caption("RCO Assistant v1.0 · Baseado na metodologia de Jimmy Carvalho · Apenas fins educacionais")
