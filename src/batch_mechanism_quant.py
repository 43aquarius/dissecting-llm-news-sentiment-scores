#!/usr/bin/env python3
"""Quantify how much of the batch-composition level shift linear anchoring
can explain, with the FULL batch-mate pool (in-window + out-of-window).

The telescoping identity (anchoring_regression3.py) shows linear anchoring
predicts zero shift for any re-batching of the SAME corpus. But the
composition contrast (341-only batches vs. 542-article batches) changes the
mate pool itself: ~37% of an in-window headline's batch-mates in the 542
batches are OUT-OF-WINDOW headlines. If those 201 headlines' grand means
differ from the in-window ones, linear anchoring alone predicts a level
shift  theta * (mean mates_fixed_542 - mean mates_fixed_341).

This script computes:
 1. grand means (alphas) for all 542 headlines from the archived passes
 2. the out-of-window (n=201) vs in-window (n=341) alpha distributions
 3. exact per-headline batch-mate means under both compositions
 4. the linear-anchoring-predicted composition shift (theta from the clean
    regression, and re-estimated with full mates)
 5. comparison with observed +3.61 (s3), +3.50 (s4), pooled +3.56
 6. the same-corpus re-batch contrast (predicted 0, observed +4.72)

Output: data/results_batch_quant.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = "/home/z/my-project/data"
BATCH = 25

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
outw = [a for a in arts if not (a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14")]
url_in = [a["url"] for a in inwin]
url_out = [a["url"] for a in outw]
url_all = [a["url"] for a in arts]          # news_scored order = v1/341-composition order? NO:
# NOTE: the 341-only passes score url_in sequence; the 542 passes score news_all order.
news_all = json.load(open(f"{DATA}/news_all.json"))
url_all_542 = [a["url"] for a in news_all]   # 542-article original stream order
assert len(inwin) == 341 and len(outw) == 201, (len(inwin), len(outw))
assert set(url_all_542) == set(url_in) | set(url_out)

# ---- 1. grand means (alphas) --------------------------------------------
# in-window alphas: 8 passes (s3 r1-r4, s3_v1c, s4_orig, s4_shuf, s4_v1c)
s3 = {f"s3_r{r}": json.load(open(f"{DATA}/llm_scores_s3_named_r{r}.json")) for r in (1, 2, 3, 4)}
s3_v1c = json.load(open(f"{DATA}/llm_scores_s3_v1comp.json"))
s4_orig = json.load(open(f"{DATA}/llm_scores_s4_orig.json"))
s4_shuf = json.load(open(f"{DATA}/llm_scores_s4_shuf.json"))
s4_v1c = json.load(open(f"{DATA}/llm_scores_s4_v1comp.json"))
v1 = json.load(open(f"{DATA}/llm_scores.json"))

alpha_in = {}
for u in url_in:
    vals = [s3[k][u]["sentiment"] for k in s3] + [
        s3_v1c[u]["sentiment"], s4_orig[u]["sentiment"],
        s4_shuf[u]["sentiment"], s4_v1c[u]["sentiment"]]
    alpha_in[u] = float(np.mean(vals))
# out-of-window alphas: the three 542-protocol passes (v1, s3_v1c, s4_v1c)
alpha_out = {}
for u in url_out:
    vals = [v1[u]["sentiment"], s3_v1c[u]["sentiment"], s4_v1c[u]["sentiment"]]
    alpha_out[u] = float(np.mean(vals))

a_in = np.array([alpha_in[u] for u in url_in])
a_out = np.array([alpha_out[u] for u in url_out])
R = {
    "n_in": len(a_in), "n_out": len(a_out),
    "alpha_in_mean": float(a_in.mean()), "alpha_in_sd": float(a_in.std(ddof=1)),
    "alpha_out_mean": float(a_out.mean()), "alpha_out_sd": float(a_out.std(ddof=1)),
    "alpha_gap_out_minus_in": float(a_out.mean() - a_in.mean()),
    "alpha_out_share_pos": float((a_out > 0).mean()),
    "alpha_in_share_pos": float((a_in > 0).mean()),
}

# ---- 2. batch-mate means under each composition -------------------------
def mates_mean(seq, alphas, url):
    """mean alpha of the other members of url's batch (batch = 25-blocks of seq)"""
    pos = {u: k for k, u in enumerate(seq)}
    k = pos[url]
    b = k // BATCH
    members = seq[b * BATCH:(b + 1) * BATCH]
    vals = [alphas[m] for m in members if m != url and m in alphas]
    return float(np.mean(vals)), len(vals)

