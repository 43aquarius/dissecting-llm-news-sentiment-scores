#!/usr/bin/env python3
"""ANALYSIS v2 (audit-driven re-examination). Pre-specified test family:

  H1 baseline : named LLM sentiment -> next-day return (augmented inference)
  H2 identity : anonymized scores vs named scores (level shift, agreement,
                and predictive coefficient difference via cluster bootstrap)
  H3 stability: repeat-call ICC and agreement (4 draws incl. original)
  H4 echo     : price-language headline subset vs clean subset; + same-day ret control
  H5 selection: news coverage selected on realized volatility/moves

Inference upgrades over v1:
  - wild cluster bootstrap (Rademacher, day-level) for H1
  - Benjamini-Hochberg FDR over the declared 5-hypothesis family
  - formal coefficient-difference tests (never inferred from separate significance)
Output: data/results_v2.json
"""
import json
import re
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
rng = np.random.default_rng(20261016)
pd.set_option("display.width", 200)

PRICE_PAT = re.compile(
    r"\b(rose|rises?|risen|jump(?:s|ed|ing)?|surge[sd]?|surging|soar(?:s|ed|ing)?|"
    r"climb(?:s|ed|ing)?|rall(?:y|ies|ied|ing)|gain(?:s|ed|ing)?|fell|falls?|fallen|"
    r"drop(?:s|ped|ping)?|dropped|plunge[sd]?|plunging|sink[s]?|sank|sinking|slide[sd]?|"
    r"slump(?:s|ed|ing)?|tumbl(?:e|es|ed|ing)|crash(?:es|ed|ing)?|declin(?:e|es|ed|ing)|"
    r"rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)|spike[sd]?|spiking|dip(?:s|ped)?|"
    r"up\s?\d|down\s?\d|\d+%\s?(?:up|down)|hit\s+(?:a\s+)?(?:record|new|52)|"
    r"after\s+(?:earnings|results|guidance|beating|missing))\b", re.I)

# ---------------- load and rebuild the news firm-day panel with all conditions ----------------
def build():
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

    # relevance>=30 filter identical to v1
    hi = adf[adf["relevance"] >= 30]
    agg = hi.groupby(["ticker", "date"]).agg(
        sent=("s_orig", "mean"), sent_anon=("s_anon", "mean"),
        rep1=("s_rep1", "mean"), rep2=("s_rep2", "mean"), rep3=("s_rep3", "mean"),
        lm_tone=("lm_tone", "mean"), n_news=("url", "count"),
        priced_any=("priced", "max"), relevance=("relevance", "mean"),
    ).reset_index()
    agg["date"] = pd.to_datetime(agg["date"])

    p = panel.merge(agg, on=["ticker", "date"], how="left")
    # unify column names (merge suffixes) and scale to [-1,1] as in v1
    if "lm_tone_y" in p.columns:
        p["lm_tone"] = p["lm_tone_y"]
    if "n_news_y" in p.columns:
        p["n_news"] = p["n_news_y"]
    for col in ("sent", "sent_anon", "rep1", "rep2", "rep3", "lm_tone"):
        if col in p.columns:
            p[col] = p[col] / 100.0
    p["priced_any"] = p["priced_any"].astype(bool)
    return panel, adf, p

panel, adf, p = build()
news = p[p["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"]).sort_values(["ticker", "date"])
ctrl = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
ctrl = ctrl.dropna(subset=["sent_anon"])  # same sample for named/anon comparisons
ctrl["priced_any"] = ctrl["priced_any"].astype(bool)
ctrl["lm_tone"] = pd.to_numeric(ctrl["lm_tone"], errors="coerce")
print(f"news firm-days: {len(news)} | regression sample: {len(ctrl)} | "
      f"article-level n: {len(adf)}")

R = {"design": {
    "n_articles_in_window": int(len(adf)),
    "n_firmdays": int(len(news)),
    "n_reg_sample": int(len(ctrl)),
    "scoring_rounds": "original(named) + anonymized + 3 repeat named calls",
    "test_family": ["H1 named baseline fwd1", "H2 named-vs-anon difference",
                    "H3 repeat-call ICC", "H4 price-language echo split", "H5 coverage selection"],
}}

