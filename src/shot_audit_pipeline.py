#!/usr/bin/env python3
"""Screenshot audit pipeline diagram at 2x scale."""
import asyncio
from playwright.async_api import async_playwright

HTML = "file:///home/z/my-project/data/figures/audit_pipeline.html"
OUT = "/home/z/my-project/data/figures/fig_audit_design.png"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(
            viewport={"width": 1240, "height": 760},
            device_scale_factor=2,
        )
        await page.goto(HTML, wait_until="networkidle")
        await page.wait_for_timeout(600)
        canvas = await page.query_selector(".canvas")
        await canvas.screenshot(path=OUT)
        await browser.close()
        print("saved:", OUT)


asyncio.run(main())
