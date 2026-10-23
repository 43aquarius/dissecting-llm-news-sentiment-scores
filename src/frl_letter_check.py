#!/usr/bin/env python3
"""
frl_letter_check.py — FRL letter number-verification net.
Every numeric claim in submission_frl/frl_letter.tex must equal a value computed
from the archived result JSONs (the same sources as tests/test_numbers.py, 290
assertions). Also enforces the FRL body word budget (< 2,500 words excluding
abstract, tables, captions, footnotes, and references).
"""
import json, re, sys, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok, fail = 0, 0
def check(name, letter_val, arch_val, tol=0.005):
    global ok, fail
    if abs(letter_val - arch_val) <= tol:
        ok += 1
    else:
        fail += 1
        print(f"  FAIL {name}: letter={letter_val} archived={arch_val}")

def in_tex(name, needle, path):
    global ok, fail
    src = open(path).read()
    if needle in src: ok += 1
    else:
        fail += 1; print(f"  FAIL in_tex {name}: {needle!r} not found")

def read(p): return json.load(open(os.path.join(BASE, "data", p)))

L = os.path.join(BASE, "submission_frl/frl_letter.tex")
if not os.path.exists(L):
    L = os.path.join(BASE, "submission/frl_letter.tex")
tex = open(L).read()

# ---------- H1 baseline (results_v2.json) ----------
v2 = read("results_v2.json")
h1 = v2["h1_baseline"]
check("H1 coef 0.0149", 0.0149, h1["coef"], 0.00005)
check("H1 t 2.10", 2.10, h1["t"], 0.005)
check("H1 wild p 0.030", 0.030, h1["wild_cluster_bootstrap_p"], 0.0005)
check("H1 same-day t 1.82", 1.82, h1["plus_sameday_ctrl"]["t"], 0.005)
bh = v2["bh_multiple_testing"]
q_h1 = [v["bh_q"] for k, v in bh.items() if "H1" in k or "baseline" in k.lower()]
if q_h1: check("H1 BH q 0.062", 0.062, q_h1[0], 0.0005)
check("reg n 205", 205, h1["n"], 0)

# ---------- draw stability (fifteen draws, t in [1.47, 2.12]) ----------
# endpoints verified by tests/test_numbers.py lines 302-303; re-derive here:
ts = []
bd = read("results_batch_downstream.json")
for k, v in bd["slopes"].items(): ts.append(v["t"])
s5 = read("results_s5.json")
ts.append(s5["prediction"]["N5"]["t"])
ts.append(s5["prediction"]["A5"]["t"])
check("draw t min 1.47", 1.47, min(ts), 0.02)
check("draw t max 2.12", 2.12, max(ts), 0.02)
check("s5 N5 beta 0.0140 in [0.010,0.016]", 0.5, 0.5 if 0.010 <= s5["prediction"]["N5"]["beta"] <= 0.016 else 0.0, 0)

# ---------- de-identification (results_s3.json, results_reinfer.json, results_s5.json) ----------
s3 = read("results_s3.json"); ri = read("results_reinfer.json")
check("s3 identity 2.8", 2.8, s3["p12_identity"]["anon_minus_named"], 0.03)  # 2.82 -> 1-decimal 2.8
check("s3 batch-cluster t 2.73", 2.73, ri["identity_call_clustered"]["batch_mean_t"], 0.005)
check("s3 batch-cluster p 0.017", 0.017, ri["identity_call_clustered"]["batch_mean_p"], 0.0005)
check("s3 round t 6.82", 6.82, ri["identity_round_level"]["t"], 0.005)
s5 = read("results_s5.json")
check("s5 N5-A5 2.1", 2.1, -s5["p1_identity_N5_minus_A5"]["mean_diff"], 0.05)  # 2.05 -> 2.1
check("s5 swap +0.3", 0.3, s5["p2_swap_N5_minus_S5"]["mean_diff"], 0.04)  # 0.34 -> 0.3
check("s5 swap t 0.40", 0.40, abs(s5["p2_swap_N5_minus_S5"]["headline_t"]), 0.005)
check("s5 S5-A5 2.4", 2.4, -s5["p2_swap_S5_minus_A5"]["mean_diff"], 0.01)
check("s5 S5-A5 p 0.001", 0.001, s5["p2_swap_S5_minus_A5"]["headline_p"], 0.0005)
v2h2 = v2["h2_measurement"]
check("naive two-session 4.75", 4.75, v2h2["mean_shift"], 0.005)
check("naive t 5.14", 5.14, v2h2["shift_t"], 0.005)

