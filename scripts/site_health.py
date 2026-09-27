#!/usr/bin/env python3
"""
site_health.py - stale-content and sanity digest for the LWV Newport County site.

Printed at the start of every Claude Code web session by
.claude/hooks/session-start.sh, and safe to run by hand any time:

    python3 scripts/site_health.py            # digest; always exits 0
    python3 scripts/site_health.py --strict   # exit 1 if anything is flagged (for CI)
    SITE_HEALTH_TODAY=2026-10-02 python3 scripts/site_health.py   # preview a future day

Standard library only and read-only. Every check fails soft: a check that
can't run prints a note instead of breaking the session. Dates are judged in
Newport's time zone (America/New_York).

Checks
  1. events.html  - event cards under "Upcoming Events" whose date has passed.
  2. index.html   - dates in the top-of-page banners (alert band, Elections
                    band) that have passed or expire within SOON_DAYS.
  3. Promo pages  - a past "Weekday, Month D" date near a Register / Tickets /
                    RSVP link: a likely stale event promo.
  4. elections-2026.html - countdown cards and "Add to calendar" items whose
                    date has passed (informational; the hub keeps a timeline).
  5. Every *.html - files cut off before </html> (a web-upload failure mode),
                    dead Cloudflare /cdn-cgi/ email links, and tag balance.
  6. GitHub Actions - latest run of each workflow that still exists (skipped
                    when the API can't be reached).

Why this exists: in Sept 2026 the site showed events from April and June as
"upcoming", a homepage deadline two months stale, and a workflow that had
failed for days - all things a two-second check at session start catches.
"""
import glob
import html
import json
import os
import re
import ssl
import sys
import urllib.request
from datetime import date, datetime
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "cball8475/LWVNewportCounty"
SOON_DAYS = 7

try:
    from zoneinfo import ZoneInfo
    TODAY = datetime.now(ZoneInfo("America/New_York")).date()
except Exception:  # no tz database: UTC is close enough for a digest
    TODAY = datetime.utcnow().date()
