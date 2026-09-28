#!/usr/bin/env python3
"""Report the rendered height of each flyer section, to keep pages from overflowing."""
import sys, os, glob
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SEL = [".page", ".header", ".body", ".kicker", "h1", "h2", ".lede",
       ".card", ".cards", ".banner", ".partners", ".footer"]

def main(paths):
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium", args=["--no-sandbox"])
        pg = b.new_page(viewport={"width": 816, "height": 1056})
        for path in paths:
            pg.goto("file://" + os.path.abspath(path))
            print("\n==", os.path.basename(path))
            scroll = pg.evaluate("document.querySelector('.body').scrollHeight")
            client = pg.evaluate("document.querySelector('.body').clientHeight")
            print("   .body content %spx vs available %spx  -> overflow %spx"
                  % (scroll, client, scroll - client))
            for s in SEL:
                el = pg.query_selector(s)
                if not el:
                    continue
                bb = el.bounding_box()
                print("   %-10s top=%7.1f  h=%6.1f  bottom=%7.1f"
                      % (s, bb["y"], bb["height"], bb["y"] + bb["height"]))
        b.close()

if __name__ == "__main__":
    args = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, "out", "*.html")))
    main(args)
