import sys, os, json, re, math, html
from datetime import datetime, timezone
from collections import defaultdict, Counter
from urllib.parse import urlparse, urlunparse, urlsplit, parse_qs, unquote
from pathlib import Path

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

from models.signal import MacroSignal, MacroSignalSet
from models.kmco_save import save_json, save_table, save_log
from src.ai.cache_macro_ai import get_cached, put_cache
from src.ai.macro_tag import macro_nlp_analyze
from src.price_in.price_inference import enrich_price_inference
from src.price_in.driver_pricein import aggregate_price_in_detail, classify_driver_from_text
# en haut des imports
from src.price_in.price_inference import enrich_price_inference
from src.price_in.calibration import load_calib
from src.ai.nlp_article_scoring import score_article
from src.ai.aggregate_currency_ai import aggregate_by_currency
from src.ai.blend_quant_ai import compute_pair_conviction_and_pricein





ARTICLES_PATH = r"D:\trading\News Last 48H\KMCO_out\articles.json"
SESSION = "EU"

# =========================
# URL CLEANING HELPERS
# =========================

def _pricein_boost(pi: dict) -> float:
    resid = float(pi.get("residual_trade_value", 0.0) or 0.0)  # 0..1
    state = pi.get("pricing_state", "ambiguous")
    base = {
        "priced": 0.05,
        "partially_priced": 0.25,
        "not_priced": 0.60,
        "ambiguous": 0.15
    }.get(state, 0.15)
    boost = base + 0.8*resid
    return max(0.0, min(1.25, boost))

def _final_conviction(nlp_strength: float, pi: dict) -> float:
    calib = load_calib()
    w_nlp = float(calib.get("conv_base", 0.45))
    w_pi  = float(calib.get("conv_pricein_boost", 0.55))
    boost = _pricein_boost(pi)
    raw = w_nlp * max(0.0, min(1.0, float(nlp_strength))) + w_pi * boost
    capped = min(1.0, raw)
    return max(0.25, round(capped, 2))



def strip_tracking(u: str) -> str:
    try:
        p = urlparse(u)
        q = parse_qs(p.query, keep_blank_values=False)
        for k in list(q.keys()):
            if k.startswith("utm_") or k in {"oc", "ved", "sei", "gws_rd"}:
                q.pop(k, None)
        new_query = "&".join(f"{k}={v[0]}" for k, v in q.items() if v)
        return urlunparse(p._replace(query=new_query, fragment=""))
    except Exception:
        return u

def extract_href_from_summary(summary_html: str) -> str | None:
    if not summary_html:
        return None
    try:
        m = re.search(r'href="([^"]+)"', summary_html)
        if not m:
            return None
        return strip_tracking(unquote(html.unescape(m.group(1))))
    except Exception:
        return None

def resolve_google_news_url(u: str) -> str:
    try:
        sp = urlsplit(u)
        q = parse_qs(sp.query)
        if "url" in q and q["url"]:
            return strip_tracking(unquote(q["url"][0]))
    except Exception:
        pass
    return strip_tracking(u)

def best_article_url(a: dict) -> str:
    href = extract_href_from_summary(a.get("summary", ""))
    if href:
        return href
    u = a.get("url", "")
    if not u:
        return ""
    return resolve_google_news_url(u)

def canonical_url(u: str) -> str:
    try:
        p = urlparse(u)
        host = p.netloc.lower()
        return urlunparse(p._replace(netloc=host, query="", fragment=""))
    except Exception:
        return u

def dedup_urls(urls, max_n=5):
    seen = set()
    out = []
    for u in urls:
        if not u:
            continue
        c = canonical_url(u)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) >= max_n:
            break
    return out

# =========================
# TAXONOMIE & HEURISTIQUES
# =========================
HIGH_QUALITY = {"Reuters","Bloomberg","ECB","Federal Reserve","Bank of England","BoJ","BoC","RBA","RBNZ","SNB"}
TOPIC_WEIGHT = {
    "banques_centrales":1.0,"inflation":0.9,"croissance":0.8,"emploi":0.8,
    "energie":0.6,"geopolitique":0.5,"devises":0.6
}

SOURCE_WEIGHTS = {
    "reuters": 1.00,
    "bloomberg": 1.00,
    "financial times": 0.95,
    "ft": 0.95,
    "wall street journal": 0.95,
    "wsj": 0.95,
    "nikkei": 0.85,
    "cnbc": 0.60,
    "marketwatch": 0.55,
    "yahoo finance": 0.50,
    "google news": 0.45,
    "unknown": 0.40
}

