from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class SnapshotValue:
    symbol: str
    price: Optional[float]          # None => NA
    change: Optional[float] = None
    change_pct: Optional[float] = None
    currency: Optional[str] = None
    ts_utc: Optional[str] = None
    source: str = "NA"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class MarketSnapshot:
    asof_utc: str
    fx: Dict[str, SnapshotValue]
    rates: Dict[str, SnapshotValue]        # proxies futures (ZN, ZT, RX...)
    commodities: Dict[str, SnapshotValue]
    equities: Dict[str, SnapshotValue]
    meta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asof_utc": self.asof_utc,
            "fx": {k: v.to_dict() for k, v in self.fx.items()},
            "rates": {k: v.to_dict() for k, v in self.rates.items()},
            "commodities": {k: v.to_dict() for k, v in self.commodities.items()},
            "equities": {k: v.to_dict() for k, v in self.equities.items()},
            "meta": self.meta,
        }
