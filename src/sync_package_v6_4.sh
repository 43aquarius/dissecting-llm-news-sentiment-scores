#!/usr/bin/env bash
# Sync v6.4 artifacts into replication_package_v2 and github_repo (idempotent).
set -e
PKG=/home/z/my-project/replication_package_v2
REPO=/home/z/my-project/github_repo
PROJ=/home/z/my-project

# ---- paper sources + compiled ----
for DEST in "$PKG/paper" "$REPO/paper"; do
  cp "$PROJ/paper/main.tex" "$DEST/main.tex"
  cp "$PROJ/paper/sections/"*.tex "$DEST/sections/"
  cp "$PROJ/paper/sections/gen/"*.tex "$DEST/sections/gen/"
  cp "$PROJ/paper/cover.html" "$DEST/cover.html"
  cp "$PROJ/paper/main.pdf" "$DEST/main.pdf"
  cp "$PROJ/paper/checklist_onepage.tex" "$DEST/checklist_onepage.tex"
  cp "$PROJ/download/Audit_Protocol_Checklist_OnePage.pdf" "$DEST/Audit_Protocol_Checklist_OnePage.pdf"
  cp "$PROJ/download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf" \
     "$DEST/Dissecting_LLM_News_Sentiment_Scores_v6_4.pdf"
done
# refresh the unversioned current-paper file in the repo (was stale at v6.2 citations)
cp "$PROJ/download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf" \
   "$REPO/paper/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf"

# ---- data: new session-6/6b + analysis outputs ----
NEW_DATA="llm_scores_s6_named.json llm_scores_s6_anonv2.json llm_scores_s6_fictional.json \
llm_scores_s6b_b1a.json llm_scores_s6b_b25.json llm_scores_s6b_b5.json llm_scores_s6b_b1b.json \
s6b_sample.json s6_verify_report.json results_s6.json results_s6b.json \
results_level_tost.json results_swap_leakage.json s6_cue_lexicon.json"
for f in $NEW_DATA; do
  cp "$PROJ/data/$f" "$PKG/data/$f"
  cp "$PROJ/data/$f" "$REPO/data/$f"
done

# ---- src: new + updated scripts ----
NEW_SRC="llm_score_v6.mjs llm_score_v6b_batchsize.mjs analysis_v6.py analysis_v6b.py \
level_tost_and_margins.py swap_leakage_audit.py move_naive_benchmark.py promote_downstream.py \
build_onepage_checklist.py s6_fictional_map.json draw_range_check.py test_numbers.py \
frl_letter_check.py pdf_qa_v6.py"
for f in $NEW_SRC; do
  cp "$PROJ/scripts/$f" "$PKG/src/$f"
  cp "$PROJ/scripts/$f" "$REPO/src/$f"
done
cp "$PROJ/scripts/test_numbers.py" "$PKG/tests/test_numbers.py"
cp "$PROJ/scripts/test_numbers.py" "$REPO/tests/test_numbers.py"

# ---- logs ----
for f in llm_score_v6.log llm_score_v6b.log; do
  cp "$PROJ/scripts/$f" "$PKG/logs/$f"
done

# ---- audits ----
for f in P3_preregistration_session6.md P3_experiments_report.md P2_v6_revision_log.md \
         Submission_Package_and_Positioning.md Submission_Readiness_Checklist.md; do
  if [ -f "$PROJ/audits/$f" ]; then cp "$PROJ/audits/$f" "$PKG/audits/$f"; cp "$PROJ/audits/$f" "$REPO/audits/$f"; fi
  if [ -f "$PROJ/download/audit_reports/$f" ]; then cp "$PROJ/download/audit_reports/$f" "$PKG/audits/$f"; cp "$PROJ/download/audit_reports/$f" "$REPO/audits/$f"; fi
done
# prereg doc lives in audit/ (project) — copy both ways covered above

# ---- submission (letter v6.4) ----
for f in frl_letter.tex frl_letter.pdf cover_letter_FRL.md highlights.txt declarations_FRL.md; do
  cp "$PROJ/submission_frl/$f" "$REPO/submission/$f"
done

# ---- README/notes/manifest/CITATION ----
if ! grep -q "## v6.4 " "$PKG/replication_notes.md"; then
cat >> "$PKG/replication_notes.md" << 'EOF'

