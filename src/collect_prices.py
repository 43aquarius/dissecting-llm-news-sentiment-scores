#!/usr/bin/env python3
"""Collect daily stock prices from NASDAQ public API + FRED market data.
Sample: 36 large-cap US firms, window 2026-07-01 to 2026-10-14.
Output: /home/z/my-project/data/prices.csv (long format), /home/z/my-project/data/market.csv
"""
import json
import time
import os
import csv
import requests
from datetime import datetime

OUT_DIR = "/home/z/my-project/data"
os.makedirs(OUT_DIR, exist_ok=True)

TICKERS = [
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "Nvidia"), ("GOOGL", "Alphabet Google"),
    ("AMZN", "Amazon"), ("META", "Meta Platforms"), ("TSLA", "Tesla"), ("AVGO", "Broadcom"),
    ("AMD", "AMD"), ("NFLX", "Netflix"), ("INTC", "Intel"), ("ORCL", "Oracle"),
    ("CRM", "Salesforce"), ("ADBE", "Adobe"), ("QCOM", "Qualcomm"), ("IBM", "IBM"),
    ("JPM", "JPMorgan"), ("BAC", "Bank of America"), ("GS", "Goldman Sachs"), ("MS", "Morgan Stanley"),
    ("WFC", "Wells Fargo"), ("V", "Visa"), ("MA", "Mastercard"), ("XOM", "Exxon Mobil"),
    ("CVX", "Chevron"), ("PG", "Procter Gamble"), ("KO", "Coca-Cola"), ("WMT", "Walmart"),
    ("COST", "Costco"), ("JNJ", "Johnson Johnson"), ("LLY", "Eli Lilly"), ("DIS", "Disney"),
    ("BA", "Boeing"), ("CAT", "Caterpillar"), ("GE", "GE Aerospace"), ("PFE", "Pfizer"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://www.nasdaq.com",
    "Referer": "https://www.nasdaq.com/",
}

FROM, TO = "2026-07-01", "2026-10-14"


def num(s):
    if s is None:
        return None
    s = str(s).replace("$", "").replace(",", "").replace("%", "").strip()
    if s in ("", "N/A", "--"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_ticker(ticker):
    url = f"https://api.nasdaq.com/api/quote/{ticker}/historical"
    params = {"assetclass": "stocks", "fromdate": FROM, "todate": TO, "limit": "200"}
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=25)
            if r.status_code != 200:
                time.sleep(3)
                continue
            j = r.json()
            rows = j["data"]["tradesTable"]["rows"]
            out = []
            for row in rows:
                d = datetime.strptime(row["date"], "%m/%d/%Y").date()
                out.append({
                    "ticker": ticker, "date": d.isoformat(),
                    "close": num(row.get("close")), "open": num(row.get("open")),
                    "high": num(row.get("high")), "low": num(row.get("low")),
                    "volume": num(row.get("volume")),
                })
            return out
        except Exception as e:
            print(f"  attempt {attempt+1} failed for {ticker}: {str(e)[:80]}")
            time.sleep(4)
    return None


def main():
    all_rows = []
    failures = []
    # incremental save: load existing progress
    done_path = f"{OUT_DIR}/prices.csv"
    done_tickers = set()
    if os.path.exists(done_path):
        with open(done_path) as f:
            for line in f.readlines()[1:]:
                done_tickers.add(line.split(",")[0])
    if done_tickers:
        print(f"resuming, {len(done_tickers)} tickers already done: {sorted(done_tickers)}")
    for i, (t, name) in enumerate(TICKERS):
        if t in done_tickers:
            continue
        rows = fetch_ticker(t)
        if rows:
            all_rows = rows
            with open(done_path, "a", newline="") as f:
                exists = os.path.exists(done_path) and os.path.getsize(done_path) > 0
                w = csv.DictWriter(f, fieldnames=["ticker", "date", "close", "open", "high", "low", "volume"])
                if not exists:
                    w.writeheader()
                w.writerows(rows)
            print(f"[{i+1}/{len(TICKERS)}] {t}: {len(rows)} days saved", flush=True)
        else:
            failures.append(t)
            print(f"[{i+1}/{len(TICKERS)}] {t}: FAILED", flush=True)
        time.sleep(1.2)
    print(f"\nprices.csv updated, failures: {failures}", flush=True)

    # save ticker universe (only when all done or at end)
    with open(f"{OUT_DIR}/universe.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "company"])
        for t, n in TICKERS:
            if t not in failures:
                w.writerow([t, n])
    print("universe.csv saved", flush=True)

    # FRED market data (skip if exists)
    fred_series = {"SP500": "sp500", "VIXCLS": "vix", "NASDAQCOM": "nasdaq", "DGS10": "dgs10", "DGS2": "dgs2"}
    for code, short in fred_series.items():
        path = f"{OUT_DIR}/market_{short}.csv"
        if os.path.exists(path) and os.path.getsize(path) > 100:
            print(f"FRED {code} cached, skip")
            continue
        try:
            r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}",
                             headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            lines = r.text.strip().split("\n")
            with open(path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["date", short])
                for line in lines[1:]:
                    d, v = line.split(",")
                    if v not in (".", "") and d >= "2026-06-25":
                        w.writerow([d, v])
            print(f"FRED {code} saved", flush=True)
        except Exception as e:
            print(f"FRED {code} FAILED: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
