#!/usr/bin/env node
/**
 * build-member-portal.js
 * Fetches LWVNC member portal content from a published Google Sheet (CSV per tab),
 * builds the HTML page, and writes members-source.html to stdout or a file.
 *
 * Usage: node scripts/build-member-portal.js > members-source.html
 *
 * Tab GIDs are hardcoded from the published sheet. If tabs are reordered or
 * recreated in Google Sheets, these GIDs will need updating.
 */

// ── Published sheet base URL and tab GIDs ──
const BASE = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vROP_1R5IJfAbTQk8Lm5gHn_cfqF4PLnbZqZ37kLw0sdV1rxHeU9Cx5_98-HM1f3g/pub?output=csv';

const TABS = {
  announcements:      '135605888',
  officers:           '2041641894',
  committees:         '1068037234',
  memberEvents:       '391099368',
  meetingMinutes:     '1996909618',
  boardDocuments:     '1970422255',
  newsletterArchive:  '261506271',
  membershipRoster:   '754158794',
  positions:          '1230793155',
  resources:          '186492680',
};

// ── CSV fetcher (uses Node 20 native fetch — auto-follows redirects) ──
async function fetchCSV(gid) {
  const url = `${BASE}&gid=${gid}`;
  const res = await fetch(url, {
    headers: { 'User-Agent': 'LWVNC-Builder/1.0' },
    redirect: 'follow',
  });
  if (!res.ok) throw new Error(`Failed to fetch gid=${gid}: ${res.status}`);
  return await res.text();
}

// ── Simple CSV parser (handles quoted fields with commas) ──
function parseCSV(text) {
  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  if (lines.length < 2) return []; // header only or empty

  const rows = [];
  for (let i = 1; i < lines.length; i++) { // skip header row
    const line = lines[i].trim();
    if (!line) continue;

    const fields = [];
    let field = '';
    let inQuotes = false;
    for (let j = 0; j < line.length; j++) {
      const ch = line[j];
      if (inQuotes) {
        if (ch === '"' && line[j + 1] === '"') {
          field += '"';
          j++;
        } else if (ch === '"') {
          inQuotes = false;
        } else {
          field += ch;
        }
      } else {
        if (ch === '"') {
          inQuotes = true;
        } else if (ch === ',') {
          fields.push(field.trim());
          field = '';
        } else {
          field += ch;
        }
      }
    }
    fields.push(field.trim());
    rows.push(fields);
  }
  return rows;
}

