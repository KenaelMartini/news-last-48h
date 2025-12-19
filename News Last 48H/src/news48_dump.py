# -*- coding: utf-8 -*-
"""
KM&CO News Collector v3.1 — Clean Institutional Edition (Oct 2025)
Collecteur RSS global, stable, sans flux morts.
"""

from __future__ import annotations
import argparse, json, logging, os, re, socket, sys, time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import feedparser, requests
from dateutil import parser as dtparser
import random

# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_OUTDIR = Path(r"D:\trading\News Last 48H\out")
DEFAULT_WINDOW_HOURS = 96
DEFAULT_MAX_PER_FEED = 200

socket.setdefaulttimeout(10)

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Chrome/125.0"
    ),
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8,fr;q=0.6",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
]


# =========================
# FLUX RSS ACTIFS — CLEAN 2025
# =========================

LIVE_FEEDS = [
    # --- Reuters (Google fallback, flux officiels obsolètes)
    "https://news.google.com/rss/search?q=site:reuters.com+markets",
    "https://news.google.com/rss/search?q=site:reuters.com+currencies",
    "https://news.google.com/rss/search?q=site:reuters.com+central+bank",

    # --- Bloomberg
    "https://news.google.com/rss/search?q=site:bloomberg.com+markets",
    "https://news.google.com/rss/search?q=site:bloomberg.com+economics",
    "https://news.google.com/rss/search?q=site:bloomberg.com+fed+ecb+boj",

    # --- Financial Times
    "https://news.google.com/rss/search?q=site:ft.com+markets",
    "https://news.google.com/rss/search?q=site:ft.com+central+banks",
    "https://news.google.com/rss/search?q=site:ft.com+foreign+exchange",

    # --- WSJ
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",

    # --- BBC
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",

    # --- Investing.com / InvestingLive
    "https://news.google.com/rss/search?q=site:investing.com+forex",
    "https://news.google.com/rss/search?q=site:investing.com+commodities",
    "https://news.google.com/rss/search?q=site:investinglive.com+markets",

    # --- Banques centrales (via Google News)
    "https://news.google.com/rss/search?q=site:ecb.europa.eu+press+release",
    "https://news.google.com/rss/search?q=site:bankofengland.co.uk+news",
    "https://news.google.com/rss/search?q=site:rba.gov.au+press+release",
    "https://news.google.com/rss/search?q=site:rbnz.govt.nz+statement",
    "https://news.google.com/rss/search?q=site:snb.ch+monetary+policy",
    "https://news.google.com/rss/search?q=site:bankofcanada.ca+press",
    "https://news.google.com/rss/search?q=site:boj.or.jp+statement",

    # --- Institutions internationales
    "https://news.google.com/rss/search?q=site:imf.org+press+release",
    "https://news.google.com/rss/search?q=site:worldbank.org+press+release",
]

# =========================
# STRUCTURES
# =========================

@dataclass
class Article:
    title: str
    url: str
    source: str
    published_utc: datetime
    summary: str = ""

    def to_json(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_utc": self.published_utc.replace(tzinfo=timezone.utc).isoformat(),
            "summary": self.summary or self.title,
        }

# =========================
# LOGGING
# =========================

def setup_logging(verbose=True):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout)

def log_warn(msg: str):
    if not any(x in msg for x in ("403", "404", "timed out")):
        logging.warning(f"⚠️  {msg}")

# =========================
# HELPERS
# =========================

def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())

def _norm_url(u: str) -> str:
    return (u or "").strip()

def _parse_date(entry: dict) -> Optional[datetime]:
    for key in ("published_parsed", "updated_parsed"):
        dt = entry.get(key)
        if dt:
            try:
                return datetime(*dt[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    raw = entry.get("published") or entry.get("updated")
    if raw:
        try:
            d = dtparser.parse(raw)
            return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None

def _safe_get(url: str, timeout=10, retries=2) -> Optional[bytes]:
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.content
            log_warn(f"{r.status_code} → {url}")
        except requests.exceptions.RequestException as e:
            log_warn(f"Network error on {url} ({e})")
        time.sleep(0.8 * (attempt + 1))
        HTTP_HEADERS["User-Agent"] = random.choice(USER_AGENTS)
        time.sleep(0.5 + 0.3 * random.random())

    return None

def parse_feed(url: str, max_items=150) -> Tuple[str, List[dict]]:
    raw = _safe_get(url)
    if not raw:
        return (url, [])
    parsed = feedparser.parse(raw)
    title = parsed.feed.get("title", url) if getattr(parsed, "feed", None) else url
    entries = getattr(parsed, "entries", []) or []
    return (title, entries[:max_items])

# =========================
# COLLECTE
# =========================

def collect_window(urls: List[str], hours: int, workers: int = DEFAULT_MAX_WORKERS) -> List[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    all_articles: List[Article] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(collect_feed, url, cutoff): url for url in urls}
        for future in as_completed(futures):
            try:
                result = future.result()
                all_articles.extend(result)
            except Exception as e:
                log_warn(f"Erreur sur {futures[future]} ({e})")

    # === Ajout ici ===
    counter = Counter(a.source for a in all_articles)
    logging.info("\n📊 Rendement par flux :")
    for src, n in sorted(counter.items(), key=lambda x: -x[1]):
        logging.info(f"{src:50} {n:4d}")
    logging.info(f"Total final : {sum(counter.values())} articles valides.")
    # === Fin ajout ===

    with open(outdir / "source_stats.txt", "w", encoding="utf-8") as f:
        for src, n in sorted(counter.items(), key=lambda x: -x[1]):
            f.write(f"{src:50} {n:4d}\n")

    return all_articles


# =========================
# EXPORT
# =========================

def save_articles_json(items: List[Article], outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    payload = {
        "report_date_iso": datetime.now().strftime("%Y-%m-%d"),
        "window_days": max(1, int(round(len(items) / 200))) if items else 2,
        "articles": [a.to_json() for a in items],
    }
    path = outdir / "articles.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logging.info(f"✅ articles.json prêt : {path}")
    return path

# =========================
# CLI
# =========================

def main():
    p = argparse.ArgumentParser(description="KM&CO RSS Collector — FX, Macro, Central Banks, Commodities")
    p.add_argument("--outdir", type=str, default=str(DEFAULT_OUTDIR), help="Dossier de sortie")
    p.add_argument("--hours", type=int, default=DEFAULT_WINDOW_HOURS, help="Fenêtre en heures")
    p.add_argument("--quiet", action="store_true", help="Logs silencieux")
    args = p.parse_args()

    setup_logging(verbose=not args.quiet)
    outdir = Path(args.outdir)

    logging.info(f"🔍 {len(LIVE_FEEDS)} flux RSS actifs chargés.")
    articles = collect_window(LIVE_FEEDS, hours=args.hours)
    logging.info(f"Total {len(articles)} articles collectés.")
    save_articles_json(articles, outdir)

if __name__ == "__main__":
    # Normalise et affiche les vrais chemins utilisés
    print("\n=== KM&CO PATH CHECK ===")
    print("Script:", __file__)
    print("Project dir:", PROJECT_DIR)
    print("Output dir:", DEFAULT_OUTDIR)
    print("Config:", DEFAULT_CONFIG)
    print("========================\n")

    main()

