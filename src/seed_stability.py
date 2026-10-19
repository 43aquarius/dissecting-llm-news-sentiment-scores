#!/usr/bin/env python3
"""P0-10 acceptance: seed stability of the H4 day-cluster bootstrap difference
(with-same-day-control specification, B=9,999) and the H5 day-cluster gap
bootstrap. Runs three fresh seeds; acceptance: max-min p < 0.01 for H4.
"""
import json
import re
import numpy as np
import pandas as pd

DATA = "/home/z/my-project/data"

PRICE_PAT = re.compile(
    r"\b(rose|rises?|risen|jump(?:s|ed|ing)?|surge[sd]?|surging|soar(?:s|ed|ing)?|"
    r"climb(?:s|ed|ing)?|rall(?:y|ies|ied|ing)|gain(?:s|ed|ing)?|fell|falls?|fallen|"
    r"drop(?:s|ped|ping)?|dropped|plunge[sd]?|plunging|sink[s]?|sank|sinking|slide[sd]?|"
    r"slump(?:s|ed|ing)?|tumbl(?:e|es|ed|ing)|crash(?:es|ed|ing)?|declin(?:e|es|ed|ing)|"
    r"rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)|spike[sd]?|spiking|dip(?:s|ped)?|"
    r"up\s?\d|down\s?\d|\d+%\s?(?:up|down)|hit\s+(?:a\s+)?(?:record|new|52)|"
    r"after\s+(?:earnings|results|guidance|beating|missing))\b", re.I)

arts = json.load(open(f"{DATA}/news_scored.json"))
orig = json.load(open(f"{DATA}/llm_scores.json"))
anon = json.load(open(f"{DATA}/llm_scores_anon.json"))
reps = {k: json.load(open(f"{DATA}/llm_scores_{k}.json")) for k in ("rep1", "rep2", "rep3")}

rows = []
for a in arts:
    if not (a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"):
        continue
    u = a["url"]
    rows.append({"ticker": a["ticker"], "date": a["date_iso"], "url": u,
                 "s_orig": orig.get(u, {}).get("sentiment"),
                 "s_anon": anon.get(u, {}).get("sentiment"),
                 "relevance": orig.get(u, {}).get("relevance"),
                 "priced": bool(PRICE_PAT.search(a["title"]))})
adf = pd.DataFrame(rows)

panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)
hi = adf[adf["relevance"] >= 30]
agg = hi.groupby(["ticker", "date"]).agg(
    sent=("s_orig", "mean"), sent_anon=("s_anon", "mean"),
    priced_any=("priced", "max")).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
p = panel.merge(agg, on=["ticker", "date"], how="left")
p["sent"] = p["sent"] / 100.0
news = p[p["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
ctrl = ctrl.dropna(subset=["sent_anon"])
ctrl["priced_any"] = ctrl["priced_any"].astype(bool)

Xc = np.column_stack([np.ones(len(ctrl)), ctrl["sent"], ctrl["ret"],
                      ctrl["ret_lag1"], ctrl["vol_21"], ctrl["mkt_ew"]])
yc = ctrl["ret_fwd1"].values
priced_v = ctrl["priced_any"].values.astype(bool)
dk = ctrl["date_str"].values
uq = np.unique(dk)
day_idx = [np.where(dk == d)[0] for d in uq]
nd = len(uq)

def h4_boot(seed, B=9999):
    r = np.random.default_rng(seed)
    diffs = []
    for b in range(B):
        picks = r.integers(0, nd, size=nd)
        idx = np.concatenate([day_idx[k] for k in picks])
        pm = priced_v[idx]
        i_pr, i_cl = idx[pm], idx[~pm]
        if len(i_pr) < 25 or len(i_cl) < 25:
            continue
        Xp, yp = Xc[i_pr], yc[i_pr]
        Xl_, yl_ = Xc[i_cl], yc[i_cl]
        try:
            bp = np.linalg.solve(Xp.T @ Xp, Xp.T @ yp)[1]
            bc = np.linalg.solve(Xl_.T @ Xl_, Xl_.T @ yl_)[1]
        except np.linalg.LinAlgError:
            continue
        diffs.append(bp - bc)
    diffs = np.array(diffs)
    pv = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return pv, np.percentile(diffs, [2.5, 97.5]), len(diffs)

print("H4 priced-minus-clean day-cluster bootstrap (with-ret spec, B=9,999):")
ps = []
for seed in (20261016, 20261018, 20261019):
    pv, ci, nb = h4_boot(seed)
    ps.append(pv)
    print(f"  seed {seed}: p={pv:.4f}  CI=[{ci[0]:.4f},{ci[1]:.4f}]  (B_eff={nb})")
print(f"  max-min p = {max(ps)-min(ps):.4f}  -> {'STABLE' if max(ps)-min(ps) < 0.01 else 'UNSTABLE'}")

# H5 gap bootstrap stability (vectorized)
covf = p.dropna(subset=["ret"]).copy()
covf["has_news"] = covf["sent"].notna().astype(int)
covf["abs_ret"] = covf["ret"].abs()
dkh = covf["date_str"].values
uqh = np.unique(dkh)
arv = covf["abs_ret"].values
hnv = covf["has_news"].values
ndh = len(uqh)
s1 = np.array([arv[(dkh == d) & (hnv == 1)].sum() for d in uqh])
n1 = np.array([((dkh == d) & (hnv == 1)).sum() for d in uqh])
s0 = np.array([arv[(dkh == d) & (hnv == 0)].sum() for d in uqh])
n0 = np.array([((dkh == d) & (hnv == 0)).sum() for d in uqh])

def h5_boot(seed, B=9999):
    r = np.random.default_rng(seed)
    gaps = np.empty(B)
    for b in range(B):
        cnt = np.bincount(r.integers(0, ndh, size=ndh), minlength=ndh)
        gaps[b] = (cnt * s1).sum() / (cnt * n1).sum() - (cnt * s0).sum() / (cnt * n0).sum()
    pv = 2 * min((gaps <= 0).mean(), (gaps >= 0).mean())
    return max(pv, 2.0 / (B + 1)), np.percentile(gaps, [2.5, 97.5]) * 1e4

print("\nH5 coverage-selection day-cluster bootstrap (B=9,999):")
for seed in (20261016, 20261018, 20261019):
    pv, ci = h5_boot(seed)
    print(f"  seed {seed}: p={pv:.4f}  CI=[{ci[0]:.1f},{ci[1]:.1f}] bps")
