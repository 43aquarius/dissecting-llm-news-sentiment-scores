# Dissecting LLM News Sentiment Scores: De-Identification, Batch Composition, Scoring Noise, and Price Echoes in Return Predictability

**Chang Tan** — Dalian University of Technology — aquars43@foxmail.com

*Working paper, October 2026. A measurement audit on 36 U.S. large-cap firms, July–October 2026.*

> [!IMPORTANT]
> **Downloads**: the compiled paper (35 pp., with cover) and the full replication package (zip) are attached to the [**Releases**](../../releases) page — no build required.

## Abstract

Do LLM sentiment scores on firm news predict stock returns because of what the text *means*, or because of what the scorer *brings to* the text — and to the batch? We audit a short-horizon predictability design on 542 search-collected headlines about 36 large U.S. firms (341 in-window, July–October 2026), scored by GLM-4-Plus under conditions that each vary one ingredient: identity visible, removed, or swapped; repeat calls; controlled batch composition; temperature-zero decoding; and the Loughran–McDonald dictionary. The baseline next-day association is marginal (t = 2.10, BH q = 0.062) and draw-dependent across thirteen re-scorings. The robust findings concern the measurement: de-identification — replacing the firm's name with a placeholder — raises score levels by two to three points without changing predictive content, while swapping the name to another firm moves levels by essentially nothing; batch composition — which headlines share an API call — moves levels by 3.6 points, a channel not previously quantified in this setting; the instrument is stochastic (ICC 0.92; 30% exact replication; temperature zero does not restore determinism); predictability directionally concentrates in the 15% of headlines that echo realized prices (p = 0.10); and news coverage is itself selected on realized volatility (t = 2.76). Anonymized, repeated, batch-frozen, session-interleaved scoring should precede any deployment of LLM sentiment as a predictor.

## Headline findings

| Channel | Result | Inference |
|---|---|---|
| **De-identification** — named vs. anonymized vs. identity-swapped | removing the firm's name raises score levels by 2–3 points (interleaved −2.82; corrected-anonymization replication −2.05); **swapping the name to another firm moves levels by +0.34 (n.s.)** — the effect is the removal of a concrete name, not a firm prior; predictive content unchanged in every variant (all difference p ≥ 0.62, swap p = 0.92) | same-session interleaved + swap/prefix controls, batch-call-clustered inference |
| **Batch composition** — which headlines share an API call | +3.6 points when out-of-window filler headlines join the batches; cross-session drift decomposes exactly into composition (+3.61) + endpoint (±1); linear anchoring explains ~1% of the shift (predicted +0.04), leaving the mechanism to response-level non-linear components | replicated with inverted run order (+3.50, pooled z = 3.4); anchoring θ = 0.36–0.38; downstream: slopes and ranks robust, fixed thresholds and daily signs are *not* |
| **Scoring noise** — repeat calls of the identical prompt | ICC = 0.92, 30% exact replication, within-SD ≈ 7.2 pts; 13% of variance is a batch-level "mood"; two temperature-zero rounds agree bitwise on only 83.3% of headlines — nondeterminism is partly server-side | two-way variance decomposition; pre-registered temperature-0 controls |
| **Price echoes** — headlines quoting realized prices | predictability directionally concentrates in the 15% of headlines that echo realized prices (priced β = 0.047 vs. clean β = 0.003, difference p = 0.10) | classifier precision 82.7% (52-headline itemized audit); reported as directional pending independent human labels |
| **Coverage selection** — which firms get news | coverage is selected on realized volatility (t = 2.76, firm+day FE, two-way clustered) | BH q = 0.014 within the declared family |

The baseline next-day association itself is marginal and draw-dependent: t ∈ [1.47, 2.12] across twelve independent scoring passes (fourteen archived draws including two within-condition means), so the paper's contribution is the **measurement audit**, not a new anomaly.

## What this repository contains

```
├── paper/                  LaTeX source (main.tex + sections/), script-generated tables (sections/gen/),
│                           compiled PDFs (v1 → v6 archive) and the final 35-page deliverable
├── src/                    Full pipeline: news collection, price collection, LLM scoring runs
│                           (sessions 1–5), LM dictionary, panel construction, analysis (v1–v5),
│                           mechanism/anchoring regressions, downstream-consequence analysis,
│                           table generators, QA scripts, power calculations
├── data/                   All archived inputs and outputs (see data_manifest.csv): 542 headlines,
│                           every score file for every condition and session, panel.csv, figures/,
│                           results JSONs for every analysis layer
├── audits/                 Process deliverables: original-draft audit (A), literature matrix (B),
│                           research plan (C), simulated referee (G), revision response (H),
│                           data-and-code audit (P0), problem list, fix logs, experiment reports (P1),
│                           pre-registration documents (P2), v6 revision log, journal positioning
├── annotation_package/     Two-rater human annotation kit for the 52 echo-flagged headlines
│                           (codebook, instructions, CSV sheets, κ analysis script)
├── logs/                   Raw API call logs with ISO timestamps for every scoring session
├── tests/                  test_numbers.py — 183 assertions locking published numbers to script outputs
├── data_manifest.csv       Provenance, role, and verification status of every data file
└── replication_notes.md    Reproduction limitations (API access, licensing)
```

