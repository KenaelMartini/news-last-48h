# ai_core/intelligence/macro_interpreter.py
from typing import List, Dict

INFLATION_KEYS = ["cpi", "pce", "inflation", "core"]
EMPLOYMENT_KEYS = ["payrolls", "jobs", "nfp", "unemployment"]
GROWTH_KEYS = ["gdp", "growth"]
POLICY_KEYS = ["fed", "ecb", "boe", "boj", "rba", "rbnz", "boc", "snb"]

def classify_indicator(text: str) -> str:
    t = text.lower()
    if any(k in t for k in INFLATION_KEYS): return "inflation"
    if any(k in t for k in EMPLOYMENT_KEYS): return "employment"
    if any(k in t for k in GROWTH_KEYS): return "growth"
    if any(k in t for k in POLICY_KEYS): return "policy"
    return "other"

def interpret_numbers(extracted: List[Dict]) -> List[Dict]:
    interpreted = []
    for item in extracted:
        indicator = classify_indicator(item["context"])
        value = item["value"]

        # simple logic baseline
        sentiment = "neutral"
        if indicator == "inflation":
            sentiment = "hawkish" if value > 0.2 else "dovish"
        elif indicator == "employment":
            sentiment = "hawkish" if value > 200 else "dovish"
        elif indicator == "growth":
            sentiment = "hawkish" if value > 2 else "dovish"

        interpreted.append({
            **item,
            "indicator": indicator,
            "signal": sentiment
        })

    return interpreted
