# Replication Notes and Limitations

## What cannot be reproduced exactly

1. **News collection (Step 1)**. Web-search results drift with time, search-engine ranking, and index updates. Re-running `collect_ws_news.mjs` today will not return the same 542 headlines. The archived `news_all.json` is the frozen corpus; all downstream steps are deterministic given it. This irreproducibility is a substantive finding of the paper (coverage selection, H5), not a defect of the archive.
2. **LLM scores (Steps 3, 6)**. The scoring model is a served endpoint; its exact version and decoding defaults are not client-visible. The four conditions were executed within hours of each other on the same endpoint (see `logs/llm_score_v2.log`), which supports within-endpoint comparability but cannot guarantee cross-time stability. Repeat-call dispersion (ICC 0.919, 29.9% exact across four calls) bounds stochasticity but not endpoint drift.
3. **Price data (Step 2)**. NASDAQ's public chart API is unofficial and unversioned; the archived `prices.csv` is the source of truth.

## What reproduces deterministically

- LM dictionary scores, panel construction, both analysis layers (`results.json` bit-for-bit; `results_v2.json` up to fixed seeds), all figures, and the paper PDF.

## API and licensing constraints

- The z-ai-web-dev-sdk endpoints (chat, web-search, page-reader) require project credentials; the scripts fail gracefully without them. Substitute any OpenAI-compatible chat endpoint by editing the SDK import in the two `llm_score*.mjs` scripts; the prompt is engine-agnostic.
- News headlines are redistributed at title length only for research verification. The LM Master Dictionary is redistributed under its original academic-use terms with citation.

## Known imperfections (documented, not hidden)

- Anonymization is conservative (names/tickers only; product names and third-party firm names in a headline survive) — a lower bound on de-identification.
- `llm_scores.json` covers all 542 headlines; the audit conditions cover the 341 in-window subset only.
- The v1 analysis used `cov_type="cluster"` with 2-column groups; the audit verified this behaves as approximately two-way clustered (see `src/audit_cluster_se.py`), and all v2 inference re-states this explicitly.
- Publication timestamps are unavailable (dates only); event-window alignment beyond date granularity is impossible with this corpus — stated in Sec. 8.


## v3 revision notes (2026-10-16)

- The revision stage added `revision_power.py` (power/MDE, session-confounding decomposition, same-session instrument contrasts, residual third-party identification) and `figures_v3.py` (Figure 5). No new LLM API calls were made; all revision numbers derive from the archived four-condition scores.
- Scoring-session fact underlying Section 5.2 / Appendix F: the v1 named round ran 2026-10-15 16:01-16:24 UTC (`logs/llm_score.log`, `logs/llm_score2.log`); the anonymized and repeat rounds ran 2026-10-16 04:24-04:33 UTC (`logs/llm_score_v2.log`). The named protocol is verbatim-identical across the two sittings.
- The same-session identity contrast and the same-session predictive difference are labeled revision-stage additions outside the declared BH family; the family and its q-values are unchanged from v2.
- The v2-to-v3 editorial changes to the LaTeX sources are archived in `src/edit_results.py` and `src/edit_others.py` (assertion-guarded span replacements; idempotent).


## v4 P0-repair notes (2026-10-18)

- An independent data-and-code audit (`audits/P0_data_code_audit.md`) catalogued 13 defects in the v3 draft (9 P0-level); all 12 P0 tasks were fixed (`audits/P0_fix_log_v4.md`). The most consequential: Table 6 was hand-assembled and contained a firm with no archived records; Table 1 mixed an all-542 computation into N=341 rows; "44% exact across four calls" was a two-draw pairwise rate (correct: 29.9%); the H5 selection test used a pooled Welch statistic that ignored the panel's double indexing (now firm+day FE, two-way clustered, t=2.76); the H4 difference bootstrap mixed specifications and was seed-sensitive (now B=9,999, consistent spec, p=0.100); the executed alias table failed to de-identify ticker V (10/341 no-op, disclosed with excluding-V robustness, -1.29, p=0.04).
- Run order note: `revision_power.py` (v4) reads `data/v_exclusion.json`, so run `v_exclusion.py` first.
- Tables 1 and 6 are now generated as LaTeX by `descriptives.py` / `coverage_table.py` and \input-ed from `paper/sections/gen/`; hand-editing those tables is no longer possible. `tests/test_numbers.py` asserts 60 published numbers against script outputs after any change.
- The `edit_*.py` surgical-edit scripts are retired from the pipeline (kept in `src/` for provenance only); the paper is edited only through its LaTeX sources, with numbers flowing from script outputs.

## v5 additions (P1 round)

