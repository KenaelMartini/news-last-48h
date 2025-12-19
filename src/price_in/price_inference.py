from __future__ import annotations
from typing import Dict
from .market_data import load_snapshot, get_change
from .reaction import market_reaction_snapshot, reaction_score
from .calibration import load_calib, update_running_stats

def _sign(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0

def _combine_signals(hawk_dove: float, risk_sent: float) -> str:
    if abs(hawk_dove) < 0.2 and abs(risk_sent) < 0.2:
        return "neutral"
    if abs(hawk_dove) >= abs(risk_sent):
        return "hawkish" if hawk_dove > 0 else "dovish"
    return "risk_on" if risk_sent > 0 else "risk_off"

def enrich_price_inference(macro_ai: Dict) -> Dict:
    """
    Retourne:
    - surprise_dir
    - market_agreement [0..1]
    - pricing_state
    - residual_trade_value [0..1]
    - details (réaction marché + magnitudes)
    """
    calib = load_calib()

    hawk = float(macro_ai.get("hawk_dove", 0) or 0.0)
    risk = float(macro_ai.get("risk_sentiment", 0) or 0.0)
    fx_dir: Dict[str, float] = macro_ai.get("fx_direction", {}) or {}

    surprise_dir = _combine_signals(hawk, risk)
    surprise_mag = max(abs(hawk), abs(risk))  # magnitude IA

    # Réaction marché
    mkt = market_reaction_snapshot()
    agree_signed = reaction_score(surprise_dir, mkt)   # [-1..1]
    # On garde un agreement [0..1] en valeur absolue, mais signée pour l’état
    market_agreement = max(0.0, min(1.0, abs(agree_signed)))

    # Residuel (surprise forte, accord faible)
    residual = max(0.0, surprise_mag * (1.0 - market_agreement))
    priced = surprise_mag * market_agreement

    # Classification calibrée
    if surprise_mag < calib["surprise_low"]:
        pricing_state = "ambiguous"
    elif market_agreement >= calib["agree_high"]:
        pricing_state = "priced"
    elif market_agreement <= calib["agree_low"]:
        pricing_state = "not_priced"
    else:
        pricing_state = "partially_priced"

    # Mise à jour stats pour auto-calibration
    try:
        update_running_stats({
            "surprise_mag": float(surprise_mag),
            "agreement": float(market_agreement),
            "residual": float(residual)
        })
    except Exception:
        pass

    return {
        "surprise_dir": surprise_dir,
        "market_agreement": round(float(market_agreement), 3),
        "pricing_state": pricing_state,
        "residual_trade_value": round(float(min(1.0, residual)), 3),
        "surprise_mag": round(float(surprise_mag), 3),
        "priced_value": round(float(priced), 3),
        "market_reaction": mkt,
    }
