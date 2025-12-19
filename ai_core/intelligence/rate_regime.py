# ai_core/intelligence/rate_regime.py
import os, yaml

CFG_PATH = os.path.join(os.path.dirname(__file__), "../../configs/yield_rules.yaml")

def load_yield_rules():
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

_rules = load_yield_rules()
signals_cfg = _rules.get("yield_signals", {})
weights_cfg = _rules.get("weights", {})

def detect_rates_context(text: str) -> dict:
    """
    Retourne un dict de scores pour les signaux de taux détectés dans le texte.
    Ex: {"front_end_hawkish": 0.3, "real_rates_up": 0.0, ...}
    """
    txt = (text or "").lower()
    out = {k: 0.0 for k in signals_cfg.keys()}

    for name, block in signals_cfg.items():
        kws = block.get("keywords", [])
        for kw in kws:
            if kw.lower() in txt:
                out[name] += weights_cfg.get(name, 0.0)

    return out
