# Candidate forum flyers

Reusable version of the flyer template first used for the RI District 13 State
Senate Primary Forum: US Letter (8.5 × 11 in), LWV navy header with the logo
card, red `CANDIDATES FORUM` badge, navy headline, bordered info card with icon
rows, navy call-to-action banner, partner-logo strip and navy footer.

Output PDFs are real text (embedded Liberation Sans, metric-compatible with
Arial), so they stay sharp at any size and the Google Form links are clickable.

## Files

| Path | What it is |
| --- | --- |
| `forums.json` | The content of each flyer — this is the only file you normally edit |
| `build.py` | Generates the HTML and renders PDF + PNG into `out/` |
| `measure.py` | Prints the rendered height of every section, for debugging layout |
| `assets/` | LWV logo and the five partner logos |
| `out/` | Generated `.html`, `.pdf` (print/press) and `.png` (2×, for web and social) |

## Rebuilding

```sh
python3 flyers/build.py
```

Requires Python 3, and a Chromium binary (set `CHROME_BIN` if it is not at
`/opt/pw-browsers/chromium`). Install `playwright` to enable the page-fit check;
without it the build still works but skips that check.

## Adding a flyer

Append an entry to `forums.json`:

- `slug` — output filename
- `kicker`, `title` (a list, one entry per headline line), `subtitle`, `lede`
- `rows` — the info-card rows, each with `icon`
  (`calendar` / `pin` / `user` / `question`), `label`, `value`, optional
  `detail`, and optional `href` to make the value a link
- `cards` instead of `rows` puts two events side by side on one sheet, each with
  its own `head` and `rows` (used for the two Newport forums)

## Keeping it on one page

Everything between the header and the footer sits in a flex column; only the
`.spacer` elements absorb slack, so extra content pushes the layout past the
bottom of the sheet rather than being silently squeezed. `build.py` checks this
after every render and exits non-zero with a `FAIL` line naming what overflowed.
If you hit that, shorten a line, drop a row, or trim the `max-height` on the
spacers.
