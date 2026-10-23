#!/usr/bin/env python3
"""Equivalence testing (TOST) for predictive-coefficient differences.

Implements the revision plan's Phase-2 Task B: "failure to detect a
difference" is NOT evidence of equivalence. This script replaces that
inference with a formal equivalence assessment where the data support one,
and states explicitly where they cannot.

Methodology
-----------
- Same day-cluster paired bootstrap as analysis_v2/v3/v5 (B=9,999, fresh
  seed 20261020), full bootstrap distributions stored.
- Percentile TOST: equivalence at margin delta iff the 90% percentile
  interval of Delta-beta lies inside (-delta, +delta). Normal-approximation
  TOST p-values reported as secondary.
- EMT (equivalence margin threshold) = max(|q5|, |q95|): the smallest
  margin at which the contrast passes -- margin-free reporting so any
  reader-preferred margin can be tested directly.
- Primary margin: delta* = 0.5 x beta_named (v2 H1 benchmark), the
  "same order of magnitude" standard common in replication practice.
  Sensitivity: 0.25x and 1.0x.
- Analytic power at true difference 0 (and delta*/2); N-multiple needed
  for 80% power at delta*.
- HONESTY LABEL: this analysis was designed in revision, AFTER the
  difference tests were computed. It is exploratory, outside the declared
  family (forking-paths discipline, Sec. 3.5). The margin is set by
  convention (half the benchmark), not tuned to pass any contrast; EMT is
  reported margin-free.

Contrasts (all next-day predictive coefficient, spec
  ret_fwd1 ~ X + ret_lag1 + vol_21 + mkt_ew unless noted):
  C1 named vs anonymized, cross-session (v2 sample)     [difference p=.887]
  C2 named vs anonymized, interleaved session-3         [p=.622, definitive]
  C3 N5 vs A5, session-5 corrected anonymization        [p=.929]
  C4 N5 vs S5, session-5 identity swap                  [p=.917]
  C5 named vs LM dictionary (v2 sample)                 [p=.731]
  C6 priced vs clean, same-day-control spec             [p=.100, directional]
  C7 clean coefficient vs zero (one-sample TOST)        [supports H4 wording]
  C8 session-2 same-session named-repeat-mean vs anon   [p=.905]

Output: data/results_equivalence.json
"""
import json
import re
import numpy as np
import pandas as pd
from scipy import stats

DATA = "/home/z/my-project/data"
rng = np.random.default_rng(20261020)
B = 9999
Z90 = 1.6448536269514722      # z_{0.95}
Z80P = 0.8416212335729143     # Phi^{-1}(0.80) = 0.8416 -> for 80% power calc

PRICE_PAT = re.compile(
    r"\b(rose|rises?|risen|jump(?:s|ed|ing)?|surge[sd]?|surging|soar(?:s|ed|ing)?|"
    r"climb(?:s|ed|ing)?|rall(?:y|ies|ied|ing)|gain(?:s|ed|ing)?|fell|falls?|fallen|"
    r"drop(?:s|ped|ping)?|dropped|plunge[sd]?|plunging|sink[s]?|sank|sinking|slide[sd]?|"
    r"slump(?:s|ed|ing)?|tumbl(?:e|es|ed|ing)|crash(?:es|ed|ing)?|declin(?:e|es|ed|ing)|"
    r"rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)|spike[sd]?|spiking|dip(?:s|ped)?|"
    r"up\s?\d|down\s?\d|\d+%\s?(?:up|down)|hit\s+(?:a\s+)?(?:record|new|52)|"
    r"after\s+(?:earnings|results|guidance|beating|missing))\b", re.I)

