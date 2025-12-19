from __future__ import annotations
from typing import Dict, Optional, Tuple
from .market_data import load_snapshot, get_change

def market_reaction_snapshot() -> Dict[str, float]:
    snap = load_snapshot()
    def num(x): 
        try: 
            return float(x)
        except Exception:
            return 0.0
    return {
        "DXY": num(get_change("DXY", snap)),             # %
        "UST2Y_BP": num(get_change("UST2Y_BP", snap)),   # bp
        "ES1": num(get_change("ES1", snap)),             # %
        "JPY_BASKET": num(get_change("JPY_BASKET", snap)),
        "CHF_BASKET": num(get_change("CHF_BASKET", snap)),
    }

def reaction_score(direction: str, m: Dict[str, float]) -> float:
    """
    direction ∈ {hawkish, dovish, risk_on, risk_off, neutral}
    Retourne un score [-1, +1] indiquant si le marché CONFIRME cette direction.
    """
    if direction == "neutral":
        return 0.0
    sc, w = 0.0, 0.0
    def sgn(x): 
        return 1 if x > 0 else (-1 if x < 0 else 0)

    if direction in ("hawkish", "dovish"):
        # Hawkish → DXY↑ UST2Y↑ ES1↓ ; Dovish → inverse
        target = 1 if direction == "hawkish" else -1
        sc += 0.45 if sgn(m.get("DXY", 0.0)) == target else 0.0; w += 0.45
        sc += 0.45 if sgn(m.get("UST2Y_BP", 0.0)) == target else 0.0; w += 0.45
        # bonus via ES1
        sc += 0.10 if sgn(m.get("ES1", 0.0)) == (-target) else 0.0; w += 0.10

    elif direction in ("risk_on", "risk_off"):
        target = 1 if direction == "risk_on" else -1
        sc += 0.60 if sgn(m.get("ES1", 0.0)) == target else 0.0; w += 0.60
        # DXY/CHF/JPY appuis
        if direction == "risk_on":
            sc += 0.20 if sgn(m.get("DXY", 0.0)) <= 0 else 0.0; w += 0.20
        else:
            # risk-off: DXY↑ ou CHF/JPY baskets ↑
            any_safe_up = any(sgn(m.get(k, 0.0)) >= 0 for k in ("DXY","CHF_BASKET","JPY_BASKET"))
            sc += 0.20 if any_safe_up else 0.0; w += 0.20

    return 0.0 if w == 0 else max(-1.0, min(1.0, sc / w))
