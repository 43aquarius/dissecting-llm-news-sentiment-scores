#!/usr/bin/env python3
"""AUDIT (substantive): endogeneity and selection in the news-sentiment panel.

A. How many headlines contain RETROSPECTIVE PRICE LANGUAGE (already-realized moves)?
B. Is news coverage selected on return outcomes? (news vs no-news firm-days)
C. Does sentiment predict next-day returns AFTER controlling for same-day return?
D. Placebo: shuffled sentiment within day, 1000 draws.
E. Does sentiment merely echo same-day price movement? (sent on ret regression)
"""
import json
import re
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
pd.set_option("display.width", 200)

# ---------- A. retrospective price language in headlines ----------
arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
print(f"A. HEADLINE CONTENT AUDIT: {len(inwin)} in-window scored articles")

PRICE_PAT = re.compile(
    r"\b(rose|rises?|risen|jump(?:s|ed|ing)?|surge[sd]?|surging|soar(?:s|ed|ing)?|"
    r"climb(?:s|ed|ing)?|rall(?:y|ies|ied|ing)|gain(?:s|ed|ing)?|fell|falls?|fallen|"
    r"drop(?:s|ped|ping)?|dropped|plunge[sd]?|plunging|sink[s]?|sank|sinking|slide[sd]?|"
    r"slump(?:s|ed|ing)?|tumbl(?:e|es|ed|ing)|crash(?:es|ed|ing)?|declin(?:e|es|ed|ing)|"
    r"rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)|spike[sd]?|spiking|dip(?:s|ped)?|"
    r"up\s?\d|down\s?\d|\d+%\s?(?:up|down)|hit\s+(?:a\s+)?(?:record|new|52)|"
    r"after\s+(?:earnings|results|guidance|beating|missing))\b", re.I)

n_price = 0
examples = []
for a in inwin:
    if PRICE_PAT.search(a["title"]):
        n_price += 1
        if len(examples) < 8:
            examples.append(f"  [{a['ticker']} {a['date_iso']}] s={a.get('lm_tone')}: {a['title'][:95]}")
print(f"  headlines with retrospective price language: {n_price} of {len(inwin)} ({100*n_price/len(inwin):.1f}%)")
for e in examples: print(e)

# also with LLM scores attached
sc = json.load(open(f"{DATA}/llm_scores.json"))
for a in inwin:
    s = sc.get(a["url"], {})
    a["llm_s"] = s.get("sentiment")
priced = [a for a in inwin if PRICE_PAT.search(a["title"])]
unpriced = [a for a in inwin if not PRICE_PAT.search(a["title"])]
print(f"  mean LLM sentiment: price-language {np.mean([a['llm_s'] for a in priced if a['llm_s'] is not None]):.1f} "
      f"vs clean {np.mean([a['llm_s'] for a in unpriced if a['llm_s'] is not None]):.1f}")

# ---------- B. coverage selection ----------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)
panel["sent_rel"] = panel["llm_sent_rel"] / 100.0
panel["has_news_f"] = panel["sent_rel"].notna()

cov = panel.dropna(subset=["ret", "ret_fwd1"])
g = cov.groupby("has_news_f")["ret"].agg(["mean", "std", "count"])
print("\nB. COVERAGE SELECTION (same-day return by news status):")
print(g.applymap(lambda v: f"{v:.5f}" if v > 1e-4 else f"{v:.1f}").to_string())
tt = stats.ttest_ind(cov.loc[cov["has_news_f"], "ret"], cov.loc[~cov["has_news_f"], "ret"], equal_var=False)
print(f"  Welch t on |same-day ret|: ", end="")
a1 = cov.loc[cov["has_news_f"], "ret"].abs(); a0 = cov.loc[~cov["has_news_f"], "ret"].abs()
print(f"{stats.ttest_ind(a1, a0, equal_var=False).statistic:.2f} (p={stats.ttest_ind(a1, a0, equal_var=False).pvalue:.4f})")
print(f"  mean |ret| news-days {a1.mean()*1e4:.0f}bps vs no-news {a0.mean()*1e4:.0f}bps")
# firm-level coverage count vs mean return
firm_n = cov.groupby("ticker")["has_news_f"].sum()
firm_ret = cov.groupby("ticker")["ret"].std()
print(f"  corr(firm news count, firm return std) = {np.corrcoef(firm_n, firm_ret)[0,1]:.3f}")

# ---------- C. incremental predictability controlling same-day return ----------
news = panel[panel["sent_rel"].notna()].copy()
news = news.drop_duplicates(subset=["ticker", "date_str"]).sort_values(["ticker", "date"])
ctrl = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
fcode = pd.factorize(ctrl["ticker"])[0]; dcode = pd.factorize(ctrl["date_str"])[0]

