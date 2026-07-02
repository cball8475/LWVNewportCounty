# Posting News to the Website

News now works like events — nobody edits HTML. There are **two automated paths** onto the [News & Updates page](https://lwvnewportcounty.org/news.html):

## 1. Post your own news (the form)

Use this for anything you want on the site: local League news, LWVRI updates, or a national story like the Supreme Court's mail-ballot decision.

1. Go to **[Post News to the Website](https://github.com/cball8475/LWVNewportCounty/issues/new?template=post-news.yml)** (Issues → New issue → "📰 Post News to the Website").
2. Fill in the form:
   - **Headline** (required)
   - **Section** — Newport County, Rhode Island, or United States
   - **Story** (required) — paragraphs separated by a blank line
   - **Category label** — the small red label, e.g. "Press Release" or "Breaking Victory" (blank = "News")
   - **Date** — blank = today
   - **Link** — shown as a "Read More →" button
   - **Image** — a web image URL, or a file already in the site's `images/` folder
3. Press **Submit new issue**. That's it.

Within a couple of minutes a GitHub Action renders your post into the right section of `news.html`, commits it, and GitHub Pages redeploys. You'll get a ✅ confirmation comment with the link, and the issue closes itself.

**Fixing a typo:** edit the issue. The published post updates automatically to match (including if you change the section).

**Who can post:** submissions from repo owners/collaborators publish instantly. Anyone else's submission waits until a maintainer adds the **approved** label to the issue — nothing goes live unreviewed.

## 2. National news posts itself (no one does anything)

`scripts/fetch_lwvus.py` runs daily (`.github/workflows/lwvus-news.yml`) and pulls the latest LWVUS press releases from lwv.org into the "News from LWV United States" section, between the `LWVUS_NEWS_START/END` markers in `news.html`. Statements like *"Supreme Court Protects Mail Voting"* appear on the site without anyone posting them.

Don't hand-edit between those two markers — the daily run replaces that block. Anything you want to say in your own words belongs in the form (path 1), which posts *above* the automatic feed.

## How it fits together on news.html

```
News from LWV Newport County
  ├─ AUTO-NEWS-LWVNC block   ← form posts (newest first)
  └─ hand-written articles    ← legacy content, still fine to keep

News from LWV Rhode Island
  ├─ AUTO-NEWS-LWVRI block   ← form posts
  └─ "coming soon" box

News from LWV United States
  ├─ AUTO-NEWS-LWVUS block   ← form posts
  └─ LWVUS_NEWS block        ← daily automatic feed from lwv.org
```

## Pieces

| File | Role |
|---|---|
| `.github/ISSUE_TEMPLATE/post-news.yml` | The posting form |
| `.github/workflows/post-news.yml` | Publishes a submission (or asks for approval) |
| `scripts/post-news.js` | Renders the submission into `news.html` |
| `scripts/fetch_lwvus.py` + `.github/workflows/lwvus-news.yml` | Daily national-news feed |
