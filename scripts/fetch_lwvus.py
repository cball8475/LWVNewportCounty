#!/usr/bin/env python3
"""
fetch_lwvus.py

Pulls the latest LWVUS press releases and keeps two things in sync in the repo:

  1. data/lwvus-news.json
     A machine-readable snapshot of the top N items (title, link, date,
     summary). Useful for SEO crawlers, future reuse (newsletter, widget,
     etc.), and for auditing what the bot saw.

  2. An HTML block on one or more pages in the repo.
     Any page that contains the marker pair below will have the block
     between the markers replaced with freshly rendered HTML:

         <!-- LWVUS_NEWS_START -->
         ...anything in here gets replaced...
         <!-- LWVUS_NEWS_END -->

     Drop those two comment lines into whichever page should display the
     feed (e.g., index.html, news.html, action-alerts.html). The script
     scans every *.html file at the repo root for the markers, so you can
     have the feed show on more than one page if you want.

Strategy:
  - Try the Drupal default RSS feed first (fast, structured, stable).
  - If that fails (403, 404, empty, malformed), fall back to scraping the
    press releases listing page with BeautifulSoup.
  - Exit non-zero only on unrecoverable failure. Commit step in the
    workflow is a no-op if nothing changed.

Brand palette (used in the rendered HTML): navy #1B3A6B, gold #C5A028.
Styling is mostly inline classes so you can theme it with the site's
existing CSS. Add matching rules to your stylesheet (see README block
at the bottom of this file for suggested CSS).
"""

import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

LWV_BASE = "https://www.lwv.org"
PRESS_URL = f"{LWV_BASE}/newsroom/press-releases"
RSS_URL = f"{LWV_BASE}/rss.xml"  # Drupal default; may or may not be live

OUTPUT_JSON = "data/lwvus-news.json"
MAX_ITEMS = 5
REQUEST_TIMEOUT = 20  # seconds

# Be a polite bot: identify ourselves and where we're coming from.
UA = (
    "Mozilla/5.0 (compatible; LWVNC-FeedBot/1.0; "
    "+https://lwvnewportcounty.org)"
)

MARKER_START = "<!-- LWVUS_NEWS_START -->"
MARKER_END = "<!-- LWVUS_NEWS_END -->"


# -----------------------------------------------------------------------------
# Fetchers
# -----------------------------------------------------------------------------

