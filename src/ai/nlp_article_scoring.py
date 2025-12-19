# src/ai/nlp_article_scoring.py
from __future__ import annotations
from typing import Dict, Any
import time
from openai import OpenAI
import hashlib
import json
import os
from tqdm import tqdm


CACHE_PATH = "D:/trading/News Last 48H/kmco_pipeline/data/cache/ia_scores.json"

SYSTEM_PROMPT = """
You are a senior macro/FX analyst on a tier-1 sell-side desk.
Task: extract structured macro signals from a news article.

Rules:
- Output JSON only, no commentary.
- Tone: institutional, concise, data-driven.
- Prioritise monetary policy, real rates, inflation, labour data, sovereign spreads, liquidity
- FX bias must reflect policy divergence & risk sentiment.
- Price-in detection is mandatory.

Output schema:
{
  "meta": {
    "ccys": ["USD","JPY"],
    "published_at": null,
    "source_quality": 0.7
  },
  "score": {
    "cb_tone": -1..1,
    "infl_tone": -1..1,
    "emp_tone": -1..1,
    "growth_tone": -1..1,
    "surprise_sign": -1..1,
    "fx_bias": {
      "USD": 0..1,
      "EUR": 0..1,
      "GBP": 0..1,
      "JPY": 0..1,
      "CHF": 0..1,
      "AUD": 0..1,
      "NZD": 0..1,
      "CAD": 0..1
    },
    "priced_in_hint": 0..1,
    "credibility": 0..1
  }
}

Logic:
- Rate/CB guidance > inflation > labour > growth > narrative
- Ignore non-macro content
- Detect if tone already priced using language patterns like:
  "already expected", "fully priced", "market shrugged", "priced in"
"""

client = OpenAI()

CACHE_PATH = "D:/trading/News Last 48H/kmco_pipeline/data/cache/ia_scores.json"
os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

try:
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        CACHE = json.load(f)
except:
    CACHE = {}

def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _save_cache():
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(CACHE, f, ensure_ascii=False, indent=2)

PROMPT = """
You are an institutional macro/FX analyst. 
Score this news text. Output ONLY JSON with:

{
  "hawk_dove": -1 to +1,
  "risk_sentiment": -1 to +1,
  "fx_direction": {
     "USD": -1 to +1,
     "EUR": -1 to +1,
     "GBP": -1 to +1,
     "JPY": -1 to +1,
     "CHF": -1 to +1,
     "AUD": -1 to +1,
     "NZD": -1 to +1,
     "CAD": -1 to +1
  }
}
"""

def call_model(text: str) -> Dict[str, Any]:
    resp = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
    )

    raw = resp.choices[0].message.content

    try:
        out = json.loads(raw)
        # Sécurité: garantir les champs attendus même si l'IA oublie un bout
        return {
            "meta": out.get("meta", {
                "ccys": [],
                "published_at": None,
                "source_quality": 0.7
            }),
            "score": {
                "fx_bias": out.get("score", {}).get("fx_bias", {k:0 for k in ["USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD"]}),
                "cb_tone": float(out.get("score", {}).get("cb_tone", 0)),
                "infl_tone": float(out.get("score", {}).get("infl_tone", 0)),
                "emp_tone": float(out.get("score", {}).get("emp_tone", 0)),
                "growth_tone": float(out.get("score", {}).get("growth_tone", 0)),
                "surprise_sign": float(out.get("score", {}).get("surprise_sign", 0)),
                "priced_in_hint": float(out.get("score", {}).get("priced_in_hint", 0.5)),
                "credibility": float(out.get("score", {}).get("credibility", 0.7)),
            }
        }

    except Exception:
        # fallback ultra-durci si model hallucine
        return {
            "meta": {
                "ccys": [],
                "published_at": None,
                "source_quality": 0.7
            },
            "score": {
                "fx_bias": {k:0 for k in ["USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD"]},
                "cb_tone": 0,
                "infl_tone": 0,
                "emp_tone": 0,
                "growth_tone": 0,
                "surprise_sign": 0,
                "priced_in_hint": 0.5,
                "credibility": 0.7
            }
        }


def score_article(text: str, meta: dict = None) -> Dict[str, Any]:
    meta = meta or {}

    key = _cache_key(text)

    # --- Vérifie si déjà scoré ---
    if key in CACHE:
        out = CACHE[key]
    else:
        try:
            out = call_model(text)
            CACHE[key] = out
            _save_cache()
        except Exception as e:
            print(f"[IA scoring] ⚠️ Error on article: {e}")
            out = {
                "meta": {"ccys": [], "published_at": None, "source_quality": 0.7},
                "score": {
                    "fx_bias": {k: 0 for k in ["USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD"]},
                    "cb_tone": 0,
                    "infl_tone": 0,
                    "emp_tone": 0,
                    "growth_tone": 0,
                    "surprise_sign": 0,
                    "priced_in_hint": 0.5,
                    "credibility": 0.7
                }
            }
            # même si erreur, on le met dans le cache pour pas replanter en boucle
            CACHE[key] = out
            _save_cache()

        # 💡 suppression du sleep pour accélérer le batch
        # (tu peux le remettre à 0.2 si tu approches du rate-limit)
        # time.sleep(0.2)

    # --- Injection meta sans casser l'output JSON ---
    out = dict(out)
    out["meta"] = {
        "ccys": meta.get("ccys", []),
        "source_quality": meta.get("source_quality", 0.7),
        "published_at": meta.get("published_at"),
        "url": meta.get("url"),
    }

    return out

