#!/usr/bin/env python3
"""
Build print-ready HTML for the LWV Newport County "Make a Voting Plan" palm card.

Everything (fonts, logo, photo, QR) is inlined as base64/SVG so the single HTML
file is self-contained and Chromium can render it straight to PDF with all
fonts embedded.

Geometry model (all inches):
  artwork box = trim + 2*BLEED          <- what actually gets printed edge to edge
  page        = artwork + 2*MARK_MARGIN <- only in press mode, gives room for crop marks
  gold band   = GOLD_BAND visible inside the trim line, bleeding off the edge

Copy lives in STRINGS, keyed by language. Spanish runs 15-25% longer than
English at the same point size, so each language also carries a TUNE table of
type sizes; the Spanish values are pulled down only where the longer strings
would otherwise wrap or crowd. Everything else is shared, so the two languages
stay visually identical.
"""
import base64, pathlib, re, sys

HERE = pathlib.Path(__file__).parent
ASSETS = HERE / "assets"
FONTS = HERE / "fonts"
OUT = HERE / "build"
OUT.mkdir(exist_ok=True)

BLEED = 0.125        # industry standard bleed
MARK_MARGIN = 0.25   # room outside the bleed for crop marks
GOLD_BAND = 0.095    # gold frame width visible inside the trim edge

NAVY = "#0D0363"
RED = "#BE0F34"
GOLD_HAIR = "#C9A24A"


def b64(path, mime):
    return f"data:{mime};base64," + base64.b64encode(pathlib.Path(path).read_bytes()).decode()


def font_face(family, weight, style, filename):
    return (
        f"@font-face{{font-family:'{family}';font-style:{style};font-weight:{weight};"
        f"font-display:block;src:url({b64(FONTS/filename,'font/woff2')}) format('woff2');}}"
    )


FONT_CSS = "".join([
    font_face("Montserrat", 500, "normal", "mont-500.woff2"),
    font_face("Montserrat", 600, "normal", "mont-600.woff2"),
    font_face("Montserrat", 700, "normal", "mont-700.woff2"),
    font_face("Montserrat", 800, "normal", "mont-800.woff2"),
    font_face("Lato", 400, "normal", "lato-400.woff2"),
    font_face("Lato", 400, "italic", "lato-400i.woff2"),
    font_face("Lato", 700, "normal", "lato-700.woff2"),
    font_face("Lato", 900, "normal", "lato-900.woff2"),
])

LOGO_NC = b64(ASSETS / "lwvnc-logo.png", "image/png")
LWV_MARK = b64(ASSETS / "lwv-mark.png", "image/png")
PHOTO = b64(ASSETS / "photo-flag.png", "image/png")
_qr = (ASSETS / "qr-sos.svg").read_text().split("?>", 1)[1].strip()
_m = re.search(r'width="(\d+)"\s+height="(\d+)"', _qr)
# give it a viewBox so the code scales instead of cropping
QR_SVG = _qr.replace("<svg ", f'<svg viewBox="0 0 {_m.group(1)} {_m.group(2)}" ', 1)


