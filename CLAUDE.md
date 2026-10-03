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
- The pages use the Inter and IBM Plex Serif web fonts, which the sandbox can't load, so text widths come out wrong. For layout checks, fetch them with `npm pack @fontsource/inter @fontsource/ibm-plex-serif`, answer the `fonts.googleapis.com` request with `@font-face` rules for both families, and serve the `.woff2` files with `access-control-allow-origin: *` (a `file://` page needs CORS for fonts).
- Run `axe-core`'s `color-contrast` rule on changed pages (`npm pack axe-core`, inject `axe.min.js`). Every restyled page passes; keep it that way.
- To catch sideways scrolling, compare `document.documentElement.scrollWidth` with the viewport width at every width from 320 to 1280px. Content inside an `overflow-x:auto` box (the Elections sub-menu, wide tables) scrolls on its own and doesn't count.

**Live site.** The sandbox proxy blocks `lwvnewportcounty.org` and `docs.google.com`. Check live pages with a web-scraping tool, or ask the owner.

**Member portal.** Never run `scripts/build-member-portal.js` into a tracked path. It writes the *plaintext* member roster, and only the StatiCrypt-encrypted `members.html` may be committed. `members-source.html` and `encrypted/` are gitignored.

## Architecture

**Pages.** The pages are `index` (home), `about`, `vote` (voter resources), `events`, `elections-2026` (the Elections hub), `issues`, `get-involved`, `news`, `action-alerts`, `find-your-rep`, `news-notes` (the newsletter archive, linked from the footer) and `members` (encrypted).

**Design system.** `styles.css` holds the LWV brand tokens (`--lwv-blue`, `--lwv-red`, `--lwv-purple`, `--lwv-purple-dark`, `--lwv-gold`, AA-safe neutrals, a spacing scale) and the shared components. `docs/styleguide.html` (not published) shows each one with copy-paste markup. Headings are IBM Plex Serif; body text is Inter.

- Build pages from the components instead of inline styles: `.page-header` (or `.page-header--photo`), a `.container.container--narrow.page-body.prose` content area, `.card`, `.callout` (the lwv.org box with a thick purple left and bottom border), `.panel`, `.promo`, `.eyebrow`, `.stat-bracket`, `.date-tile`, `.event-item`, `.alert`, `.update-box`, `.news-card`, `.table` in a `.table-wrap`, and the `.btn` variants. A rule only one page needs goes in that page's `<style>` block.
- Gold is for rules, brackets and dark backgrounds. Gold text on white fails contrast.
- The LEGACY section at the end of `styles.css` keeps old class names (`.site-header`, bare `nav`, `.cta-section`, `.impact-card`, …) working, mainly for the encrypted member portal until the bot rebuilds it. Don't use them in new work.
- The Elections hub has its own `el-` styles; its `--el-*` variables point at the brand tokens.

**Shared chrome.** Every page carries its own copy of the same chrome:
- the `<head>` block: meta description, Open Graph tags, favicon, the Plex Serif + Inter font link, and `site.js`;
- the skip link;
- the utility bar;
- the sticky `.site-nav` with Join and Donate;
- the `.site-footer`;
- `<main id="main">` around the page content.

`nav-standard.html` is the current reference copy, with instructions. A chrome change has to be made on every page **and** in the member-portal template in `scripts/build-member-portal.js`. Mark the current page's link with `aria-current="page"`. `site.js` runs the phone/tablet menu; its 1180px width must match the nav breakpoint in `styles.css`.

The newsletter signup is a pre-filled email ("Subscribe by email"). If the League sets up a signup form, swap that mailto link in every footer, in the portal template, and on `news.html` and `news-notes.html`.

**Search engines.** These are per page, not chrome, so the member portal doesn't need them.
- `sitemap.xml` lists the public pages. `robots.txt` points to it and asks crawlers to skip `members.html` and the unlinked working files.
- Each public page has a `<link rel="canonical">` right after `og:url`, and a BreadcrumbList JSON-LD block (Home > page) just before `</head>`. A new page needs both, plus a sitemap entry.
- `index.html` carries WebSite and Organization (`NGO`) JSON-LD: the site name, the "LWVNC" alias, logo, email, mailing address and social profiles. Update it when any of those change.
- Google Search Console has a Domain property for `lwvnewportcounty.org` (verified Oct 3, 2026). The proof is a `google-site-verification=…` TXT record on `@` in Namecheap DNS, where the domain is registered. Never delete that record. Namecheap also runs the domain's free email forwarding: the MX records and the locked SPF TXT record. If DNS ever moves (a Cloudflare move after the Nov 2026 election has been discussed), first recreate every email forwarder there and copy the verification record.

**Bot workflows.** Every workflow that pushes to `main` shares the concurrency group `site-content-push` and uses a rebase-and-retry push loop.

