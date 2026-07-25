#!/usr/bin/env node
/**
 * build-events.js
 * Pulls public events from the "LWVNC Public Events" Google Sheet (published as CSV)
 * and writes the rendered event cards into events.html, between the markers:
 *     <!-- AUTO-EVENTS:START -->  ...  <!-- AUTO-EVENTS:END -->
 *
 * Mirrors scripts/build-member-portal.js: Node 20 native fetch() against a
 * published-to-web CSV. No Google API key, no service account.
 *
 * Usage: node scripts/build-events.js [events.html]
 *   - EVENTS_CSV_URL env var overrides the hardcoded CSV_URL (used for local testing
 *     and lets the URL live in a repo variable if preferred).
 */

const fs = require('fs');

// ── Published-to-web CSV of the "LWVNC Public Events" sheet ──
// In the sheet: File → Share → Publish to web → select the tab → CSV → copy link.
// It looks like https://docs.google.com/spreadsheets/d/e/2PACX-...../pub?output=csv&gid=NNN
const CSV_URL = process.env.EVENTS_CSV_URL || 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTGvRvIzZeKFZcB2cXjh2aLweKXPo0ISdYuhx-blOyX6XGJ6n4GHjjdEh34T_LrUmYmjETi-Z-D_wBx/pub?output=csv';

const EVENTS_FILE = process.argv[2] || 'events.html';
const START = '<!-- AUTO-EVENTS:START -->';
const END   = '<!-- AUTO-EVENTS:END -->';

// ── fetch CSV (Node 20 native fetch follows Google's 307 redirects; https.get does not) ──
async function fetchCSV(url) {
  if (!url || url === 'PUBLISHED_CSV_URL_HERE') {
    throw new Error('CSV_URL is not set. Publish the "LWVNC Public Events" sheet to web as CSV and set CSV_URL (or EVENTS_CSV_URL).');
  }
  const res = await fetch(url, {
    headers: { 'User-Agent': 'LWVNC-Builder/1.0' },
    redirect: 'follow',
  });
  if (!res.ok) throw new Error(`Failed to fetch CSV: ${res.status} ${res.statusText}`);
  const text = await res.text();
  if (/^\s*<(?:!doctype|html)/i.test(text)) {
    throw new Error('CSV URL returned HTML (likely a login page) — re-publish the sheet to web as CSV.');
  }
  return text;
}

// ── CSV parser: handles quoted fields with embedded commas and newlines ──
function parseCSV(text) {
  const s = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const out = [];
  let row = [], field = '', inQ = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inQ) {
      if (c === '"' && s[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') inQ = false;
      else field += c;
    } else if (c === '"') inQ = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n') { row.push(field); out.push(row); row = []; field = ''; }
    else field += c;
  }
  if (field.length || row.length) { row.push(field); out.push(row); }
  const rows = out.filter(r => r.some(x => x.trim() !== ''));
  if (!rows.length) return { header: [], rows: [] };
  return { header: rows[0].map(h => h.trim()), rows: rows.slice(1) };
}

// ── adaptive column mapping from the actual header row ──
function mapColumns(header) {
  const find = (...keys) => {
    // Exact header match wins before any substring guess — with substring-only
    // matching, a "Contact Name" column left of "Event Title" silently claimed
    // the name slot and rendered contact names as event titles.
    for (let i = 0; i < header.length; i++) {
      const h = header[i].toLowerCase();
      if (keys.some(k => h === k)) return i;
    }
    for (let i = 0; i < header.length; i++) {
      const h = header[i].toLowerCase();
      if (keys.some(k => h.includes(k))) return i;
    }
    return -1;
  };
  return {
    name:        find('event name', 'event title', 'title', 'name', 'event'),
    date:        find('date'),
    start:       find('start'),
    end:         find('end'),
    location:    find('location', 'venue', 'address', 'where'),
    description: find('description', 'details', 'desc'),
    link:        find('link', 'rsvp', 'register', 'url'),
  };
}

// ── date parsing: YYYY-MM-DD, MM/DD/YYYY, M/D/YY, plus Date.parse fallback ──
function parseDate(s) {
  if (!s) return null;
  s = s.trim();
  let m;
  if ((m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/)))      return new Date(+m[1], +m[2] - 1, +m[3]);
  if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/)))    return new Date(+m[3], +m[1] - 1, +m[2]);
  if ((m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2})$/)))   return new Date(2000 + +m[3], +m[1] - 1, +m[2]);
  const t = Date.parse(s);
  return isNaN(t) ? null : new Date(t);
}

const MON  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const MONF = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const WD   = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const pad  = n => (n < 10 ? '0' : '') + n;
const ymd  = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

