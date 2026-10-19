#!/usr/bin/env python3
"""P1-6 regression test: every key number in the paper must equal a script output.

Guards against transcription errors of class E1-E5 found in the P0 audit
(hand-assembled tables, mixed sample bases, unreproducible cells).

Two layers:
  1. value assertions -- archived JSON outputs contain the published values;
  2. source assertions -- the LaTeX sources contain those same values.

Run: python tests/test_numbers.py   (exit 0 = all pass)
"""
import json
import re
import sys

DATA = "/home/z/my-project/data"
SEC = "/home/z/my-project/paper/sections"

failures = []

def load(name):
    return json.load(open(f"{DATA}/{name}"))

n_checks = [0]

def check(label, got, want, tol=0.0):
    n_checks[0] += 1
    ok = abs(got - want) <= tol if isinstance(got, (int, float)) else got == want
    if not ok:
        failures.append(f"{label}: got {got}, want {want}")
    return ok

def in_tex(label, needle, *files):
    n_checks[0] += 1
    text = ""
    for f in files:
        try:
            text += open(f"{SEC}/{f}").read()
        except FileNotFoundError:
            failures.append(f"{label}: missing file {f}")
            return False
    if needle not in text:
        failures.append(f"{label}: '{needle}' not found in {files}")
        return False
    return True

# ---------------- Table 6 (coverage_table.py) ----------------
cov = load("coverage_table.json")
check("T6 tickers", cov["n_tickers"], 36)
check("T6 articles sum", cov["sum_articles_in_window"], 341)
check("T6 firm-days sum", cov["sum_firm_days_trading"], 240)
check("T6 = regression sample", cov["sum_firm_days_trading"], cov["panel_regression_sample"])
in_tex("T6 note", "coverage\\_table.py", "appendix.tex")

# ---------------- Table 1 (descriptives.py) ----------------
d = load("descriptives_v2.json")
A, B = d["panel_a_article_level"], d["panel_b_firmday_level"]
check("T1 named mean", A["named"]["mean"], 16.88, 0.005)
check("T1 named sd", A["named"]["sd"], 38.97, 0.005)
check("T1 anon mean", A["anon"]["mean"], 12.13, 0.005)
check("T1 anon sd", A["anon"]["sd"], 36.45, 0.005)
check("T1 named nonzero", A["named"]["nonzero"], 0.701, 0.001)
check("T1 lm nonzero", A["lm_tone"]["nonzero"], 0.135, 0.001)
check("T1 relevance mean", A["relevance"]["mean"], 72.0, 0.05)
check("T1 B anon mean", B["anon"]["mean"], 0.0985, 0.0005)
check("T1 B anon sd", B["anon"]["sd"], 0.3377, 0.0005)
check("T1 B anon nonzero", B["anon"]["nonzero"], 0.625, 0.001)
check("T1 B fwd n", B["ret_fwd1_bps"]["n"], 234)
check("T1 B fwd mean bps", B["ret_fwd1_bps"]["mean"], 22.0, 0.05)
check("T1 exact_all4", d["exact_all4"], 0.299, 0.0005)
in_tex("T1 generated", "descriptives.py", "data.tex")
in_tex("T1 SD contrast", "39.0 vs.\\ 36.4", "data.tex")
in_tex("29.9 in data", "29.9\\%", "data.tex")