TOPIC_DICT = {
    "banques_centrales":["fed","ecb","boj","boe","hike","cut","rate","policy","lagarde","powell","ycc","qe","qt"],
    "inflation":["inflation","cpi","ppi","core","prices","wage"],
    "emploi":["jobs","unemployment","payrolls","nfp","labor"],
    "croissance":["gdp","growth","pmi","manufacturing","services","ism"],
    "energie":["oil","gas","opec","wti","brent","energy"],
    "geopolitique":["china","russia","ukraine","middle east","sanction","conflict","war"],
    "devises":["fx","currency","yen","dollar","euro","sterling","franc","aussie","kiwi","cad"]
}

DIR_RULES = [
    (r"\bhawkish\b|\brate hike\b|\braises rates\b|\bkeeps rates high\b", {"USD":+1,"EUR":+1,"GBP":+1,"CHF":+1,"CAD":+1,"AUD":+1,"NZD":+1}),
    (r"\bdovish\b|\brate cut\b|\bcut rates\b|\badds QE\b", {"USD":-1,"EUR":-1,"GBP":-1,"CHF":-1,"CAD":-1,"AUD":-1,"NZD":-1}),
    (r"\bmanufacturing (contracts|slows|weak)\b|\bPMI < ?50\b|\bISM (below|<) 50\b", {"USD":-1,"EUR":-1,"GBP":-1,"AUD":-1,"NZD":-1}),
    (r"\bISM Services (> ?52|expands)\b|\bPMI (> ?50)\b", {"USD":+1,"EUR":+1,"GBP":+1,"AUD":+1,"NZD":+1}),
    (r"\brisk-off\b|\bflight to safety\b|\bmarket selloff\b", {"USD":+1,"JPY":+1,"CHF":+1,"AUD":-1,"NZD":-1})
]

CURRENCY_MAP = {
    "usd":["us","u.s.","dollar","federal reserve","powell","ism","nfp"],
    "eur":["euro","ecb","lagarde","euro area","germany","france","italy","spain"],
    "gbp":["sterling","boe","bank of england","uk","britain"],
    "jpy":["yen","boj","japan"],
    "chf":["franc","snb","swiss"],
    "cad":["canada","boc","loonie"],
    "aud":["australia","rba","aussie"],
    "nzd":["new zealand","rbnz","kiwi"]
}

PAIR_UNIVERSE = [
    "EURUSD","GBPUSD","AUDUSD","NZDUSD","USDCAD","USDCHF","USDJPY",
    "EURGBP","EURAUD","AUDJPY","NZDJPY","CHFJPY","CADJPY"
]

CURRENCY_KEYS = {
    "USD": ["usd","u.s.","dollar","federal reserve","powell","treasury","ism","nfp","us "],
    "EUR": ["eur","euro","ecb","lagarde","euro area","germany","france","italy","spain","bundesbank"],
    "GBP": ["gbp","sterling","boe","bank of england","uk","britain","sunak","hunt"],
    "JPY": ["jpy","yen","boj","bank of japan","kuroda","ueda","ycc","japan"],
    "CHF": ["chf","franc","snb","swiss","jordan","switzerland"],
    "CAD": ["cad","loonie","boc","bank of canada","macklem","canada"],
    "AUD": ["aud","aussie","rba","australia"],
    "NZD": ["nzd","kiwi","rbnz","new zealand"],
}

MAX_AI_CALLS_PER_RUN = 40

# =========================
# UTILITAIRES TEXTE & SCORING
# =========================
def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

def article_text(a):
    return f"{strip_html(a.get('title',''))}. {strip_html(a.get('summary',''))}".lower()

def source_quality(src: str) -> float:
    if not src:
        return SOURCE_WEIGHTS["unknown"]
    s = src.lower()
    for key, weight in SOURCE_WEIGHTS.items():
        if key in s:
            return weight
    return SOURCE_WEIGHTS["unknown"]

def topic_tags(text):
    t = text.lower()
    cnt = {k:0 for k in TOPIC_DICT}
    for topic,kws in TOPIC_DICT.items():
        for kw in kws:
            if kw in t: cnt[topic] += 1
    return cnt

def time_decay(published):
    try:
        dt = datetime.fromisoformat(published.replace("Z","+00:00"))
        hours = (datetime.now(timezone.utc)-dt).total_seconds()/3600
        return math.exp(-hours/48)
    except Exception:
        return 0.6

def directional_votes(text):
    votes = Counter(); t = text.lower()
    for pat,eff in DIR_RULES:
        if re.search(pat,t):
            for cc,val in eff.items():
                votes[cc] += val
    for cc,kws in CURRENCY_MAP.items():
        if any(kw in t for kw in kws):
            votes[cc.upper()] += 0.1
    return votes

