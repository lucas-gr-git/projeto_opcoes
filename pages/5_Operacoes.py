"""
5_Operacoes.py — Diário de Operações
Registro pessoal das operações (editável e com exclusão), salvo em CSV local.
"""
import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

st.set_page_config(page_title="Operações | RCO", page_icon="🧾", layout="wide")

ARQ_CSV = "operacoes_rco.csv"

COLUNAS = ["Data", "Ticker", "Estrategia", "Operacao", "Opcao", "Strike",
           "Premio", "Quantidade", "Vencimento", "Status", "Resultado", "Obs"]

ESTRATEGIAS = ["Venda Coberta", "Venda de Put", "WHEEL", "Trava de Alta", "Trava de Baixa",
               "Straddle/Strangle", "Compra de ação", "Outra"]
OPERACOES = ["Compra", "Venda"]
OPCOES    = ["CALL", "PUT", "Ação"]
STATUS    = ["Aberta", "Encerrada", "Exercida", "Rolada"]


def carregar() -> pd.DataFrame:
    if os.path.exists(ARQ_CSV):
        try:
            df = pd.read_csv(ARQ_CSV)
            for c in COLUNAS:
                if c not in df.columns:
                    df[c] = None
            return df[COLUNAS]
        except Exception:
            pass
    return pd.DataFrame(columns=COLUNAS)


def salvar(df: pd.DataFrame):
    df.to_csv(ARQ_CSV, index=False)


st.markdown("## 🧾 Diário de Operações")
st.caption("Registre, edite e apague suas operações da metodologia RCO.")

if "df_ops" not in st.session_state:
    st.session_state.df_ops = carregar()

# ── Métricas resumo ────────────────────────────────────────────────────────────
df_atual = st.session_state.df_ops
if not df_atual.empty:
    abertas = df_atual[df_atual["Status"] == "Aberta"]
    encerradas = df_atual[df_atual["Status"].isin(["Encerrada", "Exercida"])]
    resultado_total = pd.to_numeric(encerradas["Resultado"], errors="coerce").sum()
else:
    abertas = encerradas = df_atual
    resultado_total = 0.0

m1, m2, m3 = st.columns(3)
m1.metric("Operações abertas", len(abertas))
m2.metric("Operações encerradas", len(encerradas))
m3.metric("Resultado acumulado", f"R$ {resultado_total:,.2f}")

st.divider()

