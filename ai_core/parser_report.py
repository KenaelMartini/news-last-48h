# -*- coding: utf-8 -*-
"""
KM&CO Report Parser – Version institutionnelle
Extraction automatique des articles depuis les rapports PDF bruts.
"""

import re
import json
from datetime import datetime
from pathlib import Path
import pdfplumber


def extract_articles(pdf_path: Path):
    """Extrait les articles du rapport PDF KM&CO."""
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # --- Nettoyage global ---
    text = text.replace("\xa0", " ").replace("\ufeff", "")
    text = re.sub(r"\s{2,}", " ", text).strip()

    # --- Découpage en articles ---
    raw_blocks = re.split(r"\n\d{1,3}\.\s", text)
    articles = []

    for i, block in enumerate(raw_blocks):
        block = block.strip()
        if not block or "http" not in block:
            continue

        # --- Titre ---
        title_part = block.split("·")[0].strip()
        title = re.sub(r"https?://\S+", "", title_part).strip()

        # --- Lien ---
        url_match = re.search(r"https?://\S+", block)
        url = url_match.group(0).strip() if url_match else None

        # --- Source ---
        src_match = re.search(r"(Reuters|Bloomberg|BBC|InvestingLive|CNBC|FT|WSJ)", block, re.I)
        source = src_match.group(1) if src_match else "Unknown"

        # --- Timestamp ---
        dt_match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", block)
        timestamp = dt_match.group(0) if dt_match else datetime.utcnow().isoformat()

        articles.append({
            "id": i + 1,
            "title": title,
            "source": source,
            "url": url,
            "timestamp": timestamp
        })

    return articles


def save_json(articles, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(articles)} articles extraits → {out_path}")


def main():
    pdf_path = Path(r"D:\\trading\\KMCO_out\\KMCO_Global_Macro_Report_2025-10-24_NEW.pdf")
    out_path = Path(r"D:\\trading\\KMCO_out\\articles_2025-10-24.json")

    articles = extract_articles(pdf_path)
    save_json(articles, out_path)


if __name__ == "__main__":
    main()
