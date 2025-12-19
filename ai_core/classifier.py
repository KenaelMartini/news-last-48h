# -*- coding: utf-8 -*-
"""
KM&CO Classifier — Trie les articles JSON par thèmes macro.
"""

import json, re, ast
from pathlib import Path

MAPPING = {
    "Politique monétaire": ["Fed", "ECB", "BoE", "interest rate", "inflation", "CPI", "monetary", "central bank"],
    "Macroéconomie globale": ["GDP", "growth", "PMI", "recession", "output", "unemployment"],
    "Devises": ["USD", "EUR", "JPY", "FX", "currency", "exchange rate"],
    "Marchés boursiers": ["S&P", "Nasdaq", "equity", "stocks", "earnings", "Dow"],
    "Matières premières": ["oil", "Brent", "OPEC", "gold", "commodity"],
    "Risques géopolitiques": ["China", "Russia", "Ukraine", "war", "Middle East", "sanction"],
    "Technologies / Réglementation": ["AI", "quantum", "chips", "semiconductor", "regulation"],
}

def classify_article(article):
    text = f"{article.get('title','')} {article.get('summary','')}".lower()
    for theme, keywords in MAPPING.items():
        if any(k.lower() in text for k in keywords):
            return theme
    return "Autres"

def main():
    in_path = Path(r"D:\trading\News Last 48H\out\articles.json")
    out_path = Path(r"D:\trading\News Last 48H\KMCO_out\articles_grouped.json")

    data_raw = json.load(open(in_path, encoding="utf-8"))

    # --- Flatten structure ---
    if isinstance(data_raw, dict):
        data = []
        for k, v in data_raw.items():
            if isinstance(v, list):
                data.extend(v)
            elif isinstance(v, dict):
                data.append(v)
    else:
        data = data_raw

    grouped = {}

    for raw in data:
        # Correction ici : certains articles sont des chaînes JSON, pas des dict
        if isinstance(raw, str):
            try:
                art = ast.literal_eval(raw)
            except Exception:
                continue
        else:
            art = raw

        if not isinstance(art, dict):
            continue

        theme = classify_article(art)
        grouped.setdefault(theme, []).append(art)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(grouped, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"✅ {len(data)} articles classés par thème → {out_path}")

if __name__ == "__main__":
    main()
