#!/usr/bin/env python3
"""Layer-2 analyses (user directive, 2026-10-25):

(1) LEVEL equivalence (TOST) for the session-5 swap/prefix controls, in score
    points -- the v6.2 TOST battery covered only the prediction-layer
    coefficients. Margin anchored to the 2-3 point placeholder-rewrite effect:
    delta_level = 1.25 points (half of the 2.5-point midpoint), pre-fixed here
    before inspection; the minimum passing margin (EMT) is reported
    margin-free alongside.
(2) ECONOMICS-anchored margin for the prediction-layer TOST battery:
    delta_econ = 10 bps of next-day response per one-SD sentiment shock
    (fixed round number ~ 1/5 of the benchmark central 1-SD response of
    53.7 bps; does not depend on the unstable benchmark coefficient anchor).
    Re-evaluates the eight archived contrasts at delta_econ and reports EMT
    in bps.

Conservative inference mirrors the paper's standard: batch-call-clustered
(14 clusters for session-5 level contrasts), cluster bootstrap B=9999,
seed 20261025. Outputs: data/results_level_tost.json.
"""
import json
import math
import random
import statistics as st

SEED = 20261025
B = 9999
DELTA_LEVEL = 1.25          # points, pre-fixed
Z90 = 1.6448536269514722     # one-sided 5% (TOST convention: 90% CI)

DATA = "/home/z/my-project/data"

# ---------- load session-5 score files ----------
def load(name):
    with open(f"{DATA}/{name}") as f:
        return json.load(f)

