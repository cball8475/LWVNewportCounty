# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

The public website of the League of Women Voters of Newport County, Rhode Island. It's hand-written static HTML with one shared `styles.css`. There is no build step and no templating. GitHub Pages serves the root of `main` at **lwvnewportcounty.org** (see `CNAME`), so **merging to `main` publishes**. Pages redeploys in about a minute. The repo is public. `_config.yml` keeps repo docs (`CLAUDE.md`, `README.md`, `NEWS-POSTING-GUIDE.md`, `docs/`) and `scripts/` off the published site. Any other Markdown file you add is published as a web page.

The site owner usually reviews from a phone, which shapes the workflow:

- For new or changed public copy, show the wording first, before/after, plus a rendered screenshot for layout changes. Wait for approval.
- Work goes in a draft PR. Merge only on the owner's explicit OK, and always **squash**-merge.
- After merging, confirm the `pages-build-deployment` run for the merge commit succeeded.

## Session start: site-health digest

`.claude/hooks/session-start.sh` runs on every Claude Code web session. It installs the Python packages the repo's scripts need (listed in the hook's header) and prints the output of `scripts/site_health.py`. That digest flags:

- events under "Upcoming Events" whose date has passed
- past or soon-to-expire dates in the homepage banners
- past-dated promos next to Register/RSVP links
- page files cut off before `</html>`
- dead Cloudflare email links
- unbalanced tags
- failed bot workflows

Bring up the ⚠ items with the owner. Don't change public pages to fix them without being asked.

```bash
python3 scripts/site_health.py                              # run the checks any time
SITE_HEALTH_TODAY=2026-10-05 python3 scripts/site_health.py # what goes stale by that date
python3 scripts/site_health.py --strict                     # exit 1 on any ⚠ (CI-style)
```

## Commands

There is no test suite or linter config. These are the checks to use:

```bash
python3 scripts/site_health.py                 # HTML structure + stale-content lint
node --check scripts/*.js                      # JS syntax
python3 -m py_compile scripts/*.py             # Python syntax

# LWVUS news feed. Rewrites data/lwvus-news.json and every page with LWVUS_NEWS markers;
# the bot already runs it every 6 h, so don't commit a local run unless that's the point.
python3 scripts/fetch_lwvus.py

# News-post renderer, run against a saved issue payload.
GITHUB_EVENT_PATH=fake-event.json node scripts/post-news.js news.html

# Print pieces (see each folder's README.md for specs and checks).
cd print/forum-flyers-2026/source && python3 build_flyers.py [town]           # writes the tracked PDFs/PNGs one level up
cd print/palm-card-2026/source && python3 build_card.py [en|es] && ./render.sh  # output goes to the gitignored build/
```

**Preview a page.** Nothing serves the site locally, so render the file itself with the globally installed Playwright:

- Run with `NODE_PATH="$(npm root -g)" node shot.js`.
- Set `executablePath` to `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- Load pages as `file://` and route-abort `http(s)` requests, because the sandbox has no general web access.
- Capture at 390px and 1280px.

**Live site.** The sandbox proxy blocks `lwvnewportcounty.org` and `docs.google.com`. Check live pages with a web-scraping tool, or ask the owner.

**Member portal.** Never run `scripts/build-member-portal.js` into a tracked path. It writes the *plaintext* member roster, and only the StatiCrypt-encrypted `members.html` may be committed. `members-source.html` and `encrypted/` are gitignored.

## Architecture

**Pages.** The pages are `index` (home), `about`, `vote` (voter resources), `events`, `elections-2026` (the Elections hub), `issues`, `get-involved`, `news`, `action-alerts`, `find-your-rep` and `members` (encrypted).

