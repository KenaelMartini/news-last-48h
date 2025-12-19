# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from ai_core.ai_european_macrocheck_core.ai_formatter_european import format_report
from src.price_in_v3.evaluator import evaluate_price_in_v3
from src.market_snapshot.snapshot_builder import build_market_snapshot, save_snapshot
import inspect
from src.market_snapshot import snapshot_builder

print("[SNAPSHOT] builder_file =", inspect.getfile(snapshot_builder))


# -------------------------
# Paths / config
# -------------------------
BASE_DIR = Path(__file__).resolve().parents[2]  # .../News Last 48H
OUT_DIR = BASE_DIR / "KMCO_out" / "EU_check"
NEWS_CACHE = BASE_DIR / "KMCO_out" / "news_cache" / "news_last_36h.json"

MODEL = os.getenv("KMCO_OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("OPENAI_API_KEY", "")


# -------------------------
# Helpers
# -------------------------
def _load_articles(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("articles"), list):
            return data["articles"]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _build_prompt(articles: list[dict], snapshot_dict: dict) -> str:
    # News compactes (36h)
    lines = []
    for a in articles[:80]:
        title = (a.get("title") or "").strip()
        src = (a.get("source") or a.get("publisher") or "").strip()
        ts = (a.get("published") or a.get("time") or "").strip()
        snip = (a.get("summary") or a.get("snippet") or a.get("content") or "").strip()[:600]
        if title:
            lines.append(f"- {title} | {src} | {ts}\n  {snip}".strip())
    news_blob = "\n".join(lines) if lines else "(AUCUN ARTICLE CHARGÉ)"

    snap_json = json.dumps(snapshot_dict, ensure_ascii=False)

    return f"""
Tu es stratégiste Macro-FX sell-side senior. Langue: FR.
Ton: froid, factuel. Hiérarchie stricte: drivers majeurs > secondaires > bruit.
Validation obligatoire par proxys marché fournis (FX / futures rates / equities / commodities).

SOURCE OF TRUTH (PRIX) — MARKET_SNAPSHOT_JSON:
{snap_json}

RÈGLES NON NÉGOCIABLES :
- Interdiction absolue d’inventer un prix, un niveau, un rendement, ou un chiffre.
- La section “2) Market Snapshot” est PRODUITE PAR LE CODE. Tu ne la rédiges pas.
- Interdiction d’introduire des thèmes non présents dans NEWS_INPUT (ex: Brexit).
- Si manque d’info → écrire “NA” et réduire conviction.
- Les champs UST2Y_FUT/UST10Y_FUT/UST30Y_FUT/BUND_FUT sont des PRIX DE FUTURES (ex: ZN, ZT, ZB, GG), pas des rendements.
- Interdiction d’écrire “taux 10 ans = 112.59” ou “rendement = …”. Utiliser “prix future” ou “proxy rates”.
- Si tu dois parler des taux/rates, parle uniquement de direction/pression si variation est disponible, sinon NA.

Tu dois produire EXACTEMENT les sections suivantes (sans markdown, pas de ###):
1) Macro Drivers
3) Market Bias (2 à 4 paires max, conviction 0.25–1.0)
4) Technique (2-3 pivots HTF max par paire, niveaux bruts si connus, sinon NA)
5) Trades Desk (lignes : Pair | Biais | Entrée | Stop | TP | RR | %cap, RR >= 2.5)
6) Scénarios Binaires (format strict : Si X → Y, sinon Z → W)
7) Risk Mgmt
8) Review

Qualité attendue :
- Chaque biais doit inclure: driver → canal (taux réels/spreads/risk) → proxy marché (dans snapshot) → conclusion.

NEWS_INPUT (36h):
{news_blob}
""".strip()


def _summarize(prompt: str) -> str:
    if not API_KEY:
        return "ERREUR: OPENAI_API_KEY manquante."
    client = OpenAI(api_key=API_KEY)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Stratégiste macro-FX sell-side senior."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=2200,
    )
    return resp.choices[0].message.content.strip()


# -------------------------
# Main
# -------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    # 1) Load news
    articles = _load_articles(NEWS_CACHE)

    # 2) Build real market snapshot (FX + commodities + rates futures)
    snapshot = build_market_snapshot()
    snap_path = BASE_DIR / "KMCO_out" / "snapshots" / f"snapshot_EU_{today}.json"
    save_snapshot(snapshot, str(snap_path))

    # 3) Price-In v3 (stub ou moteur)
    price_in = evaluate_price_in_v3(session="EU", window_hours=36, context={"articles_n": len(articles)})

    # 4) LLM narrative (sans Market Snapshot)
    prompt = _build_prompt(articles, snapshot.to_dict())
    body_text = _summarize(prompt)

    # 5) Output paths
    out_docx = OUT_DIR / f"KMCO_EU_Session_Check_{today}.docx"
    out_pdf = OUT_DIR / f"KMCO_EU_Session_Check_{today}.pdf"

    # 6) Format report — PASSAGE EXPLICITE DU SNAPSHOT (FIX DE L’ERREUR)
    format_report(
        report_date=today,
        report_stamp=stamp,
        body_text=body_text,
        price_in=price_in,
        snapshot=snapshot.to_dict(),  # <-- FIX
        out_docx_path=str(out_docx),
        out_pdf_path=str(out_pdf),
    )

    print(f"[OK] EU report generated:\n- {out_docx}\n- {out_pdf}")


if __name__ == "__main__":
    main()