def try_rss():
    """
    Attempt the Drupal RSS feed. Returns a list of item dicts or None.

    Item shape:
        {"title": str, "link": str, "date": str, "summary": str}
    """
    try:
        r = requests.get(RSS_URL, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        print(f"[rss] request failed: {e}", file=sys.stderr)
        return None

    if r.status_code != 200 or "<rss" not in r.text.lower():
        print(f"[rss] status={r.status_code}, not an RSS doc; falling back", file=sys.stderr)
        return None

    soup = BeautifulSoup(r.text, "xml")
    items = []
    for item in soup.find_all("item")[:MAX_ITEMS]:
        def _txt(tag):
            el = item.find(tag)
            return el.get_text(strip=True) if el else ""
        items.append({
            "title": _txt("title"),
            "link": _txt("link"),
            "date": _txt("pubDate"),
            "summary": _txt("description")[:300],
        })
    return items if items else None


def scrape_press_releases():
    """
    Fallback: parse the HTML press releases page. Selectors are best-effort
    and may need tuning if LWV changes their Drupal template.
    """
    r = requests.get(PRESS_URL, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    # Drupal listing pages typically wrap each entry in <article> or
    # <div class="views-row">. Try both; whichever hits first wins.
    candidates = soup.select("article, .views-row, .node--type-press-release")
    for el in candidates:
        link_el = el.find("a", href=True)
        title_el = el.find(["h2", "h3", "h4"])
        if not link_el or not title_el:
            continue

        href = urljoin(LWV_BASE, link_el["href"])
        # Skip non-press-release links (nav, social, etc.)
        if "/newsroom/" not in href and "/press-releases" not in href:
            # Still might be a valid item link; keep it if the title looks real.
            if len(title_el.get_text(strip=True)) < 10:
                continue

        title = title_el.get_text(strip=True)

        date_el = el.find("time")
        date = ""
        if date_el:
            date = date_el.get("datetime") or date_el.get_text(strip=True)

        summary_el = el.find("p")
        summary = summary_el.get_text(strip=True)[:300] if summary_el else ""

        items.append({
            "title": title,
            "link": href,
            "date": date,
            "summary": summary,
        })
        if len(items) >= MAX_ITEMS:
            break

    return items


# -----------------------------------------------------------------------------
# Rendering
# -----------------------------------------------------------------------------

def render_html_block(items):
    """
    Render items as an HTML fragment. Classes are prefixed `lwvus-` so
    they don't collide with the rest of the site's CSS.
    """
    html_lines = ['<div class="lwvus-news-list">']
    for it in items:
        title = _escape(it.get("title", ""))
        link = _escape(it.get("link", "#"))
        date = _escape(it.get("date", ""))
        summary = _escape(it.get("summary", ""))

        html_lines.append('  <article class="lwvus-news-item">')
        html_lines.append(
            f'    <h3 class="lwvus-news-title">'
            f'<a href="{link}" target="_blank" rel="noopener">{title}</a>'
            f'</h3>'
        )
        if date:
            html_lines.append(f'    <p class="lwvus-news-date">{date}</p>')
        if summary:
            html_lines.append(f'    <p class="lwvus-news-summary">{summary}</p>')
        html_lines.append('  </article>')
    html_lines.append('</div>')

    updated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    html_lines.append(
        f'<p class="lwvus-news-updated"><em>Source: '
        f'<a href="{PRESS_URL}" target="_blank" rel="noopener">LWVUS Press Releases</a>. '
        f'Last updated {updated}.</em></p>'
    )
    return "\n".join(html_lines)


def _escape(s: str) -> str:
    """Minimal HTML escaping for text we're injecting into templates."""
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


# -----------------------------------------------------------------------------
# File updates
# -----------------------------------------------------------------------------

def update_html_files(block):
    """
    Scan all *.html files at the repo root and replace the content
    between the LWVUS_NEWS markers with `block`. Returns the count of
    files that were modified.
    """
    pattern = re.compile(
        rf"({re.escape(MARKER_START)})(.*?)({re.escape(MARKER_END)})",
        re.DOTALL,
    )
    changed = 0
    for path in sorted(glob.glob("*.html")):
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        if MARKER_START not in html:
            continue
        new_html = pattern.sub(
            lambda m: f"{m.group(1)}\n{block}\n{m.group(3)}",
            html,
        )
        if new_html != html:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_html)
            print(f"[update] {path}")
            changed += 1
    return changed


def write_json(items):
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": PRESS_URL,
        "items": items,
    }
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[write] {OUTPUT_JSON} ({len(items)} items)")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    items = try_rss()
    if not items:
        print("[main] RSS unavailable, falling back to scrape", file=sys.stderr)
        try:
            items = scrape_press_releases()
        except requests.RequestException as e:
            print(f"[main] scrape failed: {e}", file=sys.stderr)
            sys.exit(1)

    if not items:
        print("[main] no items found; exiting without changes", file=sys.stderr)
        sys.exit(0)  # exit clean; commit step will be a no-op

    write_json(items)
    block = render_html_block(items)
    update_html_files(block)

    print(f"[done] {len(items)} items processed")


if __name__ == "__main__":
    main()


# -----------------------------------------------------------------------------
# Suggested CSS (paste into your site's main stylesheet)
# -----------------------------------------------------------------------------
# .lwvus-news-list { display: grid; gap: 1.25rem; margin: 1rem 0; }
# .lwvus-news-item {
#     border-left: 4px solid #C5A028;   /* LWVNC gold */
#     padding: 0.75rem 1rem;
#     background: #F8F6EF;              /* cream */
# }
# .lwvus-news-title { margin: 0 0 0.25rem; }
# .lwvus-news-title a { color: #1B3A6B; text-decoration: none; }  /* navy */
# .lwvus-news-title a:hover { text-decoration: underline; }
# .lwvus-news-date { font-size: 0.875rem; color: #555; margin: 0 0 0.5rem; }
# .lwvus-news-summary { margin: 0; line-height: 1.5; }
# .lwvus-news-updated { font-size: 0.8rem; color: #666; margin-top: 1rem; }
