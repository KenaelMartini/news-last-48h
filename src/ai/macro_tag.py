# src/ai/macro_tag.py

"""
KM&CO Macro Reasoning Engine – v1
Analyse macro de type sell-side : ton CB, risque, inflation/growth, FX tilt,
novelty, forward significance, credibility soft-check.
"""

from typing import Dict
from openai import OpenAI

client = OpenAI()

def macro_nlp_analyze(text: str) -> Dict:
    prompt = f"""
You are a senior macro strategist at a tier-1 investment bank desk.
Analyze this news headline + text and classify macro implications.

Text:
{text}

Output ONLY a JSON dict with keys:

hawk_dove: -1 dovish, 0 neutral, +1 hawkish
inflation_vs_growth: -1 growth focus, 0 neutral, +1 inflation priority
risk_sentiment: -1 risk-off, 0 neutral, +1 risk-on
fx_direction: dict of currencies w/ score (-1 to +1)
macro_relevance: 0-1 score of relevance to monetary policy / macro data
novelty: 0-1 score of how new the information is vs typical macro flow
forward_significance: 0-1 probability this affects market in 2-5 days
comment: one-line sell-side reasoning

Currencies: USD, EUR, GBP, JPY, CHF, CAD, AUD, NZD

Return JSON only. No text outside JSON.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = resp.choices[0].message.content
        return eval(content)  # safe enough given controlled structure
    except Exception as e:
        return {
            "hawk_dove": 0,
            "inflation_vs_growth": 0,
            "risk_sentiment": 0,
            "fx_direction": {},
            "macro_relevance": 0.3,
            "novelty": 0,
            "forward_significance": 0,
            "comment": f"fallback: {e}"
        }

# === Simple in-memory cache pour réduire les appels IA ===

_ai_cache = {}

def get_cached(text: str, cache: dict = None):
    key = text[:500]  # limite hash sur le début, suffisant
    if cache is None:
        return _ai_cache.get(key)
    return cache.get(key)


def put_cache(text: str, value, cache: dict = None):
    key = text[:500]
    if cache is None:
        _ai_cache[key] = value
    else:
        cache[key] = value