# ---------------- H3: repeat-call reliability (article level, 4 draws) ----------------
X4 = adf[["s_orig", "s_rep1", "s_rep2", "s_rep3"]].dropna()
n, k = X4.shape
grand = X4.values.mean()
row_m = X4.values.mean(axis=1)
ms_between = (k * ((row_m - grand) ** 2).sum()) / (n - 1)     # between-articles
ms_within = (X4.values.var(axis=1, ddof=1) * (k - 1)).sum() / (n * (k - 1))
icc_2k = (ms_between - ms_within) / (ms_between + (k - 1) * ms_within)
pair_corr = X4.corr().values[np.triu_indices(4, 1)]
exact_all = (X4.nunique(axis=1) == 1).mean()
R["h3_stability"] = {
    "n": int(n), "rounds": 4, "icc_2k": float(icc_2k),
    "mean_pairwise_pearson": float(pair_corr.mean()),
    "min_pairwise_pearson": float(pair_corr.min()),
    "exact_identical_all4": float(exact_all),
    "mean_abs_diff_any_pair": float(X4.values.std(axis=1, ddof=1).mean()),
}
print(f"\nH3 stability: ICC(2,k)={icc_2k:.4f}, pairwise r={pair_corr.mean():.3f}, "
      f"all-4-identical={exact_all:.3f}")

# ---------------- H2 (measurement layer): named vs anonymized ----------------
H = adf.dropna(subset=["s_orig", "s_anon"])
d = H["s_orig"] - H["s_anon"]
tt = stats.ttest_rel(H["s_orig"], H["s_anon"])
wil = stats.wilcoxon(H["s_orig"], H["s_anon"])
R["h2_measurement"] = {
    "n": int(len(H)),
    "mean_named": float(H["s_orig"].mean()), "mean_anon": float(H["s_anon"].mean()),
    "mean_shift": float(d.mean()), "shift_t": float(tt.statistic), "shift_p": float(tt.pvalue),
    "wilcoxon_p": float(wil.pvalue),
    "pearson": float(H[["s_orig", "s_anon"]].corr().iloc[0, 1]),
    "spearman": float(H[["s_orig", "s_anon"]].corr(method="spearman").iloc[0, 1]),
    "exact_match": float((H["s_orig"] == H["s_anon"]).mean()),
    "mean_abs_diff": float(d.abs().mean()),
    "repeat_noise_benchmark_mad": float(R["h3_stability"]["mean_abs_diff_any_pair"]),
    "changed_frac": float((H["s_anon"] != H["s_orig"]).mean()),
}
print(f"H2 measurement: shift={d.mean():.2f} (t={tt.statistic:.2f}, p={tt.pvalue:.4f}), "
      f"r={R['h2_measurement']['pearson']:.3f}, |diff|={d.abs().mean():.2f} "
      f"(noise benchmark {R['h3_stability']['mean_abs_diff_any_pair']:.2f})")

# ---------------- regression helper: two-way clustered OLS ----------------
def tw(df, formula):
    fc = pd.factorize(df["ticker"])[0]; dc = pd.factorize(df["date_str"])[0]
    m = smf.ols(formula, data=df).fit(cov_type="cluster",
        cov_kwds={"groups": np.column_stack([fc, dc])})
    return m

# ---------------- H1: baseline with augmented inference ----------------
m1 = tw(ctrl, "ret_fwd1 ~ sent + ret_lag1 + vol_21 + mkt_ew")
beta_hat = float(m1.params["sent"]); se_hat = float(m1.bse["sent"]); t_hat = float(m1.tvalues["sent"])

# wild cluster bootstrap (Rademacher, day-level), null-imposed on sent
dcodes = pd.factorize(ctrl["date_str"])[0]
X = np.column_stack([np.ones(len(ctrl)), ctrl["sent"], ctrl["ret_lag1"],
                     ctrl["vol_21"], ctrl["mkt_ew"]])
y = ctrl["ret_fwd1"].values
b_ols = np.linalg.solve(X.T @ X, X.T @ y)
resid = y - X @ b_ols
b_null = b_ols.copy(); b_null[1] = 0.0          # impose H0: beta_sent = 0
yfit_null = X @ b_null
unique_days = np.unique(dcodes)
XtXi = np.linalg.inv(X.T @ X)
t_boot = []
for b in range(1999):
    w = rng.choice([-1.0, 1.0], size=len(unique_days))
    wmap = dict(zip(unique_days, w))
    wi = np.array([wmap[c] for c in dcodes])
    yb = yfit_null + wi * resid
    bb = np.linalg.solve(X.T @ X, X.T @ yb)
    ub = yb - X @ bb
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in unique_days:
        idx = dcodes == g
        s = X[idx].T @ ub[idx]
        meat += np.outer(s, s)
    Vb = XtXi @ meat @ XtXi
    t_boot.append(bb[1] / np.sqrt(Vb[1, 1]))
