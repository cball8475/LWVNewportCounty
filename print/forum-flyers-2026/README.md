# 2026 Candidate Forum Flyers — Middletown, Tiverton, Little Compton

One-page flyers (8.5" × 11") for the League's fall 2026 town forums. They use the
same layout as the Portsmouth Town Council flyer
(`forum-portsmouth-town-council-2026-09-15.pdf`, emailed to the League on Sept 1),
so the whole series looks the same.

## Files

| File | Forum |
| --- | --- |
| `forum-middletown-town-council-2026-09-29.pdf` | Middletown Town Council — Tue 9/29, 6:30–8:00 PM, Middletown High School |
| `forum-tiverton-town-council-2026-10-07.pdf` | Tiverton Town Council — Wed 10/7, 6:30–8:00 PM, Tiverton High School |
| `forum-little-compton-town-council-school-committee-2026-10-19.pdf` | Little Compton Town Council & School Committee — Mon 10/19, 6:30–8:00 PM, Little Compton Community Center |
| `proofs/*.png` | 150 dpi images of each flyer, for email, texting, and social posts |

Each PDF is ready to print or email. The question-form link in the PDF is clickable.

## What's on each flyer

| | Middletown | Tiverton | Little Compton |
| --- | --- | --- | --- |
| Moderator | John Marion, Executive Director, Common Cause Rhode Island | Scott Pickering, Publisher, East Bay Media Group | Scott Pickering, Publisher, East Bay Media Group |
| Question form | forms.gle/AtmNKLZ4EfBSneZ66 | forms.gle/vYepZb66P8nmq9816 | forms.gle/j7v9i4A8CP1tT9zw8 |

All three form links were opened before printing, and each goes to the Google Form
for its own town. The forms' titles are "Middletown Town Council Forum", "Tiverton
Town Council Forum", and "Little Compton Town Council and School Committee".

## Differences from the Portsmouth flyer

- **QR code for the question form.** This is the one addition to the layout. It sits
  in the empty right side of the "Questions for the candidates?" row, so people
  don't have to type a 17-character link off a printed page. It prints just under
  1 in. square, and the build scans every code back to its form URL (see Checks).
  Scan a printed copy with a phone before a big run. To turn it off, set
  `QR_DEFAULT = False` in `source/build_flyers.py`, or add `"qr": False` to one forum.
- **Little Compton headline.** "Town Council & School Committee Candidates Forum" is
  too long for two lines at the series headline size. The headline reads
  "Town Council & / School Committee", and the red **CANDIDATES FORUM** label above
  it covers the rest. This keeps it the same size as the other towns' headlines.
- **Moderator title wording.** The request read "Executive Director Common Cause,
  RI". The flyer uses the organization's name as it appears on its logo:
  "Executive Director, Common Cause Rhode Island".
- **Location lines.** Portsmouth had a second location line ("Little Theatre").
  None of these three has one, so the location row is shorter. The question row
  takes up that space, which keeps the card and everything below it in the same
  place as on Portsmouth.

**Confirm before printing:** the partner strip still shows the same five logos as
Portsmouth: Greater Newport Chamber of Commerce, Newport This Week, East Bay Media
Group, Common Cause Rhode Island, and AARP Rhode Island. Check that all five are
partners on these three forums too. If not, delete that logo's line from `PARTNERS`
in the build script and rebuild. The row re-centers on its own.

## Specs

- Letter size, 612 × 792 pt, one page. No bleed, same as the Portsmouth original.
  The header and footer bands run to the page edge in the file, so an office printer
  leaves its normal white margin around them. For edge-to-edge color at a print
  shop, the generator needs a bleed added first.
- Font: Liberation Sans Regular and Bold (SIL Open Font License 1.1), embedded and
  subset. This is the same font as the Portsmouth PDF, which is why the letter
  shapes match.
- Colors are RGB:

| Role | Hex |
| --- | --- |
| Navy (bands, headline, icons, link, QR) | `#003D7B` |
| Red (label, accent bar) | `#D32F2F` |
| Light blue (header tagline, footer URL) | `#C1E3FB` |
| Gold ("All voters welcome") | `#FBD44B` |
| Gray labels | `#8A9099` |
| Card border and dividers | `#EAEDF2` |

## How it was matched to Portsmouth

Chrome printed the Portsmouth flyer from an HTML page, and that page's source didn't
survive, so the layout was measured from the PDF instead. The measurements covered
every text line's position and size, the corner radii, the letter-spacing, the icon
shapes, and the logo boxes. The partner logos were pulled out of the PDF at their
original resolution.

As a check, the generator rebuilt the Portsmouth flyer and compared it with the
original:

- Every text line landed within 0.01 pt of its original position.
- 0.05% of pixels differ. That difference is the four row icons, which sit about
  0.4 pt off where the original's pixel rounding put them.

## Rebuilding

```bash
cd source
python3 build_flyers.py              # all three
python3 build_flyers.py middletown   # one forum (any part of the file name works)
```

The copy for each flyer is in the `FORUMS` list at the top of `build_flyers.py`, one
entry per forum. To add another forum, such as the School Committee nights, copy an
entry and edit it. The build writes each PDF to this folder and a PNG to `proofs/`.

**Checks.** The build refuses or flags:

- a date whose weekday doesn't match the calendar
- anything other than one 8.5 × 11 page
- any font other than Liberation Sans
- text running past the margins or into the QR code
- a QR code that doesn't scan back to the exact form URL. The scan runs at print
  resolution and needs `opencv-python-headless`; without it, this check is skipped
  with a note.

**Requirements.** Python 3 with `segno` and `pymupdf`, plus Chromium. Set `CHROME=`
if Chromium isn't at the Playwright path the palm cards use. Fonts, logos, and the
QR code are embedded in the generated HTML, so each flyer file has everything it
needs.