- `src/llm_score_v3.mjs` re-creates the session-3 interleaved experiment (8 rounds + composition control) but re-running it produces NEW stochastic draws: the archived `data/llm_scores_s3_*.json` are the canonical artifacts, and `src/analysis_v3.py` reproduces every session-3 statistic in the paper from them (seed fixed).
- `data/priced_classification.json` records a judgment-based classification (disclosed as LLM-assisted, non-independent); it is archived, not recomputable — the honest status for any annotation step.
- The paper's cover is rendered by `src/render_cover.py` (Playwright) and merged by `src/merge_final.py`.

## v6 round notes (2026-10-19)

- Session 5 (identity-swap / neutral-prefix / temperature-0 controls) is PRE-REGISTERED
  (audits/P2_preregistration_session5.md) but its collection was interrupted by sustained
  provider rate-limiting (429) after 63 of 84 calls; the six partial score files, the call
  log, the seeded swap map, and the zero-residual verification report are archived under
  data/ and logs/. To complete: re-run src/llm_score_v5.mjs (resume-safe; it skips already-
  scored URLs), then src/analysis_v5.py -> data/results_s5.json. No design changes needed.
  No session-5 estimate appears in the v6 manuscript, per the paper's discipline.
- Cross-model validation is not executable through this provider: the API ignores the
  client-side model parameter (all requests served by glm-4-plus). Probe: logs/probe_v6.log.
- The two-rater human annotation kit lives in annotation_package/ (52 items, codebook,
  independence protocol). kappa_analysis.py refuses to compute statistics until both
  rater columns are filled; it fabricates nothing.
- tests/test_numbers.py now runs 183 assertions, including rendered-cell checks for the
  firm-coverage table (the v5.1 generator had a slicing bug that silently rendered only 20
  of 36 firms) and forbidden-phrase checks (no revision-log language in the manuscript).

## v6.1 notes (2026-10-19)

- Session-5 completion: the 21 remaining calls were run under the identical archived
  protocol (llm_score_v5_attempt.mjs, per-call log appended to llm_score_v5.log); the
  analysis ran only after all 84 calls completed. The sealed pre-completion score files
  are hash-bound in audits/aspredicted_session5_form.md.
- The paper's title changed in v6.1 ("Identity Priors" -> "De-Identification") because
  the pre-specified swap control refuted the firm-specific-prior reading; the channel
  is the removal of a concrete identifier, not the identity it carries.
- fig_downstream.png is generated by figures_v7.py, which replicates batch_downstream.py's
  regression-sample aggregation for the daily series (shift +4.5, flip rate 15.5%).
- Cross-model replication remains infeasible in this environment (single-vendor SDK,
  model parameter ignored by the serving layer; probe logs archived). The first
  follow-up design is specified in the paper's threats section and the AsPredicted form.

## v6.2 addendum (2026-10-20)

- New: `src/equivalence_testing.py` -> `data/results_equivalence.json`. Rebuilds the v2/session-3/session-5 regression samples exactly (13 assertions against stored coefficients) and runs the day-cluster paired bootstrap (B=9,999, seed 20261020) for eight contrasts, storing full distributions. Percentile TOST at delta* = 0.5 x benchmark; EMT = max(|q5|,|q95|) reported margin-free; analytic power at true difference zero; sample multiples for 80% power use SE* = delta/(1.2816+1.645).
- The echo-split contrast (`C6`/`C7`) replicates the P0-10 same-day-control specification with the >=25-obs-per-side guard.
- Paper integration: `sections/appendix.tex` (new subsection `app:equiv`, table `tab:tost`), `sections/results.tex` (prediction layer, H4, two captions), `sections/theory.tex` (converse inference clause), `sections/intro.tex`, `sections/discussion.tex`, `sections/titleblock.tex`, `sections/litreview.tex`, `sections/references.tex` (+4 entries), `sections/robustness.tex`.
- Verify with: `python src/equivalence_testing.py` (writes results_equivalence.json), `python tests/test_numbers.py` (290 checks), `bash`-free in-package compile: `cd paper && tectonic main.tex`.

## v6.3.1 addendum (2026-10-23)

- Fix: `sections/appendix.tex` + `sections/results.tex` display the session-3-vs-4 fixed-composition drift as **+0.56** (archived 0.5645 in `data/results_s4.json`); the stale "+0.57" display is gone from both files.
- Declarations: `sections/titleblock.tex` gains the competing-interest and funding sentences (standard no-conflict / no-grant language; author verifies factually at submission).
- Test net: `tests/test_numbers.py` and `src/test_numbers.py` grow to **297 checks** (+7: pinned drift value, rendering guards, stale-phrase forbidden list, declaration presence).
- Verify with: `python tests/test_numbers.py` (297 checks), `cd paper && tectonic main.tex` (39 pp. body), then `python ../src/pdf_qa_v6.py` against the merged deliverable.

## v6.3.2 addendum (2026-10-23)