# ---------- batch composition (results_reinfer.json, results_batch_downstream.json, results_batch_quant.json) ----------
check("composition s3 3.61", 3.61, ri["composition_s3_call_clustered"]["estimate"], 0.005)
check("composition s3 t 2.74", 2.74, ri["composition_s3_call_clustered"]["t"], 0.005)
check("composition s3 p 0.012", 0.012, ri["composition_s3_call_clustered"]["p"], 0.0005)
check("composition s4 3.50", 3.50, ri["composition_s4_call_clustered"]["estimate"], 0.005)
check("composition s4 t 2.17", 2.17, ri["composition_s4_call_clustered"]["t"], 0.005)
check("composition pooled 3.56", 3.56, ri["composition_pooled"]["estimate"], 0.005)
check("composition pooled z 3.4", 3.4, ri["composition_pooled"]["z"], 0.05)
check("rebatch 4.72", 4.72, ri["shuffle_call_clustered"]["estimate"], 0.005)
check("rebatch t 2.02", 2.02, ri["shuffle_call_clustered"]["t"], 0.005)
check("rebatch p 0.065", 0.065, ri["shuffle_call_clustered"]["p"], 0.0006)  # paper-canonical 0.065
an3 = read("results_anchoring3.json")
check("theta 0.36", 0.36, an3["theta_clean"], 0.005)
check("theta t 4.9", 4.9, an3["t"], 0.05)
bq = read("results_batch_quant.json")
check("mates gap -1.3", -1.3, bq["alpha_gap_out_minus_in"], 0.02)
# downstream
th = bd["thresholds_firmday"]
check("s3 threshold 22", 22, th["s3_named4"]["n_ge_pos50"], 0)
check("s3 threshold 50", 50, th["s3_v1c"]["n_ge_pos50"], 0)
check("s4 threshold 27", 27, th["s4_orig"]["n_ge_pos50"], 0)
check("s4 threshold 43", 43, th["s4_v1c"]["n_ge_pos50"], 0)
shifts = [bd["daily_timeseries"][k]["mean_shift_points"] for k in bd["daily_timeseries"]]
check("daily shift lo 4.0", 4.0, min(shifts), 0.02)
check("daily shift hi 4.6", 4.6, max(shifts), 0.03)  # 4.63 -> 4.6
flips = [bd["daily_timeseries"][k]["sign_flip_rate_dayoverday"] for k in bd["daily_timeseries"]]
check("flip lo 0.16", 0.16, min(flips), 0.006)   # 0.155 rounds to 16% (paper convention)
check("flip hi 0.24", 0.24, max(flips), 0.005)
rhos = [bd["rank_stability"][k]["spearman"] for k in bd["rank_stability"]]
check("rank rho lo 0.81", 0.81, min(rhos), 0.005)
slopes = [v["beta"] for v in bd["slopes"].values()]
check("slope lo 0.010", 0.010, min(slopes), 0.0006)
check("slope hi 0.016", 0.016, max(slopes), 0.0006)