// ── HTML escaping ──
function esc(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── HTML builders for each section ──

function buildAnnouncements(rows) {
  if (!rows.length || (rows.length === 1 && rows[0][0].startsWith('Example:'))) {
    return '<p style="margin-bottom: 0; color: #333;">No current announcements. Check back for updates on upcoming member events, volunteer opportunities, and League business.</p>';
  }
  return rows
    .filter(r => r[0] && !r[0].startsWith('Example:'))
    .map(r => `<p style="margin-bottom: 10px; color: #333;">${esc(r[0])}</p>`)
    .join('\n            ');
}

function buildOfficers(rows) {
  return rows
    .filter(r => r[0] && r[0] !== 'Example:' && !r[1]?.startsWith('Example'))
    .map(r => {
      const role = esc(r[0] || '');
      const name = esc(r[1] || '');
      const email = r[2] || '';
      let emailHTML = email ? `<p style="margin-bottom: 0;"><a href="mailto:${esc(email)}">${esc(email)}</a></p>` : '';
      return `<div style="border: 1px solid #e0e0e0; padding: 20px;">
                <h3 style="margin-top: 0; color: #1B3A6B;">${role}</h3>
                <p style="margin-bottom: 5px;">${name}</p>
                ${emailHTML}
            </div>`;
    })
    .join('\n            ');
}

function buildCommittees(rows) {
  return rows
    .filter(r => r[0] && !r[0].startsWith('Example'))
    .map(r => {
      const comm = esc(r[0] || '');
      const chair = esc(r[1] || '');
      const desc = esc(r[2] || '');
      return `<div style="border: 1px solid #e0e0e0; padding: 20px;">
                <h3 style="margin-top: 0; color: #1B3A6B;">${comm}</h3>
                <p style="margin-bottom: 5px; font-weight: 600;">Chair: ${chair}</p>
                <p style="margin-bottom: 0; color: #666; font-size: 0.9em;">${desc}</p>
            </div>`;
    })
    .join('\n            ');
}

function buildMemberEvents(rows) {
  const real = rows.filter(r => r[0] && !r[0].startsWith('Example') && r[0] !== 'May Board Meeting');
  if (!real.length) {
    return '<p style="color: #666; font-style: italic; margin-bottom: 0;">No upcoming member events. Board meetings, committee meetings, and planning sessions will be posted here.</p>';
  }
  return real.map(r => {
    const title = esc(r[0] || '');
    const date = esc(r[1] || '');
    const time = esc(r[2] || '');
    const location = esc(r[3] || '');
    const link = r[4] || '';
    let linkHTML = link && !link.includes('example') ? `<br><a href="${esc(link)}" target="_blank" style="color: #1B3A6B; font-weight: 600;">Join / RSVP &rarr;</a>` : '';
    return `<div style="padding: 12px 0; border-bottom: 1px solid #eee;">
                <strong>${title}</strong>
                <br><span style="color: #666; font-size: 0.9em;">${date}${time ? ' at ' + time : ''}${location ? ' — ' + location : ''}</span>
                ${linkHTML}
            </div>`;
  }).join('\n            ');
}

function buildLinkedList(rows, placeholder) {
  // Filter out example/placeholder rows by checking the link column for "example"
  // or the title starting with "Example". Real entries with real URLs pass through.
  const real = rows.filter(r => r[0] && !r[0].startsWith('Example') && !(r[r.length - 1] || '').includes('example'));
  if (!real.length) {
    return `<p style="color: #666; font-style: italic; margin-bottom: 0;">${placeholder}</p>`;
  }
  // Sort by date column (r[1]) newest first when parseable dates exist
  const sorted = [...real].sort((a, b) => {
    const da = Date.parse(a[1]), db = Date.parse(b[1]);
    if (!isNaN(da) && !isNaN(db)) return db - da; // newest first
    return 0; // keep original order if dates aren't parseable
  });
  return sorted.map(r => {
    const title = esc(r[0] || '');
    const dateOrCat = esc(r[1] || '');
    const link = r[r.length - 1] || '';
    let linkHTML = link && !link.includes('example') ? `<br><a href="${esc(link)}" target="_blank" style="color: #1B3A6B;">View &rarr;</a>` : '';
    return `<div style="padding: 12px 0; border-bottom: 1px solid #eee;">
                <strong>${title}</strong>
                <br><span style="color: #666; font-size: 0.9em;">${dateOrCat}</span>
                ${linkHTML}
            </div>`;
  }).join('\n            ');
}

function buildRoster(rows) {
  const real = rows.filter(r => r[0] && !r[0].startsWith('Jane Smith') && !r[0].startsWith('Example'));
  if (!real.length) {
    return `<tr>
                        <td style="padding: 10px 12px; border-bottom: 1px solid #eee;" colspan="3">
                            <span style="color: #666; font-style: italic;">Roster will be populated by the membership chair.</span>
                        </td>
                    </tr>`;
  }
  return real.map(r => {
    return `<tr>
                        <td style="padding: 10px 12px; border-bottom: 1px solid #eee;">${esc(r[0] || '')}</td>
                        <td style="padding: 10px 12px; border-bottom: 1px solid #eee;"><a href="mailto:${esc(r[1] || '')}">${esc(r[1] || '')}</a></td>
                        <td style="padding: 10px 12px; border-bottom: 1px solid #eee;">${esc(r[2] || '')}</td>
                    </tr>`;
  }).join('\n                    ');
}

function buildPositions(rows) {
  const real = rows.filter(r => r[0] && !r[0].startsWith('Voting Rights'));
  if (!real.length) {
    return '<p style="color: #666; font-style: italic; margin-bottom: 0;">Current positions and priorities will be posted here.</p>';
  }
  return real.map(r => {
    return `<div style="padding: 12px 0; border-bottom: 1px solid #eee;">
                <strong style="color: #1B3A6B;">${esc(r[0] || '')}</strong>
                <br><span style="color: #333; font-size: 0.95em;">${esc(r[1] || '')}</span>
            </div>`;
  }).join('\n            ');
}

function buildResources(rows) {
  return rows
    .filter(r => r[0] && !r[0].startsWith('Example'))
    .map(r => {
      const title = esc(r[0] || '');
      const desc = esc(r[1] || '');
      const link = r[2] || '';
      return `<div style="border: 1px solid #e0e0e0; padding: 20px;">
                <h3 style="margin-top: 0; color: #1B3A6B;">${title}</h3>
                <p>${desc}</p>
                <a href="${esc(link)}" target="_blank" style="color: #1B3A6B; font-weight: 600;">Open &rarr;</a>
            </div>`;
    })
    .join('\n            ');
}

// ── Main ──
async function main() {
  console.error('Fetching tab data...');

  // Fetch all tabs in parallel
  const data = {};
  const entries = Object.entries(TABS);
  const results = await Promise.all(entries.map(([, gid]) => fetchCSV(gid)));
  entries.forEach(([key], i) => {
    data[key] = parseCSV(results[i]);
    console.error(`  ${key}: ${data[key].length} rows`);
  });

  // Build HTML
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Member Portal - LWV Newport County</title>
    <link rel="stylesheet" href="styles.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <header class="site-header">
        <div class="container">
            <a href="index.html" class="logo">
                <img src="images/logo-newport-county-transparent.png" alt="League of Women Voters of Newport County">
            </a>
        </div>
    </header>

    <nav>
        <div class="container">
            <button class="nav-toggle" aria-label="Toggle navigation" onclick="this.classList.toggle('open'); document.querySelector('nav ul').classList.toggle('open')">
                <span></span>
                <span></span>
                <span></span>
            </button>
            <ul>
                <li><a href="index.html">Home</a></li>
                <li><a href="about.html">About</a></li>
                <li><a href="vote.html">Voter Resources</a></li>
                <li><a href="events.html">Events</a></li>
                <li><a href="issues.html">Issues &amp; Advocacy</a></li>
                <li><a href="get-involved.html">Get Involved</a></li>
                <li><a href="news.html">News</a></li>
                <li><a href="action-alerts.html">Action Alerts</a></li>
                <li><a href="members.html" class="active">Members</a></li>
            </ul>
        </div>
    </nav>

    <div class="page-header">
        <h1>Member Portal</h1>
        <p class="lead">Resources and information for LWVNC members.</p>
    </div>

    <div class="container" style="max-width: 900px; padding: 60px 20px;">

        <!-- ANNOUNCEMENTS -->
        <div style="background: #fffbeb; border: 1px solid #C5A028; padding: 25px; margin-bottom: 40px;">
            <h2 style="margin-top: 0; color: #1B3A6B;">Member Announcements</h2>
            ${buildAnnouncements(data.announcements)}
        </div>

        <!-- OFFICERS & BOARD -->
        <h2 style="color: #1B3A6B;">Officers &amp; Board</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 40px;">
            ${buildOfficers(data.officers)}
        </div>

        <!-- COMMITTEES -->
        <h2 style="color: #1B3A6B;">Committees</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 40px;">
            ${buildCommittees(data.committees)}
        </div>

        <!-- MEMBER EVENTS -->
        <h2 style="color: #1B3A6B;">Upcoming Member Events</h2>
        <div style="border: 1px solid #e0e0e0; padding: 25px; margin-bottom: 40px;">
            ${buildMemberEvents(data.memberEvents)}
        </div>

        <!-- MEETING MINUTES -->
        <h2 style="color: #1B3A6B;">Meeting Minutes</h2>
        <div style="border: 1px solid #e0e0e0; padding: 25px; margin-bottom: 40px;">
            ${buildLinkedList(data.meetingMinutes, 'Meeting minutes will be posted here after each general and board meeting.')}
        </div>

        <!-- BOARD DOCUMENTS -->
        <h2 style="color: #1B3A6B;">Board Documents</h2>
        <div style="border: 1px solid #e0e0e0; padding: 25px; margin-bottom: 40px;">
            ${buildLinkedList(data.boardDocuments, 'Board agendas, reports, and governance documents will be posted here.')}
        </div>

        <!-- NEWSLETTER ARCHIVE -->
        <h2 style="color: #1B3A6B;">Newsletter Archive</h2>
        <div style="border: 1px solid #e0e0e0; padding: 25px; margin-bottom: 40px;">
            ${buildLinkedList(data.newsletterArchive, 'Past issues of the News &amp; Notes newsletter will be archived here.')}
        </div>

        <!-- MEMBERSHIP ROSTER -->
        <h2 style="color: #1B3A6B;">Membership Roster</h2>
        <div style="border: 1px solid #e0e0e0; padding: 25px; margin-bottom: 40px;">
            <p style="color: #666; font-size: 0.85em; margin-bottom: 15px;">This directory is for LWVNC member use only. Please do not share outside the League.</p>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background: #f0f4f8;">
                        <th style="text-align: left; padding: 10px 12px; border-bottom: 2px solid #1B3A6B; color: #1B3A6B;">Name</th>
                        <th style="text-align: left; padding: 10px 12px; border-bottom: 2px solid #1B3A6B; color: #1B3A6B;">Email</th>
                        <th style="text-align: left; padding: 10px 12px; border-bottom: 2px solid #1B3A6B; color: #1B3A6B;">Town</th>
                    </tr>
                </thead>
                <tbody>
                    ${buildRoster(data.membershipRoster)}
                </tbody>
            </table>
        </div>

        <!-- POSITIONS -->
        <h2 style="color: #1B3A6B;">Positions &amp; Legislative Priorities</h2>
        <div style="border: 1px solid #e0e0e0; padding: 25px; margin-bottom: 40px;">
            <p style="color: #666; font-size: 0.9em; margin-bottom: 15px;">Positions adopted through League study and member consensus. These guide our advocacy and public communications.</p>
            ${buildPositions(data.positions)}
        </div>

        <!-- RESOURCES -->
        <h2 style="color: #1B3A6B;">Member Resources</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 40px;">
            ${buildResources(data.resources)}
        </div>

        <!-- BYLAWS -->
        <h2 style="color: #1B3A6B;">Bylaws &amp; Governance</h2>
        <div style="border: 1px solid #e0e0e0; padding: 25px; margin-bottom: 40px;">
            <p style="color: #666; font-style: italic; margin-bottom: 0;">Bylaws, standing rules, and governance documents will be posted here.</p>
        </div>

    </div>

    <!-- FOOTER -->
    <footer>
        <div class="container">
            <div>
                <h4>League of Women Voters of Newport County</h4>
                <p>A nonpartisan political organization encouraging informed and active participation in government.</p>
                <p style="margin-top: 20px;"><strong>Serving:</strong> Newport, Jamestown, Little Compton, Middletown, Portsmouth, and Tiverton</p>
                <h4 style="margin-top: 30px;">Newsletter Signup</h4>
                <p>Stay informed with our monthly NEWS and NOTES newsletter.</p>
                <a href="get-involved.html" class="btn" style="margin-top: 10px; display: inline-flex;">Subscribe</a>
            </div>
            <div>
                <h4>Quick Links</h4>
                <a href="https://vote.sos.ri.gov/Voter/RegisterToVote" target="_blank">Register to Vote</a>
                <a href="https://vote411.org" target="_blank">Vote411.org</a>
                <a href="https://www.lwv.org" target="_blank">LWV National</a>
                <a href="https://my.lwv.org/rhode-island" target="_blank">LWV Rhode Island</a>
                <a href="https://www.facebook.com/LWVNewportCounty/" target="_blank">Facebook</a>
            </div>
            <div>
                <h4>Contact</h4>
                <p><strong>General:</strong><br><a href="mailto:lwvnewportcounty@gmail.com">lwvnewportcounty@gmail.com</a></p>
                <p style="margin-top: 15px;"><strong>President:</strong><br>Christine Stenning<br><a href="mailto:presidentlwvnc25@gmail.com">presidentlwvnc25@gmail.com</a></p>
                <p style="margin-top: 15px;"><strong>Treasurer:</strong><br>Becky McSweeney<br><a href="mailto:rcmcsw@gmail.com">rcmcsw@gmail.com</a></p>
            </div>
        </div>
        <div class="footer-bottom">
            <p>&copy; 2026 League of Women Voters of Newport County. All rights reserved.</p>
            <p>A nonpartisan, nonprofit organization. | <a href="about.html">About Us</a> | <a href="get-involved.html">Get Involved</a></p>
        </div>
    </footer>
</body>
</html>`;

  // Write to file or stdout
  const outFile = process.argv[2] || null;
  if (outFile) {
    require('fs').writeFileSync(outFile, html);
    console.error(`Written to ${outFile}`);
  } else {
    process.stdout.write(html);
  }
}

main().catch(err => {
  console.error('BUILD FAILED:', err);
  process.exit(1);
});
