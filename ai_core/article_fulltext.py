# -*- coding: utf-8 -*-
r"""
KM&CO Fulltext Extractor v2.2
Pipeline principal :
 - lit D:\trading\News Last 48H\out\articles.json
 - tente extraction via requests (headers réalistes)
 - si page bloquée / contenu absent -> fallback Playwright (browser_extract.browser_extract)
 - sauvegarde D:\trading\News Last 48H\KMCO_out\articles_full.json
Chaque enregistrement contient un champ "_extraction" avec method/status/final_url.
"""

import os
import json
import time
import random
import re
from pathlib import Path
from html import unescape
from typing import Tuple

import requests
from bs4 import BeautifulSoup

# Playwright helper (fallback)
try:
    from browser_extract import browser_extract
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

# ---------------------------------------
# CONFIG
# ---------------------------------------
INPUT_PATH = Path(r"D:\trading\News Last 48H\out\articles.json")
OUTPUT_PATH = Path(r"D:\trading\News Last 48H\KMCO_out\articles_full.json")
LOG_PATH = Path(r"D:\trading\News Last 48H\KMCO_out\extract_log.txt")

REMOVE_OLD_OUTPUT = True   # supprime ancien output si True
TEST_LIMIT = None          # mettre 1 pour tester un article, None pour tout lancer

HEADERS_COMMON = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}

REQUEST_TIMEOUT = 12  # secondes
MAX_CHARS = 40000     # tronque le contenu sauvegardé

PREFERRED_DOMAINS = ("reuters.com", "bloomberg.com", "ft.com", "wsj.com", "bbc.com", "investing.com")

# ---------------------------------------
# UTIL
# ---------------------------------------
def log(msg: str):
    s = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(s)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(s + "\n")
    except Exception:
        pass

def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    return text.strip()

def extract_real_url_from_summary(art: dict) -> str:
    """Essaye d'extraire une URL directe (Reuters/Bloomberg/...) depuis summary ou title."""
    url = art.get("url", "") or ""
    if any(d in url for d in PREFERRED_DOMAINS):
        return url
    summary = art.get("summary", "") or ""
    # chercher hrefs et préférer un domaine connu
    hrefs = re.findall(r'href="([^"]+)"', summary)
    for h in hrefs:
        candidate = unescape(h)
        if any(domain in candidate for domain in PREFERRED_DOMAINS):
            return candidate
    # fallback: find any https link
    m = re.search(r'(https?://[^\s"\'<>]+)', summary)
    if m:
        return unescape(m.group(1))
    return url

# ---------------------------------------
# EXTRACTION via requests (fast path)
# ---------------------------------------
def extract_with_requests(url: str, timeout=REQUEST_TIMEOUT) -> Tuple[str, str, str]:
    """
    Retourne (text, final_url, status)
    status in {"ok","consent_block","no_content","http_error_xx","error: ..."}
    """
    s = requests.Session()
    s.headers.update(HEADERS_COMMON)
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True)
    except Exception as e:
        return ("", url, f"error: {e}")

    final = r.url
    if r.status_code != 200:
        return ("", final, f"http_error_{r.status_code}")

    body = r.text.lower()
    if "consent.google" in final or ("consent" in body and ("accept all" in body or "we use cookies" in body or "we and our partners" in body)):
        return ("", final, "consent_block")

    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "header", "footer", "aside", "nav", "noscript"]):
        tag.decompose()

    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 60]
    text = " ".join(paragraphs).strip()
    if not text:
        # fallback: meta description or article tag or ld+json articleBody
        meta = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
        if meta and meta.get("content"):
            text = meta.get("content", "")
        else:
            # try article tag
            article_tag = soup.find("article")
            if article_tag:
                paras = [p.get_text(" ", strip=True) for p in article_tag.find_all("p") if len(p.get_text(strip=True)) > 30]
                text = " ".join(paras)
            else:
                # try json-ld articleBody
                ld = soup.find("script", {"type": "application/ld+json"})
                if ld:
                    try:
                        import json as _json
                        j = _json.loads(ld.string)
                        if isinstance(j, dict):
                            body = j.get("articleBody") or j.get("description") or ""
                            text = body
                    except Exception:
                        pass
    text = clean_text(text)
    if not text:
        return ("", final, "no_content")
    return (text[:MAX_CHARS], final, "ok")

