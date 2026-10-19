#!/usr/bin/env python3
"""Session 4 mechanism analysis: replicate the composition effect with
REVERSED run order (542-comp FIRST, 341 LATE) and measure re-batch sensitivity.

Reads: llm_scores_s4_{v1comp,orig,shuf}.json, s3 scores, s4_shuffle_order.json
Writes: data/results_s4.json
Interpretation grid:
  comp_s4 ≈ +3.6  -> composition effect replicates with time working AGAINST it
                     => time-of-session ruled out; batch composition confirmed
  rebatch ≈ 0     -> re-batching within the corpus is inert => the effect is the
                     out-of-window mixing (content anchoring), not any re-batch
  rebatch ≠ 0     -> general batch sensitivity
"""
import json
import numpy as np
from scipy import stats

DATA = "/home/z/my-project/data"

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]

def load(path):
    d = json.load(open(path))
    return np.array([d[u]["sentiment"] for u in url_order])

s4_v1c = load(f"{DATA}/llm_scores_s4_v1comp.json")   # 542-composition (ran FIRST)
s4_org = load(f"{DATA}/llm_scores_s4_orig.json")     # 341 original order (ran SECOND)
s4_shf = load(f"{DATA}/llm_scores_s4_shuf.json")     # 341 shuffled (ran THIRD)
s3_n4 = np.array([np.mean([json.load(open(f"{DATA}/llm_scores_s3_named_r{r}.json"))[u]["sentiment"]
                           for r in (1, 2, 3, 4)]) for u in url_order])
s3_v1c = load(f"{DATA}/llm_scores_s3_v1comp.json")
s2_repm = np.array([np.mean([json.load(open(f"{DATA}/llm_scores_{k}.json"))[u]["sentiment"]
                             for k in ("rep1", "rep2", "rep3")]) for u in url_order])

n = len(url_order)
R = {"design": "session 4 (2026-10-18, later sitting): v1comp FIRST, orig341 SECOND, "
               "shuf341 THIRD; protocol identical; run order inverted vs session 3",
     "n": n}

# ---- (1) composition effect, reversed run order ----
dc = s4_v1c - s4_org
tt = stats.ttest_rel(s4_v1c, s4_org)
R["composition_s4"] = {
    "v1comp_minus_341": float(dc.mean()), "t": float(tt.statistic), "p": float(tt.pvalue),
    "mean_v1comp": float(s4_v1c.mean()), "mean_341": float(s4_org.mean()),
    "session3_estimate": 3.614,
}
print(f"(1) composition, s4 (542 ran FIRST): {dc.mean():+.3f} (t={tt.statistic:.2f}, p={tt.pvalue:.2e})")
print(f"    levels: 542-comp {s4_v1c.mean():+.2f} vs 341 {s4_org.mean():+.2f}")

# ---- (2) re-batch sensitivity within the 341 ----
db = s4_shf - s4_org
ttb = stats.ttest_rel(s4_shf, s4_org)
R["rebatch_s4"] = {
    "shuffled_minus_original": float(db.mean()), "t": float(ttb.statistic), "p": float(ttb.pvalue),
    "mean_shuffled": float(s4_shf.mean()),
}
print(f"(2) re-batch (shuffled - original, same session): {db.mean():+.3f} (t={ttb.statistic:.2f}, p={ttb.pvalue:.3f})")

# noise benchmark: single-call vs single-call repeat noise
noise = float(np.mean([np.abs(json.load(open(f"{DATA}/llm_scores_s3_named_r1.json"))[u]["sentiment"] -
                                 json.load(open(f"{DATA}/llm_scores_s3_named_r2.json"))[u]["sentiment"])
                       for u in url_order]))
R["rebatch_s4"]["noise_benchmark_mad"] = noise
print(f"    noise benchmark (|rep1-rep2| MAD): {noise:.2f}")

# ---- (3) cross-session drift at fixed composition (341) ----
dcs = s4_org - s3_n4
ttcs = stats.ttest_rel(s4_org, s3_n4)
R["cross_session_341"] = {
    "s4_minus_s3": float(dcs.mean()), "t": float(ttcs.statistic), "p": float(ttcs.pvalue),
    "mean_s3_named4": float(s3_n4.mean())}
print(f"(3) cross-session 341-comp: s4 - s3 = {dcs.mean():+.3f} (t={ttcs.statistic:.2f})")
dcs2 = s4_v1c - s3_v1c
ttcs2 = stats.ttest_rel(s4_v1c, s3_v1c)
R["cross_session_542"] = {"s4_minus_s3": float(dcs2.mean()), "t": float(ttcs2.statistic), "p": float(ttcs2.pvalue)}
print(f"    cross-session 542-comp: s4 - s3 = {dcs2.mean():+.3f} (t={ttcs2.statistic:.2f})")

# ---- (4) consistency grid ----
R["grid"] = {
    "s1_542": 16.877, "s2_341": 11.085,
    "s3_341": float(s3_n4.mean()), "s3_542": float(s3_v1c.mean()),
    "s4_542": float(s4_v1c.mean()), "s4_341": float(s4_org.mean()),
    "s4_shuf": float(s4_shf.mean()),
}
print("(4) level grid: s1-542 16.88 | s2-341 11.09 | s3-341 {:+.2f} s3-542 {:+.2f} | "
      "s4-542 {:+.2f} s4-341 {:+.2f} s4-shuf {:+.2f}".format(
          s3_n4.mean(), s3_v1c.mean(), s4_v1c.mean(), s4_org.mean(), s4_shf.mean()))

# exact matches
R["exact"] = {
    "s4orig_vs_s4shuf": float((s4_org == s4_shf).mean()),
    "s4orig_vs_s4v1c": float((s4_org == s4_v1c).mean()),
}

json.dump(R, open(f"{DATA}/results_s4.json", "w"), indent=1)
print("\nsaved data/results_s4.json")
