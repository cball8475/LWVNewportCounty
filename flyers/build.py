#!/usr/bin/env python3
"""
Generate LWV Newport County candidate-forum flyers.

Reproduces the template used for the RI District 13 State Senate Primary Forum
flyer: US Letter (8.5 x 11 in), LWV navy header, red "CANDIDATES FORUM" badge,
navy headline, bordered info card with icon rows, navy call-to-action banner,
partner-logo strip and navy footer.

Usage:  python3 flyers/build.py           # writes HTML + PDF + PNG into flyers/out
"""

import base64
import json
import mimetypes
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "out")

CHROME = os.environ.get("CHROME_BIN", "/opt/pw-browsers/chromium")

# ---------------------------------------------------------------- shared bits

NAVY = "#003d7b"
RED = "#d32f2f"
SKY = "#c1e3fb"
GOLD = "#fbd44b"

PARTNERS = [
    ("partner-chamber.png", 52),
    ("partner-newport-this-week.png", 21),
    ("partner-east-bay.png", 49),
    ("partner-common-cause.png", 31),
    ("partner-aarp.png", 38),
]

ICONS = {
    "calendar": (
        '<rect x="3" y="4" width="18" height="18" rx="2"/>'
        '<path d="M16 2v4M8 2v4M3 10h18"/>'
    ),
    "pin": (
        '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>'
        '<circle cx="12" cy="10" r="3"/>'
    ),
    "user": (
        '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>'
        '<circle cx="12" cy="7" r="4"/>'
    ),
    "question": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/>'
        '<path d="M12 17h.01"/>'
    ),
}


def data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode())


def icon(name, size):
    return (
        '<svg class="ic" viewBox="0 0 24 24" width="%d" height="%d" fill="none" '
        'stroke="%s" stroke-width="1.9" stroke-linecap="round" '
        'stroke-linejoin="round">%s</svg>' % (size, size, NAVY, ICONS[name])
    )


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def row(item, icon_px, compact=False):
    """One label / value / detail row inside an info card."""
    value = item["value"]
    if item.get("href"):
        value = '<a href="%s">%s</a>' % (item["href"], esc(value))
    else:
        value = esc(value)
    detail = ""
    if item.get("detail"):
        detail = '<div class="detail">%s</div>' % esc(item["detail"])
    return (
        '<div class="row%s">'
        '<div class="badge-ic">%s</div>'
        '<div class="txt"><div class="label">%s</div>'
        '<div class="value%s">%s</div>%s</div>'
        "</div>"
    ) % (
        " compact" if compact else "",
        icon(item["icon"], icon_px),
        esc(item["label"]),
        " link" if item.get("href") else "",
        value,
        detail,
    )


def partner_strip():
    imgs = "".join(
        '<img src="%s" style="height:%dpt">' % (data_uri(os.path.join(ASSETS, f)), h)
        for f, h in PARTNERS
    )
    return (
        '<div class="partners">'
        '<div class="partners-label">Presented in partnership with</div>'
        '<div class="partner-logos">%s</div>'
        "</div>" % imgs
    )