# ---------------- results_v2.json (analysis_v2.py) ----------------
r2 = load("results_v2.json")
check("H1 beta", r2["h1_baseline"]["coef"], 0.0149, 0.00005)
check("H1 t", r2["h1_baseline"]["t"], 2.10, 0.005)
check("H1 wild p", r2["h1_baseline"]["wild_cluster_bootstrap_p"], 0.030, 0.0005)
check("H1 q", r2["bh_multiple_testing"]["H1 named fwd1"]["bh_q"], 0.062, 0.0005)
check("H2 anon beta", r2["h2_prediction"]["anon"]["coef"], 0.0144, 0.00005)
check("H2 anon t", r2["h2_prediction"]["anon"]["t"], 1.78, 0.005)
check("H3 ICC", r2["h3_stability"]["icc_2k"], 0.919, 0.0005)
check("H4 priced beta", r2["h4_echo"]["priced_any"]["coef"], 0.047, 0.0005)
check("H4 clean t", r2["h4_echo"]["clean"]["t"], 0.61, 0.005)
check("H4 diff p", r2["h4_echo"]["priced_minus_clean_boot"]["boot_p"], 0.100, 0.0005)
check("H4 diff B", r2["h4_echo"]["priced_minus_clean_boot"]["B"], 9943, 60)
check("H4 q", r2["bh_multiple_testing"]["H4 priced-vs-clean difference"]["bh_q"], 0.140, 0.0005)
h5 = r2["h5_selection"]
check("H5 FE t", h5["fe2_t"], 2.76, 0.005)
check("H5 FE p", h5["fe2_p"], 0.0059, 0.0005)
check("H5 firmFE t", h5["firmFE_daycluster_t"], 2.49, 0.005)
check("H5 boot p floor", h5["daycluster_boot_p"], 0.0002, 0.00005)
check("H5 gap bps", h5["mean_abs_ret_news_bps"] - h5["mean_abs_ret_nonews_bps"], 61.05, 0.05)
check("H5 q", r2["bh_multiple_testing"]["H5 coverage selection"]["bh_q"], 0.0137, 0.0005)
in_tex("T2 anon cell", "0.0144", "results.tex")
in_tex("T3 H4 row", "0.100", "results.tex")
in_tex("T8 H5 row", "0.0059 & 0.0137", "results.tex")
in_tex("H5 FE in text", "$t=2.76$", "results.tex")

# ---------------- results_revision.json (revision_power.py) ----------------
rr = load("results_revision.json")
sc = rr["session_confounding"]
check("session drift", sc["session_drift_named_oct15_minus_oct16"]["estimate"], 5.79, 0.005)
check("same-session identity", sc["same_session_identity_effect_anon_minus_named"]["estimate"], 1.041, 0.005)
check("published shift", sc["published_shift_named_minus_anon"], 4.75, 0.005)
ss = rr["same_session_prediction"]
check("ss beta anon", ss["beta_anon_oct16"], 0.0144, 0.00005)
check("ss beta repmean", ss["beta_named_oct16_repmean"], 0.0147, 0.00005)
check("ss diff p", ss["boot_p"], 0.905, 0.0005)
pw = {r["test"]: r for r in rr["power"]["rows"]}
check("power H1", pw["H1 baseline next-day coefficient (named)"]["power_at_observed"], 0.557, 0.005)
check("power H5", pw["H5 coverage selection (|ret| gap, bps; firm+day FE)"]["power_at_observed"], 0.787, 0.005)
check("power ss identity", pw["H2 same-session identity shift (score points)"]["power_at_observed"], 0.359, 0.005)
in_tex("T7 power ss row", "1.83 & 0.36", "appendix.tex")
in_tex("T7 H5 row", "0.79", "appendix.tex")

# ---------------- v_exclusion.json ----------------
ve = load("v_exclusion.json")
check("V no-op count", ve["v_failure"]["n_anon_noop_still_names_visa"], 10)
check("V bulletin count", ve["v_failure"]["n_visa_bulletin_immigration"], 5)
check("V in rel30", ve["v_failure"]["n_v_in_rel30_sample"], 5)
check("excl-V shift", ve["robustness"]["excluding_V"]["same_session_identity_repm_minus_anon"]["estimate"], -1.294, 0.005)
check("excl-V p", ve["robustness"]["excluding_V"]["same_session_identity_repm_minus_anon"]["p"], 0.041, 0.0005)
in_tex("V disclosure", "no-op", "appendix.tex")
in_tex("excl-V row T3", "-1.29", "results.tex")

