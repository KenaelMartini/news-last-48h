# -*- coding: utf-8 -*-
from __future__ import annotations

# Détection très simple par mots-clés; à remplacer par signaux marché live (VIX, MOVE, HY spreads…)
def detect_risk_context(context_text: str) -> dict:
    ctx = (context_text or "").lower()
    risk_on = 0.0
    risk_off = 0.0
    vol = 0.0

    if any(k in ctx for k in ["rally", "risk-on", "appetite", "equities surge", "stocks jump"]):
        risk_on += 0.10
    if any(k in ctx for k in ["risk-off", "flight to safety", "safe haven", "selloff", "panic"]):
        risk_off += 0.10
    if any(k in ctx for k in ["vix spike", "volatility spike", "vol surges", "vix soars"]):
        vol += 0.10

    return {"risk_on": round(risk_on, 3), "risk_off": round(risk_off, 3), "vol": round(vol, 3)}
