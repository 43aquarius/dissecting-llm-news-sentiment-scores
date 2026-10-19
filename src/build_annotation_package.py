#!/usr/bin/env python3
"""Build the two-rater human annotation package for the 52 echo-flagged headlines.

Outputs (replication_package_v2/annotation_package/):
  annotation_sheet.csv   -- one row per flagged headline; rater1_label and
                            rater2_label columns left EMPTY for humans to fill
  CODEBOOK.md            -- the written 4-category rulebook (P/E/D/N)
  INSTRUCTIONS.md        -- annotation protocol (independent raters, blind to
                            the LLM label column and to each other)

This script only assembles existing archived artifacts; it does not create any
labels. kappa_analysis.py computes inter-rater statistics once the sheet is filled.
"""
import csv
import json
import os

DATA = "/home/z/my-project/data"
OUT = "/home/z/my-project/replication_package_v2/annotation_package"
os.makedirs(OUT, exist_ok=True)

ph = json.load(open(f"{DATA}/priced_headlines.json"))
pc = json.load(open(f"{DATA}/priced_classification.json"))
labels = pc["labels"]

rows = []
for h in ph:
    rows.append({
        "iid": h["iid"],
        "ticker": h["ticker"],
        "date_iso": h["date_iso"],
        "title": h["title"],
        "matched_pattern": h["matched_pattern"],
        "regex_flag": 1,
        "llm_audit_label": labels.get(str(h["iid"]), ""),
        "rater1_label": "",
        "rater2_label": "",
        "rater1_note": "",
        "rater2_note": "",
    })
with open(f"{OUT}/annotation_sheet.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"wrote {OUT}/annotation_sheet.csv ({len(rows)} rows)")

rb = pc["rulebook"]
codebook = f"""# Codebook: Classifying Realized-Price ("Echo") Headlines

Four mutually exclusive categories. Apply the steps in order; the first step
that applies determines the label.

## Categories

**P -- Realized price move.** The headline states or clearly implies that the
company's stock price has ALREADY moved. Markers: past or present-perfect tense
("dropped 5% after earnings", "soars after results", "has gained 5% so far"),
performance summaries ("second-best day ever"), technical levels ("falls below
its 200-day moving average"). Includes realized moves stated together with a
fundamental cause ("shares jump on blowout results" -- the move is reported).

**E -- Fundamental magnitude.** The matched keyword describes a FUNDAMENTAL
result or event magnitude, not the stock: "revenue rises 12%" (the rise is the
revenue's), "sales jump 20%", expected quarterly results ("FQ1 gains" expected
from earnings), analyst catalyst actions. No realized stock-price move is stated.

**D -- Directional forecast.** The keyword is a forecast or expectation of
FUTURE stock direction: "could sink in 2026", "may drop to $300", "can it
bounce back?", price-target chatter without a realized move.

**N -- Regex false positive.** The keyword is incidental with no stock-price
meaning: "execution short fall" (shortfall, not a fall), "just dropped October
deals" (retail promotions released), "dropping a huge deal event" (a sale event).

## Tie rule

If a headline contains BOTH a realized stock move and a fundamental result,
classify **P**: the defining feature of an echo headline is that the realized
move is reported.

## Original rulebook text (verbatim, from priced_classification.json)

- Step 1 (P): {rb['step1_P']}
- Step 2 (E): {rb['step2_E']}
- Step 3 (D): {rb['step3_D']}
- Step 4 (N): {rb['step4_N']}
- Tie rule: {rb['tie_rule']}
"""
open(f"{OUT}/CODEBOOK.md", "w").write(codebook)
print(f"wrote {OUT}/CODEBOOK.md")

instructions = """# Instructions for Annotators

## What you are doing

A regular-expression classifier flagged {n} news headlines as containing
"realized-price language" (words like *rose*, *dropped*, *surged*). The
research team needs to know, for each headline, whether the flagged word really
refers to an already-realized move of the company's STOCK PRICE, or whether it
is a fundamental magnitude, a forecast, or a false positive of the keyword
match. Your labels are the human gold standard for this classification.

## Protocol (read before starting)

1. Work **independently**. Do not discuss the headlines or your labels with the
   other rater until both of you have finished and both sheets are submitted.
2. Read `CODEBOOK.md` first. The four categories (P, E, D, N) are applied in
   step order; the first step that applies wins. The tie rule is part of the
   codebook.
3. Open `annotation_sheet.csv`. Fill ONLY the columns `rater1_label` (Rater 1)
   or `rater2_label` (Rater 2) -- each rater fills their own copy of the sheet,
   downloaded separately -- and optionally the corresponding `note` column for
   cases you found difficult.
4. **Do not look at the `llm_audit_label` column while labeling.** It contains
   the research team's machine-assisted audit labels; the purpose of your work
   is to provide an independent standard. (If your copy is a shared file, hide
   that column before you begin.)
5. Judge each headline from its text alone. You are classifying what the
   headline SAYS, not what you know about the company.
6. There is no time limit; typical completion is 25-40 minutes for 52 short
   headlines. When you finish, return the filled CSV to the research team.

## After both raters finish

The team runs `kappa_analysis.py` on the merged sheet to compute:
- Cohen's kappa between the two human raters (the inter-rater reliability of
  the human gold standard);
- each rater's agreement with the original regex flag and with the team's
  LLM-assisted audit labels;
- the per-category confusion matrix and a list of headlines where the human
  raters disagree with each other or with the machine labels.

These statistics will be reported in the paper as the human-validation of the
echo classifier.
""".format(n=len(rows))
open(f"{OUT}/INSTRUCTIONS.md", "w").write(instructions)
print(f"wrote {OUT}/INSTRUCTIONS.md")
print("annotation package assembled (no labels created by this script)")
