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
