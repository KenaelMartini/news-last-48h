import sys, os, re, json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

ARTICLES_PATH = r"D:\trading\News Last 48H\KMCO_out\articles.json"

def charger_articles():
    with open(ARTICLES_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return raw["articles"] if "articles" in raw else raw

def nettoyer_html(txt):
    return re.sub(r"<[^>]+>", "", txt or "").strip()

# Dictionnaire de mots-clés macro
macro_keywords = {
    "banques_centrales": ["Fed", "ECB", "BoJ", "BoE", "hike", "cut", "rate", "policy", "Lagarde", "Powell"],
    "inflation": ["inflation", "CPI", "PPI", "prices", "wage"],
    "emploi": ["jobs", "unemployment", "payrolls", "NFP", "labor"],
    "croissance": ["GDP", "growth", "PMI", "manufacturing", "services"],
    "energie": ["oil", "gas", "OPEC", "WTI", "Brent", "energy"],
    "geopolitique": ["China", "Russia", "Ukraine", "Middle East", "sanction", "conflict"],
    "devises": ["FX", "currency", "yen", "dollar", "euro"]
}

def classer_article(article):
    title = nettoyer_html(article.get("title", "")).lower()
    score = {k: 0 for k in macro_keywords}
    for topic, keywords in macro_keywords.items():
        for k in keywords:
            if k.lower() in title:
                score[topic] += 1
    best = max(score, key=score.get)
    return best if score[best] > 0 else "autres"

if __name__ == "__main__":
    arts = charger_articles()

    classes = {}
    for a in arts:
        tag = classer_article(a)
        classes.setdefault(tag, []).append(a)

    print("✅ Classement macro effectué :")
    for k, v in classes.items():
        print(f"- {k}: {len(v)} articles")
