# -*- coding: utf-8 -*-
"""
KM&CO – Summarizer Global Check
"""

import os
from openai import OpenAI
from openai._base_client import SyncHttpxClientWrapper

current_position = "en recherche de positions"

def summarize_articles(data):
    # Nettoyage proxy
    for var in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy"]:
        os.environ.pop(var, None)

    articles = data.get("articles", [])
    text = "\n".join(f"- {a.get('title','')}: {a.get('summary','')}" for a in articles[:60])

    quant_signal = data.get("quant_signal", "")
    datapoints_hint = data.get("datapoints_hint", "")

    prompt = f"""
Analyse ces articles macro-financiers récents et rédige un rapport institutionnel
au format KM&CO (niveau FX & Macro Strategy Desk), intégralement en texte continu.

Structure obligatoire :
1. Drivers des 24 dernières heures
2. Central Banks
3. Market Snapshot (FX, Rates, Commodities)
4. FX Bias
5. Scénarios Binaires
6. Conclusion
7. Implication du desk ({current_position})

Style : froid, analytique, structuré. Aucun bullet point, aucune numérotation.
Intègre naturellement les signaux et chiffres ci-dessous sans citation explicite.

Signaux quant :
{quant_signal}

Chiffres à intégrer :
{datapoints_hint}

Articles disponibles :
{text}
"""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("⚠️ OPENAI_API_KEY non défini")

    clean_client = SyncHttpxClientWrapper(base_url="https://api.openai.com/v1", headers={})
    client = OpenAI(api_key=api_key, http_client=clean_client)

    resp = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": "Tu es un analyste macro institutionnel."},
            {"role": "user", "content": prompt}
        ]
    )

    return resp.choices[0].message.content
