#!/usr/bin/env python3
"""P1-1: independent verification of the H4 price-language echo split.

(a) Classification audit: item-by-item LLM-assisted re-classification of the 52
    regex-flagged headlines into P (realized price move) / E (fundamental
    magnitude) / D (directional expectation) / N (regex false positive).
    Regex precision for realized-price = P / flagged.
(b) Refined echo split: strict-P firm-days vs rest, plus strict-P vs
    no-flag clean group, vs the original regex split.
(c) Dominance checks: leave-one-firm-day-out and leave-one-company-out
    jackknife of the priced coefficient and the priced-clean difference.

Output: data/results_p11.json  (consumed by the paper + test_numbers.py)
"""
import json
import re
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DATA = "/home/z/my-project/data"
rng = np.random.default_rng(20261018)

PRICE_PAT = re.compile(
    r"\b(rose|rises?|risen|jump(?:s|ed|ing)?|surge[sd]?|surging|soar(?:s|ed|ing)?|"
    r"climb(?:s|ed|ing)?|rall(?:y|ies|ied|ing)|gain(?:s|ed|ing)?|fell|falls?|fallen|"
    r"drop(?:s|ped|ping)?|dropped|plunge[sd]?|plunging|sink[s]?|sank|sinking|slide[sd]?|"
    r"slump(?:s|ed|ing)?|tumbl(?:e|es|ed|ing)|crash(?:es|ed|ing)?|declin(?:e|es|ed|ing)|"
    r"rebound(?:s|ed|ing)?|bounc(?:e|es|ed|ing)|spike[sd]?|spiking|dip(?:s|ped)?|"
    r"up\s?\d|down\s?\d|\d+%\s?(?:up|down)|hit\s+(?:a\s+)?(?:record|new|52)|"
    r"after\s+(?:earnings|results|guidance|beating|missing))\b", re.I)

# ---------------- rebuild the same panel as analysis_v2 ----------------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)

arts = json.load(open(f"{DATA}/news_scored.json"))
orig = json.load(open(f"{DATA}/llm_scores.json"))
anon = json.load(open(f"{DATA}/llm_scores_anon.json"))

cls = json.load(open(f"{DATA}/priced_classification.json"))
label_by_iid = cls["labels"]
ph = json.load(open(f"{DATA}/priced_headlines.json"))
title_to_label = {ph[i]["title"]: label_by_iid[str(i)] for i in range(len(ph))}

