#!/usr/bin/env python3
"""Cross-session pooling of the de-identification (named-minus-anonymized) level effect,
plus the TOST/EMT documentation for the session-6b batch-size singleton contrast.

Motivation (referee points 1 and 3, v6.4.0):
  (a) Each session's de-identification estimate is weak alone under call-clustered
      inference (s3 p=0.017, s5 p=0.18, s6 p=0.15); pool them.
  (b) The batch-size-1 "zero point" claim needs an honest interval: n=50, t=-0.09
      implies SE~2.3 points, so the 95% CI spans ~+/-4.6 -- it cannot exclude a
      shift the size of the +3.6 composition effect.

Inputs (all archived score files; no new data):
  Session 3 (interleaved, 2026-10-18): llm_scores_s3_named_r{1..4}.json, llm_scores_s3_anon_r{1..4}.json
  Session 5 (2026-10-19): llm_scores_s5_named.json, llm_scores_s5_anonv2.json
  Session 6 (2026-10-25): llm_scores_s6_named.json, llm_scores_s6_anonv2.json
  Reported call-clustered inference: results_s5.json / results_s6.json (cluster_t);
  session-3 clustered SE is backed out of the paper's reported 95% CI [-4.85,-0.79]
  (= 1.96 x SE; consistent with the reported clustered t=2.7 and p=0.017 on t13).
  Session 6b: results_s6b.json (level_contrasts, triangle_per_call_noise).

Conventions:
  Paper reports the identity effect in the named-minus-anonymized direction (negative).
  Session differences d_h computed here as anonymized minus named (positive), then
  sign-flipped to the paper's convention for pooling.

Outputs:
  - DerSimonian-Laird random-effects pooled estimate (with FE, Q, tau^2, I^2)
  - Empirical cross-session correlations of headline-level differences
  - A conservative correlation-adjusted pooled CI (empirical rho applied to the
    FULL clustered SEs, even though only the headline-level error component is
    plausibly shared across sessions)
  - TOST minimum-equivalence-margin (EMT) for the singleton-vs-25 contrast
  - data/results_meta_deident.json (for the assertion net)
"""
import json
import math
import os

DATA = "/home/z/my-project/github_repo/data"
OUT = os.path.join(DATA, "results_meta_deident.json")


def load(fname):
    with open(os.path.join(DATA, fname)) as f:
        return json.load(f)


def scores(d, keys):
    return [d[k]["sentiment"] for k in keys]


# ---------- headline-level differences per session (anonymized minus named) ----------
s3_named = [load(f"llm_scores_s3_named_r{i}.json") for i in (1, 2, 3, 4)]
s3_anon = [load(f"llm_scores_s3_anon_r{i}.json") for i in (1, 2, 3, 4)]
s5_named = load("llm_scores_s5_named.json")
s5_anon = load("llm_scores_s5_anonv2.json")
s6_named = load("llm_scores_s6_named.json")
s6_anon = load("llm_scores_s6_anonv2.json")

keys3 = set(s3_named[0])
for d in s3_named[1:] + s3_anon:
    keys3 &= set(d)
keys5 = set(s5_named) & set(s5_anon)
keys6 = set(s6_named) & set(s6_anon)
keys_all = sorted(keys3 & keys5 & keys6)

d3 = {k: sum(a[k]["sentiment"] for a in s3_anon) / 4 - sum(n[k]["sentiment"] for n in s3_named) / 4 for k in keys_all}
d5 = {k: s5_anon[k]["sentiment"] - s5_named[k]["sentiment"] for k in keys_all}
d6 = {k: s6_anon[k]["sentiment"] - s6_named[k]["sentiment"] for k in keys_all}

n = len(keys_all)


def mean(seq):
    return sum(seq) / len(seq)


def pearson(x, y):
    mx, my = mean(x), mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = math.sqrt(sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y))
    return num / den


v3, v5, v6 = [d3[k] for k in keys_all], [d5[k] for k in keys_all], [d6[k] for k in keys_all]
r35, r36, r56 = pearson(v3, v5), pearson(v3, v6), pearson(v5, v6)

