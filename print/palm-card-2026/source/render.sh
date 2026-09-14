#!/bin/bash
set -e
CHROME=${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}
cd "$(dirname "$0")/build"
for f in card-*.html; do
  base="${f%.html}"
  "$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
    --disable-dev-shm-usage --font-render-hinting=none --virtual-time-budget=10000 \
    --no-pdf-header-footer --print-to-pdf-no-header \
    --print-to-pdf="$base.pdf" "file://$PWD/$f" >/dev/null 2>&1
  echo "rendered $base.pdf ($(stat -c%s "$base.pdf") bytes)"
done