## Reproducing

Environment: Python 3.12 (numpy, pandas, statsmodels, scipy, matplotlib, scikit-learn), Node/Bun with `z-ai-web-dev-sdk`, Tectonic ≥ 0.14 for LaTeX, Playwright + Chromium for the design diagram.

Core verification path (≈ 5 minutes; every number regenerates from archived inputs):

```bash
python3 src/analysis.py        # v1 statistics, bit-for-bit vs data/results.json
python3 src/analysis_v2.py     # audit-layer H1–H5, wild bootstrap, BH family (seeded)
python3 src/analysis_v3.py     # session-3 interleaved identity + composition experiments
python3 src/coverage_table.py  # Table 6 (36 firms, totals 341/240) + gen/table_coverage.tex
python3 src/descriptives.py    # Table 1, every cell regenerated + gen/table_desc.tex
python3 src/v_exclusion.py     # disclosed anonymization failure quantification
python3 src/batch_downstream.py  # downstream consequences of batch composition
python3 tests/test_numbers.py  # 183 assertions: paper numbers == script outputs
```

LLM re-scoring cannot be reproduced bit-for-bit (stochastic decoding, API-side variability) — that fact is one of the paper's findings. Archived score files are the source of truth; re-running the scoring scripts reproduces the *distributional* claims, not the exact draws.

## Integrity statement

- Every LLM score was produced by real API calls logged with timestamps in `logs/`; no score was hand-edited.
- All coefficients, bootstrap p-values, ICCs, and q-values in the paper are read directly from `data/*.json` outputs of deterministic scripts; 183 regression assertions (`tests/test_numbers.py`) lock them.
- Claims found wrong during the audit were **retracted in print** (v1→v2: dictionary "victory", monotonicity, volatility heterogeneity, "no coverage selection"; v2→v3: the identity-prior interpretation of a session-confounded contrast; v3→v5: the identity effect re-established at −2.8 by a pre-registered same-session interleaved design). Retractions are documented in `audits/` and the paper text.
- Disclosed defects: a anonymization no-op for ticker V (10/341 headlines, 5 "Visa Bulletin" contamination items), quantified with excluding-V robustness in Appendix B; a partial fifth-session data collection (63 of 84 planned calls completed at the time of drafting, pre-registered design and transforms archived, resume-safe checkpoints).
- The fifth session's identity-swap / neutral-prefix / temperature-zero controls are reported at their current completion levels; a resume runner (`src/llm_score_v5_resume.mjs`) completes the remaining calls when API quota allows.
- Null results are reported as null results. The staged design's forking-paths concerns are acknowledged in the paper (Section 3.5).

## Generative-AI use

The studied scoring instrument is a large language model (GLM-4-Plus, accessed via API). The research pipeline (literature collection, scoring runs, analysis code, manuscript drafting) was operated with AI assistance under the author's direction; the author designed the study, pre-specified the staged analyses, verified every reported number against the archived scripts and data, and takes full responsibility. The AI system is not an author.

## Citing

```bibtex
@techreport{tan2026dissecting,
  title       = {Dissecting LLM News Sentiment Scores: Identity Priors, Batch Composition,
                 Scoring Noise, and Price Echoes in Return Predictability},
  author      = {Tan, Chang},
  institution = {Dalian University of Technology},
  type        = {Working paper},
  year        = {2026},
  month       = {10},
  url         = {https://github.com/43aquarius/dissecting-llm-news-sentiment-scores}
}
```

## License

- **Code and scripts**: MIT License (see `LICENSE`).
- **Paper text**: the LaTeX source is provided for verification and extension; cite the working paper.
- **Data**: headlines are short quotations from public web pages, redistributed at fair-use scale (titles only); original publishers retain all rights. `data/lm_master_dict.csv` is the Loughran–McDonald Master Dictionary obtained from its public distribution — cite Loughran & McDonald (2011) and respect its license for redistribution beyond replication. Price data originates from NASDAQ's public chart API (factual market data).
