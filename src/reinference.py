#!/usr/bin/env python3
"""Re-inference for all session-3/4 level contrasts under CALL-LEVEL CLUSTERING.

Discovery chain: each API call scores 25 headlines in one response; the 25
scores share a response-level mood (variance share ~10%). Headline-level
paired t-tests on pass-level contrasts therefore overstate precision; the
correct cluster is the batch-call (or, for averaged rounds, the round).

Also: asymmetric anchoring test (can non-linear anchoring generate the level
shifts that linear anchoring provably cannot?).
Writes: data/results_reinfer.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
BATCH = 25

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]
n = len(url_order)

def arr(path):
    d = json.load(open(path))
    return np.array([d[u]["sentiment"] for u in url_order])

s3n = {r: arr(f"{DATA}/llm_scores_s3_named_r{r}.json") for r in (1, 2, 3, 4)}
s3a = {r: arr(f"{DATA}/llm_scores_s3_anon_r{r}.json") for r in (1, 2, 3, 4)}
s3_v1c = arr(f"{DATA}/llm_scores_s3_v1comp.json")
s4_v1c = arr(f"{DATA}/llm_scores_s4_v1comp.json")
s4_org = arr(f"{DATA}/llm_scores_s4_orig.json")
s4_shf = arr(f"{DATA}/llm_scores_s4_shuf.json")

named4 = np.mean([s3n[r] for r in (1, 2, 3, 4)], axis=0)
anon4 = np.mean([s3a[r] for r in (1, 2, 3, 4)], axis=0)

R = {}

# ---------------- (1) variance decomposition: mood vs idiosyncratic ----------------
rows = []
for r in (1, 2, 3, 4):
    for i in range(n):
        rows.append({"url": url_order[i], "passid": f"n{r}", "score": s3n[r][i], "batch": i // BATCH})
    for i in range(n):
        rows.append({"url": url_order[i], "passid": f"a{r}", "score": s3a[r][i], "batch": i // BATCH})
df = pd.DataFrame(rows)
df["bkey"] = df["passid"] + "_b" + df["batch"].astype(str)
m0 = smf.ols("score ~ C(url) + C(passid)", data=df).fit()
df["resid"] = m0.resid
vb = df.groupby("bkey")["resid"].mean().var()     # between-call variance of call means
vw = df.groupby("bkey")["resid"].var().mean()     # within-call variance
nb = df["bkey"].nunique()
# call-mean variance = mood + e/25 ; solve
e_var = vw
mood_var = max(vb - e_var / 25.0, 0.0)
R["variance_decomposition"] = {
    "resid_sd": float(df["resid"].std()), "mood_sd": float(np.sqrt(mood_var)),
    "idio_sd": float(np.sqrt(e_var)), "mood_share": float(mood_var / (mood_var + e_var)),
    "n_calls": int(nb)}
print(f"(1) decomposition: resid SD {df['resid'].std():.2f} = call-mood SD "
      f"{np.sqrt(mood_var):.2f} + idiosyncratic SD {np.sqrt(e_var):.2f} "
      f"(mood share {mood_var/(mood_var+e_var):.2f})")

# ---------------- (2) identity effect with call clustering ----------------
# diff_i = anon4_i - named4_i; cluster by batch (batch assignment fixed across rounds)
d_id = anon4 - named4
cl = pd.DataFrame({"diff": d_id, "batch": np.arange(n) // BATCH})
# cluster-robust mean test: aggregate to batch means, t-test on 14 batch means
bm = cl.groupby("batch")["diff"].mean()
t_b = stats.ttest_1samp(bm, 0)
R["identity_call_clustered"] = {
    "estimate": float(d_id.mean()),
    "naive_se": float(d_id.std(ddof=1) / np.sqrt(n)),
    "batch_mean_t": float(t_b.statistic), "batch_mean_p": float(t_b.pvalue),
    "n_clusters": int(len(bm))}
print(f"(2) identity anon-named: {d_id.mean():+.3f}; naive t={d_id.mean()/(d_id.std(ddof=1)/np.sqrt(n)):.2f}; "
      f"14-batch-mean t={t_b.statistic:.2f} (p={t_b.pvalue:.4f})")
# round-level meta-test (4 rounds, each round = 14 anon + 14 named calls)
rr = [(s3a[r] - s3n[r]).mean() for r in (1, 2, 3, 4)]
t_r = stats.ttest_1samp(rr, 0)
R["identity_round_level"] = {"round_estimates": [float(x) for x in rr],
                             "mean": float(np.mean(rr)), "t": float(t_r.statistic),
                             "p": float(t_r.pvalue)}
print(f"    round-level (n=4): mean {np.mean(rr):+.3f}, t={t_r.statistic:.2f} (p={t_r.pvalue:.4f})")

# ---------------- (3) composition effects with call clustering ----------------
def batch_mean_test(x, label):
    bm2 = pd.Series(x).groupby(np.arange(n) // BATCH).mean()
    return bm2

# s3: v1c (22 calls over 542) vs named4 (56 calls); cluster s3 v1c by ITS batch assignment
allurls = [a["url"] for a in json.load(open(f"{DATA}/news_all.json"))]
pos542 = {u: k for k, u in enumerate(allurls)}
s3v_batches = np.array([pos542[u] // BATCH for u in url_order])
bm_v = pd.Series(s3_v1c - named4).groupby(s3v_batches).mean()   # 542-order batches (~22)
t_v = stats.ttest_1samp(bm_v, 0)
R["composition_s3_call_clustered"] = {"estimate": float((s3_v1c - named4).mean()),
                                      "t": float(t_v.statistic), "p": float(t_v.pvalue),
                                      "n_clusters": int(len(bm_v))}
print(f"(3a) s3 composition (v1c - named4): {(s3_v1c-named4).mean():+.3f}; "
      f"{len(bm_v)}-batch t={t_v.statistic:.2f} (p={t_v.pvalue:.4f})")

# s4: v1c vs orig, both with own batch assignments
bm_v4 = pd.Series(s4_v1c - s4_org).groupby(s3v_batches).mean()
t_v4 = stats.ttest_1samp(bm_v4, 0)
R["composition_s4_call_clustered"] = {"estimate": float((s4_v1c - s4_org).mean()),
                                      "t": float(t_v4.statistic), "p": float(t_v4.pvalue),
                                      "n_clusters": int(len(bm_v4))}
print(f"(3b) s4 composition (v1c - orig): {(s4_v1c-s4_org).mean():+.3f}; "
      f"{len(bm_v4)}-batch t={t_v4.statistic:.2f} (p={t_v4.pvalue:.4f})")

# pooled two-session estimate
pooled = (R["composition_s3_call_clustered"]["estimate"] + R["composition_s4_call_clustered"]["estimate"]) / 2
se_pooled = 0.5 * np.sqrt((R["composition_s3_call_clustered"]["estimate"] / R["composition_s3_call_clustered"]["t"])**2 +
                          (R["composition_s4_call_clustered"]["estimate"] / R["composition_s4_call_clustered"]["t"])**2)
R["composition_pooled"] = {"estimate": float(pooled), "se": float(se_pooled),
                           "z": float(pooled / se_pooled)}
print(f"    pooled: {pooled:+.3f} (z={pooled/se_pooled:.2f})")

# ---------------- (4) shuffle effect with call clustering ----------------
shuf_order = json.load(open(f"{DATA}/s4_shuffle_order.json"))
pos_shf = {u: k for k, u in enumerate(shuf_order)}
shf_batches = np.array([pos_shf[u] // BATCH for u in url_order])
bm_s = pd.Series(s4_shf - s4_org).groupby(shf_batches).mean()
t_s = stats.ttest_1samp(bm_s, 0)
R["shuffle_call_clustered"] = {"estimate": float((s4_shf - s4_org).mean()),
                               "t": float(t_s.statistic), "p": float(t_s.pvalue),
                               "n_clusters": int(len(bm_s))}
print(f"(4) shuffle (shuf - orig): {(s4_shf-s4_org).mean():+.3f}; "
      f"{len(bm_s)}-batch t={t_s.statistic:.2f} (p={t_s.pvalue:.4f})")

# ---------------- (5) cross-session drift, call-clustered ----------------
bm_c = pd.Series(s4_org - named4).groupby(np.arange(n) // BATCH).mean()
t_c = stats.ttest_1samp(bm_c, 0)
R["cross_session_call_clustered"] = {"estimate": float((s4_org - named4).mean()),
                                     "t": float(t_c.statistic), "p": float(t_c.pvalue)}
print(f"(5) cross-session 341-comp (s4 - s3): {(s4_org-named4).mean():+.3f}; t={t_c.statistic:.2f}")

# ---------------- (6) asymmetric anchoring ----------------
# use mates_fixed from anchoring_regression3 setup
passes = [(f"n{r}", s3n[r], url_order) for r in (1, 2, 3, 4)]
passes += [("s3_v1c", s3_v1c, allurls), ("s4_orig", s4_org, url_order),
           ("s4_shf", s4_shf, shuf_order), ("s4_v1c", s4_v1c, allurls)]
rows2 = []
for pname, x, seq in passes:
    pos = {u: k for k, u in enumerate(seq)}
    for i, u in enumerate(url_order):
        k = pos.get(u)
        if k is None:
            continue
        rows2.append({"url": u, "passid": pname, "score": float(x[i]), "batch": k // BATCH})
df2 = pd.DataFrame(rows2)
df2["bkey"] = df2["passid"] + "_b" + df2["batch"].astype(str)
alpha = df2.groupby("url")["score"].mean()
df2["alpha"] = df2["url"].map(alpha)
gsum = df2.groupby("bkey")["alpha"].transform("sum")
gn = df2.groupby("bkey")["alpha"].transform("count")
df2["mates_fixed"] = (gsum - df2["alpha"]) / (gn - 1)
df2["mates_pos"] = (df2["mates_fixed"] > 0).astype(int)
m_asym = smf.ols("score ~ C(url) + C(passid) + mates_fixed + mates_fixed:mates_pos",
                 data=df2).fit(cov_type="cluster", cov_kwds={"groups": df2["bkey"]})
R["asymmetric_anchoring"] = {
    "beta_base": float(m_asym.params["mates_fixed"]),
    "beta_extra_if_positive": float(m_asym.params["mates_fixed:mates_pos"]),
    "t_base": float(m_asym.tvalues["mates_fixed"]),
    "t_extra": float(m_asym.tvalues["mates_fixed:mates_pos"])}
print(f"(6) asymmetric anchoring: beta(neg mates) = {m_asym.params['mates_fixed']:+.3f} "
      f"(t={m_asym.tvalues['mates_fixed']:.2f}); extra for positive mates = "
      f"{m_asym.params['mates_fixed:mates_pos']:+.3f} (t={m_asym.tvalues['mates_fixed:mates_pos']:.2f})")

json.dump(R, open(f"{DATA}/results_reinfer.json", "w"), indent=1)
print("\nsaved data/results_reinfer.json")
