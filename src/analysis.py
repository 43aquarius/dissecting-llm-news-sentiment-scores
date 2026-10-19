#!/usr/bin/env python3
"""Econometric analysis: LLM sentiment and next-day stock returns.

Design follows Lopez-Lira & Tang (2023) adapted to a short recent sample:
- Baseline panel regressions: next-day (and same-day) returns on LLM sentiment
  with controls, firm/day fixed effects, two-way clustered SEs
- Dictionary comparison: Loughran-McDonald tone on identical headlines
- Direction prediction (logit), decile portfolio sorts, long-short economics
- Daily information coefficient (IC)
- Robustness: horizons, relevance filter, subsamples
- Heterogeneity: size, volatility regime, news intensity
Output: /home/z/my-project/data/results.json + console summary
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
pd.set_option("display.width", 200)


def two_way_cluster_ols(df, formula, firm="ticker", day="date_str"):
    """OLS with two-way (firm & day) clustered standard errors via formula API."""
    fcode, _ = pd.factorize(df[firm])
    dcode, _ = pd.factorize(df[day])
    groups = np.column_stack([fcode, dcode])
    mod = smf.ols(formula, data=df)
    res = mod.fit(cov_type="cluster", cov_kwds={"groups": groups})
    return res


def main():
    panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
    panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
    panel = panel.sort_values(["ticker", "date"])

    # forward returns within firm
    for h in (1, 2, 3):
        panel[f"ret_fwd{h}"] = panel.groupby("ticker")["ret"].shift(-h)
    panel["ret_fwd1_intraday"] = panel.groupby("ticker")["ret_intraday"].shift(-1)

    # sentiment scaled to [-1, 1]
    panel["sent"] = panel["llm_sent"] / 100.0
    panel["sent_rel"] = panel["llm_sent_rel"] / 100.0
    panel["lm"] = panel["lm_tone"] / 100.0

    # analysis sample: firm-days with relevant news (relevance >= 30)
    news = panel[panel["sent_rel"].notna()].copy()
    # fallback rows where relevance info missing but sentiment exists
    extra = panel[panel["sent_rel"].isna() & panel["sent"].notna() &
                  (panel["llm_rel_mean"] >= 30 if "llm_rel_mean" in panel else False)]
    news = pd.concat([news, extra]) if len(extra) else news
    # dedupe
    news = news.drop_duplicates(subset=["ticker", "date_str"]).sort_values(["ticker", "date"])
    print(f"news firm-day sample: {len(news)} | firms: {news['ticker'].nunique()} | days: {news['date_str'].nunique()}")

    results = {}

    # ---------- descriptive statistics ----------
    desc = {
        "n_news_firmdays": int(len(news)),
        "n_firms": int(news["ticker"].nunique()),
        "n_days": int(news["date_str"].nunique()),
        "n_articles_total": 542,
        "n_articles_window": 341,
        "mean_news_per_firmday": float(news["n_news"].mean()),
        "llm_sent_mean": float(news["sent_rel"].mean()),
        "llm_sent_sd": float(news["sent_rel"].std()),
        "lm_tone_mean": float(news["lm"].mean()),
        "lm_tone_sd": float(news["lm"].std()),
        "lm_nonzero_frac": float((news["lm"] != 0).mean()),
        "llm_nonzero_frac": float((news["sent_rel"] != 0).mean()),
        "ret_fwd1_mean_bps": float(news["ret_fwd1"].mean() * 1e4),
        "ret_fwd1_sd_bps": float(news["ret_fwd1"].std() * 1e4),
    }

    # article-level descriptives
    arts = pd.read_json(f"{DATA}/news_all.json")
    sc = json.load(open(f"{DATA}/llm_scores.json"))
    arts["s"] = arts["url"].map(lambda u: sc.get(u, {}).get("sentiment"))
    arts["r"] = arts["url"].map(lambda u: sc.get(u, {}).get("relevance"))
    desc["article_llm_sent_mean"] = float(arts["s"].mean())
    desc["article_llm_sent_sd"] = float(arts["s"].std())
    desc["article_rel_mean"] = float(arts["r"].mean())
    desc["article_lm_tone_nonzero"] = int((arts["lm_tone"] != 0).sum()) if "lm_tone" in arts else None
    results["descriptives"] = desc

    # ---------- baseline regressions ----------
    base = news.dropna(subset=["ret_fwd1"]).copy()
    regs = {}

    def pack(res, name):
        regs[name] = {
            "coef": float(res.params.get("sent_rel", np.nan) if "sent_rel" in res.params else res.params.get("sent", np.nan)),
            "se": float(res.bse.get("sent_rel", np.nan) if "sent_rel" in res.bse else res.bse.get("sent", np.nan)),
            "t": float(res.tvalues.get("sent_rel", np.nan) if "sent_rel" in res.tvalues else res.tvalues.get("sent", np.nan)),
            "p": float(res.pvalues.get("sent_rel", np.nan) if "sent_rel" in res.pvalues else res.pvalues.get("sent", np.nan)),
            "n": int(res.nobs), "r2": float(res.rsquared),
        }

    # Spec 1: pooled, no controls
    r1 = two_way_cluster_ols(base, "ret_fwd1 ~ sent_rel")
    pack(r1, "pooled")
    # Spec 2: + controls
    ctrl = base.dropna(subset=["ret_lag1", "vol_21", "mkt_ew"])
    r2 = two_way_cluster_ols(ctrl, "ret_fwd1 ~ sent_rel + ret_lag1 + vol_21 + mkt_ew")
    pack(r2, "controls")
    # Spec 3: firm FE
    r3 = smf.ols("ret_fwd1 ~ sent_rel + C(ticker)", data=ctrl).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([pd.factorize(ctrl["ticker"])[0], pd.factorize(ctrl["date_str"])[0]])})
    pack(r3, "firm_fe")
    # Spec 4: day FE
    r4 = smf.ols("ret_fwd1 ~ sent_rel + C(date_str)", data=ctrl).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([pd.factorize(ctrl["ticker"])[0], pd.factorize(ctrl["date_str"])[0]])})
    pack(r4, "day_fe")
    # Spec 5: same-day return (contemporaneous)
    base0 = news.dropna(subset=["ret"]).copy()
    r5 = two_way_cluster_ols(base0, "ret ~ sent_rel")
    regs["same_day"] = {
        "coef": float(r5.params.get("sent_rel", np.nan)), "se": float(r5.bse.get("sent_rel", np.nan)),
        "t": float(r5.tvalues.get("sent_rel", np.nan)), "p": float(r5.pvalues.get("sent_rel", np.nan)),
        "n": int(r5.nobs), "r2": float(r5.rsquared)}
    # Spec 6: LM dictionary, same spec as Spec 2
    r6 = two_way_cluster_ols(ctrl, "ret_fwd1 ~ lm + ret_lag1 + vol_21 + mkt_ew")
    regs["lm_dict"] = {
        "coef": float(r6.params.get("lm", np.nan)), "se": float(r6.bse.get("lm", np.nan)),
        "t": float(r6.tvalues.get("lm", np.nan)), "p": float(r6.pvalues.get("lm", np.nan)),
        "n": int(r6.nobs), "r2": float(r6.rsquared)}
    # Spec 7: both in same regression
    r7 = two_way_cluster_ols(ctrl, "ret_fwd1 ~ sent_rel + lm + ret_lag1 + vol_21 + mkt_ew")
    regs["both"] = {
        "coef_llm": float(r7.params.get("sent_rel", np.nan)), "se_llm": float(r7.bse.get("sent_rel", np.nan)),
        "t_llm": float(r7.tvalues.get("sent_rel", np.nan)),
        "coef_lm": float(r7.params.get("lm", np.nan)), "se_lm": float(r7.bse.get("lm", np.nan)),
        "t_lm": float(r7.tvalues.get("lm", np.nan)),
        "n": int(r7.nobs), "r2": float(r7.rsquared)}
    results["regressions"] = regs

    # ---------- horizons ----------
    horizons = {}
    for h in (2, 3):
        b = news.dropna(subset=[f"ret_fwd{h}"]).copy()
        rh = two_way_cluster_ols(b, f"ret_fwd{h} ~ sent_rel")
        horizons[f"fwd{h}"] = {
            "coef": float(rh.params.get("sent_rel", np.nan)), "t": float(rh.tvalues.get("sent_rel", np.nan)),
            "p": float(rh.pvalues.get("sent_rel", np.nan)), "n": int(rh.nobs)}
    # intraday next-day (open->close), L&T-style
    bi = news.dropna(subset=["ret_fwd1_intraday"]).copy()
    ri = two_way_cluster_ols(bi, "ret_fwd1_intraday ~ sent_rel")
    horizons["intraday_fwd1"] = {
        "coef": float(ri.params.get("sent_rel", np.nan)), "t": float(ri.tvalues.get("sent_rel", np.nan)),
        "p": float(ri.pvalues.get("sent_rel", np.nan)), "n": int(ri.nobs)}
    results["horizons"] = horizons

    # ---------- decile portfolio sorts ----------
    b = news.dropna(subset=["ret_fwd1"]).copy()
    b["sent_rank"] = b["sent_rel"].rank(method="average")
    b["quintile"] = pd.qcut(b["sent_rel"].rank(method="first"), 5, labels=False, duplicates="drop") + 1
    port = b.groupby("quintile")["ret_fwd1"].agg(["mean", "std", "count"])
    port["mean_bps"] = port["mean"] * 1e4
    ls_mean = float(b.loc[b["quintile"] == 5, "ret_fwd1"].mean() - b.loc[b["quintile"] == 1, "ret_fwd1"].mean())
    # t-test for long-short
    hi = b.loc[b["quintile"] == 5, "ret_fwd1"].dropna()
    lo = b.loc[b["quintile"] == 1, "ret_fwd1"].dropna()
    tt = stats.ttest_ind(hi, lo, equal_var=False)
    results["portfolios"] = {
        "by_quintile_mean_bps": {str(q): float(m) for q, m in port["mean_bps"].items()},
        "by_quintile_n": {str(q): int(n) for q, n in port["count"].items()},
        "long_short_bps": ls_mean * 1e4,
        "long_short_t": float(tt.statistic), "long_short_p": float(tt.pvalue),
    }

    # LM dictionary quintiles for comparison
    bl = news.dropna(subset=["ret_fwd1", "lm"]).copy()
    bl["quintile_lm"] = pd.qcut(bl["lm"].rank(method="first"), 5, labels=False, duplicates="drop") + 1
    portl = bl.groupby("quintile_lm")["ret_fwd1"].agg(["mean", "count"])
    results["portfolios"]["lm_by_quintile_bps"] = {str(q): float(m * 1e4) for q, m in portl["mean"].items()}

    # ---------- daily IC (Spearman rank correlation per day) ----------
    ics, ics_lm, dates = [], [], []
    for d, g in news.dropna(subset=["ret_fwd1"]).groupby("date_str"):
        if len(g) >= 4 and g["sent_rel"].nunique() > 1:
            ic = stats.spearmanr(g["sent_rel"], g["ret_fwd1"])[0]
            ics.append(ic); dates.append(d)
            if g["lm"].nunique() > 1:
                ics_lm.append(stats.spearmanr(g["lm"], g["ret_fwd1"])[0])
    ic_series = pd.Series(ics)
    ic_t = ic_series.mean() / (ic_series.std() / np.sqrt(len(ic_series))) if len(ics) > 2 else np.nan
    iclm_series = pd.Series(ics_lm)
    iclm_t = iclm_series.mean() / (iclm_series.std() / np.sqrt(len(iclm_series))) if len(ics_lm) > 2 else np.nan
    results["ic"] = {
        "n_days": len(ics), "ic_mean": float(ic_series.mean()), "ic_t": float(ic_t),
        "ic_pos_frac": float((ic_series > 0).mean()),
        "lm_ic_mean": float(iclm_series.mean()), "lm_ic_t": float(iclm_t), "lm_n_days": len(ics_lm),
        "ic_series": ics, "ic_dates": dates,
    }

    # ---------- heterogeneity ----------
    het = {}
    # size split by dollar volume
    med_size = ctrl["size_proxy"].median()
    big = ctrl[ctrl["size_proxy"] >= med_size]; small = ctrl[ctrl["size_proxy"] < med_size]
    for name, sub in [("large", big), ("small", small)]:
        if len(sub) > 20:
            r = two_way_cluster_ols(sub, "ret_fwd1 ~ sent_rel")
            het[f"size_{name}"] = {"coef": float(r.params.get("sent_rel", np.nan)),
                                   "t": float(r.tvalues.get("sent_rel", np.nan)), "n": int(r.nobs)}
    # volatility regime: cross-sectional realized vol proxy per day
    vol_regime = panel.groupby("date_str")["vol_21"].mean().rename("mkt_vol").reset_index()
    ctrl2 = ctrl.merge(vol_regime, on="date_str")
    vm = ctrl2["mkt_vol"].median()
    hi_v = ctrl2[ctrl2["mkt_vol"] >= vm]; lo_v = ctrl2[ctrl2["mkt_vol"] < vm]
    for name, sub in [("high_vol", hi_v), ("low_vol", lo_v)]:
        if len(sub) > 20:
            r = two_way_cluster_ols(sub, "ret_fwd1 ~ sent_rel")
            het[f"vol_{name}"] = {"coef": float(r.params.get("sent_rel", np.nan)),
                                  "t": float(r.tvalues.get("sent_rel", np.nan)), "n": int(r.nobs)}
    # news intensity
    med_n = ctrl["n_news"].median()
    for name, sub in [("multi_news", ctrl[ctrl["n_news"] > med_n]), ("single_news", ctrl[ctrl["n_news"] <= med_n])]:
        if len(sub) > 20:
            r = two_way_cluster_ols(sub, "ret_fwd1 ~ sent_rel")
            het[f"news_{name}"] = {"coef": float(r.params.get("sent_rel", np.nan)),
                                   "t": float(r.tvalues.get("sent_rel", np.nan)), "n": int(r.nobs)}
    results["heterogeneity"] = het

    # ---------- logit direction ----------
    blg = news.dropna(subset=["ret_fwd1"]).copy()
    blg["up"] = (blg["ret_fwd1"] > 0).astype(int)
    X = sm.add_constant(blg[["sent_rel"]])
    logit = sm.Logit(blg["up"], X).fit(disp=0)
    results["logit"] = {
        "coef": float(logit.params["sent_rel"]), "p": float(logit.pvalues["sent_rel"]),
        "pseudo_r2": float(logit.prsquared), "n": int(logit.nobs),
        "marginal_effect": float(logit.get_margeff().margeff[0]),
    }

    json.dump(results, open(f"{DATA}/results.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in results.items() if k not in ("ic",)}, indent=1, default=str)[:4000])
    print(f"\nIC: mean {ic_series.mean():.4f} (t={ic_t:.2f}) over {len(ics)} days; LM IC mean {iclm_series.mean():.4f} (t={iclm_t:.2f})")


if __name__ == "__main__":
    main()
