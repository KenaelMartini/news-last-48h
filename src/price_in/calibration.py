from __future__ import annotations
import json, os, math, time
from typing import Dict, Tuple

CALIB_PATH = os.path.join("kmco_pipeline","data","calibration","price_in_v2.json")

DEFAULTS = {
    "surprise_low": 0.20,
    "surprise_high": 0.55,
    "agree_low": 0.33,
    "agree_high": 0.66,
    "conv_base": 0.45,     # poids NLP macro
    "conv_pricein_boost": 0.55,  # poids boost price-in
}

def _safe_load() -> Dict:
    try:
        if os.path.exists(CALIB_PATH):
            with open(CALIB_PATH,"r",encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, dict):
                    return {**DEFAULTS, **d}
    except Exception:
        pass
    return DEFAULTS.copy()

def load_calib() -> Dict:
    return _safe_load()

def update_running_stats(observed: Dict[str, float]) -> None:
    """
    observed: {"surprise_mag":x, "agreement":y, "residual":z}
    Met à jour des EMA pour auto-calibrer les seuils.
    """
    os.makedirs(os.path.dirname(CALIB_PATH), exist_ok=True)
    d = _safe_load()
    alpha = 0.10  # EMA lente pour stabilité

    for k in ("surprise_mag","agreement","residual"):
        key = f"ema_{k}"
        prev = float(d.get(key, observed.get(k, 0.0)))
        d[key] = (1-alpha)*prev + alpha*float(observed.get(k, 0.0))

    # Ajuste seuils autour des EMA pour coller au régime
    d["surprise_low"]  = max(0.10, min(0.40, 0.75*d["ema_surprise_mag"]))
    d["surprise_high"] = max(0.30, min(0.90, 1.5*d["ema_surprise_mag"]))
    d["agree_low"]     = max(0.15, min(0.50, 0.75*d["ema_agreement"]))
    d["agree_high"]    = max(0.50, min(0.85, 1.25*d["ema_agreement"]))

    d["updated_at"] = int(time.time())
    with open(CALIB_PATH,"w",encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
