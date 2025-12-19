# src/ai/aggregate_currency_ai.py
from __future__ import annotations
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime, timezone

def _time_decay(published_iso: str, half_life_hours: float = 48.0) -> float:
    try:
        t = datetime.fromisoformat(published_iso.replace("Z","+00:00"))
    except Exception:
        return 0.7
    now = datetime.now(timezone.utc)
    dt_h = max(0.0, (now - t).total_seconds()/3600.0)
    return 0.5 ** (dt_h / half_life_hours)


def aggregate_by_currency(
    scored_articles: List[Dict[str, Any]],
    currency_map: Dict[str, List[str]] = None
) -> Dict[str, Dict[str, float]]:

    if currency_map is None:
        currency_map = {}

    bucket = defaultdict(list)

    for rec in scored_articles:
        meta = rec.get("meta", {})
        ccys = meta.get("ccys") or []
        sq = meta.get("source_quality", 0.7)

        published = meta.get("published_at")
        decay = _time_decay(published) if published else 0.7

        s = rec.get("score", {})

        w = max(0.05, sq) * max(0.05, decay) * (0.6 + 0.4 * s.get("forward_guidance", 0.5))

        # --- Fix: fx_bias is a dict, convert to score
        fx_bias_dict = s.get("fx_bias", {})
        fx_bias_score = 0.0
        if isinstance(fx_bias_dict, dict) and fx_bias_dict:
            fx_bias_score = sum(fx_bias_dict.values()) / len(fx_bias_dict)

        macro_dir = (
            0.45 * float(s.get("cb_tone", 0.0)) +
            0.20 * float(s.get("infl_tone", 0.0)) +
            0.15 * float(s.get("emp_tone", 0.0)) +
            0.15 * float(fx_bias_score) +
            0.05 * float(s.get("surprise_sign", 0.0))
        )

        priced_hint = float(s.get("priced_in_hint", 0.5))
        conf = float(s.get("credibility", 0.7))

        for cc in ccys:
            bucket[cc].append((macro_dir, priced_hint, conf, w))

    out: Dict[str, Dict[str, float]] = {}

    for cc, lst in bucket.items():
        if not lst:
            continue

        wsum = sum(w for _,_,_,w in lst) or 1.0
        dir_w = sum(mdir * w for mdir,_,_,w in lst) / wsum
        priced_w = sum(ph * w for _,ph,_,w in lst) / wsum
        conf_w = sum(cf * w for _,_,cf,w in lst) / wsum

        strength = min(1.0, abs(dir_w))
        sign = max(-1.0, min(1.0, dir_w))

        residual = max(0.0, 1.0 - priced_w)
        if priced_w >= 0.7:
            p_state = "priced"
        elif priced_w >= 0.4:
            p_state = "partial"
        else:
            p_state = "unpriced"

        out[cc] = {
            "ai_strength": round(strength, 3),
            "ai_sign": round(sign, 3),
            "ai_price_in_residual": round(residual, 3),
            "ai_pricing_state": p_state,
            "ai_confidence": round(conf_w, 3),
        }

    return out
