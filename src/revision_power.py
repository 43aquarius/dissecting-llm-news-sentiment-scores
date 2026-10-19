#!/usr/env/bin python3
"""REVISION ANALYSES (responding to the simulated referee report, deliverable G).

Three referee-requested additions, all computed from archived data only:

  (B1) Power / minimal detectable effects (MDE) for every test in the
       declared family, using the published standard errors:
           MDE_80 = (z_{0.975} + z_{0.80}) * SE = 2.8016 * SE
       and achieved power at the observed effect,
           power = Phi(|d|/SE - 1.96) + Phi(-|d|/SE - 1.96).

  (C1) Endpoint stability across scoring sessions. The four named draws were
       NOT collected simultaneously: the original round ran 2026-10-15
       16:01-16:24 UTC (scripts/llm_score.log, llm_score2.log); the
       anonymized + three repeat rounds ran 2026-10-16 04:24-04:33 UTC
       (scripts/llm_score_v2.log) ~12 hours later. If the serving endpoint
       drifted between sessions, cross-session disagreement (original vs
       repeat) would exceed the within-session noise floor (repeat vs
       repeat). We compare both.

  (C2) Residual third-party identification in the anonymized headlines:
       share of anonymized titles still naming another sample firm, under
       both a case-insensitive (upper bound) and case-sensitive (lower
       bound) matching convention, replicating the alias table of
       llm_score_v2.mjs.

Output: data/results_revision.json (results_v2.json left untouched).
"""
import json
import re
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

DATA = "/home/z/my-project/data"
Z975, Z80 = 1.959964, 0.841621
MDE_MULT = Z975 + Z80  # 2.801585

# ---------------- rebuild the article frame exactly as analysis_v2.build() ----------------
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
        "relevance": orig.get(u, {}).get("relevance"),
    })
adf = pd.DataFrame(rows)
print(f"in-window articles: {len(adf)} (should be 341)")
assert len(adf) == 341

R = {"revision_scope": "B1 power, C1 endpoint stability, C2 residual third-party identity",
     "mde_method": "MDE_80 = (z_.975 + z_.80) * SE; power = Phi(|d|/SE - 1.96) + Phi(-|d|/SE - 1.96)"}

# ================= (C1) Endpoint stability across scoring sessions =================
X4 = adf[["s_orig", "s_rep1", "s_rep2", "s_rep3"]].dropna()
n4 = len(X4)
names = ["original (Oct 15)", "rep1 (Oct 16)", "rep2 (Oct 16)", "rep3 (Oct 16)"]
C = X4.corr()
cross_pairs = [(0, 1), (0, 2), (0, 3)]          # original vs each repeat
within_pairs = [(1, 2), (1, 3), (2, 3)]         # repeats among themselves

def pair_stats(pairs, label):
    rs, sps, mads, exacts = [], [], [], []
    for i, j in pairs:
        rs.append(C.iloc[i, j])
        sps.append(X4.iloc[:, i].corr(X4.iloc[:, j], method="spearman"))
        mads.append((X4.iloc[:, i] - X4.iloc[:, j]).abs().mean())
        exacts.append((X4.iloc[:, i] == X4.iloc[:, j]).mean())
    return {"label": label, "pairs": [f"{names[i]} vs {names[j]}" for i, j in pairs],
            "mean_pearson": float(np.mean(rs)), "pearson_each": [float(r) for r in rs],
            "mean_spearman": float(np.mean(sps)),
            "mean_abs_diff_points": float(np.mean(mads)),
            "mean_exact_match": float(np.mean(exacts))}

cross = pair_stats(cross_pairs, "cross-session (original Oct 15 vs repeats Oct 16)")
within = pair_stats(within_pairs, "within-session (repeats vs repeats, Oct 16)")

# distributional test: |diff| cross (3*341 values) vs |diff| within (3*341 values)
cross_vals = np.concatenate([(X4.iloc[:, i] - X4.iloc[:, j]).abs().values for i, j in cross_pairs])
within_vals = np.concatenate([(X4.iloc[:, i] - X4.iloc[:, j]).abs().values for i, j in within_pairs])
mw = stats.mannwhitneyu(cross_vals, within_vals, alternative="two-sided")
tt = stats.ttest_ind(cross_vals, within_vals, equal_var=False)
# paired-by-article comparison of mean |diff| (each article: mean cross |diff| vs mean within |diff|)
by_art_cross = np.mean([(X4.iloc[:, i] - X4.iloc[:, j]).abs().values for i, j in cross_pairs], axis=0)
by_art_within = np.mean([(X4.iloc[:, i] - X4.iloc[:, j]).abs().values for i, j in within_pairs], axis=0)
tt_paired = stats.ttest_rel(by_art_cross, by_art_within)

