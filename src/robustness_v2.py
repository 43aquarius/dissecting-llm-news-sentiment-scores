#!/usr/bin/env python3
"""Supplementary robustness numbers for the re-written paper (all computed fresh)."""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = "/home/z/my-project/data"

arts = json.load(open(f"{DATA}/news_scored.json"))
orig = json.load(open(f"{DATA}/llm_scores.json"))
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)

rows = []
for a in arts:
    if not (a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"):
        continue
    s = orig.get(a["url"], {})
    rows.append({"ticker": a["ticker"], "date": a["date_iso"], "url": a["url"],
                 "s": s.get("sentiment"), "rel": s.get("relevance"),
                 "lm": a.get("lm_tone")})
adf = pd.DataFrame(rows)
adf["date"] = pd.to_datetime(adf["date"])

def firmday(hi, colname="sent"):
    g = hi.groupby(["ticker", "date"]).agg(sent=(colname, "mean"), n=("url", "count")).reset_index()
    return g

def regress(agg, label, extra_drop=None):
    p = panel.merge(agg, on=["ticker", "date"], how="inner")
    if extra_drop is not None:
        cnt = p.groupby("date_str")["sent"].transform("count")
        p = p[~(cnt >= extra_drop)]
    p = p.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew"])
    if len(p) < 40:
        print(f"{label}: n={len(p)} too small"); return
    fc = pd.factorize(p["ticker"])[0]; dc = pd.factorize(p["date_str"])[0]
    m = smf.ols("ret_fwd1 ~ sent + ret_lag1 + vol_21 + mkt_ew", data=p).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([fc, dc])})
    print(f"{label}: n={int(m.nobs)} coef={m.params['sent']:.4f} t={m.tvalues['sent']:.2f} p={m.pvalues['sent']:.4f}")

# R1: relevance >= 50
regress(firmday(adf[adf["rel"] >= 50].rename(columns={"s": "sent"})), "R1 relevance>=50")
# R2: unweighted all headlines (no relevance filter)
regress(firmday(adf.rename(columns={"s": "sent"})), "R2 unweighted all")
# R3: drop dense event days (>=5 covered firms)
regress(firmday(adf[adf["rel"] >= 30].rename(columns={"s": "sent"})), "R3 drop event days(>=5)", extra_drop=5)
# R4: anonymized unweighted
anon = json.load(open(f"{DATA}/llm_scores_anon.json"))
adf2 = adf.copy(); adf2["sa"] = adf2["url"].map(lambda u: anon.get(u, {}).get("sentiment"))
p = panel.merge(firmday(adf2.rename(columns={"sa": "sent"})), on=["ticker", "date"], how="inner")
p = p.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"])
fc = pd.factorize(p["ticker"])[0]; dc = pd.factorize(p["date_str"])[0]
m = smf.ols("ret_fwd1 ~ sent + ret + ret_lag1 + vol_21 + mkt_ew", data=p).fit(
    cov_type="cluster", cov_kwds={"groups": np.column_stack([fc, dc])})
print(f"R4 anon unweighted +same-day: n={int(m.nobs)} coef={m.params['sent']:.4f} t={m.tvalues['sent']:.2f}")

# R5: placebo permutation within day (named, core spec) - 1000 draws
agg = firmday(adf[adf["rel"] >= 30].rename(columns={"s": "sent"}))
p = panel.merge(agg, on=["ticker", "date"], how="inner").dropna(
    subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew"])
rng = np.random.default_rng(42)
dc = pd.factorize(p["date_str"])[0]
m0 = smf.ols("ret_fwd1 ~ sent + ret_lag1 + vol_21 + mkt_ew", data=p).fit(
    cov_type="cluster", cov_kwds={"groups": np.column_stack([pd.factorize(p['ticker'])[0], dc])})
obs = m0.params["sent"]
bs = []
for b in range(1000):
    sp = p["sent"].values.copy()
    for d in np.unique(dc):
        idx = dc == d
        sp[idx] = rng.permutation(sp[idx])
    mb = smf.ols("ret_fwd1 ~ sp + ret_lag1 + vol_21 + mkt_ew", data=p.assign(sp=sp)).fit()
    bs.append(mb.params["sp"])
bs = np.array(bs)
print(f"R5 placebo permutation p = {np.mean(np.abs(bs) >= abs(obs)):.3f} (obs {obs:.4f}, placebo sd {bs.std():.4f})")

# R6: quintile spreads under core sample
q = p.dropna(subset=["ret_fwd1"]).copy()
q["quintile"] = pd.qcut(q["sent"].rank(method="first"), 5, labels=False) + 1
means = q.groupby("quintile")["ret_fwd1"].mean() * 1e4
hi = q.loc[q["quintile"] == 5, "ret_fwd1"]; lo = q.loc[q["quintile"] == 1, "ret_fwd1"]
from scipy import stats as st
tt = st.ttest_ind(hi, lo, equal_var=False)
print("R6 quintiles (bps):", {int(k): round(v, 1) for k, v in means.items()})
print(f"   LS spread {means[5]-means[1]:.1f} bps, Welch t={tt.statistic:.2f} p={tt.pvalue:.3f}")

# R7: logit direction (named)
import statsmodels.api as sm
bl = p.dropna(subset=["ret_fwd1"]).copy()
bl["up"] = (bl["ret_fwd1"] > 0).astype(int)
lg = sm.Logit(bl["up"], sm.add_constant(bl[["sent"]])).fit(disp=0)
print(f"R7 logit: coef={lg.params['sent']:.3f} p={lg.pvalues['sent']:.3f} n={int(lg.nobs)}")