# ---------------- rebuild the v2 sample (verbatim from analysis_v2.py) --------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)
panel["ret_fwd2"] = panel.groupby("ticker")["ret"].shift(-2)

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
hi = adf[adf["relevance"] >= 30]
agg = hi.groupby(["ticker", "date"]).agg(
    sent=("s_orig", "mean"), sent_anon=("s_anon", "mean"),
    rep1=("s_rep1", "mean"), rep2=("s_rep2", "mean"), rep3=("s_rep3", "mean"),
    lm_tone=("lm_tone", "mean"), n_news=("url", "count"),
    priced_any=("priced", "max"), relevance=("relevance", "mean"),
).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
# session-2 same-session named repeat mean (for C8)
agg["rep_m"] = agg[["rep1", "rep2", "rep3"]].mean(axis=1)

p = panel.merge(agg, on=["ticker", "date"], how="left")
if "lm_tone_y" in p.columns:
    p["lm_tone"] = p["lm_tone_y"]
if "n_news_y" in p.columns:
    p["n_news"] = p["n_news_y"]
for col in ("sent", "sent_anon", "rep1", "rep2", "rep3", "rep_m", "lm_tone"):
    if col in p.columns:
        p[col] = p[col] / 100.0
p["priced_any"] = p["priced_any"].astype(bool)

news = p[p["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"]).sort_values(["ticker", "date"])
ctrl2 = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
ctrl2 = ctrl2.dropna(subset=["sent_anon"])
ctrl2["priced_any"] = ctrl2["priced_any"].astype(bool)
ctrl2["lm_tone"] = pd.to_numeric(ctrl2["lm_tone"], errors="coerce")
ctrl2["sent_repm"] = ctrl2["rep_m"]
ctrl2 = ctrl2.reset_index(drop=True)

# ---------------- rebuild the s3 (interleaved) sample (verbatim v3) ----------
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]
tick = {a["url"]: a["ticker"] for a in inwin}

def load(path):
    d = json.load(open(path))
    return {u: d[u]["sentiment"] for u in url_order if u in d}

s3n = {r: load(f"{DATA}/llm_scores_s3_named_r{r}.json") for r in (1, 2, 3, 4)}
s3a = {r: load(f"{DATA}/llm_scores_s3_anon_r{r}.json") for r in (1, 2, 3, 4)}
s2a = load(f"{DATA}/llm_scores_anon.json")
s2r = {k: load(f"{DATA}/llm_scores_{k}.json") for k in ("rep1", "rep2", "rep3")}
v1c_all = json.load(open(f"{DATA}/llm_scores_s3_v1comp.json"))
v1c = {u: v1c_all[u]["sentiment"] for u in url_order if u in v1c_all}
v1 = load(f"{DATA}/llm_scores.json")

H3 = pd.DataFrame({
    "url": url_order,
    "ticker": [tick[u] for u in url_order],
    "v1": [v1.get(u) for u in url_order],
    "s2a": [s2a.get(u) for u in url_order],
    "s2repm": [np.mean([s2r[k].get(u) for k in ("rep1", "rep2", "rep3")]) for u in url_order],
})
for r in (1, 2, 3, 4):
    H3[f"n{r}"] = [s3n[r].get(u) for u in url_order]
    H3[f"a{r}"] = [s3a[r].get(u) for u in url_order]
H3["v1c"] = [v1c.get(u) for u in url_order]
H3["named4"] = H3[[f"n{r}" for r in (1, 2, 3, 4)]].mean(axis=1)
H3["anon4"] = H3[[f"a{r}" for r in (1, 2, 3, 4)]].mean(axis=1)
H3 = H3.dropna(subset=["v1", "s2a", "s2repm", "named4", "anon4", "v1c"]).reset_index(drop=True)

relmap = {u: orig.get(u, {}).get("relevance") for u in url_order}
rows3 = [{"ticker": a["ticker"], "date": a["date_iso"], "relevance": relmap.get(u), "url": u}
         for a, u in zip(inwin, url_order)]