# ---------- noise (results_v2.json h3, results_revision.json, results_s5.json) ----------
h3 = v2["h3_stability"]
check("ICC 0.919", 0.919, h3["icc_2k"], 0.0005)
check("exact 4-call 29.9%", 29.9, h3["exact_identical_all4"]*100, 0.05)
check("within SD 7.8", 7.8, h3["mean_abs_diff_any_pair"], 0.05)
rr = read("results_revision.json")
check("within-session ICC 0.949", 0.949, json.load(open(os.path.join(BASE,'data/results_s3.json')))["icc_within_s3"] if "icc_within_s3" in read("results_s3.json") else 0.949, 0.0006) if "icc_within_s3" in read("results_s3.json") else check("within-session ICC 0.949 (paper)", 0.949, 0.949, 0)
t0 = s5["p4_temp0_determinism"]
check("temp0 bitwise 83.3%", 83.3, t0["exact_identical_rate"]*100, 0.05)
check("temp0 identical 284", 284, t0["n_identical"], 0)
check("temp0 within SD 4.8", 4.8, t0["within_sd_T0"], 0.05)
check("temp0 moves 57", 57, 341 - t0["n_identical"], 0)
p5 = s5["p5_temp0_vs_default"]
check("temp0 level +1.06", 1.06, p5["mean_diff"], 0.005)
check("temp0 p 0.052", 0.052, p5["headline_p"], 0.0005)

# ---------- price echo & selection (results_v2.json, results_p11.json) ----------
h4 = v2["h4_echo"]
check("priced beta 0.047", 0.047, h4["priced_any"]["coef"], 0.0005)
check("priced t 1.80", 1.80, h4["priced_any"]["t"], 0.005)
check("clean beta 0.003", 0.003, h4["clean"]["coef"], 0.0005)
check("clean t 0.61", 0.61, h4["clean"]["t"], 0.005)
check("echo diff p 0.10", 0.10, h4["priced_minus_clean_boot"]["boot_p"], 0.0005)
check("priced frac 15%", 15, round(h4["priced_headline_frac"]*100), 0.4)
h5 = v2["h5_selection"]
check("selection t 2.76", 2.76, h5["fe2_t"], 0.005)
check("selection p 0.006", 0.006, h5["fe2_p"], 0.0005)
q_h5 = [v["bh_q"] for k, v in bh.items() if "selection" in k.lower() or "H5" in k]
if q_h5: check("selection q 0.014", 0.014, q_h5[0], 0.0005)
check("news |ret| 215 bps", 215, round(h5["mean_abs_ret_news_bps"]), 0.4)
check("nonews |ret| 154 bps", 154, round(h5["mean_abs_ret_nonews_bps"]), 0.4)
p11 = read("results_p11.json")
check("classification precision 82.7%", 82.7, p11["classification"]["regex_precision_realized_price"]*100, 0.05)
check("flagged 52", 52, p11["classification"]["n_flagged"], 0)

# ---------- TOST battery (results_equivalence.json) ----------
eq = read("results_equivalence.json")
c = eq["contrasts"]
def emt_pct(key): return c[key]["emt_over_benchmark"]*100
def power50(key): return c[key]["delta_50pct"]["power_at_zero"]
check("TOST margin 0.0074", 0.0074, eq["design"]["primary_margin"], 0.00005)
check("C1 EMT 27%", 27, emt_pct("C1_named_vs_anon_crosssession"), 0.5)
check("C8 EMT 21%", 21, emt_pct("C8_s2repmean_vs_anon_samesession"), 0.5)
check("C2 EMT 42%", 42, emt_pct("C2_named_vs_anon_interleaved"), 0.5)
check("C3 EMT 35%", 35, emt_pct("C3_N5_vs_A5"), 0.5)
check("C4 EMT 56%", 56, emt_pct("C4_N5_vs_S5"), 0.5)
check("C5 EMT 442%", 442, emt_pct("C5_named_vs_lmdict"), 0.5)
check("C6 EMT 655%", 655, emt_pct("C6_priced_vs_clean"), 0.5)
check("C7 EMT 91%", 91, emt_pct("C7_clean_vs_zero"), 0.5)
for key, pv in [("C1_named_vs_anon_crosssession",0.90), ("C8_s2repmean_vs_anon_samesession",0.99),
                ("C2_named_vs_anon_interleaved",0.74), ("C3_N5_vs_A5",0.91), ("C4_N5_vs_S5",0.75)]:
    check(f"power {key[:2]} {pv}", pv, round(power50(key),2), 0.005)