R["endpoint_stability"] = {
    "sessions": {"original_named": "2026-10-15 16:01-16:24 UTC (llm_score.log, llm_score2.log)",
                 "anon_and_repeats": "2026-10-16 04:24-04:33 UTC (llm_score_v2.log)",
                 "gap_hours": 12.0},
    "n_articles": int(n4),
    "cross_session": cross, "within_session": within,
    "cross_minus_within_mean_abs_diff_points": float(cross_vals.mean() - within_vals.mean()),
    "mannwhitney_p": float(mw.pvalue), "welch_p": float(tt.pvalue),
    "paired_by_article_p": float(tt_paired.pvalue),
}
print("\n=== C1 endpoint stability ===")
print(f"cross-session:  r={cross['mean_pearson']:.3f}  |d|={cross['mean_abs_diff_points']:.2f}  exact={cross['mean_exact_match']:.3f}")
print(f"within-session: r={within['mean_pearson']:.3f}  |d|={within['mean_abs_diff_points']:.2f}  exact={within['mean_exact_match']:.3f}")
print(f"cross-within |d| gap: {cross['mean_abs_diff_points']-within['mean_abs_diff_points']:+.3f} pts "
      f"(Mann-Whitney p={mw.pvalue:.3f}, paired t p={tt_paired.pvalue:.3f})")

# ================= (B1) Power / MDE =================
# rebuild regression sample (same filter as analysis_v2)
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)
hi = adf[adf["relevance"] >= 30]
agg = hi.groupby(["ticker", "date"]).agg(
    sent=("s_orig", "mean"), sent_anon=("s_anon", "mean"),
    rep1=("s_rep1", "mean"), rep2=("s_rep2", "mean"), rep3=("s_rep3", "mean"),
    n_news=("url", "count"), relevance=("relevance", "mean")).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
p = panel.merge(agg, on=["ticker", "date"], how="left")
for col in ("sent", "sent_anon"):
    p[col] = p[col] / 100.0
news = p[p["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret", "sent_anon"]).copy()

def tw(df, formula):
    fc = pd.factorize(df["ticker"])[0]; dc = pd.factorize(df["date_str"])[0]
    return smf.ols(formula, data=df).fit(cov_type="cluster",
        cov_kwds={"groups": np.column_stack([fc, dc])})

m1 = tw(ctrl, "ret_fwd1 ~ sent + ret_lag1 + vol_21 + mkt_ew")
beta, se, tval = float(m1.params["sent"]), float(m1.bse["sent"]), float(m1.tvalues["sent"])
sd_sent = float(ctrl["sent"].std())

def power_at(delta, se_):
    lam = abs(delta) / se_
    return float(stats.norm.cdf(lam - Z975) + stats.norm.cdf(-lam - Z975))

power_rows = [{
    "test": "H1 baseline next-day coefficient (named)",
    "observed": beta, "se": se, "mde80": MDE_MULT * se,
    "power_at_observed": power_at(beta, se), "n": int(m1.nobs)}]

# difference tests: SE implied by the published bootstrap CIs (results_v2.json)
rv2 = json.load(open(f"{DATA}/results_v2.json"))
dt = rv2["h2_prediction"]["difference_tests"]
for key, label in [("named_minus_anon", "H2 difference: beta_named - beta_anon"),
                   ("named_minus_lm", "H2 difference: beta_named - beta_dictionary")]:
    d = dt[key]
    se_b = (d["boot_ci95"][1] - d["boot_ci95"][0]) / (2 * Z975)
    power_rows.append({"test": label, "observed": d["obs"], "se": float(se_b),
                       "mde80": MDE_MULT * se_b, "power_at_observed": power_at(d["obs"], se_b),
                       "n": 205})
pc = rv2["h4_echo"]["priced_minus_clean_boot"]
se_pc = (pc["boot_ci95"][1] - pc["boot_ci95"][0]) / (2 * Z975)
power_rows.append({"test": "H4 difference: beta_priced - beta_clean", "observed": pc["obs"],
                   "se": float(se_pc), "mde80": MDE_MULT * se_pc,
                   "power_at_observed": power_at(pc["obs"], se_pc), "n": 205})
