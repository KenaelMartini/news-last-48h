# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path

# Option: charge un JSON/YAML plus tard; fallback inline pour démarrer proprement.
def load_proxies() -> dict:
    # Proxies basiques G10 (à étendre)
    proxies = {
        "AUD": ["copper", "iron ore", "china demand", "risk-on"],
        "CAD": ["oil", "brent", "wti", "energy"],
        "NOK": ["brent", "oil", "europe energy"],
        "SEK": ["europe equities", "risk-on"],
        "JPY": ["vix", "us10y", "risk-off", "UST"],
        "CHF": ["europe risk-off", "eurostoxx", "bund"],
        "USD": ["us10y", "dxy", "real yields", "UST"],
        "GBP": ["gilts", "ftse", "uk rates"],
        "EUR": ["bund", "euribor", "eurostoxx"],
        "NZD": ["dairy", "risk-on"],
    }
    weights = {"default": 0.15, "high": 0.30}
    return {"proxies": proxies, "weights": weights}