# ------------------------------------------------------------------- copy deck
# The QR destination is the same in both languages: vote.sos.ri.gov carries its
# own language selector, so a Spanish reader lands on the same site and switches
# there rather than needing a separate short link on the card.
STRINGS = {
    "en": {
        "html_lang": "en",
        "s1_title": "Make a Voting Plan",
        "plan": [
            "Check your registration.",
            "Decide how you will vote.",
            "Find your polling place.",
            "Review your ballot.",
            "Learn about the candidates and issues.",
            "Follow through. &nbsp;Cast your vote.",
        ],
        "vic": "Your Voter Information Center",
        "sos": "RI Secretary of State",
        "fund": "This card is funded by the League of Women Voters RI Education Fund",
        "s2_title": "3 Ways to Vote in RI in 2026",
        "icon_day": ["Election", "Day"],
        "icon_mail": ["Ballot-By-", "Mail"],
        "icon_early": ["Early", "Voting"],
        "election": "General Election &ndash; November 3, 2026",
        "dates": [
            ("October&nbsp;4", "Voter Registration Deadline"),
            ("October&nbsp;13", "Mail Ballot Application Deadline"),
            ("October&nbsp;14&nbsp;&ndash;&nbsp;Nov.&nbsp;2", "Early Voting at Town Halls"),
        ],
        "id_title": "Bring a Valid Photo ID",
        "id_note": ("IDs must be valid and not have expired more than six&nbsp;(6)&nbsp;months "
                    "prior to voting, but do not need your current address."),
        "ids": [
            "RI Driver&rsquo;s License or permit, or U.S. Passport",
            "U.S. Military ID or government-issued medical card",
            "ID issued by a U.S. educational institution",
            "United States or Rhode Island ID card",
        ],
        "tune": {},
    },
    "es": {
        "html_lang": "es",
        "s1_title": "Haga su plan para votar",
        "plan": [
            "Verifique su registro de votante.",
            "Decida c&oacute;mo va a votar.",
            "Encuentre su lugar de votaci&oacute;n.",
            "Revise su boleta electoral.",
            "Inf&oacute;rmese sobre los candidatos y los temas.",
            "Cumpla con su plan. &nbsp;&iexcl;Emita su voto!",
        ],
        "vic": "Su Centro de Informaci&oacute;n para Votantes",
        "sos": "Secretario de Estado de RI",
        "fund": ("Esta tarjeta est&aacute; financiada por el Fondo Educativo de la "
                 "Liga de Mujeres Votantes de RI"),
        "s2_title": "3 maneras de votar en RI en 2026",
        "icon_day": ["D&#237;a de la", "Elecci&#243;n"],
        "icon_mail": ["Boleta por", "Correo"],
        "icon_early": ["Votaci&#243;n", "Anticipada"],
        "election": "Elecci&oacute;n General &ndash; 3 de noviembre de 2026",
        "dates": [
            ("4&nbsp;de&nbsp;octubre", "Fecha l&iacute;mite para registrarse"),
            ("13&nbsp;de&nbsp;octubre", "Fecha l&iacute;mite para solicitar boleta por correo"),
            ("14&nbsp;de&nbsp;oct.&nbsp;&ndash;&nbsp;2&nbsp;de&nbsp;nov.",
             "Votaci&oacute;n anticipada en los ayuntamientos"),
        ],
        "id_title": "Traiga una identificaci&oacute;n v&aacute;lida con foto",
        "id_note": ("La identificaci&oacute;n debe ser v&aacute;lida y no haber vencido hace "
                    "m&aacute;s de seis&nbsp;(6)&nbsp;meses. No necesita mostrar su "
                    "direcci&oacute;n&nbsp;actual."),
        "ids": [
            "Licencia o permiso de conducir de RI, o pasaporte de EE.&nbsp;UU.",
            "Identificaci&oacute;n militar de EE.&nbsp;UU. o tarjeta m&eacute;dica del gobierno",
            "Identificaci&oacute;n de una instituci&oacute;n educativa de EE.&nbsp;UU.",
            "Tarjeta de identificaci&oacute;n de los Estados Unidos o de Rhode Island",
        ],
        # Only the strings that outgrow their box get pulled down.
        "tune": {
            "h1_s1": 2.42,      # "Haga su plan para votar" is 5 characters longer
            "h1_s2": 2.06,      # "3 maneras de votar en RI en 2026" nearly fills the width
            "vic": 0.95,        # must still clear the logo on the same footer row
            "h2": 1.30,
            "dates": 0.98,
            "id_note": 0.86,
            "ids": 0.90,
            "fund": 0.72,
            "icon_fs": 11.0,    # two-line captions inside a fixed icon panel
            "icon_fs_mail": 11.0,
            "cal_x": 13, "cal_w": 74,   # "Anticipada" needs a wider calendar body
        },
    },
}

# Defaults every language starts from; a language's "tune" overrides these.
TUNE_BASE = {
    "h1_s1": 2.62, "h1_s2": 2.30, "list": 1.29, "vic": 1.12, "h2": 1.46,
    "dates": 1.05, "id_note": 0.92, "ids": 0.97, "fund": 0.80,
    "icon_fs": 13.2, "icon_fs_mail": 12.4, "cal_x": 17, "cal_w": 66,
}


# ---------------------------------------------------------------- vector icons
# Rebuilt from the source bitmaps (172 px) as SVG so they stay sharp at 300 dpi.
def icon_election_day(L, T):
    a, b = L["icon_day"]
    return f"""
<svg viewBox="0 0 100 100" class="icn">
  <rect width="100" height="100" fill="#0C0064"/>
  <!-- ballot slip with red check badge, entering the slot -->
  <rect x="34" y="12" width="32" height="26" fill="#fff"/>
  <rect x="34" y="12" width="32" height="12" fill="#BE0F34"/>
  <circle cx="50" cy="21" r="7.2" fill="#fff"/>
  <path d="M46.3 21.2l2.9 2.9 5.1-5.6" fill="none" stroke="#BE0F34"
        stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
  <!-- box body: tapered bin -->
  <path d="M18 46h64l-5 42H23z" fill="#fff"/>
  <!-- lid + slot -->
  <path d="M15 38h70v9H15z" fill="#fff"/>
  <rect x="36" y="41" width="28" height="3.4" rx="1.7" fill="#0C0064"/>
  <text x="50" y="62" class="ic-t" style="font-size:{T['icon_fs']}px">{a}</text>
  <text x="50" y="77" class="ic-t" style="font-size:{T['icon_fs']}px">{b}</text>
</svg>"""


