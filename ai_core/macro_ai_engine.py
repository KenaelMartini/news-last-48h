# -*- coding: utf-8 -*-
"""
KM&CO Macro AI Engine – Version institutionnelle complète (V3)
Auteur : Kénael MARTINI & Co. | FX & Macro Strategy Desk
Objectif : Génération d'analyses fondamentales par section via IA.
"""

import os
import json
import textwrap
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


# =====================================================================
# 1. INITIALISATION CLIENT OPENAI
# =====================================================================
load_dotenv()  # charge les variables du .env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =====================================================================
# 2. PROMPTS INSTITUTIONNELS PAR THÈME
# =====================================================================
PROMPTS = {
    "Politique monétaire": """
    Tu es stratégiste macroéconomique senior au FX & Macro Strategy Desk de KÉNAEL MARTINI & CO.
    Rédige une analyse institutionnelle complète sur les politiques monétaires globales (Fed, ECB, BoE, BoJ, etc.).
    Structure exigée :
    1. Contexte macro récent et dynamique de l’inflation
    2. Positionnement des banques centrales et différentiel de taux
    3. Transmission monétaire et effets sur la liquidité
    4. Implications marchés (FX, taux, actions)
    5. Conclusion factuelle et neutre
    """,

    "Macroéconomie globale": """
    Tu es stratégiste macro senior.
    Rédige une analyse de la conjoncture mondiale à partir des données et articles récents.
    Structure :
    1. Contexte macro global (croissance, emploi, demande)
    2. Signaux de ralentissement ou de résilience économique
    3. Corrélations interrégionales (US, Europe, Chine)
    4. Implications pour les marchés globaux et les devises
    """,

    "Devises": """
    Tu es stratégiste FX au sein du Desk KM&CO.
    Fais une synthèse des dynamiques de change mondiales.
    Structure :
    1. Facteurs dominants (taux réels, spreads, flux risk-on/off)
    2. Mouvements récents sur USD, EUR, JPY, GBP, CHF
    3. Corrélation avec les taux et matières premières
    4. Perspectives court terme (3–5 jours)
    """,

    "Marchés boursiers": """
    Analyse institutionnelle sur les marchés actions.
    Structure :
    1. Sentiment général du marché et facteurs de risque
    2. Performances sectorielles clés
    3. Impact des publications de résultats
    4. Corrélations avec la politique monétaire et la volatilité
    """,

    "Matières premières": """
    Analyse institutionnelle sur les marchés de l’énergie et des métaux.
    Structure :
    1. Facteurs d’offre et de demande
    2. Effets géopolitiques et logistiques
    3. Corrélations avec le dollar et les taux réels
    4. Lecture institutionnelle des flux de matières premières
    """,

    "Risques géopolitiques": """
    Analyse factuelle des tensions et équilibres géopolitiques récents.
    Structure :
    1. Conflits, sanctions, relations bilatérales
    2. Risques commerciaux et énergétiques
    3. Effets macro et marché à court terme
    4. Positionnement prudentiel attendu
    """,

    "Technologies / Réglementation": """
    Analyse institutionnelle sur la technologie, les régulations et l’innovation.
    Structure :
    1. Évolutions réglementaires (États-Unis, Europe, Asie)
    2. Innovations clés (IA, chips, transition énergétique)
    3. Impacts macro et sur les marchés
    4. Lecture stratégique pour investisseurs institutionnels
    """,

    "Autres": """
    Analyse synthétique neutre sur les événements macro et financiers divers.
    Structure :
    1. Contexte général
    2. Événements récents
    3. Implications macro modérées
    """
}


# =====================================================================
# 3. FONCTION D’APPEL IA
# =====================================================================
def call_model(prompt, model="gpt-5", max_tokens=1800):
    """Appel au modèle OpenAI GPT pour la génération de texte complet."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un stratégiste macro institutionnel du FX & Macro Strategy Desk de KÉNAEL MARTINI & CO. "
                    "Rédige toujours des analyses longues, claires et factuelles. "
                    "Utilise un ton analytique, sans puces, ni listes."
                )
            },
            {"role": "user", "content": prompt.strip()}
        ],
        max_completion_tokens=max_tokens,
        response_format={"type": "text"},
        temperature=1
    )

    content = response.choices[0].message.content
    if not content or not content.strip():
        content = "[Aucune réponse générée]"
    return content.strip()

# =====================================================================
# 4. GÉNÉRATION DE CHAQUE SECTION
# =====================================================================
def generate_ai_analysis(theme, articles, mode="global"):
    # Limite les articles à 15 pour éviter surcharge
    titles = [a.get("title", "").strip() for a in articles[:15] if a.get("title")]
    context = " | ".join(titles)

    base_prompt = PROMPTS.get(theme, PROMPTS["Autres"])

    prompt = textwrap.dedent(f"""
        {base_prompt.strip()}

        Mode : {mode.upper()}
        Articles récents (extraits de presse) :
        {context}

        Écris une analyse macroéconomique institutionnelle complète de minimum 400 mots.
        Ton froid, analytique, aucun style journalistique.
    """)


    print(f"🧠 Génération IA pour {theme} ({len(articles)} articles, mode {mode})...")
    analysis_text = call_model(prompt)

    # Sécurité : si la réponse est vide
    if not analysis_text.strip():
        analysis_text = f"[Aucune réponse générée pour {theme}]"

    print(f"✅ Section {theme} générée ({len(analysis_text.split())} mots).")
    return analysis_text



# =====================================================================
# 5. PIPELINE GLOBAL
# =====================================================================
def generate_fundamental_analysis(grouped_path, mode="global"):
    grouped = json.load(open(grouped_path, encoding="utf-8"))
    output = {}

    for theme, articles in grouped.items():
        if not articles:
            continue
        try:
            output[theme] = generate_ai_analysis(theme, articles, mode)
        except Exception as e:
            print(f"⚠️ Erreur sur {theme}: {e}")
            output[theme] = f"[Erreur IA] {str(e)}"

    date = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = Path(f"D:\\trading\\News Last 48H\\KMCO_out\\analysis_texts_{mode}_{date}.json")
    json.dump(output, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\n✅ Rapport IA complet généré → {out_path}\n")


# =====================================================================
# 6. EXECUTION PRINCIPALE
# =====================================================================
def main():
    grouped_path = Path(r"D:\trading\News Last 48H\KMCO_out\articles_grouped.json")
    generate_fundamental_analysis(grouped_path, mode="global")

if __name__ == "__main__":
    main()
