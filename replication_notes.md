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
