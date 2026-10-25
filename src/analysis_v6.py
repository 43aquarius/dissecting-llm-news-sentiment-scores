#!/usr/bin/env python3
"""Session 6: fictional-name control (pre-registered: audits/P3_preregistration_session6.md).

Conditions (one sitting, 2026-10-25, three-way rotated batch order, glm-4-plus):
  N6  named protocol (anchor)
  A6  anonymized v2 (forced verification, word-boundary + substring tiers)
  F6  fictional firm names (s6_fictional_map.json; natural text, concrete name,
      no real-world prior by construction)

Pre-registered predictions tested here (locked before collection):
  P6a  discriminating cell -- placeholder-rewrite hypothesis: F6-N6 ~= 0 and
       F6-A6 ~= +2..3; identity-removal hypothesis: the opposite assignment.
  P6b  N6-A6 ~= -2 (replication cell; direction and magnitude consistent).
  P6c  prediction layer: N6/A6/F6 coefficients formally equivalent.

Inference: headline-level paired contrasts; batch-call-clustered (14 clusters)
conservative default; level TOST at the pre-fixed 1.25-point margin with EMT
(minimum passing margin) reported margin-free; day-cluster bootstrap for
prediction-layer differences. Seed 20261025.

Writes: data/results_s6.json
"""
import json
import math

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
rng = np.random.default_rng(20261025)
B = 999
BATCH = 25
DELTA_LEVEL = 1.25
T90 = 1.6495  # t_{0.95, infty} approx for headline CI90

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]
tick = {a["url"]: a["ticker"] for a in inwin}

def load(name):
    d = json.load(open(f"{DATA}/{name}"))
    return {u: d[u]["sentiment"] for u in url_order if u in d}

N6 = load("llm_scores_s6_named.json")
A6 = load("llm_scores_s6_anonv2.json")
F6 = load("llm_scores_s6_fictional.json")

complete = [u for u in url_order if u in N6 and u in A6 and u in F6]
print(f"complete-case headlines: {len(complete)} / {len(url_order)}")
R = {"design": {"session": "2026-10-25, single sitting, three-way rotated batch order",
                "model": "glm-4-plus", "n_complete": len(complete),
                "preregistration": "audits/P3_preregistration_session6.md",
                "seed": 20261025, "delta_level_points": DELTA_LEVEL}}
if len(complete) < len(url_order):
    R["incomplete"] = True

H = pd.DataFrame({
    "url": complete,
    "ticker": [tick[u] for u in complete],
    "N6": [N6[u] for u in complete],
    "A6": [A6[u] for u in complete],
    "F6": [F6[u] for u in complete],
})
H["batch"] = np.arange(len(H)) // BATCH

def clust_t(df, col):
    fc = pd.factorize(df["batch"])[0]
    m = sm.OLS(df[col], np.ones(len(df))).fit(cov_type="cluster", cov_kwds={"groups": fc})
    return float(m.params[0]), float(m.tvalues[0]), float(m.pvalues[0])

