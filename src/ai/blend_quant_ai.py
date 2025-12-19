from __future__ import annotations

# Imports
from typing import Dict, List, Any
import math



# Hyperparam Plan B
ALPHA_AI_STRENGTH = 0.55    # poids IA vs quant pour la conviction
BETA_RESIDUAL = 0.45        # poids du "non-pricé" dans la conviction
CAP_CONV = 0.95             # plafond sécurité

def _safe(v, lo, hi, default=0.0):
    try:
        v = float(v)
        return max(lo, min(hi, v))
    except:
        return default

def compute_pair_conviction_and_pricein(
    base_fx_score: float,
    quote_fx_score: float,
    price_in_state: str,
    pi_avg_ma: float,
    pi_avg_resid: float
) -> Dict[str, float]:
    
    # Différence macro directionnelle
    diff = base_fx_score - quote_fx_score
    raw_conv = abs(diff)

    # Normalisation simple (0..1)
    norm = min(1.0, max(0.0, raw_conv))

    # Price-in rules
    boost = 0.0
    if price_in_state == "priced":
        boost = -0.15 * norm
    elif price_in_state == "partially_priced":
        boost = 0.05 * norm
    elif price_in_state == "not_priced":
        boost = 0.15 * norm
    # ambiguous → no change

    # Influence résiduelle du marché (si résiduel > 0, opportunité)
    boost += 0.2 * pi_avg_resid

    # Influence accord marché (fort accord → momentum)
    boost += 0.1 * pi_avg_ma

    final = norm + boost
    final = max(0.0, min(1.0, final))  # clamp

    return {
        "conviction": round(final, 3),
        "conviction_boost": round(boost, 3)
    }