CSS = """
@page { size: 8.5in 11in; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { width: 816px; height: 1056px; }
body {
  font-family: "Liberation Sans", Arial, Helvetica, sans-serif;
  background: #fff; color: #1a1a1a;
  -webkit-font-smoothing: antialiased;
  -webkit-print-color-adjust: exact; print-color-adjust: exact;
}
.page { width: 816px; height: 1056px; display: flex; flex-direction: column; overflow: hidden; }

/* ---------- header ---------- */
.header { position: relative; height: 162px; background: NAVY; flex: none;
          display: flex; flex-direction: column; align-items: center; }
.logo-card { width: 260px; height: 83px; margin-top: 22px; background: #fff;
             border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.logo-card img { width: 213px; display: block; }
.tagline { margin-top: 17px; color: SKY; font-size: 12.5px; font-weight: 700;
           letter-spacing: .19em; text-transform: uppercase; }
.accent { position: absolute; left: 0; bottom: 0; width: 33%; height: 8px; background: RED; }

/* ---------- body ---------- */
.body { flex: 1; min-height: 0; display: flex; flex-direction: column;
        align-items: center; padding: 0 46px; text-align: center; }
/* only the spacers may absorb slack - real content keeps its natural height so
   that too much of it overflows visibly instead of being silently clipped */
.body > *:not(.spacer) { flex-shrink: 0; }
.kicker { margin-top: 26px; background: RED; color: #fff; font-size: 13.5px;
          font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
          padding: 8px 21px; border-radius: 6px; }
h1 { margin-top: 19px; color: NAVY; font-size: 58px; font-weight: 700;
     line-height: .96; letter-spacing: -.5px; }
h1.tight { font-size: 52px; }
h2 { margin-top: 8px; color: #111; font-size: 28px; font-weight: 700; letter-spacing: -.2px; }
.lede { margin-top: 13px; color: #525252; font-size: 18.5px; font-weight: 700; line-height: 1.3; }

/* ---------- info card ---------- */
.card { width: 724px; border: 1px solid #eaedf2; border-radius: 12px;
        background: #fff; overflow: hidden; text-align: left; }
.row { display: flex; align-items: center; gap: 21px; padding: 15px 28px;
       border-top: 1px solid #eaedf2; }
.row:first-child { border-top: 0; }
.badge-ic { width: 47px; height: 47px; flex: none; border-radius: 50%;
            background: #ecf0f8; display: flex; align-items: center; justify-content: center; }
.label { color: #8a9099; font-size: 12px; font-weight: 700; letter-spacing: .11em;
         text-transform: uppercase; }
.value { margin-top: 3px; color: #1a1a1a; font-size: 21px; font-weight: 700; line-height: 1.2; }
.value.link a { color: NAVY; text-decoration: none; }
.detail { margin-top: 2px; color: #545454; font-size: 14.5px; line-height: 1.3; }

/* two-up (Newport) variant */
.cards { display: flex; gap: 24px; width: 724px; text-align: left; }
.cards .card { width: 350px; flex: 1; display: flex; flex-direction: column; }
.card-head { background: NAVY; color: #fff; font-size: 13px; font-weight: 700;
             letter-spacing: .13em; text-transform: uppercase; text-align: center;
             padding: 9px 6px; }
/* rows share the space evenly so both cards line up row-for-row */
.cards .row { flex: 1; }
.row.compact { gap: 13px; padding: 9px 17px; }
.row.compact .badge-ic { width: 38px; height: 38px; }
.row.compact .label { font-size: 10.5px; letter-spacing: .1em; }
.row.compact .value { font-size: 17.5px; margin-top: 2px; }
.row.compact .value.link { font-size: 16.5px; }
.row.compact .detail { font-size: 13px; }

/* ---------- banner ---------- */
.banner { width: 724px; background: NAVY; color: #fff; border-radius: 8px;
          font-size: 21px; font-weight: 700; text-align: center; padding: 13px 10px; }
.banner .gold { color: GOLD; }

/* ---------- partners + footer ---------- */
.partners { text-align: center; }
.partners-label { color: #8a9099; font-size: 12px; font-weight: 700;
                  letter-spacing: .16em; text-transform: uppercase; }
.partner-logos { margin-top: 16px; display: flex; align-items: center;
                 justify-content: center; gap: 37px; }
.partner-logos img { display: block; }
.footer { height: 49px; flex: none; background: NAVY; color: #fff; font-size: 16px;
          font-weight: 700; display: flex; align-items: center; justify-content: center; }
.footer .url { color: SKY; margin-left: 10px; }
.footer .url:before { content: "\\2022"; color: #fff; margin-right: 10px; }
.spacer { flex: 1; min-height: 14px; }
""".replace("NAVY", NAVY).replace("RED", RED).replace("SKY", SKY).replace("GOLD", GOLD)


def build(cfg):
    logo = data_uri(os.path.join(ASSETS, "lwv-newport-county.png"))

    if cfg.get("cards"):  # two-up layout
        blocks = []
        for c in cfg["cards"]:
            rows = "".join(row(i, 22, compact=True) for i in c["rows"])
            blocks.append(
                '<div class="card"><div class="card-head">%s</div>%s</div>'
                % (esc(c["head"]), rows)
            )
        body_card = '<div class="cards">%s</div>' % "".join(blocks)
    else:
        rows = "".join(row(i, 26) for i in cfg["rows"])
        body_card = '<div class="card">%s</div>' % rows

    h1_cls = " tight" if cfg.get("tight") else ""
    h1 = "<br>".join(esc(l) for l in cfg["title"])

    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>%(tab)s</title>
