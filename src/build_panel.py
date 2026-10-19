#!/usr/bin/env python3
"""LM dictionary sentiment scoring for news headlines + firm-day panel construction.

Stages:
1. Score all clean news headlines with Loughran-McDonald (2011) word lists
   (tone = (pos - neg) / total words, per LM 2011 methodology)
2. Build firm-day panel: merge LLM scores (if available) + LM scores with prices
3. Compute returns, controls (lagged ret, volatility, size proxy, market return)
Output: /home/z/my-project/data/panel.csv
"""
import json
import re
import csv
import pandas as pd
import numpy as np

DATA = "/home/z/my-project/data"


def load_lm_words():
    """Load positive/negative word lists from LM Master Dictionary."""
    df = pd.read_csv(f"{DATA}/lm_master_dict.csv", encoding="latin1", low_memory=False)
    neg = set(df.loc[df["Negative"] != 0, "Word"].astype(str).str.upper().str.strip())
    pos = set(df.loc[df["Positive"] != 0, "Word"].astype(str).str.upper().str.strip())
    print(f"LM dictionary: {len(neg)} negative, {len(pos)} positive words")
    return neg, pos


def lm_score_title(title, neg, pos):
    """LM 2011 tone for a headline: (#pos - #neg) / #words (word-level counting)."""
    words = re.findall(r"[A-Za-z]+", title.upper())
    if not words:
        return 0.0, 0
    n_pos = sum(1 for w in words if w in pos)
    n_neg = sum(1 for w in words if w in neg)
    tone = 100.0 * (n_pos - n_neg) / len(words)  # scale to match LLM -100..100 metric
    return tone, n_pos + n_neg


def parse_date(s):
    if not s:
        return None
    s = str(s).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return s[:10]
    months = {m.lower(): i for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
    mm = re.match(r"^([A-Za-z]{3})[a-z]*\s+(\d{1,2}),?\s+(\d{4})", s)
    if mm and mm.group(1).lower() in months:
        return f"{mm.group(3)}-{months[mm.group(1).lower()]:02d}-{int(mm.group(2)):02d}"
    return None


def main():
    # ---------- 1. LM scoring ----------
    articles = json.load(open(f"{DATA}/news_all.json"))
    neg, pos = load_lm_words()
    for a in articles:
        tone, nflag = lm_score_title(a["title"], neg, pos)
        a["lm_tone"] = round(tone, 2)
        a["lm_flagwords"] = nflag
        a["date_iso"] = parse_date(a["date"])
    json.dump(articles, open(f"{DATA}/news_scored.json", "w"), indent=1)

    dated = [a for a in articles if a["date_iso"]]
    print(f"articles: {len(articles)}, dated: {len(dated)}")
    in_window = [a for a in dated if "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
    print(f"in sample window (Jul 1 - Oct 14): {len(in_window)}")

    # ---------- 2. Load LLM scores if available ----------
    llm = {}
    try:
        llm = json.load(open(f"{DATA}/llm_scores.json"))
        print(f"LLM scores available: {len(llm)}")
    except FileNotFoundError:
        print("LLM scores not yet available")

    # ---------- 3. Build firm-day panel ----------
    prices = pd.read_csv(f"{DATA}/prices.csv", parse_dates=["date"])
    prices = prices.sort_values(["ticker", "date"])

    # returns and controls per firm
    prices["ret"] = prices.groupby("ticker")["close"].pct_change()
    prices["ret_overnight"] = prices["open"] / prices.groupby("ticker")["close"].shift(1) - 1
    prices["ret_intraday"] = prices["close"] / prices["open"] - 1
    prices["ret_lag1"] = prices.groupby("ticker")["ret"].shift(1)
    prices["vol_21"] = prices.groupby("ticker")["ret"].transform(
        lambda x: x.rolling(21, min_periods=10).std() * np.sqrt(252))
    prices["dollar_vol"] = prices["close"] * prices["volume"]
    prices["size_proxy"] = prices.groupby("ticker")["dollar_vol"].transform("mean")  # avg over sample
    prices["mkt_ew"] = prices.groupby("date")["ret"].transform("mean")  # equal-weight market
    # rank-based scaled sentiment: standardized within article pool handled later

    # firm-day news aggregation
    rows = []
    for a in in_window:
        s = llm.get(a["url"], {})
        rows.append({
            "ticker": a["ticker"], "date": a["date_iso"],
            "llm_sent": s.get("sentiment"), "llm_rel": s.get("relevance"),
            "lm_tone": a["lm_tone"],
            "url": a["url"], "title": a["title"],
        })
    news_df = pd.DataFrame(rows)
    if len(news_df) == 0:
        print("NO dated news in window - panel cannot be built")
        return

    # aggregate per firm-day
    agg = news_df.groupby(["ticker", "date"]).agg(
        llm_sent=("llm_sent", "mean"),
        llm_rel_mean=("llm_rel", "mean"),
        lm_tone=("lm_tone", "mean"),
        n_news=("url", "count"),
    ).reset_index()

    # relevance-filtered LLM sentiment (relevance >= 30)
    if "llm_rel" in news_df.columns:
        hi_rel = news_df[pd.to_numeric(news_df["llm_rel"], errors="coerce") >= 30]
        if len(hi_rel):
            agg2 = hi_rel.groupby(["ticker", "date"]).agg(llm_sent_rel=("llm_sent", "mean")).reset_index()
            agg = agg.merge(agg2, on=["ticker", "date"], how="left")
        else:
            agg["llm_sent_rel"] = np.nan
    else:
        agg["llm_sent_rel"] = np.nan

    # firm-day panel: prices x news
    news_df["date"] = pd.to_datetime(news_df["date"])
    panel = prices.merge(
        agg.assign(date=lambda d: pd.to_datetime(d["date"])),
        on=["ticker", "date"], how="left")
    panel["has_news"] = panel["llm_sent"].notna() | panel["lm_tone"].notna()

    panel.to_csv(f"{DATA}/panel.csv", index=False)
    print(f"\npanel: {len(panel)} firm-days, {panel['has_news'].sum()} with news")
    print(f"firm-day with LLM sentiment: {panel['llm_sent'].notna().sum()}")
    print(f"firm-day with LM tone: {panel['lm_tone'].notna().sum()}")
    print(f"date range: {panel['date'].min().date()} .. {panel['date'].max().date()}")


if __name__ == "__main__":
    main()
