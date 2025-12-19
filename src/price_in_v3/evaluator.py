from .schema import PriceInResult, RegimeState, PositioningState

def evaluate_price_in_v3(*, session: str, window_hours: int, context: dict | None = None) -> PriceInResult:
    # STUB v0: objectif = intégrer proprement dans les reports sans casser le pipeline
    # On remplace ensuite ce stub par: regime + positioning + reaction + scoring.
    return PriceInResult(
        session=session,  # "OVERNIGHT"/"EU"/"US"/"GLOBAL"
        window_hours=window_hours,
        status="PARTIAL",
        score=50,
        conviction=0.50,
        one_liner="Stub v0: Price-in engine wired. Await regime/positioning/reaction scoring.",
        regime=RegimeState(),
        positioning=PositioningState(),
        validation="Stub: no validation yet",
        binary="IF rates+FX confirm -> follow-through ELSE fade/flat",
        meta={"version": "v3_stub_0"}
    )
