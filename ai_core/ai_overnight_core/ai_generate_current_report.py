# -*- coding: utf-8 -*-
"""
current_macro_check.py — KM&CO – Analyse macro sur fenêtre horaire glissante
But : récupérer les news et produire un rapport "Current Macro Check"
sur les dernières X heures, au format institutionnel KM&CO.
"""

from pathlib import Path
import json
from datetime import datetime, timedelta, timezone
from ai_core.ai_overnight_core.ai_summarizer_overnight import summarize_articles
from ai_core.ai_overnight_core.ai_formatter_overnight import format_report
import win32com.client as win32  # conversion Word -> PDF (nécessite Word installé)

# ======================================================
# CONFIG
# ======================================================

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "KMCO_out"
ARTICLES = OUT / "articles.json"
MD_OUT = OUT / "report_current_check.md"

# Fenêtre horaire glissante (en heures)
LOOKBACK_HOURS = 12  # <--- à ajuster selon ton besoin


# ======================================================
# FONCTIONS
# ======================================================

def convert_to_pdf(docx_path: Path, pdf_path: Path):
    """Convertit un DOCX en PDF via Word COM API (Windows only)."""
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    doc = word.Documents.Open(str(docx_path))
    doc.SaveAs(str(pdf_path), FileFormat=17)  # 17 = wdFormatPDF
    doc.Close(False)
    word.Quit()
    print(f"✅ Export PDF terminé : {pdf_path}")


# ======================================================
# MAIN
# ======================================================

def main():
    if not ARTICLES.exists():
        raise FileNotFoundError(f"{ARTICLES} introuvable.")

    with open(ARTICLES, "r", encoding="utf-8") as f:
        data = json.load(f)

    # === FENÊTRE GLISSANTE ===
    now_utc = datetime.now(timezone.utc)
    start_window = now_utc - timedelta(hours=LOOKBACK_HOURS)
    end_window = now_utc

    filtered_articles = []
    for a in data.get("articles", []):
        try:
            pub_time = datetime.fromisoformat(a["published_utc"].replace("Z", "+00:00"))
            if start_window <= pub_time <= end_window:
                filtered_articles.append(a)
        except Exception:
            continue

    print(f"🕐 Fenêtre glissante : {start_window:%Y-%m-%d %H:%M UTC} → {end_window:%Y-%m-%d %H:%M UTC}")
    print(f"✅ {len(filtered_articles)} articles retenus sur {LOOKBACK_HOURS}h.")

    if not filtered_articles:
        raise ValueError(f"Aucun article trouvé dans la fenêtre ({LOOKBACK_HOURS}h).")

    data["articles"] = filtered_articles

    # === GÉNÉRATION RAPPORT ===
    report_raw = summarize_articles(data)
    formatted_path = format_report(report_raw, date=datetime.now())

    OUT.mkdir(exist_ok=True)
    with open(MD_OUT, "w", encoding="utf-8") as f:
        f.write(report_raw)
    print(f"✅ Rapport brut : {MD_OUT}")
    print(f"✅ Rapport institutionnel Word généré : {formatted_path}")

    # === CONVERSION PDF ===
    date_str = datetime.now().strftime("%Y-%m-%d")
    pdf_path = OUT / f"KMCO_Current_Macro_Check_{date_str}.pdf"
    convert_to_pdf(Path(formatted_path), pdf_path)


if __name__ == "__main__":
    main()