<style>%(css)s</style></head>
<body><div class="page">
  <div class="header">
    <div class="logo-card"><img src="%(logo)s" alt="League of Women Voters of Newport County"></div>
    <div class="tagline">Nonpartisan &bull; Informed &bull; Engaged</div>
    <div class="accent"></div>
  </div>
  <div class="body">
    <div class="kicker">%(kicker)s</div>
    <h1 class="%(h1cls)s">%(h1)s</h1>
    <h2>%(sub)s</h2>
    <div class="lede">%(lede)s</div>
    <div class="spacer" style="max-height:26px"></div>
    %(card)s
    <div class="spacer" style="max-height:20px"></div>
    <div class="banner">FREE &amp; open to the public &bull; <span class="gold">%(cta)s</span></div>
    <div class="spacer"></div>
    %(partners)s
    <div class="spacer" style="max-height:22px"></div>
  </div>
  <div class="footer">League of Women Voters of Newport County<span class="url">lwvnewportcounty.org</span></div>
</div></body></html>
""" % {
        "tab": esc(cfg["tab"]),
        "css": CSS,
        "logo": logo,
        "kicker": esc(cfg["kicker"]),
        "h1cls": h1_cls.strip(),
        "h1": h1,
        "sub": esc(cfg["subtitle"]),
        "lede": esc(cfg["lede"]),
        "card": body_card,
        "cta": esc(cfg.get("cta", "All voters welcome")),
        "partners": partner_strip(),
    }


def render(html_path, stem):
    pdf = os.path.join(OUT, stem + ".pdf")
    png = os.path.join(OUT, stem + ".png")
    common = [CHROME, "--headless", "--disable-gpu", "--no-sandbox",
              "--hide-scrollbars", "--force-color-profile=srgb",
              "--run-all-compositor-stages-before-draw",
              "--virtual-time-budget=6000"]
    subprocess.run(common + ["--no-pdf-header-footer", "--print-to-pdf=" + pdf,
                             "file://" + html_path], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(common + ["--screenshot=" + png, "--window-size=816,1056",
                             "--force-device-scale-factor=2",
                             "file://" + html_path], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pdf, png


def verify(html_paths):
    """Fail loudly if any flyer's content pushes the navy footer off the page.

    Everything between the header and the footer is flexible, so adding a row or
    a longer line silently squeezes the layout until the footer falls off the
    bottom of the sheet.  Playwright is optional; skip the check if absent.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("note: playwright not installed - skipping page-fit check")
        return True
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 816, "height": 1056})
        for path in html_paths:
            pg.goto("file://" + os.path.abspath(path))
            report = pg.evaluate("""() => {
              const body = document.querySelector('.body');
              const limit = body.getBoundingClientRect().bottom;
              const over = [...body.children]
                .filter(e => e.getBoundingClientRect().bottom > limit + 0.5)
                .map(e => e.className + ' by ' +
                     (e.getBoundingClientRect().bottom - limit).toFixed(0) + 'px');
              const foot = document.querySelector('.footer').getBoundingClientRect();
              const slack = [...body.querySelectorAll(':scope > .spacer')]
                .reduce((a, e) => a + e.getBoundingClientRect().height, 0);
              return {over, footBottom: foot.bottom, slack};
            }""")
            name = os.path.basename(path)
            if report["over"]:
                print("FAIL %s: clipped at the page edge - %s"
                      % (name, "; ".join(report["over"])))
                ok = False
            if abs(report["footBottom"] - 1056) > 1:
                print("FAIL %s: footer ends at %.1fpx, expected 1056"
                      % (name, report["footBottom"]))
                ok = False
            if ok and report["slack"] < 60:
                print("warn %s: only %.0fpx of flexible whitespace left"
                      % (name, report["slack"]))
        b.close()
    return ok


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(HERE, "forums.json")) as fh:
        forums = json.load(fh)
    pages = []
    for cfg in forums:
        stem = cfg["slug"]
        html_path = os.path.join(OUT, stem + ".html")
        with open(html_path, "w") as fh:
            fh.write(build(cfg))
        pdf, png = render(html_path, stem)
        pages.append(html_path)
        print("built %-42s %7d B pdf" % (stem, os.path.getsize(pdf)))
    if not verify(pages):
        sys.exit(1)


if __name__ == "__main__":
    main()
