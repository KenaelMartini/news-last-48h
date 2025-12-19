# ai_core/intelligence/fx_scoring.py
from __future__ import annotations
from typing import Dict, List
from statistics import mean

# ===== Imports tolérants (fallbacks si modules absents) =====
try:
    from ai_core.intelligence.proxies_loader import load_proxies
except Exception:
    def load_proxies() -> dict:
        # Fallback minimal si le loader est introuvable
        return {
            "proxies": {
                "AUD": ["copper", "china", "iron ore", "risk-on"],
                "CAD": ["oil", "brent", "wti", "energy"],
                "JPY": ["vix", "risk-off", "ust"],
                "CHF": ["risk-off", "europe"],
            },
            "weights": {"default": 0.15, "high": 0.30},
        }

try:
    from ai_core.intelligence.risk_regime import detect_risk_context
except Exception:
    def detect_risk_context(ctx: str) -> dict:
        return {"risk_on": 0.0, "risk_off": 0.0, "vol": 0.0}

G10 = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "NOK", "SEK"]

WEIGHTS = {
    "inflation": 0.4,
    "employment": 0.3,
    "growth": 0.2,
    "policy": 0.1,
}

SENTIMENT_MAP = {
    "hawkish": 1,
    "neutral": 0,
    "dovish": -1,
}

# ===== Proxies config =====
proxy_cfg = load_proxies()
proxy_map = proxy_cfg.get("proxies", {})
proxy_weights = proxy_cfg.get("weights", {})
BOOST_DEFAULT = float(proxy_weights.get("default", 0.15))
BOOST_HIGH = float(proxy_weights.get("high", 0.30))

def proxy_boost_for(ccy: str, context_text: str) -> float:
    proxies = proxy_map.get(ccy.upper(), [])
    context = (context_text or "").lower()

    boost = 0.0
    for proxy in proxies:
        if proxy.lower() in context:
            boost += BOOST_DEFAULT
            if any(x in context for x in ["surge", "rally", "jumps", "spike"]):
                boost += BOOST_HIGH
            elif any(x in context for x in ["slump", "falls", "decline", "drop"]):
                boost -= BOOST_HIGH
    return round(boost, 3)

def score_currency(signals: List[Dict], currency: str) -> float:
    values: List[float] = []

    for s in signals:
        ctx = s.get("context", "") or ""
        if currency not in ctx:
            continue

        indicator = s.get("indicator", "other")
        sentiment = s.get("signal", "neutral")
        consensus_boost = float(s.get("boost", 1.0))

        w = float(WEIGHTS.get(indicator, 0.05))
        v = float(SENTIMENT_MAP.get(sentiment, 0))

        macro_val = w * v * consensus_boost

        # Proxies (commodities/flows)
        macro_val += proxy_boost_for(currency, ctx)

        # Risk regime
        risk = detect_risk_context(ctx)

        if risk.get("risk_on", 0) > 0:
            if currency in ["AUD", "NZD", "CAD", "GBP"]:
                macro_val += risk["risk_on"]
            if currency in ["JPY", "CHF"]:
                macro_val -= risk["risk_on"]

        if risk.get("risk_off", 0) > 0:
            if currency in ["JPY", "CHF", "USD"]:
                macro_val += risk["risk_off"]
            if currency in ["AUD", "NZD"]:
                macro_val -= risk["risk_off"]

        if risk.get("vol", 0) > 0:
            if currency == "JPY":
                macro_val += risk["vol"]
            if currency in ["AUD", "NZD"]:
                macro_val -= risk["vol"]

        values.append(macro_val)

    return round(mean(values), 3) if values else 0.0

def score_all_fx(signals: List[Dict]) -> Dict[str, float]:
    scores = {ccy: score_currency(signals, ccy) for ccy in G10}
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
