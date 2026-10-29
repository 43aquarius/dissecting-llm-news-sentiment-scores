# Cover Letter — Journal of Forecasting submission

**To:** The Editors, *Journal of Forecasting*
**From:** Chang Tan, Dalian University of Technology (aquars43@foxmail.com)
**Re:** Submission of "Dissecting LLM News Sentiment Scores: De-Identification, Batch Composition, Scoring Noise, and Price Echoes in Return Predictability"

Dear Editors,

Please consider the enclosed manuscript, "Dissecting LLM News Sentiment Scores: De-Identification, Batch Composition, Scoring Noise, and Price Echoes in Return Predictability," for publication as a regular research article in the *Journal of Forecasting*.

Forecasting with machine-generated sentiment is spreading quickly through finance, but the measuring instrument itself is rarely audited. This paper provides that audit inside a next-day U.S. stock-return forecasting design: 542 search-collected news headlines on 36 large-cap firms (341 in-window, July–October 2026), scored $-100$ to $+100$ by GLM-4-Plus across six sittings and fourteen re-scorings, with every channel varied one ingredient at a time. The manuscript should interest the journal's readership on three forecasting-relevant grounds:

1. **Signal reliability, quantified.** The instrument is stochastic, not deterministic: ICC 0.92 across sessions, only 30% exact replication across repeated calls, and temperature-zero decoding restores bitwise determinism for just 83% of headlines. The baseline next-day association (coefficient 0.0149, $t=2.10$, BH $q=0.062$) is marginal and draw-dependent across sixteen archived scoring draws — a caution for anyone forecasting on LLM signals from a single pass.

2. **Two context channels that move the signal without moving the news.** De-identification (replacing the firm's real name with a placeholder) raises score levels by 2.6 points pooled across three sessions (95% CI 1.1–4.1); swapping in another firm's name moves levels by essentially nothing — the effect is the removal of the name, not a company prior. Batch composition — which headlines share an API call — moves levels by 3.6 points, survives inverted run order, and defies a linear-anchoring explanation. Slope-based and cross-sectional uses are robust to both channels, but a fixed +50 threshold doubles its trade count under a mere re-batching of identical headlines, and day-over-day sign changes flip on up to a quarter of trading days.

3. **A deployment-ready audit protocol.** We distill the findings into a seven-step protocol — anonymized, repeated, batch-frozen, session-interleaved scoring with call-clustered inference — that should precede any deployment of LLM sentiment as a forecasting input.

Every number in the paper regenerates deterministically from an archived replication package (all score sets, per-call API logs, seeds, prices, and scripts, publicly released), and the design documents for each staged session were archived before data collection. The full evidence base, including power tables, equivalence tests, mechanism accounting, and the staged-session design documents, appears in the 18-page Online Appendix submitted as Supporting Information.

The manuscript is original, is not under consideration elsewhere, and I have no competing interests. It has a single author; author details and all required statements (data availability, funding, competing interests, generative-AI use) appear on the title page of the manuscript itself, in keeping with the journal's free-format submission policy.

Thank you for your consideration.

Sincerely,

Chang Tan
Dalian University of Technology
aquars43@foxmail.com
