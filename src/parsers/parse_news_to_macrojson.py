import sys, os, json
from datetime import datetime

# Permet d'importer le dossier parent (où se trouve models/)
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Chemin du fichier avec les news scrapées
ARTICLES_PATH = r"D:\trading\News Last 48H\KMCO_out\articles.json"

def charger_articles(path=ARTICLES_PATH):
    """Charge les articles depuis le fichier JSON et retourne la liste 'articles'."""

    with open(path, "r", encoding="utf-8") as f:
        brut = json.load(f)

    # Ton fichier a la forme :
    # { "report_date_iso": "...", "window_days": X, "articles": [ ... ] }
    if "articles" in brut:
        return brut["articles"]

    # Backup si un jour tu exportes une liste brute
    if isinstance(brut, list):
        return brut

    raise ValueError("❌ Format JSON inattendu : impossible de trouver la clé 'articles'.")

# ---- Exécution ----

articles = charger_articles()

print(f"✅ Nombre d'articles chargés : {len(articles)}")

# Affiche les 3 premiers pour contrôle visuel
for item in articles[:3]:
    print("\n--- Aperçu article ---")
    print(f"Titre     : {item.get('title')}")
    print(f"Source    : {item.get('source')}")
    print(f"Date UTC  : {item.get('published_utc')}")
    print(f"Résumé    : {item.get('summary')[:200] if item.get('summary') else 'Aucun résumé'}")