def fit(formula, data):
    m = smf.ols(formula, data=data).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([fcode if data is ctrl else pd.factorize(data['ticker'])[0],
                                                                 dcode if data is ctrl else pd.factorize(data['date_str'])[0]])})
    return m

print("\nC. INCREMENTAL PREDICTION (adding same-day ret as control):")
m0 = smf.ols("ret_fwd1 ~ sent_rel + ret_lag1 + vol_21 + mkt_ew", data=ctrl).fit(
    cov_type="cluster", cov_kwds={"groups": np.column_stack([fcode, dcode])})
m1 = smf.ols("ret_fwd1 ~ sent_rel + ret_lag1 + vol_21 + mkt_ew + ret", data=ctrl).fit(
    cov_type="cluster", cov_kwds={"groups": np.column_stack([fcode, dcode])})
m2 = smf.ols("ret_fwd1 ~ sent_rel + ret + ret_overnight", data=ctrl).fit(
    cov_type="cluster", cov_kwds={"groups": np.column_stack([fcode, dcode])})
print(f"  baseline (paper spec):      beta={m0.params['sent_rel']:.4f} t={m0.tvalues['sent_rel']:.2f} p={m0.pvalues['sent_rel']:.4f}")
print(f"  + same-day ret control:     beta={m1.params['sent_rel']:.4f} t={m1.tvalues['sent_rel']:.2f} p={m1.pvalues['sent_rel']:.4f}")
print(f"  + ret & overnight ret:      beta={m2.params['sent_rel']:.4f} t={m2.tvalues['sent_rel']:.2f} p={m2.pvalues['sent_rel']:.4f}")
print(f"  same-day ret coef in m1:    {m1.params['ret']:.4f} t={m1.tvalues['ret']:.2f}")

# ---------- E. sentiment as echo of same-day movement ----------
mE = smf.ols("ret ~ sent_rel + ret_lag1", data=ctrl).fit(
    cov_type="cluster", cov_kwds={"groups": np.column_stack([fcode, dcode])})
print(f"\nE. SENTIMENT ECHOES SAME-DAY PRICE: ret on sent: beta={mE.params['sent_rel']:.4f} t={mE.tvalues['sent_rel']:.2f}")
# price-language subset vs clean subset predictability
# rebuild priced flag properly from news_scored by (ticker,date)
nd = {(a["ticker"], a["date_iso"]): bool(PRICE_PAT.search(a["title"])) for a in inwin}
anypriced = {k for k, v in nd.items() if v}
ctrl2 = ctrl.copy()
ctrl2["priced"] = [((t, d) in anypriced) for t, d in zip(ctrl2["ticker"], ctrl2["date_str"])]
print("\nE2. PREDICTABILITY BY HEADLINE TYPE (firm-day has any price-language headline):")
for label, sub in [("price-language firm-days", ctrl2[ctrl2["priced"]]), ("clean firm-days", ctrl2[~ctrl2["priced"]])]:
    if len(sub) > 30:
        fc = pd.factorize(sub["ticker"])[0]; dc = pd.factorize(sub["date_str"])[0]
        try:
            mm = smf.ols("ret_fwd1 ~ sent_rel + ret_lag1 + vol_21 + mkt_ew + ret", data=sub).fit(
                cov_type="cluster", cov_kwds={"groups": np.column_stack([fc, dc])})
            print(f"  {label}: n={len(sub)} beta={mm.params['sent_rel']:.4f} t={mm.tvalues['sent_rel']:.2f}")
        except Exception as e:
            print(f"  {label}: n={len(sub)} (SE failed: {e})")

# ---------- D. placebo: shuffle sentiment within day ----------
rng = np.random.default_rng(42)
ts = []
for b in range(1000):
    sp = ctrl["sent_rel"].values.copy()
    for d in np.unique(dcode):
        idx = dcode == d
        sp[idx] = rng.permutation(sp[idx])
    dfb = ctrl.assign(sp=sp)
    mb = smf.ols("ret_fwd1 ~ sp + ret_lag1 + vol_21 + mkt_ew", data=dfb).fit()
    ts.append(mb.params["sp"])
ts = np.array(ts)
p_two = np.mean(np.abs(ts) >= abs(m0.params["sent_rel"]))
print(f"\nD. PLACEBO (permute sentiment within day, 1000 draws): mean|t placebo coef| sd={ts.std():.5f}")
print(f"  observed beta {m0.params['sent_rel']:.5f}; placebo 97.5th pct |beta| = {np.percentile(np.abs(ts), 97.5):.5f}")
print(f"  permutation p-value (two-sided) = {p_two:.3f}")