## v6.4 addendum (2026-10-25) — three-layer revision: session-6/6b experiments, level TOST, leakage audit

- New staged sessions (pre-registered in `audits/P3_preregistration_session6.md`, archived before collection): session 6 (fictional-name control: N6/A6/F6 over the identical 341, one sitting, three-way rotation; 41 calls) and session 6b (batch-size dose-response: 50 seeded headlines scored alone / in 5s / in 25s, one pass per size; 62 calls).
- Headline results: fictional-name condition lands midway between named and anonymized (+1.20 / -1.33; clustered p=0.45), splitting the de-identification displacement into ~half real-name and ~half placeholder-rewrite; de-identification effect replicates a third time (N6-A6 = -2.54); singleton-vs-25-batch level gap -0.20 (batch-size-1 zero point: composition requires changed mates); mood decomposition underpowered at one pass per size (disclosed).
- New analyses: level-layer TOST battery at a pre-fixed 1.25-point margin (`level_tost_and_margins.py`; prefix passes, swap EMT 1.73 headline / 3.22 clustered); economics-anchored 10 bps/SD margin on the prediction-layer battery (no contrast passes; verdicts margin-specific); swapped-text leakage audit (`swap_leakage_audit.py`; 15.0%/26.7% cue-flagged, 1.8% identity leaks via concatenated name variants; conclusions unchanged after exclusion).
- Wording downgrades throughout WP+letter per the referee directive (no "replicates/settles/rules out" for clustered-insignificant contrasts; temperature-0 attribution is "consistent with server-side nondeterminism"); the naive two-session benchmark paragraph moved from §5.2 to Appendix (app:session); the downstream-consequences table+figure promoted from the appendix into §5.2.
- Draw-stability count updated: 14 independent named passes across 6 sittings (16 archived draws incl. 2 within-condition means); ranges unchanged (beta [0.0104,0.0161], t [1.47,2.12]).
- Verify with: `cd paper && tectonic main.tex` (42 pp., 0 errors), `python tests/test_numbers.py` (323 checks), `python src/frl_letter_check.py` (109 checks; letter body 1,440 words), `python src/pdf_qa_v6.py` (65/65 key strings on the merged deliverable, 43 pp.).
EOF
fi
cp "$PKG/replication_notes.md" "$REPO/replication_notes.md"

# manifest: append new rows (idempotent)
for row in \
"llm_scores_s6_named.json,session-6 named anchor (341),llm_score_v6.mjs 2026-10-25,341 records,Sec 5.2 / App session6,verified (recomputable)" \
"llm_scores_s6_anonv2.json,session-6 anonymized-v2 (341),llm_score_v6.mjs 2026-10-25,341 records,Sec 5.2 / App session6,verified (recomputable)" \
"llm_scores_s6_fictional.json,session-6 fictional-name condition (341),llm_score_v6.mjs + s6_fictional_map.json,341 records,Sec 5.2 / App session6,verified (recomputable)" \
"llm_scores_s6b_b1a.json,session-6b singleton pass first half (25),llm_score_v6b_batchsize.mjs,25 records,App session6,verified" \
"llm_scores_s6b_b1b.json,session-6b singleton pass second half (25),llm_score_v6b_batchsize.mjs,25 records,App session6,verified" \
"llm_scores_s6b_b25.json,session-6b size-25 pass (50; 2 batches),llm_score_v6b_batchsize.mjs,50 records,App session6,verified" \
"llm_scores_s6b_b5.json,session-6b size-5 pass (50; 10 batches),llm_score_v6b_batchsize.mjs,50 records,App session6,verified" \
"s6b_sample.json,session-6b seeded 50-headline subsample order,llm_score_v6b_batchsize.mjs (seed 20261025),50 urls,App session6,verified" \
"s6_verify_report.json,session-6 verification gate report (both tiers zero),llm_score_v6.mjs,341 checks,App session6,verified" \
"results_s6.json,session-6 locked analysis,analysis_v6.py (seed 20261025),12 keys,Sec 5.2 / App session6,verified (recomputable)" \
"results_s6b.json,session-6b dose-response analysis,analysis_v6b.py,10 keys,App session6,verified (recomputable)" \
"results_level_tost.json,level-layer TOST + economics-margin battery,level_tost_and_margins.py (seed 20261025),5 level contrasts + 8 coef contrasts,App power,verified (recomputable)" \
"results_swap_leakage.json,swapped-text leakage audit,swap_leakage_audit.py,counts + rechecks,Sec 5.2 / App session6,verified (recomputable)" \
"s6_cue_lexicon.json,firm-specific cue lexicons (primary + sensitivity),swap_leakage_audit.py,36 firms,App session6,verified" \
"s6_fictional_map.json,36 invented firm names + synthetic tickers,construction (design choice),36 entries,App session6,archived (design input)" \
; do
  f=$(echo "$row" | cut -d, -f1)
  grep -q "^$f," "$PKG/data_manifest.csv" || echo "$row" >> "$PKG/data_manifest.csv"
