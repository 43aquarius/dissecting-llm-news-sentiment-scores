#!/usr/bin/env python3
"""Final clean anchoring identification.

score_ip = mu_i + delta_p + theta * mates_fixed_ip + eps_ip

mates_fixed_ip = mean of batch-mates' GRAND means alpha_j (estimated across
all passes, noise-averaged). Deterministic given the batch assignment ->
theta is clean of same-response noise endogeneity. Cross-batching variation
(shuffled / 542-order vs original) provides the identifying variation.

Also decomposes response-level mood: residuals of same call correlate?
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = "/home/z/my-project/data"
BATCH = 25

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]

passes = []
for r in (1, 2, 3, 4):
    passes.append((f"s3_r{r}", json.load(open(f"{DATA}/llm_scores_s3_named_r{r}.json")), url_order))
passes.append(("s3_v1c", json.load(open(f"{DATA}/llm_scores_s3_v1comp.json")),
               [a["url"] for a in json.load(open(f"{DATA}/news_all.json"))]))
passes.append(("s4_orig", json.load(open(f"{DATA}/llm_scores_s4_orig.json")), url_order))
passes.append(("s4_shuf", json.load(open(f"{DATA}/llm_scores_s4_shuf.json")),
               json.load(open(f"{DATA}/s4_shuffle_order.json"))))
passes.append(("s4_v1c", json.load(open(f"{DATA}/llm_scores_s4_v1comp.json")),
               [a["url"] for a in json.load(open(f"{DATA}/news_all.json"))]))

rows = []
for pname, smap, seq in passes:
    pos_in_seq = {u: k for k, u in enumerate(seq)}
    for u in url_order:
        k = pos_in_seq.get(u)
        if k is None or u not in smap:
            continue
        rows.append({"url": u, "passid": pname, "score": smap[u]["sentiment"], "batch": k // BATCH})
df = pd.DataFrame(rows)

# grand means alpha_j (all passes; each headline has 8 obs)
alpha = df.groupby("url")["score"].mean()
df["alpha"] = df["url"].map(alpha)
# batch-mates' fixed means (excluding own alpha)
df["bkey"] = df["passid"] + "_" + df["batch"].astype(str)
gsum = df.groupby("bkey")["alpha"].transform("sum")
gn = df.groupby("bkey")["alpha"].transform("count")
df["mates_fixed"] = (gsum - df["alpha"]) / (gn - 1)

m = smf.ols("score ~ C(url) + C(passid) + mates_fixed", data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["bkey"]})
R = {"theta_clean": float(m.params["mates_fixed"]),
     "t": float(m.tvalues["mates_fixed"]),
     "se": float(m.bse["mates_fixed"]),
     "n_obs": int(m.nobs)}
print(f"clean anchoring theta = {m.params['mates_fixed']:+.4f} (t={m.tvalues['mates_fixed']:.2f})")

# placebo on original-order passes only: mates_fixed constant per headline
# there -> theta should be unidentified/zero; check
orig_passes = [p for p in df["passid"].unique() if p.startswith("s3_r") or p == "s4_orig"]
mo = smf.ols("score ~ C(url) + C(passid) + mates_fixed",
             data=df[df["passid"].isin(orig_passes)]).fit(
    cov_type="cluster", cov_kwds={"groups": df[df["passid"].isin(orig_passes)]["bkey"]})
R["placebo_orig_theta"] = float(mo.params["mates_fixed"])
R["placebo_orig_t"] = float(mo.tvalues["mates_fixed"])
print(f"placebo (no re-batching): theta = {mo.params['mates_fixed']:+.4f} (t={mo.tvalues['mates_fixed']:.2f})")

# response-level mood: within-call residual correlation
df["resid"] = m.resid
vc = df.groupby("bkey")["resid"].var()
within = vc.mean()
total = df["resid"].var()
R["response_mood_icc"] = float(within / total)
print(f"response-level mood share of residual variance: {within/total:.3f}")

# how much of the shuffle level shift does theta explain?
# shuffled batches: mates_fixed ~ global mean alpha; original: company-blocks
glob = alpha.mean()
for p in ("s4_orig", "s4_shuf", "s4_v1c"):
    sub = df[df["passid"] == p]
    R[f"mates_fixed_mean_{p}"] = float(sub["mates_fixed"].mean())
print("mates_fixed means:", {p: round(R[f"mates_fixed_mean_{p}"], 2) for p in ("s4_orig", "s4_shuf", "s4_v1c")})
th = R["theta_clean"]
R["predicted_level_from_anchoring"] = {
    "shuf_minus_orig": th * (R["mates_fixed_mean_s4_shuf"] - R["mates_fixed_mean_s4_orig"]),
    "v1c_minus_orig": th * (R["mates_fixed_mean_s4_v1c"] - R["mates_fixed_mean_s4_orig"]),
}
print("predicted shifts:", {k: round(v, 2) for k, v in R["predicted_level_from_anchoring"].items()})
print("observed: shuf-orig = +4.72; v1c-orig = +3.50")

json.dump(R, open(f"{DATA}/results_anchoring3.json", "w"), indent=1)
print("\nsaved data/results_anchoring3.json")