# =========================
# AI defaults
# =========================
def default_ai_blob(quota: bool=False) -> dict:
    return {
        "hawk_dove": 0,
        "inflation_vs_growth": 0,
        "risk_sentiment": 0,
        "fx_direction": {},
        "macro_relevance": 0.3 if not quota else 0.2,
        "novelty": 0.0,
        "forward_significance": 0.0,
        "comment": "ai_error" if not quota else "ai_skipped_quota"
    }

# =========================
# BUCKETS
# =========================
def load_articles():
    path = Path("KMCO_out/articles.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["articles"]

def bucket_by_currency(articles):
    buckets = {cc:[] for cc in CURRENCY_KEYS}
    for a in articles:
        t = article_text(a)
        for cc,kws in CURRENCY_KEYS.items():
            if any(kw in t for kw in kws):
                buckets[cc].append(a)
    return buckets

def score_currency_bucket(cc, arts):
    if not arts:
        return {
            "cc": cc, "n": 0,
            "avg_quality": 0.0, "avg_decay": 0.0,
            "topic_mix": {}, "topic_weight": 0.0,
            "votes": Counter(), "top_urls": [], "items": []
        }


    items = []
    ai_cache = {}
    ai_calls = 0
    MAX_AI_CALLS = 50

    for a in arts:
        t = article_text(a)

        # IA tags
        ai_blob = get_cached(t, ai_cache)
        if ai_blob is None and ai_calls < MAX_AI_CALLS:
            try:
                ai_blob = macro_nlp_analyze(t)
                put_cache(t, ai_blob)
                ai_calls += 1
            except Exception:
                ai_blob = default_ai_blob()
        elif ai_blob is None:
            ai_blob = default_ai_blob(quota=True)

        # Price-in simple
                # Price-in simple
        try:
            price_in = enrich_price_inference(ai_blob)
        except Exception:
            price_in = {
                "surprise_dir": "neutral",
                "market_agreement": 0.0,
                "pricing_state": "ambiguous",
                "residual_trade_value": 0.0
            }

        # Driver tags par texte simple
        try:
            driver_tags = classify_driver_from_text(t)
        except Exception:
            driver_tags = {"misc": True}

        items.append({
            "text": t,
            "q": source_quality(a.get("source", "")),
            "decay": time_decay(a.get("published_utc", "")),
            "topics": topic_tags(t),
            "url": best_article_url(a),
            "macro_ai": ai_blob,
            "price_in": price_in,
            "driver_tags": driver_tags
        })

        # Debug PI only when meaningful
        # Debug PI only when meaningful
        try:
            if price_in.get("pricing_state") not in ("no_signal", "ambiguous"):
                print(f"[PI] {cc}: {price_in}")
        except Exception:
            pass



    avg_quality = sum(x["q"] for x in items) / len(items)
    avg_decay = sum(x["decay"] for x in items) / len(items)

    topic_sum = Counter()
    for x in items:
        for k, v in x["topics"].items():
            topic_sum[k] += v

    total = sum(topic_sum.values()) or 1
    topic_mix = {k: topic_sum[k] / total for k in topic_sum}
    topic_weight = sum(topic_mix.get(k,0)*TOPIC_WEIGHT.get(k,0.5) for k in TOPIC_WEIGHT)

    residual_vals = [x["price_in"]["residual_trade_value"] for x in items]
    if residual_vals:
        topic_weight += 0.05 * (sum(residual_vals)/len(residual_vals))

    votes = directional_votes(". ".join(x["text"] for x in items[:600]))
    top_src = sorted(items, key=lambda x: x["q"] * x["decay"], reverse=True)[:8]
    urls = [x["url"] for x in top_src if x["url"]]

    return {
        "cc": cc, "n": len(items),
        "avg_quality": avg_quality,
        "avg_decay": avg_decay,
        "topic_mix": topic_mix,
        "topic_weight": topic_weight,
        "votes": votes,
        "top_urls": urls,
        "items": items
    }

# ---- suivi des articles utilisés par paire
pair_article_buckets = {}



def is_relevant_for_pair(txt, base, quote):
    keys = CURRENCY_KEYS
    return any(kw in txt for kw in keys[base]+keys[quote])

def top_sources_for_pair(base, quote, cur, n_each=4, max_total=5):
    items_b = cur[base]["items"]
    items_q = cur[quote]["items"]

    scored = []
    for it in items_b + items_q:
        t = it["text"]
        if is_relevant_for_pair(t, base, quote):
            u = strip_tracking(resolve_google_news_url(it["url"]))
            scored.append((u, it["q"]*it["decay"]))

    scored.sort(key=lambda x:x[1], reverse=True)
    urls = [u for u,_ in scored][:max_total]
    return dedup_urls(urls, max_n=max_total)

def pair_from_votes(pair, cur):
    base, quote = pair[:3], pair[3:]
    v = Counter({k.upper():cur[base]["votes"][k] for k in cur[base]["votes"]})
    u = Counter({k.upper():cur[quote]["votes"][k] for k in cur[quote]["votes"]})
    strength = (v.get(base,0)-v.get("USD",0)) - (u.get(quote,0)-u.get("USD",0))
    if abs(strength) < 0.15:
        return pair, "Flat", 0.0
    return pair, ("Long" if strength>0 else "Short"), abs(strength)

def aggregate_price_in(items_base, items_quote):
    vals = []
    for it in (items_base + items_quote):
        pi = it.get("price_in", {})
        vals.append({
            "ma": pi.get("market_agreement", 0),
            "resid": pi.get("residual_trade_value", 0),
            "state": pi.get("pricing_state", "ambiguous")
        })

    if not vals:
        return {
            "pricing_state":"ambiguous",
            "avg_market_agreement":0.0,
            "avg_residual_trade_value":0.0,
            "conviction_boost":0.0
        }

    # protect against None values
    ma_vals = [v.get("ma") for v in vals if isinstance(v.get("ma"), (int, float))]
    resid_vals = [v.get("resid") for v in vals if isinstance(v.get("resid"), (int, float))]
    avg_ma = sum(ma_vals)/len(ma_vals) if ma_vals else 0.0
    avg_resid = sum(resid_vals)/len(resid_vals) if resid_vals else 0.0
    states = [v.get("state") for v in vals if v.get("state")]
    pricing_state = max(set(states), key=states.count)

    conviction_boost = 0.0
    if avg_resid > 0.35 and avg_ma < 0.45:
        conviction_boost = round(min(0.25, avg_resid * (1-avg_ma)),3)

    return {
        "pricing_state": pricing_state,
        "avg_market_agreement": round(avg_ma,3),
        "avg_residual_trade_value": round(avg_resid,3),
        "conviction_boost": conviction_boost
    }

# =========================
# CORE
# =========================
def build_signals(max_signals=5, min_bucket=8):
    # === LOAD & BUCKET ===
    arts = load_articles()
    buckets = bucket_by_currency(arts)
    cur = {cc: score_currency_bucket(cc, lst) for cc, lst in buckets.items()}

    # === ADAPTIVE FILTER ===
    total = len(arts)
    if total < 400:
        min_bucket = max(6, min_bucket)
    elif total < 200:
        min_bucket = 4

    # === RANK FX PAIRS ===
    pairs = []
    for p in PAIR_UNIVERSE:
        base, quote = p[:3], p[3:]
        if cur[base]["n"] < min_bucket or cur[quote]["n"] < min_bucket:
            continue

        pair, direction, strength = pair_from_votes(p, cur)
        if direction == "Flat":
            continue

        avg_q = (cur[base]["avg_quality"] + cur[quote]["avg_quality"]) / 2
        avg_d = (cur[base]["avg_decay"]   + cur[quote]["avg_decay"])   / 2
        tw    = (cur[base]["topic_weight"]+ cur[quote]["topic_weight"])/ 2
        score = (0.40*avg_q + 0.20*avg_d + 0.25*tw + 0.15*min(strength/2,1))*100
        pairs.append((p, direction, strength, score))

    if not pairs:
        return [], {}

    # === KEEP BEST PAIRS (avoid overlap) ===
    pairs.sort(key=lambda x: x[3], reverse=True)
    per_cc = Counter()
    keep = []
    for p, d, st, sc in pairs:
        b, q = p[:3], p[3:]
        if per_cc[b] >= 2 or per_cc[q] >= 2:
            continue
        keep.append((p, d, st, sc))
        per_cc[b] += 1
        per_cc[q] += 1
        if len(keep) >= max_signals:
            break

    global pair_article_buckets
    pair_article_buckets = {}
    signals = []
    price_in_details_store = {}

    print(f"[IA scoring] cur articles total =", sum(len(v['items']) for v in cur.values()))

    # === IA SCORING PHASE ===
    MAX_AI_ARTICLES = 20
    scored_articles = []
    seen = 0

    for cc, data in cur.items():
        for art in data["items"]:
            if seen >= MAX_AI_ARTICLES:
                break

            text = art.get("text", "").strip()
            if not text:
                continue

            meta = {
                "ccys": art.get("ccys") or [],
                "source_quality": float(art.get("source_quality", 0.7)),
                "published_at": art.get("published_at"),
                "url": art.get("url"),
            }

            rec = score_article(text, meta)
            scored_articles.append(rec)
            seen += 1

        if seen >= MAX_AI_ARTICLES:
            break

    ai_by_ccy = aggregate_by_currency(scored_articles)

    # === BUILD SIGNALS ===
    for p, d, st, sc in keep:
        base, quote = p[:3], p[3:]

        # --- Macro Drivers ---
        mix = Counter(cur[base]["topic_mix"]); mix.update(cur[quote]["topic_mix"])
        top_topics = [k for k, _ in mix.most_common(3)]

        drivers = []
        if "banques_centrales" in top_topics: drivers.append("CB guidance différenciée")
        if "inflation" in top_topics:         drivers.append("Inflation/Real-yields divergence")
        if "croissance" in top_topics:        drivers.append("Growth/PMI divergence")
        if "energie" in top_topics:           drivers.append("Energy-linked divergence")
        if not drivers:                       drivers.append("Directional signal")

        triggers = []
        if "USD" in p: triggers += ["ISM", "NFP", "Fedspeak"]
        if "EUR" in p: triggers += ["EZ CPI", "ECB speakers"]
        if "GBP" in p: triggers += ["UK CPI", "BoE speakers"]
        if "JPY" in p: triggers += ["BoJ/YCC", "MoF intervention risk"]
        if "CHF" in p: triggers += ["SNB comms", "Risk-off"]
        if "CAD" in p: triggers += ["BoC", "Oil"]
        if "AUD" in p: triggers += ["RBA", "China PMIs"]
        if "NZD" in p: triggers += ["RBNZ", "Dairy/ToT"]

        urls = top_sources_for_pair(base, quote, cur, n_each=4, max_total=5)
        if not urls:
            urls = dedup_urls(cur[base]["top_urls"] + cur[quote]["top_urls"], max_n=5)

        # --- IA Macro Layer ---
        base_ai  = ai_by_ccy.get(base, {})
        quote_ai = ai_by_ccy.get(quote, {})

        base_fx_score  = float(base_ai.get("ai_sign", 0.0)) * float(base_ai.get("ai_strength", 0.0))
        quote_fx_score = float(quote_ai.get("ai_sign", 0.0)) * float(quote_ai.get("ai_strength", 0.0))

        # --- Price-in Layer ---
        price_in_meta = aggregate_price_in(cur[base]["items"], cur[quote]["items"])
        pi_avg_ma     = float(price_in_meta.get("avg_market_agreement", 0.0))
        pi_avg_resid  = float(price_in_meta.get("avg_residual_trade_value", 0.0))
        price_in_state = price_in_meta.get("pricing_state", "ambiguous")

        # --- Conviction (AI Blend) ---
        res = compute_pair_conviction_and_pricein(
            base_fx_score,
            quote_fx_score,
            price_in_state,
            pi_avg_ma,
            pi_avg_resid
        )

        final_conviction = res["conviction"]
        price_in_meta["conviction_boost"] = res["conviction_boost"]

        # --- Build Signal ---
        sig = MacroSignal(
            asset=p,
            direction=d,
            conviction=round(final_conviction, 2),
            score=round(sc, 1),
            drivers=drivers,
            triggers=triggers,
            risk_to_view="Opposite CB pivot/data",
            horizon="2-5 jours",
            sources=urls,
            meta={
                "topic_mix": dict(mix),
                "articles_used": cur[base]["n"] + cur[quote]["n"],
                "time_weight": round((cur[base]["avg_decay"] + cur[quote]["avg_decay"]) / 2, 3),
                "source_quality": round((cur[base]["avg_quality"] + cur[quote]["avg_quality"]) / 2, 3),
                "price_in": pi_avg_resid,
                "pi_avg_ma": pi_avg_ma,
                "pi_avg_resid": pi_avg_resid,
                "pi_boost": price_in_meta["conviction_boost"],
            },
            price_in_state=price_in_state
        )

        signals.append(sig)
        price_in_details_store[p] = price_in_meta

    print(f"[DEBUG AI] {p}: base={base_fx_score:.3f}, quote={quote_fx_score:.3f}, pi_ma={pi_avg_ma:.3f}, pi_resid={pi_avg_resid:.3f}")


    return signals, price_in_details_store
