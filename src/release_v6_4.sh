#!/usr/bin/env bash
# Create GitHub Release v6.4.0 with 5 assets and push local commits+tag.
# Usage: GH_TOKEN=<fresh fine-grained PAT with Contents:read/write> bash release_v6_4.sh
# NOTE (2026-10-25): the token used by earlier sessions was REVOKED/EXPIRED (401
# Bad credentials on both /user and repo endpoints). This script is ready to run
# the moment a fresh token is supplied; it pushes first, then creates the release.
set -e
TOKEN="${GH_TOKEN:?Set GH_TOKEN to a valid fine-grained PAT (Contents: read/write)}"
REPO="43aquarius/dissecting-llm-news-sentiment-scores"
API="https://api.github.com/repos/$REPO"
DIR=/home/z/my-project
GR="$DIR/github_repo"

echo "--- 0. sanity: token validity ---"
curl -s -o /dev/null -w "token check: %{http_code}\n" -H "Authorization: Bearer $TOKEN" "$API"

echo "--- 1. push branch + tag ---"
git -C "$GR" push "https://43aquaris:$TOKEN@github.com/$REPO.git" main
git -C "$GR" push "https://43aquaris:$TOKEN@github.com/$REPO.git" v6.4.0

echo "--- 2. create release ---"
python3 - "$TOKEN" > /tmp/release_payload_v64.json << 'PYEOF'
import json, sys
notes = """## v6.4.0 — Referee-driven three-layer revision (fictional-name control, batch-size zero point, level TOST, leakage audit)

**New staged experiments** (pre-registered in `audits/P3_preregistration_session6.md`, archived before collection):
- **Session 6 — fictional-name control (41 calls)**: scoring the identical 341 headlines with *invented* firm names (natural text, no real-world prior) lands almost exactly midway between named and anonymized (+1.20 above named, −1.33 below anonymized; clustered p=0.45): the de-identification displacement splits about evenly into a **real-name component (~half)** and a **placeholder-rewrite component (~half)**; the effect itself replicates a third time (N6−A6 = −2.54). The pre-collection verification gate blocked six concatenated-name identity leaks ("ExxonMobil", "JPMorganChase") *before any call* — disclosed as a design deviation.
- **Session 6b — batch-size dose-response (62 calls)**: the **batch-size-1 zero point** — singleton and 25-batch levels match on identical titles (−0.20 pts, t=−0.09): the +3.6-point composition channel requires a *changed mate pool*, not batching per se. Mood-vs-position decomposition underpowered at one pass per size (disclosed; design archived).

**New inference machinery**:
- **Level-layer TOST** at a pre-fixed 1.25-point margin: the prefix control certifies equivalence (EMT 1.10), the swap does not (EMT 1.73 headline / 3.22 clustered) — the formal basis for the downgraded wording ("does not support a material firm-specific prior", not "rules out").
- **Economics-anchored margin (10 bps/SD)**: no prediction-layer contrast passes (EMTs 11.5–29.8 bps/SD for identity contrasts); the equivalence verdicts are now explicitly margin-specific.
- **Swapped-text leakage audit**: 15.0%/26.7% of swapped headlines retain an original-firm lexical cue, 1.8% retain identity outright via concatenated name variants; excluding flagged headlines leaves every conclusion unchanged.

**Editorial (layer 1+3)**: cover overlap fixed (flow layout); "replicates/settles/rules out" downgraded throughout WP+letter; temperature-0 attribution now "consistent with server-side nondeterminism"; the naive two-session benchmark moved to the appendix; the downstream-consequences table+figure promoted into main text §5.2 (slopes/ranks robust vs thresholds/time-series not — at a glance); draw stability now 14 passes / 6 sittings (ranges unchanged: t∈[1.47,2.12], β∈[0.0104,0.0161]); a **one-page audit-protocol checklist** generated from the same source as the paper's appendix.

**Verification**: `tests/test_numbers.py` 323/323 · `src/frl_letter_check.py` 109/109 (letter body 1,440 words < 2,500) · `src/pdf_qa_v6.py` 65/65 key strings · WP 43 pp. (cover + 42), Tectonic 0 errors · in-package test net 323/323.

**Assets**: 43-page working paper · full replication package (232 files) · FRL letter (6 pp.) · FRL submission package (five-piece set) · one-page audit-protocol checklist."""
print(json.dumps({"tag_name": "v6.4.0",
                  "name": "v6.4.0 — fictional-name control, batch-size zero point, level TOST, leakage audit",
                  "body": notes}))
PYEOF

RESP=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  --data-binary @/tmp/release_payload_v64.json "$API/releases")
RID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))")
if [ -z "$RID" ]; then echo "RELEASE FAILED"; echo "$RESP" | head -5; exit 1; fi
echo "release id: $RID"

echo "--- 3. upload assets (data-binary @file) ---"
upload() {  # name, path, ctype
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: ${3:-application/octet-stream}" \
    --data-binary "@$2" \
    "https://uploads.github.com/repos/$REPO/releases/$RID/assets?name=$1" | python3 -c "import json,sys; d=json.load(sys.stdin); print('uploaded:', d.get('name'), d.get('size'), d.get('state'))"
}
upload "Dissecting_LLM_News_Sentiment_Scores_v6_4.pdf" \
  "$DIR/github_repo/paper/Dissecting_LLM_News_Sentiment_Scores_v6_4.pdf" "application/pdf"
upload "Replication_Package_v2_Audit.zip" \
  "$DIR/download/Replication_Package_v2_Audit.zip" "application/zip"
upload "FRL_Letter_v6_4.pdf" \
  "$DIR/submission_frl/frl_letter.pdf" "application/pdf"
upload "FRL_Submission_Package_v6_4_0.zip" \
  "$DIR/download/submission_frl/FRL_Submission_Package_v6_4_0.zip" "application/zip"
upload "Audit_Protocol_Checklist_OnePage.pdf" \
  "$DIR/download/Audit_Protocol_Checklist_OnePage.pdf" "application/pdf"

echo "--- 4. verify ---"
curl -s "https://api.github.com/repos/$REPO/releases/latest" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print('latest:', d.get('tag_name')); [print(' ', a['name'], a['size']) for a in d.get('assets',[])]"
echo "v6.4.0 release complete."
