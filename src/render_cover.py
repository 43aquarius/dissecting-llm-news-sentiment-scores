#!/usr/bin/env python3
"""Render cover.html -> cover.pdf via Playwright (A4 @96dpi = 794x1123 px)."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 794, "height": 1123})
    pg.goto("file:///home/z/my-project/paper/cover.html")
    pg.wait_for_timeout(2500)  # webfonts
    pg.pdf(path="/home/z/my-project/paper/cover.pdf",
           width="794px", height="1123px",
           print_background=True,
           margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    b.close()
print("cover.pdf rendered")
