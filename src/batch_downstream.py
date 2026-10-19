#!/usr/bin/env python3
"""L2-C: Does the batch-composition effect propagate to DOWNSTREAM uses?

Question a reviewer will ask: levels move by +3.6 points under re-batching, but
if slopes and ranks do not move, what is the harm? This script quantifies which
downstream uses of the score are contaminated by batch composition and which are
robust, using ONLY archived draws (no new data collection; staged addition,
reported outside the declared family).

Sources (all named protocol, identical 341 in-window headlines):
  s1_v1      session 1 (Oct 15), 542-article batch composition
  s2_repm    session 2 (Oct 16), mean of 3 repeats, 341-only composition
  s3_named4  session 3 (Oct 18), mean of 4 interleaved rounds, 341-only comp
  s3_v1c     session 3, 542-article composition (composition control pass)
  s4_orig    session 4 (Oct 18, later sitting), 341-only composition
  s4_v1c     session 4, 542-article composition (run FIRST, order inverted)
  s4_shuf    session 4, seeded random re-batch of the 341

Downstream uses tested:
  (1) predictive slope  beta of the H1 next-day regression per source + day-cluster
      bootstrap differences for composition/re-batch contrasts
  (2) portfolio sort    Q5-Q1 spread per source
  (3) cross-sectional rank  Spearman rho of firm-day sentiment across sources
  (4) threshold rules   share of firm-days crossing fixed score thresholds
  (5) time series       daily-mean series: shift, correlation, sign-flip rate
                        of day-over-day changes across compositions

Writes: data/results_batch_downstream.json
"""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
rng = np.random.default_rng(20261019)
B = 999

arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]
tick = {a["url"]: a["ticker"] for a in inwin}

def load(path):
    d = json.load(open(path))
    return {u: d[u]["sentiment"] for u in url_order if u in d}

v1 = load(f"{DATA}/llm_scores.json")
s2r = {k: load(f"{DATA}/llm_scores_{k}.json") for k in ("rep1", "rep2", "rep3")}
s3n = {r: load(f"{DATA}/llm_scores_s3_named_r{r}.json") for r in (1, 2, 3, 4)}
s4o = load(f"{DATA}/llm_scores_s4_orig.json")
s4v = load(f"{DATA}/llm_scores_s4_v1comp.json")
s4s = load(f"{DATA}/llm_scores_s4_shuf.json")

S = {
    "s1_v1":     v1,
    "s2_repm":   {u: float(np.mean([s2r[k][u] for k in ("rep1", "rep2", "rep3")])) for u in url_order},
    "s3_named4": {u: float(np.mean([s3n[r][u] for r in (1, 2, 3, 4)])) for u in url_order},
    "s3_v1c":    load(f"{DATA}/llm_scores_s3_v1comp.json"),
    "s4_orig":   s4o, "s4_v1c": s4v, "s4_shuf": s4s,
}

# ---------------- panel + firm-day aggregation (session-1 relevance filter) --------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)

rel = {u: json.load(open(f"{DATA}/llm_scores.json")).get(u, {}).get("relevance") for u in url_order}
rows = [{"ticker": a["ticker"], "date": a["date_iso"], "relevance": rel.get(u), "url": u}
        for a, u in zip(inwin, url_order)]
rdf = pd.DataFrame(rows)
hi = rdf[rdf["relevance"] >= 30].copy()
for name, src in S.items():
    hi[f"sent_{name}"] = hi["url"].map(src) / 100.0
agg = hi.groupby(["ticker", "date"]).agg(
    {f"sent_{n}": "mean" for n in S}).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
pp = panel.merge(agg, on=["ticker", "date"], how="left")

ctrl = pp[pp["sent_s3_named4"].notna()].drop_duplicates(subset=["ticker", "date_str"])
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

# (1) predictive slope per source
slopes = {}
for n in S:
    col = f"sent_{n}"
    m = tw(ctrl, col)
    slopes[n] = {"beta": float(m.params[col]), "t": float(m.tvalues[col]),
                 "p": float(m.pvalues[col]), "n": int(m.nobs)}
    print(f"beta[{n:9s}] = {m.params[col]:+.4f} (t={m.tvalues[col]:.2f})")

# day-cluster bootstrap differences
def boot_diff(col_a, col_b):
    days = ctrl["date_str"].unique()
    obs = fit_beta(ctrl, col_a) - fit_beta(ctrl, col_b)
    stats_ = np.empty(B)
    for i in range(B):
        pick = rng.choice(days, size=len(days), replace=True)
        parts = [ctrl[ctrl["date_str"] == d] for d in pick]
        dfb = pd.concat(parts)
        stats_[i] = fit_beta(dfb, col_a) - fit_beta(dfb, col_b)
    lo, hi_ = np.percentile(stats_, [2.5, 97.5])
    p = 2 * min((stats_ >= obs).mean(), (stats_ <= obs).mean())
    return {"diff": float(obs), "ci95": [float(lo), float(hi_)], "p": float(p)}

