# ai_core/ai_overnight_core/ai_summarizer_overnight.py
# -*- coding: utf-8 -*-
"""
KM&CO – Summarizer Overnight (Asie) – format 30/10
"""

import os
from openai import OpenAI
from openai._base_client import SyncHttpxClientWrapper

current_position = "en recherche de positions" \
"<"

def summarize_articles(data):
    # Purge proxies
    for var in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"]:
        os.environ.pop(var, None)

    articles = data.get("articles", [])
    text = "\n".join(f"- {a.get('title','')}: {a.get('summary','')}" for a in articles[:40])

    quant_signal = data.get("quant_signal", "")
    datapoints_hint = data.get("datapoints_hint", "")

    prompt = f"""
Analyse ces articles macro-financiers récents et rédige un rapport institutionnel 
au format KM&CO (niveau FX & Macro Strategy Desk), intégralement en texte continu 
— sans puces, sans listes, sans séparateurs — en paragraphes complets.

Structure obligatoire :
1. Top Overnight Drivers
2. Central Banks
3. Market Snapshot (FX, Rates, Commodities)
4. FX Bias
5. Scénarios Binaires
6. Conclusion
7. Implication du desk ({current_position})

Style : froid, professionnel, analytique. Chaque section doit s’enchaîner naturellement.
Aucune numérotation ni bullet point. Pas d’intro ni d’outro hors structure.

Indications du moteur FX interne (ne pas citer explicitement, juste influencer la tonalité) :
{quant_signal}

Chiffres à intégrer dans la narration (jamais listés, uniquement dans le texte) :
{datapoints_hint}

Articles disponibles :
{text}
"""
    

    api = os.getenv("OPENAI_API_KEY")
    if not api:
        raise RuntimeError("OPENAI_API_KEY non définie")

    client = OpenAI(
        api_key=api,
        http_client=SyncHttpxClientWrapper(base_url="https://api.openai.com/v1", headers={})
    )

    resp = client.chat.completions.create(
        model="gpt-5",
        temperature=1,
        messages=[
            {"role": "system", "content": "Tu es un analyste macro de salle des marchés."},
            {"role": "user", "content": prompt}
        ]
    )

    return resp.choices[0].message.content
