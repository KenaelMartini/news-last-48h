# ai_core/intelligence/quant_bridge.py
from __future__ import annotations
from typing import List, Dict

from ai_core.intelligence.data_extraction import extract_numbers
from ai_core.intelligence.macro_interpreter import interpret_numbers
from ai_core.intelligence.fx_scoring import score_all_fx

def quant_from_articles(articles: List[Dict]) -> Dict:
    """
    articles: list of dicts with keys 'title', 'summary'
    returns: {"scores": {...}, "text_block": "Signal FX (...)"}
    """
    full_text = " ".join([(a.get("title","") or "") + " " + (a.get("summary","") or "") for a in articles])
    extracted = extract_numbers(full_text)
    interpreted = interpret_numbers(extracted)
    fx_scores = score_all_fx(interpreted)

    text_block = format_fx_scores(fx_scores)
    return {"scores": fx_scores, "text_block": text_block}

def format_fx_scores(scores: Dict[str, float]) -> str:
    if not scores:
        return "Signal FX (moteur quant interne) : données insuffisantes."
    # tri décroissant
    items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    leaders = items[:3]
    laggards = items[-3:] if len(items) >= 3 else items[-len(items):]

    top = ", ".join([f"{c} ({v:+.2f})" for c, v in leaders])
    bottom = ", ".join([f"{c} ({v:+.2f})" for c, v in laggards])

    return (
        f"Signal FX (moteur quant interne) : biais positif sur {top}. "
        f"Pression relative sur {bottom}. "
        f"Contexte : carry + momentum macro + régimes de risque/taux."
    )
