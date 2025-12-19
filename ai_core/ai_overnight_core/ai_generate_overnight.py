# ai_core/ai_overnight_core/ai_generate_overnight.py
# -*- coding: utf-8 -*-
"""
KM&CO – Overnight Asia Session Check (23h–06h UTC)
Style 30/10 – Quant & chiffres intégrés implicitement
"""

from pathlib import Path
import json
from datetime import datetime, timedelta, timezone
import win32com.client as win32

from ai_core.ai_overnight_core.ai_summarizer_overnight import summarize_articles
from ai_core.ai_overnight_core.ai_formatter_overnight import format_report

from ai_core.intelligence.quant_bridge import quant_from_articles
from ai_core.intelligence.contextual_numbers import collect_relevant_numbers

# ---------------------------------------------------------------------
# Dossiers KM&CO standard
# ---------------------------------------------------------------------
BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "KMCO_out" / "Overnight_check"
OUT.mkdir(parents=True, exist_ok=True)

ARTICLES = BASE / "out" / "articles.json"
MD_OUT = OUT / "report_overnight_check.md"

# ---------------------------------------------------------------------
# Conversion DOCX → PDF via Word COM (standard KM&CO)
# ---------------------------------------------------------------------
def convert_to_pdf(docx_path: Path, pdf_path: Path):
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(docx_path))
    doc.SaveAs(str(pdf_path), FileFormat=17)
    doc.Close(False)
    word.Quit()

# ---------------------------------------------------------------------
# Main pipeline Overnight Asia
# ---------------------------------------------------------------------
def main():
    if not ARTICLES.exists():
        raise FileNotFoundError(f"{ARTICLES} introuvable.")

    with open(ARTICLES, "r", encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now(timezone.utc)

    # ---------------------------------------------------------------
    # FENÊTRE FIXE : SESSION ASIE 23h00 → 06h00 UTC
    # ---------------------------------------------------------------
    if now.hour < 6:
        # Si on est avant 06h00 UTC → session terminée ce matin
        start_asia = (now - timedelta(days=1)).replace(hour=23, minute=0, second=0, microsecond=0)
        end_asia = now.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        # Si on est après 06h00 UTC → on prend la nuit précédente
        start_asia = now.replace(hour=23, minute=0, second=0, microsecond=0) - timedelta(days=1)
        end_asia = now.replace(hour=6, minute=0, second=0, microsecond=0)

    # ---------------------------------------------------------------
    # Filtrage temporel des articles
    # ---------------------------------------------------------------
    filtered = []
    for a in data.get("articles", []):
        try:
            t = datetime.fromisoformat(a["published_utc"].replace("Z", "+00:00"))
            if start_asia <= t <= end_asia:
                filtered.append(a)
        except Exception:
            pass

    print(f"🌏 Fenêtre Asie : {start_asia:%Y-%m-%d %H:%M UTC} → {end_asia:%Y-%m-%d %H:%M UTC}")
    print(f"✅ {len(filtered)} articles retenus.")
    if not filtered:
        raise ValueError("Aucun article overnight dans la fenêtre 23h–06h UTC.")

    # ---------------------------------------------------------------
    # Bloc quantitatif et chiffres macro
    # ---------------------------------------------------------------
    quant = quant_from_articles(filtered)
    quant_block = quant.get("text_block", "")

    nums = collect_relevant_numbers(filtered, max_per_theme=10)
    picked = (
        nums.get("3. Devises et marchés des changes", []) +
        nums.get("2. Politique monétaire et banques centrales", []) +
        nums.get("1. Tendances macroéconomiques globales", []) +
        nums.get("5. Matières premières (énergie, métaux, etc.)", [])
    )[:12]
    datapoints_hint = " | ".join(picked)

    # ---------------------------------------------------------------
    # Génération du résumé macro Overnight (IA Core)
    # ---------------------------------------------------------------
    report_raw = summarize_articles({
        "articles": filtered,
        "quant_signal": quant_block,
        "datapoints_hint": datapoints_hint
    })

    formatted_path = format_report(report_raw, date=datetime.now())

    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(report_raw)

    # ---------------------------------------------------------------
    # Export PDF
    # ---------------------------------------------------------------
    pdf = OUT / f"KMCO_Overnight_Check_{datetime.now():%Y-%m-%d}.pdf"
    convert_to_pdf(Path(formatted_path), pdf)

    print("🏁 Rapport Overnight Check (KM&CO) généré avec succès.")

# ---------------------------------------------------------------------
if __name__ == "__main__":
    main()
