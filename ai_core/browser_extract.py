# -*- coding: utf-8 -*-
"""
KM&CO Browser Extractor v1.4
Fallback Playwright : suit Google News -> redirige vers site d'origine, clique les boutons "accept" si détectés,
et extrait le texte principal.
Retour: dict { "text": str, "final_url": str, "debug": str }
"""

import time
import re
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    raise RuntimeError("Playwright non disponible. Installe `pip install playwright` et `playwright install`") from e

TARGET_DOMAINS = [
    "reuters.com", "bloomberg.com", "bbc.com", "investing.com", "ft.com", "wsj.com"
]

CONSENT_SELECTORS = [
    'button:has-text("Accept all")',
    'button:has-text("I agree")',
    'button:has-text("Accept")',
    'button:has-text("AGREE")',
    'button:has-text("OK")',
    'text="Accept all"',
    'text="I agree"',
]

def browser_extract(url: str, headless: bool = True, timeout: int = 30000) -> dict:
    debug = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ))
            page = context.new_page()

            debug.append(f"goto: {url}")
            page.goto(url, timeout=timeout)
            time.sleep(1.0)

            html = page.content()
            final_url = page.url

            # Si Google News, cherche une vraie URL dans le HTML et redirige
            if "news.google" in final_url:
                pattern = r'https://(?:www\.)?(?:' + "|".join([re.escape(d) for d in TARGET_DOMAINS]) + r')[^"\'<> ]+'
                m = re.search(pattern, html)
                if m:
                    true_url = m.group(0)
                    debug.append(f"found_true_url_in_google_news: {true_url}")
                    page.goto(true_url, timeout=timeout)
                    time.sleep(2.0)
                else:
                    debug.append("no_true_url_found_on_google_news")

            # Essayer de cliquer les boutons de consentement s'ils existent
            clicked = False
            for sel in CONSENT_SELECTORS:
                try:
                    if page.locator(sel).count() > 0:
                        page.locator(sel).first.click(timeout=4000)
                        debug.append(f"clicked_consent_selector: {sel}")
                        time.sleep(1.2)
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                debug.append("no_consent_clicked")

            # reload content after interactions
            html = page.content()
            final_url = page.url
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "header", "footer", "aside", "nav", "noscript"]):
                tag.decompose()

            # method 1: paragraph extraction
            paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 50]
            text = "\n".join(paragraphs).strip()

            # method 2 fallback: article tag text
            if not text:
                article = soup.find("article")
                if article:
                    paras = [p.get_text(" ", strip=True) for p in article.find_all("p") if len(p.get_text(strip=True)) > 30]
                    text = "\n".join(paras).strip()

            # method 3 fallback: og:description or meta description
            if not text:
                meta = soup.find("meta", {"property": "og:description"}) or soup.find("meta", {"name": "description"})
                if meta and meta.get("content"):
                    text = meta.get("content", "").strip()

            # final cleanup
            text = text.strip()
            if not text:
                debug.append("no_content_extracted")
                browser.close()
                return {"text": "", "final_url": final_url, "debug": "\n".join(debug)}

            debug.append(f"content_len:{len(text)}")
            browser.close()
            return {"text": text, "final_url": final_url, "debug": "\n".join(debug)}

    except Exception as e:
        debug.append(f"exception:{e}")
        return {"text": "", "final_url": url, "debug": "\n".join(debug)}
