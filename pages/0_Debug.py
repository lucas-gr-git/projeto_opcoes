import streamlit as st
import requests

st.title("🔍 Debug de Conexão")

# Testar secrets
st.subheader("1. Secrets")
try:
    token = st.secrets["BRAPI_TOKEN"]
    st.success(f"✅ Token encontrado: {token[:8]}...")
except Exception as e:
    st.error(f"❌ Sem token: {e}")
    token = ""

# Testar conexão BRAPI
st.subheader("2. Teste BRAPI")
url = f"https://brapi.dev/api/quote/PETR4?range=1d&interval=1d"
if token:
    url += f"&token={token}"

st.code(f"URL: {url}")

try:
    r = requests.get(url, timeout=10)
    st.write(f"Status HTTP: {r.status_code}")
    st.json(r.json())
except Exception as e:
    st.error(f"Erro: {e}")
