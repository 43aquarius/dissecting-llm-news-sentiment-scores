#!/usr/bin/env python3
"""Screenshot pipeline diagram HTML at 2x device scale (academic brief Path B)."""
import asyncio
import sys
from playwright.async_api import async_playwright

HTML = "file:///home/z/my-project/data/figures/pipeline.html"
OUT = "/home/z/my-project/data/figures/fig_pipeline.png"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(
            viewport={"width": 1000, "height": 420},
            device_scale_factor=2,
        )
        await page.goto(HTML, wait_until="networkidle")
        await page.wait_for_timeout(800)
        canvas = await page.query_selector(".canvas")
        await canvas.screenshot(path=OUT)
        await browser.close()
        print("saved:", OUT)


asyncio.run(main())
