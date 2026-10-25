# P3 Experiments Report — Session 6 (Fictional-Name Control), Session 6b (Batch-Size Dose-Response), Level-Layer TOST, Economics-Anchored Margin, and the Swapped-Text Leakage Audit

**Date:** 2026-10-25 · **Pre-registration:** `audit/P3_preregistration_session6.md` (archived before collection; within-study staged pre-specification, NOT independent registration)
**Status:** all experiments completed (41 + 62 successful API calls; every condition 341/341 or 50/50); all analyses under locked plans; WP integrated as v6.4; letter updated.

---

## 1. Session 6 — the fictional-name control (the missing cell)

**Design.** Three conditions over the identical 341 in-window headlines, one sitting (2026-10-25), batch size 25, three-way rotated call order per batch, protocol verbatim-identical to sessions 1–5, thinking disabled, every call logged (`llm_score_v6.log`):

- **N6** named anchor → `llm_scores_s6_named.json`
- **A6** anonymized v2 + forced verification → `llm_scores_s6_anonv2.json`
- **F6** fictional names → `llm_scores_s6_fictional.json` (map: `s6_fictional_map.json`; 36 invented two-part names + synthetic tickers, constructed to carry no association with any prominent public company)

**Verification gate (pre-collection).** The first run attempt was **blocked by the gate itself**: six F6 texts retained their original identity through concatenated name variants (`ExxonMobil` ×5, `JPMorganChase` ×1) that the session-5 word-boundary check cannot see — the same failure class as the ticker-V anonymization gap, caught *before any call* this time. The session-6 transform adds concatenated-variant replacement (`replaceConcatVariants` in `llm_score_v6.mjs`); the re-run gate reports **zero residuals on all 341 texts across both tiers, zero missing fictional names, zero anonymization residuals** (`s6_verify_report.json`). The blocked first attempt is archived in the log as a disclosed design deviation.

**Results (`analysis_v6.py`, seed 20261025).**

| Contrast | Estimate | Headline t / Wilcoxon | Clustered (14) p | Level-TOST EMT (headline) |
|---|---|---|---|---|
| F6 − N6 (fictional vs named) | **+1.202** | t=1.64 / p=0.014 | 0.450 | 2.41 pts (fails δ=1.25) |
| F6 − A6 (fictional vs placeholder) | **−1.334** | t=−1.72 / p=0.152 | 0.450 | 2.62 pts (fails δ=1.25) |
| N6 − A6 (replication cell) | **−2.537** | t=−2.92 / p=0.0018 | 0.153 | 3.97 pts (fails, as it should) |

Levels: N6 = 12.70, F6 = 13.90, A6 = 15.23 — **the fictional level lands almost exactly midway** ((12.70+15.23)/2 = 13.97 vs observed 13.90). Correlations: r(N6,F6)=0.936, r(N6,A6)=0.911, r(F6,A6)=0.930.

**Prediction layer.** β = 0.0126 (N6) / 0.0112 (A6) / 0.0113 (F6), n=205; day-cluster bootstrap pairwise differences p = 0.68 / 0.62 / 0.96 — no difference, as in every prior identity variant.

**Interpretation (locked to the pre-registered competing predictions).** The placeholder-rewrite hypothesis predicted F6≈N6 and F6−A6≈+2..3; the identity-removal hypothesis predicted the opposite assignment. The data place F6 midway: **neither pure hypothesis is certifiable; the point estimates split the de-identification displacement roughly evenly between a real-name component (~1.2 pts) and a placeholder-rewrite component (~1.3 pts).** Neither sub-contrast is individually established under clustered inference — the split is a point-estimate reading, reported as such in the paper. The swap control's firm-specific-prior bound is unchanged (wrong real firm ≈ right real firm, +0.34): the real-name component is about the name being *real/familiar*, not about *which* firm it denotes. The de-identification effect itself now has **three independent same-session estimates**: −2.82 (interleaved), −2.05 (session 5), −2.54 (session 6).

**Consequence for the paper's wording.** The absolute phrase "the removal of a concrete name, not a prior about the identified firm" is refined throughout to: removing the firm's *real* name raises scores by two to three points — about half survives a fictional replacement, half is the rewrite — with no support for a material prior about which firm the name denotes.

## 2. Session 6b — batch-size dose-response (the zero point)

**Design.** Seeded 50-headline subsample (seed 20261025, `s6b_sample.json`), one pass per size in one sitting: B1a (25 singletons) → B25 (2×25) → B5 (10×5) → B1b (25 singletons), so the size-1 level is centered in session time. 62 calls, resume-safe (`llm_score_v6b.log`).

**Results (`analysis_v6b.py`).**

| Quantity | Value |
|---|---|
| Level B1 (size 1) | 27.20 |
| Level B5 (size 5) | 21.70 |
| Level B25 (size 25) | 27.40 |
| B1 − B25 (paired, n=50) | **−0.20 ± 2.35 (t = −0.09)** — the zero point |
| B1 − B5 | +5.50 (t = 2.30) — suggestive, unexplained |
| B5 − B25 | −5.70 (t = 2.50) — suggestive, unexplained |
| Per-call noise (triangle solve) | n1=12.3, n5=11.6, n25=11.2 pts (s3 benchmark: 7.2) |
| Mood² estimator (5v5−v1)/4 | −50.6, bootstrap CI [−275, +409] — **underpowered** |

