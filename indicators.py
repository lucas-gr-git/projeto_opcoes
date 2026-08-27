"""
indicators.py — Histórico de preços (BRAPI) + Average True Range (ATR)
Sem dependências além de pandas/requests (já usadas no projeto).
"""
import requests
import pandas as pd

# ── Níveis padrão (estilo Fibonacci) usados no seletor de ATR ────────────────
NIVEIS_ATR_PADRAO = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 2.0, 3.0]

# Referência → (interval BRAPI para o candle, range de histórico a buscar)
REFERENCIA_MAP = {
    "Diário":  {"interval": "1d",  "range": "6mo"},
    "Semanal": {"interval": "1wk", "range": "2y"},
    "Mensal":  {"interval": "1mo", "range": "5y"},
}


def buscar_historico(ticker: str, referencia: str, token: str = "") -> pd.DataFrame:
    """Busca candles históricos (OHLC) na BRAPI para o timeframe escolhido."""
    cfg = REFERENCIA_MAP.get(referencia, REFERENCIA_MAP["Diário"])
    url = (f"https://brapi.dev/api/quote/{ticker}"
           f"?range={cfg['range']}&interval={cfg['interval']}&fundamental=false")
    if token:
        url += f"&token={token}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                hist = results[0].get("historicalDataPrice", [])
                if hist:
                    df = pd.DataFrame(hist)
                    df["date"] = pd.to_datetime(df["date"], unit="s")
                    df = df.dropna(subset=["close", "high", "low"])
                    df = df[["date", "open", "high", "low", "close", "volume"]]
                    return df.sort_values("date").reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])


def calcular_atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """ATR de Wilder (média móvel exponencial do True Range)."""
    if df.empty or len(df) < 2:
        return pd.Series(dtype=float)
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / periodo, adjust=False, min_periods=min(periodo, len(df))).mean()


def calcular_niveis_atr(preco_ref: float, atr_valor: float, niveis: list) -> pd.DataFrame:
    """Projeta níveis superiores/inferiores a partir do preço de referência ± N×ATR."""
    linhas = []
    for n in sorted(niveis):
        linhas.append({
            "nivel": n,
            "rotulo": f"±{n:g}×ATR",
            "preco_superior": round(preco_ref + n * atr_valor, 2),
            "preco_inferior": round(preco_ref - n * atr_valor, 2),
        })
    return pd.DataFrame(linhas)


def obter_atr_e_referencia(ticker: str, referencia: str, periodo: int, token: str = ""):
    """
    Retorna (df_historico, atr_atual, preco_referencia).
    preco_referencia = fechamento do candle mais recente do timeframe escolhido.
    """
    df = buscar_historico(ticker, referencia, token)
    if df.empty:
        return df, None, None
    atr_serie = calcular_atr(df, periodo)
    df = df.assign(atr=atr_serie)
    atr_atual = df["atr"].iloc[-1] if not df["atr"].isna().all() else None
    preco_ref = df["close"].iloc[-1]
    return df, atr_atual, preco_ref