# 341-only composition: batches over url_in (in-window stream)
mates_341 = np.array([mates_mean(url_in, alpha_in, u)[0] for u in url_in])
# 542 composition: batches over url_all_542; mates include out-of-window
alpha_full = {**alpha_in, **alpha_out}
mates_542 = np.array([mates_mean(url_all_542, alpha_full, u)[0] for u in url_in])

# proper share of OUT-OF-WINDOW mates per in-window headline
url_out_set = set(url_out)
def count_out_mates(seq, url):
    pos = {u: k for k, u in enumerate(seq)}
    b = pos[url] // BATCH
    members = seq[b * BATCH:(b + 1) * BATCH]
    return sum(1 for m in members if m != url and m in url_out_set)
n_out_mates = np.array([count_out_mates(url_all_542, u) for u in url_in])
share_out_per_batch = n_out_mates / 24.0

R["mates_mean_341"] = float(mates_341.mean())
R["mates_mean_542"] = float(mates_542.mean())
R["d_mates_mean"] = float((mates_542 - mates_341).mean())
R["share_out_mates_mean"] = float(share_out_per_batch.mean())
R["share_out_mates_min"] = float(share_out_per_batch.min())
R["share_out_mates_max"] = float(share_out_per_batch.max())
R["alpha_out_quartiles"] = [float(x) for x in np.percentile(a_out, [10, 25, 50, 75, 90])]
R["alpha_in_quartiles"] = [float(x) for x in np.percentile(a_in, [10, 25, 50, 75, 90])]
# out-of-window composition: undated vs dated-outside
undated = [a for a in arts if not a.get("date_iso")]
dated_out = [a for a in outw if a.get("date_iso")]
R["n_undated"] = len(undated)
R["n_dated_outside"] = len(dated_out)
if undated:
    R["alpha_undated_mean"] = float(np.mean([alpha_out[a["url"]] for a in undated if a["url"] in alpha_out]))
if dated_out:
    R["alpha_dated_outside_mean"] = float(np.mean([alpha_out[a["url"]] for a in dated_out if a["url"] in alpha_out]))

# ---- 3. theta: archived clean estimate + full-mate re-estimate ----------
theta_archived = 0.35868815461102  # anchoring_regression3.py (in-window mates only)

# re-estimate with the FULL mate pool for the v1c passes
rows = []
passes = []
for r in (1, 2, 3, 4):
    passes.append((f"s3_r{r}", s3[k := f"s3_r{r}"], url_in, alpha_in))
passes = [(f"s3_r{r}", json.load(open(f"{DATA}/llm_scores_s3_named_r{r}.json")), url_in, alpha_in)
          for r in (1, 2, 3, 4)]