rdf3 = pd.DataFrame(rows3)
hi3 = rdf3[rdf3["relevance"] >= 30]
for col, src in [("sent_s3n", H3.set_index("url")["named4"]),
                 ("sent_s3a", H3.set_index("url")["anon4"])]:
    hi3 = hi3.assign(**{col: hi3["url"].map(src) / 100.0})
agg3 = hi3.groupby(["ticker", "date"]).agg(
    sent_s3n=("sent_s3n", "mean"), sent_s3a=("sent_s3a", "mean")).reset_index()
agg3["date"] = pd.to_datetime(agg3["date"])
pp3 = panel.merge(agg3, on=["ticker", "date"], how="left")
ctrl3 = pp3[pp3["sent_s3n"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl3 = ctrl3.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
ctrl3 = ctrl3.reset_index(drop=True)

# ---------------- rebuild the s5 sample (verbatim v5) ------------------------
N5 = load(f"{DATA}/llm_scores_s5_named.json")
A5 = load(f"{DATA}/llm_scores_s5_anonv2.json")
S5 = load(f"{DATA}/llm_scores_s5_swap.json")
P5 = load(f"{DATA}/llm_scores_s5_placeholder.json")
T0a = load(f"{DATA}/llm_scores_s5_t0a.json")
T0b = load(f"{DATA}/llm_scores_s5_t0b.json")
complete = [u for u in url_order if u in N5 and u in A5 and u in S5 and u in P5 and u in T0a and u in T0b]
H5 = pd.DataFrame({"url": complete, "ticker": [tick[u] for u in complete],
                   "N5": [N5[u] for u in complete], "A5": [A5[u] for u in complete],
                   "S5": [S5[u] for u in complete], "P5": [P5[u] for u in complete]})
rows5 = [{"ticker": a["ticker"], "date": a["date_iso"], "relevance": relmap.get(u), "url": u}
         for a, u in zip(inwin, url_order)]
rdf5 = pd.DataFrame(rows5)
hi5 = rdf5[rdf5["relevance"] >= 30].copy()
srcs = {"N5": H5.set_index("url")["N5"], "A5": H5.set_index("url")["A5"],
        "S5": H5.set_index("url")["S5"], "P5": H5.set_index("url")["P5"]}
for n, s in srcs.items():
    hi5[f"sent_{n}"] = hi5["url"].map(s) / 100.0
agg5 = hi5.groupby(["ticker", "date"]).agg({f"sent_{n}": "mean" for n in srcs}).reset_index()
agg5["date"] = pd.to_datetime(agg5["date"])
pp5 = panel.merge(agg5, on=["ticker", "date"], how="left")
ctrl5 = pp5[pp5["sent_N5"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl5 = ctrl5.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
ctrl5 = ctrl5.reset_index(drop=True)

# ---------------- sanity: reproduce stored point estimates -------------------
def fit_beta(df, col, sameday=False):
    cols = [np.ones(len(df)), df[col], df["ret"], df["ret_lag1"], df["vol_21"], df["mkt_ew"]] \
        if sameday else [np.ones(len(df)), df[col], df["ret_lag1"], df["vol_21"], df["mkt_ew"]]
    Xl = np.column_stack(cols)
    yl = df["ret_fwd1"].values
    try:
        return np.linalg.solve(Xl.T @ Xl, Xl.T @ yl)[1]
    except np.linalg.LinAlgError:
        return np.nan

beta_named = fit_beta(ctrl2, "sent")
beta_anon = fit_beta(ctrl2, "sent_anon")
beta_lm = fit_beta(ctrl2, "lm_tone")
beta_repm = fit_beta(ctrl2, "sent_repm")
beta_s3n = fit_beta(ctrl3, "sent_s3n")
beta_s3a = fit_beta(ctrl3, "sent_s3a")
beta_N5 = fit_beta(ctrl5, "sent_N5")
beta_A5 = fit_beta(ctrl5, "sent_A5")
beta_S5 = fit_beta(ctrl5, "sent_S5")
beta_pr = fit_beta(ctrl2[ctrl2["priced_any"]], "sent", sameday=True)
beta_cl = fit_beta(ctrl2[~ctrl2["priced_any"]], "sent", sameday=True)

rv2 = json.load(open(f"{DATA}/results_v2.json"))
rs3 = json.load(open(f"{DATA}/results_s3.json"))
rs5 = json.load(open(f"{DATA}/results_s5.json"))
rrev = json.load(open(f"{DATA}/results_revision.json"))

chk = [
    ("v2 n", len(ctrl2), 205), ("v3 n", len(ctrl3), 205), ("v5 n", len(ctrl5), 205),
    ("beta_named", beta_named, rv2["h1_baseline"]["coef"]),
    ("beta_anon", beta_anon, rv2["h2_prediction"]["anon"]["coef"]),
    ("beta_lm", beta_lm, rv2["h2_prediction"]["lm_dict"]["coef"]),
    ("beta_s3n", beta_s3n, rs3["prediction"]["s3_named"]["coef"]),
    ("beta_s3a", beta_s3a, rs3["prediction"]["s3_anon"]["coef"]),
    ("beta_N5", beta_N5, rs5["prediction"]["N5"]["beta"]),
    ("beta_A5", beta_A5, rs5["prediction"]["A5"]["beta"]),
    ("beta_S5", beta_S5, rs5["prediction"]["S5"]["beta"]),
    ("beta_priced", beta_pr, rv2["h4_echo"]["priced_any"]["coef"]),
    ("beta_clean", beta_cl, rv2["h4_echo"]["clean"]["coef"]),
]
for name, got, want in chk:
    tol = 0.5 if isinstance(want, int) else 1e-9
    assert abs(got - want) < tol, f"REBUILD MISMATCH {name}: {got} vs {want}"
print("rebuild checks passed:", ", ".join(n for n, _, _ in chk))

# session-2 repeat-mean contrast: stored in results_revision.json
c8_stored = rrev.get("same_session_prediction", {})   # keys unknown; probe below
print("results_revision same-session keys:", list(c8_stored.keys()) if c8_stored
      else [k for k in rrev.keys()])

# ---------------- bootstrap machinery ----------------------------------------
def day_cluster_boot_contrast(df, colA, colB=None, sameday=False, b=B):
    """Day-cluster paired bootstrap of (beta_colA - beta_colB). colB None ->
    one-sample bootstrap of beta_colA (vs 0)."""
    dk = df["date_str"].values
    uq = np.unique(dk)
    idx_by_day = {d: np.where(dk == d)[0] for d in uq}
    n_days = len(uq)
    colsA = [np.ones(len(df)), df[colA]]
    colsA += [df["ret"]] if sameday else []
    colsA += [df["ret_lag1"], df["vol_21"], df["mkt_ew"]]
    XA = np.column_stack(colsA)
    if colB is not None:
        colsB = [np.ones(len(df)), df[colB]]
        colsB += [df["ret"]] if sameday else []
        colsB += [df["ret_lag1"], df["vol_21"], df["mkt_ew"]]
        XB = np.column_stack(colsB)
    else:
        XB = None
    y = df["ret_fwd1"].values
    out = []
    for _ in range(b):
        picks = rng.integers(0, n_days, size=n_days)
        idx = np.concatenate([idx_by_day[uq[k]] for k in picks])
        try:
            ba = np.linalg.solve(XA[idx].T @ XA[idx], XA[idx].T @ y[idx])[1]
            bb = 0.0 if XB is None else \
                np.linalg.solve(XB[idx].T @ XB[idx], XB[idx].T @ y[idx])[1]
        except np.linalg.LinAlgError:
            continue
        out.append(ba - bb)
    return np.array(out)

def day_cluster_boot_priced_clean(df, b=B):
    """Same-day-control spec; within each draw split rows by priced flag
    (replicates the v4/P0-10 design). Returns (diff dist, clean-beta dist,
    priced-beta dist)."""
    X = np.column_stack([np.ones(len(df)), df["sent"], df["ret"],
                         df["ret_lag1"], df["vol_21"], df["mkt_ew"]])
    y = df["ret_fwd1"].values
    pv = df["priced_any"].values.astype(bool)
    dk = df["date_str"].values
    uq = np.unique(dk)
    idx_by_day = {d: np.where(dk == d)[0] for d in uq}
    n_days = len(uq)
    diffs, cleans, priceds = [], [], []
    for _ in range(b):
        picks = rng.integers(0, n_days, size=n_days)
        idx = np.concatenate([idx_by_day[uq[k]] for k in picks])
        pm = pv[idx]
        i_pr, i_cl = idx[pm], idx[~pm]
        if len(i_pr) < 25 or len(i_cl) < 25:
            continue
        try:
            bp = np.linalg.solve(X[i_pr].T @ X[i_pr], X[i_pr].T @ y[i_pr])[1]
            bc = np.linalg.solve(X[i_cl].T @ X[i_cl], X[i_cl].T @ y[i_cl])[1]
        except np.linalg.LinAlgError:
            continue
        diffs.append(bp - bc); cleans.append(bc); priceds.append(bp)
    return np.array(diffs), np.array(cleans), np.array(priceds)

# ---------------- TOST statistics --------------------------------------------
def tost(dist, obs, beta_bench):
    q5, q95 = np.percentile(dist, [5, 95])
    q25, q975 = np.percentile(dist, [2.5, 97.5])
    se = float(dist.std(ddof=1))
    emt = max(abs(q5), abs(q95))
    res = {"obs": float(obs), "n_boot": int(len(dist)),
           "ci90": [float(q5), float(q95)], "ci95": [float(q25), float(q975)],
           "se_boot": se, "emt": float(emt), "emt_over_benchmark": float(emt / beta_bench)}
    for tag, frac in (("delta_25pct", 0.25), ("delta_50pct", 0.50), ("delta_100pct", 1.0)):
        d = frac * beta_bench
        verdict = bool(q5 > -d and q95 < d)
        p1 = 1 - stats.norm.cdf((obs + d) / se)     # H0: diff <= -d
        p2 = stats.norm.cdf((obs - d) / se)         # H0: diff >= +d
        p_tost = float(max(p1, p2))
        # analytic power at true diff 0 and at d/2 (normal approx)
        lo_, hi_ = -d + Z90 * se, d - Z90 * se
        pw0 = max(0.0, stats.norm.cdf((hi_) / se) - stats.norm.cdf((lo_) / se)) if hi_ > lo_ else 0.0
        tau = d / 2
        pwh = max(0.0, stats.norm.cdf((hi_ - tau) / se) - stats.norm.cdf((lo_ - tau) / se)) if hi_ > lo_ else 0.0
        # N multiple for 80% power at margin d (central-two-sided 80%:
        # need (d - z*SE)/SE = Phi^-1(0.90) = 1.2816  ->  SE* = d/2.9266)
        se_star = d / (1.2815515655446004 + Z90)
        res[tag] = {"margin": float(d),
                    "percentile_verdict": verdict,
                    "tost_p_normal": p_tost,
                    "power_at_zero": float(pw0),
                    "power_at_half_margin": float(pwh),
                    "n_multiple_for_80pct": float((se / se_star) ** 2)}
    return res

# ---------------- run all contrasts ------------------------------------------
R = {"design": {
    "script": "equivalence_testing.py", "seed": 20261020, "B": B,
    "benchmark_beta_named": float(beta_named),
    "primary_margin": float(0.5 * beta_named),
    "margin_rule": "delta* = 0.5 x benchmark named coefficient (same-order-of-"
                   "magnitude standard); sensitivity at 0.25x and 1.0x; EMT "
                   "reported margin-free",
    "status": "EXPLORATORY: designed in revision after difference tests were "
              "computed; outside the declared BH family; percentual TOST on "
              "day-cluster bootstrap (90% CI inside +/- delta)",
    "sample_sd_sent_firmday": float(ctrl2["sent"].std(ddof=1)),
    "n": {"v2": int(len(ctrl2)), "s3": int(len(ctrl3)), "s5": int(len(ctrl5))},
}}
bench = beta_named
sd_sent = float(ctrl2["sent"].std(ddof=1))

print(f"\nbenchmark beta = {beta_named:.6f}; delta* = {0.5*beta_named:.6f}; "
      f"SD(sent) = {sd_sent:.4f} -> delta* = {0.5*beta_named*sd_sent*1e4:.1f} bps per 1-SD shock")

C = {}

# C1: cross-session named vs anon
obs = beta_named - beta_anon
dist = day_cluster_boot_contrast(ctrl2, "sent", "sent_anon")
C["C1_named_vs_anon_crosssession"] = tost(dist, obs, bench)
# C8: session-2 same-session repeat-mean vs anon
obs8 = beta_repm - beta_anon
dist8 = day_cluster_boot_contrast(ctrl2, "sent_repm", "sent_anon")
C["C8_s2repmean_vs_anon_samesession"] = tost(dist8, obs8, bench)
# C5: named vs LM
obs5 = beta_named - beta_lm
dist5 = day_cluster_boot_contrast(ctrl2, "sent", "lm_tone")
C["C5_named_vs_lmdict"] = tost(dist5, obs5, bench)
# C2: interleaved s3
obs2 = beta_s3n - beta_s3a
dist2 = day_cluster_boot_contrast(ctrl3, "sent_s3n", "sent_s3a")
C["C2_named_vs_anon_interleaved"] = tost(dist2, obs2, bench)
# C3/C4: session-5
obs3 = beta_N5 - beta_A5
dist3 = day_cluster_boot_contrast(ctrl5, "sent_N5", "sent_A5")
C["C3_N5_vs_A5"] = tost(dist3, obs3, bench)
obs4 = beta_N5 - beta_S5
dist4 = day_cluster_boot_contrast(ctrl5, "sent_N5", "sent_S5")
C["C4_N5_vs_S5"] = tost(dist4, obs4, bench)
# C6/C7: priced-clean split (same-day spec)
d6, c7, p6 = day_cluster_boot_priced_clean(ctrl2)
C["C6_priced_vs_clean"] = tost(d6, beta_pr - beta_cl, bench)
C["C7_clean_vs_zero"] = tost(c7, beta_cl, bench)

R["contrasts"] = C
R["bps_translation"] = {
    "sd_sent_firmday": sd_sent,
    "benchmark_response_per_sd_bps": float(bench * sd_sent * 1e4),
    "delta_star_bps_per_sd": float(0.5 * bench * sd_sent * 1e4),
    "delta_25pct_bps_per_sd": float(0.25 * bench * sd_sent * 1e4),
}

json.dump(R, open(f"{DATA}/results_equivalence.json", "w"), indent=1)

# ---------------- report ------------------------------------------------------
print(f"\n{'contrast':38s} {'obs':>9s} {'90% CI':22s} {'EMT':>8s} {'EMT/b':>6s} "
      f"{'TOST@50%':>8s} {'pw@0':>6s} {'Nmult':>7s}")
for k, v in C.items():
    d50 = v["delta_50pct"]
    print(f"{k:38s} {v['obs']:>+9.4f} [{v['ci90'][0]:+.4f},{v['ci90'][1]:+.4f}] "
          f"{v['emt']:8.4f} {v['emt_over_benchmark']:6.2f} "
          f"{'PASS' if d50['percentile_verdict'] else 'FAIL':>8s} "
          f"{d50['power_at_zero']:6.2f} {d50['n_multiple_for_80pct']:7.1f}")
print("\nwrote data/results_equivalence.json")