t_boot = np.array(t_boot)
p_wild = 2.0 * min((t_boot >= t_hat).mean(), (t_boot <= t_hat).mean())
p_wild = min(p_wild, 1.0)
R["h1_baseline"] = {
    "spec": "ret_fwd1 ~ sent + ret_lag1 + vol_21 + mkt_ew (two-way cluster)",
    "coef": beta_hat, "se": se_hat, "t": t_hat, "p": float(m1.pvalues["sent"]),
    "n": int(m1.nobs),
    "wild_cluster_bootstrap_p": float(p_wild), "wild_boot_B": 1999,
    "wild_boot_tq": [float(np.percentile(t_boot, q)) for q in (2.5, 50, 97.5)],
}
# with same-day return control (echo-adjusted)
m1c = tw(ctrl, "ret_fwd1 ~ sent + ret + ret_lag1 + vol_21 + mkt_ew")
R["h1_baseline"]["plus_sameday_ctrl"] = {
    "coef": float(m1c.params["sent"]), "t": float(m1c.tvalues["sent"]),
    "p": float(m1c.pvalues["sent"]), "n": int(m1c.nobs)}
print(f"\nH1: beta={beta_hat:.4f} t={t_hat:.2f} p={m1.pvalues['sent']:.4f} "
      f"| wild-bootstrap p={p_wild:.4f} | +same-day t={m1c.tvalues['sent']:.2f}")

# ---------------- H2 (prediction layer): named vs anon vs LM coefficients + difference tests ----------------
ma = tw(ctrl, "ret_fwd1 ~ sent_anon + ret_lag1 + vol_21 + mkt_ew")
mlm = tw(ctrl, "ret_fwd1 ~ lm_tone + ret_lag1 + vol_21 + mkt_ew")
R["h2_prediction"] = {
    "named": {"coef": beta_hat, "t": t_hat, "n": int(m1.nobs)},
    "anon": {"coef": float(ma.params["sent_anon"]), "t": float(ma.tvalues["sent_anon"]), "n": int(ma.nobs)},
    "lm_dict": {"coef": float(mlm.params["lm_tone"]), "t": float(mlm.tvalues["lm_tone"]), "n": int(mlm.nobs)},
}

# cluster bootstrap (resample day clusters) difference tests
def fit_beta_sent(df, col="sent"):
    Xl = np.column_stack([np.ones(len(df)), df[col], df["ret_lag1"], df["vol_21"], df["mkt_ew"]])
    yl = df["ret_fwd1"].values
    try:
        return np.linalg.solve(Xl.T @ Xl, Xl.T @ yl)[1]
    except np.linalg.LinAlgError:
        return np.nan
day_keys = ctrl["date_str"].values
uniq = np.unique(day_keys)
diffs_na, diffs_nl = [], []
for b in range(999):
    picked = rng.choice(uniq, size=len(uniq), replace=True)
    parts = [ctrl[day_keys == d] for d in picked]
    dfb = pd.concat([part.assign(date_str=f"{d}__{i}") for i, (d, part) in enumerate(zip(picked, parts))])
    bn = fit_beta_sent(dfb, "sent")
    ba = fit_beta_sent(dfb, "sent_anon")
    bl = fit_beta_sent(dfb, "lm_tone")
    diffs_na.append(bn - ba)
    diffs_nl.append(bn - bl)
diffs_na = np.array(diffs_na); diffs_nl = np.array(diffs_nl)
obs_diff_na = beta_hat - float(ma.params["sent_anon"])
obs_diff_nl = beta_hat - float(mlm.params["lm_tone"])
ci_na = np.percentile(diffs_na, [2.5, 97.5])
ci_nl = np.percentile(diffs_nl, [2.5, 97.5])
p_na = 2 * min((diffs_na <= 0).mean(), (diffs_na >= 0).mean())
p_nl = 2 * min((diffs_nl <= 0).mean(), (diffs_nl >= 0).mean())
R["h2_prediction"]["difference_tests"] = {
    "named_minus_anon": {"obs": obs_diff_na, "boot_ci95": [float(ci_na[0]), float(ci_na[1])],
                          "boot_p": float(p_na), "B": 999},
    "named_minus_lm": {"obs": obs_diff_nl, "boot_ci95": [float(ci_nl[0]), float(ci_nl[1])],
                        "boot_p": float(p_nl), "B": 999},
}
print(f"H2 prediction: anon t={ma.tvalues['sent_anon']:.2f}, lm t={mlm.tvalues['lm_tone']:.2f}")
print(f"  diff named-anon: {obs_diff_na:.4f} CI[{ci_na[0]:.4f},{ci_na[1]:.4f}] p={p_na:.3f}")
print(f"  diff named-lm:   {obs_diff_nl:.4f} CI[{ci_nl[0]:.4f},{ci_nl[1]:.4f}] p={p_nl:.3f}")