function esc(str) {
  return String(str == null ? '' : str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── render one card, mirroring the existing hand-written events.html card markup ──
function renderCard(ev) {
  const d = ev.dateObj;
  const dateline = `${WD[d.getDay()]}, ${MONF[d.getMonth()]} ${d.getDate()}`;
  const timeBits = [ev.start, ev.end].filter(Boolean).join(' – ');
  const meta = [dateline, timeBits, ev.location].filter(Boolean).join(' • ');
  const linkHTML = ev.link
    ? `\n                    <p style="margin-top: 12px;"><a href="${esc(ev.link)}" target="_blank">Details &amp; RSVP &rarr;</a></p>`
    : '';
  const descHTML = ev.description ? `\n                    <p>${esc(ev.description)}</p>` : '';
  return `        <div style="border-left: 6px solid #003d7a; background: #f9f9f9; padding: 30px 35px; margin: 30px 0;">
            <div style="display: flex; align-items: flex-start; gap: 30px; flex-wrap: wrap;">
                <div style="text-align: center; min-width: 70px;">
                    <div style="font-size: 12px; color: #d32f2f; font-weight: 700; text-transform: uppercase; letter-spacing: 1px;">${MON[d.getMonth()]}</div>
                    <div style="font-size: 48px; font-weight: 700; line-height: 1; color: #003d7a;">${d.getDate()}</div>
                </div>
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 8px 0; color: #003d7a;">${esc(ev.name)}</h3>
                    <p style="color: #666; font-size: 15px; margin-bottom: 12px;">${esc(meta)}</p>${descHTML}${linkHTML}
                </div>
            </div>
        </div>`;
}

function buildBlock(cards) {
  if (!cards.length) {
    return `\n        <!-- No upcoming events in the sheet yet. Add rows to the "LWVNC Public Events" Google Sheet and they appear here automatically. -->\n        `;
  }
  return '\n' + cards.join('\n') + '\n        ';
}

function escapeRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

async function main() {
  const csv = await fetchCSV(CSV_URL);
  const { header, rows } = parseCSV(csv);
  console.error('CSV header row:', JSON.stringify(header));
  const col = mapColumns(header);
  console.error('Inferred column mapping:', JSON.stringify(col));
  if (col.name === -1 || col.date === -1) {
    throw new Error('Could not find required "Event Name" and "Date" columns in the sheet header.');
  }

  const today = new Date(); today.setHours(0, 0, 0, 0);

  let events = rows.map(r => {
    const get = i => (i >= 0 && i < r.length ? String(r[i]).trim() : '');
    return {
      name: get(col.name),
      dateObj: parseDate(get(col.date)),
      start: get(col.start),
      end: get(col.end),
      location: get(col.location),
      description: get(col.description),
      link: get(col.link),
    };
  });

  // Filter with a paper trail. A volunteer who types "TBD" or "Nov 3rd" in the
  // date column gets no feedback anywhere — the event just never appears — so
  // every skipped row is named, and unparseable dates are called out as the
  // thing to fix in the sheet.
  const badDates = [];
  events = events.filter(ev => {
    if (!ev.name || /^example[:\s]/i.test(ev.name)) return false; // blank + example rows, by design
    if (!ev.dateObj || isNaN(ev.dateObj)) {
      badDates.push(ev);
      return false;
    }
    if (ev.dateObj < today) return false;                         // past events, by design
    return true;
  });
  for (const ev of badDates) {
    console.error(`SKIPPED (unparseable date): "${ev.name}" — fix the Date cell in the Google Sheet for this row`);
  }

  events.sort((a, b) => a.dateObj - b.dateObj);                   // soonest first

  const seen = new Set();                                         // de-dupe on (name + date)
  events = events.filter(ev => {
    const key = ev.name.toLowerCase() + '|' + ymd(ev.dateObj);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  console.error(`Rendering ${events.length} upcoming event(s): ${events.map(e => e.name + ' (' + ymd(e.dateObj) + ')').join('; ') || '(none)'}`);

  const block = buildBlock(events.map(renderCard));

  let html = fs.readFileSync(EVENTS_FILE, 'utf8');
  if (html.includes(START) && html.includes(END)) {
    html = html.replace(new RegExp(escapeRe(START) + '[\\s\\S]*?' + escapeRe(END)), START + block + END);
  } else {
    const anchor = html.match(/<h2[^>]*>\s*Upcoming Events\s*<\/h2>/i);
    if (!anchor) throw new Error('Could not find the "Upcoming Events" heading to anchor the AUTO-EVENTS block.');
    const at = anchor.index + anchor[0].length;
    html = html.slice(0, at) + '\n\n        ' + START + block + END + '\n' + html.slice(at);
  }

  fs.writeFileSync(EVENTS_FILE, html);
  console.error(`Wrote ${EVENTS_FILE} with ${events.length} auto event card(s).`);
}

main().catch(err => { console.error('BUILD FAILED:', err.message || err); process.exit(1); });