diffs = {}
for tag, a, b in [
    ("composition_s3_542minus341", "sent_s3_v1c", "sent_s3_named4"),
    ("composition_s4_542minus341", "sent_s4_v1c", "sent_s4_orig"),
    ("rebatch_s4_shufminusorig",   "sent_s4_shuf", "sent_s4_orig"),
    ("crosssession_s1minus_s2",    "sent_s1_v1",   "sent_s2_repm"),
]:
    diffs[tag] = boot_diff(a, b)
    print(f"diff[{tag}] = {diffs[tag]['diff']:+.5f} p={diffs[tag]['p']:.3f}")

# (2) quintile spreads per source
quint = {}
for n in S:
    col = f"sent_{n}"
    d = ctrl.dropna(subset=[col]).copy()
    d["q"] = pd.qcut(d[col], 5, labels=False, duplicates="drop")
    means = d.groupby("q")["ret_fwd1"].mean() * 1e4
    spread = means.iloc[-1] - means.iloc[0]
    top = d[d["q"] == d["q"].max()]["ret_fwd1"]; bot = d[d["q"] == d["q"].min()]["ret_fwd1"]
    w = stats.ttest_ind(top, bot, equal_var=False)
    quint[n] = {"q_means_bps": [float(x) for x in means], "spread_bps": float(spread),
                "welch_t": float(w.statistic), "p": float(w.pvalue)}
    print(f"Q5-Q1[{n:9s}] = {spread:+7.1f} bps (Welch t={w.statistic:.2f})")

# (3) cross-sectional rank stability (firm-day level)
ranks = {}
pairs = [("s3_v1c", "s3_named4"), ("s4_v1c", "s4_orig"), ("s4_shuf", "s4_orig"),
         ("s1_v1", "s2_repm"), ("s3_named4", "s4_orig")]
for a, b in pairs:
    d = ctrl.dropna(subset=[f"sent_{a}", f"sent_{b}"])
    r = stats.spearmanr(d[f"sent_{a}"], d[f"sent_{b}"])
    lv = float((d[f"sent_{a}"] - d[f"sent_{b}"]).mean())
    ranks[f"{a}_vs_{b}"] = {"spearman": float(r.statistic), "n": int(len(d)),
                            "level_shift_points": lv * 100}
    print(f"rho[{a} vs {b}] = {r.statistic:.3f} (level shift {lv*100:+.2f} pts)")

# (4) threshold rules: share of firm-days crossing fixed thresholds
thr = {}
for n in S:
    col = f"sent_{n}"
    d = ctrl.dropna(subset=[col])[col]
    thr[n] = {"share_ge_pos50": float((d >= 0.5).mean()), "n_ge_pos50": int((d >= 0.5).sum()),
              "share_le_neg50": float((d <= -0.5).mean()), "n_le_neg50": int((d <= -0.5).sum()),
              "share_ge_pos25": float((d >= 0.25).mean()), "n_ge_pos25": int((d >= 0.25).sum())}
    print(f"threshold[{n:9s}]: >=+50: {thr[n]['n_ge_pos50']:3d} firm-days ({thr[n]['share_ge_pos50']*100:4.1f}%)  <=-50: {thr[n]['n_le_neg50']:3d}")

# headline-level thresholds too
hl_thr = {}
for n in S:
    v = np.array([S[n][u] for u in url_order], dtype=float)
    hl_thr[n] = {"share_ge_pos50": float((v >= 50).mean()), "share_le_neg50": float((v <= -50).mean())}

# (5) daily time-series: daily mean sentiment per source
ts = {}
for n in S:
    col = f"sent_{n}"
    d = ctrl.dropna(subset=[col])
    ts[n] = d.groupby("date_str")[col].mean()
ts_df = pd.DataFrame(ts).dropna()
ts_out = {}
for a, b in [("s3_v1c", "s3_named4"), ("s4_v1c", "s4_orig"), ("s4_shuf", "s4_orig")]:
    common = ts_df.dropna(subset=[a, b])
    corr = float(np.corrcoef(common[a], common[b])[0, 1])
    shift = float((common[a] - common[b]).mean()) * 100
    dchg_a = np.sign(common[a].diff().dropna())
    dchg_b = np.sign(common[b].diff().dropna())
    flip = float((dchg_a != dchg_b).mean())
    ts_out[f"{a}_vs_{b}"] = {"corr_daily_mean": corr, "mean_shift_points": shift,
                             "n_days": int(len(common)),
                             "sign_flip_rate_dayoverday": flip}
    print(f"daily-mean[{a} vs {b}]: corr={corr:.3f}, shift={shift:+.2f} pts, "
          f"day-over-day sign flips {flip*100:.0f}%")

R = {"design": "downstream consequences of batch composition, archived draws only; "
               "staged addition outside the declared family; seed 20261019",
     "n_firmdays": int(len(ctrl)),
     "slopes": slopes, "slope_differences": diffs,
     "quintile_spreads": quint, "rank_stability": ranks,
     "thresholds_firmday": thr, "thresholds_headline": hl_thr,
     "daily_timeseries": ts_out}
json.dump(R, open(f"{DATA}/results_batch_downstream.json", "w"), indent=1)
print(f"\nwrote {DATA}/results_batch_downstream.json")
