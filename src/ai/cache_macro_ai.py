# src/ai/cache_macro_ai.py
import os, json, hashlib
from pathlib import Path
from typing import Dict, Optional

CACHE_DIR = Path("kmco_pipeline/data")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH = CACHE_DIR / "macro_ai_cache.jsonl"

def _key(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def load_cache() -> dict:
    cache = {}
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    cache[row["key"]] = row["value"]
                except Exception:
                    continue
    return cache

def get_cached(text: str, cache: Optional[dict] = None) -> Optional[Dict]:
    cache = cache or load_cache()
    return cache.get(_key(text))

def put_cache(text: str, value: Dict) -> None:
    rec = {"key": _key(text), "value": value}
    with open(CACHE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
