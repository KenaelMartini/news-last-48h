from __future__ import annotations

from typing import Dict
from datetime import datetime, timezone

from ..schema import SnapshotValue
from .stooq_csv import fetch_last_close

def fetch_fx_pairs(pairs: list[str], timeout_s: int = 12) -> Dict[str, SnapshotValue]:
    """
    Stooq FX symbols examples: EURUSD, EURGBP, EURJPY, EURCHF, EURAUD, EURCAD, EURNZD
    They exist on Stooq (example EURUSD). :contentReference[oaicite:2]{index=2}
    """
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    # Use 5-min bars when available
    q = fetch_last_close([p.lower() for p in pairs], interval="5", timeout_s=timeout_s)

    out: Dict[str, SnapshotValue] = {}
    for p in pairs:
        sym = p.lower()
        v = q.get(sym)
        if v is None:
            out[p] = SnapshotValue(symbol=p, price=None, ts_utc=ts, source="stooq_csv_fx")
        else:
            out[p] = SnapshotValue(
                symbol=p,
                price=v.price,
                change=None,
                change_pct=None,
                currency=None,
                ts_utc=v.ts_utc or ts,
                source=v.source,
            )
    return out