# ---------------- H4: price-language echo split ----------------
R["h4_echo"] = {}
pr_mask = ctrl["priced_any"].astype(bool)
for label in ("priced_any", "clean"):
    sub = ctrl[pr_mask] if label == "priced_any" else ctrl[~pr_mask]
    if len(sub) < 30:
        continue
    mm = tw(sub, "ret_fwd1 ~ sent + ret + ret_lag1 + vol_21 + mkt_ew")
    R["h4_echo"][label] = {"n": int(mm.nobs), "coef": float(mm.params["sent"]),
                            "t": float(mm.tvalues["sent"])}
# same-day regression (echo diagnostic)
msd = tw(ctrl, "ret ~ sent + ret_lag1")
R["h4_echo"]["same_day_named"] = {"coef": float(msd.params["sent"]), "t": float(msd.tvalues["sent"])}
msd_a = tw(ctrl, "ret ~ sent_anon + ret_lag1")
R["h4_echo"]["same_day_anon"] = {"coef": float(msd_a.params["sent_anon"]),
                                  "t": float(msd_a.tvalues["sent_anon"])}
R["h4_echo"]["priced_headline_frac"] = float(adf["priced"].mean())
print(f"\nH4 echo: priced {R['h4_echo']['priced_headline_frac']:.3f} of articles; "
      f"same-day t named={msd.tvalues['sent']:.2f} vs anon={msd_a.tvalues['sent_anon']:.2f}")

# ---------------- H5: coverage selection ----------------
# v4 inference upgrade (audit E6): the 2,664 firm-day observations are
# double-indexed -- the same firm repeats across days, and firms share the same
# trading day (common market shocks). The pooled Welch t-test of the v2 draft
# ignored both sources of dependence. Main specification: firm and day fixed
# effects with two-way clustered SE (absorbs firm means and same-day market
# shocks). Robustness: firm FE with day-clustered SE, and a day-cluster
# bootstrap of the mean gap. The Welch statistic is retained as a descriptive
# cross-check only.
cov = p.dropna(subset=["ret"]).copy()
cov["has_news"] = cov["sent"].notna().astype(int)
a1 = cov.loc[cov["has_news"] == 1, "ret"].abs(); a0 = cov.loc[cov["has_news"] == 0, "ret"].abs()
ttsel = stats.ttest_ind(a1, a0, equal_var=False)
firm_n = cov.groupby("ticker")["has_news"].sum()
firm_vol = cov.groupby("ticker")["ret"].std()

covf = cov.assign(abs_ret=cov["ret"].abs())
fcf = pd.factorize(covf["ticker"])[0]; dcf = pd.factorize(covf["date_str"])[0]
m_fe2 = smf.ols("abs_ret ~ has_news + C(ticker) + C(date_str)", data=covf).fit(
    cov_type="cluster", cov_kwds={"groups": np.column_stack([fcf, dcf])})
m_fe1 = smf.ols("abs_ret ~ has_news + C(ticker)", data=covf).fit(
    cov_type="cluster", cov_kwds={"groups": dcf})

# day-cluster bootstrap of the mean |ret| gap (B=9,999; at B=999 the p-value
# hit the resolution floor in test runs). Vectorized: resampling days with
# multiplicity is equivalent to weighting each day's (sum, count) contributions.
dks_h5 = covf["date_str"].values
uq_h5 = np.unique(dks_h5)
abs_ret_v = covf["abs_ret"].values
hn_v = covf["has_news"].values
n_days_h5 = len(uq_h5)
s1_d = np.array([abs_ret_v[(dks_h5 == d) & (hn_v == 1)].sum() for d in uq_h5])
n1_d = np.array([((dks_h5 == d) & (hn_v == 1)).sum() for d in uq_h5])
s0_d = np.array([abs_ret_v[(dks_h5 == d) & (hn_v == 0)].sum() for d in uq_h5])
n0_d = np.array([((dks_h5 == d) & (hn_v == 0)).sum() for d in uq_h5])
boot_gaps = np.empty(9999)
for b in range(9999):
    cnt = np.bincount(rng.integers(0, n_days_h5, size=n_days_h5), minlength=n_days_h5)
    b1 = (cnt * s1_d).sum() / (cnt * n1_d).sum()
    b0 = (cnt * s0_d).sum() / (cnt * n0_d).sum()
    boot_gaps[b] = b1 - b0