**Findings.** (1) **The zero point**: singleton and 25-batch levels match on identical titles to −0.2 points — mere batch-mate presence does not move levels; the +3.6-point composition channel requires a *changed mate pool*. This is the cleanest evidence yet that the composition effect is about *which* headlines share the call, not about batching as such. (2) The size-5 dip is a single-pass reading carried by ten calls; it exceeds the documented within-sitting drift scale and is reported as unexplained rather than interpreted. (3) The pre-registered mood decomposition (P6d) is **underpowered at this design** (one pass per size): the estimator's interval spans the session-3 benchmark (mood²≈6.8), and headline resampling cannot represent call-level mood variation — resolving mood vs position needs multiple passes per size (design archived). (4) Per-call noise this sitting (≈11–12 pts across sizes) exceeds session-3's 7.2 — consistent with serving-stack noise varying across days, and itself a replication of the paper's stochasticity claim.

## 3. Level-layer TOST battery (points)

Pre-fixed margin **δ = 1.25 points** = half the 2.5-pt midpoint of the placeholder-rewrite family (2.05–3.13), fixed before inspection. 14-cluster cluster bootstrap, B=9999, seed 20261025 (`level_tost_and_margins.py` → `results_level_tost.json`).

| Level contrast | Mean | 90% CI (headline) | EMT (headline) | Pass δ=1.25 | EMT (clustered) |
|---|---|---|---|---|---|
| Named − swapped | +0.34 | [−1.06, +1.73] | 1.73 | **No** | 3.22 |
| Named − prefixed | −2.19 | [−3.50, −0.87] | 3.50 | No | 5.15 |
| Prefixed − anonymized | +0.13 | [−0.84, +1.10] | 1.10 | **Yes** | 2.39 |
| Swapped − anonymized | −2.39 | [−3.60, −1.18] | 3.60 | No (should) | 4.53 |
| Named − anonymized | −2.05 | [−3.24, −0.86] | 3.24 | No (should) | 4.35 |

**Reading.** The prefix control certifies equivalence; the swap difference is small (13% of the placeholder midpoint) but **not certifiable at half the effect** with n=341 (~3.9× headlines needed for 80% power headline-level; under 14-cluster clustering no level contrast certifies below ~3 points). This is the formal backing for the paper's downgraded wording ("does not support a material firm-specific prior", not "rules out").

## 4. Economics-anchored margin (10 bps/SD)

**δ_econ = 10 bps of next-day response per 1-SD sentiment shock** (coef 0.00277; round threshold independent of the benchmark t ∈ [1.47, 2.12]). Re-evaluation of the eight archived prediction-layer contrasts (`results_level_tost.json`):

| Contrast | EMT (bps/SD) | Pass 10 bps | Pass δ*=26.85 bps (half-benchmark) | n× for 80% power at 10 bps |
|---|---|---|---|---|
| C8 same-session | 11.5 | No | Yes | 3.6× |
| C1 cross-session | 14.5 | No | Yes | 5.8× |
| C3 session-5 | 18.9 | No | Yes | 5.5× |
| C2 interleaved | 22.3 | No | Yes | 7.8× |
| C4 swap | 29.8 | No | No (56%) | 7.7× |
| C7 clean-vs-zero | 48.9 | No | No | 44× |
| C5 dictionary | 237.1 | No | No | 1184× |
| C6 priced-vs-clean | 351.8 | No | No | 969× |

**Reading.** The v6.2 equivalence findings are **margin-specific**: at the half-benchmark margin the four de-identification contrasts pass; at a strict 10 bps/SD margin **none do** (this sample bounds invariance at ~11.5–29.8 bps/SD for identity contrasts, 3.6–7.8× more data needed). The paper now says exactly this, replacing any impression of margin-free equivalence.

## 5. Swapped-text leakage audit

**Method** (`swap_leakage_audit.py` → `results_swap_leakage.json`, `s6_cue_lexicon.json`): transparent data-driven cue lexicon — a token is a firm cue if it appears in ≥3 of the firm's in-window titles and in ≤5 other firms' titles (primary), or ≥2/≤3 (sensitivity); firm's own names, tickers, and a finance-generic stoplist excluded; lexical heuristic, reproducible, **not human annotation**.

**Findings.**
- Primary rule: **51/341 = 15.0%** of swapped headlines retain ≥1 original-firm lexical cue; sensitivity rule: 91/341 = 26.7%.
- **6/341 = 1.8% retain the original identity outright** via concatenated name variants (the `ExxonMobil`/`JPMorganChase` class) — caught by this audit, invisible to the session-5 verification gate; the session-6 transform fixes it going forward.
- Excluding every flagged headline: N−S = **+0.36** (primary) to **+0.42** (sensitivity) vs full-sample +0.34; S−A = −2.64 / −2.52 (larger in magnitude); N−A = −2.28 / −2.10. **The swap null is not an artifact of identity leakage**; if anything, leakage was diluting the placeholder-vs-swap separation.

## 6. Honesty ledger

- Established (clustered-robust): de-identification effect, three same-session replications; batch-composition effect (+3.61/+3.50); zero-point level-neutrality at size 1 (n=50, single pass, headline-level); predictive-layer invariance at the half-benchmark margin.
- Point-estimate readings (not individually certified under clustering): the real-name/rewrite split; the B5 dip (unexplained).
- Underpowered as pre-registered: mood-vs-position decomposition at one pass per size (P6d) — design archived for a multi-pass rerun.
- Not executable in this environment: cross-model replication (SDK ignores the model parameter; probe archived), independent human annotation (package ready; `kappa_analysis.py` refuses empty inputs) — both remain disclosed limitations with concrete remedies.