# ---------------- results_s3.json (session-3 interleaved experiment, v5) ----------------
s3 = load("results_s3.json")
check("s3 identity anon-named", s3["p12_identity"]["anon_minus_named"], 2.8226, 0.005)
check("s3 identity t", s3["p12_identity"]["t"], 4.278, 0.02)
check("s3 identity wilcoxon p", s3["p12_identity"]["wilcoxon_p"], 1.64e-06, 2e-06)
check("s3 identity V-excl", s3["p12_identity"]["v_excluded"]["anon_minus_named"], 3.134, 0.005)
check("s3 identity V-excl t", s3["p12_identity"]["v_excluded"]["t"], 4.882, 0.02)
check("s3 exact paired", s3["p12_identity"]["exact_match_paired_calls"], 0.4853, 0.005)
comp = s3["p13_composition"]
check("s3 composition effect", comp["v1comp_minus_341comp"], 3.614, 0.005)
check("s3 composition t", comp["t"], 4.548, 0.02)
tr = s3["trajectory"]
check("traj s1", tr["s1_v1_oct15"], 16.877, 0.005)
check("traj s2 repm", tr["s2_repm_oct16"], 11.085, 0.005)
check("traj s3 named4", tr["s3_named4_oct18"], 12.221, 0.005)
check("traj s3 v1comp", tr["s3_v1comp_oct18"], 15.836, 0.005)
# exact additivity: total = leg1 + composition + leg2
leg1 = tr["s1_v1_oct15"] - tr["s3_v1comp_oct18"]
leg2 = tr["s3_named4_oct18"] - tr["s2_repm_oct16"]
total = tr["drift_s1_to_s2"]
check("additivity total", leg1 + comp["v1comp_minus_341comp"] + leg2, total, 0.001)
rel = s3["reliability"]
check("s3 ICC named", rel["icc_s3_named_4draws"], 0.9491, 0.003)
check("s3 within-SD", rel["within_sd_s3_named"], 7.188, 0.02)
pr = s3["prediction"]
check("s3 pred named coef", pr["s3_named"]["coef"], 0.01460, 0.0001)
check("s3 pred named t", pr["s3_named"]["t"], 1.674, 0.02)
check("s3 pred anon coef", pr["s3_anon"]["coef"], 0.01326, 0.0001)
check("s3 pred anon t", pr["s3_anon"]["t"], 1.884, 0.02)
check("s3 pred diff p", pr["diff_named_minus_anon"]["boot_p"], 0.622, 0.005)
stab = s3["h1_stability_across_draws"]
ts = [v["t"] for v in stab.values()]
bs = [v["coef"] for v in stab.values()]
check("h1 stability t min", min(ts), 1.47, 0.03)
check("h1 stability t max", max(ts), 2.12, 0.03)
check("h1 stability beta min", min(bs), 0.0116, 0.0005)
check("h1 stability beta max", max(bs), 0.0161, 0.0005)
in_tex("T3 s3 identity row", "-2.82", "results.tex")
in_tex("T3 composition row", "3.61", "results.tex")
in_tex("App G present", "The Interleaved Replication Session", "appendix.tex")
in_tex("App H present", "Classification Audit of the Price-Language Flag", "appendix.tex")
in_tex("comp table total", "+5.79", "appendix.tex")

# ---------------- results_p11.json (classification audit, v5) ----------------
p11 = load("results_p11.json")
cl = p11["classification"]
check("cls n flagged", cl["n_flagged"], 52, 0)
check("cls P count", cl["counts"]["P"], 43, 0)
check("cls precision", cl["regex_precision_realized_price"], 0.827, 0.005)
sp = p11["splits"]
check("split regex beta", sp["regex_priced"]["coef"], 0.0470, 0.0005)
check("split strictP beta", sp["strictP"]["coef"], 0.0475, 0.0005)
check("split strictP t", sp["strictP"]["t"], 1.61, 0.02)
check("split strictP n", sp["strictP"]["n"], 33, 0)
cd = p11["category_descriptives"]
check("strictP |ret| bps", cd["strictP"]["mean_abs_sameday_ret_bps"], 361, 3)
check("clean |ret| bps", cd["clean"]["mean_abs_sameday_ret_bps"], 178, 3)
check("flagged_nonP |ret| bps", cd["flagged_nonP"]["mean_abs_sameday_ret_bps"], 120, 3)
dm = p11["dominance"]
check("dom max share", dm["max_share_one_company"], 0.09, 0.01)
check("dom loco sign flips", dm["loco_sign_flip_frac"], 0.0, 0.0)
check("dom jko sign flips", dm["jko_sign_flip_frac"], 0.0, 0.0)
in_tex("cls precision in tex", "82.7", "results.tex")
in_tex("strictP beta in tex", "0.0475", "results.tex")

