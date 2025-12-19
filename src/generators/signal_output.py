import json
from datetime import datetime
from pathlib import Path

def save_signals_json(signals, session, out_dir="kmco_pipeline/data"):
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    # Convertir chaque signal en dict propre (Pydantic → JSON safe)
    signals_dump = [s.model_dump(mode="json") for s in signals]

    payload = {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "session": session,
        "signals": signals_dump
    }

    file_name = f"signals_{session}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out_path = Path(out_dir) / file_name
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"✅ JSON signal export: {out_path}")
    return out_path