# H2 level shift (article level)
hm = rv2["h2_measurement"]
se_shift = abs(hm["mean_shift"]) / abs(hm["shift_t"])
power_rows.append({"test": "H2 identity level shift (score points)", "observed": hm["mean_shift"],
                   "se": float(se_shift), "mde80": MDE_MULT * se_shift,
                   "power_at_observed": power_at(hm["mean_shift"], se_shift), "n": int(hm["n"])})
# H5 selection (v4: main test is firm+day FE with two-way clustered SE)
h5 = rv2["h5_selection"]
d_bps = (h5["mean_abs_ret_news_bps"] - h5["mean_abs_ret_nonews_bps"])
se_sel = abs(d_bps) / abs(h5["fe2_t"])
power_rows.append({"test": "H5 coverage selection (|ret| gap, bps; firm+day FE)",
                   "observed": d_bps, "se": float(se_sel), "mde80": MDE_MULT * se_sel,
                   "power_at_observed": power_at(d_bps, se_sel),
                   "n": int(h5.get("n_panel_firmdays", 2664))})

R["power"] = {"rows": power_rows,
              "h1_sd_sent": sd_sent, "h1_mde80_in_sd_units": MDE_MULT * se * sd_sent}
print("\n=== B1 power / MDE ===")
for r_ in power_rows:
    print(f"{r_['test']:48s} obs={r_['observed']:+.4f} se={r_['se']:.4f} "
          f"MDE80={r_['mde80']:.4f} power={r_['power_at_observed']:.3f}")
print(f"H1: MDE80 = {MDE_MULT*se:.4f} = {MDE_MULT*se*sd_sent:.4f} per 1-SD sentiment move "
      f"(1-SD = {sd_sent:.2f}); estimate/SD-move = {beta*sd_sent:.4f}")

# ================= (C1b) Session confounding decomposition =================
# CRITICAL REVISION FINDING: the published H2 level shift (named - anon = +4.75)
# compares scores collected ~12h apart (named: Oct 15; anon: Oct 16), while the
# anonymized condition and all three named repeats ran in the SAME Oct-16 session
# (04:24-04:33 UTC). Decompose:
#   (named_Oct15 - anon_Oct16) = [named_Oct15 - named_Oct16] + [named_Oct16 - anon_Oct16]
#                              = session drift        + same-session identity effect
Xa = adf[["s_orig", "s_anon", "s_rep1", "s_rep2", "s_rep3"]].dropna()
Xa = Xa.assign(repm=Xa[["s_rep1", "s_rep2", "s_rep3"]].mean(axis=1))
tt_id = stats.ttest_rel(Xa["s_anon"], Xa["repm"])
wil_id = stats.wilcoxon(Xa["s_anon"], Xa["repm"])
tt_sess = stats.ttest_rel(Xa["s_orig"], Xa["repm"])
per_rep = {}
for c in ("s_rep1", "s_rep2", "s_rep3"):
    t_ = stats.ttest_rel(Xa["s_anon"], Xa[c])
    per_rep[c] = {"shift": float(Xa["s_anon"].mean() - Xa[c].mean()), "t": float(t_.statistic),
                  "p": float(t_.pvalue)}

def icc2k(cols):
    V = Xa[cols].values; n_, k_ = V.shape
    gm = V.mean(); rm = V.mean(axis=1)
    msb = (k_ * ((rm - gm) ** 2).sum()) / (n_ - 1)
    msw = (V.var(axis=1, ddof=1) * (k_ - 1)).sum() / (n_ * (k_ - 1))
    return float((msb - msw) / (msb + (k_ - 1) * msw))

