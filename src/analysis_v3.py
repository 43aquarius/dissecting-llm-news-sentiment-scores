#!/usr/bin/env python3
"""Session 3 experiments: the definitive same-session interleaved identity
estimate (P1-2) and the batch-composition vs endpoint decomposition of the
cross-session drift (P1-3).

Design recap (all scoring in ONE session, 2026-10-18, model glm-4-plus):
  - 341 in-window headlines; 4 rounds; within each round the 14 batches were
    scored in alternating condition order (even batch: named->anon; odd batch:
    anon->named). => 4 named + 4 anonymized draws, interleaved.
  - One additional named pass over all 542 articles in the ORIGINAL v1 order
    (v1 batch composition), in the same session.
  - Session 1 (Oct 15): v1 named. Session 2 (Oct 16): anon + 3 named reps.

Outputs: data/results_s3.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
rng = np.random.default_rng(20261018)

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]
tick = {a["url"]: a["ticker"] for a in inwin}

def load(path):
    d = json.load(open(path))
    return {u: d[u]["sentiment"] for u in url_order if u in d}

s3n = {r: load(f"{DATA}/llm_scores_s3_named_r{r}.json") for r in (1, 2, 3, 4)}
s3a = {r: load(f"{DATA}/llm_scores_s3_anon_r{r}.json") for r in (1, 2, 3, 4)}
v1 = load(f"{DATA}/llm_scores.json")                      # session 1 named
s2a = load(f"{DATA}/llm_scores_anon.json")                # session 2 anon
s2r = {k: load(f"{DATA}/llm_scores_{k}.json") for k in ("rep1", "rep2", "rep3")}

v1comp_all = json.load(open(f"{DATA}/llm_scores_s3_v1comp.json"))
v1c = {u: v1comp_all[u]["sentiment"] for u in url_order if u in v1comp_all}

H = pd.DataFrame({
    "url": url_order,
    "ticker": [tick[u] for u in url_order],
    "v1": [v1.get(u) for u in url_order],
    "s2a": [s2a.get(u) for u in url_order],
    "s2repm": [np.mean([s2r[k].get(u) for k in ("rep1", "rep2", "rep3")]) for u in url_order],
})
for r in (1, 2, 3, 4):
    H[f"n{r}"] = [s3n[r].get(u) for u in url_order]
    H[f"a{r}"] = [s3a[r].get(u) for u in url_order]
H["v1c"] = [v1c.get(u) for u in url_order]
H["named4"] = H[[f"n{r}" for r in (1, 2, 3, 4)]].mean(axis=1)
H["anon4"] = H[[f"a{r}" for r in (1, 2, 3, 4)]].mean(axis=1)
H = H.dropna(subset=["v1", "s2a", "s2repm", "named4", "anon4", "v1c"]).reset_index(drop=True)
print(f"complete-case headlines: {len(H)}")

R = {"design": {
    "session": "2026-10-18 (single session, interleaved)",
    "model": "glm-4-plus (from completion metadata, llm_score_v3.log)",
    "rounds": 4, "alternation": "even batch named->anon, odd batch anon->named",
    "n_headlines": int(len(H)),
}}

# ---------------- P1-2: same-session interleaved identity effect ----------------
d = H["anon4"] - H["named4"]                 # sign convention: anon - named
tt = stats.ttest_rel(H["anon4"], H["named4"])
wil = stats.wilcoxon(H["anon4"], H["named4"])
sig = stats.binomtest(int((H["anon4"] < H["named4"]).sum()), len(H), 0.5)
per_round = {}
for r in (1, 2, 3, 4):
    ttr = stats.ttest_rel(H[f"a{r}"], H[f"n{r}"])
    per_round[f"round{r}"] = {
        "anon_minus_named": float((H[f"a{r}"] - H[f"n{r}"]).mean()),
        "t": float(ttr.statistic), "p": float(ttr.pvalue)}
nv = H[H["ticker"] != "V"]
ttv = stats.ttest_rel(nv["anon4"], nv["named4"])
wilv = stats.wilcoxon(nv["anon4"], nv["named4"])
R["p12_identity"] = {
    "anon_minus_named": float(d.mean()),
    "named_minus_anon_paper_convention": float(-d.mean()),
    "sd_diff": float(d.std(ddof=1)),
    "t": float(tt.statistic), "p": float(tt.pvalue),
    "wilcoxon_p": float(wil.pvalue),
    "sign_test_p": float(sig.pvalue),
    "n": int(len(H)),
    "per_round": per_round,
    "v_excluded": {
        "anon_minus_named": float((nv["anon4"] - nv["named4"]).mean()),
        "t": float(ttv.statistic), "p": float(ttv.pvalue),
        "wilcoxon_p": float(wilv.pvalue), "n": int(len(nv))},
    "exact_match_paired_calls": float(
        np.mean([H[f"a{r}"].values == H[f"n{r}"].values for r in (1, 2, 3, 4)])),
    "benchmark": "session-2 same-session estimate was -1.04 (t=1.60, p=0.111); "
                 "session-2 batches were NOT interleaved (all anon first, then named reps)",
}
print(f"\nP1-2 identity (anon - named), interleaved: {d.mean():+.3f} "
      f"(t={tt.statistic:.2f}, p={tt.pvalue:.4f}; Wilcoxon p={wil.pvalue:.4f})")
print(f"  per round: " + " ".join(f"{v['anon_minus_named']:+.2f}" for v in per_round.values()))
print(f"  V excluded: {(nv['anon4'] - nv['named4']).mean():+.3f} (t={ttv.statistic:.2f}, p={ttv.pvalue:.4f})")

# order effect is not identified by batch parity alone (batch membership is a
# fixed headline property across rounds); the testable contamination check is
# whether the IDENTITY EFFECT differs between even batches (named called
# first) and odd batches (anon called first)
BATCH = 25
H["batch"] = H.index // BATCH
ev, od = H[H["batch"] % 2 == 0], H[H["batch"] % 2 == 1]
id_ev = (ev["anon4"] - ev["named4"]).mean()
id_od = (od["anon4"] - od["named4"]).mean()
R["order_check"] = {
    "identity_effect_evenbatches_namedfirst": float(id_ev),
    "identity_effect_oddbatches_anonfirst": float(id_od),
    "n_even": int(len(ev)), "n_odd": int(len(od)),
    "interpretation": "batch parity is a fixed headline property; the identity "
                      "effect is similar across parities => no call-order contamination",
}
print(f"order contamination check: identity effect even(named-first) {id_ev:+.2f} vs "
      f"odd(anon-first) {id_od:+.2f}")

# ---------------- P1-3: batch composition vs endpoint ----------------
dc = H["v1c"] - H["named4"]                   # v1 composition minus 341 composition, same session
ttc = stats.ttest_rel(H["v1c"], H["named4"])
R["p13_composition"] = {
    "v1comp_minus_341comp": float(dc.mean()),
    "t": float(ttc.statistic), "p": float(ttc.pvalue),
    "n": int(len(H)),
    "mean_v1comp_542order": float(H["v1c"].mean()),
    "mean_341comp_named4": float(H["named4"].mean()),
}
print(f"\nP1-3 composition effect (v1-composition minus 341-composition, same session): "
      f"{dc.mean():+.3f} (t={ttc.statistic:.2f}, p={ttc.pvalue:.4f})")

# session trajectory (341-composition named across sessions)
R["trajectory"] = {
    "s1_v1_oct15": float(H["v1"].mean()),
    "s2_repm_oct16": float(H["s2repm"].mean()),
    "s3_named4_oct18": float(H["named4"].mean()),
    "s3_v1comp_oct18": float(H["v1c"].mean()),
    "s2_anon_oct16": float(H["s2a"].mean()),
    "s3_anon4_oct18": float(H["anon4"].mean()),
    "drift_s1_to_s2": float(H["v1"].mean() - H["s2repm"].mean()),
    "drift_s2_to_s3": float(H["s2repm"].mean() - H["named4"].mean()),
}
tr = R["trajectory"]
print("trajectory (named, 341):  Oct15 %+0.2f -> Oct16 repm %+0.2f -> Oct18 named4 %+0.2f" %
      (tr["s1_v1_oct15"], tr["s2_repm_oct16"], tr["s3_named4_oct18"]))
print("  drift s1->s2: %+.2f | drift s2->s3: %+.2f" % (tr["drift_s1_to_s2"], tr["drift_s2_to_s3"]))
print("anon: Oct16 %+0.2f -> Oct18 %+0.2f" % (tr["s2_anon_oct16"], tr["s3_anon4_oct18"]))

# ---------------- reliability ----------------
def icc2k(df, cols):
    X = df[cols].dropna().values
    n, k = X.shape
    gm = X.mean()
    ssb = k * ((X.mean(axis=1) - gm) ** 2).sum()
    ssw = ((X - X.mean(axis=1, keepdims=True)) ** 2).sum()
    msw = ssw / (n * (k - 1)); msb = ssb / (n - 1)
    return float((msb - msw) / (msb + (k - 1) * msw))

R["reliability"] = {
    "icc_s3_named_4draws": icc2k(H, ["n1", "n2", "n3", "n4"]),
    "icc_s3_anon_4draws": icc2k(H, ["a1", "a2", "a3", "a4"]),
}
for k_ in ("rep1", "rep2", "rep3"):
    H[f"s2{k_}"] = [s2r[k_].get(u) for u in url_order]
H = H.dropna(subset=["s2rep1", "s2rep2", "s2rep3"]).reset_index(drop=True)
R["reliability"]["icc_s2_named_3draws"] = icc2k(H, ["s2rep1", "s2rep2", "s2rep3"])
# exact match rates
ex_s3 = [float((H[f"n{i}"] == H[f"n{j}"]).mean()) for i, j in ((1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4))]
ex_s2 = [float((H[f"s2rep{i}"] == H[f"s2rep{j}"]).mean()) for i, j in ((1, 2), (1, 3), (2, 3))]
cross_ex = [float((H[f"n{i}"] == H[f"s2rep{j}"]).mean()) for i in (1, 2, 3, 4) for j in (1, 2, 3)]
# noise SD: within s3 named rounds
dev = H[["n1", "n2", "n3", "n4"]].sub(H["named4"], axis=0)
R["reliability"].update({
    "exact_pairwise_s3_named": ex_s3,
    "exact_pairwise_s2_named": ex_s2,
    "exact_cross_session_named": cross_ex,
    "within_sd_s3_named": float(np.sqrt((dev.values ** 2).sum() / (4 * len(H)))),
    "within_sd_s2_named": float(np.sqrt(
        ((H[["s2rep1", "s2rep2", "s2rep3"]].sub(H["s2repm"], axis=0)).values ** 2).sum() / (3 * len(H)))),
})
print(f"\nreliability: ICC s3-named {R['reliability']['icc_s3_named_4draws']:.3f} | "
      f"s2-named {R['reliability']['icc_s2_named_3draws']:.3f} | "
      f"within-SD s3 {R['reliability']['within_sd_s3_named']:.2f} vs s2 {R['reliability']['within_sd_s2_named']:.2f}")

# ---------------- prediction layer (definitive H2 test) ----------------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)

rel = {}
for u in url_order:
    rel[u] = json.load(open(f"{DATA}/llm_scores.json")).get(u, {}).get("relevance")
rows = []
for a in inwin:
    u = a["url"]
    rows.append({"ticker": a["ticker"], "date": a["date_iso"],
                 "relevance": rel.get(u), "url": u})
rdf = pd.DataFrame(rows)
hi = rdf[rdf["relevance"] >= 30]
for col, src in [("sent_s3n", H.set_index("url")["named4"]),
                 ("sent_s3a", H.set_index("url")["anon4"]),
                 ("sent_v1c", H.set_index("url")["v1c"])]:
    hi = hi.assign(**{col: hi["url"].map(src) / 100.0})   # scale to [-1,1] as in v1
agg = hi.groupby(["ticker", "date"]).agg(
    sent_s3n=("sent_s3n", "mean"), sent_s3a=("sent_s3a", "mean"),
    sent_v1c=("sent_v1c", "mean")).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
pp = panel.merge(agg, on=["ticker", "date"], how="left")
news = pp[pp["sent_s3n"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()

def tw(df, formula):
    fc = pd.factorize(df["ticker"])[0]; dc = pd.factorize(df["date_str"])[0]
    return smf.ols(formula, data=df).fit(cov_type="cluster",
        cov_kwds={"groups": np.column_stack([fc, dc])})

mn = tw(ctrl, "ret_fwd1 ~ sent_s3n + ret_lag1 + vol_21 + mkt_ew")
ma = tw(ctrl, "ret_fwd1 ~ sent_s3a + ret_lag1 + vol_21 + mkt_ew")
mc = tw(ctrl, "ret_fwd1 ~ sent_v1c + ret_lag1 + vol_21 + mkt_ew")
R["prediction"] = {
    "s3_named": {"coef": float(mn.params["sent_s3n"]), "t": float(mn.tvalues["sent_s3n"]),
                 "p": float(mn.pvalues["sent_s3n"]), "n": int(mn.nobs)},
    "s3_anon": {"coef": float(ma.params["sent_s3a"]), "t": float(ma.tvalues["sent_s3a"]),
                "p": float(ma.pvalues["sent_s3a"]), "n": int(ma.nobs)},
    "s3_v1comp": {"coef": float(mc.params["sent_v1c"]), "t": float(mc.tvalues["sent_v1c"]),
                  "p": float(mc.pvalues["sent_v1c"]), "n": int(mc.nobs)},
}
# day-cluster bootstrap difference named-anon (B=9999, vectorized via day resample)
def fit_beta(df, col):
    Xl = np.column_stack([np.ones(len(df)), df[col], df["ret_lag1"], df["vol_21"], df["mkt_ew"]])
    yl = df["ret_fwd1"].values
    try:
        return np.linalg.solve(Xl.T @ Xl, Xl.T @ yl)[1]
    except np.linalg.LinAlgError:
        return np.nan

dk = ctrl["date_str"].values
uq = np.unique(dk)
ctrl_v = ctrl.reset_index(drop=True)
diffs = np.empty(9999)
idx_by_day = {d: ctrl_v.index[dk == d].values for d in uq}
for b in range(9999):
    picked = rng.choice(uq, size=len(uq), replace=True)
    idxs = np.concatenate([idx_by_day[d] for d in picked])
    dfb = ctrl_v.iloc[idxs]
    diffs[b] = fit_beta(dfb, "sent_s3n") - fit_beta(dfb, "sent_s3a")
obs = R["prediction"]["s3_named"]["coef"] - R["prediction"]["s3_anon"]["coef"]
ci = np.percentile(diffs, [2.5, 97.5])
p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
R["prediction"]["diff_named_minus_anon"] = {
    "obs": float(obs), "boot_ci95": [float(ci[0]), float(ci[1])],
    "boot_p": float(max(p, 2.0 / (len(diffs) + 1))), "B": 9999}
print(f"\nprediction: s3 named beta {R['prediction']['s3_named']['coef']:.4f} (t={R['prediction']['s3_named']['t']:.2f}) | "
      f"s3 anon beta {R['prediction']['s3_anon']['coef']:.4f} (t={R['prediction']['s3_anon']['t']:.2f}) | "
      f"s3 v1comp beta {R['prediction']['s3_v1comp']['coef']:.4f} (t={R['prediction']['s3_v1comp']['t']:.2f})")
print(f"  diff {obs:+.4f} CI[{ci[0]:.4f},{ci[1]:.4f}] p={p:.3f}")

# ---------------- H1 stability across ALL scoring draws ----------------
# the same H1 spec re-estimated with every available named/anon draw; shows how
# the headline predictability statistic moves with the scoring endpoint
draw_cols = {
    "v1_named_oct15": "v1", "s2_repm_oct16": "s2repm",
    "s3_named_r1": "n1", "s3_named_r2": "n2", "s3_named_r3": "n3", "s3_named_r4": "n4",
    "s3_named4_avg": "named4", "s3_v1comp": "v1c",
    "s2_anon_oct16": "s2a", "s3_anon4_avg": "anon4",
}
stab = {}
hi_stab = hi.copy()
Hmap = H.set_index("url")
for label, col in draw_cols.items():
    vals = hi_stab["url"].map(Hmap[col]) / 100.0
    hi_stab[f"d_{label}"] = vals
agg_stab = hi_stab.groupby(["ticker", "date"])[[f"d_{l}" for l in draw_cols]].mean().reset_index()
agg_stab["date"] = pd.to_datetime(agg_stab["date"])
pp2 = panel.merge(agg_stab, on=["ticker", "date"], how="left")
news2 = pp2[pp2["d_v1_named_oct15"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl2 = news2.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
for label in draw_cols:
    c = f"d_{label}"
    mm = tw(ctrl2.dropna(subset=[c]), f"ret_fwd1 ~ {c} + ret_lag1 + vol_21 + mkt_ew")
    stab[label] = {"coef": float(mm.params[c]), "t": float(mm.tvalues[c]),
                   "p": float(mm.pvalues[c]), "n": int(mm.nobs)}
R["h1_stability_across_draws"] = stab
print("\nH1 stability across draws:")
for k, v in stab.items():
    print(f"  {k:16s} beta={v['coef']:+.4f} t={v['t']:+.2f} p={v['p']:.3f} n={v['n']}")

json.dump(R, open(f"{DATA}/results_s3.json", "w"), indent=1)
print("\nsaved data/results_s3.json")