# ── Nova operação ────────────────────────────────────────────────────────────
with st.expander("➕ Nova operação", expanded=df_atual.empty):
    with st.form("form_nova_op", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_data = st.date_input("Data", value=date.today())
            f_ticker = st.text_input("Ticker", placeholder="PETR4")
        with c2:
            f_estrategia = st.selectbox("Estratégia", ESTRATEGIAS)
            f_operacao = st.selectbox("Operação", OPERACOES)
        with c3:
            f_opcao = st.selectbox("Tipo", OPCOES)
            f_status = st.selectbox("Status", STATUS)

        c4, c5, c6 = st.columns(3)
        with c4:
            f_strike = st.number_input("Strike (R$)", min_value=0.0, step=0.01, format="%.2f")
        with c5:
            f_premio = st.number_input("Prêmio unitário (R$)", min_value=0.0, step=0.0001, format="%.4f")
        with c6:
            f_qtd = st.number_input("Quantidade", min_value=1, step=1, value=100)

        c7, c8 = st.columns(2)
        with c7:
            f_venc = st.date_input("Vencimento", value=date.today())
        with c8:
            f_resultado = st.number_input("Resultado (R$) — preencher ao encerrar", step=0.01, format="%.2f")

        f_obs = st.text_area("Observações", placeholder="Ex: rolada para o mês seguinte, exercida, etc.")

        enviar = st.form_submit_button("💾 Adicionar operação", type="primary")

    if enviar:
        if not f_ticker.strip():
            st.warning("Informe o ticker antes de salvar.")
        else:
            nova = {
                "Data": f_data.isoformat(), "Ticker": f_ticker.strip().upper(),
                "Estrategia": f_estrategia, "Operacao": f_operacao, "Opcao": f_opcao,
                "Strike": f_strike, "Premio": f_premio, "Quantidade": int(f_qtd),
                "Vencimento": f_venc.isoformat(), "Status": f_status,
                "Resultado": f_resultado, "Obs": f_obs,
            }
            st.session_state.df_ops = pd.concat(
                [st.session_state.df_ops, pd.DataFrame([nova])], ignore_index=True)
            salvar(st.session_state.df_ops)
            st.success(f"Operação {nova['Ticker']} adicionada.")
            st.rerun()

st.divider()

# ── Tabela editável — editar e apagar linhas ─────────────────────────────────
st.markdown("### 📋 Operações registradas")

if st.session_state.df_ops.empty:
    st.info("Nenhuma operação registrada ainda. Use o formulário acima para adicionar a primeira.")
else:
    busca = st.text_input("🔎 Filtrar por ticker", placeholder="Ex: PETR4")
    df_visivel = st.session_state.df_ops
    if busca.strip():
        df_visivel = df_visivel[df_visivel["Ticker"].str.contains(busca.strip().upper(), na=False)]

    st.caption("Clique numa linha e use o ícone 🗑️ (ou tecle Delete) para apagar. "
               "Clique em ➕ no rodapé da tabela para adicionar direto por aqui. "
               "Depois clique em **Salvar alterações**.")

    editado = st.data_editor(
        df_visivel,
        width="stretch",
        num_rows="dynamic",
        hide_index=True,
        key="editor_ops",
        column_config={
            "Estrategia": st.column_config.SelectboxColumn("Estratégia", options=ESTRATEGIAS),
            "Operacao":   st.column_config.SelectboxColumn("Operação", options=OPERACOES),
            "Opcao":      st.column_config.SelectboxColumn("Tipo", options=OPCOES),
            "Status":     st.column_config.SelectboxColumn("Status", options=STATUS),
            "Strike":     st.column_config.NumberColumn("Strike (R$)", format="%.2f"),
            "Premio":     st.column_config.NumberColumn("Prêmio (R$)", format="%.4f"),
            "Resultado":  st.column_config.NumberColumn("Resultado (R$)", format="%.2f"),
            "Quantidade": st.column_config.NumberColumn("Qtd", format="%d"),
        },
    )

    col_sv, col_rm = st.columns(2)
    with col_sv:
        if st.button("💾 Salvar alterações", type="primary", width="stretch"):
            if busca.strip():
                resto = st.session_state.df_ops[
                    ~st.session_state.df_ops["Ticker"].str.contains(busca.strip().upper(), na=False)]
                completo = pd.concat([resto, editado], ignore_index=True)
            else:
                completo = editado
            st.session_state.df_ops = completo.reset_index(drop=True)
            salvar(st.session_state.df_ops)
            st.success("Alterações salvas.")
            st.rerun()
    with col_rm:
        confirmar = st.checkbox("Confirmo que quero apagar TODAS as operações")
        if st.button("🗑️ Apagar tudo", width="stretch", disabled=not confirmar):
            st.session_state.df_ops = pd.DataFrame(columns=COLUNAS)
            salvar(st.session_state.df_ops)
            st.success("Todas as operações foram apagadas.")
            st.rerun()

    st.divider()
    st.download_button("⬇️ Baixar backup (CSV)",
                        data=st.session_state.df_ops.to_csv(index=False).encode("utf-8"),
                        file_name=f"operacoes_rco_{datetime.now():%Y%m%d}.csv", mime="text/csv")

st.divider()
with st.expander("♻️ Restaurar backup (CSV)"):
    up = st.file_uploader("Selecione um arquivo CSV exportado anteriormente", type=["csv"])
    if up is not None:
        try:
            df_up = pd.read_csv(up)
            for c in COLUNAS:
                if c not in df_up.columns:
                    df_up[c] = None
            st.session_state.df_ops = df_up[COLUNAS]
            salvar(st.session_state.df_ops)
            st.success("Backup restaurado com sucesso.")
            st.rerun()
        except Exception as e:
            st.error(f"Não foi possível ler o arquivo: {e}")

st.caption("⚠️ Os dados ficam salvos em um arquivo local do app. No Streamlit Community Cloud "
           "esse armazenamento é temporário — reinícios ou novos deploys podem apagá-lo. "
           "Baixe o backup em CSV de vez em quando para não perder o histórico.")
