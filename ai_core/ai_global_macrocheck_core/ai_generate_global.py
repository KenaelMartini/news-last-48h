# -*- coding: utf-8 -*-
"""
KM&CO – Global Macro Check (12h–24h)
Version sans restriction horaire : agrège tout le dernier JSON.
"""

from pathlib import Path
import json
from datetime import datetime
import win32com.client as win32
from docx2pdf import convert
from ai_core.ai_global_macrocheck_core.ai_summarizer_global import summarize_articles
from ai_core.ai_global_macrocheck_core.ai_formatter_global import format_report
from ai_core.intelligence.quant_bridge import quant_from_articles
from ai_core.intelligence.contextual_numbers import collect_relevant_numbers

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "KMCO_out" / "Global_check"
OUT.mkdir(parents=True, exist_ok=True)

ARTICLES = BASE / "out" / "articles.json"
MD_OUT = OUT / "report_global_check.md"

def convert_to_pdf(docx_path: Path, pdf_path: Path):
    """Convertit DOCX en PDF (Word COM API)."""
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(docx_path))
    doc.SaveAs(str(pdf_path), FileFormat=17)
    doc.Close(False)
    word.Quit()
    print(f"✅ PDF généré : {pdf_path}")

def main():
    if not ARTICLES.exists():
        raise FileNotFoundError(f"{ARTICLES} introuvable.")

    with open(ARTICLES, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data.get("articles", [])
    print(f"✅ {len(articles)} articles chargés pour le Global Check.")

    quant = quant_from_articles(articles)
    quant_block = quant.get("text_block", "")

    nums = collect_relevant_numbers(articles, max_per_theme=10)
    picked = (
        nums.get("3. Devises et marchés des changes", [])
        + nums.get("2. Politique monétaire et banques centrales", [])
        + nums.get("1. Tendances macroéconomiques globales", [])
        + nums.get("5. Matières premières (énergie, métaux, etc.)", [])
    )[:12]
    datapoints_hint = " | ".join(picked)

    report_raw = summarize_articles({
        "articles": articles,
        "quant_signal": quant_block,
        "datapoints_hint": datapoints_hint
    })

    formatted_path = format_report(report_raw, date=datetime.now())

    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(report_raw)

    pdf_path = OUT / f"KMCO_Global_Check_{datetime.now():%Y-%m-%d}.pdf"
    convert_to_pdf(Path(formatted_path), pdf_path)

    print("🏁 Rapport Global Macro Check généré.")
    print("Lecture :", ARTICLES.resolve())

if __name__ == "__main__":
    main()
