from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Literal

class MacroSignal(BaseModel):
    asset: str
    direction: Literal["Long","Short"]
    conviction: float
    score: float
    drivers: List[str]
    triggers: List[str]
    risk_to_view: str
    horizon: str
    sources: List[HttpUrl]
    meta: Dict[str, float | Dict[str, float] | int]

class MacroSignalSet(BaseModel):
    as_of: str
    session: Literal["Asia","EU","US","Global"]
    signals: List[MacroSignal]
