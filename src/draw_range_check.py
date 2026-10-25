#!/usr/bin/env python3
"""Exact beta/t range over ALL archived named-protocol draws (for consistent text)."""
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = "/home/z/my-project/data"
arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]

def load(path):
    d = json.load(open(path))
    return {u: d[u]["sentiment"] for u in url_order if u in d}

draws = {"v1_original": load(f"{DATA}/llm_scores.json")}
for k in ("rep1", "rep2", "rep3"):
    draws[k] = load(f"{DATA}/llm_scores_{k}.json")
for r in (1, 2, 3, 4):
    draws[f"s3_named_r{r}"] = load(f"{DATA}/llm_scores_s3_named_r{r}.json")
draws["s3_v1comp"] = load(f"{DATA}/llm_scores_s3_v1comp.json")
draws["s4_orig"] = load(f"{DATA}/llm_scores_s4_orig.json")
draws["s4_v1comp"] = load(f"{DATA}/llm_scores_s4_v1comp.json")
draws["s4_shuffle"] = load(f"{DATA}/llm_scores_s4_shuf.json")
draws["s5_named"] = load(f"{DATA}/llm_scores_s5_named.json")
draws["s6_named"] = load(f"{DATA}/llm_scores_s6_named.json")
# session means
draws["s2_repeat_mean"] = {u: np.mean([draws[k][u] for k in ("rep1", "rep2", "rep3")]) for u in url_order}
draws["s3_named_mean"] = {u: np.mean([draws[f"s3_named_r{r}"][u] for r in (1, 2, 3, 4)]) for u in url_order}

panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)
rel = {u: json.load(open(f"{DATA}/llm_scores.json")).get(u, {}).get("relevance") for u in url_order}
rows = [{"ticker": a["ticker"], "date": a["date_iso"], "relevance": rel.get(u), "url": u}
        for a, u in zip(inwin, url_order)]
hi = pd.DataFrame(rows)
hi = hi[hi["relevance"] >= 30].copy()

res = {}
for name, src in draws.items():
    hi2 = hi.assign(sent=hi["url"].map(src) / 100.0)
    agg = hi2.groupby(["ticker", "date"]).agg(sent=("sent", "mean")).reset_index()
    agg["date"] = pd.to_datetime(agg["date"])
    pp = panel.merge(agg, on=["ticker", "date"], how="left")
    ctrl = pp[pp["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"])
    ctrl = ctrl.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
    fc = pd.factorize(ctrl["ticker"])[0]; dc = pd.factorize(ctrl["date_str"])[0]
    m = smf.ols("ret_fwd1 ~ sent + ret_lag1 + vol_21 + mkt_ew", data=ctrl).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([fc, dc])})
    res[name] = (m.params["sent"], m.tvalues["sent"])
    print(f"{name:16s} beta={m.params['sent']:+.4f} t={m.tvalues['sent']:.2f}")

betas = [v[0] for v in res.values()]; ts = [v[1] for v in res.values()]
print(f"\nn_draws={len(res)}  beta range [{min(betas):.4f}, {max(betas):.4f}]  t range [{min(ts):.2f}, {max(ts):.2f}]")