# ---------- session estimates and clustered SEs (paper convention: named minus anon) ----------
b3 = -mean(v3)   # = -2.8226 expected
b5 = -mean(v5)   # = -2.0528 expected
b6 = -mean(v6)   # = -2.5367 expected

r_s5 = load("results_s5.json")["p1_identity_N5_minus_A5"]
r_s6 = load("results_s6.json")["p6b_named_minus_anonv2"]
se5 = abs(b5) / abs(r_s5["cluster_t"])
se6 = abs(b6) / abs(r_s6["cluster_t"])
se3 = (4.85 - 0.79) / (2 * 1.959964)          # from the paper's reported clustered 95% CI
t3 = abs(b3) / se3

# ---------- DerSimonian-Laird ----------
beta = [b3, b5, b6]
se = [se3, se5, se6]
k = 3
w = [1.0 / s ** 2 for s in se]
sw = sum(w)
fe = sum(wi * yi for wi, yi in zip(w, beta)) / sw
se_fe = math.sqrt(1.0 / sw)
Q = sum(wi * (yi - fe) ** 2 for wi, yi in zip(w, beta))
df = k - 1
C = sw - sum(wi ** 2 for wi in w) / sw
tau2 = max(0.0, (Q - df) / C)
I2 = max(0.0, 100.0 * (Q - df) / Q) if Q > 0 else 0.0
wr = [1.0 / (s ** 2 + tau2) for s in se]
swr = sum(wr)
re = sum(wi * yi for wi, yi in zip(wr, beta)) / swr
se_re = math.sqrt(1.0 / swr)
z = re / se_re
ci_lo, ci_hi = re - 1.959964 * se_re, re + 1.959964 * se_re
p_norm = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))

# ---------- conservative correlation-adjusted pooled CI ----------
# normalized weights; empirical rho applied to the FULL clustered SEs
wn = [wi / sw for wi in w]
rho = {(0, 1): r35, (0, 2): r36, (1, 2): r56}
var_adj = 0.0
for i in range(k):
    for j in range(k):
        r = 1.0 if i == j else rho[(min(i, j), max(i, j))]
        var_adj += wn[i] * wn[j] * r * se[i] * se[j]
se_adj = math.sqrt(var_adj)
ci_adj = (fe - 1.959964 * se_adj, fe + 1.959964 * se_adj)

# ---------- session-6b singleton TOST / EMT ----------
s6b = load("results_s6b.json")["level_contrasts"]
b1b25 = [c for c in s6b if c["contrast"] == "B1_minus_B25"][0]
b1b5 = [c for c in s6b if c["contrast"] == "B1_minus_B5"][0]
b5b25 = [c for c in s6b if c["contrast"] == "B5_minus_B25"][0]
m, s_m, n_bs = b1b25["mean"], b1b25["se"], b1b25["n"]
df_bs = n_bs - 1


def t_cdf_tails(p, dof):  # two-sided p for given t via continued fraction not needed:
    # use statistics-free approach: match against known values via math.tdist fallback
    try:
        from scipy import stats as st
        return st.t.ppf(p, dof)
    except Exception:
        # t_{0.95,49}=1.67655, t_{0.975,49}=2.00958 (hardcoded fallback)
        return {0.95: 1.676551, 0.975: 2.009575}[p]


t90 = t_cdf_tails(0.95, df_bs)
t95 = t_cdf_tails(0.975, df_bs)
ci90 = (m - t90 * s_m, m + t90 * s_m)
ci95 = (m - t95 * s_m, m + t95 * s_m)
emt = max(abs(ci90[0]), abs(ci90[1]))

# ---------- fictional-control near-coincidence documentation ----------
fs = load("results_s6.json")
fn = fs["p6a_fictional_minus_named"]
fa = fs["p6a_fictional_minus_anonv2"]