p_boot_h5 = 2 * min((boot_gaps <= 0).mean(), (boot_gaps >= 0).mean())
p_boot_h5 = max(p_boot_h5, 2.0 / (len(boot_gaps) + 1.0))  # resolution floor

R["h5_selection"] = {
    "n_panel_firmdays": int(len(covf)),
    "mean_abs_ret_news_bps": float(a1.mean() * 1e4),
    "mean_abs_ret_nonews_bps": float(a0.mean() * 1e4),
    "welch_t_descriptive": float(ttsel.statistic), "welch_p_descriptive": float(ttsel.pvalue),
    "main_test": "firm+day FE, two-way clustered",
    "fe2_t": float(m_fe2.tvalues["has_news"]), "fe2_p": float(m_fe2.pvalues["has_news"]),
    "firmFE_daycluster_t": float(m_fe1.tvalues["has_news"]),
    "firmFE_daycluster_p": float(m_fe1.pvalues["has_news"]),
    "daycluster_boot_p": float(p_boot_h5),
    "daycluster_boot_ci95_bps": [float(np.percentile(boot_gaps, 2.5) * 1e4),
                                 float(np.percentile(boot_gaps, 97.5) * 1e4)],
    "daycluster_boot_B": int(len(boot_gaps)),
    "corr_firm_newscount_vol": float(np.corrcoef(firm_n, firm_vol)[0, 1]),
}
print(f"H5 selection: |ret| {a1.mean()*1e4:.0f} vs {a0.mean()*1e4:.0f} bps; "
      f"FE2 t={m_fe2.tvalues['has_news']:.2f} (p={m_fe2.pvalues['has_news']:.4f}); "
      f"firmFE/daycl t={m_fe1.tvalues['has_news']:.2f}; boot p={p_boot_h5:.4f}")

# ---------------- heterogeneity via INTERACTIONS (formal difference tests) ----------------
ctrl2 = ctrl.copy()
med_dv = ctrl2.groupby("ticker")["dollar_vol"].transform("mean").median()
ctrl2["big"] = (ctrl2.groupby("ticker")["dollar_vol"].transform("mean") >= med_dv).astype(int)
ctrl2["multi"] = (ctrl2["n_news"] > 1).astype(int)
med_vol = ctrl2["mkt_vol"] if "mkt_vol" in ctrl2 else None
vold = panel.groupby("date_str")["vol_21"].mean().rename("mkt_vol").reset_index()
ctrl2 = ctrl2.merge(vold, on="date_str", how="left")
ctrl2["hivol"] = (ctrl2["mkt_vol"] >= ctrl2["mkt_vol"].median()).astype(int)
inter = {}
for name, mod in [("size", "big"), ("news", "multi"), ("vol", "hivol")]:
    mm = tw(ctrl2, f"ret_fwd1 ~ sent + sent:{mod} + {mod} + ret + ret_lag1 + vol_21 + mkt_ew")
    inter[name] = {"interaction_t": float(mm.tvalues.get(f"sent:{mod}", np.nan)),
                   "interaction_coef": float(mm.params.get(f"sent:{mod}", np.nan)),
                   "p": float(mm.pvalues.get(f"sent:{mod}", np.nan))}
R["heterogeneity_interactions"] = inter
print(f"\nHeterogeneity interaction t: size={inter['size']['interaction_t']:.2f}, "
      f"news={inter['news']['interaction_t']:.2f}, vol={inter['vol']['interaction_t']:.2f}")

