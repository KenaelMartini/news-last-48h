# ai_core/intelligence/contextual_numbers.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from typing import List, Dict

# regex pour capter chiffres du flux
RE_PERCENT = re.compile(r"\b\d+(?:\.\d+)?\s?%")
RE_BPS = re.compile(r"\b\d{1,4}\s?bps\b", re.IGNORECASE)
RE_YIELD = re.compile(r"\b\d+(?:\.\d+)?\s?%(?:\s?yld|\s?yield)?\b", re.IGNORECASE)
RE_DOLLAR = re.compile(r"\$\s?\d+(?:\.\d+)?")

# mots-clés
KW = {
    "inflation": ["cpi","pce","inflation","core","désinflation"],
    "jobs": ["nfp","emploi","jobs","payrolls","chômage","unemployment","wage"],
    "growth": ["gdp","croissance","recession","pmi","ism","activity","activité"],
    "policy": ["fed","ecb","boj","boc","rba","rbnz","snb","rate","cut","hike","guidance","policy","taux"],
    "rates": ["ust","us10y","2y","10y","bund","btp","jgb","gilt","ois","swap","curve"],
    "fx": ["eurusd","usdjpy","gbpusd","audusd","usdchf","usdcad","nzdusd","dxy","fx","devise","currency"],
    "equities": ["sp500","s&p","nasdaq","dow","stoxx","eurostoxx","nikkei","equities","stocks","bourse"],
    "commodities": ["brent","wti","oil","pétrole","or","gold","copper","cuivre","iron ore","lng"],
    "geopolitics": ["ukraine","russia","israel","gaza","iran","taiwan","sanction","geopolit","conflit"],
    "tech": ["ai","semi","chip","nvidia","tsmc","cloud","cyber"],
    "regulation": ["regulation","policy","tariff","tarif","trade","ban","law","législation"],
    "vol": ["vix","move","volatilité","volatility"],
}

# mapping thèmes
THEME_MAP = {
    "1. Tendances macroéconomiques globales": ["inflation","growth","jobs","policy","rates","vol"],
    "2. Politique monétaire et banques centrales": ["policy","inflation","rates"],
    "3. Devises et marchés des changes": ["fx","rates","commodities","policy","vol"],
    "4. Marchés boursiers internationaux": ["equities","rates","policy","vol"],
    "5. Matières premières (énergie, métaux, etc.)": ["commodities","growth","geopolitics"],
    "6. Entreprises & résultats financiers": ["equities"],
    "7. Risques géopolitiques et diplomatie économique": ["geopolitics","commodities","fx"],
    "8. Nouveaux développements technologiques": ["tech","equities"],
    "9. Environnement réglementaire et mesures commerciales": ["regulation","policy","fx"],
    "10. Conclusions et perspectives": ["policy","rates","inflation","fx"],
    "11. Implication du Desk": ["fx","rates","vol","commodities"],
    "12. Notes internes du Desk": ["fx","rates","commodities","equities","policy"],
}

def _classify(text: str):
    t = text.lower()
    cats = [k for k,v in KW.items() if any(w in t for w in v)]
    return cats or ["misc"]

def _extract_points(text: str):
    found = set()
    for rx in (RE_PERCENT, RE_BPS, RE_DOLLAR, RE_YIELD):
        for m in rx.findall(text):
            found.add(m.strip())
    return list(found) if found else []

# ✅ Fonction manquante — maintenant elle EXISTE
def _build_datapoint_string(article: dict, tokens: List[str], cats: List[str]) -> str:
    src = article.get("source", "")
    ttl = article.get("title", "")
    tok = "; ".join(tokens)
    tag = ",".join(cats)
    return f"[{src}] {ttl} :: {tok} || tags:{tag}"

def collect_relevant_numbers(articles: List[dict], max_per_theme: int = 12) -> Dict[str, List[str]]:
    bucket: Dict[str, List[str]] = {k: [] for k in THEME_MAP.keys()}

    for a in articles:
        text = f"{a.get('title','')} {a.get('summary','')}"
        tokens = _extract_points(text)
        if not tokens:
            continue

        cats = _classify(text)
        point = _build_datapoint_string(a, tokens, cats)

        for theme, preferred in THEME_MAP.items():
            if any(c in preferred for c in cats) and len(bucket[theme]) < max_per_theme:
                bucket[theme].append(point)

    for k, v in bucket.items():
        seen = set()
        dedup = []
        for s in v:
            if s not in seen:
                dedup.append(s)
                seen.add(s)
        bucket[k] = dedup

    return bucket
