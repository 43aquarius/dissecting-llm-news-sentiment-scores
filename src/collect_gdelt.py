#!/usr/bin/env python3
"""Collect firm-specific news headlines from GDELT DOC 2.0 API (v2: resilient).
- Incremental save after every firm-window
- Exponential backoff on 429 (30/60/120s)
- Resume support via progress file
Output: /home/z/my-project/data/gdelt_news.json + /home/z/my-project/data/gdelt_progress.json
"""
import json
import time
import os
import requests
from datetime import datetime

OUT_DIR = "/home/z/my-project/data"
os.makedirs(OUT_DIR, exist_ok=True)

FIRMS = [
    ("AAPL", "(Apple OR AAPL)"), ("MSFT", "(Microsoft OR MSFT)"), ("NVDA", "(Nvidia OR NVDA)"),
    ("GOOGL", "(Google OR Alphabet OR GOOGL)"), ("AMZN", "(Amazon OR AMZN)"),
    ("META", "(Meta OR Facebook)"), ("TSLA", "(Tesla OR TSLA)"), ("AVGO", "(Broadcom OR AVGO)"),
    ("AMD", "(AMD)"), ("NFLX", "(Netflix OR NFLX)"), ("INTC", "(Intel OR INTC)"),
    ("ORCL", "(Oracle OR ORCL)"), ("CRM", "(Salesforce OR CRM)"), ("ADBE", "(Adobe OR ADBE)"),
    ("QCOM", "(Qualcomm OR QCOM)"), ("IBM", "(IBM)"), ("JPM", "(JPMorgan OR JPM)"),
    ("BAC", "(\"Bank of America\" OR BAC)"), ("GS", "(Goldman OR GS)"), ("MS", "(Morgan OR MS)"),
    ("WFC", "(Wells OR WFC)"), ("V", "(Visa OR V)"), ("MA", "(Mastercard OR MA)"),
    ("XOM", "(Exxon OR XOM)"), ("CVX", "(Chevron OR CVX)"), ("PG", "(P&G OR Procter)"),
    ("KO", "(Coca-Cola OR Coke OR KO)"), ("WMT", "(Walmart OR WMT)"), ("COST", "(Costco OR COST)"),
    ("JNJ", "(Johnson&Johnson OR JNJ)"), ("LLY", "(\"Eli Lilly\" OR LLY)"), ("DIS", "(Disney OR DIS)"),
    ("BA", "(Boeing OR BA)"), ("CAT", "(Caterpillar OR CAT)"), ("GE", "(\"GE Aerospace\" OR GE)"),
    ("PFE", "(Pfizer OR PFE)"),
]

WINDOWS = [
    ("20260715000000", "20260731235959"),
    ("20260801000000", "20260831235959"),
    ("20260901000000", "20260930235959"),
    ("20261001000000", "20261014235959"),
]

MAXRECORDS = 60
BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

NEWS_PATH = f"{OUT_DIR}/gdelt_news.json"
PROG_PATH = f"{OUT_DIR}/gdelt_progress.json"


def load_state():
    articles = {}
    if os.path.exists(NEWS_PATH):
        for a in json.load(open(NEWS_PATH)):
            articles[a["url"]] = a
    done = set()
    if os.path.exists(PROG_PATH):
        done = set(json.load(open(PROG_PATH)).get("done", []))
    return articles, done


def save_state(articles, done):
    with open(NEWS_PATH, "w") as f:
        json.dump(list(articles.values()), f, ensure_ascii=False, indent=1)
    with open(PROG_PATH, "w") as f:
        json.dump({"done": sorted(done)}, f)


def fetch(query, start, end):
    """Fetch with exponential backoff on 429. Returns article list or None (fatal)."""
    backoffs = [30, 60, 120, 180]
    for attempt in range(6):
        try:
            r = requests.get(BASE, params={
                "query": f"{query} sourcelang:english", "mode": "artlist",
                "maxrecords": str(MAXRECORDS), "sort": "hybridrel", "format": "json",
                "startdatetime": start, "enddatetime": end,
            }, headers=HEADERS, timeout=40)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                return r.json().get("articles", [])
            if r.status_code == 429 or "limit requests" in r.text:
                wait = backoffs[min(attempt, len(backoffs) - 1)]
                print(f"    429: backing off {wait}s (attempt {attempt+1})", flush=True)
                time.sleep(wait)
                continue
            print(f"    status={r.status_code}: {r.text[:60]}", flush=True)
            time.sleep(10)
        except Exception as e:
            print(f"    err: {str(e)[:70]}", flush=True)
            time.sleep(10)
    return []


def main():
    articles, done = load_state()
    print(f"resume: {len(articles)} articles, {len(done)} firm-windows done", flush=True)
    for fi, (ticker, query) in enumerate(FIRMS):
        for (start, end) in WINDOWS:
            key = f"{ticker}_{start[:8]}"
            if key in done:
                continue
            arts = fetch(query, start, end)
            added = 0
            for a in arts:
                url = a.get("url", "")
                if not url or url in articles:
                    continue
                articles[url] = {
                    "ticker": ticker, "url": url,
                    "title": a.get("title", "").strip(),
                    "seendate": a.get("seendate", ""),
                    "domain": a.get("domain", ""),
                }
                added += 1
            done.add(key)
            save_state(articles, done)
            time.sleep(7)
        print(f"[{fi+1}/{len(FIRMS)}] {ticker}: +{added} (total {len(articles)})", flush=True)
    print(f"DONE: {len(articles)} unique articles", flush=True)


if __name__ == "__main__":
    main()
