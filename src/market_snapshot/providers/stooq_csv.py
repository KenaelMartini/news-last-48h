from __future__ import annotations

import csv
import io
import requests
from datetime import datetime, timezone
from typing import Dict, Optional

from ..schema import SnapshotValue

# Stooq CSV endpoint (historical/intraday):
# https://stooq.com/q/l/?s=cl.f&i=5   (5-min bars)
# https://stooq.com/q/l/?s=^spx&i=d  (daily)
STOOQ_CSV_URL = "https://stooq.com/q/l/"

def _last_close_from_csv(text: str) -> Optional[float]:
    # CSV typically: Date,Time,Open,High,Low,Close,Volume
    # or daily: Date,Open,High,Low,Close,Volume
    f = io.StringIO(text)
    reader = csv.reader(f)
    rows = list(reader)
    if not rows or len(rows) < 2:
        return None
    header = [h.strip().lower() for h in rows[0]]
    # find close column
    try:
        close_idx = header.index("close")
    except ValueError:
        return None
    # last data row
    for row in reversed(rows[1:]):
        if len(row) <= close_idx:
            continue
        v = row[close_idx].strip()
        if not v:
            continue
        try:
            return float(v)
        except Exception:
            continue
    return None

def fetch_last_close(symbols: list[str], interval: str = "5", timeout_s: int = 12) -> Dict[str, SnapshotValue]:
    """
    interval:
      - "5" for 5-min
      - "d" for daily
    """
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    out: Dict[str, SnapshotValue] = {}
    headers = {"User-Agent": "Mozilla/5.0"}

    for sym in symbols:
        try:
            r = requests.get(STOOQ_CSV_URL, params={"s": sym, "i": interval}, timeout=timeout_s, headers=headers)
            r.raise_for_status()
            px = _last_close_from_csv(r.text)
            out[sym] = SnapshotValue(
                symbol=sym,
                price=px,
                change=None,
                change_pct=None,
                currency=None,
                ts_utc=ts,
                source=f"stooq_csv(i={interval})",
            )
        except Exception as e:
            print(f"[SNAPSHOT][STOOQ_CSV] ERROR sym={sym} i={interval} -> {e}")
            out[sym] = SnapshotValue(symbol=sym, price=None, ts_utc=ts, source=f"stooq_csv(i={interval})")

    return out
