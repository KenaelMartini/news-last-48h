# -*- coding: utf-8 -*-
"""
ai_generate_us.py — KM&CO – US Session Check (14h–22h UTC)
Date du header = date de la session US analysée (pas date d'exécution)
"""

from pathlib import Path
import json
from datetime import datetime, timedelta, timezone
import win32com.client as win32

from ai_core.ai_us_macrocheck_core.ai_summarizer_us import summarize_articles
from ai_core.ai_us_macrocheck_core.ai_formatter_us import format_report

from ai_core.intelligence.quant_bridge import quant_from_articles
from ai_core.intelligence.contextual_numbers import collect_relevant_numbers


BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "KMCO_out" / "US_check"
OUT.mkdir(parents=True, exist_ok=True)

ARTICLES = BASE / "out" / "articles.json"
MD_OUT = OUT / "report_us_check.md"


def convert_to_pdf(docx_path, pdf_path):
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(docx_path))
        doc.SaveAs2(str(pdf_path), FileFormat=17)
        doc.Close()
    finally:
        word.Quit()


def get_us_session_date():
    """
    Renvoie la date de la dernière session US disponible.
    - Si on est entre 14h et 22h UTC -> date du jour
    - Sinon -> date de la session US précédente
    """
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()
    start_us = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=14)
    end_us = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc).replace(hour=22)

    if start_us <= now_utc <= end_us:
        return today  # session du jour
    else:
        return today - timedelta(days=1)  # session US de la veille


def main():
    if not ARTICLES.exists():
        raise FileNotFoundError(f"{ARTICLES} introuvable.")

    # 1) On récupère la vraie date de session US
    us_date = get_us_session_date()

    with open(ARTICLES, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 2) Fenêtre US basée sur la date détectée
    start_us = datetime(us_date.year, us_date.month, us_date.day, 14, 0, tzinfo=timezone.utc)
    end_us = datetime(us_date.year, us_date.month, us_date.day, 22, 0, tzinfo=timezone.utc)

    filtered = []
    for a in data.get("articles", []):
        try:
            t = datetime.fromisoformat(a["published_utc"].replace("Z", "+00:00"))
            if start_us <= t <= end_us:
                filtered.append(a)
        except:
            continue

    print(f"🕑 Fenêtre US analysée : {start_us:%Y-%m-%d %H:%M UTC} → {end_us:%Y-%m-%d %H:%M UTC}")
    print(f"📌 Date du header = {us_date}")
    print(f"📰 {len(filtered)} articles retenus.")

    if not filtered:
        raise ValueError("Aucun article dans la fenêtre US sélectionnée.")

    # 3) Intelligence cachée
    quant = quant_from_articles(filtered)
    quant_block = quant.get("text_block", "")

    nums = collect_relevant_numbers(filtered, max_per_theme=10)
    picked = (
        nums.get("3. Devises et marchés des changes", [])
        + nums.get("2. Politique monétaire et banques centrales", [])
        + nums.get("1. Tendances macroéconomiques globales", [])
        + nums.get("5. Matières premières (énergie, métaux, etc.)", [])
    )[:12]
    datapoints_hint = " | ".join(picked)

    # 4) Résumé texte (LLM)
    report_raw = summarize_articles({
        "articles": filtered,
        "quant_signal": quant_block,
        "datapoints_hint": datapoints_hint
    })

    # 5) Format KM&CO avec la bonne date US
    formatted_path = format_report(report_raw, date=datetime(us_date.year, us_date.month, us_date.day))

    # 6) Markdown brut
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(report_raw)

    # 7) PDF final avec la date US
    pdf_path = OUT / f"KMCO_US_Session_Check_{us_date}.pdf"
    convert_to_pdf(Path(formatted_path), pdf_path)

    print("🏁 Rapport US Session Check généré avec la bonne date.")


if __name__ == "__main__":
    main()
