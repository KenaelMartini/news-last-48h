# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import requests

URL = "https://www.finhacker.cz/en/fear-and-greed-index-historical-data-and-chart/"
UA = "Mozilla/5.0"

_RE_VALUE = re.compile(
    r"current value of the Fear\s*&\s*Greed Index.*? is\s+(\d+)\s*-",
    re.IGNORECASE
)
_RE_DATE = re.compile(
    r"as of\s+([A-Za-z]{3}\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE
)

# Local history (intentionally under data/ => ignored by git)
HIST_PATH = Path("kmco_pipeline/data/risk/fear_greed_history.jsonl")


@dataclass
class FearGreedPoint:
    value: int
    asof_text: Optional[str]
    source: str = "finhacker"


def fetch_fear_greed_value(timeout: int = 10) -> Optional[FearGreedPoint]:
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    html = r.text or ""

    m_val = _RE_VALUE.search(html)
    if not m_val:
        return None

    val = int(m_val.group(1))
    m_dt = _RE_DATE.search(html)
    asof = m_dt.group(1) if m_dt else None

    return FearGreedPoint(value=val, asof_text=asof)


def append_fg_history(value: int, ts_utc: str) -> None:
    HIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HIST_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts_utc": ts_utc, "value": value}) + "\n")


def load_fg_history() -> List[Dict[str, Any]]:
    if not HIST_PATH.exists():
        return []
    out: List[Dict[str, Any]] = []
    with HIST_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def pct_change_from(history: List[Dict[str, Any]], days_back: int) -> Optional[float]:
    if not history:
        return None

    history_sorted = sorted(history, key=lambda x: x.get("ts_utc", ""))
    last = history_sorted[-1]
    last_ts = last.get("ts_utc")
    last_val = last.get("value")

    if not last_ts or last_val is None:
        return None

    # Accept both "...Z" and naive iso strings
    last_dt = datetime.fromisoformat(last_ts.replace("Z", ""))

    target_dt = last_dt - timedelta(days=days_back)

    prev = None
    for row in reversed(history_sorted):
        ts = row.get("ts_utc")
        if not ts:
            continue
        dt = datetime.fromisoformat(ts.replace("Z", ""))
        if dt <= target_dt:
            prev = row
            break

    if not prev:
        return None

    prev_val = prev.get("value")
    if prev_val in (0, None):
        return None

    return (last_val - prev_val) / prev_val * 100.0
