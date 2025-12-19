"""
KM&CO – Signal Engine Runner
Standalone execution for full-database FX signal generation.
This script is independent from session-based textual reports.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.generators.build_signals import build_signals
from models.signal import MacroSignalSet
from models.kmco_save import save_json, save_table, save_log

SESSION = "Global"

# JSON Saver (for pure cleaned export purpose)
def save_signals_json(signals, session, out_dir="kmco_pipeline/data"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp_utc": datetime.utcnow().isoformat().replace("+00:00","Z"),
        "session": session,
        "signals": signals
    }

    file_name = f"signals_{session}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = Path(out_dir) / file_name
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON signal export: {out_path}")
    return out_path


def canonical_clean(u: str):
    from urllib.parse import urlparse, urlunparse
    try:
        p = urlparse(u)
        return urlunparse(p._replace(fragment="", query=""))
    except:
        return u


def main():
    print("🔎 Loading full news database for signal engine...")
    
    sigs, details_store = build_signals(max_signals=5)

    if not sigs:
        print("⚠️ No signals produced.")
        return

    # Build tier-1 clean signal object
    # --- Final export patch ---
    as_of_ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    out = {
        "signals": {
            "as_of": as_of_ts,
            "session": SESSION,
            "signals": [s.model_dump(mode="json") for s in sigs]
        }
    }


    print("💾 Saving KM&CO core JSON + table...")
    save_path = save_json(out, session=SESSION)

    print(f"✅ Saved JSON: {save_path}")
    save_log(f"[KMCO-SIGNALS] Generated {len(sigs)} signals FULL pass")
    # Force overwrite (no old file reuse)
    final_json = f"D:/trading/News Last 48H/kmco_pipeline/data/ideas/macro_ideas_{datetime.now().strftime('%Y-%m-%d')}_Global.json"
    with open(final_json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"💾 Overwritten: {final_json}")

    save_log(f"[KMCO-SIGNALS] Generated {len(sigs)} signals FULL pass")

    # Build human readable signal table
    import pandas as pd
    rows = []
    for s in sigs:
        # Safe retrieval of price-in details
        if isinstance(details_store, dict):
            pid = details_store.get(s.asset, {})
        elif isinstance(details_store, list):
            # fallback: no detailed info
            pid = {}
        else:
            pid = {}

        drivers = pid.get("drivers", {}) if isinstance(pid, dict) else {}
        top_drv = sorted(
            drivers.items(),
            key=lambda kv: kv[1].get("avg_residual_trade_value", 0),
            reverse=True
        )[:3]

        pid_str = " ; ".join(
            f"{k}: resid={v.get('avg_residual_trade_value',0):.2f}, "
            f"ma={v.get('avg_market_agreement',0):.2f}, "
            f"{v.get('pricing_state','ambiguous')}"
            for k,v in top_drv
        ) or "n/a"

        rows.append({
            "Asset": s.asset,
            "Direction": s.direction,
            "Conviction": s.conviction,
            "Score": s.score,
            "Drivers": " | ".join(s.drivers),
            "Triggers": " | ".join(s.triggers),
            "Horizon": s.horizon,
            "Residual Value": f"{s.meta.get('pi_avg_resid',0):.2f}",
            "State": getattr(s, "price_in_state", "ambiguous"),
            "Boost": f"{s.meta.get('pi_boost',0):.2f}",
            "PI Top Drivers": pid_str,
            "Sources": " | ".join(canonical_clean(str(u)) for u in s.sources)
        })

    df = pd.DataFrame(rows).astype(str)
    save_table(df, session=SESSION)

    print(f"✅ Signals: {len(sigs)}")
    print("🏁 Full signal pipeline done.")


if __name__ == "__main__":
    main()
