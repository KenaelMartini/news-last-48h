# -*- coding: utf-8 -*-
"""
KM&CO News Collector v2.3 — Extended version Nov 2025
Collecteur multi-flux RSS/Atom, compatible YAML, multi-threaded, optimisé Reuters/Bloomberg/CB.
"""

from __future__ import annotations
import argparse, json, logging, sys, time, re, socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import feedparser, requests, yaml
from dateutil import parser as dtparser
from collections import Counter


# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DEFAULT_OUTDIR = PROJECT_DIR / "out"
DEFAULT_WINDOW_HOURS = 240
DEFAULT_MAX_PER_FEED = 3000
DEFAULT_MAX_WORKERS = 12

socket.setdefaulttimeout(10)

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Chrome/125.0",
    "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8,fr;q=0.6",
}

# =========================
# FLUX RSS PAR DÉFAUT
# =========================

DEFAULT_FEEDS = [
    # Reuters
    "- https://news.google.com/rss/search?q=site:reuters.com+markets",
    "- https://news.google.com/rss/search?q=site:reuters.com+currencies",
    "- https://news.google.com/rss/search?q=site:reuters.com+central+bank",
    "- https://news.google.com/rss/search?q=site:reuters.com+economy",
    # Bloomberg
    "https://news.google.com/rss/search?q=site:bloomberg.com+markets",
    "https://news.google.com/rss/search?q=site:bloomberg.com+economics",
    # Financial Times
    "https://news.google.com/rss/search?q=site:ft.com+markets",
    "https://news.google.com/rss/search?q=site:ft.com+central+banks",
    # WSJ
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    # BBC
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    # InvestingLive
    "https://news.google.com/rss/search?q=site:investinglive.com+markets",
    # Banques centrales
    "https://www.ecb.europa.eu/rss/press.xml",
    "https://www.bankofengland.co.uk/news?NewsTypes=ce90163e489841e0b66d06243d35d5cb&Direction=Latest",
    "https://www.rba.gov.au/rss/rss.xml",
    "https://www.bankofcanada.ca/feeds/press-releases/",
    "https://www.snb.ch/en/rss",
    "https://www.rbnz.govt.nz/feeds/media-releases",
    # IMF / World Bank
    "https://www.imf.org/external/np/exr/feeds/rss.aspx?feed=PressReleases",
    "https://www.worldbank.org/en/news/all?format=rss",
]

# =========================
# DATACLASS
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
        time.sleep(0.7 * (attempt + 1))
    return None

def parse_feed(url: str, max_items=DEFAULT_MAX_PER_FEED) -> Tuple[str, List[dict]]:
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

def collect_feed(url: str, cutoff: datetime) -> List[Article]:
    title, entries = parse_feed(url)
    collected: List[Article] = []
    for e in entries:
        dt = _parse_date(e)
        if not dt or dt < cutoff:
            continue
        a = Article(
            title=_norm_title(e.get("title")),
            url=_norm_url(e.get("link")),
            source=title,
            published_utc=dt,
            summary=(e.get("summary") or e.get("title") or "").strip(),
        )
        if a.url:
            collected.append(a)
    logging.info(f"{title}: {len(collected)} articles valides.")
    return collected

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
# CHARGEMENT YAML
# =========================

def load_feeds_from_yaml(yaml_path: Path) -> List[str]:
    if not yaml_path.exists():
        logging.info("Aucun fichier YAML trouvé, utilisation des flux par défaut.")
        return DEFAULT_FEEDS
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    feeds = data.get("feeds") or []
    logging.info(f"{len(feeds)} flux chargés depuis YAML.")
    return feeds or DEFAULT_FEEDS

# =========================
# CLI
# =========================

def main():
    p = argparse.ArgumentParser(description="Collecteur RSS universel (Reuters, Bloomberg, FX, CB)")
    p.add_argument("--outdir", type=str, default=str(DEFAULT_OUTDIR), help="Dossier de sortie")
    p.add_argument("--hours", type=int, default=DEFAULT_WINDOW_HOURS, help="Fenêtre en heures")
    p.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS, help="Threads simultanés")
    p.add_argument("--yaml", type=str, default=str(PROJECT_DIR / "configs" / "sources.yaml"),
                   help="Chemin vers le fichier YAML de sources")
    p.add_argument("--quiet", action="store_true", help="Logs silencieux")
    args = p.parse_args()

    setup_logging(verbose=not args.quiet)
    outdir = Path(args.outdir)

    feeds = load_feeds_from_yaml(Path(args.yaml))
    logging.info(f"🔍 {len(feeds)} flux RSS actifs chargés.")
    articles = collect_window(feeds, hours=args.hours, workers=args.max_workers)
    logging.info(f"Total {len(articles)} articles collectés.")
    save_articles_json(articles, outdir)

if __name__ == "__main__":
    main()
