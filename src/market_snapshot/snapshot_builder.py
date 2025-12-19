# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple, List
import time
import requests
import csv
import io


# =========================
# STOOQ CONFIG
# =========================

STOOQ_QUOTE_BASE = "https://stooq.com/q/l/"   # intraday quote CSV, NO HEADER
STOOQ_DAILY_BASE = "https://stooq.com/q/d/l/" # daily history CSV, HAS HEADER

DEFAULT_TIMEOUT = 8
DEFAULT_RETRIES = 2


# =========================
# DESK UNIVERSE (STRICT)
# =========================

FX_SYMBOLS = {
    "EURUSD": "eurusd",
    "EURGBP": "eurgbp",
    "EURJPY": "eurjpy",
    "EURCHF": "eurchf",
    "EURAUD": "euraud",
    "EURCAD": "eurcad",
    "EURNZD": "eurnzd",
}

COMMODITY_SYMBOLS = {
    "WTI": "cl.f",
    "Gold": "gc.f",
}

RATES_FUT_SYMBOLS = {
    "UST2Y_FUT": "zt.f",
    "UST10Y_FUT": "zn.f",
    "UST30Y_FUT": "zb.f",
    "BUND_FUT": "gg.f",
}

# Risk/Sentiment proxies (daily)
RISK_SYMBOLS_DAILY = {
    "SPX": "^spx",
    "VIX_FUT": "VI.F",
    "FEAR_GREED": None,
}


# =========================
# UTILS
# =========================

def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)

def _utc_now_iso() -> str:
    return _utc_now().isoformat()

def _is_probably_html(text: str) -> bool:
    t = (text or "").lstrip().lower()
    return t.startswith("<!doctype") or t.startswith("<html") or "<body" in t[:500]


