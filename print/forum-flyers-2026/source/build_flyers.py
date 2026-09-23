#!/usr/bin/env python3
"""
Build the 2026 LWV Newport County candidate forum flyers (US Letter, 8.5 x 11 in).

The layout is a point-for-point rebuild of the Portsmouth Town Council flyer
(forum-portsmouth-town-council-2026-09-15.pdf, sent to the League on Sept 1).
That file was an HTML page printed by headless Chrome 141; every position,
size, color, radius and letter-spacing below was measured from it, so a new
town's flyer reads as the same series. See README.md for the one deliberate
addition: a QR code for the question form.

    python3 build_flyers.py               # every forum in FORUMS
    python3 build_flyers.py middletown    # only slugs containing "middletown"

Pipeline per forum:
    FORUMS entry -> self-contained HTML (fonts, logos, QR inlined) -> Chromium
    headless print-to-PDF -> ../<slug>.pdf, plus a 150 dpi PNG in ../proofs/.
Then it checks each PDF: one page, nothing overflowing the card, and (when
OpenCV is installed) the printed QR decodes back to the form URL.

Requires Python 3 with segno and pymupdf; opencv-python-headless is optional
(QR scan check). Chromium path comes from $CHROME, defaulting to the
Playwright build used for the palm cards.

All units are PostScript points (1/72 in). CSS "pt" maps 1:1 onto PDF
coordinates, which is what made measuring the original straightforward.
"""
import base64, html, os, pathlib, subprocess, sys

import segno

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                     # print/forum-flyers-2026/
ASSETS = HERE / "assets"
FONTS = HERE / "fonts"
BUILD = HERE / "build"                 # intermediate HTML (git-ignored)
PROOFS = ROOT / "proofs"
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

# Turn the QR code off globally here, or per forum with "qr": False.
QR_DEFAULT = True


# ------------------------------------------------------------------ copy deck
# One entry per flyer. Dates are checked against the weekday at build time.
# "title" is exactly two lines; the headline is sized for two.
# A *_sub line is optional; rows without one are shorter, same as the
# "Date & Time" row on the Portsmouth original.
FORUMS = [
    {
        "slug": "forum-middletown-town-council-2026-09-29",
        "town": "Middletown",
        "title": ["Town Council", "Candidates Forum"],
        "iso_date": "2026-09-29",
        "date": "Tuesday, September 29, 2026",
        "time": "6:30 &ndash; 8:00 PM",
        "location": "Middletown High School",
        "location_sub": None,
        "moderator": "John Marion",
        "moderator_sub": "Executive Director, Common Cause Rhode Island",
        "form": "https://forms.gle/AtmNKLZ4EfBSneZ66",
    },
    {
        "slug": "forum-tiverton-town-council-2026-10-07",
        "town": "Tiverton",
        "title": ["Town Council", "Candidates Forum"],
        "iso_date": "2026-10-07",
        "date": "Wednesday, October 7, 2026",
        "time": "6:30 &ndash; 8:00 PM",
        "location": "Tiverton High School",
        "location_sub": None,
        "moderator": "Scott Pickering",
        "moderator_sub": "Publisher, East Bay Media Group",
        "form": "https://forms.gle/vYepZb66P8nmq9816",
    },
    {
        # Two races at one forum. "Town Council & School Committee Candidates
        # Forum" won't fit two lines at the series headline size, so the
        # headline names the races and the red "Candidates Forum" label above
        # it carries the rest.
        "slug": "forum-little-compton-town-council-school-committee-2026-10-19",
        "town": "Little Compton",
        "title": ["Town Council &amp;", "School Committee"],
        "doc_title": "Little Compton Town Council & School Committee Candidates Forum",
        "iso_date": "2026-10-19",
        "date": "Monday, October 19, 2026",
        "time": "6:30 &ndash; 8:00 PM",
        "location": "Little Compton Community Center",
        "location_sub": None,
        "moderator": "Scott Pickering",
        "moderator_sub": "Publisher, East Bay Media Group",
        "form": "https://forms.gle/j7v9i4A8CP1tT9zw8",
    },
]

