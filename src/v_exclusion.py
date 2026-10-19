#!/usr/bin/env python3
"""P0-7: Visa (ticker V) anonymization failure — quantification and robustness.

llm_score_v2.mjs ALIASES has V: [] (no "Visa" alias). All 10 in-window V
headlines contain the word "Visa" but never the standalone all-caps token "V",
so the anonymization procedure is a NO-OP for ticker V: the "anonymized" text
still contains the company name. 5 of the 10 are U.S. State Department "Visa
Bulletin" (immigration) headlines — non-corporate corpus pollution.

This script computes the numbers the paper needs for the disclosure and the
excluding-V robustness rows, and the third-party residual count under the TRUE
alias table (as executed), replacing the wrong-alias replication in the v2
revision script.
Output: data/v_exclusion.json
"""
import json
import re
import numpy as np
import pandas as pd
from scipy import stats

DATA = "/home/z/my-project/data"
arts = json.load(open(f"{DATA}/news_scored.json"))
orig = json.load(open(f"{DATA}/llm_scores.json"))
anon = json.load(open(f"{DATA}/llm_scores_anon.json"))
reps = {k: json.load(open(f"{DATA}/llm_scores_{k}.json")) for k in ("rep1", "rep2", "rep3")}

ALIASES_TRUE = {
    "AAPL": ["Apple"], "MSFT": ["Microsoft"], "NVDA": ["Nvidia", "NVIDIA"], "GOOGL": ["Alphabet", "Google"],
    "AMZN": ["Amazon"], "META": ["Meta Platforms", "Meta", "Facebook"], "TSLA": ["Tesla"], "AVGO": ["Broadcom"],
    "AMD": ["Advanced Micro Devices", "AMD"], "NFLX": ["Netflix"], "INTC": ["Intel"], "ORCL": ["Oracle"],
    "CRM": ["Salesforce"], "ADBE": ["Adobe"], "QCOM": ["Qualcomm"], "IBM": ["IBM"],
    "JPM": ["JPMorgan Chase", "JPMorgan", "J.P. Morgan"], "BAC": ["Bank of America", "BofA"],
    "GS": ["Goldman Sachs"], "MS": ["Morgan Stanley"], "WFC": ["Wells Fargo"], "V": [],
    "MA": ["Mastercard"], "XOM": ["Exxon Mobil", "Exxon"], "CVX": ["Chevron"], "PG": ["Procter & Gamble", "P&G"],
    "KO": ["Coca-Cola", "Coca Cola", "Coke"], "WMT": ["Walmart", "Wal-Mart"], "COST": ["Costco"],
    "JNJ": ["Johnson & Johnson", "Johnson and Johnson"], "LLY": ["Eli Lilly", "Lilly"], "DIS": ["Disney"],
    "BA": ["Boeing"], "CAT": ["Caterpillar"], "GE": ["GE Aerospace", "General Electric"], "PFE": ["Pfizer"]}

iw = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
v_arts = [a for a in iw if a["ticker"] == "V"]

def contains_focal_identifier(text, ticker, aliases):
    """Focal-firm residual: the anonymized text still identifies the focal firm.
    For V the company name 'Visa' must be checked explicitly (the executed alias
    table has no V names, which is exactly the failure being disclosed)."""
    if re.search(rf"\b{re.escape(ticker)}\b", text):
        return True
    names = list(aliases.get(ticker, []))
    if ticker == "V":
        names.append("Visa")  # the company name the procedure failed to remove
    for nm in names:
        if re.search(rf"\b{re.escape(nm)}\b", text, flags=re.I):
            return True
    return False

def anonymize_true(title, ticker):
    t = title
    t = re.sub(rf"\b{ticker}\b", "the company", t)
    for name in ALIASES_TRUE.get(ticker, []):
        t = re.sub(rf"\b{re.escape(name)}\b", "the company", t, flags=re.I)
    t = re.sub(r"\bthe company( the company)+\b", "the company", t, flags=re.I)
    return t

# ---- 1. quantify the V failure ----
n_v = len(v_arts)
n_v_leak = sum(1 for a in v_arts if contains_focal_identifier(
    anonymize_true(a["title"], "V"), "V", ALIASES_TRUE))
n_bulletin = sum(1 for a in v_arts if "bulletin" in a["title"].lower())
n_v_hirel = sum(1 for a in v_arts
                if (orig.get(a["url"], {}).get("relevance") or 0) >= 30)
bulletin_rel = [orig.get(a["url"], {}).get("relevance") for a in v_arts
                if "bulletin" in a["title"].lower()]
print(f"V in-window articles: {n_v}; anonymization no-op (still 'Visa'): {n_v_leak}")
print(f"  'Visa Bulletin' (immigration) pollution: {n_bulletin} (relevance: {bulletin_rel})")
print(f"  V articles passing rel>=30 (in regression sample): {n_v_hirel}")

