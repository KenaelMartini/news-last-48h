from __future__ import annotations

from typing import Dict
from datetime import datetime, timezone

from ..schema import SnapshotValue
from .stooq_csv import fetch_last_close


def fetch_fx_pairs(pairs: list[str], timeout_s: int = 12) -> Dict[str, SnapshotValue]:
    """
    Fetch FX pairs from Stooq via CSV.
    Expected pairs: ["EURUSD","EURGBP","EURJPY","EURCHF","EURAUD","EURCAD","EURNZD"]
    Stooq symbols are lowercase in CSV endpoint (eurusd, eurgbp, ...).
    """
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

    symbols = [p.lower() for p in pairs]
    q = fetch_last_close(symbols, interval="5", timeout_s=timeout_s)

    out: Dict[str, SnapshotValue] = {}
    for p in pairs:
        sym = p.lower()
        v = q.get(sym)
        if v is None or v.price is None:
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
