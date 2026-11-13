# -*- coding: utf-8 -*-
"""
ai_analysis.py — KM&CO Global Macro Desk
v5 — Narrative + Quant Intelligence Layer (centralisée) + FX bias inline + Chiffres intégrés
"""

from __future__ import annotations
import json, os, sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from openai import OpenAI


# ========= KMCO QUANT BRIDGE =========
from ai_core.intelligence.quant_bridge import quant_from_articles
from ai_core.intelligence.contextual_numbers import collect_relevant_numbers

# ======================================================
# CONFIG
# ======================================================

# OpenAI credentials must come from an environment variable; never commit a token.
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Ensure project dir in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

ARTICLES_PATH = Path(r"D:\trading\News Last 48H\KMCO_out\articles.json")
OUT_PATH = Path(r"D:\trading\News Last 48H\out\KMCO_Global_Macro_AI_Report.txt")

MAX_PER_THEME = 200
MODEL = "gpt-5"
current_position = "En recherche de position"

# ======================================================
# LOAD / CLASSIFY NEWS
# ======================================================

def load_articles(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    data = json.load(open(path, encoding="utf-8"))
    return data.get("articles", [])

def classify_articles(articles: list[dict]) -> dict[str, list[str]]:
    themes = defaultdict(list)
    leftovers = []

    for a in articles:
        text = f"{a.get('title','')} {a.get('summary','')}".lower()
        line = f"- {a.get('title','').strip()} ({a.get('source','')})"

        if any(k in text for k in ["fed","powell","ecb","boj","boc","rba","rbnz","central bank","monetary policy"]):
            themes["2. Politique monétaire et banques centrales"].append(line)
        elif any(k in text for k in ["inflation","cpi","pmi","jobs","gdp","macro"]):
            themes["1. Tendances macroéconomiques globales"].append(line)
        elif any(k in text for k in ["eur","usd","gbp","jpy","cad","chf","aud","nzd","forex","fx"]):
            themes["3. Devises et marchés des changes"].append(line)
        elif any(k in text for k in ["stocks","sp500","nasdaq","equities"]):
            themes["4. Marchés boursiers internationaux"].append(line)
        elif any(k in text for k in ["oil","gas","brent","wti","gold","commodity"]):
            themes["5. Matières premières (énergie, métaux, etc.)"].append(line)
        elif any(k in text for k in ["earnings","profit","revenue"]):
            themes["6. Entreprises & résultats financiers"].append(line)
        elif any(k in text for k in ["ukraine","china","israel","geopolit"]):
            themes["7. Risques géopolitiques et diplomatie économique"].append(line)
        elif any(k in text for k in ["tech","semi","chip","ai","cloud"]):
            themes["8. Nouveaux développements technologiques"].append(line)
        elif any(k in text for k in ["regulation","tariff","trade"]):
            themes["9. Environnement réglementaire et mesures commerciales"].append(line)
        elif any(k in text for k in ["forecast","outlook","perspective"]):
            themes["10. Conclusions et perspectives"].append(line)
        else:
            leftovers.append(line)

    if leftovers:
        themes["10. Conclusions et perspectives"].extend(leftovers[:15])
        themes["12. Notes internes du Desk"].extend(leftovers[15:150])

    return {k: v[:MAX_PER_THEME] for k, v in themes.items()}

# ======================================================
# LLM
# ======================================================

def ask_ai(theme, articles, previous_sections="", datapoints=None):
    joined = "\n".join(articles)
    count = len(articles)
    dp_text = "\n".join(datapoints or [])

    prompt = f"""
Tu es analyste macro/FX institutionnel (desk sell-side).
Texte pur, froid, professionnel. Zéro puce, zéro liste, zéro tableau.

Règles :
- N'utiliser QUE les chiffres ci-dessous (provenant des news)
- Les fondre dans le narratif, jamais de façon détachée
- Si aucun chiffre pertinent: analyse macro pure (pas d’invention)

Datapoints (si pertinents) :
{dp_text}

Articles ({count}) :
{joined}

Contexte précédent :
{previous_sections}

Rédige la section "{theme}".
"""

    prompt += """

### Decision Layer (KM&CO Framework)

Sur la base de l'analyse macroéconomique ci-dessus, remplis le tableau suivant en te fondant sur les facteurs majeurs identifiés :

| Module | Statut | Commentaire |
|:--|:--|:--|
| Macro Bias | OK / NEUTRE / KO | cohérence macro du biais principal |
| Sentiment | OK / NEUTRE / KO | niveau de risk-on/off ou appétit pour le risque |
| Positioning | OK / NEUTRE / KO | positioning des investisseurs (CFTC, options, flows) |
| Timing | OK / NEUTRE / KO | degré de pricing déjà effectué ou non |
| Technical Setup | OK / NEUTRE / KO | structure technique et ratio RR ≥ 2.5 |

Règles de décision :
- 3 ou plus "OK" → Trade actionable
- 2 "OK" → Surveillance
- 1 ou 0 "OK" → Pas d’action

Détaille ensuite brièvement la justification de la décision finale, sous forme :
**Décision : [TRADE_ACTIONABLE / SURVEILLANCE / NO_TRADE]**
"""


    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "Institutional FX & Macro desk. Cold tone. No bullets."},
            {"role": "user", "content": prompt},
        ],
    )
    return completion.choices[0].message.content.strip() + "\n"



# ======================================================
# MAIN
# ======================================================

def generate_report():
    articles = load_articles(ARTICLES_PATH)
    print(f"[{datetime.now():%H:%M:%S}] {len(articles)} articles chargés.")

    quant = quant_from_articles(articles)
    quant_block = quant["text_block"]

    themes = classify_articles(articles)
    intro_text = ask_intro(len(articles))
    numbers_by_theme = collect_relevant_numbers(articles)

    report = [
        f"Analyse Globale du Marché – {datetime.now():%d %B %Y}",
        "",
        intro_text,
        ""
    ]


    ordered = [
        "1. Tendances macroéconomiques globales",
        "2. Politique monétaire et banques centrales",
        "3. Devises et marchés des changes",
        "4. Marchés boursiers internationaux",
        "5. Matières premières (énergie, métaux, etc.)",
        "6. Entreprises & résultats financiers",
        "7. Risques géopolitiques et diplomatie économique",
        "8. Nouveaux développements technologiques",
        "9. Environnement réglementaire et mesures commerciales",
        "10. Conclusions et perspectives",
        f"11. Implication du Desk ({current_position})",
        "12. Notes internes du Desk"
    ]

    prev = ""
    for sec in ordered:
        arts = themes.get(sec, [])
        dps = numbers_by_theme.get(sec, [])
        print(f"→ {sec}: {len(arts)} news | {len(dps)} datapoints")
        txt = ask_ai(sec, arts, prev, dps)
        report.append(txt)
        report.append("\n")
        prev += txt

    OUT_PATH.write_text("\n".join(report), encoding="utf-8")
    print(f"✅ Rapport complet généré → {OUT_PATH}")

if __name__ == "__main__":
    generate_report()