The nav and footer are **copied into every page**. A nav or footer change has to be made on every page. Copy the nav from `index.html`: `nav-standard.html` is a reference snippet that lags behind (it's missing Find Your Rep). Most styling is inline; `styles.css` holds the shared base.

**Bot workflows.** Every workflow that pushes to `main` shares the concurrency group `site-content-push` and uses a rebase-and-retry push loop.

| Workflow | Trigger | Effect |
|---|---|---|
| `lwvus-news.yml` | every 6 h, manual | `fetch_lwvus.py` tries the lwv.org RSS feed first and scrapes the site if that fails. It writes `data/lwvus-news.json` and the `LWVUS_NEWS_START/END` block in any page (today, `news.html`). It exits 1 when it finds no items, and keeps the old HTML when results are thin. |
| `post-news.yml` | the "📰 Post News" issue form (label `news-post`) | `post-news.js` renders the issue into the `AUTO-NEWS-LWVNC/LWVRI/LWVUS` block of `news.html`. Posts from owners and collaborators publish immediately; anyone else's need the `approved` label. Editing the issue replaces its card (`news-post:N` markers). Owner-facing guide: `NEWS-POSTING-GUIDE.md`. |
| `update-member-portal.yml` | 12:00 and 22:00 UTC, manual | `build-member-portal.js` reads published CSV tabs of the member-portal Google Sheet (tab GIDs are hardcoded) and writes `members-source.html`. StatiCrypt then encrypts it with secret `MEMBER_PASSWORD` into `members.html`. An inline check refuses to commit plaintext, keyed on the `lwvnc-portal-plaintext-sentinel` comment the builder emits. |
| `validate-member-portal.yml` | a push touching `members.html` | Runs the same encryption check on human pushes. Pushes made with `GITHUB_TOKEN` don't trigger it, which is why the check also runs inline above. |

Never hand-edit inside machine-owned marker blocks (`LWVUS_NEWS_*`, `AUTO-NEWS-*`, `news-post:*`). Bot commits land on `main` several times a day, so branches go stale fast. Bring `main` in with a merge rather than rebasing a shared branch.

## Events: hand-maintained

Events are hand-written HTML. The Google Sheet events feed (`update-events.yml`) was retired in Sept 2026 after its sheet was deleted (PR #18). Nothing removes past events automatically, which is why the session digest checks for them.

- **Where an event appears.** Cards go under "Upcoming Events" in `events.html`, soonest first. To add one, copy an existing card: a month label with a 48px day number, an `<h3>` title, a meta line ("Weekday, Month D • time • location"), a description and a link. The same event may also be promoted on `index.html` (a section after the Elections band), on `issues.html` ("News from LWVRI"), and on `elections-2026.html`. When it changes, change every copy.
- **Candidate forums.** The schedule is the "2026 Candidate Forums" list in `events.html`. Full details and **Add to calendar** buttons are in `elections-2026.html#forums`; each button carries `data-cal data-title data-date="YYYY-MM-DD" [data-end]`. In the `events.html` list, each forum date is a `<span class="forum-date" data-date="YYYY-MM-DD">`, and a script at the bottom of that page tags passed dates "Past". When a forum is added or moves, update the date on both pages.
- **Past items on the Elections hub.** The page's `hidePastItems()` script handles them from their dates. Countdown cards (`.el-count-card[data-date]`) hide and the row re-flows. Timeline entries and forums whose calendar button's `data-end`/`data-date` has passed are dimmed, tagged "Past" and lose the button. Give every new card or entry a `data-date`, or it never ages out.
- **After an event:**
  1. Remove its card and every promo of it.
  2. Add the card to the top of `events-archive.html`, newest first. That file is an unlinked record, not a page. Use its header box: `ARCHIVED: <date> — <title>` / `Removed from events.html: <YYYY-MM-DD>`.
  3. If "Upcoming Events" is now empty, point readers to the forum schedule or the Elections hub.

## Time-sensitive copy and facts

- **Homepage banners.** The top of `index.html` has two time-sensitive blocks: the red alert banner (`vr-alert-band`, which currently covers the SAVE Act) and the Elections band facts (`el-home-fact`). Keep the Elections band's dates in the future and in date order, and swap an item out when its deadline passes. Every banner and dated box keeps an HTML comment naming its sources and the date it was last updated. Keep those comments current.
- **Election dates.** Dates must match the official sources: the RI Board of Elections "Upcoming Elections" table (elections.ri.gov) and the Secretary of State's voter site (vote.sos.ri.gov). `elections-2026.html` holds the full, labeled deadlines (primary vs. general). `vote.html` lists the general-election deadlines, with the past primary as a one-line note. The homepage must agree with both.
- **Dated updates in `action-alerts.html`.** Use the existing "Update — Month D, YYYY" box style, which sits at the top of the alert it updates.
- **Voice.** Write in the League's nonpartisan voice. The League takes positions on issues, never on candidates or parties. Don't confuse the **SAVE Act** (the legislation) with DHS's **SAVE database**, which is the subject of the League's own litigation.

## Print: flyers and palm cards

Each series under `print/` has a `README.md` covering specs, colors, fonts, the checks the build runs, and what to confirm before printing. Read it before editing.

Generators write self-contained HTML (fonts, logos and QR codes inlined) and print it to PDF with headless Chromium:

- **Forum flyers.** Copy for each flyer is in the `FORUMS` list in `build_flyers.py`. The build checks that weekdays match dates, that each flyer is one page, the font, the margins, and that each QR code scans back to its form URL (this needs `opencv-python-headless`).
- **Palm cards.** Copy is in the `STRINGS` dict of `build_card.py`, one entry per language. Press PDFs include bleed and crop marks and print head-to-head.
- **QR codes.** Always scan a printed proof before a full print run.

## Gotchas

- Files uploaded through the GitHub web UI have arrived **cut off mid-tag**. `site_health.py` flags any page that doesn't end with `</html>`. Browsers auto-close the missing tags, so a cut-off page can look fine at a glance.
- Pages copied from a live site can carry Cloudflare `/cdn-cgi/l/email-protection` links, which are dead on GitHub Pages. Use plain `mailto:` links instead.
- `docs/history/` holds change notes from earlier builds. They aren't published, and many describe things that no longer exist. The current workflow docs are `NEWS-POSTING-GUIDE.md` and `print/*/README.md`.
- `event-section.html` is an unlinked leftover, a copy of an old homepage promo. It isn't part of the site navigation.