res = {
    "design": {
        "purpose": "pool the de-identification level effect across sessions 3/5/6; document batch-size wide null",
        "convention": "named minus anonymized (negative = anonymized scores sit above named)",
        "inputs": "archived score files; clustered SEs from results_s5/s6 cluster_t and the paper's session-3 clustered CI",
    },
    "session_estimates": {
        "s3": {"beta": round(b3, 4), "se_cluster": round(se3, 4), "t_cluster": round(t3, 3), "p": 0.017},
        "s5": {"beta": round(b5, 4), "se_cluster": round(se5, 4), "t_cluster": round(r_s5["cluster_t"], 4), "p": r_s5["cluster_p"]},
        "s6": {"beta": round(b6, 4), "se_cluster": round(se6, 4), "t_cluster": round(r_s6["cluster_t"], 4), "p": r_s6["cluster_p"]},
    },
    "headline_level_diff_correlations": {
        "note": "Pearson correlation of per-headline anonymized-minus-named differences across sessions; same 341 headlines re-scored in each session",
        "n": n,
        "rho_s3_s5": round(r35, 4),
        "rho_s3_s6": round(r36, 4),
        "rho_s5_s6": round(r56, 4),
        "mean_rbar": round((r35 + r36 + r56) / 3, 4),
    },
    "dl_random_effects": {
        "pooled_beta": round(re, 3),
        "se": round(se_re, 3),
        "ci95": [round(ci_lo, 2), round(ci_hi, 2)],
        "z": round(z, 2),
        "p_normal": round(p_norm, 5),
        "fixed_effect_beta": round(fe, 3),
        "Q": round(Q, 3),
        "df": df,
        "tau2": round(tau2, 4),
        "I2_pct": round(I2, 1),
    },
    "correlation_adjusted_conservative": {
        "note": "empirical rho applied to full clustered SEs (conservative; only headline-level error is plausibly shared)",
        "se": round(se_adj, 3),
        "ci95": [round(ci_adj[0], 2), round(ci_adj[1], 2)],
    },
    "s6b_batch_size": {
        "b1_vs_b25": {"mean": m, "se": round(s_m, 3), "t": round(m / s_m, 3), "n": n_bs,
                      "ci95_t": [round(ci95[0], 2), round(ci95[1], 2)],
                      "ci90_t": [round(ci90[0], 2), round(ci90[1], 2)],
                      "EMT_points": round(emt, 2),
                      "note": "EMT = minimum TOST margin; exceeds the +3.61 composition effect -> singleton contrast cannot certify level neutrality at the composition-effect scale"},
        "b1_vs_b5": {"mean": b1b5["mean"], "t": round(b1b5["t"], 3)},
        "b5_vs_b25": {"mean": b5b25["mean"], "t": round(b5b25["t"], 3)},
    },
    "fictional_control_coincidence": {
        "note": "the two clustered p-values are near-identical because the fictional level sits almost exactly midway: both contrasts share clustered |t| ~ 0.755",
        "fict_minus_named": {"cluster_t": fn["cluster_t"], "cluster_p": fn["cluster_p"]},
        "fict_minus_anonv2": {"cluster_t": fa["cluster_t"], "cluster_p": fa["cluster_p"]},
    },
}

with open(OUT, "w") as f:
    json.dump(res, f, indent=1)

print(json.dumps(res, indent=1))
print("\n=== VERIFICATION ===")
print(f"n shared headlines: {n} (expect 341)")
print(f"session means anon-minus-named: s3={mean(v3):+.4f} (expect +2.8226)  s5={mean(v5):+.4f} (expect +2.0528)  s6={mean(v6):+.4f} (expect +2.5367)")
print(f"pooled (named-minus-anon): {re:+.3f}  95% CI [{ci_lo:+.2f}, {ci_hi:+.2f}]  z={z:.2f}  p={p_norm:.5f}")
print(f"tau2={tau2:.4f}  I2={I2:.1f}%  Q={Q:.3f} on {df} df")
print(f"conservative corr-adjusted CI: [{ci_adj[0]:+.2f}, {ci_adj[1]:+.2f}] (rho 35/36/56 = {r35:.3f}/{r36:.3f}/{r56:.3f})")
print(f"s6b B1-B25: {m:+.2f} SE {s_m:.3f}  95% CI [{ci95[0]:+.2f}, {ci95[1]:+.2f}]  EMT(90%) {emt:.2f} points")