passes.append(("s3_v1c", s3_v1c, url_all_542, alpha_full))
passes.append(("s4_orig", s4_orig, url_in, alpha_in))
passes.append(("s4_shuf", s4_shuf, json.load(open(f"{DATA}/s4_shuffle_order.json")), alpha_in))
passes.append(("s4_v1c", s4_v1c, url_all_542, alpha_full))
for pname, smap, seq, alphas in passes:
    pos = {u: k for k, u in enumerate(seq)}
    for u in url_in:
        k = pos.get(u)
        if k is None or u not in smap:
            continue
        mm, _ = mates_mean(seq, alphas, u)
        rows.append({"url": u, "passid": pname, "score": smap[u]["sentiment"],
                     "batch": k // BATCH, "mates_full": mm})
df = pd.DataFrame(rows)
m = smf.ols("score ~ C(url) + C(passid) + mates_full", data=df).fit(
    cov_type="cluster", cov_kwds={"groups": df["passid"] + "_" + df["batch"].astype(str)})
theta_full = float(m.params["mates_full"])
R["theta_archived_inwin_mates"] = theta_archived
R["theta_full_mates"] = theta_full
R["theta_full_t"] = float(m.tvalues["mates_full"])

# ---- 4. predicted composition shift -------------------------------------
R["pred_composition_theta_archived"] = float(theta_archived * R["d_mates_mean"])
R["pred_composition_theta_full"] = float(theta_full * R["d_mates_mean"])
R["observed_composition_s3"] = 3.61
R["observed_composition_s4"] = 3.50
R["observed_composition_pooled"] = 3.56
for k2, p in (("theta_archived", R["pred_composition_theta_archived"]),
             ("theta_full", R["pred_composition_theta_full"])):
    R[f"share_explained_{k2}"] = float(p / 3.56)

# ---- 5. same-corpus re-batch: identity binds -----------------------------
shuf_order = json.load(open(f"{DATA}/s4_shuffle_order.json"))
mates_shuf = np.array([mates_mean(shuf_order, alpha_in, u)[0] for u in url_in])
R["d_mates_shuf_minus_orig"] = float((mates_shuf - mates_341).mean())  # = 0 by identity
R["pred_rebatch_theta_full"] = float(theta_full * R["d_mates_shuf_minus_orig"])
R["observed_rebatch"] = 4.72

# sanity: identity check
assert abs(R["d_mates_shuf_minus_orig"]) < 1e-9, "telescoping identity violated"

# ---- 6. equivalent out-vs-in gap needed to fully explain +3.56 -----------
R["gap_needed_full_explanation"] = float(3.56 / (theta_full * R["share_out_mates_mean"]))

json.dump(R, open(f"{DATA}/results_batch_quant.json", "w"), indent=1)

print("=== Out-of-window vs in-window grand means (alphas) ===")
print(f"in-window  n=341: mean {R['alpha_in_mean']:+.2f}  SD {R['alpha_in_sd']:.1f}  share>0 {R['alpha_in_share_pos']:.2f}")
print(f"out-window n=201: mean {R['alpha_out_mean']:+.2f}  SD {R['alpha_out_sd']:.1f}  share>0 {R['alpha_out_share_pos']:.2f}")
print(f"gap (out - in): {R['alpha_gap_out_minus_in']:+.2f} points")
print(f"\nshare of out-of-window mates in 542 batches: {R['share_out_mates_mean']:.3f} (min {R['share_out_mates_min']:.2f}, max {R['share_out_mates_max']:.2f})")
print(f"out-of-window composition: {R['n_undated']} undated (mean {R.get('alpha_undated_mean', 0):+.1f}), {R['n_dated_outside']} dated-outside (mean {R.get('alpha_dated_outside_mean', 0):+.1f})")
print(f"mean mates_fixed: 341-only {R['mates_mean_341']:.2f}  542 {R['mates_mean_542']:.2f}  dM {R['d_mates_mean']:+.3f}")
print(f"\ntheta (full mates) = {theta_full:+.4f} (t={R['theta_full_t']:.2f})   [archived in-window theta {theta_archived:+.4f}]")
print(f"predicted composition shift: {R['pred_composition_theta_archived']:+.3f} (archived) / {R['pred_composition_theta_full']:+.3f} (full)")
print(f"observed: +3.61 (s3) / +3.50 (s4) / pooled +3.56")
print(f"linear anchoring explains {100*R['share_explained_theta_archived']:.0f}% (archived) / {100*R['share_explained_theta_full']:.0f}% (full) of the composition effect")
print(f"re-batch contrast: predicted {R['pred_rebatch_theta_full']:+.3f} (identity) vs observed +4.72 -> nonlinear only")
print(f"out-vs-in gap needed to FULLY explain +3.56 at theta_full: {R['gap_needed_full_explanation']:+.1f} points (actual gap {R['alpha_gap_out_minus_in']:+.1f})")
print("\nsaved data/results_batch_quant.json")