def icon_mail(L, T):
    a, b = L["icon_mail"]
    return f"""
<svg viewBox="0 0 100 100" class="icn">
  <rect width="100" height="100" fill="#0C0064"/>
  <!-- ballot sheet rising out of the envelope -->
  <path d="M33 8h26l9 9v33H33z" fill="#4A7FC1"/>
  <path d="M59 8l9 9h-9z" fill="#2E5C96"/>
  <g fill="#fff">
    <rect x="38" y="18" width="25" height="2.8"/><rect x="38" y="24" width="25" height="2.8"/>
    <rect x="38" y="30" width="25" height="2.8"/><rect x="38" y="36" width="25" height="2.8"/>
    <rect x="38" y="42" width="16" height="2.8"/>
  </g>
  <!-- envelope: open flaps left and right -->
  <path d="M10 44l24 16-24 16z" fill="#BE0F34"/>
  <path d="M90 44L66 60l24 16z" fill="#BE0F34"/>
  <path d="M10 44l40 26 40-26v4L50 76 10 48z" fill="#8E0B26"/>
  <!-- white label panel carrying the caption -->
  <rect x="10" y="58" width="80" height="32" fill="#fff"/>
  <text x="50" y="70" class="ic-t" style="font-size:{T['icon_fs_mail']}px">{a}</text>
  <text x="50" y="84" class="ic-t" style="font-size:{T['icon_fs_mail']}px">{b}</text>
</svg>"""


def icon_early(L, T):
    a, b = L["icon_early"]
    return f"""
<svg viewBox="0 0 100 100" class="icn">
  <rect width="100" height="100" fill="#0C0064"/>
  <!-- spiral binding -->
  <g fill="none" stroke="#BE0F34" stroke-width="5" stroke-linecap="round">
    <path d="M30 20a5.5 5.5 0 0 1 11 0v10"/>
    <path d="M45 20a5.5 5.5 0 0 1 11 0v10"/>
    <path d="M60 20a5.5 5.5 0 0 1 11 0v10"/>
  </g>
  <!-- calendar head + body -->
  <rect x="{T['cal_x']}" y="24" width="{T['cal_w']}" height="16" fill="#BE0F34"/>
  <rect x="{T['cal_x']}" y="40" width="{T['cal_w']}" height="44" fill="#fff"/>
  <text x="50" y="58" class="ic-t" style="font-size:{T['icon_fs']}px">{a}</text>
  <text x="50" y="74" class="ic-t" style="font-size:{T['icon_fs']}px">{b}</text>
</svg>"""


# ---------------------------------------------------------------------- markup
def side_one(L):
    items = "".join(f"      <li>{t}</li>\n" for t in L["plan"])
    return f"""
<div class="inner side1">
  <div class="s1top">
    <h1>{L['s1_title']}</h1>
    <img class="photo" src="{PHOTO}" alt="">
    <ol class="plan">
{items}    </ol>
  </div>
  <div class="s1foot">
    <div class="vic">
      <div class="vic-h">{L['vic']}</div>
      <div class="qr">{QR_SVG}</div>
      <div class="vic-h">{L['sos']}</div>
    </div>
    <img class="nclogo" src="{LOGO_NC}" alt="League of Women Voters of Newport County">
  </div>
  <div class="fund">{L['fund']}</div>
</div>"""


def side_two(L, T):
    dates = "".join(f"    <li><b>{d}</b><span>{t}</span></li>\n" for d, t in L["dates"])
    ids = "".join(f"    <li>{t}</li>\n" for t in L["ids"])
    return f"""
<div class="inner side2">
  <h1>{L['s2_title']}</h1>
  <div class="icons">
    <div class="icw">{icon_election_day(L, T)}</div>
    <div class="icw">{icon_mail(L, T)}</div>
    <div class="icw">{icon_early(L, T)}</div>
  </div>

  <h2>{L['election']}</h2>
  <ul class="dates">
{dates}  </ul>

  <h2 class="id-h">{L['id_title']}</h2>
  <p class="idnote">{L['id_note']}</p>
  <ul class="ids">
{ids}  </ul>
  <img class="mark" src="{LWV_MARK}" alt="League of Women Voters">
</div>"""


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}
@page{margin:0;size:%(pw).4fin %(ph).4fin}

