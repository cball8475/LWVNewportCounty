#!/usr/bin/env node
/**
 * post-news.js
 * Turns a "📰 Post News to the Website" issue-form submission into a news card
 * on news.html. Runs inside the post-news.yml GitHub Action — the issue payload
 * is read from GITHUB_EVENT_PATH, so posting news is just: fill the form, submit.
 *
 * Cards are inserted into one of three marker blocks in news.html:
 *     <!-- AUTO-NEWS-LWVNC:START --> ... <!-- AUTO-NEWS-LWVNC:END -->
 *     <!-- AUTO-NEWS-LWVRI:START --> ... <!-- AUTO-NEWS-LWVRI:END -->
 *     <!-- AUTO-NEWS-LWVUS:START --> ... <!-- AUTO-NEWS-LWVUS:END -->
 *
 * Each card is wrapped in <!-- news-post:N:START/END --> comments (N = issue
 * number), so editing the issue replaces the existing card instead of
 * duplicating it — including when the edit moves it to a different section.
 *
 * Local testing: GITHUB_EVENT_PATH=fake-event.json node scripts/post-news.js [news.html]
 */

const fs = require('fs');

const NEWS_FILE = process.argv[2] || 'news.html';

const SECTIONS = {
  LWVNC: { start: '<!-- AUTO-NEWS-LWVNC:START -->', end: '<!-- AUTO-NEWS-LWVNC:END -->' },
  LWVRI: { start: '<!-- AUTO-NEWS-LWVRI:START -->', end: '<!-- AUTO-NEWS-LWVRI:END -->' },
  LWVUS: { start: '<!-- AUTO-NEWS-LWVUS:START -->', end: '<!-- AUTO-NEWS-LWVUS:END -->' },
};

function esc(str) {
  return String(str == null ? '' : str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── parse the structured markdown body GitHub generates from an issue form ──
// The body looks like: "### Headline\n\nvalue\n\n### Section\n\nvalue\n\n..."
function parseIssueForm(body) {
  const fields = {};
  const parts = String(body || '').replace(/\r\n/g, '\n').split(/^### +/m).slice(1);
  for (const part of parts) {
    const nl = part.indexOf('\n');
    if (nl === -1) continue;
    const label = part.slice(0, nl).trim().toLowerCase();
    let value = part.slice(nl + 1).trim();
    if (/^_no response_$/i.test(value) || value === 'None') value = '';
    fields[label] = value;
  }
  const get = (...keys) => {
    for (const k of Object.keys(fields)) {
      if (keys.some(want => k.includes(want))) return fields[k];
    }
    return '';
  };
  return {
    headline: get('headline'),
    section: get('section'),
    story: get('story'),
    category: get('category'),
    date: get('date'),
    link: get('link'),
    image: get('image'),
  };
}

function sectionKey(section) {
  const s = String(section || '').toLowerCase();
  if (s.includes('rhode')) return 'LWVRI';
  if (s.includes('united states') || s.includes('lwvus')) return 'LWVUS';
  return 'LWVNC';
}

// ── date parsing: YYYY-MM-DD, MM/DD/YYYY, M/D/YY, plus Date.parse fallback ──
function parseDate(s) {
  if (!s) return null;
  s = s.trim();
  let m;
  if ((m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/)))    return new Date(+m[1], +m[2] - 1, +m[3]);
  if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/)))  return new Date(+m[3], +m[1] - 1, +m[2]);
  if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2})$/))) return new Date(2000 + +m[3], +m[1] - 1, +m[2]);
  const t = Date.parse(s);
  return isNaN(t) ? null : new Date(t);
}

const MONF = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const formatDate = d => `${MONF[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;

// only allow safe link/image targets — everything else is dropped, not guessed at
function safeUrl(url) {
  const u = String(url || '').trim();
  if (/^https?:\/\//i.test(u)) return u;
  if (/^[\w./-]+\.(html|jpg|jpeg|png|gif|webp|svg|pdf)$/i.test(u) && !u.startsWith('/') && !u.includes('..')) return u;
  return '';
}

// ── render one card, matching the hand-written article style on news.html ──
function renderCard(post, issueNumber) {
  const paragraphs = post.story.split(/\n\s*\n/)
    .map(p => esc(p.replace(/\s*\n\s*/g, ' ').trim()))
    .filter(Boolean);
  const bodyHTML = paragraphs
    .map((p, i) => (i === 0 ? `            <p>${p}</p>` : `            <p style="margin-top: 14px;">${p}</p>`))
    .join('\n');

  const label = `${esc(post.category || 'News')} &bull; ${esc(post.dateline)}`;
  const image = safeUrl(post.image);
  const link = safeUrl(post.link);

  const imageHTML = image
    ? `            <img src="${esc(image)}" alt="${esc(post.headline)}" style="width: 100%; height: auto; border-radius: 6px; margin-bottom: 20px;">\n`
    : '';
  const linkHTML = link
    ? `\n            <p style="margin-top: 15px;">\n                <a href="${esc(link)}" target="_blank" rel="noopener" style="background: #003d7a; color: white; padding: 10px 22px; text-decoration: none; font-weight: 600; display: inline-block; font-size: 14px;">Read More &rarr;</a>\n            </p>`
    : '';

  return `        <!-- news-post:${issueNumber}:START -->
        <article style="border-bottom: 1px solid #e0e0e0; padding: 35px 0;">
${imageHTML}            <p style="color: #d32f2f; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">${label}</p>
            <h3 style="margin: 0 0 12px 0; color: #003d7a;">${esc(post.headline)}</h3>
${bodyHTML}${linkHTML}
        </article>
        <!-- news-post:${issueNumber}:END -->`;
}

function main() {
  const eventPath = process.env.GITHUB_EVENT_PATH;
  if (!eventPath) throw new Error('GITHUB_EVENT_PATH is not set — this script runs inside the post-news workflow.');
  const event = JSON.parse(fs.readFileSync(eventPath, 'utf8'));
  const issue = event.issue;
  if (!issue) throw new Error('Event payload has no issue.');

  const post = parseIssueForm(issue.body);
  if (!post.headline) throw new Error('The form is missing a Headline.');
  if (!post.story) throw new Error('The form is missing a Story.');

  const dateObj = parseDate(post.date) || new Date(issue.created_at);
  post.dateline = formatDate(dateObj);

  const key = sectionKey(post.section);
  const { start, end } = SECTIONS[key];
  const card = renderCard(post, issue.number);

  let html = fs.readFileSync(NEWS_FILE, 'utf8');
  if (!html.includes(start) || !html.includes(end)) {
    throw new Error(`Marker block for ${key} not found in ${NEWS_FILE}.`);
  }

  // remove any existing card for this issue (handles edits, incl. section moves)
  const existing = new RegExp(`[ \\t]*<!-- news-post:${issue.number}:START -->[\\s\\S]*?<!-- news-post:${issue.number}:END -->\\n?`, 'g');
  html = html.replace(existing, '');

  // newest post goes at the top of its section block
  html = html.replace(start, `${start}\n${card}`);

  fs.writeFileSync(NEWS_FILE, html);
  console.error(`Published issue #${issue.number} ("${post.headline}") to the ${key} section of ${NEWS_FILE}.`);
}

try {
  main();
} catch (err) {
  console.error('POST FAILED:', err.message || err);
  process.exit(1);
}