# focal-firm leaks across all 35 other tickers (should be 0 by construction)
n_other_leak = sum(1 for a in iw if a["ticker"] != "V" and contains_focal_identifier(
    anonymize_true(a["title"], a["ticker"]), a["ticker"], ALIASES_TRUE))
print(f"focal leaks among other 35 tickers: {n_other_leak}")

# third-party residual under TRUE aliases
def third_party_hits(text, focal):
    hits = []
    for tk, names in ALIASES_TRUE.items():
        if tk == focal:
            continue
        if tk != "V" and re.search(rf"\b{re.escape(tk)}\b", text):
            hits.append(tk); continue
        for nm in names:
            if re.search(rf"\b{re.escape(nm)}\b", text, flags=re.I):
                hits.append(tk); break
    return hits

n_third = 0
for a in iw:
    if a["ticker"] == "V":
        continue
    at = anonymize_true(a["title"], a["ticker"])
    if third_party_hits(at, a["ticker"]):
        n_third += 1
print(f"third-party residual under TRUE alias table: {n_third}/341 = {n_third/341:.3f}")

# ---- 2. the illustrative case ----
case = None
for a in v_arts:
    t = a["title"]
    if "best quarter" in t.lower():
        case = {"title": t,
                "named": orig.get(a["url"], {}).get("sentiment"),
                "anon": anon.get(a["url"], {}).get("sentiment"),
                "relevance": orig.get(a["url"], {}).get("relevance")}
if case:
    print(f"illustrative case: {case}")

# ---- 3. robustness: excluding V from the article-level tests ----
rows = []
for a in iw:
    u = a["url"]
    rows.append({"ticker": a["ticker"],
                 "s_orig": orig.get(u, {}).get("sentiment"),
                 "s_anon": anon.get(u, {}).get("sentiment"),
                 "s_rep1": reps["rep1"].get(u, {}).get("sentiment"),
                 "s_rep2": reps["rep2"].get(u, {}).get("sentiment"),
                 "s_rep3": reps["rep3"].get(u, {}).get("sentiment"),
                 "relevance": orig.get(u, {}).get("relevance")})
X = pd.DataFrame(rows)
X["repm"] = X[["s_rep1", "s_rep2", "s_rep3"]].mean(axis=1)

def paired(sub, a_col, b_col):
    d = sub.dropna(subset=[a_col, b_col])
    t_ = stats.ttest_rel(d[a_col], d[b_col])
    w_ = stats.wilcoxon(d[a_col], d[b_col])
    return {"n": int(len(d)), "estimate": float(d[a_col].mean() - d[b_col].mean()),
            "t": float(t_.statistic), "p": float(t_.pvalue), "wilcoxon_p": float(w_.pvalue)}

out = {"v_failure": {
        "n_v_articles": n_v, "n_anon_noop_still_names_visa": n_v_leak,
        "n_visa_bulletin_immigration": n_bulletin, "bulletin_relevances": bulletin_rel,
        "n_v_in_rel30_sample": n_v_hirel, "n_focal_leaks_other_tickers": n_other_leak,
        "third_party_residual_true_aliases": {"n": n_third, "share": n_third / 341},
        "illustrative_case": case},
       "robustness": {}}
for label, sub in [("all_341", X), ("excluding_V", X[X["ticker"] != "V"])]:
    r = {"same_session_identity_repm_minus_anon": paired(sub, "repm", "s_anon"),
         "cross_session_published_shift_orig_minus_anon": paired(sub, "s_orig", "s_anon"),
         "session_drift_orig_minus_repm": paired(sub, "s_orig", "repm")}
    # ICC(2,3) named-only Oct16 and pooled variants
    def icc2k(cols):
        V = sub[cols].dropna().values
        if len(V) < 10:
            return None
        n_, k_ = V.shape
        gm = V.mean(); rm = V.mean(axis=1)
        msb = (k_ * ((rm - gm) ** 2).sum()) / (n_ - 1)
        msw = (V.var(axis=1, ddof=1) * (k_ - 1)).sum() / (n_ * (k_ - 1))
        return float((msb - msw) / (msb + (k_ - 1) * msw))
    r["icc_pooled_4draws"] = icc2k(["s_orig", "s_rep1", "s_rep2", "s_rep3"])
    r["icc_named_oct16_3draws"] = icc2k(["s_rep1", "s_rep2", "s_rep3"])
    out["robustness"][label] = r
    print(f"\n[{label}]")
    for k, v in r.items():
        print(f"  {k}: {v}")

json.dump(out, open(f"{DATA}/v_exclusion.json", "w"), indent=1)
print("\nsaved data/v_exclusion.json")
