# src/price_in/driver_pricein.py
from collections import defaultdict, Counter

# Mapping simple des drivers (catégories desk)
DRIVER_KEYS = {
    "CB_path":      ["fed","ecb","boj","boe","boc","rba","rbnz","snb","rate","hike","cut","ycc","qe","qt","powell","lagarde","ueda","bailey","macklem","jordan"],
    "inflation":    ["inflation","cpi","ppi","core","prices","wage"],
    "growth_data":  ["gdp","growth","pmi","ism","manufacturing","services","retail sales"],
    "employment":   ["nfp","jobs","unemployment","payrolls","labor","wage"],
    "risk_regime":  ["risk-off","flight to safety","volatility","selloff","geopolitic","conflict","war","oil","brent","wti","opec"],
}

def classify_driver_from_text(text: str) -> list[str]:
    t = (text or "").lower()
    tags = []
    for k, kws in DRIVER_KEYS.items():
        if any(kw in t for kw in kws):
            tags.append(k)
    return tags or ["misc"]

def driver_price_in_from_ai(ai_blob: dict) -> dict:
    """
    Convertit le blob IA article → métriques price-in par driver.
    On prend les champs produits par macro_nlp_analyze + enrich_price_inference
    si disponibles, sinon on met des défauts conservateurs.
    """
    if not isinstance(ai_blob, dict):
        ai_blob = {}
    # Valeurs par défaut robustes
    ma = float(ai_blob.get("market_agreement", ai_blob.get("price_in_market_agreement", 0.0)) or 0.0)
    resid = float(ai_blob.get("residual_trade_value", ai_blob.get("price_in_residual", 0.0)) or 0.0)
    state = str(ai_blob.get("pricing_state", "ambiguous") or "ambiguous")
    return {"ma": ma, "resid": resid, "state": state}

def aggregate_price_in_detail(items_base: list[dict], items_quote: list[dict]) -> dict:
    """
    Agrège article→driver→métriques pour une paire.
    Retourne un dict stable: {driver: {avg_ma, avg_resid, state, count}}
    + un résumé global.
    """
    buckets = defaultdict(list)

    for it in (items_base + items_quote):
        pi = it.get("price_in", {}) or {}
        ai = it.get("macro_ai", {}) or {}
        # fallback: si enrich_price_inference a déjà écrit les champs dans it["price_in"]
        ma   = float(pi.get("market_agreement", 0.0) or 0.0)
        resid= float(pi.get("residual_trade_value", 0.0) or 0.0)
        state= str(pi.get("pricing_state", "ambiguous") or "ambiguous")

        # on essaie de déduire le/les drivers depuis le texte
        tags = it.get("driver_tags")
        if not tags:
            tags = classify_driver_from_text(it.get("text",""))
            it["driver_tags"] = tags

        for tag in tags:
            buckets[tag].append({"ma": ma, "resid": resid, "state": state})

    out = {}
    states_flat = []
    all_ma, all_res = [], []
    for drv, arr in buckets.items():
        if not arr:
            continue
        avg_ma   = sum(x["ma"]   for x in arr)/len(arr)
        avg_res  = sum(x["resid"]for x in arr)/len(arr)
        states   = [x["state"] for x in arr]
        maj_state= max(set(states), key=states.count)
        out[drv] = {
            "avg_market_agreement": round(avg_ma,3),
            "avg_residual_trade_value": round(avg_res,3),
            "pricing_state": maj_state,
            "count": len(arr)
        }
        all_ma.append(avg_ma)
        all_res.append(avg_res)
        states_flat.extend(states)

    if states_flat:
        global_state = max(set(states_flat), key=states_flat.count)
    else:
        global_state = "ambiguous"

    summary = {
        "global_pricing_state": global_state,
        "drivers": out,
        "avg_market_agreement": round(sum(all_ma)/len(all_ma),3) if all_ma else 0.0,
        "avg_residual_trade_value": round(sum(all_res)/len(all_res),3) if all_res else 0.0,
    }
    return summary
