#!/usr/bin/env python3
"""Mechanism audit (preparatory): can within-session TIME drift explain the
+3.61 batch-composition effect?

Each batch is an independent API call (no conversation continuity), so the
only non-composition channel is endpoint state evolving over the session's
wall-clock time. The 542-composition control pass ran AFTER the 8 interleaved
rounds in session 3, so if scores trend with time-of-session, part of the
+3.61 could be time, not composition.

Tests on existing session-3 data (no new API calls):
  (1) named level by round (r1..r4)          -> across-session-3 time trend
  (2) named level by batch index (0..13)     -> within-round position trend
  (3) anon level by round and batch index    -> same for the other condition
  (4) time-stamped check: score vs call time within session 3 (from log order)
If all flat -> time-of-session cannot explain +3.61; the remaining channel is
within-batch composition (batch-mates and/or within-prompt position).
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = "/home/z/my-project/data"

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]

def load(path):
    d = json.load(open(path))
    return [d[u]["sentiment"] for u in url_order if u in d]

s3n = {r: load(f"{DATA}/llm_scores_s3_named_r{r}.json") for r in (1, 2, 3, 4)}
s3a = {r: load(f"{DATA}/llm_scores_s3_anon_r{r}.json") for r in (1, 2, 3, 4)}

rows = []
BATCH = 25
for r in (1, 2, 3, 4):
    for i, v in enumerate(s3n[r]):
        rows.append({"round": r, "batch": i // BATCH, "pos": i, "cond": "named", "score": v})
    for i, v in enumerate(s3a[r]):
        rows.append({"round": r, "batch": i // BATCH, "pos": i, "cond": "anon", "score": v})
df = pd.DataFrame(rows)

R = {}
# (1) named level by round
by_round = df[df.cond == "named"].groupby("round")["score"].agg(["mean", "sem"])
R["named_by_round"] = {int(k): [float(v["mean"]), float(v["sem"])] for k, v in by_round.iterrows()}
print("(1) named level by round:")
print(by_round.round(2).to_string())
m_r = smf.ols("score ~ round", data=df[df.cond == "named"]).fit(cov_type="HC1")
R["named_round_trend"] = {"coef": float(m_r.params["round"]), "t": float(m_r.tvalues["round"])}
print(f"    trend per round: {m_r.params['round']:+.3f} (t={m_r.tvalues['round']:.2f})")

# (2) named level by batch index (position in the 14-batch stream, within round)
by_batch = df[df.cond == "named"].groupby("batch")["score"].mean()
m_b = smf.ols("score ~ batch", data=df[df.cond == "named"]).fit(cov_type="cluster",
        cov_kwds={"groups": df[df.cond == "named"]["round"]})
R["named_batch_trend"] = {"coef": float(m_b.params["batch"]), "t": float(m_b.tvalues["batch"])}
R["named_by_batch"] = {int(k): float(v) for k, v in by_batch.items()}
print(f"(2) named level by batch index 0->13: trend {m_b.params['batch']:+.3f} per batch (t={m_b.tvalues['batch']:.2f})")
print("    batch means:", " ".join(f"{v:.1f}" for v in by_batch.values))

# (3) anon same checks
m_ra = smf.ols("score ~ round", data=df[df.cond == "anon"]).fit(cov_type="HC1")
m_ba = smf.ols("score ~ batch", data=df[df.cond == "anon"]).fit(cov_type="cluster",
        cov_kwds={"groups": df[df.cond == "anon"]["round"]})
R["anon_round_trend"] = {"coef": float(m_ra.params["round"]), "t": float(m_ra.tvalues["round"])}
R["anon_batch_trend"] = {"coef": float(m_ba.params["batch"]), "t": float(m_ba.tvalues["batch"])}
print(f"(3) anon: round trend {m_ra.params['round']:+.3f} (t={m_ra.tvalues['round']:.2f}); "
      f"batch trend {m_ba.params['batch']:+.3f} (t={m_ba.tvalues['batch']:.2f})")

# (4) combined: does round/batch explain ANY variance? R2
m_full = smf.ols("score ~ C(round) + C(batch) + C(cond)", data=df).fit()
R["r2_round_batch_cond"] = float(m_full.rsquared)
print(f"(4) R2 of round+batch+condition on scores: {m_full.rsquared:.4f}")

# bound: if the strongest plausible time trend (per-batch coef x 22 batches for v1comp) were real
b_coef = R["named_batch_trend"]["coef"]
r_coef = R["named_round_trend"]["coef"]
# v1comp ran ~after 8 rounds + interleaved: time equivalent ~ 8*14=112 batches later than round-1 batch-0
bound_batch = abs(b_coef) * 112
bound_round = abs(r_coef) * 8
R["time_drift_bound_if_linear"] = {
    "per_batch_coef": float(b_coef), "per_round_coef": float(r_coef),
    "max_abs_displacement_batches": float(bound_batch),
    "max_abs_displacement_rounds": float(bound_round),
}
print(f"    linear bound: |batch coef| x 112 = {bound_batch:.2f} pts; |round coef| x 8 = {bound_round:.2f} pts")
print(f"    (composition effect to explain: +3.61)")

json.dump(R, open(f"{DATA}/results_mechanism_audit.json", "w"), indent=1)
print("\nsaved data/results_mechanism_audit.json")
