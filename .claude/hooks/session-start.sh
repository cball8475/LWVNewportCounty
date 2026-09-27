#!/bin/bash
# SessionStart hook for Claude Code on the web: LWV Newport County site.
#
# 1. Installs the Python packages this repo's scripts need, skipping any that
#    are already present so cached containers start fast:
#      requests, beautifulsoup4, lxml  scripts/fetch_lwvus.py (same set as lwvus-news.yml)
#      segno, pymupdf                  print/forum-flyers-2026/source/build_flyers.py
#      segno, pillow                   print/palm-card-2026/source/build_card.py
#      opencv-python-headless          flyer QR scan-back check (optional; the build skips it if missing)
# 2. Exposes the globally installed Playwright to `node` scripts (render checks).
# 3. Prints the site-health digest (scripts/site_health.py). Hook stdout lands in
#    Claude's context, so stale events, cut-off pages and failed workflows get
#    noticed at the start of every session.
#
# Package installs log to stderr so only the digest reaches Claude's context.
# Nothing here may fail the session: every step falls back to a note.
set -euo pipefail

# Web sessions only. Local machines manage their own environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# `has MODULE` is silent either way: some imports print warnings on success
# (PyMuPDF's old `fitz` name does), and stdout here goes to Claude's context.
has() { python3 -c "import $1" >/dev/null 2>&1; }
pip_install() { pip3 install --quiet --disable-pip-version-check --root-user-action=ignore "$@" >&2; }

missing=()
has requests || missing+=(requests)
has bs4      || missing+=(beautifulsoup4)
has lxml     || missing+=(lxml)
has segno    || missing+=(segno)
has pymupdf  || missing+=(pymupdf)
has PIL      || missing+=(pillow)
if [ "${#missing[@]}" -gt 0 ]; then
  pip_install "${missing[@]}" \
    || echo "Note: pip couldn't install ${missing[*]}; the news fetcher or print builds may not run."
fi
has cv2 || pip_install opencv-python-headless \
  || echo "Note: opencv-python-headless not installed; the flyer build will skip its QR scan-back check."

# Let `node` scripts require('playwright') from the global install (Chromium is preinstalled).
if [ -n "${CLAUDE_ENV_FILE:-}" ] && command -v npm >/dev/null 2>&1; then
  echo "export NODE_PATH=\"$(npm root -g)\"" >> "$CLAUDE_ENV_FILE"
fi

python3 scripts/site_health.py || echo "Note: scripts/site_health.py didn't run."