# ---------------- results_s4.json + results_reinfer.json (mechanism round, v5.1) ----------------
s4 = load("results_s4.json")
check("s4 composition est", s4["composition_s4"]["v1comp_minus_341"], 3.504, 0.005)
check("s4 composition t", s4["composition_s4"]["t"], 3.51, 0.03)
check("s4 rebatch est", s4["rebatch_s4"]["shuffled_minus_original"], 4.721, 0.01)
check("s4 rebatch t", s4["rebatch_s4"]["t"], 4.48, 0.03)
check("s4 cross-session drift", s4["cross_session_341"]["s4_minus_s3"], 0.565, 0.005)
grid = s4["grid"]
check("s4 542 level", grid["s4_542"], 16.29, 0.02)
check("s4 341 level", grid["s4_341"], 12.79, 0.02)
check("s4 shuf level", grid["s4_shuf"], 17.51, 0.02)
ri = load("results_reinfer.json")
check("identity batch-clustered t", ri["identity_call_clustered"]["batch_mean_t"], 2.73, 0.05)
check("identity round-level t", ri["identity_round_level"]["t"], 6.82, 0.1)
check("comp s3 clustered t", ri["composition_s3_call_clustered"]["t"], 2.74, 0.05)
check("comp s4 clustered t", ri["composition_s4_call_clustered"]["t"], 2.17, 0.05)
check("comp pooled z", ri["composition_pooled"]["z"], 3.41, 0.05)
check("shuffle clustered t", ri["shuffle_call_clustered"]["t"], 2.02, 0.05)
check("V-excl clustered t", ri["identity_v_excl_call_clustered"]["t"], 4.83, 0.05)
vd = ri["variance_decomposition_named_only"]
check("mood share", vd["mood_share"], 0.133, 0.01)
check("mood sd", vd["mood_sd"], 2.62, 0.1)
check("idio sd", vd["idio_sd"], 6.66, 0.1)
a3 = load("results_anchoring3.json")
check("clean anchoring theta", a3["theta_clean"], 0.3587, 0.005)
check("anchoring t", a3["t"], 4.93, 0.1)
check("asym extra", ri["asymmetric_anchoring"]["beta_extra_if_positive"], 0.687, 0.01)
check("asym t", ri["asymmetric_anchoring"]["t_extra"], 2.33, 0.05)
in_tex("T3 clustered p", "0.017", "results.tex")
in_tex("T3 s4 row", "3.50", "results.tex")
in_tex("mech table theta", "0.36", "appendix.tex")
in_tex("mood share tex", "13\\%", "results.tex")


# ---------------- V6 additions: table-6 rendering, unified numbers, downstream, revision-log net ----------------
import pandas as pd
import numpy as np

# (a) coverage table RENDERED cells must show 36 unique firms with matching sums
tex6 = open(f"{SEC}/gen/table_coverage.tex").read()
cells = re.findall(r"([A-Z]{1,5}) & (\d+) & (\d+) ", tex6)
tick6 = [c[0] for c in cells]
check("T6 rendered unique tickers", len(set(tick6)), 36)
check("T6 rendered ticker count", len(tick6), 36)
check("T6 rendered articles sum", sum(int(c[1]) for c in cells), 341)
check("T6 rendered firm-days sum", sum(int(c[2]) for c in cells), 240)

# (b) dictionary nonzero unified at 39/240 (16.2%)
panel = pd.read_csv(f"{DATA}/panel.csv")
sub = panel.dropna(subset=["llm_sent_rel"])
check("dict nonzero count", int((sub["lm_tone"] != 0).sum()), 39)
check("dict nonzero share pct", round(100 * (sub["lm_tone"] != 0).mean(), 1), 16.2)
in_tex("dict text count", r"39 of the 240 analysis firm-days (16.2\%)", "data.tex")
in_tex("dict table 16.2", r"16.2\%", "gen/table_desc.tex")

# (c) H5 regression N = 2,628 = 2,664 - 36 first-day cells
rv2 = load("results_v2.json")
check("H5 n panel firmdays", rv2["h5_selection"]["n_panel_firmdays"], 2628)
check("H5 panel arithmetic", len(panel) - int(panel["ret"].isna().sum()), 2628)
in_tex("H5 N explained", "2,628 firm-days with a non-missing same-day return", "results.tex")

# (d) clean-vs-priced and clean-vs-baseline ratio language
in_tex("ratio to price-language", "one-fourteenth of the price-language coefficient", "results.tex")
in_tex("ratio to baseline", "one-fifth of the baseline ($0.22$)", "results.tex")
check("priced coef", rv2["h4_echo"]["priced_any"]["coef"], 0.0470, 0.0005)

# (e) draw-stability range over 14 named draws
import statsmodels.formula.api as smf
arts = json.load(open(f"{DATA}/news_scored.json"))
inwin0 = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin0]
def _load_scores(path):
    d = json.load(open(path))
    return {u: d[u]["sentiment"] for u in url_order if u in d}