.page{width:%(pw).4fin;height:%(ph).4fin;position:relative;overflow:hidden;
      display:flex;align-items:center;justify-content:center;page-break-after:always}
.page:last-child{page-break-after:auto}

/* artwork = trim + bleed on all four sides */
.card{width:%(aw).4fin;height:%(ah).4fin;position:relative;overflow:hidden;
      font-family:'Lato',sans-serif;color:%(navy)s;
      font-size:%(base).4fin;line-height:1.2;
      background:linear-gradient(128deg,#F3E3B0 0%%,#C9A15C 18%%,#EBD79C 37%%,
                 #B98B4A 55%%,#E4CE8C 74%%,#C29553 88%%,#F0DFAC 100%%)}
/* white field: bleed + gold band in from the artwork edge */
.field{position:absolute;inset:%(field).4fin;background:#fff}
/* hairline gold rule inside the white field */
.inner{position:absolute;inset:%(hair).4fin;border:%(hairw).4fin solid %(gold)s;
       padding:%(pad).4fin %(padx).4fin;display:flex;flex-direction:column}

h1{font-family:'Montserrat',sans-serif;font-weight:800;text-align:center;
   letter-spacing:-.005em;color:%(navy)s}

/* ---------------- side 1 ---------------- */
.s1top{display:flow-root}
.side1 h1{font-size:%(h1_s1).3fem;line-height:1.02;margin-bottom:.34em}
.photo{float:right;width:%(photow).4fin;height:auto;margin:.10em 0 .34em .85em}
.plan{list-style:none;counter-reset:step;font-family:'Montserrat',sans-serif;
      font-weight:700;font-size:%(list).3fem;line-height:1.72;margin-left:.30em}
.plan li{counter-increment:step;position:relative;padding-left:1.28em}
.plan li::before{content:counter(step) ".";position:absolute;left:0;font-weight:600}
/* Items 1-4 sit beside the photo; 5 onward run full width. Clearing explicitly
   keeps the long items off the float instead of relying on the line box
   happening to land below it, which the longer Spanish strings do not. */
.plan li:nth-child(n+5){clear:right}

.s1foot{clear:both;display:flex;align-items:flex-end;justify-content:space-between;
        gap:.6em;margin-top:auto}
.vic{text-align:center}
.vic-h{font-family:'Montserrat',sans-serif;font-weight:700;color:%(red)s;
       font-size:%(vic).3fem;line-height:1.25;white-space:nowrap}
.qr{margin:.34em auto .26em;width:%(qr).4fin;height:%(qr).4fin}
.qr svg{width:100%%;height:100%%;display:block}
.nclogo{width:%(nclogo).4fin;height:auto;margin-bottom:.18em}
.fund{font-family:'Lato',sans-serif;font-style:italic;font-size:%(fund).3fem;
      text-align:center;color:#111;margin-top:.34em}

/* ---------------- side 2 ---------------- */
.side2{padding-top:%(pad2).4fin}
.side2 h1{font-size:%(h1_s2).3fem;line-height:1.04;margin-bottom:.22em}
.icons{display:flex;justify-content:center;gap:%(icgap).4fin;margin:0 0 .30em}
.icw{width:%(icon).4fin;height:%(icon).4fin}
.icn{width:100%%;height:100%%;display:block}
.ic-t{font-family:'Montserrat',sans-serif;font-weight:700;
      fill:#0C0064;text-anchor:middle}

.side2 h2{font-family:'Montserrat',sans-serif;font-weight:700;font-size:%(h2).3fem;
          line-height:1.2;color:%(navy)s;margin-bottom:.16em}
.id-h{margin-top:.40em}

.dates{list-style:none;font-size:%(dates).3fem;line-height:1.34;margin-left:.45em}
.dates li{display:flex;align-items:baseline;gap:.5em;padding-left:.85em;position:relative}
.dates li::before{content:"";position:absolute;left:0;top:.50em;
                  width:.30em;height:.30em;border-radius:50%%;background:%(navy)s}
.dates b{font-weight:900;white-space:nowrap}
.dates span{font-weight:400}

.idnote{font-size:%(id_note).3fem;line-height:1.30;margin:0 0 .20em}
.ids{list-style:none;font-size:%(ids).3fem;line-height:1.30;margin-left:.45em}
.ids li{padding-left:.85em;position:relative;margin-bottom:.05em}
.ids li::before{content:"";position:absolute;left:0;top:.52em;
                width:.26em;height:.26em;border-radius:50%%;background:%(navy)s}
.mark{position:absolute;right:%(padx).4fin;bottom:%(pad).4fin;width:%(mark).4fin;height:auto}

/* ---------------- crop marks (press build only) ---------------- */
.cm{position:absolute;background:#000}
.cm.h{height:%(cmw).4fin;width:%(cml).4fin}
.cm.v{width:%(cmw).4fin;height:%(cml).4fin}
"""


def crop_marks(pw, ph, trim_w, trim_h):
    """L-shaped marks sitting on the trim lines, in the margin outside the bleed."""
    lx = (pw - trim_w) / 2.0          # left trim line
    rx = lx + trim_w                  # right trim line
    ty = (ph - trim_h) / 2.0          # top trim line
    by = ty + trim_h                  # bottom trim line
    gap = BLEED + 0.03                # start marks just outside the bleed box
    ln = MARK_MARGIN - 0.06           # mark length
    w = 0.0055                        # ~0.4 pt hairline
    d = []
    for x in (lx, rx):
        d.append(f'<div class="cm v" style="left:{x-w/2:.4f}in;top:{ty-gap-ln:.4f}in"></div>')
        d.append(f'<div class="cm v" style="left:{x-w/2:.4f}in;top:{by+gap:.4f}in"></div>')
    for y in (ty, by):
        d.append(f'<div class="cm h" style="top:{y-w/2:.4f}in;left:{lx-gap-ln:.4f}in"></div>')
        d.append(f'<div class="cm h" style="top:{y-w/2:.4f}in;left:{rx+gap:.4f}in"></div>')
    return "".join(d)


def build(trim_w, trim_h, press, label, lang="en"):
    L = STRINGS[lang]
    T = {**TUNE_BASE, **L["tune"]}

    bleed = BLEED if press else 0.0
    aw, ah = trim_w + 2 * bleed, trim_h + 2 * bleed
    pw = aw + (2 * MARK_MARGIN if press else 0.0)
    ph = ah + (2 * MARK_MARGIN if press else 0.0)

    base = trim_w / 47.0                     # typographic unit scales with card width
    field = bleed + GOLD_BAND                # white field inset from artwork edge
    hair = trim_w * 0.0095                   # gap between gold band and hairline rule

    css = CSS % dict(
        pw=pw, ph=ph, aw=aw, ah=ah, base=base, navy=NAVY, red=RED, gold=GOLD_HAIR,
        field=field, hair=hair, hairw=max(trim_w * 0.0022, 0.010),
        pad=trim_w * 0.027, padx=trim_w * 0.040, pad2=trim_w * 0.026,
        qr=trim_w * 0.118, nclogo=trim_w * 0.330, photow=trim_w * 0.268,
        mark=trim_w * 0.105, icon=trim_w * 0.148, icgap=trim_w * 0.083,
        cmw=0.0055, cml=MARK_MARGIN - 0.06, **T,
    )

    marks = (crop_marks(pw, ph, trim_w, trim_h) if press else "")
    pages = "".join(
        f'<div class="page"><div class="card">'
        f'<div class="field"></div>{body}</div>{marks}</div>'
        for body in (side_one(L), side_two(L, T))
    )

    html = (f"<!doctype html><html lang=\"{L['html_lang']}\"><head><meta charset=utf-8>"
            f"<title>LWVNC Palm Card {label}</title>"
            f"<style>{FONT_CSS}{css}</style></head><body>{pages}</body></html>")

    path = OUT / f"card-{label}.html"
    path.write_text(html)
    print(f"{path.name}  page {pw:.3f}x{ph:.3f}in  trim {trim_w}x{trim_h}in  "
          f"bleed {bleed}in  lang {lang}  {len(html)/1024:.0f}KB")
    return path


if __name__ == "__main__":
    langs = sys.argv[1:] or list(STRINGS)
    for lang in langs:
        suffix = "" if lang == "en" else f"-{lang}"
        for w, h, tag in [(6.0, 4.0, "6x4"), (8.5, 5.5, "8.5x5.5")]:
            build(w, h, press=True, label=f"{tag}{suffix}-press", lang=lang)
            build(w, h, press=False, label=f"{tag}{suffix}-proof", lang=lang)