# Same five partners as the Portsmouth flyer, left to right, at the exact
# width x height (pt) each had there; the sizes balance the row by eye, so
# keep them fixed rather than letting the browser round auto widths.
PARTNERS = [
    ("chamber.png", "Greater Newport Chamber of Commerce", 53.25, 51.75),
    ("newport-this-week.png", "Newport This Week", 48.75, 21.0),
    ("east-bay-media.png", "East Bay Media Group", 50.25, 48.75),
    ("common-cause-ri.png", "Common Cause Rhode Island", 108.0, 30.75),
    ("aarp-ri.png", "AARP Rhode Island", 101.25, 38.25),
]


# -------------------------------------------------------------------- palette
NAVY = "#003D7B"      # header/footer bands, headline, icons, link
RED = "#D32F2F"       # "Candidates Forum" label, accent bar under the header
SKY = "#C1E3FB"       # header tagline, footer URL
GOLD = "#FBD44B"      # "All voters welcome"
LABEL = "#8A9099"     # small caps row labels, "Presented in partnership with"
INK = "#1A1A1A"       # row values
SUB = "#545454"       # row sub-lines
LEDE = "#525252"      # "Hear directly from the candidates..."
TOWN = "#111111"      # "Middletown, Rhode Island"
RULE = "#EAEDF2"      # card border and row dividers
ICON_BG = "#ECF0F8"   # circle behind each row icon

# Liberation Sans vertical metrics (hhea, per em). Used to put each line's
# baseline exactly where the original had it, whatever the line-height.
ASC, DESC = 0.9053, 0.2119


# Blink rounds font ascent/descent to whole CSS pixels when it lays out a
# line, so a computed baseline can land one pixel (0.75 pt) off. The +PX / -PX
# nudges in the CSS were found by diffing a Portsmouth rebuild against the
# original PDF; with them every text line lands within 0.01 pt.
PX = 0.75


def top_for(baseline, size, lh):
    """CSS top of a single-line box whose baseline must land on `baseline`."""
    return baseline - (lh - (ASC + DESC) * size) / 2 - ASC * size


# ----------------------------------------------------------------- geometry
# Everything below was measured off the Portsmouth PDF (see module docstring).
PAGE_W, PAGE_H = 612, 792
HEADER_H = 121.5
FOOTER_TOP, FOOTER_H = 755.25, 36.75
CARD_X, CARD_TOP, CARD_W, CARD_H = 34.5, 333.0, 543.0, 270.75
BORDER = 0.75
ROW_H_1LINE, ROW_H_2LINE = 57.75, 69.75   # row heights without / with a sub-line
ROW_PAD_X = 21.0                          # card edge -> icon circle, and card edge -> QR
QR_PAD_Y = 7.875                          # row edge -> QR, top and bottom


def b64(path, mime):
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


FONT_CSS = "".join(
    f"@font-face{{font-family:'Liberation Sans';font-style:normal;font-weight:{w};"
    f"font-display:block;src:url({b64(FONTS / f'liberation-sans-{w}.woff2', 'font/woff2')}) format('woff2');}}"
    for w in (400, 700)
)
LOGO = b64(ASSETS / "lwvnc-logo.png", "image/png")

# Lucide/Feather icons, the same set the original used (26 px, stroke 1.9).
ICONS = {
    "date": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "location": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "moderator": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "questions": ('<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>'
                  '<path d="M12 17h.01"/>'),
}