R["session_confounding"] = {
    "n_articles": int(len(Xa)),
    "published_shift_named_minus_anon": float((Xa["s_orig"] - Xa["s_anon"]).mean()),
    "session_drift_named_oct15_minus_oct16": {
        "estimate": float(Xa["s_orig"].mean() - Xa["repm"].mean()),
        "t": float(tt_sess.statistic), "p": float(tt_sess.pvalue)},
    "same_session_identity_effect_anon_minus_named": {
        "estimate": float(Xa["s_anon"].mean() - Xa["repm"].mean()),
        "t": float(tt_id.statistic), "p": float(tt_id.pvalue),
        "wilcoxon_p": float(wil_id.pvalue),
        "per_repeat": per_rep},
    "mean_by_draw": {c: float(Xa[c].mean()) for c in ("s_orig", "s_anon", "s_rep1", "s_rep2", "s_rep3")},
    "icc_variants": {"named_only_oct16_3draws": icc2k(["s_rep1", "s_rep2", "s_rep3"]),
                     "pooled_4draws_2sessions": icc2k(["s_orig", "s_rep1", "s_rep2", "s_rep3"]),
                     "oct16_anon_plus_3reps": icc2k(["s_anon", "s_rep1", "s_rep2", "s_rep3"])},
    "displacement_benchmarks": {
        "anon_vs_rep_mean_abs_diff": float(np.mean([(Xa["s_anon"] - Xa[c]).abs().mean()
                                                    for c in ("s_rep1", "s_rep2", "s_rep3")])),
        "rep_vs_rep_mean_abs_diff": float(np.mean([(Xa[a] - Xa[b]).abs().mean()
                                                    for a, b in (("s_rep1", "s_rep2"), ("s_rep1", "s_rep3"), ("s_rep2", "s_rep3"))])),
        "orig_vs_anon_mean_abs_diff": float((Xa["s_orig"] - Xa["s_anon"]).abs().mean())},
    "protocol_note": "v1 and v2 named protocols verbatim-identical (system prompt, user message, batch=25, thinking disabled); the gap reflects session-level variation (endpoint state and/or batch composition), not protocol change",
}
print("\n=== C1b session confounding ===")
sc = R["session_confounding"]
print(f"published shift (orig-anon): {sc['published_shift_named_minus_anon']:+.3f}")
print(f"session drift (Oct15-Oct16): {sc['session_drift_named_oct15_minus_oct16']['estimate']:+.3f} "
      f"(t={sc['session_drift_named_oct15_minus_oct16']['t']:.2f})")
print(f"same-session identity: {sc['same_session_identity_effect_anon_minus_named']['estimate']:+.3f} "
      f"(t={sc['same_session_identity_effect_anon_minus_named']['t']:.2f}, "
      f"p={sc['same_session_identity_effect_anon_minus_named']['p']:.4f})")
print(f"ICC: named-only {sc['icc_variants']['named_only_oct16_3draws']:.3f} | "
      f"pooled {sc['icc_variants']['pooled_4draws_2sessions']:.3f} | "
      f"oct16-4cond {sc['icc_variants']['oct16_anon_plus_3reps']:.3f}")

# same-session predictive layer: beta_anon vs beta_repmean (both Oct 16)
hi_r = adf[adf["relevance"] >= 30].copy()
hi_r["repmean"] = hi_r[["s_rep1", "s_rep2", "s_rep3"]].mean(axis=1)
agg_r = hi_r.groupby(["ticker", "date"]).agg(
    sent_rep=("repmean", "mean"), sent_anon=("s_anon", "mean"),
    n_news=("url", "count"), relevance=("relevance", "mean")).reset_index()
agg_r["date"] = pd.to_datetime(agg_r["date"])
pr = panel.merge(agg_r, on=["ticker", "date"], how="left")
for col in ("sent_rep", "sent_anon"):
    pr[col] = pr[col] / 100.0