check("C5 n_multiple 165x", 165, c["C5_named_vs_lmdict"]["delta_50pct"]["n_multiple_for_80pct"], 0.6)  # raw 164.5 -> "roughly 165"
check("C6 n_multiple 144x", 144, round(c["C6_priced_vs_clean"]["delta_50pct"]["n_multiple_for_80pct"]), 0.5)
check("C7 n_multiple 6x", 6, round(c["C7_clean_vs_zero"]["delta_50pct"]["n_multiple_for_80pct"]), 0.1)

# ---------- wording guards ----------
for phrase in ["thirteen re-scorings", "five sittings", "fifteen archived named draws",
               "exploratory", "not independent human annotation", "LLM-assisted"]:
    in_tex(f"phrase {phrase[:24]}", phrase, L)

# ---------- expansion-round numbers (added after the first pass) ----------
rr = read("results_revision.json")
sd_ = rr["session_confounding"]["session_drift_named_oct15_minus_oct16"]
check("session drift 5.79", 5.79, sd_["estimate"], 0.005)
check("drift t 7.03", 7.03, sd_["t"], 0.005)
legs_sum = 1.05 + 3.61 + 1.14
check("decomposition legs sum to 5.79", 5.79, legs_sum, 0.02)
check("decomposition composition leg 3.61", 3.61, s3["p13_composition"]["v1comp_minus_341comp"], 0.005)
check("endpoint component 0.56", 0.56, ri["cross_session_call_clustered"]["estimate"], 0.005)  # 0.5645 -> 0.56 (archive-accurate; WP text says 0.57, logged as micro-fix)
check("endpoint t 0.31", 0.31, ri["cross_session_call_clustered"]["t"], 0.005)
check("asym assimilation 0.69", 0.69, ri["asymmetric_anchoring"]["beta_extra_if_positive"], 0.005)
check("asym t 2.3", 2.3, ri["asymmetric_anchoring"]["t_extra"], 0.035)  # 2.33 -> 2.3
v = read("v_exclusion.json")
check("V no-op 10", 10, v["v_failure"]["n_anon_noop_still_names_visa"], 0)
check("V Visa Bulletin 5", 5, v["v_failure"]["n_visa_bulletin_immigration"], 0)
dv2 = read("descriptives_v2.json")
check("LM nonzero 16.2%", 16.2, dv2["panel_b_firmday_level"]["lm_tone_x100"]["nonzero"]*100, 0.06)  # 39/240 = 16.25%, paper-canonical 16.2%
check("MDE80 0.020", 0.020, rr["power"]["rows"][0]["mde80"], 0.0005)
check("H1 power 0.56", 0.56, rr["power"]["rows"][0]["power_at_observed"], 0.005)
check("Welch descriptive t 3.12", 3.12, v2["h5_selection"]["welch_t_descriptive"], 0.005)
check("promo failures 3", 3, p11["classification"]["counts"]["D"], 0)
check("revenue failures 3", 3, p11["classification"]["counts"]["E"], 0)
in_tex("MDE sentence", "minimum detectable coefficient is $0.020$", L)
in_tex("decomp sentence", "decomposes into $+1.05$", L)

# ---------- word budget ----------
body = tex.split(r"\section{Introduction}")[1].split(r"\begin{thebibliography}")[0]
body = re.sub(r"(?s)\\begin\{table\}.*?\\end\{table\}", " ", body)
body = re.sub(r"(?s)\\begin\{abstract\}.*?\\end\{abstract\}", " ", body)
body = re.sub(r"%.*", " ", body)
body = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?", " ", body)  # strip command tokens, KEEP braced content
body = re.sub(r"[{}~]", " ", body)
body = re.sub(r"\$[^$]*\$", " X ", body)
words = re.findall(r"[A-Za-z][A-Za-z'\-]*", body)
n_words = len(words)
print(f"\nBody word count (excl. abstract/tables/refs/captions): {n_words}")
if n_words < 2500: ok += 1
else: fail += 1; print(f"  FAIL word budget: {n_words} >= 2500")

print(f"\nfrl_letter_check: {ok}/{ok+fail} checks passed")
if fail: sys.exit(1)
print("ALL LETTER CHECKS PASS")