# ---------------- BH multiple-testing correction over declared family ----------------
family = {
    "H1 named fwd1": R["h1_baseline"]["p"],
    "H2 named-vs-anon level shift": R["h2_measurement"]["shift_p"],
    "H2 named-vs-anon predictive diff": R["h2_prediction"]["difference_tests"]["named_minus_anon"]["boot_p"],
    "H2 named-vs-lm predictive diff": R["h2_prediction"]["difference_tests"]["named_minus_lm"]["boot_p"],
    "H3 ICC>0.5 (one-sided F)" : None,  # filled below
    "H4 priced-vs-clean difference": None,
    "H5 coverage selection": R["h5_selection"]["fe2_p"],
}
# H3: F-test style proxy for ICC significance -> use 95% CI via bootstrap of ICC
icc_boots = []
X4v = X4.values
for b in range(499):
    idx = rng.choice(len(X4v), size=len(X4v), replace=True)
    Xb = X4v[idx]
    rm = Xb.mean(axis=1); gm = Xb.mean()
    msb = (k * ((rm - gm) ** 2).sum()) / (len(Xb) - 1)
    msw = (Xb.var(axis=1, ddof=1) * 3).sum() / (len(Xb) * 3)
    icc_boots.append((msb - msw) / (msb + 3 * msw))
icc_boots = np.array(icc_boots)
R["h3_stability"]["icc_boot_ci95"] = [float(np.percentile(icc_boots, 2.5)),
                                       float(np.percentile(icc_boots, 97.5))]
family["H3 ICC>0.5 (one-sided)"] = float((icc_boots <= 0.5).mean())

# H4: difference between priced and clean coefficients via day-cluster bootstrap
# v4 (audit E10): B raised from 499 to 9,999 to stabilize the p-value (the v2
# value p=0.077 was seed-sensitive; a fresh seed gave 0.099). The bootstrap
# design matrix is ALSO aligned with the point-estimate specification: the v2
# code bootstrapped the no-same-day-control spec while the point estimates
# include the same-day return -- an inconsistency found in the P0 audit.
Xc_h4 = np.column_stack([np.ones(len(ctrl)), ctrl["sent"], ctrl["ret"],
                         ctrl["ret_lag1"], ctrl["vol_21"], ctrl["mkt_ew"]])
yc_h4 = ctrl["ret_fwd1"].values
priced_v = ctrl["priced_any"].values.astype(bool)
day_keys_c = ctrl["date_str"].values
uniq_c = np.unique(day_keys_c)
day_idx_c = [np.where(day_keys_c == d)[0] for d in uniq_c]
n_days_c = len(uniq_c)
diffs_pc = []
for b in range(9999):
    picks = rng.integers(0, n_days_c, size=n_days_c)
    idx = np.concatenate([day_idx_c[k] for k in picks])
    pm = priced_v[idx]
    i_pr, i_cl = idx[pm], idx[~pm]
    if len(i_pr) < 25 or len(i_cl) < 25:
        continue
    Xp, yp = Xc_h4[i_pr], yc_h4[i_pr]
    Xl_, yl_ = Xc_h4[i_cl], yc_h4[i_cl]
    try:
        bp = np.linalg.solve(Xp.T @ Xp, Xp.T @ yp)[1]
        bc = np.linalg.solve(Xl_.T @ Xl_, Xl_.T @ yl_)[1]
    except np.linalg.LinAlgError:
        continue
    diffs_pc.append(bp - bc)
diffs_pc = np.array(diffs_pc)
obs_pc = R["h4_echo"]["priced_any"]["coef"] - R["h4_echo"]["clean"]["coef"]
p_pc = 2 * min((diffs_pc <= 0).mean(), (diffs_pc >= 0).mean())
family["H4 priced-vs-clean difference"] = float(p_pc)
R["h4_echo"]["priced_minus_clean_boot"] = {
    "obs": float(obs_pc), "boot_ci95": [float(np.percentile(diffs_pc, 2.5)),
                                         float(np.percentile(diffs_pc, 97.5))],
    "boot_p": float(p_pc), "B": len(diffs_pc)}

# BH procedure
fam = {k: v for k, v in family.items() if v is not None}
keys = list(fam.keys()); pvals = np.array([fam[k] for k in keys])
order = np.argsort(pvals)
m = len(pvals)
adj = np.empty(m)
q_running = 0.0
for rank_i in range(m - 1, -1, -1):
    idx_ = order[rank_i]
    val = pvals[idx_] * m / (rank_i + 1)
    q_running = min(q_running, val) if rank_i < m - 1 else val
    adj[idx_] = q_running
R["bh_multiple_testing"] = {k: {"raw_p": float(fam[k]), "bh_q": float(a)}
                            for k, a in zip(keys, adj)}
print("\nBH-corrected family:")
for k, v in R["bh_multiple_testing"].items():
    print(f"  {k}: raw={v['raw_p']:.4f} BH q={v['bh_q']:.4f}")

json.dump(R, open(f"{DATA}/results_v2.json", "w"), indent=1, default=str)
print("\nsaved data/results_v2.json")