newsr = pr[pr["sent_rep"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrlr = newsr.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
ctrlr = ctrlr.dropna(subset=["sent_anon"])
m_rep = tw(ctrlr, "ret_fwd1 ~ sent_rep + ret_lag1 + vol_21 + mkt_ew")
m_ano = tw(ctrlr, "ret_fwd1 ~ sent_anon + ret_lag1 + vol_21 + mkt_ew")
b_rep, t_rep = float(m_rep.params["sent_rep"]), float(m_rep.tvalues["sent_rep"])
b_ano, t_ano = float(m_ano.params["sent_anon"]), float(m_ano.tvalues["sent_anon"])

def fit_beta(df, col):
    Xl = np.column_stack([np.ones(len(df)), df[col], df["ret_lag1"], df["vol_21"], df["mkt_ew"]])
    yl = df["ret_fwd1"].values
    try:
        return np.linalg.solve(Xl.T @ Xl, Xl.T @ yl)[1]
    except np.linalg.LinAlgError:
        return np.nan
rng2 = np.random.default_rng(20261017)
dks = ctrlr["date_str"].values; uq = np.unique(dks)
diffs_ar = []
for b in range(999):
    picked = rng2.choice(uq, size=len(uq), replace=True)
    parts = [ctrlr[dks == d] for d in picked]
    dfb = pd.concat([pt.assign(date_str=f"{d}__{i}") for i, (d, pt) in enumerate(zip(picked, parts))])
    diffs_ar.append(fit_beta(dfb, "sent_rep") - fit_beta(dfb, "sent_anon"))
diffs_ar = np.array(diffs_ar)
obs_ar = b_rep - b_ano
p_ar = 2 * min((diffs_ar <= 0).mean(), (diffs_ar >= 0).mean())
R["same_session_prediction"] = {
    "beta_named_oct16_repmean": b_rep, "t": t_rep,
    "beta_anon_oct16": b_ano, "t_anon": t_ano,
    "difference": float(obs_ar),
    "boot_ci95": [float(np.percentile(diffs_ar, 2.5)), float(np.percentile(diffs_ar, 97.5))],
    "boot_p": float(p_ar), "B": 999, "n": int(m_rep.nobs)}
print(f"same-session prediction: beta_rep={b_rep:.4f} (t={t_rep:.2f}) beta_anon={b_ano:.4f} (t={t_ano:.2f}) "
      f"diff={obs_ar:.4f} p={p_ar:.3f}")

# per-rep baseline coefficients (session robustness of H1)
perrep_beta = {}
for c in ("s_rep1", "s_rep2", "s_rep3"):
    agg_x = hi_r.groupby(["ticker", "date"]).agg(sent_x=(c, "mean")).reset_index()
    agg_x["date"] = pd.to_datetime(agg_x["date"])
    px = panel.merge(agg_x, on=["ticker", "date"], how="left")
    px["sent_x"] = px["sent_x"] / 100.0
    nx = px[px["sent_x"].notna()].drop_duplicates(subset=["ticker", "date_str"])
    cx = nx.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
    mx = tw(cx, "ret_fwd1 ~ sent_x + ret_lag1 + vol_21 + mkt_ew")
    perrep_beta[c] = {"beta": float(mx.params["sent_x"]), "t": float(mx.tvalues["sent_x"]), "n": int(mx.nobs)}
R["session_robustness_h1"] = {"beta_orig_oct15": beta, "t_orig": tval,
                              "per_repeat": perrep_beta,
                              "beta_repmean_oct16": b_rep, "t_repmean": t_rep}
print("H1 session robustness: orig(t=%.2f) " % tval +
      " ".join(f"{v['beta']:.4f}(t={v['t']:.2f})" for v in perrep_beta.values()) +
      f" repmean={b_rep:.4f}(t={t_rep:.2f})")

# ================= (C2) residual identity in the anonymized headlines =================
# v4 fix (audit E7): the previous replication used V: ["Visa"] in the alias
# table, but the EXECUTED script (llm_score_v2.mjs) has V: [] -- no Visa alias.
# Under the executed table, ticker-V headlines are a NO-OP for anonymization
# (10/341 still name "Visa"). The table below is now the executed one, and the
# focal-firm V failure is quantified separately in v_exclusion.py.
ALIASES = {
    "AAPL": ["Apple"], "MSFT": ["Microsoft"], "NVDA": ["Nvidia", "NVIDIA"], "GOOGL": ["Alphabet", "Google"],
    "AMZN": ["Amazon"], "META": ["Meta Platforms", "Meta", "Facebook"], "TSLA": ["Tesla"], "AVGO": ["Broadcom"],
    "AMD": ["Advanced Micro Devices", "AMD"], "NFLX": ["Netflix"], "INTC": ["Intel"], "ORCL": ["Oracle"],
    "CRM": ["Salesforce"], "ADBE": ["Adobe"], "QCOM": ["Qualcomm"], "IBM": ["IBM"],
    "JPM": ["JPMorgan Chase", "JPMorgan", "J.P. Morgan"], "BAC": ["Bank of America", "BofA"],
    "GS": ["Goldman Sachs"], "MS": ["Morgan Stanley"], "WFC": ["Wells Fargo"], "V": [],
    "MA": ["Mastercard"], "XOM": ["Exxon Mobil", "Exxon"], "CVX": ["Chevron"], "PG": ["Procter & Gamble", "P&G"],
    "KO": ["Coca-Cola", "Coca Cola", "Coke"], "WMT": ["Walmart", "Wal-Mart"], "COST": ["Costco"],
    "JNJ": ["Johnson & Johnson", "Johnson and Johnson"], "LLY": ["Eli Lilly", "Lilly"], "DIS": ["Disney"],
    "BA": ["Boeing"], "CAT": ["Caterpillar"], "GE": ["GE Aerospace", "General Electric"], "PFE": ["Pfizer"],
}
SKIP_TICKER = {"V"}  # single-letter ticker: \bV\b false-positives (e.g. "V-shaped")

def anonymize(title, ticker):
    """Replicates llm_score_v2.mjs anonymize() exactly."""
    t = title
    t = re.sub(rf"\b{ticker}\b", "the company", t)
    for name in ALIASES.get(ticker, []):
        esc = re.escape(name)
        t = re.sub(rf"\b{esc}\b", "the company", t, flags=re.I)
    t = re.sub(r"\bthe company( the company)+\b", "the company", t, flags=re.I)
    return t

def third_party_hits(text, focal, case_insensitive=True):
    """Count mentions of OTHER sample firms in text (same conventions as anonymizer)."""
    hits = []
    for tk, names in ALIASES.items():
        if tk == focal:
            continue
        if tk not in SKIP_TICKER and re.search(rf"\b{re.escape(tk)}\b", text):
            hits.append(tk); continue
        for nm in names:
            flags = re.I if case_insensitive else 0
            if re.search(rf"\b{re.escape(nm)}\b", text, flags=flags):
                hits.append(tk); break
    return hits

for ci, label in [(True, "case_insensitive_upper_bound"), (False, "case_sensitive_lower_bound")]:
    orig_n, anon_n, examples = 0, 0, []
    for _, a in adf.iterrows():
        at = anonymize(a["title"], a["ticker"])
        if third_party_hits(a["title"], a["ticker"], ci):
            orig_n += 1
        hits = third_party_hits(at, a["ticker"], ci)
        if hits:
            anon_n += 1
            if len(examples) < 4:
                examples.append({"title": at[:110], "focal": a["ticker"], "third": hits})
    R.setdefault("third_party", {})[label] = {
        "share_original_titles_with_third_party": orig_n / len(adf),
        "share_anonymized_titles_with_third_party": anon_n / len(adf),
        "n_original": orig_n, "n_anonymized": anon_n, "n_total": len(adf),
        "examples": examples}
    print(f"\n=== C2 third-party residual ({label}, EXECUTED alias table) ===")
    print(f"original titles w/ third-party firm: {orig_n}/{len(adf)} ({orig_n/len(adf):.1%})")
    print(f"anonymized titles w/ third-party firm: {anon_n}/{len(adf)} ({anon_n/len(adf):.1%})")
    for e in examples:
        print(f"  [{e['focal']}] {e['title'][:80]}... -> third: {e['third']}")

# focal-firm failure for ticker V (anonymization no-op: 'Visa' survives)
vres = json.load(open(f"{DATA}/v_exclusion.json"))["v_failure"]
R["focal_firm_failure_V"] = {
    "n_v_articles": vres["n_v_articles"],
    "n_still_name_visa": vres["n_anon_noop_still_names_visa"],
    "share_of_341": vres["n_anon_noop_still_names_visa"] / 341,
    "n_visa_bulletin_immigration": vres["n_visa_bulletin_immigration"],
    "n_v_in_rel30_sample": vres["n_v_in_rel30_sample"],
    "illustrative_case": vres["illustrative_case"]}
print(f"\n=== C2b focal-firm failure (ticker V) ===")
print(f"anonymization no-op for V: {vres['n_anon_noop_still_names_visa']}/341 "
      f"({vres['n_anon_noop_still_names_visa']/341:.1%}); immigration pollution: "
      f"{vres['n_visa_bulletin_immigration']}; V in rel30 sample: {vres['n_v_in_rel30_sample']}")

# ================= (B1b) same-session identity power row (audit E4) =================
sc = R["session_confounding"]
ss_id = sc["same_session_identity_effect_anon_minus_named"]
se_id = abs(ss_id["estimate"]) / abs(ss_id["t"])
p_row = {"test": "H2 same-session identity shift (score points)",
         "observed": ss_id["estimate"], "se": float(se_id), "mde80": MDE_MULT * se_id,
         "power_at_observed": power_at(ss_id["estimate"], se_id),
         "n": int(sc["n_articles"])}
R["power"]["rows"].append(p_row)
R["power"]["same_session_identity_row"] = p_row
print(f"\n=== B1b same-session identity power row ===")
print(f"obs={p_row['observed']:.3f} se={p_row['se']:.3f} MDE80={p_row['mde80']:.3f} "
      f"power={p_row['power_at_observed']:.3f}")

json.dump(R, open(f"{DATA}/results_revision.json", "w"), indent=1, default=str)
print("\nsaved data/results_revision.json")