rows = []
for a in arts:
    if not (a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"):
        continue
    u = a["url"]
    flagged = bool(PRICE_PAT.search(a["title"]))
    lab = title_to_label.get(a["title"], None) if flagged else None
    rows.append({
        "ticker": a["ticker"], "date": a["date_iso"], "url": u,
        "s_orig": orig.get(u, {}).get("sentiment"),
        "s_anon": anon.get(u, {}).get("sentiment"),
        "relevance": orig.get(u, {}).get("relevance"),
        "priced": flagged, "cls": lab,
    })
adf = pd.DataFrame(rows)

hi = adf[adf["relevance"] >= 30]
agg = hi.groupby(["ticker", "date"]).agg(
    sent=("s_orig", "mean"), sent_anon=("s_anon", "mean"), n_news=("url", "count"),
    priced_any=("priced", "max"), relevance=("relevance", "mean"),
).reset_index()
# strict-P / E / D / N firm-day flags (any article of that class on the day)
for cat in ("P", "E", "D", "N"):
    hi2 = hi.assign(flag=hi["cls"] == cat)
    agg2 = hi2.groupby(["ticker", "date"])["flag"].max().rename(f"any_{cat}").reset_index()
    agg = agg.merge(agg2, on=["ticker", "date"], how="left")
agg["date"] = pd.to_datetime(agg["date"])

p = panel.merge(agg, on=["ticker", "date"], how="left")
p["priced_any"] = p["priced_any"].astype(bool)
for cat in ("P", "E", "D", "N"):
    p[f"any_{cat}"] = p[f"any_{cat}"].fillna(False).astype(bool)
p["sent"] = p["sent"] / 100.0   # scale to [-1,1], identical to analysis_v2
p["sent_anon"] = p["sent_anon"] / 100.0
news = p[p["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"]).sort_values(["ticker", "date"])
ctrl = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
ctrl = ctrl.dropna(subset=["sent_anon"])

def tw(df, formula):
    fc = pd.factorize(df["ticker"])[0]; dc = pd.factorize(df["date_str"])[0]
    m = smf.ols(formula, data=df).fit(cov_type="cluster",
        cov_kwds={"groups": np.column_stack([fc, dc])})
    return m

FORM = "ret_fwd1 ~ sent + ret + ret_lag1 + vol_21 + mkt_ew"

# ---------------- (a) classification quality ----------------
flagged = adf[adf["priced"]]
counts = flagged["cls"].value_counts().to_dict()
R = {"classification": {
    "n_flagged": int(len(flagged)),
    "n_flagged_rel30": int((hi["priced"]).sum()),
    "counts": counts,
    "regex_precision_realized_price": float(counts.get("P", 0) / len(flagged)),
    "classifier": "LLM-assisted structured re-classification (rulebook in "
                  "data/priced_classification.json); not independent human annotation",
}}

# ---------------- (b) refined echo splits ----------------
splits = {}
for name, mask in [
    ("regex_priced", ctrl["priced_any"]),
    ("regex_clean", ~ctrl["priced_any"]),
    ("strictP", ctrl["any_P"]),
    ("non_strictP", ~ctrl["any_P"]),
    ("clean_noflag", ~ctrl["priced_any"]),
    ("flagged_nonP", ctrl["priced_any"] & ~ctrl["any_P"]),
]:
    sub = ctrl[mask]
    if len(sub) < 30:
        splits[name] = {"n": int(len(sub))}
        continue
    m = tw(sub, FORM)
    splits[name] = {"n": int(m.nobs), "coef": float(m.params["sent"]),
                    "t": float(m.tvalues["sent"]), "p": float(m.pvalues["sent"])}
R["splits"] = splits

# category descriptives at firm-day level
cat_desc = {}
for name, mask in [
    ("strictP", ctrl["any_P"]), ("flagged_nonP", ctrl["priced_any"] & ~ctrl["any_P"]),
    ("clean", ~ctrl["priced_any"]),
]:
    sub = ctrl[mask]
    cat_desc[name] = {
        "n_firmdays": int(len(sub)),
        "mean_sent": float(sub["sent"].mean() * 100),
        "mean_abs_sameday_ret_bps": float(sub["ret"].abs().mean() * 1e4),
        "mean_sameday_ret_bps": float(sub["ret"].mean() * 1e4),
        "mean_fwd1_ret_bps": float(sub["ret_fwd1"].mean() * 1e4),
    }
R["category_descriptives"] = cat_desc

# ---------------- (c) dominance: jackknife ----------------
pk = ctrl[ctrl["any_P"]]
print(f"strict-P firm-days: {len(pk)} over {pk['ticker'].nunique()} companies")
comp = pk.groupby("ticker").size().sort_values(ascending=False)
R["dominance"] = {
    "n_strictP_firmdays": int(len(pk)),
    "n_companies": int(pk["ticker"].nunique()),
    "top_companies": {k: int(v) for k, v in comp.head(8).items()},
    "max_share_one_company": float(comp.max() / comp.sum()),
}

# leave-one-firm-day-out on the strict-P coefficient and the strictP-clean difference
loco_beta, loco_diff = [], []
idxs = list(pk.index)
for i in idxs:
    sub = ctrl[ctrl["any_P"]].drop(index=i)
    cl = ctrl[~ctrl["any_P"]]
    try:
        m1 = tw(sub, FORM); m2 = tw(cl, FORM)
        loco_beta.append(float(m1.params["sent"]))
        loco_diff.append(float(m1.params["sent"]) - float(m2.params["sent"]))
    except Exception:
        pass
R["dominance"]["loco_beta_range"] = [float(np.min(loco_beta)), float(np.max(loco_beta))]
R["dominance"]["loco_diff_range"] = [float(np.min(loco_diff)), float(np.max(loco_diff))]
R["dominance"]["loco_sign_flip_frac"] = float(np.mean(np.array(loco_diff) <= 0))

# leave-one-company-out (drop all firm-days of each company present in strict-P set)
jko_beta, jko_diff = [], []
for tick in sorted(pk["ticker"].unique()):
    sub = ctrl[ctrl["any_P"] & (ctrl["ticker"] != tick)]
    cl = ctrl[~ctrl["any_P"] & (ctrl["ticker"] != tick)]
    if len(sub) < 30:
        continue
    try:
        m1 = tw(sub, FORM); m2 = tw(cl, FORM)
        jko_beta.append(float(m1.params["sent"]))
        jko_diff.append(float(m1.params["sent"]) - float(m2.params["sent"]))
    except Exception:
        pass
R["dominance"]["jko_beta_range"] = [float(np.min(jko_beta)), float(np.max(jko_beta))]
R["dominance"]["jko_diff_range"] = [float(np.min(jko_diff)), float(np.max(jko_diff))]
R["dominance"]["jko_sign_flip_frac"] = float(np.mean(np.array(jko_diff) <= 0))
R["dominance"]["jko_n_evals"] = len(jko_diff)

json.dump(R, open(f"{DATA}/results_p11.json", "w"), indent=1)

# ---------------- report ----------------
print("\n=== P1-1 classification audit ===")
print(f"flagged: {R['classification']['n_flagged']} | labels {counts} | "
      f"regex precision for realized-price: {R['classification']['regex_precision_realized_price']:.3f}")
print("\n=== refined splits (ret_fwd1 ~ sent + ret + ...) ===")
for k, v in splits.items():
    if "coef" in v:
        print(f"  {k:14s} n={v['n']:4d} beta={v['coef']:+.4f} t={v['t']:+.2f} p={v['p']:.3f}")
    else:
        print(f"  {k:14s} n={v['n']} (too small)")
print("\n=== descriptives ===")
for k, v in cat_desc.items():
    print(f"  {k:12s} n={v['n_firmdays']:3d} sent={v['mean_sent']:+6.1f} |ret|={v['mean_abs_sameday_ret_bps']:5.0f}bps ret={v['mean_sameday_ret_bps']:+6.0f}bps fwd={v['mean_fwd1_ret_bps']:+6.0f}bps")
print("\n=== dominance ===")
print(f"  top companies: {comp.head(5).to_dict()}")
print(f"  max share one company: {R['dominance']['max_share_one_company']:.2f}")
print(f"  LOCO beta range: [{R['dominance']['loco_beta_range'][0]:+.4f}, {R['dominance']['loco_beta_range'][1]:+.4f}]")
print(f"  LOCO diff range: [{R['dominance']['loco_diff_range'][0]:+.4f}, {R['dominance']['loco_diff_range'][1]:+.4f}] sign-flip frac {R['dominance']['loco_sign_flip_frac']:.2f}")
print(f"  JK-company beta range: [{R['dominance']['jko_beta_range'][0]:+.4f}, {R['dominance']['jko_beta_range'][1]:+.4f}]")
print(f"  JK-company diff range: [{R['dominance']['jko_diff_range'][0]:+.4f}, {R['dominance']['jko_diff_range'][1]:+.4f}] sign-flip frac {R['dominance']['jko_sign_flip_frac']:.2f}")
