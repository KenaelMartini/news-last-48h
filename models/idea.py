from pydantic import BaseModel, HttpUrl
from typing import List, Literal

class MacroIdea(BaseModel):
    asset: str
    direction: Literal["Long", "Short"]
    conviction: float  # 0.25, 0.50, 0.75, 1.00
    drivers_core: List[str]
    macro_context: List[str]
    risk_to_view: str
    key_data_triggers: List[str]
    sources: List[HttpUrl]
    time_horizon: str
    priority: Literal["High","Medium","Low"]
class MacroSessionReport(BaseModel):
    date: str
    session: Literal["Asia","EU","US","Global"]
    macro_biases: List[MacroIdea]
