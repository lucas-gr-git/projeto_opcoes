# 📊 RCO Assistant — Recomendador de Opções

Aplicativo Streamlit baseado na metodologia **RCO (Renda Com Opções)** de **Jimmy Carvalho**.

Calcula preços teóricos via **Black-Scholes** e recomenda estratégias de acordo com o cenário de mercado informado.

---

## 🚀 Rodando localmente

```bash
# 1. Clone o repositório
git clone https://github.com/SEU_USUARIO/rco-assistant.git
cd rco-assistant

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute o app
streamlit run app.py
```

Acesse em: `http://localhost:8501`

---

## ☁️ Deploy no Streamlit Community Cloud (gratuito)

1. Faça push do repositório para o GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Clique em **New app**
4. Selecione seu repositório, branch `main` e arquivo `app.py`
5. Clique em **Deploy** — pronto! 🎉

---

## 📐 Estratégias implementadas

| Estratégia | Descrição |
|---|---|
| 🎯 Recomendação inteligente | Analisa VI, IV Rank e tendência automaticamente |
| 💼 Venda Coberta | 3 strikes OTM com prêmio, retorno, Delta e Theta |
| 🔻 Venda de Put | Preço efetivo de compra e desconto sobre spot |
| 🔄 WHEEL | Ciclo Put → Call com renda estimada |
| 📈 Trava de Alta | Bull Call Spread com payoff interativo |
| 📉 Trava de Baixa | Bear Put Spread com payoff interativo |
| 💥 Straddle/Strangle | Opções longas para grandes movimentos |
| 🛡️ Gestão de Risco | Limites, checklist e calculadora de posição |

---

## ⚠️ Aviso legal

Este aplicativo é de **fins exclusivamente educacionais**.  
Não constitui recomendação de investimento.  
Consulte sempre um profissional habilitado antes de operar.

---

## 🏗️ Estrutura do projeto

```
rco-assistant/
├── app.py           # Interface Streamlit
├── rco_core.py      # Cálculos (Black-Scholes, gregas, estratégias)
├── requirements.txt
└── README.md
```
