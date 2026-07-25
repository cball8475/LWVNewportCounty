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

# Don't rewrite the HTML block unless the fetch produced at least this many
# valid items — a thin result usually means the scrape half-failed, and we'd
# rather keep yesterday's good content than replace it with less.
MIN_ITEMS_FOR_HTML = 2

# Titles that mean the scraper grabbed site chrome, not a press release.
JUNK_TITLES = {
    "pagination", "next", "previous", "next page", "previous page",
    "read more", "learn more", "press releases", "newsroom",
}


def looks_valid(item):
    """Filter out nav/pager artifacts regardless of which fetcher produced them."""
    title = (item.get("title") or "").strip()
    link = item.get("link") or ""
    if len(title) < 15 or title.lower() in JUNK_TITLES:
        return False
    return "/newsroom/press-releases/" in link


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
    Fallback: parse the HTML press releases page. Walks every link that points
    at a press-release detail page and takes the link's own text as the title —
    container-based selectors proved fragile against the Drupal template (they
    once matched a nav block and produced an item titled "Pagination").
    """
    r = requests.get(PRESS_URL, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(LWV_BASE, a["href"]).split("#")[0].split("?")[0]
        if "/newsroom/press-releases/" not in href or href.rstrip("/") == PRESS_URL:
            continue
        if href in seen:
            continue

        title = a.get_text(strip=True)
        if len(title) < 15 or title.lower() in JUNK_TITLES:
            continue  # "Read more"-style links; the headline link will come by
        seen.add(href)

        date = ""
        summary = ""
        container = a.find_parent(["article", "li", "div"])
        if container:
            date_el = container.find("time")
            if date_el:
                date = date_el.get("datetime") or date_el.get_text(strip=True)
            summary_el = container.find("p")
            if summary_el:
                summary = summary_el.get_text(strip=True)[:300]

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

def _fmt_date(raw):
    """Best-effort: turn ISO / RSS date strings into 'June 29, 2026'."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    dt = None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                    "%m/%d/%Y", "%B %d, %Y"):
            try:
                dt = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
    if dt is None:
        return raw  # show whatever the source gave us rather than nothing
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def render_html_block(items):
    """
    Render items as article cards matching the hand-written press-release
    cards on news.html (inline styles, site palette).
    """
    html_lines = []
    for it in items:
        title = _escape(it.get("title", ""))
        link = _escape(it.get("link", "#"))
        date = _escape(_fmt_date(it.get("date", "")))
        summary = _escape(it.get("summary", ""))

        label = "Press Release &bull; LWVUS" + (f" &bull; {date}" if date else "")
        html_lines.append('        <article style="border-bottom: 1px solid #e0e0e0; padding: 35px 0;">')
        html_lines.append(
            f'            <p style="color: #d32f2f; font-size: 13px; font-weight: 700; '
            f'text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">{label}</p>'
        )
        html_lines.append(f'            <h3 style="margin: 0 0 12px 0; color: #003d7a;">{title}</h3>')
        if summary:
            html_lines.append(f'            <p>{summary}</p>')
        html_lines.append('            <p style="margin-top: 15px;">')
        html_lines.append(
            f'                <a href="{link}" target="_blank" rel="noopener" '
            f'style="background: #003d7a; color: white; padding: 10px 22px; text-decoration: none; '
            f'font-weight: 600; display: inline-block; font-size: 14px;">Read Full Statement &rarr;</a>'
        )
        html_lines.append('            </p>')
        html_lines.append('        </article>')

    updated = datetime.now(timezone.utc).strftime("%B %d, %Y")
    html_lines.append(
        f'        <p style="color: #888; font-size: 13px; font-style: italic; margin-top: 20px;">'
        f'Updated automatically from the '
        f'<a href="{PRESS_URL}" target="_blank" rel="noopener">LWVUS newsroom</a> on {updated}.</p>'
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

    items = [it for it in (items or []) if looks_valid(it)][:MAX_ITEMS]
    if not items:
        # RSS unavailable AND the scrape producing zero valid items is not a
        # slow news week — LWVUS always has press releases. Exiting 0 here made
        # a site redesign look like success every 6 hours indefinitely while
        # the news block silently froze. Fail the workflow so it shows red.
        print(
            "[main] FATAL: zero valid items from both RSS and scrape — the "
            "LWVUS site layout has probably changed and the fetchers need "
            "updating. Failing loudly instead of freezing the feed silently.",
            file=sys.stderr,
        )
        sys.exit(1)

    write_json(items)
    if len(items) >= MIN_ITEMS_FOR_HTML:
        block = render_html_block(items)
        update_html_files(block)
    else:
        # Thin result: JSON updated, HTML deliberately kept. Surface it as a
        # visible annotation on the workflow run, not just a stderr line.
        print(
            f"::warning::fetch_lwvus got only {len(items)} valid item(s) "
            f"(need {MIN_ITEMS_FOR_HTML} to rewrite HTML) — the scrape may be "
            "half-broken; site HTML block left unchanged.",
        )
        print(
            f"[main] only {len(items)} valid item(s) — keeping the existing HTML block",
            file=sys.stderr,
        )

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