scored = load("news_scored.json")
inwin = [a for a in scored if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
assert len(inwin) == 341, f"expected 341 in-window, got {len(inwin)}"
urls = [a["url"] for a in inwin]
tickers = [a["ticker"] for a in inwin]
BATCH = 25
batch_of = {u: i // BATCH for i, u in enumerate(urls)}

n5 = load("llm_scores_s5_named.json")
a5 = load("llm_scores_s5_anonv2.json")
s5 = load("llm_scores_s5_swap.json")
p5 = load("llm_scores_s5_placeholder.json")
for nm, d in [("N5", n5), ("A5", a5), ("S5", s5), ("P5", p5)]:
    missing = [u for u in urls if u not in d]
    assert not missing, f"{nm} missing {len(missing)} urls"

def diffs(x, y):
    """paired d = x - y per headline, in corpus order"""
    return [x[u]["sentiment"] - y[u]["sentiment"] for u in urls]

CONTRASTS = {
    "L1_named_minus_swapped":   diffs(n5, s5),
    "L2_named_minus_prefixed": diffs(n5, p5),
    "L3_prefixed_minus_anonv2": diffs(p5, a5),
    "L4_swapped_minus_anonv2": diffs(s5, a5),
    "L5_named_minus_anonv2":   diffs(n5, a5),   # the de-identification effect itself
}

# ---------- clustered inference helpers ----------
def cluster_se(d, batches):
    """cluster-robust SE of the mean, clusters = batch calls (equal-n approx ok)"""
    m = sum(d) / len(d)
    gs = {}
    for v, b in zip(d, batches):
        gs.setdefault(b, []).append(v)
    G = len(gs)
    ss = 0.0
    for b, vals in gs.items():
        s_b = sum(vals) - len(vals) * m
        ss += s_b * s_b
    return math.sqrt(ss / (len(d) ** 2) * G / (G - 1)), G

def cluster_boot_ci90(d, batches, seed, B=B):
    rng = random.Random(seed)
    bs = sorted(set(batches))
    means = []
    for _ in range(B):
        pick = [rng.choice(bs) for _ in bs]
        dd = []
        for b in pick:
            dd.extend(dv for dv, bb in zip(d, batches) if bb == b)
        means.append(sum(dd) / len(dd))
    means.sort()
    lo = means[int(0.05 * B)]
    hi = means[min(B - 1, int(0.95 * B) + 1)]
    return lo, hi

def tost_normal(dbar, se, delta):
    t1 = (dbar + delta) / se   # H1: d <= -delta
    t2 = (delta - dbar) / se   # H1: d >= +delta
    from math import erf, sqrt
    def pnorm(t):
        return 0.5 * (1 + erf(t / sqrt(2)))
    p1 = 1 - pnorm(t1)
    p2 = 1 - pnorm(t2)
    return max(p1, p2)

def power_tost(delta, se):
    """TOST power under true mean 0 at one-sided 5%: rejection region is
    (-delta+z*SE, delta-z*SE); empty (power 0) when delta/se <= 2z."""
    from math import erf, sqrt
    def phi(z):
        return 0.5 * (1 + erf(z / sqrt(2)))
    x = delta / se - Z90
    if x <= 0:
        return 0.0
    return max(0.0, 2 * phi(x) - 1)

def n_mult_for_power(delta, se, target=0.8):
    """sample multiplier needed for TOST power `target` at margin delta
    (SE scales as 1/sqrt(n))."""
    from math import sqrt
    from statistics import NormalDist
    nd = NormalDist()
    z_t = nd.inv_cdf(0.5 + target / 2)
    se_needed = delta / (z_t + Z90)
    return (se / se_needed) ** 2 if se_needed > 0 else float('inf')

out = {"design": {
        "script": "level_tost_and_margins.py", "seed": SEED, "B": B,
        "n_headlines": 341, "clusters": 14,
        "delta_level_points": DELTA_LEVEL,
        "margin_rationale": "half the 2.5-point midpoint of the 2-3 point placeholder-rewrite (de-identification) effect family; pre-fixed before inspection",
        "inference": "headline paired t + batch-call-clustered SE (14 clusters) + cluster bootstrap 90% CI",
       },
       "level_contrasts": {}}

batches = [batch_of[u] for u in urls]
for name, d in CONTRASTS.items():
    dbar = sum(d) / len(d)
    se_cl, G = cluster_se(d, batches)
    sd = st.pstdev(d)
    se_hl = sd / math.sqrt(len(d))
    lo, hi = cluster_boot_ci90(d, batches, SEED)
    emt = max(abs(lo), abs(hi))
    t_hl = dbar / se_hl
    # headline-level t-based 90% CI (n=341, t_.95,340 = 1.6495)
    T = 1.6495
    lo_hl, hi_hl = dbar - T * se_hl, dbar + T * se_hl
    emt_hl = max(abs(lo_hl), abs(hi_hl))
    out["level_contrasts"][name] = {
        "mean_diff": round(dbar, 4),
        "sd_diff": round(sd, 4),
        "t_headline": round(t_hl, 3),
        "se_cluster": round(se_cl, 4),
        "t_cluster": round(dbar / se_cl, 3),
        "ci90_boot": [round(lo, 4), round(hi, 4)],
        "EMT_points_cluster": round(emt, 4),
        "ci90_headline": [round(lo_hl, 4), round(hi_hl, 4)],
        "EMT_points_headline": round(emt_hl, 4),
        "pass_delta_level_cluster": bool(lo >= -DELTA_LEVEL and hi <= DELTA_LEVEL),
        "pass_delta_level_headline": bool(lo_hl >= -DELTA_LEVEL and hi_hl <= DELTA_LEVEL),
        "tost_p_cluster": round(tost_normal(dbar, se_cl, DELTA_LEVEL), 4),
        "power_at_delta_cluster": round(power_tost(DELTA_LEVEL, se_cl), 3),
        "power_at_delta_headline": round(power_tost(DELTA_LEVEL, se_hl), 3),
        "n_mult_for_power80_cluster": round(n_mult_for_power(DELTA_LEVEL, se_cl), 1),
        "n_mult_for_power80_headline": round(n_mult_for_power(DELTA_LEVEL, se_hl), 1),
        "as_pct_of_placeholder": round(abs(dbar) / 2.5, 3),
    }

# ---------- (2) economics margin on the prediction-layer battery ----------
eq = load("results_equivalence.json")
bps_per_coef = eq["bps_translation"]["benchmark_response_per_sd_bps"] / eq["design"]["benchmark_beta_named"]
DELTA_ECON_BPS = 10.0
delta_econ_coef = DELTA_ECON_BPS / bps_per_coef
res = {"delta_econ_bps_per_sd": DELTA_ECON_BPS,
       "delta_econ_coef": round(delta_econ_coef, 6),
       "bps_per_coef_unit_per_sd": round(bps_per_coef, 2),
       "rationale": "10 bps of next-day response per 1-SD sentiment shock: round economic threshold, ~1/5 of the benchmark central 1-SD response (53.7 bps), anchor-independent of the unstable benchmark t-statistic",
       "contrasts": {}}
for cname, c in eq["contrasts"].items():
    lo, hi = c["ci90"]
    emt_coef = max(abs(lo), abs(hi))
    emt_bps = emt_coef * bps_per_coef
    # approximate SE from CI90 width / (2*1.645) for power calc
    se = (hi - lo) / (2 * Z90)
    res["contrasts"][cname] = {
        "ci90_coef": c["ci90"],
        "EMT_bps_per_sd": round(emt_bps, 2),
        "EMT_pct_of_benchmark": round(emt_coef / eq["design"]["benchmark_beta_named"], 4),
        "pass_delta_econ": bool(lo >= -delta_econ_coef and hi <= delta_econ_coef),
        "pass_delta_star_half_benchmark": bool(lo >= -eq["design"]["primary_margin"] and hi <= eq["design"]["primary_margin"]),
        "power_at_delta_econ": round(power_tost(delta_econ_coef, se), 3),
        "n_mult_for_power80_econ": round(n_mult_for_power(delta_econ_coef, se), 1),
    }
out["econ_margin_battery"] = res

with open(f"{DATA}/results_level_tost.json", "w") as f:
    json.dump(out, f, indent=1)

# ---------- console summary ----------
print("=== LEVEL TOST (points; 14-cluster bootstrap B=9999 + headline-level t) ===")
print(f"{'contrast':28s} {'mean':>7s} {'CI90_hl':>16s} {'EMThl':>6s} {'ok@1.25':>7s} {'CI90_cl':>16s} {'EMTcl':>6s} {'ok@1.25':>7s} {'nX80hl':>6s}")
for name, r in out["level_contrasts"].items():
    print(f"{name:28s} {r['mean_diff']:>7.3f} [{r['ci90_headline'][0]:>6.2f},{r['ci90_headline'][1]:>6.2f}] {r['EMT_points_headline']:>6.2f} "
          f"{str(r['pass_delta_level_headline']):>7s} [{r['ci90_boot'][0]:>6.2f},{r['ci90_boot'][1]:>6.2f}] {r['EMT_points_cluster']:>6.2f} "
          f"{str(r['pass_delta_level_cluster']):>7s} {r['n_mult_for_power80_headline']:>6.1f}")
print()
print(f"=== ECON MARGIN: delta = {DELTA_ECON_BPS:.0f} bps/SD (coef {delta_econ_coef:.5f}); half-benchmark delta* = 26.85 bps/SD ===")
for cname, r in res["contrasts"].items():
    print(f"{cname:34s} EMT={r['EMT_bps_per_sd']:>7.2f} bps/SD  pass10bps={str(r['pass_delta_econ']):>5s}  passHalfBench={str(r['pass_delta_star_half_benchmark']):>5s}  nX80={r['n_mult_for_power80_econ']:>6.1f}")
print("saved -> data/results_level_tost.json")
