#!/usr/bin/env python3
"""P1-1 step 1: extract the price-language headlines for manual verification.

Outputs data/priced_headlines.json with all in-window headlines matching the
audit_substantive.py PRICE_PAT regex, plus metadata (ticker, date, LLM scores
named/anon/reps, LM score, relevance) so each can be classified by hand.
"""
import json
import re

DATA = "/home/z/my-project/data"

PRICE_PAT = re.compile(
    r"\b(rose|rises?|risen|jump(?:s|ed|ing)?|surge[sd]?|surging|soar(?:s|ed|ing)?|"
    r"climb(?:s|ed|ing)?|rall(?:y|ies|ied|ing)|gain(?:s|ed|ing)?|fell|falls?|fallen|"
    r"drop(?:s|ped|ping)?|dropped|plunge[sd]?|plunging|sink[s]?|sank|sinking|slide[sd]?|"
    r"slump(?:s|ed|ing)?|tumbl(?:e|es|ed|ing)|crash(?:es|ed|ing)?|declin(?:e|es|ed|ing)|"
    r"rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)|spike[sd]?|spiking|dip(?:s|ped)?|"
    r"up\s?\d|down\s?\d|\d+%\s?(?:up|down)|hit\s+(?:a\s+)?(?:record|new|52)|"
    r"after\s+(?:earnings|results|guidance|beating|missing))\b", re.I)

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]

sc_named = json.load(open(f"{DATA}/llm_scores.json"))
sc_anon = json.load(open(f"{DATA}/llm_scores_anon.json"))
sc_r1 = json.load(open(f"{DATA}/llm_scores_rep1.json"))
sc_r2 = json.load(open(f"{DATA}/llm_scores_rep2.json"))
sc_r3 = json.load(open(f"{DATA}/llm_scores_rep3.json"))

rows = []
for i, a in enumerate(inwin):
    m = PRICE_PAT.search(a["title"])
    if not m:
        continue
    url = a["url"]
    rows.append({
        "iid": len(rows),
        "ticker": a["ticker"],
        "date_iso": a["date_iso"],
        "title": a["title"],
        "matched_pattern": m.group(0),
        "named": sc_named.get(url, {}).get("sentiment"),
        "anon": sc_anon.get(url, {}).get("sentiment"),
        "rep1": sc_r1.get(url, {}).get("sentiment"),
        "rep2": sc_r2.get(url, {}).get("sentiment"),
        "rep3": sc_r3.get(url, {}).get("sentiment"),
        "relevance": sc_named.get(url, {}).get("relevance"),
        "lm_tone": a.get("lm_tone"),
    })

json.dump(rows, open(f"{DATA}/priced_headlines.json", "w"), indent=1)
print(f"price-language headlines (regex classifier): {len(rows)} of {len(inwin)} "
      f"({100*len(rows)/len(inwin):.1f}%)")
# how many enter the rel>=30 trading-day sample?
import pandas as pd
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
fd = set(zip(panel.loc[panel["llm_sent_rel"].notna(), "ticker"],
              panel.loc[panel["llm_sent_rel"].notna(), "date"].dt.strftime("%Y-%m-%d")))
n_in_sample = sum(1 for r in rows if (r["ticker"], r["date_iso"]) in fd)
print(f"of these, in rel>=30 trading-day firm-day sample: {n_in_sample}")
print(f"score availability: named={sum(r['named'] is not None for r in rows)}, "
      f"anon={sum(r['anon'] is not None for r in rows)}")