- Journal-guideline compliance round (FRL Guide for Authors). Paper changes: `sections/references.tex` (Glasserman and Lin updated from the 2023 arXiv working paper to the published *Journal of Financial Data Science* 6(1), 25-42, 2024 version; new entry Korikov, Du, Sanner, and Rekabsaz 2025, EMNLP 2025, arXiv:2505.12570) and `sections/litreview.tex` (the NLP context-effects sentence now also credits batch composition/permutation work in information retrieval). No numbers, tables, or figures change.
- Verify with: `cd paper && tectonic main.tex` (39 pp., 0 errors), `python tests/test_numbers.py` (297 checks), `python src/pdf_qa_v6.py` (65/65 key strings; run against the merged deliverable).

## v6.4 addendum (2026-10-25) — three-layer revision: session-6/6b experiments, level TOST, leakage audit

- New staged sessions (pre-registered in `audits/P3_preregistration_session6.md`, archived before collection): session 6 (fictional-name control: N6/A6/F6 over the identical 341, one sitting, three-way rotation; 41 calls) and session 6b (batch-size dose-response: 50 seeded headlines scored alone / in 5s / in 25s, one pass per size; 62 calls).
- Headline results: fictional-name condition lands midway between named and anonymized (+1.20 / -1.33; clustered p=0.45), splitting the de-identification displacement into ~half real-name and ~half placeholder-rewrite; de-identification effect replicates a third time (N6-A6 = -2.54); singleton-vs-25-batch level gap -0.20 (batch-size-1 zero point: composition requires changed mates); mood decomposition underpowered at one pass per size (disclosed).
- New analyses: level-layer TOST battery at a pre-fixed 1.25-point margin (`level_tost_and_margins.py`; prefix passes, swap EMT 1.73 headline / 3.22 clustered); economics-anchored 10 bps/SD margin on the prediction-layer battery (no contrast passes; verdicts margin-specific); swapped-text leakage audit (`swap_leakage_audit.py`; 15.0%/26.7% cue-flagged, 1.8% identity leaks via concatenated name variants; conclusions unchanged after exclusion).
- Wording downgrades throughout WP+letter per the referee directive (no "replicates/settles/rules out" for clustered-insignificant contrasts; temperature-0 attribution is "consistent with server-side nondeterminism"); the naive two-session benchmark paragraph moved from §5.2 to Appendix (app:session); the downstream-consequences table+figure promoted from the appendix into §5.2.
- Draw-stability count updated: 14 independent named passes across 6 sittings (16 archived draws incl. 2 within-condition means); ranges unchanged (beta [0.0104,0.0161], t [1.47,2.12]).
- Verify with: `cd paper && tectonic main.tex` (42 pp., 0 errors), `python tests/test_numbers.py` (323 checks), `python src/frl_letter_check.py` (109 checks; letter body 1,440 words), `python src/pdf_qa_v6.py` (65/65 key strings on the merged deliverable, 43 pp.).

## v6.5 addendum (2026-10-28) — five-point referee revision: pooling, wide null, point-estimate labeling, count unification, main/appendix split

- New analysis: cross-session pooled de-identification estimate (`src/meta_deident_pooling.py` from the archived session score files): DerSimonian–Laird random effects over the three call-clustered session estimates (−2.82/SE 1.04; −2.05/SE 1.51; −2.54/SE 1.78) gives −2.57 points, 95% CI [−4.08, −1.06], z=3.34, τ²=0, I²=0%. Because the three sessions re-score the same 341 headlines, the estimates are not independent (per-headline response correlations across sessions: 0.45/0.40/0.32); a conservative covariance-adjusted interval is [−4.56, −0.58], still excluding zero. Session 3's estimate retains the ten ticker-V no-op headlines (V-excluded variant −3.13 is larger in magnitude, so the pooled figure is conservative). Output: `data/results_meta_deident.json`.
- Batch-size singleton contrast re-characterized: wide null, not a zero point (95% CI [−4.92, +4.52]; equivalence minimum margin 4.1 points > the +3.61 composition effect); the "level-neutral" claim is withdrawn from WP, appendix, and letter; the size-5 anomaly and the elevated per-call noise (11–12 vs 7.2) are now in the main text as well.
- Fictional-name split: explicitly a point-estimate reading throughout (neither sub-contrast individually significant; the two clustered p=0.45 values are a documented coincidence — both clustered |t|≈0.755).
- Count unification: fourteen individual named passes + two within-condition means = sixteen draws, enumerated consistently (session-6 anchor restored to both enumerations).
- Structure: main text 27 pp. (title page + 26 content pages, references included; 28 pp. in the merged deliverable with the external cover) + separate 18-pp. online appendix (`paper/online_appendix.tex`, appendices A–K; bidirectional xr cross-references); §5.2 keeps one summary table; the identity-anatomy figures and the downstream-consequences table+figure moved to the online appendix.
- Verify with: `cd paper && tectonic main.tex && tectonic online_appendix.tex` (0 errors), `python tests/test_numbers.py` (343 checks), `python src/frl_letter_check.py` (117 checks; letter body 1,428 words), `python src/pdf_qa_v7.py` (PASS on the merged main + online appendix).
