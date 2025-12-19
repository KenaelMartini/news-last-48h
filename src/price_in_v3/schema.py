from dataclasses import dataclass, asdict
from typing import Literal, Optional, Dict, Any

PriceInStatus = Literal["FULLY", "PARTIAL", "NOT"]
SessionName = Literal["OVERNIGHT", "EU", "US", "GLOBAL"]

@dataclass(frozen=True)
class RegimeState:
    risk: str = "UNKNOWN"        # RISK_ON / RISK_OFF / MIXED / UNKNOWN
    vol: str = "UNKNOWN"         # LOW / NORMAL / HIGH / UNKNOWN
    rates: str = "UNKNOWN"       # BULL / BEAR / MIXED / UNKNOWN
    liquidity: str = "UNKNOWN"   # GOOD / THIN / UNKNOWN

@dataclass(frozen=True)
class PositioningState:
    bias: str = "UNKNOWN"        # SUPPORTIVE / CONTRA / NEUTRAL / UNKNOWN
    constraint: str = "UNKNOWN"  # NONE / ONE_SIDED / EVENT_RISK / UNKNOWN

@dataclass(frozen=True)
class PriceInResult:
    session: SessionName
    window_hours: int
    status: PriceInStatus
    score: int                  # 0-100
    conviction: float           # 0.25-1.0
    one_liner: str
    regime: RegimeState
    positioning: PositioningState
    validation: str             # short: "Rates+FX confirm" etc.
    binary: str                 # "IF X -> Y ELSE Z"
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d