def icon(name):
    return (f'<svg class="icn" viewBox="0 0 24 24" fill="none" stroke="{NAVY}" stroke-width="1.9" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def qr_svg(url, size_pt):
    """Vector QR, no quiet zone drawn (the white card around it serves as one)."""
    q = segno.make(url, error="m", micro=False)
    n = q.symbol_size(border=0)[0]
    path = []
    for y, row in enumerate(q.matrix):
        x = 0
        while x < n:
            if row[x]:
                run = x
                while run < n and row[run]:
                    run += 1
                path.append(f"M{x} {y}h{run - x}v1h-{run - x}z")
                x = run
            else:
                x += 1
    return (f'<svg class="qr" viewBox="0 0 {n} {n}" width="{size_pt}pt" height="{size_pt}pt" '
            f'shape-rendering="crispEdges" role="img" aria-label="QR code: {html.escape(url)}">'
            f'<path fill="{NAVY}" d="{"".join(path)}"/></svg>'), q.version, n


def row_html(kind, label, value, sub=None, height=ROW_H_1LINE, extra=""):
    sub_html = f'<div class="sub">{sub}</div>' if sub else ""
    return (f'<div class="row" style="height:{height}pt">'
            f'<div class="dot">{icon(kind)}</div>'
            f'<div class="txt"><div class="lbl">{label}</div>'
            f'<div class="val">{value}</div>{sub_html}</div>{extra}</div>')


def build_html(f):
    use_qr = f.get("qr", QR_DEFAULT)
    short = f["form"].replace("https://", "")
    doc_title = f.get("doc_title") or html.unescape(f"{f['town']} {' '.join(f['title'])}")

    # Rows keep the original's heights; the last row takes whatever is left so
    # the card stays exactly the original's size and nothing below it moves.
    rows = [
        ("date", "DATE &amp; TIME", f"{f['date']} &bull; {f['time']}", None),
        ("location", "LOCATION", f["location"], f.get("location_sub")),
        ("moderator", "MODERATOR", f["moderator"], f.get("moderator_sub")),
    ]
    heights = [ROW_H_2LINE if r[3] else ROW_H_1LINE for r in rows]
    inner = CARD_H - 2 * BORDER - BORDER * 3          # three dividers between four rows
    last_h = round(inner - sum(heights), 3)
    if last_h < ROW_H_2LINE:
        sys.exit(f"{f['slug']}: rows don't fit the card ({last_h}pt left for the questions row)")

    qr_extra, qr_info = "", None
    if use_qr:
        qr_pt = round(last_h - 2 * QR_PAD_Y, 3)
        svg, ver, n = qr_svg(f["form"], qr_pt)
        qr_extra = f'<a class="qr-link" href="{html.escape(f["form"])}">{svg}</a>'
        qr_info = (qr_pt, ver, n)

    row_markup = "".join(row_html(k, lab, val, sub, h) for (k, lab, val, sub), h in zip(rows, heights))
    row_markup += row_html(
        "questions", "QUESTIONS FOR THE CANDIDATES?",
        f'<a class="link" href="{html.escape(f["form"])}">{html.escape(short)}</a>',
        "Submit your questions in advance", last_h, qr_extra)

    partners = "".join(
        f'<img src="{b64(ASSETS / "partners" / fn, "image/png")}" alt="{html.escape(alt)}" '
        f'style="width:{w}pt;height:{h}pt">'
        for fn, alt, w, h in PARTNERS)

    css = f"""
{FONT_CSS}
@page {{ size: 8.5in 11in; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {PAGE_W}pt; height: {PAGE_H}pt; background: #fff; }}
body {{ font-family: 'Liberation Sans', Arial, Helvetica, sans-serif; font-weight: 700; color: {INK};
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page {{ position: relative; width: {PAGE_W}pt; height: {PAGE_H}pt; overflow: hidden; }}
.abs {{ position: absolute; left: 0; width: {PAGE_W}pt; text-align: center; white-space: nowrap; }}
a {{ color: inherit; text-decoration: none; }}

/* header band: logo card, tagline, red accent bar along the bottom-left */
.hdr {{ position: absolute; left: 0; top: 0; width: {PAGE_W}pt; height: {HEADER_H}pt; background: {NAVY}; }}
.logo {{ position: absolute; left: 208.5pt; top: 16.5pt; width: 195pt; height: 62.25pt; background: #fff;
         border-radius: 7.5pt; display: flex; align-items: center; justify-content: center; }}
.logo img {{ width: 159.75pt; height: 42.75pt; display: block; }}
.tag {{ top: {top_for(99.79, 9.375, 11.25) + PX:.3f}pt; font-size: 9.375pt; line-height: 11.25pt;
        letter-spacing: .19em; color: {SKY}; }}
.bar {{ position: absolute; left: 0; top: 115.5pt; width: 33%; height: 6pt; background: {RED}; }}

/* red label + headline stack */
.pill-wrap {{ top: 141pt; line-height: 0; }}
.pill {{ display: inline-block; vertical-align: top; height: 23.25pt; line-height: 23.25pt; padding: 0 15.375pt;
         background: {RED}; color: #fff; border-radius: 4.5pt; font-size: 10.125pt; letter-spacing: .14em; }}
.h1 {{ top: {top_for(214.47, 43.5, 42):.3f}pt; font-size: 43.5pt; line-height: 42pt; letter-spacing: -.375pt;
       color: {NAVY}; }}
.town {{ top: {top_for(286.5, 21, 25.2) + PX:.3f}pt; font-size: 21pt; line-height: 25.2pt; letter-spacing: -.15pt;
         color: {TOWN}; }}
.lede {{ top: {top_for(314.96, 13.875, 16.65) + PX:.3f}pt; font-size: 13.875pt; line-height: 16.65pt; color: {LEDE}; }}

/* details card */
.card {{ position: absolute; left: {CARD_X}pt; top: {CARD_TOP}pt; width: {CARD_W}pt; height: {CARD_H}pt;
         border: {BORDER}pt solid {RULE}; border-radius: 9pt; background: #fff; overflow: hidden; }}
.row {{ display: flex; align-items: center; padding: 0 {ROW_PAD_X}pt; }}
.row + .row {{ border-top: {BORDER}pt solid {RULE}; box-sizing: content-box; }}
.dot {{ flex: none; width: 35.25pt; height: 35.25pt; border-radius: 50%; background: {ICON_BG};
        display: flex; align-items: center; justify-content: center; margin-right: 15.75pt; }}
.icn {{ width: 19.5pt; height: 19.5pt; display: block; }}
.txt {{ flex: 1; white-space: nowrap; }}
.lbl {{ font-size: 9pt; line-height: 10.8pt; letter-spacing: .11em; color: {LABEL};
        margin-bottom: 2.31pt; }}
/* -PX margin + PX padding lifts the value one pixel without moving the sub-line or
   changing paint order (a relative offset would reorder the PDF text layer) */
.val {{ margin-top: -{PX}pt; padding-bottom: {PX}pt; font-size: 15.75pt; line-height: 18.9pt; color: {INK}; }}
.val .link {{ color: {NAVY}; }}
.sub {{ font-size: 10.875pt; line-height: 13.05pt; font-weight: 400; color: {SUB}; margin-top: 1.95pt; }}
.qr-link {{ flex: none; display: block; line-height: 0; }}
.qr {{ display: block; }}

/* bottom stack: banner, partners, footer band */
.banner {{ position: absolute; left: {CARD_X}pt; top: 617.25pt; width: {CARD_W}pt; height: 37.5pt;
           line-height: 37.5pt; border-radius: 6pt; background: {NAVY}; color: #fff; font-size: 15.75pt;
           text-align: center; white-space: nowrap; }}
.gold {{ color: {GOLD}; }}
.with {{ top: {top_for(675.75, 9, 10.8):.3f}pt; font-size: 9pt; line-height: 10.8pt; letter-spacing: .16em;
         color: {LABEL}; }}
.logos {{ position: absolute; left: 0; top: 690pt; width: {PAGE_W}pt; height: 51.75pt; display: flex;
          align-items: center; justify-content: center; gap: 27.75pt; }}
.logos img {{ display: block; }}
.ftr {{ position: absolute; left: 0; top: {FOOTER_TOP}pt; width: {PAGE_W}pt; height: {FOOTER_H}pt;
        line-height: {FOOTER_H}pt; background: {NAVY}; color: #fff; font-size: 12pt; text-align: center;
        white-space: nowrap; }}
.ftr .sep {{ margin: 0 7.5pt; }}
.ftr a {{ color: {SKY}; }}
"""

    body = f"""
<div class="page">
  <div class="hdr">
    <div class="logo"><img src="{LOGO}" alt="League of Women Voters of Newport County"></div>
    <div class="abs tag">NONPARTISAN &bull; INFORMED &bull; ENGAGED</div>
    <div class="bar"></div>
  </div>
  <div class="abs pill-wrap"><span class="pill">CANDIDATES FORUM</span></div>
  <h1 class="abs h1">{f['title'][0]}<br>{f['title'][1]}</h1>
  <div class="abs town">{f['town']}, Rhode Island</div>
  <div class="abs lede">Hear directly from the candidates before you vote in the November 3 election.</div>
  <div class="card">{row_markup}</div>
  <div class="banner">FREE &amp; open to the public &bull; <span class="gold">All voters welcome</span></div>
  <div class="abs with">PRESENTED IN PARTNERSHIP WITH</div>
  <div class="logos">{partners}</div>
  <div class="ftr">League of Women Voters of Newport County<span class="sep">&bull;</span><a href="https://lwvnewportcounty.org">lwvnewportcounty.org</a></div>
</div>"""
    page = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<title>{html.escape(doc_title)}</title><style>{css}</style></head><body>{body}</body></html>\n')
    return page, qr_info


# -------------------------------------------------------------------- render
def render_pdf(html_path, pdf_path):
    subprocess.run(
        [CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         "--disable-dev-shm-usage", "--font-render-hinting=none", "--virtual-time-budget=10000",
         "--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={pdf_path}",
         html_path.as_uri()],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def check_pdf(f, pdf_path, png_path):
    """Fail loudly on the mistakes that would ruin a print run."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    problems = []
    if doc.page_count != 1:
        problems.append(f"{doc.page_count} pages (expected 1)")
    page = doc[0]
    if (round(page.rect.width), round(page.rect.height)) != (PAGE_W, PAGE_H):
        problems.append(f"page is {page.rect.width}x{page.rect.height}pt, not 8.5x11in")
    fonts = {fn[3] for fn in page.get_fonts()}
    if not all("LiberationSans" in fn for fn in fonts):
        problems.append(f"unexpected fonts {sorted(fonts)}")

    # The QR prints as one navy vector path; find it by shape rather than
    # trusting the layout math, so a layout slip can't hide from the check.
    qr_box = None
    if f.get("qr", QR_DEFAULT):
        navy = tuple(int(NAVY[i:i + 2], 16) / 255 for i in (1, 3, 5))
        for d in page.get_drawings():
            r, fill = d["rect"], d.get("fill")
            if fill and max(abs(a - b) for a, b in zip(fill, navy)) < 0.01 \
                    and r.width > 36 and abs(r.width - r.height) < 0.5 and r.y0 > CARD_TOP:
                qr_box = r
        if qr_box is None:
            problems.append("QR code not found on the page")

    # Text must stay inside the card's side margins and clear of the QR.
    for b in page.get_text("dict")["blocks"]:
        for line in b.get("lines", []):
            for s in line["spans"]:
                if not s["text"].strip():
                    continue
                bb = pymupdf.Rect(s["bbox"])
                if bb.x0 < CARD_X - 0.5 or bb.x1 > CARD_X + CARD_W + 0.5:
                    problems.append(f"text runs past the margins: {s['text']!r}")
                if qr_box is not None and bb.intersects(qr_box + (-6, -6, 6, 6)):
                    problems.append(f"text too close to the QR code: {s['text']!r}")

    page.get_pixmap(dpi=150).save(png_path)

    # Scan the QR the way a phone would see a print: 300 dpi, with the
    # surrounding white as quiet zone, and require the exact form URL back.
    if qr_box is not None:
        try:
            import cv2, numpy as np
            pix = page.get_pixmap(dpi=300, clip=qr_box + (-16, -16, 16, 16))
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)[:, :, :3]
            data, _, _ = cv2.QRCodeDetector().detectAndDecode(np.ascontiguousarray(img[:, :, ::-1]))
            if data != f["form"]:
                problems.append(f"QR decodes to {data!r}, expected {f['form']!r}")
            else:
                print(f"    QR scan check: OK -> {data}")
        except ImportError:
            print("    QR scan check skipped (pip install opencv-python-headless numpy to enable)")
    return problems


def main(argv):
    import datetime
    picks = [f for f in FORUMS if not argv or any(a in f["slug"] for a in argv)]
    if not picks:
        sys.exit(f"no forum slug matches {argv}")
    BUILD.mkdir(exist_ok=True)
    PROOFS.mkdir(exist_ok=True)
    failed = False
    for f in picks:
        # Guard against a date typed with the wrong weekday.
        weekday = datetime.date.fromisoformat(f["iso_date"]).strftime("%A")
        if not f["date"].startswith(weekday + ","):
            sys.exit(f"{f['slug']}: {f['iso_date']} is a {weekday}, but the copy says {f['date']!r}")
        page, qr_info = build_html(f)
        if qr_info:
            f["qr_pt"] = qr_info[0]
        html_path = BUILD / f"{f['slug']}.html"
        html_path.write_text(page, encoding="utf-8")
        pdf_path = ROOT / f"{f['slug']}.pdf"
        render_pdf(html_path, pdf_path)
        qr_note = (f"QR {qr_info[0]}pt ({qr_info[0] / 72:.2f} in), version {qr_info[1]}, "
                   f"{qr_info[2]} modules" if qr_info else "no QR")
        print(f"built {pdf_path.name} ({pdf_path.stat().st_size:,} bytes; {qr_note})")
        problems = check_pdf(f, pdf_path, PROOFS / f"{f['slug']}.png")
        for p in problems:
            print(f"    PROBLEM: {p}")
        failed |= bool(problems)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