# ---------------------------------------
# MAIN
# ---------------------------------------
def main():
    start_time = time.time()

    if not INPUT_PATH.exists():
        log(f"FATAL: input file not found: {INPUT_PATH}")
        return

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    log(f"Données chargées : type={type(data)}")

    # normalize
    if isinstance(data, dict):
        flat = []
        for v in data.values():
            if isinstance(v, list):
                flat.extend(v)
        data = flat
    elif isinstance(data, list):
        pass
    else:
        log("FATAL: JSON format unknown (neither list nor dict).")
        return

    log(f"Articles à traiter : {len(data)}")

    if REMOVE_OLD_OUTPUT and OUTPUT_PATH.exists():
        try:
            OUTPUT_PATH.unlink()
            log(f"Ancien fichier {OUTPUT_PATH} supprimé (REMOVE_OLD_OUTPUT=True).")
        except Exception as e:
            log(f"Warning: impossible de supprimer ancien output: {e}")

    # Pré-traitement : remplacer les urls Google News si on peut trouver une vraie url dans summary
    replaced = 0
    for art in data:
        if not isinstance(art, dict):
            continue
        url = art.get("url", "") or ""
        if "news.google" in url:
            candidate = extract_real_url_from_summary(art)
            if candidate and candidate != url:
                art["url"] = candidate
                replaced += 1
    log(f"Pré-traitement URLs : {replaced} URLs Google News remplacées si trouvées.")

    output = []
    failures = []

    for i, art in enumerate(data, start=1):
        if TEST_LIMIT and i > TEST_LIMIT:
            break

        if not isinstance(art, dict):
            log(f"SKIP #{i} : element type {type(art)}")
            continue

        candidate_url = art.get("url", "") or ""
        if not candidate_url:
            candidate_url = extract_real_url_from_summary(art)
        if not candidate_url:
            log(f"SKIP #{i} : no url")
            continue

        log(f"[{i}/{len(data)}] Try requests -> {candidate_url[:160]}")
        content, final_url, status = extract_with_requests(candidate_url)

        record = dict(art)
        record["_extraction"] = {
            "method": "requests",
            "status": status,
            "final_url": final_url,
        }

        if status == "ok":
            record["content"] = content
            output.append(record)
            log(f"OK (requests) #{i} -> approx {len(content.split())} words.")
        else:
            if PLAYWRIGHT_AVAILABLE:
                log(f"Fallback Playwright for #{i} (reason: {status})")
                try:
                    res = browser_extract(candidate_url, headless=True, timeout=30_000)
                    # browser_extract returns dict with keys: text, final_url, debug
                    if isinstance(res, dict):
                        text = res.get("text", "") or ""
                        final_page = res.get("final_url") or final_url or candidate_url
                    else:
                        text = str(res)
                        final_page = final_url or candidate_url

                    if text and len(text.strip()) > 50:
                        record["content"] = text[:MAX_CHARS]
                        record["_extraction"] = {
                            "method": "playwright",
                            "status": "ok",
                            "final_url": final_page,
                        }
                        output.append(record)
                        log(f"OK (playwright) #{i} -> approx {len(text.split())} words.")
                    else:
                        record["content"] = ""
                        record["_extraction"]["status"] = "playwright_no_content"
                        record["_extraction"]["debug"] = (res.get("debug") if isinstance(res, dict) else "")
                        failures.append(record)
                        log(f"FAIL (playwright_no_content) #{i}")
                except Exception as e:
                    record["content"] = ""
                    record["_extraction"]["status"] = f"playwright_error: {e}"
                    failures.append(record)
                    log(f"ERROR (playwright) #{i} : {e}")
            else:
                record["content"] = ""
                failures.append(record)
                log(f"NO PLAYWRIGHT installed, skipped fallback for #{i} (status={status})")

        time.sleep(random.uniform(0.45, 1.15))

    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        log(f"✅ Extraction terminée : {len(output)} articles sauvés -> {OUTPUT_PATH}")
        if failures:
            log(f"⚠️ Articles échoués : {len(failures)} (voir log pour détails)")
    except Exception as e:
        log(f"FATAL: impossible d'écrire output: {e}")

    elapsed = round(time.time() - start_time, 1)
    log(f"Durée totale : {elapsed}s")


if __name__ == "__main__":
    main()
