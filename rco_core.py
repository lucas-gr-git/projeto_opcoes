"""
rco_core.py — Cálculos Black-Scholes + Gregas + Estratégias RCO
Sem dependências externas (só math da stdlib).
"""
import math
from dataclasses import dataclass, field
from typing import Optional


# ── Black-Scholes ──────────────────────────────────────────────────────────

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes(S, K, T, r, sigma, tipo="call") -> float:
    if T <= 0:
        return max(S - K, 0) if tipo == "call" else max(K - S, 0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if tipo == "call":
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def gregas(S, K, T, r, sigma, tipo="call") -> dict:
    if T <= 0:
        return dict(delta=0.0, theta=0.0, gamma=0.0, vega=0.0)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    phi = math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi)
    gamma = phi / (S * sigma * math.sqrt(T))
    vega  = S * phi * math.sqrt(T) / 100
    if tipo == "call":
        delta = norm_cdf(d1)
        theta = (-(S * phi * sigma) / (2 * math.sqrt(T))
                 - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365
    else:
        delta = norm_cdf(d1) - 1
        theta = (-(S * phi * sigma) / (2 * math.sqrt(T))
                 + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365
    return dict(delta=delta, theta=theta, gamma=gamma, vega=vega)


def moneyness(S, K) -> str:
    pct = (S - K) / K * 100
    if pct > 2:   return "ITM"
    if pct < -2:  return "OTM"
    return "ATM"


# ── Estruturas de dados ────────────────────────────────────────────────────

@dataclass
class Mercado:
    S:          float          # preço spot
    vi:         float          # volatilidade implícita (decimal)
    dias:       int            # dias corridos até vencimento
    taxa_juros: float = 0.1075 # CDI / Selic aproximado
    tendencia:  Optional[str] = None   # 'alta','baixa','lateral','indefinida'
    iv_rank:    Optional[int] = None   # 0–100

    @property
    def T(self):
        return self.dias / 365

    @property
    def vi_pct(self):
        return self.vi * 100


@dataclass
class Linha:
    label: str
    valor: str
    destaque: bool = False


# ── Estratégias ────────────────────────────────────────────────────────────

def calc_venda_coberta(mkt: Mercado) -> list[dict]:
    resultados = []
    for mult in (1.05, 1.07, 1.10):
        K = round(mkt.S * mult, 2)
        p = black_scholes(mkt.S, K, mkt.T, mkt.taxa_juros, mkt.vi, "call")
        g = gregas(mkt.S, K, mkt.T, mkt.taxa_juros, mkt.vi, "call")
        resultados.append({
            "strike":     K,
            "moneyness":  moneyness(mkt.S, K),
            "premio":     round(p, 4),
            "retorno_pct": round(p / mkt.S * 100, 2),
            "delta":      round(g["delta"], 3),
            "theta":      round(abs(g["theta"]), 4),
            "breakeven":  round(mkt.S - p, 2),
        })
    return resultados


def calc_venda_put(mkt: Mercado) -> list[dict]:
    resultados = []
    for mult in (0.95, 0.93, 0.90):
        K = round(mkt.S * mult, 2)
        p = black_scholes(mkt.S, K, mkt.T, mkt.taxa_juros, mkt.vi, "put")
        g = gregas(mkt.S, K, mkt.T, mkt.taxa_juros, mkt.vi, "put")
        resultados.append({
            "strike":          K,
            "moneyness":       moneyness(mkt.S, K),
            "premio":          round(p, 4),
            "preco_efetivo":   round(K - p, 2),
            "desconto_pct":    round((1 - (K - p) / mkt.S) * 100, 2),
            "delta":           round(g["delta"], 3),
            "theta":           round(abs(g["theta"]), 4),
        })
    return resultados


def calc_wheel(mkt: Mercado) -> dict:
    K_put  = round(mkt.S * 0.95, 2)
    K_call = round(mkt.S * 1.07, 2)
    p_put  = black_scholes(mkt.S, K_put,  mkt.T, mkt.taxa_juros, mkt.vi, "put")
    p_call = black_scholes(mkt.S, K_call, mkt.T, mkt.taxa_juros, mkt.vi, "call")
    renda  = p_put + p_call
    return {
        "K_put":         K_put,
        "K_call":        K_call,
        "premio_put":    round(p_put,  4),
        "premio_call":   round(p_call, 4),
        "renda_total":   round(renda,  4),
        "retorno_pct":   round(renda / mkt.S * 100, 2),
    }


def calc_trava_alta(mkt: Mercado) -> dict:
    K1 = round(mkt.S, 2)
    K2 = round(mkt.S * 1.05, 2)
    c1 = black_scholes(mkt.S, K1, mkt.T, mkt.taxa_juros, mkt.vi, "call")
    c2 = black_scholes(mkt.S, K2, mkt.T, mkt.taxa_juros, mkt.vi, "call")
    debito    = c1 - c2
    lucro_max = (K2 - K1) - debito
    rr = lucro_max / debito if debito > 0 else 0
    return {
        "K1": K1, "K2": K2,
        "c1": round(c1, 4), "c2": round(c2, 4),
        "debito":    round(debito,    4),
        "lucro_max": round(lucro_max, 4),
        "breakeven": round(K1 + debito, 2),
        "rr":        round(rr, 2),
    }


def calc_trava_baixa(mkt: Mercado) -> dict:
    K1 = round(mkt.S, 2)
    K2 = round(mkt.S * 0.95, 2)
    p1 = black_scholes(mkt.S, K1, mkt.T, mkt.taxa_juros, mkt.vi, "put")
    p2 = black_scholes(mkt.S, K2, mkt.T, mkt.taxa_juros, mkt.vi, "put")
    debito    = p1 - p2
    lucro_max = (K1 - K2) - debito
    rr = lucro_max / debito if debito > 0 else 0
    return {
        "K1": K1, "K2": K2,
        "p1": round(p1, 4), "p2": round(p2, 4),
        "debito":    round(debito,    4),
        "lucro_max": round(lucro_max, 4),
        "breakeven": round(K1 - debito, 2),
        "rr":        round(rr, 2),
    }


def calc_straddle_strangle(mkt: Mercado) -> dict:
    K_atm   = round(mkt.S, 2)
    K_call  = round(mkt.S * 1.05, 2)
    K_put   = round(mkt.S * 0.95, 2)
    ca = black_scholes(mkt.S, K_atm,  mkt.T, mkt.taxa_juros, mkt.vi, "call")
    pa = black_scholes(mkt.S, K_atm,  mkt.T, mkt.taxa_juros, mkt.vi, "put")
    co = black_scholes(mkt.S, K_call, mkt.T, mkt.taxa_juros, mkt.vi, "call")
    po = black_scholes(mkt.S, K_put,  mkt.T, mkt.taxa_juros, mkt.vi, "put")
    custo_std = ca + pa
    custo_str = co + po
    return {
        "K_atm": K_atm, "K_call": K_call, "K_put": K_put,
        "call_atm":  round(ca, 4), "put_atm":  round(pa, 4),
        "call_otm":  round(co, 4), "put_otm":  round(po, 4),
        "custo_straddle":  round(custo_std, 4),
        "custo_strangle":  round(custo_str, 4),
        "be_sup_std": round(K_atm  + custo_std, 2),
        "be_inf_std": round(K_atm  - custo_std, 2),
        "mov_necessario_pct": round(custo_std / mkt.S * 100, 2),
        "economia_strangle_pct": round((custo_std - custo_str) / custo_std * 100, 1),
    }


def np_like_linspace(start: float, stop: float, n: int) -> list:
    """linspace sem depender de numpy."""
    if n <= 1:
        return [start]
    step = (stop - start) / (n - 1)
    return [round(start + step * i, 4) for i in range(n)]


def _dias_variacoes(dias_base: int, n: int) -> list:
    """Gera N vencimentos espalhados ao redor do dia base (ex: 15, 30, 45, 60...)."""
    base_list = [15, 22, 30, 37, 45, 60, 75, 90]
    if n <= len(base_list):
        ordenado = sorted(base_list, key=lambda d: abs(d - dias_base))[:n]
        return sorted(ordenado)
    return sorted(set([max(7, dias_base + passo) for passo in
                       range(-15 * (n // 2), 15 * (n // 2) + 1, 15)]))[:n]


# ── Geradores de MÚLTIPLAS variações (strike × vencimento × largura) ────────

def gerar_venda_coberta_variacoes(mkt: Mercado, n: int = 5) -> list:
    """Gera N combinações de strike × vencimento para Venda Coberta."""
    mults = np_like_linspace(1.03, 1.15, n)
    dias_list = _dias_variacoes(mkt.dias, n)
    resultados = []
    for mult, dias_v in zip(mults, dias_list):
        K = round(mkt.S * mult, 2)
        T_v = dias_v / 365
        p = black_scholes(mkt.S, K, T_v, mkt.taxa_juros, mkt.vi, "call")
        g = gregas(mkt.S, K, T_v, mkt.taxa_juros, mkt.vi, "call")
        resultados.append({
            "strike": K, "dias": dias_v, "moneyness": moneyness(mkt.S, K),
            "premio": round(p, 4), "retorno_pct": round(p / mkt.S * 100, 2),
            "retorno_anualizado_pct": round((p / mkt.S) * (365 / dias_v) * 100, 1),
            "delta": round(g["delta"], 3), "theta": round(abs(g["theta"]), 4),
            "breakeven": round(mkt.S - p, 2),
        })
    return resultados


def gerar_venda_put_variacoes(mkt: Mercado, n: int = 5) -> list:
    mults = np_like_linspace(0.97, 0.85, n)
    dias_list = _dias_variacoes(mkt.dias, n)
    resultados = []
    for mult, dias_v in zip(mults, dias_list):
        K = round(mkt.S * mult, 2)
        T_v = dias_v / 365
        p = black_scholes(mkt.S, K, T_v, mkt.taxa_juros, mkt.vi, "put")
        g = gregas(mkt.S, K, T_v, mkt.taxa_juros, mkt.vi, "put")
        preco_efetivo = K - p
        resultados.append({
            "strike": K, "dias": dias_v, "moneyness": moneyness(mkt.S, K),
            "premio": round(p, 4), "preco_efetivo": round(preco_efetivo, 2),
            "desconto_pct": round((1 - preco_efetivo / mkt.S) * 100, 2),
            "delta": round(g["delta"], 3), "theta": round(abs(g["theta"]), 4),
        })
    return resultados


def gerar_wheel_variacoes(mkt: Mercado, n: int = 5) -> list:
    put_mults  = np_like_linspace(0.97, 0.85, n)
    call_mults = np_like_linspace(1.03, 1.15, n)
    dias_list  = _dias_variacoes(mkt.dias, n)
    resultados = []
    for put_m, call_m, dias_v in zip(put_mults, call_mults, dias_list):
        T_v = dias_v / 365
        K_put  = round(mkt.S * put_m, 2)
        K_call = round(mkt.S * call_m, 2)
        p_put  = black_scholes(mkt.S, K_put,  T_v, mkt.taxa_juros, mkt.vi, "put")
        p_call = black_scholes(mkt.S, K_call, T_v, mkt.taxa_juros, mkt.vi, "call")
        renda  = p_put + p_call
        resultados.append({
            "dias": dias_v, "K_put": K_put, "K_call": K_call,
            "premio_put": round(p_put, 4), "premio_call": round(p_call, 4),
            "renda_total": round(renda, 4),
            "retorno_pct": round(renda / mkt.S * 100, 2),
            "retorno_anualizado_pct": round((renda / mkt.S) * (365 / dias_v) * 100, 1),
        })
    return resultados


def gerar_trava_alta_variacoes(mkt: Mercado, n: int = 5) -> list:
    """Varia a LARGURA do spread (distância entre K1 e K2) e vencimento."""
    larguras = np_like_linspace(0.03, 0.12, n)
    dias_list = _dias_variacoes(mkt.dias, n)
    resultados = []
    for largura, dias_v in zip(larguras, dias_list):
        T_v = dias_v / 365
        K1 = round(mkt.S, 2)
        K2 = round(mkt.S * (1 + largura), 2)
        c1 = black_scholes(mkt.S, K1, T_v, mkt.taxa_juros, mkt.vi, "call")
        c2 = black_scholes(mkt.S, K2, T_v, mkt.taxa_juros, mkt.vi, "call")
        debito    = c1 - c2
        lucro_max = (K2 - K1) - debito
        rr = lucro_max / debito if debito > 0 else 0
        resultados.append({
            "dias": dias_v, "largura_pct": round(largura * 100, 1),
            "K1": K1, "K2": K2, "debito": round(debito, 4),
            "lucro_max": round(lucro_max, 4),
            "breakeven": round(K1 + debito, 2), "rr": round(rr, 2),
        })
    return resultados


def gerar_trava_baixa_variacoes(mkt: Mercado, n: int = 5) -> list:
    larguras = np_like_linspace(0.03, 0.12, n)
    dias_list = _dias_variacoes(mkt.dias, n)
    resultados = []
    for largura, dias_v in zip(larguras, dias_list):
        T_v = dias_v / 365
        K1 = round(mkt.S, 2)
        K2 = round(mkt.S * (1 - largura), 2)
        p1 = black_scholes(mkt.S, K1, T_v, mkt.taxa_juros, mkt.vi, "put")
        p2 = black_scholes(mkt.S, K2, T_v, mkt.taxa_juros, mkt.vi, "put")
        debito    = p1 - p2
        lucro_max = (K1 - K2) - debito
        rr = lucro_max / debito if debito > 0 else 0
        resultados.append({
            "dias": dias_v, "largura_pct": round(largura * 100, 1),
            "K1": K1, "K2": K2, "debito": round(debito, 4),
            "lucro_max": round(lucro_max, 4),
            "breakeven": round(K1 - debito, 2), "rr": round(rr, 2),
        })
    return resultados


def gerar_straddle_strangle_variacoes(mkt: Mercado, n: int = 5) -> list:
    """Varia a largura do strangle (0 = straddle ATM até strangle largo) e vencimento."""
    larguras = np_like_linspace(0.0, 0.10, n)
    dias_list = _dias_variacoes(mkt.dias, n)
    resultados = []
    for largura, dias_v in zip(larguras, dias_list):
        T_v = dias_v / 365
        K_call = round(mkt.S * (1 + largura), 2)
        K_put  = round(mkt.S * (1 - largura), 2)
        co = black_scholes(mkt.S, K_call, T_v, mkt.taxa_juros, mkt.vi, "call")
        po = black_scholes(mkt.S, K_put,  T_v, mkt.taxa_juros, mkt.vi, "put")
        custo = co + po
        tipo_nome = "Straddle (ATM)" if largura == 0 else f"Strangle (±{largura*100:.0f}%)"
        resultados.append({
            "dias": dias_v, "largura_pct": round(largura * 100, 1), "nome": tipo_nome,
            "K_call": K_call, "K_put": K_put,
            "call_otm": round(co, 4), "put_otm": round(po, 4),
            "custo_total": round(custo, 4),
            "be_sup": round(K_call + custo, 2), "be_inf": round(K_put - custo, 2),
            "mov_necessario_pct": round(custo / mkt.S * 100, 2),
        })
    return resultados


def recomendar(mkt: Mercado) -> list[dict]:
    vi_alta  = mkt.vi >= 0.35
    vi_baixa = mkt.vi < 0.25
    longo    = mkt.dias >= 45
    ivr      = mkt.iv_rank or 50
    tend     = mkt.tendencia

    rec = []

    if vi_alta or ivr >= 50:
        if tend in ("alta", "lateral", None, "indefinida"):
            rec.append({"nome": "Venda Coberta", "emoji": "🥇",
                        "motivo": "VI alta = prêmios gordos. Pilar principal do método RCO.",
                        "prioridade": "Alta", "tab": "venda_coberta"})
            rec.append({"nome": "WHEEL", "emoji": "🥈",
                        "motivo": "Combine Venda de Put + Venda Coberta para renda contínua.",
                        "prioridade": "Alta", "tab": "wheel"})
        if tend in ("baixa", "lateral", None, "indefinida"):
            rec.append({"nome": "Venda de Put", "emoji": "🥉",
                        "motivo": "Receba prêmio e possivelmente compre o ativo com desconto.",
                        "prioridade": "Média", "tab": "venda_put"})

    if tend == "alta" and not vi_alta:
        rec.append({"nome": "Trava de Alta", "emoji": "📈",
                    "motivo": "Visão de alta confirmada com risco controlado.",
                    "prioridade": "Média", "tab": "trava_alta"})
    if tend == "baixa" and not vi_alta:
        rec.append({"nome": "Trava de Baixa", "emoji": "📉",
                    "motivo": "Visão de queda confirmada com risco controlado.",
                    "prioridade": "Média", "tab": "trava_baixa"})

    if vi_baixa and longo:
        rec.append({"nome": "Strangle / Straddle", "emoji": "💥",
                    "motivo": "VI barata + prazo suficiente = cenário ideal para opções longas.",
                    "prioridade": "Alta", "tab": "straddle"})

    if not rec:
        rec.append({"nome": "Venda Coberta", "emoji": "✅",
                    "motivo": "Estratégia mais robusta em qualquer cenário (método RCO).",
                    "prioridade": "Média", "tab": "venda_coberta"})
    return rec
