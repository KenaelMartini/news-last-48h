# src/price_in/market_data.py
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timezone

SNAP_PATH = Path("KMCO_out/market_snapshot.json")

class MarketSnapshot:
    """
    Contient des variations récentes (ret% / bp) de quelques proxies:
      - DXY (%)
      - UST2Y, UST10Y (bp)
      - ES1 (S&P futures %) 
      - CL1 (WTI %) optionnel
      - JPY_BASKET (%), CHF_BASKET (%)
    Format attendu (exemple):
    {
      "as_of_utc": "2025-11-04T05:20:00Z",
      "changes": {
        "DXY": 0.18,
        "UST2Y_BP": +3.5,
        "ES1": -0.4,
        "JPY_BASKET": -0.25,
        "CHF_BASKET": +0.10
      }
    }
    """
    def __init__(self, as_of_utc: str, changes: Dict[str, float]):
        self.as_of_utc = as_of_utc
        self.changes = changes

def load_snapshot() -> Optional[MarketSnapshot]:
    try:
        if SNAP_PATH.exists():
            with open(SNAP_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return MarketSnapshot(
                as_of_utc=data.get("as_of_utc", datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00","Z")),
                changes=data.get("changes", {})
            )
    except Exception:
        pass
    # Fallback neutre si rien
    return MarketSnapshot(
        as_of_utc=datetime.utcnow().replace(tzinfo=timezone.utc).isoformat().replace("+00:00","Z"),
        changes={}
    )

def get_change(symbol: str, snap: Optional[MarketSnapshot]=None) -> float:
    snap = snap or load_snapshot()
    return float(snap.changes.get(symbol, 0.0))
