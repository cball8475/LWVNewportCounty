# "Make a Voting Plan" Palm Card — 2026 General Election

Two-sided voter education palm card for the League of Women Voters of Newport County.
Rebuilt from the LWV South County card with the Newport County logo and updated back copy.

## Which file goes to the printer

| File | Use |
| --- | --- |
| `LWVNC-voting-plan-card-6x4-PRESS.pdf` | **Send this one.** 6" × 4" pocket card |
| `LWVNC-voting-plan-card-8.5x5.5-PRESS.pdf` | Alternate: 8.5" × 5.5" half-sheet handout |
| `*-PROOF.pdf` | Trim-size only, no marks — for review and email approval |
| `proofs/*.png` | 300 dpi flats for review, social, and email |

Page 1 is the front, page 2 is the back. Both PRESS files are set up for
standard two-sided printing — tell the printer **head-to-head (long-edge flip)**
so the back reads right side up.

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
- All fonts are embedded and subset (Montserrat, Lato — both SIL Open Font License).
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
Center. This is the same destination as the QR on the original South County card;
it was decoded from that artwork and regenerated as vector so it prints sharp
instead of being a rescaled screenshot.

**Scan it off a printed proof before the full run.**

## Rebuilding

The layout is generated, not hand-placed, so sizes and copy are cheap to change.

```bash
cd source
python3 build_card.py     # writes build/card-<size>-{press,proof}.html
./render.sh               # Chromium headless -> PDF
```

Trim sizes are the list at the bottom of `build_card.py`; add a
`(width, height, "tag")` tuple to get another size. Everything (fonts, logo,
photo, QR) is inlined into the HTML, so the generated file is self-contained.

Requires Python 3 with `segno` and `pillow`, plus a Chromium binary — set the
`CHROME` path at the top of `render.sh`.
