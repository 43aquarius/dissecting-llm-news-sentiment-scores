# AsPredicted Form — Session-5 Controls: Analysis Plan for External Timestamping

**Purpose.** The session-5 design and its falsifiable predictions were deposited in an
archived design document (`audits/P2_preregistration_session5.md`) before any session-5
data collection, as part of the paper's within-study staged pre-specification. This form
packages that design into the standard AsPredicted format so it can receive an
**independent external timestamp** (OSF or AsPredicted.org) *before the remaining calls
of session 5 complete*. Data collection was interrupted by provider rate-limiting after
63 of 84 planned API calls; the design, transformations, seeded swap map, and verification
report were all frozen before the interruption and are hash-bound below.

**How to file (for the author):** create an OSF registration (or AsPredicted submission)
under your own account, paste the nine answers below verbatim, attach
`audits/P2_preregistration_session5.md` and `data/s5_artifact_hashes.json`, and file.
The registration date must precede the completion run of the remaining 21 calls to
constitute an external timestamp for the analysis plan.

---

**Q1. Data collection status.**
Partially collected. Sessions 1–4 of the project (the original named scoring, anonymized
scoring, three repeat calls, the interleaved session 3, and the mechanism session 4) are
complete and reported in the paper. For session 5 itself — the design this form covers —
63 of 84 planned API calls completed (N5: 275/341 headlines, A5/S5/P5: 250/341 each,
T0a/T0b: 275/341 each) before a sustained provider rate-limit interrupted collection.
**No session-5 estimate has been computed or reported**; the partial score files are
hash-bound below and are treated as sealed. The registered analysis applies to the
completed session-5 collection (all 84 calls) and only to it.

**Q2. Main questions.**
(a) Is the interleaved identity level effect (−2.82 points, named minus anonymized,
session 3) driven by the firm prior carried by the identity tags or by the text
perturbation that anonymization introduces? (b) Is the instrument's stochasticity
(within-headline SD ≈ 7.8 points across repeat calls under default decoding) sampling
noise removable by temperature-0 decoding, or server-side nondeterminism that decoding
settings cannot remove? (c) Does the corrected anonymization (with the ticker-V alias
fixed and a forced verification pass) change the published identity estimate?

**Q3. Key falsifiable predictions (stated in the design document before any session-5 data).**
- **P1 (identity replication):** N5 − A5 ≈ −2.8 points (the session-3 interleaved
  estimate), possibly slightly larger in magnitude because the ten ticker-V headlines
  are now genuinely anonymized.
- **P2 (perturbation vs. identity):** if the identity prior drives the N5−A5 gap, then
  S5 (swapped identity, natural text) should NOT track N5, and |N5 − S5| should exceed
  the repeat-noise floor (within-SD ≈ 7.8 points per headline). If text perturbation
  drives the gap, S5 should sit near N5 and away from A5/P5.
- **P3 (prefix neutrality):** P5 − A5 ≈ 0; a materially nonzero difference attributes
  part of the published identity effect to the prefix format itself.
- **P4 (decoding noise):** if sampling noise dominates, T0a and T0b are bitwise
  identical score vectors (within-headline SD = 0); if the two temperature-0 rounds
  still differ, server-side nondeterminism is documented and the paper's stochasticity
  claim strengthens beyond decoding settings.
- **P5 (decoding level shift):** no directional prediction (two-sided): the temperature-0
  mean level may differ from N5; reported either way.

**Q4. Dependent and independent variables.**
Dependent: the headline-level sentiment score on the [−100, +100] scale returned by the
scoring API (GLM-4-Plus, served model; thinking disabled). Independent: experimental
condition (N5 named / A5 anonymized-v2 / S5 identity-swap / P5 neutral prefix /
T0a,T0b temperature-0 named), batch assignment (14 batches of 25), and call order
(six-way rotated by batch index). Texts are deterministic transformations of the frozen
341-headline corpus (seeded derangement seed 20261019 for the swap map; corrected alias
table; forced zero-residual verification on all transformed texts).

**Q5. Conditions.**
Six conditions in one sitting, batch-interleaved, order rotated left by (batch index
mod 6) so every condition occupies every time-of-session position uniformly; batch size
25; system prompt verbatim-identical to sessions 1–4. Corrected anonymization (A5)
includes the "Visa" alias and sentence-start capitalization; S5 replaces focal
identifiers with a seeded random other firm's identifiers; P5 = A5 text under a
"[Company X]" prefix; T0a/T0b are named passes at temperature 0.

**Q6. Analysis plan (locked in the design document before data).**
Headline-level paired contrasts with batch-call-clustered inference (14 clusters) as
the conservative default and headline-level t as the liberal bound, exactly the
session-3 convention (analysis_v3.py); exact-match rates between condition pairs;
prediction-layer re-estimation of the H1 next-day coefficient for each condition that is
a valid firm-day sentiment source (N5, A5, S5; P5 only descriptively). **No new
comparisons will be added after seeing the data; any additional exploration will be
labeled exploratory in the paper.**

**Q7. Outliers and exclusions.**
None at the headline level: all 341 in-window headlines are scored in every condition and
analyzed. Robustness checks (not exclusions) that are part of the locked plan: the ten
ticker-V headlines are reported both included and excluded in identity contrasts
(continuity with the paper's disclosed anonymization failure); scores are truncated to
[−100, 100] and relevance to [0, 100] by the scoring parser as in all prior sessions.

**Q8. Sample size / number of observations.**
341 headlines per condition (fixed corpus, no sampling); 14 batch-calls per condition;
84 calls total; six conditions. The corpus is frozen (no additional collection), so the
only stochastic replication is at the call level: the design provides 2 draws for
temperature-0 (T0a, T0b) and the comparison against sessions 1–4 (12 independent named
passes) for level benchmarks. Power against the session-3 effect (−2.82 points,
within-SD 7.2) at 341 paired headlines exceeds 0.99 (paper Appendix E).

**Q9. Sample size justification.**
The corpus is fixed by the paper's design (the identical 341 in-window headlines scored
in every prior session); session 5 varies conditions, not the sample. Batch-call
clustering is the binding constraint on inference (14 clusters per condition), and the
session-3 identity effect was detected at clustered t = 2.7 with the same cluster
count, so the design is powered for effects of the magnitude already established.

---

## Hash-bound frozen artifacts (SHA-256, first 16 hex)

Computed 2026-10-19 (UTC), after the interruption, before any completion run:

| Artifact | SHA-256 (16) |
|---|---|
| P2_preregistration_session5.md | 5a10b8955d2074d7 |
| s5_swap_map.json | 70868a17c4d54d95 |
| s5_transforms.mjs | 039bc93a90858f39 |
| llm_score_v5.mjs | 81e730b64705d3de |
| s5_verify_report.json | 77f6ffe6c51b982d |
| llm_scores_s5_named.json (partial, sealed) | 7995b621f453479a |
| llm_scores_s5_anonv2.json (partial, sealed) | 239337bb8f9f146f |
| llm_scores_s5_swap.json (partial, sealed) | 285c8781d44d1011 |
| llm_scores_s5_placeholder.json (partial, sealed) | 75e01d77370c1038 |
| llm_scores_s5_t0a.json (partial, sealed) | 4e735d2ac20c7e84 |
| llm_scores_s5_t0b.json (partial, sealed) | a19ffad461bde87a |
| llm_score_v5.log (through interruption) | 5c9ac7a99cc8ccab |

Full hashes: `data/s5_artifact_hashes.json` in the replication package.