if os.environ.get("SITE_HEALTH_TODAY"):  # e.g. SITE_HEALTH_TODAY=2026-10-02 to preview a future day
    TODAY = date.fromisoformat(os.environ["SITE_HEALTH_TODAY"])

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
MONTH_RE = (r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|"
            r"Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
# "Oct 4", "Sept. 30", "September 30, 2026": capitalised month + day, optional year.
DATE_RE = re.compile(MONTH_RE + r"\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:,?\s+(\d{4}))?")
WEEKDAY_DATE_RE = re.compile(r"(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+" + DATE_RE.pattern)
PROMO_LINK_RE = re.compile(r"(?i)register now|get your tickets|\btickets?\b|\brsvp\b|qgiv\.com|"
                           r"eventbrite|forms\.gle|docs\.google\.com/forms|sign up")
# Pages that carry event promos. vote.html and elections-2026.html are reference
# schedules (past dates there are records, not promos); events.html has check 1.
PROMO_PAGES = ["index.html", "issues.html", "get-involved.html", "action-alerts.html", "about.html"]

findings = []  # (level, message); level is one of LEVELS
LEVELS = {"warn": "⚠", "soon": "⏳", "info": "ℹ", "ok": "✓", "skip": "…"}


def to_date(mon, day, year=None):
    """Month name + day (+ optional year) -> date. A year-less date more than
    about six months back is read as next year's (a January event listed in
    December)."""
    try:
        month = MONTHS[mon[:3].lower()]
        if year:
            return date(int(year), month, int(day))
        d = date(TODAY.year, month, int(day))
        if (TODAY - d).days > 183:
            d = date(TODAY.year + 1, month, int(day))
        return d
    except (KeyError, ValueError):
        return None


def short(d):
    return f"{d.strftime('%b')} {d.day}"


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_noise(src):
    """Drop comments, <script> and <style>, so dates in notes and code don't count."""
    src = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    return re.sub(r"<(script|style)\b.*?</\1>", " ", src, flags=re.S | re.I)


def text_of(src):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", strip_noise(src)))).strip()


# ---------------------------------------------------------------------- checks

def check_upcoming_events():
    src = strip_noise(read("events.html"))
    m = re.search(r"<h2[^>]*>\s*Upcoming Events\s*</h2>(.*?)(?=<h2)", src, re.S | re.I)
    if not m:
        findings.append(("skip", "events.html: couldn't find the Upcoming Events section"))
        return
    # Card date badge: month label div, the 48px day number, then the card's <h3> title.
    cards = re.findall(r">\s*" + MONTH_RE + r"\s*</div>\s*<div[^>]*font-size:\s*48px[^>]*>\s*(\d{1,2})\s*</div>"
                       r".*?<h3[^>]*>(.*?)</h3>", m.group(1), re.S)
    past = [(to_date(mon, day), text_of(title)) for mon, day, title in cards]
    past = [(d, t) for d, t in past if d and d < TODAY]
    for d, t in past:
        findings.append(("warn", f'events.html: "{t}" ({short(d)}) has passed but is still under Upcoming Events'))
    if not past:
        findings.append(("ok", f"events.html: {len(cards)} upcoming event card(s), none past"))


def check_homepage_top():
    src = read("index.html")
    cut = src.find("<!-- IMPACT SECTION -->")
    top = text_of(src[:cut] if cut > 0 else src[:20000])
    seen, flagged = set(), 0
    for m in DATE_RE.finditer(top):
        d = to_date(m.group(1), m.group(2), m.group(3))
        if not d or (m.group(0), d) in seen:
            continue
        seen.add((m.group(0), d))
        # Lead-in words for context ("Register by"), cut at the previous icon or punctuation.
        before = re.split(r"[^\w\s,'()-]", top[max(0, m.start() - 40):m.start()])[-1].lstrip()
        if d < TODAY:
            findings.append(("warn", f'index.html top banners: "{before}{m.group(0)}" has passed'))
            flagged += 1
        elif (d - TODAY).days <= SOON_DAYS:
            days = (d - TODAY).days
            when = "today" if days == 0 else f"in {days} day(s)"
            findings.append(("soon", f'index.html top banners: "{before}{m.group(0)}" goes stale {when}'))
            flagged += 1
    if not flagged:
        findings.append(("ok", "index.html top banners: no past or soon-to-expire dates"))


def check_stale_promos():
    hits = 0
    for name in PROMO_PAGES:
        if not os.path.exists(os.path.join(ROOT, name)):
            continue
        src = strip_noise(read(name))
        seen = set()
        for m in WEEKDAY_DATE_RE.finditer(src):
            d = to_date(m.group(1), m.group(2), m.group(3))
            if not d or d >= TODAY or d in seen:
                continue
            if PROMO_LINK_RE.search(src[max(0, m.start() - 1500):m.end() + 1500]):
                seen.add(d)
                hits += 1
                findings.append(("warn", f'{name}: "{html.unescape(m.group(0))}" has passed but sits next to a '
                                         f'Register/Tickets/RSVP link (likely a stale promo)'))
    if not hits:
        findings.append(("ok", "promo pages: no past-dated event promos"))


def check_elections_hub():
    name = "elections-2026.html"
    if not os.path.exists(os.path.join(ROOT, name)):
        return
    src = strip_noise(read(name))
    # Countdown cards at the top of the hub: static "Aug 10" + a label.
    for mon, day, label in re.findall(r'class="el-count-num"[^>]*>\s*' + MONTH_RE + r"\.?\s+(\d{1,2})\s*</div>\s*"
                                      r'<div class="el-count-label">(.*?)</div>', src, re.S):
        d = to_date(mon, day)
        if d and d < TODAY:
            findings.append(("info", f'{name}: countdown card "{text_of(label)}" ({short(d)}) has passed'))
    # "Add to calendar" buttons carry ISO dates.
    items = []
    for tag in re.findall(r"<[^>]*\bdata-cal\b[^>]*>", src):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        try:
            end = date.fromisoformat(attrs.get("data-end") or attrs["data-date"])
        except (KeyError, ValueError):
            continue
        items.append((end, html.unescape(attrs.get("data-title", "?"))))
    if items:
        past = sorted((e, t) for e, t in items if e < TODAY)
        msg = f'{name}: {len(past)} of {len(items)} "Add to calendar" items have passed'
        upcoming = sorted((e, t) for e, t in items if e >= TODAY)
        if upcoming:
            msg += f'; next is "{upcoming[0][1]}" ({short(upcoming[0][0])})'
        findings.append(("info", msg))


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr", "path", "rect", "circle", "line", "polyline", "polygon", "ellipse", "use", "stop"}


class _Balance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], 0

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors += 1


