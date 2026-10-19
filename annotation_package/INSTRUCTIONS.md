# Instructions for Annotators

## What you are doing

A regular-expression classifier flagged 52 news headlines as containing
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
