# "Make a Voting Plan" Palm Card — 2026 General Election

Two-sided voter education palm card for the League of Women Voters of Newport County,
in English and Spanish. Rebuilt from the LWV South County card with the Newport County
logo and updated back copy.

## Which file goes to the printer

| File | Use |
| --- | --- |
| `LWVNC-voting-plan-card-6x4-PRESS.pdf` | **English — send this one.** 6" × 4" pocket card |
| `LWVNC-voting-plan-card-ES-6x4-PRESS.pdf` | **Spanish — send this one.** 6" × 4" pocket card |
| `LWVNC-voting-plan-card-8.5x5.5-PRESS.pdf` | English alternate: 8.5" × 5.5" half-sheet |
| `LWVNC-voting-plan-card-ES-8.5x5.5-PRESS.pdf` | Spanish alternate: 8.5" × 5.5" half-sheet |
| `*-PROOF.pdf` | Trim-size only, no marks — for review and email approval |
| `proofs/*.png` | 300 dpi flats for review, social, and email (`ES-` prefix = Spanish) |

Page 1 is the front, page 2 is the back. Both PRESS files are set up for
standard two-sided printing — tell the printer **head-to-head (long-edge flip)**
so the back reads right side up.

English and Spanish are separate cards, not a flip-side pair. Printing them as one
two-language card would mean four sides; if that's wanted, say so and the generator
can emit a four-page file instead.

## Specs

| | 6 × 4 | 8.5 × 5.5 |
| --- | --- | --- |
| Trim | 6.0 × 4.0 in | 8.5 × 5.5 in |
| Bleed | 0.125 in all sides | 0.125 in all sides |
| PDF page (press) | 6.75 × 4.75 in | 9.25 × 6.25 in |
| Safe margin | 0.125 in inside trim | 0.125 in inside trim |

- Crop marks sit on the trim line, offset outside the bleed box.
- The gold frame is a full-bleed element — it runs off all four edges by design,
  leaving roughly 0.095 in of gold visible inside the trim.
- All fonts are embedded and subset (Montserrat, Lato — both SIL Open Font License),
  including every accented Spanish glyph. The text layer is selectable and searchable.
- Colors are RGB. If the printer wants CMYK, they can convert on their end;
  flag the navy (`#0D0363`) so it doesn't shift muddy.

Suggested stock: 14 pt or 16 pt C2S cover, matte or satin finish.

## Colors

| Role | Hex |
| --- | --- |
| Navy (headlines, list, icons) | `#0D0363` |
| LWV red (accents, icon detail) | `#BE0F34` |
| Gold frame | gradient `#F3E3B0` → `#B98B4A` |
| Gold hairline rule | `#C9A24A` |

## QR code

Encodes `https://vote.sos.ri.gov/` — the RI Secretary of State Voter Information
Center — on both the English and Spanish cards. That site carries its own language
selector, so a Spanish reader lands there and switches rather than needing a
separate short link printed on the card.

This is the same destination as the QR on the original South County card; it was
decoded from that artwork and regenerated as vector so it prints sharp instead of
being a rescaled screenshot.

**Scan it off a printed proof before the full run.**

## Spanish translation notes

The translation uses formal *usted* throughout, which is the register US election
offices use for voter materials. Three word choices are judgment calls worth a
native-speaker review before a large run:

| Term | Used | Alternative |
| --- | --- | --- |
| Town Halls | *ayuntamientos* | *municipios*, *alcaldías* |
| RI Secretary of State | *Secretario de Estado de RI* | *Secretaría de Estado de RI* (the office rather than the officeholder) |
| League of Women Voters RI Education Fund | *Fondo Educativo de la Liga de Mujeres Votantes de RI* | keep the legal entity name in English if the League's compliance guidance requires it |

The LWV logo lockup stays in English on both cards — it is the registered
trademark artwork.

## Rebuilding

The layout is generated, not hand-placed, so sizes, copy, and languages are cheap
to change.

```bash
cd source
python3 build_card.py          # both languages
python3 build_card.py es       # one language
./render.sh                    # Chromium headless -> PDF
```

Copy lives in the `STRINGS` dict at the top of `build_card.py`, keyed by language.
Adding a language means adding one entry there; adding a trim size means adding a
`(width, height, "tag")` tuple at the bottom.

Spanish runs 15–25% longer than English at the same point size, so each language
also carries a `tune` table of type sizes that overrides `TUNE_BASE`. Only the
strings that would otherwise wrap or crowd are pulled down — everything else is
shared, so the two cards read as the same design.

Everything (fonts, logo, photo, QR) is inlined into the generated HTML, so each
file is self-contained. Requires Python 3 with `segno` and `pillow`, plus a
Chromium binary — override the `CHROME` path in `render.sh` if yours differs.
