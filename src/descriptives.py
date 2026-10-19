#!/usr/bin/env python3
"""P0-3: Rebuild Table 1 (descriptive statistics) from archived artifacts.

The previous table mixed samples: several Panel A columns were transcribed from
the v1 all-542 descriptives (desc_stats.json) while being labeled N=341, and
Panel B anonymized/volatility cells were not reproducible at all. This script
recomputes EVERY cell from the raw archived files under the exact definitions
of analysis_v2.py, writes the machine-readable JSON, and generates the LaTeX
table consumed by data.tex via \\input{sections/gen/table_desc}.

Panel A: article level, 341 in-window headlines (2026-07-01..2026-10-14).
Panel B: firm-day level, 240 relevance-qualified (rel>=30) trading-day firm-days.
"""
import json
import re
import numpy as np
import pandas as pd

DATA = "/home/z/my-project/data"
OUT_JSON = f"{DATA}/descriptives_v2.json"
OUT_TEX = "/home/z/my-project/paper/sections/gen/table_desc.tex"

PRICE_PAT = re.compile(
    r"\b(rose|rises?|risen|jump(?:s|ed|ing)?|surge[sd]?|surging|soar(?:s|ed|ing)?|"
    r"climb(?:s|ed|ing)?|rall(?:y|ies|ied|ing)|gain(?:s|ed|ing)?|fell|falls?|fallen|"
    r"drop(?:s|ped|ping)?|dropped|plunge[sd]?|plunging|sink[s]?|sank|sinking|slide[sd]?|"
    r"slump(?:s|ed|ing)?|tumbl(?:e|es|ed|ing)|crash(?:es|ed|ing)?|declin(?:e|es|ed|ing)|"
    r"rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)|spike[sd]?|spiking|dip(?:s|ped)?|"
    r"up\s?\d|down\s?\d|\d+%\s?(?:up|down)|hit\s+(?:a\s+)?(?:record|new|52)|"
    r"after\s+(?:earnings|results|guidance|beating|missing))\b", re.I)

# ---------------- article-level frame (identical to analysis_v2.build) ----------------
arts = json.load(open(f"{DATA}/news_scored.json"))
orig = json.load(open(f"{DATA}/llm_scores.json"))
anon = json.load(open(f"{DATA}/llm_scores_anon.json"))
reps = {k: json.load(open(f"{DATA}/llm_scores_{k}.json")) for k in ("rep1", "rep2", "rep3")}