def _http_get(base: str, params: dict) -> Optional[str]:
    headers = {
        "User-Agent": "KMCO-Snapshot/1.0",
        "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.1",
        "Connection": "close",
    }
    for attempt in range(DEFAULT_RETRIES + 1):
        try:
            r = requests.get(base, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            if r.status_code != 200:
                time.sleep(0.2 * attempt)
                continue
            text = r.text
            if not text or len(text) < 20:
                time.sleep(0.2 * attempt)
                continue
            if _is_probably_html(text):
                return None
            return text
        except Exception:
            time.sleep(0.2 * attempt)
    return None


# =========================
# STOOQ /q/l/ (INTRADAY QUOTE)
# =========================

def _fetch_stooq_quote_csv(symbol: str, interval: str = "5") -> Optional[str]:
    return _http_get(STOOQ_QUOTE_BASE, {"s": symbol, "i": interval})


def _parse_vendor_ts_utc_from_quote_line(line: str) -> Optional[datetime]:
    parts = [p.strip() for p in (line or "").split(",")]
    if len(parts) < 3:
        return None
    ymd = parts[1]
    hms = parts[2]
    if len(ymd) != 8 or len(hms) != 6:
        return None
    try:
        return datetime(
            int(ymd[0:4]), int(ymd[4:6]), int(ymd[6:8]),
            int(hms[0:2]), int(hms[2:4]), int(hms[4:6]),
            tzinfo=timezone.utc
        )
    except Exception:
        return None


def _last_price_and_vendor_ts(csv_text: str) -> Tuple[Optional[float], Optional[datetime]]:
    if not csv_text:
        return (None, None)

    for line in reversed(csv_text.splitlines()):
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 7:
            continue
        try:
            price = float(parts[6])  # CLOSE
        except ValueError:
            continue
        vendor_ts = _parse_vendor_ts_utc_from_quote_line(line)
        return (price, vendor_ts)

    return (None, None)


def _mk_point(price: Optional[float], vendor_ts_utc: Optional[datetime]) -> Dict[str, Any]:
    now = _utc_now()
    lag_seconds: Optional[int] = None
    vendor_iso: Optional[str] = vendor_ts_utc.isoformat() if vendor_ts_utc else None

    if vendor_ts_utc is not None:
        lag = int((now - vendor_ts_utc).total_seconds())

        # Guard CET/UTC ambiguity: normalize -1h if lag is negative and fix is reasonable
        if lag < 0:
            vendor_ts_adj = vendor_ts_utc - timedelta(hours=1)
            lag2 = int((now - vendor_ts_adj).total_seconds())
            if 0 <= lag2 <= 6 * 3600:
                vendor_ts_utc = vendor_ts_adj
                vendor_iso = vendor_ts_utc.isoformat()
                lag = lag2

        lag_seconds = lag

    return {
        "price": price,
        "vendor_ts_utc": vendor_iso,
        "lag_seconds": lag_seconds,
        "change": None,
        "change_pct": None,
    }


# =========================
# STOOQ /q/d/l/ (DAILY HISTORY)
# =========================

def _fetch_stooq_daily_csv(symbol: str, *, d1: str, d2: str) -> Optional[str]:
    # Stooq expects dates as YYYYMMDD
    return _http_get(STOOQ_DAILY_BASE, {"s": symbol, "i": "d", "d1": d1, "d2": d2})

def _yyyymmdd(dt: datetime) -> str:
    return dt.strftime("%Y%m%d")

def _parse_daily_closes(csv_text: str, max_rows: int = 200) -> List[Tuple[str, float]]:
    if not csv_text:
        return []

    # Normalize BOM
    csv_text = csv_text.lstrip("\ufeff")

    f = io.StringIO(csv_text)
    reader = csv.DictReader(f)

    # Normalize fieldnames (lower + strip)
    if not reader.fieldnames:
        return []

    fields = {fn.lower().strip(): fn for fn in reader.fieldnames}

    # Stooq daily usually: Date,Open,High,Low,Close,Volume
    date_key = fields.get("date")
    close_key = fields.get("close")

    # Hard fail if no explicit Close column
    if not date_key or not close_key:
        return []

    out: List[Tuple[str, float]] = []
    for row in reader:
        d = (row.get(date_key) or "").strip()
        c = (row.get(close_key) or "").strip()
        if not d or not c:
            continue
        try:
            out.append((d, float(c)))
        except ValueError:
            continue
        if len(out) >= max_rows:
            break

    out.sort(key=lambda x: x[0])
    return out




def _pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    if new is None or old is None or old == 0:
        return None
    return (new / old - 1.0) * 100.0


def _risk_block_from_daily(symbol: Optional[str]) -> Dict[str, Any]:
    if not symbol:
        return {"price": None, "w1_pct": None, "m1_pct": None, "source": None}

    now = _utc_now()
    d2 = _yyyymmdd(now)
    d1 = _yyyymmdd(now - timedelta(days=120))

    variants = [symbol, symbol.upper(), symbol.lower()]
    seen = set()
    variants = [v for v in variants if not (v in seen or seen.add(v))]

    # 1) Daily windowed (best)
    for sym in variants:
        raw = _fetch_stooq_daily_csv(sym, d1=d1, d2=d2)
        closes = _parse_daily_closes(raw, max_rows=200)
        if closes:
            last_close = closes[-1][1]
            w1_close = closes[-6][1] if len(closes) >= 6 else None
            m1_close = closes[-23][1] if len(closes) >= 23 else None
            return {
                "price": last_close,
                "w1_pct": _pct_change(last_close, w1_close),
                "m1_pct": _pct_change(last_close, m1_close),
                "source": f"stooq:{sym}",
            }

    # 2) Quote fallback (price only)
    for sym in variants:
        raw_q = _fetch_stooq_quote_csv(sym, interval="5")
        px, _ = _last_price_and_vendor_ts(raw_q)
        if px is not None:
            return {
                "price": px,
                "w1_pct": None,
                "m1_pct": None,
                "source": f"stooq_quote:{sym}",
            }

    return {"price": None, "w1_pct": None, "m1_pct": None, "source": f"stooq:{symbol}"}




# =========================
# SNAPSHOT MODEL
# =========================

@dataclass
class MarketSnapshot:
    asof_utc: str
    fx: Dict[str, Dict[str, Any]]
    commodities: Dict[str, Dict[str, Any]]
    rates: Dict[str, Dict[str, Any]]
    risk: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asof_utc": self.asof_utc,
            "fx": self.fx,
            "commodities": self.commodities,
            "rates": self.rates,
            "risk": self.risk,
        }


# =========================
# SNAPSHOT BUILDER
# =========================

def build_market_snapshot(interval: str = "5") -> MarketSnapshot:
    asof = _utc_now_iso()

    fx_out: Dict[str, Dict[str, Any]] = {}
    for label, sym in FX_SYMBOLS.items():
        raw = _fetch_stooq_quote_csv(sym, interval)
        price, vts = _last_price_and_vendor_ts(raw)
        fx_out[label] = _mk_point(price, vts)

    comm_out: Dict[str, Dict[str, Any]] = {}
    for label, sym in COMMODITY_SYMBOLS.items():
        raw = _fetch_stooq_quote_csv(sym, interval)
        price, vts = _last_price_and_vendor_ts(raw)
        comm_out[label] = _mk_point(price, vts)

    rates_out: Dict[str, Dict[str, Any]] = {}
    for label, sym in RATES_FUT_SYMBOLS.items():
        raw = _fetch_stooq_quote_csv(sym, interval)
        price, vts = _last_price_and_vendor_ts(raw)
        rates_out[label] = _mk_point(price, vts)

    # Risk (daily): level + 1w/1m change
    risk_out: Dict[str, Dict[str, Any]] = {}
    for label, sym in RISK_SYMBOLS_DAILY.items():
        risk_out[label] = _risk_block_from_daily(sym)

    return MarketSnapshot(
        asof_utc=asof,
        fx=fx_out,
        commodities=comm_out,
        rates=rates_out,
        risk=risk_out,
    )


def save_snapshot(snapshot: MarketSnapshot, path: str) -> None:
    import json
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
