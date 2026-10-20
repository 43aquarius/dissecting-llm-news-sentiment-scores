# Pre-Registration: Session 5 Controls (Identity-Swap, Neutral Prefix, Temperature-0)

**Status:** Written and archived BEFORE any session-5 data collection. Part of the
within-study staged pre-specification (the declared seven-comparison family of the
original audit predates all augmented inference; each later sitting was pre-specified
before it ran; see paper Sections 4 and 6). This document is archived verbatim in the
replication package as `audits/P2_preregistration_session5.md`.

**Date of pre-registration:** 2026-10-19 (UTC+8), before the session-5 API calls.
**Scoring model:** `glm-4-plus` (the SDK's served model; the `model` parameter is
ignored by the serving layer — probe log `scripts/probe_v6.log`, 2026-10-19).
**Corpus:** the identical 341 in-window headlines (news_scored.json order), batch size 25,
same system prompt as sessions 1–4, `thinking: {type: "disabled"}`.

## Motivation (design gaps identified at review)

1. The interleaved identity effect (−2.82 points, session 3) compares **named vs.
   anonymized** text. Anonymization both (a) removes identity AND (b) perturbs the
   text (lowercase "the company" inside title-case headlines, loss of the prefix).
   Reviewers asked for a control that separates the identity channel from the
   perturbation channel.
2. The reliability statistics (ICC 0.919; within-SD 7.8) are measured under the
   API's **default decoding**. Whether that noise is sampling noise (removable at
   temperature 0) or server-side/batch-level noise (not removable by decoding
   settings) has not been tested. The API accepts `temperature: 0` (probe, 2026-10-19).
3. The executed anonymizer was a no-op for the ten ticker-V headlines (paper
   Appendix B). The corrected alias table (V → "Visa") plus a forced verification
   pass is pre-specified here for the new anonymized pass.

## Conditions (all in ONE sitting, batch-interleaved)

For batch $b$ (0-indexed, 14 batches), the six calls run in an order rotated left by
$b \bmod 6$, so every condition occupies every time-of-session position uniformly:

| Tag | Condition | Text | Prefix | Decoding |
|-----|-----------|------|--------|----------|
| N5 | named | original | `[Company]` (true firm) | default |
| A5 | anonymized v2 | corrected alias table (incl. "Visa"), sentence-start capitalization fix, **forced verification** | none | default |
| S5 | identity swap | focal identifiers replaced by a **seeded random other firm's** identifiers (derangement, seed 20261019) | `[SwapCompany]` | default |
| P5 | neutral prefix | identical text to A5 | `[Company X]` | default |
| T0a | named, temperature 0 | original | `[Company]` | `temperature: 0` |
| T0b | named, temperature 0 (2nd round) | original | `[Company]` | `temperature: 0` |

Swap-mapping rule: seeded derangement over the 36 tickers (seed 20261019, mapping
archived as `s5_swap_map.json`); focal aliases (longest-first, case-insensitive,
whole-word) → swap firm's display name; standalone all-caps ticker token → swap
ticker. Third-party firm mentions are left intact (conservative, as in A5).

## Predictions (falsifiable, stated before data)

- **P1 (identity replication):** N5 − A5 ≈ −2.8 points (the session-3 interleaved
  estimate), possibly slightly larger in magnitude because the ten V headlines are
  now genuinely anonymized.
- **P2 (perturbation vs identity):** if the identity prior drives the N5−A5 gap, then
  S5 should NOT track N5: swapped scores load onto the wrong firm's prior, and
  |N5 − S5| should exceed the repeat-noise floor (within-SD 7.8 points per headline).
  If text perturbation (not identity) drives the gap, S5 (natural text, wrong
  identity) should sit near N5 and away from A5/P5.
- **P3 (prefix neutrality):** P5 − A5 ≈ 0 (a neutral prefix should not move levels);
  a materially nonzero P5−A5 would attribute part of the published "identity" effect
  to the prefix format itself.
- **P4 (decoding noise):** if sampling noise is the dominant stochastic component,
  T0a ≡ T0b (bitwise identical 341-score vectors) and T0 within-headline SD = 0;
  if the two T0 rounds still differ, server-side nondeterminism is documented and
  the paper's "scoring is stochastic" claim strengthens beyond decoding settings.
- **P5 (decoding level shift):** no prediction (two-sided): T0 mean level may differ
  from N5; reported either way.

## Analysis plan (locked before data)

Headline-level paired contrasts with batch-call-clustered inference (14 clusters)
as the conservative default, headline-level t as the liberal bound, exactly as in
session 3 (analysis_v3.py convention); exact-match rates; prediction-layer
re-estimation of the H1 coefficient per condition where the condition is a valid
firm-day sentiment source (N5, A5, S5; P5 only descriptively). No new comparisons
will be added after seeing the data; any additional exploration will be labeled
exploratory in the paper.

## Infeasibility disclosure (recorded at pre-registration)

- **Cross-model validation is not executable in this environment**: the serving
  layer ignores the `model` parameter (all requested models return served model
  `glm-4-plus`; probe log archived). The paper's single-scorer limitation therefore
  stands and is disclosed; no cross-model numbers will be reported.
- **Independent human annotation of the 52 echo-flagged headlines cannot be produced
  by the research pipeline itself.** An annotation package (codebook, per-item
  sheets, kappa script) is prepared for two human raters; until human labels exist,
  the paper reports only (i) the original LLM-assisted audit and (ii) a
  protocol-variation second LLM rater (different prompt format, temperature 0,
  item-by-item), explicitly labeled as LLM-vs-LLM agreement, not human agreement.