_draws = {"v1": _load_scores(f"{DATA}/llm_scores.json")}
for _k in ("rep1", "rep2", "rep3"):
    _draws[_k] = _load_scores(f"{DATA}/llm_scores_{_k}.json")
for _r in (1, 2, 3, 4):
    _draws[f"s3n{_r}"] = _load_scores(f"{DATA}/llm_scores_s3_named_r{_r}.json")
_draws["s3v1c"] = _load_scores(f"{DATA}/llm_scores_s3_v1comp.json")
_draws["s4o"] = _load_scores(f"{DATA}/llm_scores_s4_orig.json")
_draws["s4v"] = _load_scores(f"{DATA}/llm_scores_s4_v1comp.json")
_draws["s4s"] = _load_scores(f"{DATA}/llm_scores_s4_shuf.json")
_draws["s2m"] = {u: float(np.mean([_draws[k][u] for k in ("rep1", "rep2", "rep3")])) for u in url_order}
_draws["s3m"] = {u: float(np.mean([_draws[f"s3n{_r}"][u] for _r in (1, 2, 3, 4)])) for u in url_order}
pan2 = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
pan2["date_str"] = pan2["date"].dt.strftime("%Y-%m-%d")
pan2 = pan2.sort_values(["ticker", "date"])
pan2["ret_fwd1"] = pan2.groupby("ticker")["ret"].shift(-1)
_rel = {u: json.load(open(f"{DATA}/llm_scores.json")).get(u, {}).get("relevance") for u in url_order}
_hi = pd.DataFrame([{"ticker": a["ticker"], "date": a["date_iso"], "relevance": _rel.get(u), "url": u}
                    for a, u in zip(inwin0, url_order)])
_hi = _hi[_hi["relevance"] >= 30].copy()
_betas, _ts = [], []
for _n, _src in _draws.items():
    _h = _hi.assign(sent=_hi["url"].map(_src) / 100.0)
    _agg = _h.groupby(["ticker", "date"]).agg(sent=("sent", "mean")).reset_index()
    _agg["date"] = pd.to_datetime(_agg["date"])
    _pp = pan2.merge(_agg, on=["ticker", "date"], how="left")
    _c = _pp[_pp["sent"].notna()].drop_duplicates(subset=["ticker", "date_str"])
    _c = _c.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
    _fc = pd.factorize(_c["ticker"])[0]; _dc = pd.factorize(_c["date_str"])[0]
    _m = smf.ols("ret_fwd1 ~ sent + ret_lag1 + vol_21 + mkt_ew", data=_c).fit(
        cov_type="cluster", cov_kwds={"groups": np.column_stack([_fc, _dc])})
    _betas.append(_m.params["sent"]); _ts.append(_m.tvalues["sent"])
check("n draws", len(_betas), 14)
check("draw beta min", min(_betas), 0.0104, 0.0005)
check("draw beta max", max(_betas), 0.0161, 0.0005)
check("draw t min", min(_ts), 1.47, 0.02)
check("draw t max", max(_ts), 2.12, 0.02)
in_tex("draw range tex", "[0.0104,", "results.tex")

# (f) batch-composition downstream consequences
bd = load("results_batch_downstream.json")
check("downstream slope diffs all ns (min p)", min(d["p"] for d in bd["slope_differences"].values()), 0.93, 0.005)
check("threshold s3 341comp", bd["thresholds_firmday"]["s3_named4"]["n_ge_pos50"], 22)
check("threshold s3 542comp", bd["thresholds_firmday"]["s3_v1c"]["n_ge_pos50"], 50)
check("threshold s4 341comp", bd["thresholds_firmday"]["s4_orig"]["n_ge_pos50"], 27)
check("threshold s4 542comp", bd["thresholds_firmday"]["s4_v1c"]["n_ge_pos50"], 43)
check("flip s3", bd["daily_timeseries"]["s3_v1c_vs_s3_named4"]["sign_flip_rate_dayoverday"], 0.16, 0.01)
check("flip s4", bd["daily_timeseries"]["s4_v1c_vs_s4_orig"]["sign_flip_rate_dayoverday"], 0.17, 0.01)
check("flip rebatch", bd["daily_timeseries"]["s4_shuf_vs_s4_orig"]["sign_flip_rate_dayoverday"], 0.24, 0.01)
check("rank rho s3", bd["rank_stability"]["s3_v1c_vs_s3_named4"]["spearman"], 0.914, 0.005)
check("rank rho s4", bd["rank_stability"]["s4_v1c_vs_s4_orig"]["spearman"], 0.862, 0.005)
check("rank rho rebatch", bd["rank_stability"]["s4_shuf_vs_s4_orig"]["spearman"], 0.807, 0.005)
in_tex("downstream table", "batch\\_downstream.py", "appendix.tex")
in_tex("threshold doubling text", "22 to 50 firm-days in session 3; 27 to 43 in session 4", "appendix.tex")

