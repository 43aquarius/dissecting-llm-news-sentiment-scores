#!/usr/bin/env python3
"""Anchoring regression: does a headline's score depend on its BATCH-MATES?

Identification: the same 341 headlines were scored under several DIFFERENT
batch assignments (named condition):
  - s3 rounds r1..r4 and s4 'orig': original company-grouped 341 order
  - s3 'v1comp' and s4 'v1comp': 542-order (company-grouped + out-of-window)
  - s4 'shuf': seeded random shuffle (mixed-company batches)
Within-headline variation in batch-mates across these passes identifies the
anchoring coefficient beta in:  score_ip = alpha_i + beta * LOOmean_ip + eps
where LOOmean = leave-one-out mean of the other headlines' scores in i's batch
in pass p. beta > 0 = assimilation; beta < 0 = contrast.

Also: within-batch position effect (id 0..24 in the prompt).
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
url_idx = {u: i for i, u in enumerate(url_order)}

def load_map(path):
    return json.load(open(path))

passes = []
for r in (1, 2, 3, 4):
    passes.append((f"s3_r{r}", load_map(f"{DATA}/llm_scores_s3_named_r{r}.json"),
                   {u: k for k, u in enumerate(url_order)}))  # original order
passes.append(("s3_v1c", load_map(f"{DATA}/llm_scores_s3_v1comp.json"), None))  # 542 order
passes.append(("s4_orig", load_map(f"{DATA}/llm_scores_s4_orig.json"),
               {u: k for k, u in enumerate(url_order)}))
passes.append(("s4_shuf", load_map(f"{DATA}/llm_scores_s4_shuf.json"), None))  # shuffle order
passes.append(("s4_v1c", load_map(f"{DATA}/llm_scores_s4_v1comp.json"), None))  # 542 order

# build (headline, pass, score, batch-mates LOO mean, within-batch position)
rows = []
for pname, smap, order in passes:
    if order is None:
        if "shuf" in pname:
            seq = json.load(open(f"{DATA}/s4_shuffle_order.json"))
        elif "v1c" in pname:
            allarts = json.load(open(f"{DATA}/news_all.json"))
            seq = [a["url"] for a in allarts]
        # index within the pass's own sequence
        pos_in_seq = {u: k for k, u in enumerate(seq)}
        # batch assignment for the 341 urls
        for u in url_order:
            k = pos_in_seq.get(u)
            if k is None:
                continue
            b = k // BATCH
            rows.append((u, pname, smap[u]["sentiment"], b, k % BATCH, "seq"))
    else:
        for u in url_order:
            if u not in smap:
                continue
            k = order[u]
            b = k // BATCH
            rows.append((u, pname, smap[u]["sentiment"], b, k % BATCH, "seq"))

df = pd.DataFrame(rows, columns=["url", "pass", "score", "batch", "posinbatch", "grp"])
# LOO mean: batch-mates' scores within the same pass
df["bkey"] = df["pass"] + "_" + df["batch"].astype(str)
g = df.groupby("bkey")
df["batch_sum"] = g["score"].transform("sum")
df["batch_n"] = g["score"].transform("count")
df["loo_mean"] = (df["batch_sum"] - df["score"]) / (df["batch_n"] - 1)

print(f"observations: {len(df)}; passes: {df['pass'].nunique()}; "
      f"distinct (pass,batch): {df['bkey'].nunique()}")
print(f"LOO-mean sd across batches within pass: "
      f"{df.groupby('pass')['loo_mean'].std().round(2).to_dict()}")

# headline fixed effects + LOO mean
m1 = smf.ols("score ~ C(url) + loo_mean", data=df).fit(cov_type="cluster",
        cov_kwds={"groups": df["bkey"]})
R = {"anchoring_beta": float(m1.params["loo_mean"]),
     "anchoring_t": float(m1.tvalues["loo_mean"]),
     "anchoring_se": float(m1.bse["loo_mean"]),
     "n_obs": int(m1.nobs), "n_headlines": int(df["url"].nunique())}
print(f"\n(1) anchoring (headline FE): beta = {m1.params['loo_mean']:+.4f} "
      f"(t={m1.tvalues['loo_mean']:.2f}, cluster-by-batch SE)")

# with within-batch position
m2 = smf.ols("score ~ C(url) + loo_mean + posinbatch", data=df).fit(cov_type="cluster",
        cov_kwds={"groups": df["bkey"]})
R["position_beta"] = float(m2.params["posinbatch"])
R["position_t"] = float(m2.tvalues["posinbatch"])
R["anchoring_beta_with_pos"] = float(m2.params["loo_mean"])
R["anchoring_t_with_pos"] = float(m2.tvalues["loo_mean"])
print(f"(2) + position: anchoring beta = {m2.params['loo_mean']:+.4f} (t={m2.tvalues['loo_mean']:.2f}); "
      f"position beta = {m2.params['posinbatch']:+.4f} (t={m2.tvalues['posinbatch']:.2f})")

# interpretation: company-grouped vs mixed batches
# batch homogeneity: share of same-ticker batch-mates
tick = {a["url"]: a["ticker"] for a in inwin}
df["ticker"] = df["url"].map(tick)
def homo_frac(gr):
    t = gr["ticker"].values
    same = sum(1 for i in range(len(t)) for j in range(len(t)) if i != j and t[i] == t[j])
    tot = len(t) * (len(t) - 1)
    return same / tot if tot else 0
hf = df.groupby("bkey").apply(homo_frac, include_groups=False)
df["homo"] = df["bkey"].map(hf)
R["homogeneity_by_pass"] = {p: float(v) for p, v in df.groupby("pass")["homo"].first().items()}
print("\n(3) same-ticker batch-mate share by pass:",
      {p: round(float(v), 2) for p, v in df.groupby("pass")["homo"].first().items()})

# predicted composition shift from anchoring beta:
# original (homo) batches have LOO means far from the global mean; shuffled pulls to global mean
glob = df["score"].mean()
for p in ["s4_orig", "s4_shuf", "s4_v1c"]:
    sub = df[df["pass"] == p]
    dev = (sub["loo_mean"] - sub["score"]).mean()  # not the right quantity; use loo dev from glob
R["loo_dev_from_global_by_pass"] = {p: float((df[df['pass'] == p]['loo_mean'] - glob).mean())
                                    for p in ("s4_orig", "s4_shuf", "s4_v1c")}
print("(4) mean LOO deviation from global mean:",
      {p: round(float((df[df['pass'] == p]['loo_mean'] - glob).mean()), 2)
       for p in ("s4_orig", "s4_shuf", "s4_v1c")})

json.dump(R, open(f"{DATA}/results_anchoring.json", "w"), indent=1)
print("\nsaved data/results_anchoring.json")