rows = []
for a in arts:
    if not (a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"):
        continue
    u = a["url"]
    rows.append({
        "ticker": a["ticker"], "date": a["date_iso"], "url": u, "title": a["title"],
        "s_orig": orig.get(u, {}).get("sentiment"),
        "s_anon": anon.get(u, {}).get("sentiment"),
        "s_rep1": reps["rep1"].get(u, {}).get("sentiment"),
        "s_rep2": reps["rep2"].get(u, {}).get("sentiment"),
        "s_rep3": reps["rep3"].get(u, {}).get("sentiment"),
        "lm_tone": a.get("lm_tone"),
        "relevance": orig.get(u, {}).get("relevance"),
        "priced": bool(PRICE_PAT.search(a["title"])),
    })
adf = pd.DataFrame(rows)
assert len(adf) == 341, f"expected 341 in-window articles, got {len(adf)}"

def stat_block(s, scale=1.0):
    s = s.dropna() * scale
    return {"n": int(len(s)), "mean": float(s.mean()), "sd": float(s.std()),
            "min": float(s.min()), "max": float(s.max()),
            "nonzero": float((s != 0).mean())}

A = {
    "named": stat_block(adf["s_orig"]),
    "anon": stat_block(adf["s_anon"]),
    "rep1": stat_block(adf["s_rep1"]),
    "rep2": stat_block(adf["s_rep2"]),
    "rep3": stat_block(adf["s_rep3"]),
    "lm_tone": stat_block(adf["lm_tone"]),
    "relevance": stat_block(adf["relevance"]),
    "priced_flag": {"mean": float(adf["priced"].mean()), "n": 341},
}

# ---------------- firm-day frame (identical to analysis_v2.build) ----------------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)

hi = adf[adf["relevance"] >= 30]
agg = hi.groupby(["ticker", "date"]).agg(
    sent=("s_orig", "mean"), sent_anon=("s_anon", "mean"),
    rep1=("s_rep1", "mean"), rep2=("s_rep2", "mean"), rep3=("s_rep3", "mean"),
    lm_tone=("lm_tone", "mean"), n_news=("url", "count"),
    priced_any=("priced", "max"), relevance=("relevance", "mean")).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
p = panel.merge(agg, on=["ticker", "date"], how="left")
if "lm_tone_y" in p.columns:
    p["lm_tone"] = p["lm_tone_y"]
if "n_news_y" in p.columns:
    p["n_news"] = p["n_news_y"]
for col in ("sent", "sent_anon", "rep1", "rep2", "rep3", "lm_tone"):
    if col in p.columns:
        p[col] = p[col] / 100.0
news = p[p["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"]).sort_values(["ticker", "date"])
assert len(news) == 240, f"expected 240 firm-days, got {len(news)}"

B = {
    "named": stat_block(news["sent"]),
    "anon": stat_block(news["sent_anon"]),
    "lm_tone_x100": stat_block(news["lm_tone"], scale=100.0),
    "n_news": stat_block(news["n_news"]),
    "ret_fwd1_bps": stat_block(news["ret_fwd1"], scale=1e4),
    "vol_21": stat_block(news["vol_21"]),
}

out = {"script": "descriptives.py", "panel_a_article_level": A, "panel_b_firmday_level": B,
       "exact_all4": float((adf[["s_orig", "s_rep1", "s_rep2", "s_rep3"]].dropna()
                            .nunique(axis=1) == 1).mean()),
       "pairwise_exact": {f"{i}_{j}": float(pd.Series(
                              [adf.loc[k, i] == adf.loc[k, j]
                               for k in adf[i].dropna().index.intersection(adf[j].dropna().index)]
                          ).mean())
                          for i, j in (("s_orig", "s_rep1"), ("s_orig", "s_rep2"),
                                       ("s_orig", "s_rep3"), ("s_rep1", "s_rep2"),
                                       ("s_rep1", "s_rep3"), ("s_rep2", "s_rep3"))}}
json.dump(out, open(OUT_JSON, "w"), indent=1)

# ---------------- LaTeX table ----------------
def f2(x):  # 2 decimals, minus sign
    return f"{x:.2f}".replace("-", "$-$")
def f1(x):
    return f"{x:.1f}".replace("-", "$-$")

rep_means = [A[r]["mean"] for r in ("rep1", "rep2", "rep3")]
rep_sds = [A[r]["sd"] for r in ("rep1", "rep2", "rep3")]
n_fwd = B["ret_fwd1_bps"]["n"]

tex = f"""% AUTO-GENERATED by scripts/descriptives.py -- DO NOT EDIT BY HAND
% Panel A: 341 in-window articles; Panel B: 240 relevance-qualified firm-days
\\begin{{table}}[htbp]
\\centering
\\small
\\caption{{Descriptive statistics across scoring conditions}}
\\label{{tab:desc}}
\\begin{{adjustbox}}{{max width=\\textwidth}}
\\begin{{tabular}}{{lcccccc}}
\\toprule
 & Mean & Std.\\ dev. & Min & Max & $N$ & Nonzero \\\\
\\midrule
\\multicolumn{{7}}{{l}}{{\\emph{{Panel A: Article level (341 in-window headlines)}}}} \\\\
LLM sentiment, named ($-100$ to $+100$) & {f2(A['named']['mean'])} & {f2(A['named']['sd'])} & {A['named']['min']:.0f} & {A['named']['max']:.0f} & 341 & {A['named']['nonzero']*100:.1f}\\% \\\\
LLM sentiment, anonymized & {f2(A['anon']['mean'])} & {f2(A['anon']['sd'])} & {A['anon']['min']:.0f} & {A['anon']['max']:.0f} & 341 & {A['anon']['nonzero']*100:.1f}\\% \\\\
LLM sentiment, repeat draws 1--3 (ranges) & {f2(min(rep_means))}--{f2(max(rep_means))} & {f2(min(rep_sds))}--{f2(max(rep_sds))} &~--- &~--- & 341 &~--- \\\\
LM dictionary tone (per 100 words) & {f2(A['lm_tone']['mean'])} & {f2(A['lm_tone']['sd'])} & {f1(A['lm_tone']['min'])} & {f1(A['lm_tone']['max'])} & 341 & {A['lm_tone']['nonzero']*100:.1f}\\% \\\\
Price-language headline flag & {A['priced_flag']['mean']:.3f} &~--- & 0 & 1 & 341 &~--- \\\\
Relevance (0--100) & {f1(A['relevance']['mean'])} & {f1(A['relevance']['sd'])} & 0 & 100 & 341 &~--- \\\\
\\midrule
\\multicolumn{{7}}{{l}}{{\\emph{{Panel B: Firm-day level (240 relevance-qualified firm-days)}}}} \\\\
Named sentiment ($[-1,1]$ scale) & {f2(B['named']['mean'])} & {f2(B['named']['sd'])} & {f2(B['named']['min'])} & {f2(B['named']['max'])} & 240 & {B['named']['nonzero']*100:.1f}\\% \\\\
Anonymized sentiment & {f2(B['anon']['mean'])} & {f2(B['anon']['sd'])} & {f2(B['anon']['min'])} & {f2(B['anon']['max'])} & 240 & {B['anon']['nonzero']*100:.1f}\\% \\\\
Dictionary tone ($\\times 10^{{-2}}$) & {f2(B['lm_tone_x100']['mean'])} & {f2(B['lm_tone_x100']['sd'])} & {f1(B['lm_tone_x100']['min'])} & {f1(B['lm_tone_x100']['max'])} & 240 & {B['lm_tone_x100']['nonzero']*100:.1f}\\% \\\\
Headlines per firm-day & {f2(B['n_news']['mean'])} & {f2(B['n_news']['sd'])} & {B['n_news']['min']:.0f} & {B['n_news']['max']:.0f} & 240 &~--- \\\\
Next-day return (\\bps) & {f1(B['ret_fwd1_bps']['mean'])} & {f1(B['ret_fwd1_bps']['sd'])} & {B['ret_fwd1_bps']['min']:.0f} & {B['ret_fwd1_bps']['max']:.0f} & {n_fwd} &~--- \\\\
Lagged 21-day volatility (annualized) & {B['vol_21']['mean']:.3f} & {B['vol_21']['sd']:.3f} & {B['vol_21']['min']:.2f} & {B['vol_21']['max']:.2f} & 240 &~--- \\\\
\\bottomrule
\\end{{tabular}}
\\end{{adjustbox}}
\\begin{{tablenotes}}[flushleft]\\footnotesize
\\item Panel A is computed over the 341 in-window headlines; Panel B over the 240 relevance-qualified trading-day firm-days of the analysis sample (next-day returns are non-missing for {n_fwd} of 240 firm-days). Repeat draws report ranges across the three independent calls. Nonzero is the share of observations with score $\\neq 0$. Every cell is generated by \\texttt{{descriptives.py}} from the archived scores and panel; the previous hand-transcribed version mixed an all-542 computation into the $N=341$ rows and has been withdrawn.
\\end{{tablenotes}}
\\end{{table}}
"""
import os
os.makedirs(os.path.dirname(OUT_TEX), exist_ok=True)
open(OUT_TEX, "w").write(tex)

# ---------------- verification printout ----------------
print("=== Panel A (341) ===")
for k in ("named", "anon", "rep1", "rep2", "rep3", "lm_tone", "relevance"):
    v = A[k]
    print(f"{k:10s} mean={v['mean']:8.3f} sd={v['sd']:7.3f} min={v['min']:7.1f} "
          f"max={v['max']:7.1f} nz={v['nonzero']*100:5.1f}%")
print(f"priced flag: {A['priced_flag']['mean']:.3f}")
print("=== Panel B (240) ===")
for k, v in B.items():
    print(f"{k:14s} mean={v['mean']:9.4f} sd={v['sd']:8.4f} min={v['min']:9.1f} "
          f"max={v['max']:9.1f} n={v['n']}")
print(f"exact all-4 identical: {out['exact_all4']:.3f}")
print(f"pairwise exact: { {k: round(v,3) for k,v in out['pairwise_exact'].items()} }")
print(f"wrote {OUT_JSON}")
print(f"wrote {OUT_TEX}")
