#!/usr/bin/env python3
"""Session 5 control experiments (pre-registered: audits/P2_preregistration_session5.md).

Conditions (one sitting, 2026-10-19, six-way rotated batch order, glm-4-plus):
  N5  named, default decoding
  A5  anonymized v2 (corrected alias table incl. "Visa", sentence-case smoother,
      forced verification: 0 residual focal identifiers)
  S5  identity swap (seeded derangement, seed 20261019)
  P5  neutral prefix "[Company X]" over the A5 text
  T0a/T0b  named, temperature 0, two rounds

Pre-registered predictions tested here (locked before data collection):
  P1  N5 - A5 ~= -2.8 pts (identity replication, V now anonymized)
  P2  identity vs perturbation: |N5 - S5| vs repeat-noise floor; S5 placement
  P3  P5 - A5 ~= 0 (prefix neutrality)
  P4  T0a == T0b bitwise? (decoding determinism)
  P5  T0 vs N5 level (two-sided)

Inference: headline-level paired contrasts; batch-call-clustered (14 clusters)
as conservative default (the 25 scores of one API response share a mood);
day-cluster bootstrap for prediction-layer differences. Seed 20261019.

Writes: data/results_s5.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
rng = np.random.default_rng(20261019)
B = 999
BATCH = 25

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]
tick = {a["url"]: a["ticker"] for a in inwin}

def load(name):
    d = json.load(open(f"{DATA}/{name}"))
    return {u: d[u]["sentiment"] for u in url_order if u in d}

N5 = load("llm_scores_s5_named.json")
A5 = load("llm_scores_s5_anonv2.json")
S5 = load("llm_scores_s5_swap.json")
P5 = load("llm_scores_s5_placeholder.json")
T0a = load("llm_scores_s5_t0a.json")
T0b = load("llm_scores_s5_t0b.json")

complete = [u for u in url_order if u in N5 and u in A5 and u in S5 and u in P5 and u in T0a and u in T0b]
print(f"complete-case headlines: {len(complete)} / {len(url_order)}")
R = {"design": {"session": "2026-10-19, single sitting, six-way rotated batch order",
                "model": "glm-4-plus", "n_complete": len(complete),
                "preregistration": "audits/P2_preregistration_session5.md",
                "seed": 20261019}}
if len(complete) < len(url_order):
    R["incomplete"] = True

H = pd.DataFrame({
    "url": complete,
    "ticker": [tick[u] for u in complete],
    "N5": [N5[u] for u in complete],
    "A5": [A5[u] for u in complete],
    "S5": [S5[u] for u in complete],
    "P5": [P5[u] for u in complete],
    "T0a": [T0a[u] for u in complete],
    "T0b": [T0b[u] for u in complete],
})
H["batch"] = np.arange(len(H)) // BATCH

def clust_t(df, col):
    """Cluster-robust t for the mean of `col`, clustered by batch-call."""
    fc = pd.factorize(df["batch"])[0]
    m = sm.OLS(df[col], np.ones(len(df))).fit(cov_type="cluster",
                                              cov_kwds={"groups": fc})
    return float(m.params[0]), float(m.tvalues[0]), float(m.pvalues[0])

def paired(df, a, b):
    """a-minus-b paired contrast: headline t, Wilcoxon, batch-clustered t."""
    d = df[a] - df[b]
    tt = stats.ttest_rel(df[a], df[b])
    try:
        wil = stats.wilcoxon(df[a], df[b])
        wp = float(wil.pvalue)
    except ValueError:
        wp = float("nan")
    cm, ct, cp = clust_t(df.assign(d=d), "d")
    return {"mean_diff": float(d.mean()), "headline_t": float(tt.statistic),
            "headline_p": float(tt.pvalue), "wilcoxon_p": wp,
            "cluster_t": ct, "cluster_p": cp, "n": int(len(d)),
            "exact_match_rate": float((d == 0).mean()),
            "mean_abs_diff": float(d.abs().mean())}

R["levels"] = {c: float(H[c].mean()) for c in ("N5", "A5", "S5", "P5", "T0a", "T0b")}
print("levels:", {k: round(v, 2) for k, v in R["levels"].items()})

# P1: identity replication (named minus anonymized v2)
R["p1_identity_N5_minus_A5"] = paired(H, "N5", "A5")
# V-excluded variant (pre-registered: V now genuinely anonymized, but keep parity)
nv = H[H["ticker"] != "V"]
R["p1_identity_excl_V"] = paired(nv, "N5", "A5")

# P2: identity swap vs named (natural text, wrong identity)
R["p2_swap_N5_minus_S5"] = paired(H, "N5", "S5")
R["p2_swap_S5_minus_A5"] = paired(H, "S5", "A5")
R["p2_context"] = {
    "corr_N5_S5": float(stats.pearsonr(H["N5"], H["S5"])[0]),
    "corr_N5_A5": float(stats.pearsonr(H["N5"], H["A5"])[0]),
    "corr_S5_A5": float(stats.pearsonr(H["S5"], H["A5"])[0]),
    "repeat_noise_floor_sd_points": 7.2,
}

# P3: prefix neutrality
R["p3_prefix_P5_minus_A5"] = paired(H, "P5", "A5")

# P4: decoding determinism (T0a vs T0b)
ident = (H["T0a"] == H["T0b"])
R["p4_temp0_determinism"] = {
    "exact_identical_rate": float(ident.mean()),
    "n_identical": int(ident.sum()),
    "n": int(len(H)),
    "within_sd_T0": float((H["T0a"] - H["T0b"]).std(ddof=1) / np.sqrt(2)) if ident.mean() < 1 else 0.0,
    "mean_abs_diff_T0ab": float((H["T0a"] - H["T0b"]).abs().mean()),
    "default_repeat_within_sd_reference": 7.2,
}
# P5: temp0 level vs default (two-sided)
R["p5_temp0_vs_default"] = paired(H, "T0a", "N5")

# ---------------- prediction layer ----------------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)

rel = {u: json.load(open(f"{DATA}/llm_scores.json")).get(u, {}).get("relevance") for u in url_order}
rows = [{"ticker": a["ticker"], "date": a["date_iso"], "relevance": rel.get(u), "url": u}
        for a, u in zip(inwin, url_order)]
rdf = pd.DataFrame(rows)
hi = rdf[rdf["relevance"] >= 30].copy()
srcs = {"N5": H.set_index("url")["N5"], "A5": H.set_index("url")["A5"],
        "S5": H.set_index("url")["S5"], "P5": H.set_index("url")["P5"]}
for n, s in srcs.items():
    hi[f"sent_{n}"] = hi["url"].map(s) / 100.0
agg = hi.groupby(["ticker", "date"]).agg({f"sent_{n}": "mean" for n in srcs}).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
pp = panel.merge(agg, on=["ticker", "date"], how="left")
ctrl = pp[pp["sent_N5"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl = ctrl.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
print(f"firm-day regression sample: {len(ctrl)}")

def tw(df, col):
    fc = pd.factorize(df["ticker"])[0]; dc = pd.factorize(df["date_str"])[0]
    m = smf.ols(f"ret_fwd1 ~ {col} + ret_lag1 + vol_21 + mkt_ew", data=df).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([fc, dc])})
    return m

def fit_beta(df, col):
    X = np.column_stack([np.ones(len(df)), df[col], df["ret_lag1"], df["vol_21"], df["mkt_ew"]])
    y = df["ret_fwd1"].values
    return np.linalg.solve(X.T @ X, X.T @ y)[1]

R["prediction"] = {}
for n in ("N5", "A5", "S5", "P5"):
    m = tw(ctrl, f"sent_{n}")
    R["prediction"][n] = {"beta": float(m.params[f"sent_{n}"]),
                          "t": float(m.tvalues[f"sent_{n}"]), "n": int(m.nobs)}

def boot_diff(a, b):
    days = ctrl["date_str"].unique()
    obs = fit_beta(ctrl, a) - fit_beta(ctrl, b)
    st = np.empty(B)
    for i in range(B):
        pick = rng.choice(days, size=len(days), replace=True)
        dfb = pd.concat([ctrl[ctrl["date_str"] == d] for d in pick])
        st[i] = fit_beta(dfb, a) - fit_beta(dfb, b)
    lo, hi_ = np.percentile(st, [2.5, 97.5])
    p = 2 * min((st >= obs).mean(), (st <= obs).mean())
    return {"diff": float(obs), "ci95": [float(lo), float(hi_)], "p": float(p), "B": B}

R["prediction_diffs"] = {
    "N5_minus_A5": boot_diff("sent_N5", "sent_A5"),
    "N5_minus_S5": boot_diff("sent_N5", "sent_S5"),
}

json.dump(R, open(f"{DATA}/results_s5.json", "w"), indent=1)
print(json.dumps({k: v for k, v in R.items() if k not in ("design",)}, indent=1)[:2000])
print(f"wrote {DATA}/results_s5.json")
