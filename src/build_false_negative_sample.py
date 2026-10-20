#!/usr/bin/env python3
"""Build the false-negative sampling frame for the price-language classifier audit.

The 52-headline annotation sheet estimates the classifier's PRECISION. To estimate
its FALSE-NEGATIVE rate (realized-price headlines the regex MISSED), two human raters
label a seeded random sample of NON-flagged in-window headlines with the same P/E/D/N
codebook. This script draws that sample deterministically (seed 20261019) and writes
annotation_package/false_negative_sample.csv with the same layout as the main sheet.

The sample is drawn from headlines that (a) are in-window (341), (b) have relevance>=30
(the analysis filter), and (c) were NOT flagged by the regex. 50 headlines: two-rater
labeling takes ~30 minutes and bounds the miss rate's 95% CI to about ±14% at worst.
"""
import json
import numpy as np
import pandas as pd

DATA = "/home/z/my-project/data"
PKG = "/home/z/my-project/replication_package_v2/annotation_package"
N_SAMPLE = 50
SEED = 20261019

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
flagged_titles = set(a["title"] for a in json.load(open(f"{DATA}/priced_headlines.json")))
scores = json.load(open(f"{DATA}/llm_scores.json"))
rel = {u: (scores.get(u) or {}).get("relevance", 0) for u in [a["url"] for a in inwin]}

pool = [a for a in inwin if a["title"] not in flagged_titles and (rel.get(a["url"], 0) or 0) >= 30]
rng = np.random.default_rng(SEED)
idx = rng.choice(len(pool), size=min(N_SAMPLE, len(pool)), replace=False)
sample = [pool[i] for i in sorted(idx)]

rows = []
for k, a in enumerate(sample):
    rows.append({
        "iid": k,
        "ticker": a["ticker"],
        "date_iso": a["date_iso"],
        "title": a["title"].replace("\t", " ").strip(),
        "regex_flag": 0,
        "rater1_label": "", "rater2_label": "",
        "rater1_note": "", "rater2_note": "",
    })
df = pd.DataFrame(rows)
df.to_csv(f"{PKG}/false_negative_sample.csv", index=False)
print(f"pool of non-flagged relevance>=30 headlines: {len(pool)}")
print(f"wrote {len(df)} sampled headlines -> {PKG}/false_negative_sample.csv (seed {SEED})")