def check_structure():
    files = sorted(glob.glob(os.path.join(ROOT, "*.html")))
    cut_off, unbalanced, cloudflare = [], [], []
    for path in files:
        name = os.path.basename(path)
        with open(path, encoding="utf-8", errors="replace") as f:
            src = f.read()
        # A full page (not a fragment like events-archive.html) must end with </html>;
        # files uploaded through the GitHub web UI have arrived cut off mid-tag.
        # Cloudflare's email obfuscation only works behind Cloudflare; copied onto
        # GitHub Pages it leaves dead /cdn-cgi/l/email-protection links.
        if "/cdn-cgi/" in src:
            cloudflare.append(name)
        if re.search(r"<html\b", src, re.I) and not re.search(r"</html>\s*$", src, re.I):
            cut_off.append(name)
            continue
        p = _Balance()
        try:
            p.feed(src)
            p.close()
        except Exception as e:
            unbalanced.append(f"{name} (parse error: {e})")
            continue
        if p.errors or p.stack:
            unbalanced.append(f"{name} ({p.errors} mismatched, {len(p.stack)} unclosed)")
    if cut_off:
        findings.append(("warn", "page file is cut off (doesn't end with </html>): " + ", ".join(cut_off)))
    if cloudflare:
        findings.append(("warn", "dead Cloudflare /cdn-cgi/ email links (copied from a live page): " + ", ".join(cloudflare)))
    if unbalanced:
        findings.append(("warn", "HTML tag balance: " + "; ".join(unbalanced)))
    if not (cut_off or cloudflare or unbalanced):
        findings.append(("ok", f"HTML structure: all {len(files)} pages complete and balanced"))


def _ssl_context():
    # The web sandbox routes HTTPS through a proxy with its own CA; honour the
    # usual CA-bundle variables so the API call works there and on laptops alike.
    for var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "PIP_CERT"):
        path = os.environ.get(var)
        if path and os.path.exists(path):
            return ssl.create_default_context(cafile=path)
    return ssl.create_default_context()


def check_workflows():
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch=main&per_page=50"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "lwvnc-site-health"})
    try:
        with urllib.request.urlopen(req, timeout=6, context=_ssl_context()) as r:
            runs = json.load(r).get("workflow_runs", [])
    except Exception as e:
        findings.append(("skip", f"workflows: GitHub API not reachable ({e.__class__.__name__}); check the Actions tab"))
        return
    latest = {}
    for run in runs:  # the API returns newest first
        path = (run.get("path") or "").split("@")[0]
        # Skip workflows whose file has been deleted (their last run may be a stale failure).
        if path.startswith(".github/workflows/") and not os.path.exists(os.path.join(ROOT, path)):
            continue
        latest.setdefault(run.get("name") or path, run)
    bad = {n: r for n, r in latest.items()
           if r.get("status") == "completed" and r.get("conclusion") not in ("success", "skipped", "neutral")}
    for n, r in bad.items():
        findings.append(("warn", f'workflow "{n}": last run {r.get("conclusion")} on {(r.get("created_at") or "")[:10]} '
                                 f'({r.get("html_url")})'))
    if latest and not bad:
        findings.append(("ok", f"workflows: latest run of each is green ({', '.join(sorted(latest))})"))


def main():
    for check in (check_upcoming_events, check_homepage_top, check_stale_promos,
                  check_elections_hub, check_structure, check_workflows):
        try:
            check()
        except Exception as e:  # one broken check must never hide the others
            findings.append(("skip", f"{check.__name__} didn't run: {e.__class__.__name__}: {e}"))
    print(f"LWVNC site health - {TODAY.strftime('%a %b')} {TODAY.day}, {TODAY.year} (Newport time)")
    for level, icon in LEVELS.items():
        for lvl, msg in findings:
            if lvl == level:
                print(f"  {icon} {msg}")
    warns = sum(1 for lvl, _ in findings if lvl == "warn")
    if warns:
        print(f"  -> {warns} item(s) need attention. Mention them to the user at a natural point; "
              f"don't change public pages without their OK.")
    return 1 if ("--strict" in sys.argv and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