| Workflow | Trigger | Effect |
|---|---|---|
| `lwvus-news.yml` | every 6 h, manual | `fetch_lwvus.py` tries the lwv.org RSS feed first and scrapes the site if that fails. It writes `data/lwvus-news.json` and the `LWVUS_NEWS_START/END` block in any page (today, `news.html`). It exits 1 when it finds no items, and keeps the old HTML when results are thin. |
| `post-news.yml` | the "📰 Post News" issue form (label `news-post`) | `post-news.js` renders the issue into the `AUTO-NEWS-LWVNC/LWVRI/LWVUS` block of `news.html`. Posts from owners and collaborators publish immediately; anyone else's need the `approved` label. Editing the issue replaces its card (`news-post:N` markers). Owner-facing guide: `NEWS-POSTING-GUIDE.md`. |
| `update-member-portal.yml` | 12:00 and 22:00 UTC, manual | `build-member-portal.js` reads published CSV tabs of the member-portal Google Sheet (tab GIDs are hardcoded) and writes `members-source.html`. StatiCrypt then encrypts it with secret `MEMBER_PASSWORD` into `members.html`. An inline check refuses to commit plaintext, keyed on the `lwvnc-portal-plaintext-sentinel` comment the builder emits. |
| `validate-member-portal.yml` | a push touching `members.html` | Runs the same encryption check on human pushes. Pushes made with `GITHUB_TOKEN` don't trigger it, which is why the check also runs inline above. |

Never hand-edit inside machine-owned marker blocks (`LWVUS_NEWS_*`, `AUTO-NEWS-*`, `news-post:*`). Both generators emit `<article class="news-card">` markup, so restyle the cards by changing the generators and the `.news-card` rules together. To re-render existing posts, re-run `post-news.js` for each issue with its current body (action `edited`, `TZ=UTC`, ascending issue number), as the Sept/Oct 2026 redesign did. Bot commits land on `main` several times a day, so branches go stale fast. Bring `main` in with a merge rather than rebasing a shared branch.

## Events: hand-maintained

Events are hand-written HTML. The Google Sheet events feed (`update-events.yml`) was retired in Sept 2026 after its sheet was deleted (PR #18). Nothing removes past events automatically, which is why the session digest checks for them.

- **Where an event appears.** Cards go under "Upcoming Events" in `events.html`, soonest first. To add one, copy the commented-out card template under "Upcoming Events": an `.event-item` with a `.date-tile` (month and day), an `<h3>` title, a meta line ("Weekday, Month D • time • location"), a description and a link. `site_health.py` reads the date tile and the `<h3>`, and warns about any card there it can't read. The same event may also be promoted on `index.html` (a section after the Elections band), on `issues.html` ("News from LWVRI"), and on `elections-2026.html`. When it changes, change every copy.
- **Candidate forums.** The schedule is the "2026 Candidate Forums" list in `events.html`. Full details and **Add to calendar** buttons are in `elections-2026.html#forums`; each button carries `data-cal data-title data-date="YYYY-MM-DD" [data-end]`. In the `events.html` list, each forum date is a `<span class="forum-date" data-date="YYYY-MM-DD">`, and a script at the bottom of that page tags passed dates "Past". When a forum is added or moves, update the date on both pages.
- **Past items on the Elections hub.** The page's `hidePastItems()` script handles them from their dates. Countdown cards (`.el-count-card[data-date]`) hide and the row re-flows. Timeline entries and forums whose calendar button's `data-end`/`data-date` has passed are dimmed, tagged "Past" and lose the button. Give every new card or entry a `data-date`, or it never ages out.
- **After an event:**
  1. Remove its card and every promo of it.
  2. Add the card to the top of `events-archive.html`, newest first. That file is an unlinked record, not a page. Use its header box: `ARCHIVED: <date> — <title>` / `Removed from events.html: <YYYY-MM-DD>`.
  3. If "Upcoming Events" is now empty, point readers to the forum schedule or the Elections hub.

## Time-sensitive copy and facts

- **Homepage banners.** The top of `index.html` has two time-sensitive blocks: the one-line red notice bar above the header (`.notice-bar`, which currently covers the SAVE Act) and the Elections band facts (`el-home-fact`). Keep the Elections band's dates in the future and in date order, and swap an item out when its deadline passes. Every banner and dated box keeps an HTML comment naming its sources and the date it was last updated. Keep those comments current. The Elections band keeps its original markup, including its own `<style>` block; `styles.css` restyles it with higher-specificity rules under "HOMEPAGE".
- **Election dates.** Dates must match the official sources: the RI Board of Elections "Upcoming Elections" table (elections.ri.gov) and the Secretary of State's voter site (vote.sos.ri.gov). `elections-2026.html` holds the full, labeled deadlines (primary vs. general). `vote.html` lists the general-election deadlines, with the past primary as a one-line note. The homepage must agree with both.
- **Dated updates in `action-alerts.html`.** Each alert is an `<article class="alert">`. An update is a `.update-box` whose `.update-box__label` reads "Update — Month D, YYYY", placed at the top of the alert it updates.
- **Membership dues.** The prices on `get-involved.html` (and the homepage line) must match the LWVRI join page, where members actually pay (my.lwv.org/rhode-island/membership). The comment above the price cards records when that page was last checked.
- **Scheduled homepage jobs (until Nov 4, 2026).** Routines set up on Sep 27, 2026 update the homepage Elections band on Oct 5, Oct 14 and Oct 23, and draft a cleanup PR on Nov 4. They work on branch `claude/fix-this-axlf34` and match the band by exact text. Keep the `<a href="elections-2026.html" class="el-home-band" …>` tag and the `el-home-fact` spans' wording unchanged; restyle the band only through CSS. The Oct 5 job merges itself only if no open PR on another branch touches `index.html`.
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