def level_tost(d):
    """EMT + pass/fail at DELTA_LEVEL under headline and clustered inference."""
    n = len(d)
    dbar = float(d.mean())
    se_hl = float(d.std(ddof=1) / math.sqrt(n))
    lo_hl, hi_hl = dbar - T90 * se_hl, dbar + T90 * se_hl
    emt_hl = max(abs(lo_hl), abs(hi_hl))
    dfc = pd.DataFrame({"d": d, "batch": np.arange(n) // BATCH})
    _, ct, cp = clust_t(dfc, "d")
    # clustered bootstrap CI90
    bs = sorted(set(dfc["batch"]))
    means = []
    for _ in range(B):
        pick = list(rng.choice(bs, size=len(bs), replace=True))
        dd = pd.concat([dfc[dfc["batch"] == b]["d"] for b in pick])
        means.append(float(dd.mean()))
    means = np.sort(np.array(means))
    lo_cl, hi_cl = float(np.percentile(means, 5)), float(np.percentile(means, 95))
    emt_cl = max(abs(lo_cl), abs(hi_cl))
    return {
        "mean_diff": dbar,
        "ci90_headline": [round(lo_hl, 3), round(hi_hl, 3)],
        "EMT_points_headline": round(emt_hl, 3),
        "pass_delta_headline": bool(lo_hl >= -DELTA_LEVEL and hi_hl <= DELTA_LEVEL),
        "ci90_cluster": [round(lo_cl, 3), round(hi_cl, 3)],
        "EMT_points_cluster": round(emt_cl, 3),
        "pass_delta_cluster": bool(lo_cl >= -DELTA_LEVEL and hi_cl <= DELTA_LEVEL),
        "as_pct_of_placeholder_midpoint": round(abs(dbar) / 2.5, 3),
    }

def paired(df, a, b):
    d = df[a] - df[b]
    tt = stats.ttest_rel(df[a], df[b])
    try:
        wp = float(stats.wilcoxon(df[a], df[b]).pvalue)
    except ValueError:
        wp = float("nan")
    cm, ct, cp = clust_t(df.assign(d=d), "d")
    out = {"mean_diff": float(d.mean()), "headline_t": float(tt.statistic),
           "headline_p": float(tt.pvalue), "wilcoxon_p": wp,
           "cluster_t": ct, "cluster_p": cp, "n": int(len(d)),
           "exact_match_rate": float((d == 0).mean()),
           "mean_abs_diff": float(d.abs().mean())}
    out["level_tost"] = level_tost(d)
    return out

R["levels"] = {c: float(H[c].mean()) for c in ("N6", "A6", "F6")}
print("levels:", {k: round(v, 2) for k, v in R["levels"].items()})

# P6a: the discriminating cell
R["p6a_fictional_minus_named"] = paired(H, "F6", "N6")
R["p6a_fictional_minus_anonv2"] = paired(H, "F6", "A6")
R["p6a_context"] = {
    "corr_N6_F6": float(stats.pearsonr(H["N6"], H["F6"])[0]),
    "corr_N6_A6": float(stats.pearsonr(H["N6"], H["A6"])[0]),
    "corr_F6_A6": float(stats.pearsonr(H["F6"], H["A6"])[0]),
    "repeat_noise_floor_sd_points": 7.2,
}

# P6b: replication cell
R["p6b_named_minus_anonv2"] = paired(H, "N6", "A6")

# placement summary vs session-5 anchors (cross-session, descriptive only)
s5 = json.load(open(f"{DATA}/results_s5.json"))
R["cross_session_descriptive"] = {
    "s5_N5_level": s5["levels"]["N5"], "s6_N6_level": R["levels"]["N6"],
    "s5_A5_level": s5["levels"]["A5"], "s6_A6_level": R["levels"]["A6"],
    "note": "cross-session level comparisons are confounded by session/batch drift; within-session contrasts only",
}

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
srcs = {"N6": H.set_index("url")["N6"], "A6": H.set_index("url")["A6"], "F6": H.set_index("url")["F6"]}
for n, s in srcs.items():
    hi[f"sent_{n}"] = hi["url"].map(s) / 100.0
agg = hi.groupby(["ticker", "date"]).agg({f"sent_{n}": "mean" for n in srcs}).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
pp = panel.merge(agg, on=["ticker", "date"], how="left")
ctrl = pp[pp["sent_N6"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl = ctrl.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
print(f"firm-day regression sample: {len(ctrl)}")

def tw(df, col):
    fc = pd.factorize(df["ticker"])[0]
    dc = pd.factorize(df["date_str"])[0]
    m = smf.ols(f"ret_fwd1 ~ {col} + ret_lag1 + vol_21 + mkt_ew", data=df).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([fc, dc])})
    return m

def fit_beta(df, col):
    return float(tw(df, col).params[col])

R["prediction"] = {}
for n in srcs:
    m = tw(ctrl, f"sent_{n}")
    R["prediction"][n] = {"beta": float(m.params[f"sent_{n}"]), "t": float(m.tvalues[f"sent_{n}"]),
                          "n": int(len(ctrl))}

def boot_diff(a, b):
    obs = fit_beta(ctrl, a) - fit_beta(ctrl, b)
    st = []
    days = ctrl["date_str"].unique()
    for _ in range(B):
        pick = rng.choice(days, size=len(days), replace=True)
        dfb = pd.concat([ctrl[ctrl["date_str"] == d] for d in pick])
        st.append(fit_beta(dfb, a) - fit_beta(dfb, b))
    st = np.sort(np.array(st))
    return {"obs": obs, "p": float((np.abs(st) >= abs(obs)).mean()),
            "ci95": [float(np.percentile(st, 2.5)), float(np.percentile(st, 97.5))]}

R["prediction_diffs"] = {
    "N6_minus_A6": boot_diff("sent_N6", "sent_A6"),
    "N6_minus_F6": boot_diff("sent_N6", "sent_F6"),
    "A6_minus_F6": boot_diff("sent_A6", "sent_F6"),
}

with open(f"{DATA}/results_s6.json", "w") as f:
    json.dump(R, f, indent=1)

print("\n=== P6a discriminating cell ===")
print(f"F6-N6: {R['p6a_fictional_minus_named']['mean_diff']:+.3f} "
      f"(t={R['p6a_fictional_minus_named']['headline_t']:.2f}, cl p={R['p6a_fictional_minus_named']['cluster_p']:.3f}) "
      f"EMT_hl={R['p6a_fictional_minus_named']['level_tost']['EMT_points_headline']}")
print(f"F6-A6: {R['p6a_fictional_minus_anonv2']['mean_diff']:+.3f} "
      f"(t={R['p6a_fictional_minus_anonv2']['headline_t']:.2f}, cl p={R['p6a_fictional_minus_anonv2']['cluster_p']:.3f}) "
      f"EMT_hl={R['p6a_fictional_minus_anonv2']['level_tost']['EMT_points_headline']}")
print(f"N6-A6: {R['p6b_named_minus_anonv2']['mean_diff']:+.3f} "
      f"(t={R['p6b_named_minus_anonv2']['headline_t']:.2f}, cl p={R['p6b_named_minus_anonv2']['cluster_p']:.3f})")
print("\n=== prediction layer ===")
for n, r in R["prediction"].items():
    print(f"beta_{n}: {r['beta']:.4f} (t={r['t']:.2f}, n={r['n']})")
for k, r in R["prediction_diffs"].items():
    print(f"{k}: diff={r['obs']:+.4f} p={r['p']:.3f} ci95=[{r['ci95'][0]:+.4f},{r['ci95'][1]:+.4f}]")
print("saved -> data/results_s6.json")