# (g) revision-log language must be gone; author block must be human
_all_tex = "".join(open(f"{SEC}/{f}").read() for f in
                   ["intro.tex", "litreview.tex", "theory.tex", "data.tex", "results.tex",
                    "robustness.tex", "discussion.tex", "conclusion.tex", "appendix.tex",
                    "titleblock.tex"])
for _bad in ["earlier draft", "earlier-draft", "we retract", "Revision note",
             "problem list", "v2 draft", "v4 inference", "Z.ai Research"]:
    in_tex(f"no revision-log phrase: {_bad!r}", "\00" if False else _bad, "titleblock.tex") if False else None
    n_checks[0] += 1
    if _bad in _all_tex:
        failures.append(f"forbidden phrase present: {_bad!r}")
in_tex("author present", "Chang Tan", "titleblock.tex")
in_tex("affiliation present", "Dalian University of Technology", "titleblock.tex")
in_tex("ai disclosure present", "Generative-AI use", "titleblock.tex")

# (h) abstract at most 200 words
_m = re.search(r"\\textbf\{Abstract\.\}(.*?)\\par", _all_tex, re.S)
if _m:
    _t = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", _m.group(1))
    _t = re.sub(r"\\[a-zA-Z]+", " ", _t).replace("~---", " ").replace("---", " ").replace("~", " ")
    _t = re.sub(r"\$[^$]*\$", "X", _t)
    _n_words = len([w for w in re.split(r"\s+", _t) if re.search(r"[A-Za-z0-9]", w)])
    n_checks[0] += 1
    if _n_words > 200:
        failures.append(f"abstract too long: {_n_words} words (limit 200)")
else:
    n_checks[0] += 1
    failures.append("abstract not found in titleblock.tex")

# (i) references updated
_refs = open(f"{SEC}/references.tex").read()
n_checks[0] += 1
if "officioso" in _refs:
    failures.append("unverifiable reference officioso still present")
for _need in ["kirtac2024", "lin2024batch", "liu2024lost", "zheng2024", "Y. Tang, and M. Zhu",
              "Journal of Financial Economics} 184, 104335"]:
    in_tex(f"reference present: {_need}", _need, "references.tex")

# (j) session-5 artifacts (guard: only checked once collection is complete)
_s5_files = ["llm_scores_s5_named.json", "llm_scores_s5_anonv2.json", "llm_scores_s5_swap.json",
             "llm_scores_s5_placeholder.json", "llm_scores_s5_t0a.json", "llm_scores_s5_t0b.json"]
_counts = {f: len(load(f)) for f in _s5_files}
if all(c == 341 for c in _counts.values()):
    for f, c in _counts.items():
        check(f"s5 complete {f}", c, 341)
else:
    print(f"NOTE: session-5 collection in progress ({_counts}); value checks deferred.")

