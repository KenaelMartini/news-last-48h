from __future__ import annotations
import requests
from datetime import datetime, timezone
from typing import Dict, Optional

from ..schema import SnapshotValue

BASE_URL = "https://api.exchangerate.host/latest"

def fetch_fx(base: str, symbols: list[str], timeout_s: int = 10) -> Dict[str, SnapshotValue]:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    out: Dict[str, SnapshotValue] = {}

    params = {"base": base, "symbols": ",".join(symbols)}
    try:
        r = requests.get(BASE_URL, params=params, timeout=timeout_s, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        rates = data.get("rates", {}) or {}

        for s in symbols:
            px: Optional[float] = rates.get(s)
            out[f"{base}{s}"] = SnapshotValue(
                symbol=f"{base}/{s}",
                price=float(px) if px is not None else None,
                currency=s,
                ts_utc=ts,
                source="exchangerate.host",
            )

    except Exception as e:
        print(f"[SNAPSHOT][FX] ERROR calling {BASE_URL} params={params} -> {e}")
        for s in symbols:
            out[f"{base}{s}"] = SnapshotValue(
                symbol=f"{base}/{s}",
                price=None,
                currency=s,
                ts_utc=ts,
                source="exchangerate.host",
            )

    return out