done
# paper deliverable row update
sed -i 's|paper/Dissecting_LLM_News_Sentiment_Scores_v6_3_2.pdf,"compiled (v6.3.2 merged deliverable, cover + 39 pp.)"|paper/Dissecting_LLM_News_Sentiment_Scores_v6_4.pdf,"compiled (v6.4 merged deliverable, cover + 42 pp.; adds session-6/6b, level TOST, leakage audit)"|' "$PKG/data_manifest.csv"
grep -q "Audit_Protocol_Checklist_OnePage.pdf" "$PKG/data_manifest.csv" || \
  echo 'paper/Audit_Protocol_Checklist_OnePage.pdf,"one-page Minimal Audit Protocol checklist (generated from app:checklist source)",build_onepage_checklist.py,1 page,App checklist,verified' >> "$PKG/data_manifest.csv"
cp "$PKG/data_manifest.csv" "$REPO/data_manifest.csv"

# ---- README v6.4 note (idempotent) ----
for R in "$PKG/README.md" "$REPO/README.md"; do
  if ! grep -q "v6.4.0" "$R"; then
cat >> "$R" << 'EOF'

## v6.4.0 (2026-10-25) — referee-driven three-layer revision

- **Session 6 (fictional-name control, 41 calls)**: the invented-firm-name condition lands midway between named and anonymized (+1.20 / −1.33; clustered p=0.45), splitting the de-identification displacement into ~half real-name and ~half placeholder-rewrite; the de-identification effect replicates a third time (−2.54). Pre-registered in `audits/P3_preregistration_session6.md`; verification gate caught six concatenated-name identity leaks *before* any call (design deviation disclosed).
- **Session 6b (batch-size dose-response, 62 calls)**: batch-size-1 zero point established — singleton and 25-batch levels match on identical titles (−0.20 pts); the composition channel requires a changed mate pool, not batching per se; mood decomposition underpowered at one pass per size (disclosed).
- **New inference**: level-layer TOST at a pre-fixed 1.25-point margin (prefix certifies, swap EMT 1.73/3.22 — backing the downgraded "does not support a material firm-specific prior" wording); economics-anchored 10 bps/SD margin (no prediction-layer contrast passes; verdicts margin-specific); swapped-text leakage audit (15.0%/26.7% cue-flagged, 1.8% identity leaks; conclusions unchanged after exclusion).
- **Editorial**: cover overlap fixed (flow layout); "replicates/settles/rules out" wording downgraded throughout; the naive two-session benchmark moved to the appendix; the downstream-consequences table+figure promoted into main text §5.2; draw-stability now 14 passes / 6 sittings (ranges unchanged); one-page audit-protocol checklist added (`paper/Audit_Protocol_Checklist_OnePage.pdf`).
- Citation state: the current submission PDF (v6_4 and the unversioned file) cites Glasserman & Lin (2024, JFDS) and Korikov et al. (2025); archived v6.0–v6.3.1 PDFs intentionally retain the 2023 working-paper citation (history).
- Checks: `tests/test_numbers.py` 323/323 · `src/frl_letter_check.py` 109/109 · `src/pdf_qa_v6.py` 65/65 · WP 43 pp. (cover + 42), Tectonic 0 errors · letter 1,440 words.
EOF
  fi
done

# ---- CITATION.cff version bump ----
sed -i 's/version: 6\.3\.2/version: 6.4.0/; s/date-released: "2026-10-23"/date-released: "2026-10-25"/' "$REPO/CITATION.cff"

echo "v6.4 sync complete."