# (k) session-5 pre-registered results (analysis_v5.py, seed 20261019)
if all(c == 341 for c in _counts.values()):
    s5 = load("results_s5.json")
    check("s5 P1 de-id N5-A5", s5["p1_identity_N5_minus_A5"]["mean_diff"], -2.05, 0.005)
    check("s5 P1 headline t", s5["p1_identity_N5_minus_A5"]["headline_t"], -2.84, 0.01)
    check("s5 P1 cluster p", s5["p1_identity_N5_minus_A5"]["cluster_p"], 0.175, 0.005)
    check("s5 P1 excl V", s5["p1_identity_excl_V"]["mean_diff"], -2.15, 0.005)
    check("s5 P2 swap N5-S5", s5["p2_swap_N5_minus_S5"]["mean_diff"], 0.34, 0.005)
    check("s5 P2 swap cluster p", s5["p2_swap_N5_minus_S5"]["cluster_p"], 0.857, 0.005)
    check("s5 P2 S5-A5", s5["p2_swap_S5_minus_A5"]["mean_diff"], -2.39, 0.005)
    check("s5 P2 S5-A5 headline p", s5["p2_swap_S5_minus_A5"]["headline_p"], 0.0012, 0.0005)
    check("s5 P3 prefix", s5["p3_prefix_P5_minus_A5"]["mean_diff"], 0.13, 0.005)
    check("s5 P4 identical rate", s5["p4_temp0_determinism"]["exact_identical_rate"], 284 / 341, 0.001)
    check("s5 P4 within sd", s5["p4_temp0_determinism"]["within_sd_T0"], 4.84, 0.01)
    check("s5 P5 level shift", s5["p5_temp0_vs_default"]["mean_diff"], 1.06, 0.005)
    check("s5 pred beta N5", s5["prediction"]["N5"]["beta"], 0.0140, 0.0005)
    check("s5 pred beta A5", s5["prediction"]["A5"]["beta"], 0.0158, 0.0005)
    check("s5 pred beta S5", s5["prediction"]["S5"]["beta"], 0.0179, 0.0005)
    check("s5 pred diff N5-A5 p", s5["prediction_diffs"]["N5_minus_A5"]["p"], 0.929, 0.005)
    check("s5 pred diff N5-S5 p", s5["prediction_diffs"]["N5_minus_S5"]["p"], 0.917, 0.005)
    in_tex("s5 results in paper", "de-identification", "results.tex")
    in_tex("s5 swap number", "0.34", "results.tex")
    in_tex("s5 temp0 rate", "83.3\\%", "results.tex")
    in_tex("s5 appendix section", "Session-5 Controls: Archived Design Document and Results", "appendix.tex")
    in_tex("s5 model tag", "analysis\\_v5.py", "appendix.tex")
    # swap control re-attribution must be stated in the abstract-level documents
    in_tex("s5 swap in intro", "swap control", "intro.tex")

# (l) batch-mechanism quantification (batch_mechanism_quant.py)
if all(c == 341 for c in _counts.values()):
    bq = load("results_batch_quant.json")
    check("mech theta full mates", bq["theta_full_mates"], 0.381, 0.005)
    check("mech alpha out mean", bq["alpha_out_mean"], 12.60, 0.05)
    check("mech alpha in mean", bq["alpha_in_mean"], 13.91, 0.05)
    check("mech alpha gap", bq["alpha_gap_out_minus_in"], -1.32, 0.05)
    check("mech pred composition shift", bq["pred_composition_theta_full"], 0.039, 0.005)
    check("mech gap needed", bq["gap_needed_full_explanation"], 30.1, 0.5)
    check("mech share out mates", bq["share_out_mates_mean"], 0.31, 0.01)
    check("mech rebatch identity zero", bq["pred_rebatch_theta_full"], 0.0, 0.001)
    in_tex("mech quant in intro", "quantifiably explains only about 1\\%", "intro.tex")
    in_tex("mech pred shift in results", "0.04", "results.tex")
    in_tex("mech table rows", "Level shift predicted by \\emph{linear} anchoring, composition contrast", "appendix.tex")

# (m) title, channel naming, and new forbidden phrases
in_tex("title de-identification", "De-Identification, Batch Composition", "titleblock.tex")
for _bad in ["pessimism prior", "make no attempt to hide", "committed, in sequence",
             "got both wrong", "no human labels existed", "Pre-Registered Control Session",
             "ten times across", "Identity Priors, Batch Composition"]:
    n_checks[0] += 1
    if _bad in _all_tex:
        failures.append(f"forbidden phrase present: {_bad!r}")
in_tex("thirteen passes intro", "thirteen independent passes across five sittings", "intro.tex")
in_tex("fifteen draws robust", "fifteen archived named draws", "robustness.tex")
n_checks[0] += 1
if "fourteen archived" in _all_tex or "twelve independent passes" in _all_tex:
    failures.append("stale draw count (fourteen archived / twelve independent passes) still present")
in_tex("checklist appendix present", "Minimal Viable Audit Protocol", "appendix.tex")
in_tex("downstream figure present", "fig_downstream.png", "appendix.tex")

# ---------------- report ----------------
n_total = n_checks[0]
print(f"test_numbers.py: {n_total - len(failures)}/{n_total} checks passed")
if failures:
    print("\nFAILURES:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("ALL REGRESSION CHECKS PASS")
